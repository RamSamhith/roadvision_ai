#!/usr/bin/env python3
"""S4-T3A dataset policy audit (READ-ONLY).

Answers Q-03 (class mapping / out-of-scope annotations) and Q-04 (duplicates,
near-duplicate threshold, splitting) with measured evidence.

Nothing here writes into ``data/raw``.  The tool only reads images and XML
files and writes audit artefacts under ``data/reports/audit``.

Deliberate design points
------------------------
* Near-duplicate buckets are never silently skipped.  Images that share an
  identical 64-bit dHash are collapsed to one representative before pairwise
  comparison, which removes the degenerate blow-up that the S4-T2 inspection
  handled with a 500-image cap.  A hard safety ceiling exists, but exceeding it
  raises an error instead of skipping data.
* Candidate pairs use pigeonhole bucketing over 8 x 8-bit chunks, which is
  exact for every Hamming distance <= 7 (a pair at distance d <= 7 must share
  at least one of 8 chunks).  The threshold study therefore never misses a pair
  it claims to report.
* Ambiguous groups are reported separately, never merged silently.

Usage
-----
    .\\.venv\\Scripts\\python.exe training\\audit_dataset_policy.py
    .\\.venv\\Scripts\\python.exe training\\audit_dataset_policy.py --countries China_Drone
    .\\.venv\\Scripts\\python.exe training\\audit_dataset_policy.py --refresh-hashes
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import random
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DEFAULT = PROJECT_ROOT / "data" / "raw" / "RDD2022"
OUT_DEFAULT = PROJECT_ROOT / "data" / "reports" / "audit"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}

# TDD v1.1 section 4.3 - fixed mapping.  Exact string equality only.
CODE_TO_ID = {"D00": 0, "D10": 1, "D20": 2, "D40": 3}
TARGET_CODES = tuple(CODE_TO_ID)
TOL_PX = 2.0

# Every code observed in RDD2022 (S4-T2 inspection, re-derived here).
KNOWN_CODES = {
    "D00", "D10", "D20", "D40",
    "D01", "D0w0", "D11", "D43", "D44", "D50",
    "Repair", "Block crack",
}

HASH_CHUNKS = 8          # 8 x 8-bit pigeonhole chunks -> exact for d <= 7
CHUNK_BITS = 64 // HASH_CHUNKS
CHUNK_MASK = (1 << CHUNK_BITS) - 1
MAX_DISTANCE = 6         # threshold study range
FINAL_THRESHOLD = 3      # TDD skeleton recommendation, under test here
HARD_PAIR_LIMIT = 400_000_000
MAX_LIST = 25
PROGRESS_EVERY = 2000
CACHE_VERSION = 1


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def rel_key(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def classify(path: Path, root: Path) -> tuple[str, str]:
    parts = path.relative_to(root).parts
    country = parts[0] if parts else "<unknown>"
    split = "<unknown>"
    for part in parts[1:-1]:
        lowered = part.lower()
        if lowered in {"train", "training"}:
            return country, "train"
        if lowered in {"test", "testing"}:
            return country, "test"
        if lowered in {"val", "valid", "validation"}:
            return country, "val"
    return country, split


def dhash64(bgr: np.ndarray, hash_size: int = 8) -> int:
    """64-bit difference hash, identical to training/inspect_dataset.py."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (hash_size + 1, hash_size), interpolation=cv2.INTER_AREA)
    diff = resized[:, 1:] > resized[:, :-1]
    packed = np.packbits(diff.reshape(-1)).tobytes()
    return int.from_bytes(packed, "big")


def pct(part: float, total: float, digits: int = 2) -> float:
    return round(100.0 * part / total, digits) if total else 0.0


def median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return round(ordered[mid], 4)
    return round((ordered[mid - 1] + ordered[mid]) / 2.0, 4)


def quantile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(round(q * (len(ordered) - 1)))))
    return round(ordered[idx], 4)


class UnionFind:
    def __init__(self) -> None:
        self.parent: dict[int, int] = {}

    def find(self, x: int) -> int:
        self.parent.setdefault(x, x)
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != x:
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra

    def components(self) -> dict[int, list[int]]:
        out: dict[int, list[int]] = collections.defaultdict(list)
        for node in list(self.parent):
            out[self.find(node)].append(node)
        return out


# --------------------------------------------------------------------------- #
# Part A - annotation / class-mapping audit
# --------------------------------------------------------------------------- #
def audit_annotations(
    root: Path,
    xml_paths: list[Path],
    image_paths: list[Path],
    dims: dict[str, tuple[int, int]],
) -> dict:
    started = time.perf_counter()

    image_index: dict[tuple[str, str, str], str] = {}
    no_xml_paths: list[str] = []
    for path in image_paths:
        country, split = classify(path, root)
        image_index[(country, split, path.stem.lower())] = rel_key(path, root)

    per_image: dict[str, dict] = {}
    cat = collections.Counter()
    country_cat: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    class_objects = collections.Counter()
    class_images = collections.Counter()
    class_countries: dict[str, set] = collections.defaultdict(set)
    raw_name_variants = collections.Counter()
    whitespace_variants = collections.Counter()
    unknown_codes = collections.Counter()
    only_oos_combo = collections.Counter()
    only_oos_by_code = collections.Counter()
    only_oos_by_country = collections.Counter()
    mixed_by_country = collections.Counter()
    empty_by_country = collections.Counter()
    exclusion_target = collections.Counter()
    exclusion_oos = collections.Counter()
    clipped_target = 0
    clipped_oos = 0
    xml_size_mismatch = 0
    xml_missing_image: list[str] = []
    missing_names = 0
    total_objects = 0
    total_target = 0
    total_target_retained = 0
    total_oos = 0
    target_objs_in_mixed = 0
    target_retained_in_mixed = 0

    empty_paths: list[str] = []
    only_oos_paths: list[str] = []
    pool_a_paths: list[str] = []
    mapping_zero_paths: list[str] = []

    for idx, xml_path in enumerate(xml_paths, 1):
        country, split = classify(xml_path, root)
        img_rel = image_index.get((country, split, xml_path.stem.lower()))
        if img_rel is None:
            xml_missing_image.append(rel_key(xml_path, root))
            img_rel = None

        parsed = ET.parse(xml_path).getroot()
        objects = list(parsed.iter("object"))
        total_objects += len(objects)
        codes: set[str] = set()
        kept_by_code: collections.Counter = collections.Counter()
        n_target = n_target_kept = n_oos = 0

        true_wh = dims.get(img_rel) if img_rel else None
        if true_wh is None:
            # fall back to the XML size only for the geometric rules
            size = parsed.find("size")
            try:
                true_wh = (int(float(size.findtext("width"))), int(float(size.findtext("height"))))
            except (AttributeError, TypeError, ValueError):
                true_wh = None
        else:
            size = parsed.find("size")
            try:
                xw = int(float(size.findtext("width")))
                xh = int(float(size.findtext("height")))
                if (xw, xh) != true_wh:
                    xml_size_mismatch += 1
            except (AttributeError, TypeError, ValueError):
                pass

        for obj in objects:
            raw_name = obj.findtext("name")
            raw_name_variants[repr(raw_name)] += 1
            code = (raw_name or "").strip()
            if raw_name is not None and raw_name != code:
                whitespace_variants[repr(raw_name)] += 1
            if not code:
                missing_names += 1
                continue
            if code not in KNOWN_CODES:
                unknown_codes[code] += 1
            codes.add(code)
            class_objects[code] += 1
            class_countries[code].add(country)

            is_target = code in CODE_TO_ID
            if is_target:
                n_target += 1
                total_target += 1
            else:
                n_oos += 1
                total_oos += 1

            # TDD section 4.3 validation rules, applied in the documented order
            bb = obj.find("bndbox")
            try:
                x1 = float(bb.findtext("xmin"))
                y1 = float(bb.findtext("ymin"))
                x2 = float(bb.findtext("xmax"))
                y2 = float(bb.findtext("ymax"))
            except (AttributeError, TypeError, ValueError):
                (exclusion_target if is_target else exclusion_oos)["bad_box_values"] += 1
                continue

            x1, x2 = sorted((x1, x2))
            y1, y2 = sorted((y1, y2))

            if true_wh is not None:
                W, H = true_wh
                if x1 < -TOL_PX or y1 < -TOL_PX or x2 > W + TOL_PX or y2 > H + TOL_PX:
                    (exclusion_target if is_target else exclusion_oos)["out_of_bounds"] += 1
                    continue
                cx1, cy1 = max(0.0, x1), max(0.0, y1)
                cx2, cy2 = min(float(W), x2), min(float(H), y2)
            else:
                cx1, cy1, cx2, cy2 = x1, y1, x2, y2

            if (cx1, cy1, cx2, cy2) != (x1, y1, x2, y2):
                if is_target:
                    clipped_target += 1
                else:
                    clipped_oos += 1
            if cx2 - cx1 < 1 or cy2 - cy1 < 1:
                (exclusion_target if is_target else exclusion_oos)["degenerate"] += 1
                continue
            if is_target:
                n_target_kept += 1
                total_target_retained += 1
                kept_by_code[code] += 1

        for code in codes:
            class_images[code] += 1

        if not objects:
            category = "empty_xml"
            empty_paths.append(img_rel or rel_key(xml_path, root))
        elif n_target and n_oos:
            category = "mixed_target_oos"
            mixed_by_country[country] += 1
            only_oos_combo["+".join(sorted(c for c in codes if c not in CODE_TO_ID))] += 1
        elif n_target:
            category = "only_target"
        else:
            category = "only_oos"
            only_oos_paths.append(img_rel or rel_key(xml_path, root))
            only_oos_by_country[country] += 1
            for code in codes:
                if code not in CODE_TO_ID:
                    only_oos_by_code[code] += 1
            only_oos_combo["+".join(sorted(codes))] += 1
        cat[category] += 1
        country_cat[country][category] += 1
        if category == "empty_xml":
            empty_by_country[country] += 1

        if category in {"mixed_target_oos"}:
            target_objs_in_mixed += n_target
            target_retained_in_mixed += n_target_kept

        if n_target_kept >= 1:
            pool_a_paths.append(img_rel or rel_key(xml_path, root))
        elif n_target >= 1:
            mapping_zero_paths.append(img_rel or rel_key(xml_path, root))

        per_image[img_rel or rel_key(xml_path, root)] = {
            "country": country,
            "split": split,
            "category": category,
            "codes": sorted(codes),
            "objects": len(objects),
            "target_objects": n_target,
            "target_retained": n_target_kept,
            "oos_objects": n_oos,
            "kept_by_code": dict(kept_by_code),
        }

        if idx % PROGRESS_EVERY == 0:
            print(f"  xml audited: {idx}/{len(xml_paths)}", flush=True)

    annotated = len(per_image)
    no_xml = [p for p in image_index.values() if p not in per_image]

    summary = {
        "elapsed_s": round(time.perf_counter() - started, 1),
        "xml_files": len(xml_paths),
        "annotated_images": annotated,
        "images_without_xml": len(no_xml),
        "images_without_xml_by_country": dict(
            sorted(collections.Counter(p.split("/")[0] for p in no_xml).items())
        ),
        "objects_total": total_objects,
        "image_categories": {
            "only_target": cat["only_target"],
            "mixed_target_oos": cat["mixed_target_oos"],
            "only_oos": cat["only_oos"],
            "empty_xml": cat["empty_xml"],
            "check_sum_equals_annotated": (
                cat["only_target"] + cat["mixed_target_oos"] + cat["only_oos"] + cat["empty_xml"]
                == annotated
            ),
        },
        "category_by_country": {k: dict(sorted(v.items())) for k, v in sorted(country_cat.items())},
        "class_objects": dict(sorted(class_objects.items(), key=lambda kv: -kv[1])),
        "class_images": dict(sorted(class_images.items(), key=lambda kv: -kv[1])),
        "class_countries": {k: sorted(v) for k, v in sorted(class_countries.items())},
        "raw_name_variants": dict(sorted(raw_name_variants.items(), key=lambda kv: -kv[1])),
        "names_differing_after_strip": dict(whitespace_variants),
        "unknown_codes_not_in_known_set": dict(unknown_codes),
        "objects_without_name": missing_names,
        "target_objects": total_target,
        "target_objects_retained_after_rules": total_target_retained,
        "target_objects_excluded": total_target - total_target_retained,
        "target_exclusion_reasons": dict(exclusion_target),
        "target_boxes_clipped": clipped_target,
        "oos_objects": total_oos,
        "oos_exclusion_reasons": dict(exclusion_oos),
        "oos_boxes_clipped": clipped_oos,
        "target_objects_in_mixed_images": target_objs_in_mixed,
        "target_objects_retained_in_mixed_images": target_retained_in_mixed,
        "images_with_retained_target": len(pool_a_paths),
        "images_with_target_but_zero_retained": len(mapping_zero_paths),
        "mapping_zero_sample": mapping_zero_paths[:MAX_LIST],
        "xml_size_mismatch": xml_size_mismatch,
        "xml_without_image": len(xml_missing_image),
        "only_oos_by_code": dict(sorted(only_oos_by_code.items(), key=lambda kv: -kv[1])),
        "only_oos_by_country": dict(sorted(only_oos_by_country.items(), key=lambda kv: -kv[1])),
        "only_oos_code_combination": dict(
            sorted(only_oos_combo.items(), key=lambda kv: -kv[1])[:20]
        ),
        "mixed_by_country": dict(sorted(mixed_by_country.items(), key=lambda kv: -kv[1])),
        "empty_by_country": dict(sorted(empty_by_country.items(), key=lambda kv: -kv[1])),
        "_paths": {
            "empty": empty_paths,
            "only_oos": only_oos_paths,
            "pool_a": pool_a_paths,
            "no_xml": no_xml,
        },
        "_per_image": per_image,
    }
    return summary


# --------------------------------------------------------------------------- #
# Part B - image hashing (cached) and duplicate audit
# --------------------------------------------------------------------------- #
def build_hash_cache(
    root: Path,
    image_paths: list[Path],
    cache_path: Path,
    refresh: bool,
) -> dict[str, list]:
    cache: dict[str, list] = {}
    if cache_path.exists() and not refresh:
        raw = json.loads(cache_path.read_text(encoding="utf-8"))
        if raw.get("version") == CACHE_VERSION:
            cache = raw.get("entries", {})
            print(f"  hash cache: {len(cache)} entries loaded", flush=True)

    todo = [p for p in image_paths if rel_key(p, root) not in cache]
    print(f"  hash cache: {len(todo)} images to hash", flush=True)
    started = time.perf_counter()
    failed: list[str] = []

    for idx, path in enumerate(todo, 1):
        key = rel_key(path, root)
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        array = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        if array is None:
            failed.append(key)
            cache[key] = [digest, None, None, None]
        else:
            height, width = array.shape[:2]
            cache[key] = [digest, dhash64(array), int(width), int(height)]
        if idx % PROGRESS_EVERY == 0:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(
                json.dumps({"version": CACHE_VERSION, "entries": cache}, ensure_ascii=False),
                encoding="utf-8",
            )
            elapsed = time.perf_counter() - started
            print(
                f"  hashed: {idx}/{len(todo)} ({idx / max(elapsed, 1e-9):.1f}/s)",
                flush=True,
            )

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps({"version": CACHE_VERSION, "entries": cache}, ensure_ascii=False),
        encoding="utf-8",
    )
    print(
        f"  hash cache written ({len(cache)} entries, {len(failed)} unreadable, "
        f"{round(time.perf_counter() - started, 1)} s for {len(todo)} new)",
        flush=True,
    )
    return cache


def verify_hash_implementation(root: Path, cache: dict[str, list], sample: int = 300) -> dict:
    """Prove this file's dHash equals training/inspect_dataset.py on real images."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from inspect_dataset import dhash as reference_dhash  # type: ignore
    except Exception as exc:  # pragma: no cover - import guard
        return {"checked": 0, "agreement": None, "error": f"{type(exc).__name__}: {exc}"}

    keys = [k for k, v in cache.items() if v[1] is not None]
    rng = random.Random(42)
    rng.shuffle(keys)
    checked = 0
    agree = 0
    for key in keys[:sample]:
        array = cv2.imread(str(root / key))
        if array is None:
            continue
        checked += 1
        if dhash64(array) == reference_dhash(array) and dhash64(array) == cache[key][1]:
            agree += 1
    return {"checked": checked, "agreement": agree, "all_match": checked == agree}


def enumerate_candidate_edges(unique_hashes: list[int], max_distance: int) -> tuple[dict, dict]:
    """Pigeonhole over 8 x 8-bit chunks. Exact for d <= 7; returns edges + bucket stats."""
    n = len(unique_hashes)
    edges: dict[tuple[int, int], int] = {}
    comparisons = 0
    largest_bucket = 0
    oversized = 0
    per_chunk_buckets = 0

    for chunk in range(HASH_CHUNKS):
        shift = chunk * CHUNK_BITS
        buckets: dict[int, list[int]] = collections.defaultdict(list)
        for i, h in enumerate(unique_hashes):
            buckets[(h >> shift) & CHUNK_MASK].append(i)
        per_chunk_buckets += len(buckets)
        for members in buckets.values():
            size = len(members)
            if size < 2:
                continue
            largest_bucket = max(largest_bucket, size)
            if size > 5000:
                oversized += 1
            comparisons += size * (size - 1) // 2
            if comparisons > HARD_PAIR_LIMIT:
                raise RuntimeError(
                    f"candidate pair budget exceeded ({comparisons}); refusing to skip buckets"
                )
            for a in range(size):
                ia = members[a]
                ha = unique_hashes[ia]
                for b in range(a + 1, size):
                    ib = members[b]
                    dist = (ha ^ unique_hashes[ib]).bit_count()
                    if dist <= max_distance:
                        key = (ia, ib) if ia < ib else (ib, ia)
                        if key not in edges:
                            edges[key] = dist

    stats = {
        "unique_hashes": n,
        "chunks": HASH_CHUNKS,
        "chunk_bits": CHUNK_BITS,
        "buckets_total": per_chunk_buckets,
        "largest_bucket_unique_hashes": largest_bucket,
        "buckets_over_5000": oversized,
        "pairwise_comparisons": comparisons,
        "pairs_within_max_distance": len(edges),
        "max_distance_enumerated": max_distance,
    }
    return edges, stats


def groups_at_threshold(
    unique_hashes: list[int],
    edges: dict,
    threshold: int,
    hash_to_paths: dict[int, list[str]],
) -> list[list[int]]:
    dsu = UnionFind()
    for i in range(len(unique_hashes)):
        dsu.parent[i] = i
    for (a, b), dist in edges.items():
        if dist <= threshold:
            dsu.union(a, b)
    comps = dsu.components()
    # A component is a duplicate group when it holds at least two images.
    # Identical hashes were collapsed into one node, so count image paths.
    return [
        members
        for members in comps.values()
        if sum(len(hash_to_paths.get(unique_hashes[i], [])) for i in members) > 1
    ]


def near_group_analysis(
    groups: list[list[int]],
    unique_hashes: list[int],
    hash_to_paths: dict[int, list[str]],
    per_image: dict[str, dict],
    edges: dict,
    threshold: int,
) -> dict:
    """Describe groups, flag chained / label-inconsistent / cross-split groups."""
    image_groups: list[list[str]] = []
    for members in groups:
        paths: list[str] = []
        for idx in members:
            paths.extend(hash_to_paths.get(unique_hashes[idx], []))
        image_groups.append(sorted(paths))

    sizes = sorted((len(g) for g in image_groups), reverse=True)
    split_sets = collections.Counter()
    country_sets = collections.Counter()
    cat_sets = collections.Counter()
    cross_split: list[dict] = []
    cross_country: list[dict] = []
    mixed_label_groups: list[dict] = []
    chained: list[dict] = []
    pathological_ids: set[int] = set()

    def edge_dist(a_hash: int, b_hash: int) -> int:
        return (a_hash ^ b_hash).bit_count()

    for group_id, members in enumerate(groups):
        paths = image_groups[group_id]
        if len(paths) < 2:
            continue
        splits = {per_image[p]["split"] if p in per_image else "no_xml" for p in paths}
        countries = {per_image[p]["country"] if p in per_image else p.split("/", 1)[0] for p in paths}
        cats = {
            per_image[p]["category"] if p in per_image else "no_xml"
            for p in paths
        }
        split_sets["|".join(sorted(splits))] += 1
        country_sets["|".join(sorted(countries))] += 1
        cat_sets["+".join(sorted(cats))] += 1

        if len(splits) > 1:
            cross_split.append(
                {
                    "group_id": group_id,
                    "size": len(paths),
                    "splits": sorted(splits),
                    "members": paths[:8],
                }
            )
        if len(countries) > 1:
            cross_country.append(
                {
                    "group_id": group_id,
                    "size": len(paths),
                    "countries": sorted(countries),
                    "members": paths[:8],
                }
            )

        # An XML-bearing image with zero target objects sitting in the same
        # duplicate group as a target-labelled image is annotation evidence.
        has_target = any(
            per_image.get(p, {}).get("target_objects", 0) > 0 for p in paths
        )
        has_empty_labelled = any(
            (p in per_image) and per_image[p]["target_objects"] == 0 for p in paths
        )
        if has_target and has_empty_labelled:
            mixed_label_groups.append(
                {
                    "group_id": group_id,
                    "size": len(paths),
                    "categories": dict(collections.Counter(
                        per_image[p]["category"] if p in per_image else "no_xml" for p in paths
                    )),
                    "members": [
                        {
                            "path": p,
                            "category": per_image[p]["category"] if p in per_image else "no_xml",
                            "codes": per_image[p]["codes"] if p in per_image else [],
                        }
                        for p in paths[:6]
                    ],
                }
            )

        # chained group: diameter greater than the threshold (transitive merge)
        if len(members) > 1:
            diameter = 0
            for a in range(len(members)):
                ha = unique_hashes[members[a]]
                for b in range(a + 1, len(members)):
                    diameter = max(diameter, edge_dist(ha, unique_hashes[members[b]]))
            if diameter > threshold:
                pathological_ids.add(group_id)
                chained.append(
                    {
                        "group_id": group_id,
                        "size": len(paths),
                        "diameter": diameter,
                        "splits": sorted(splits),
                        "countries": sorted(countries),
                        "members": paths[:6],
                    }
                )

    return {
        "threshold": threshold,
        "groups": len(image_groups),
        "images_in_groups": sum(len(g) for g in image_groups),
        "size_distribution_top": sizes[:20],
        "largest_group": sizes[0] if sizes else 0,
        "groups_by_size": dict(sorted(collections.Counter(sizes).items())),
        "cross_split_groups": cross_split,
        "cross_split_group_count": len(cross_split),
        "split_signatures": dict(sorted(split_sets.items(), key=lambda kv: -kv[1])),
        "cross_country_groups": cross_country,
        "cross_country_group_count": len(cross_country),
        "label_inconsistent_groups": mixed_label_groups,
        "label_inconsistent_group_count": len(mixed_label_groups),
        "chained_groups": chained,
        "chained_group_count": len(chained),
        "_image_groups": image_groups,
        "_pathological_ids": sorted(pathological_ids),
    }


def pixel_similarity(root: Path, path_a: str, path_b: str) -> tuple[float, float]:
    a = cv2.imread(str(root / path_a), cv2.IMREAD_GRAYSCALE)
    b = cv2.imread(str(root / path_b), cv2.IMREAD_GRAYSCALE)
    if a is None or b is None:
        return (math.nan, math.nan)
    a = cv2.resize(a, (32, 32), interpolation=cv2.INTER_AREA).astype(np.float32)
    b = cv2.resize(b, (32, 32), interpolation=cv2.INTER_AREA).astype(np.float32)
    av, bv = a.reshape(-1), b.reshape(-1)
    if av.std() < 1e-6 or bv.std() < 1e-6:
        corr = 1.0 if np.allclose(av, bv) else 0.0
    else:
        corr = float(np.corrcoef(av, bv)[0, 1])
    mad = float(np.mean(np.abs(av - bv)) / 255.0)
    return corr, mad


def verify_threshold_pairs(
    root: Path,
    edges: dict,
    unique_hashes: list[int],
    hash_to_paths: dict[int, list[str]],
    per_distance: int,
    seed: int,
) -> dict:
    rng = random.Random(seed)
    by_distance: dict[int, list[tuple[str, str]]] = collections.defaultdict(list)
    for (a, b), dist in edges.items():
        pa = hash_to_paths[unique_hashes[a]][0]
        pb = hash_to_paths[unique_hashes[b]][0]
        by_distance[dist].append((pa, pb))

    out: dict[str, dict] = {}
    for dist in range(MAX_DISTANCE + 1):
        pairs = by_distance.get(dist, [])
        if not pairs:
            continue
        rng.shuffle(pairs)
        sample = pairs[:per_distance]
        corrs: list[float] = []
        mads: list[float] = []
        suspicious: list[dict] = []
        for pa, pb in sample:
            corr, mad = pixel_similarity(root, pa, pb)
            if not math.isnan(corr):
                corrs.append(corr)
                mads.append(mad)
                if corr < 0.75 and len(suspicious) < 10:
                    suspicious.append({"a": pa, "b": pb, "corr": round(corr, 4)})
        out[str(dist)] = {
            "pairs_available": len(pairs),
            "pairs_sampled": len(corrs),
            "correlation_median": median(corrs),
            "correlation_p10": quantile(corrs, 0.10),
            "correlation_min": round(min(corrs), 4) if corrs else None,
            "mad_median": median(mads),
            "mad_p90": quantile(mads, 0.90),
            "fraction_corr_below_0_90": round(
                sum(1 for c in corrs if c < 0.90) / len(corrs), 4
            ) if corrs else None,
            "fraction_corr_below_0_75": round(
                sum(1 for c in corrs if c < 0.75) / len(corrs), 4
            ) if corrs else None,
            "suspicious_samples": suspicious,
        }
    return out


def sequential_pair_analysis(
    root: Path,
    image_paths: list[Path],
    cache: dict[str, list],
    seed: int = 42,
    pixel_sample: int = 120,
) -> dict:
    """Hamming distance between consecutive file numbers inside one folder.

    RDD2022 contains video-derived image sequences.  This measures how far apart
    consecutive frames are under the chosen hash, which is the empirical basis
    for a near-duplicate threshold that keeps neighbouring frames together.
    """
    by_group: dict[tuple[str, str], list[Path]] = collections.defaultdict(list)
    for path in image_paths:
        by_group[classify(path, root)].append(path)

    def natural_key(path: Path):
        digits = "".join(ch for ch in path.stem if ch.isdigit())
        return (int(digits) if digits else 0, path.stem)

    distances: list[int] = []
    pairs: list[tuple[str, str, int]] = []
    per_country: dict[str, list[int]] = collections.defaultdict(list)
    for (country, _split), paths in sorted(by_group.items()):
        ordered = sorted(paths, key=natural_key)
        for a, b in zip(ordered, ordered[1:]):
            ea = cache.get(rel_key(a, root))
            eb = cache.get(rel_key(b, root))
            if not ea or not eb or ea[1] is None or eb[1] is None:
                continue
            dist = (ea[1] ^ eb[1]).bit_count()
            distances.append(dist)
            per_country[country].append(dist)
            pairs.append((rel_key(a, root), rel_key(b, root), dist))

    buckets = collections.Counter()
    for dist in distances:
        if dist <= 2:
            buckets["0-2"] += 1
        elif dist <= 4:
            buckets["3-4"] += 1
        elif dist <= 6:
            buckets["5-6"] += 1
        elif dist <= 8:
            buckets["7-8"] += 1
        elif dist <= 12:
            buckets["9-12"] += 1
        elif dist <= 16:
            buckets["13-16"] += 1
        elif dist <= 24:
            buckets["17-24"] += 1
        else:
            buckets["25+"] += 1

    rng = random.Random(seed)
    sample = pairs[:]
    rng.shuffle(sample)
    sample = sample[:pixel_sample]
    corrs: list[float] = []
    mads: list[float] = []
    for pa, pb, _dist in sample:
        corr, mad = pixel_similarity(root, pa, pb)
        if not math.isnan(corr):
            corrs.append(corr)
            mads.append(mad)

    return {
        "consecutive_pairs": len(distances),
        "distance_histogram": dict(buckets),
        "distance_median": median([float(d) for d in distances]),
        "distance_p90": quantile([float(d) for d in distances], 0.90),
        "distance_p95": quantile([float(d) for d in distances], 0.95),
        "distance_p99": quantile([float(d) for d in distances], 0.99),
        "fraction_within": {
            str(t): round(sum(1 for d in distances if d <= t) / len(distances), 4)
            if distances else None
            for t in (3, 4, 5, 6, 8, 10, 12, 16)
        },
        "per_country_median": {
            country: median([float(d) for d in values])
            for country, values in sorted(per_country.items())
        },
        "pixel_sample": {
            "pairs": len(corrs),
            "correlation_median": median(corrs),
            "correlation_p10": quantile(corrs, 0.10),
            "fraction_corr_above_0_90": round(
                sum(1 for c in corrs if c >= 0.90) / len(corrs), 4
            ) if corrs else None,
            "mad_median": median(mads),
        },
    }


# --------------------------------------------------------------------------- #
# Part C - split simulation on groups
# --------------------------------------------------------------------------- #
def split_simulation(
    per_image: dict[str, dict],
    pool: list[str],
    image_groups: list[list[str]],
    seed: int,
    sha_of: dict[str, str] | None = None,
    n_splits: int = 10,
) -> dict:
    from sklearn.model_selection import StratifiedGroupKFold

    sha_of = sha_of or {}
    pool_set = set(pool)
    group_of: dict[str, int] = {}
    groups: list[list[str]] = []
    for members in image_groups:
        kept = [m for m in members if m in pool_set]
        if kept:
            gid = len(groups)
            groups.append(sorted(kept))
            for member in kept:
                group_of[member] = gid
    for path in pool:
        if path not in group_of:
            group_of[path] = len(groups)
            groups.append([path])

    # rarest retained class per group -> stratification label
    def retained_codes(path: str) -> list[str]:
        return sorted(per_image[path].get("kept_by_code", {}))

    image_counts = collections.Counter()
    for path in pool:
        for code in retained_codes(path):
            image_counts[code] += 1

    labels: list[str] = []
    for members in groups:
        present: set[str] = set()
        for path in members:
            present.update(retained_codes(path))
        if not present:
            present = {"none"}
        rarest = min(present, key=lambda c: (image_counts.get(c, 0), c))
        labels.append(rarest)

    label_index = {label: i for i, label in enumerate(sorted(set(labels)))}
    y = np.array([label_index[label] for label in labels])
    group_ids = np.array([str(i) for i in range(len(groups))])

    splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    folds = [set(te) for _, te in splitter.split(np.zeros(len(groups)), y, group_ids)]
    assignment: dict[int, str] = {}
    for gid in range(len(groups)):
        if gid in folds[0]:
            assignment[gid] = "test"
        elif gid in folds[1]:
            assignment[gid] = "val"
        else:
            assignment[gid] = "train"

    result: dict[str, dict] = {}
    for split_name in ("train", "val", "test"):
        result[split_name] = {
            "groups": 0,
            "images": 0,
            "objects": 0,
            "class_images": collections.Counter(),
            "class_objects": collections.Counter(),
            "countries": collections.Counter(),
        }

    image_split: dict[str, str] = {}
    for gid, members in enumerate(groups):
        split_name = assignment[gid]
        bucket = result[split_name]
        bucket["groups"] += 1
        for path in members:
            info = per_image[path]
            bucket["images"] += 1
            bucket["objects"] += info["target_retained"]
            bucket["countries"][info["country"]] += 1
            image_split[path] = split_name
            for code, count in info.get("kept_by_code", {}).items():
                bucket["class_images"][code] += 1
                bucket["class_objects"][code] += count

    totals_images = sum(b["images"] for b in result.values())
    totals_objects = sum(b["objects"] for b in result.values())

    per_class_balance: dict[str, dict] = {}
    for code in TARGET_CODES:
        global_images = sum(result[s]["class_images"][code] for s in result)
        global_objects = sum(result[s]["class_objects"][code] for s in result)
        row = {}
        for split_name in ("train", "val", "test"):
            count = result[split_name]["class_images"][code]
            objs = result[split_name]["class_objects"][code]
            row[split_name] = {
                "images": count,
                "objects": objs,
                "share_of_split_pct": pct(count, result[split_name]["images"]),
                "global_share_pct": pct(global_images, totals_images),
                "deviation_pp": round(
                    pct(count, result[split_name]["images"]) - pct(global_images, totals_images), 2
                ),
                "object_share_of_class_pct": pct(objs, global_objects),
            }
        per_class_balance[code] = row

    # disjointness checks
    seen_group: dict[int, str] = {}
    group_violations = 0
    for path, split_name in image_split.items():
        gid = group_of[path]
        if seen_group.setdefault(gid, split_name) != split_name:
            group_violations += 1

    exact_hash_to_splits: dict[str, set[str]] = collections.defaultdict(set)
    for path, split_name in image_split.items():
        exact_hash_to_splits[sha_of.get(path, path)].add(split_name)

    return {
        "seed": seed,
        "n_splits": n_splits,
        "pool_images": len(pool),
        "pool_groups": len(groups),
        "group_size_distribution": dict(
            sorted(collections.Counter(len(g) for g in groups).items())
        ),
        "labels": dict(collections.Counter(labels)),
        "splits": {
            s: {
                "groups": result[s]["groups"],
                "images": result[s]["images"],
                "retained_objects": result[s]["objects"],
                "images_pct": pct(result[s]["images"], totals_images),
                "objects_pct": pct(result[s]["objects"], totals_objects),
                "class_images": dict(sorted(result[s]["class_images"].items())),
                "countries": dict(sorted(result[s]["countries"].items(), key=lambda kv: -kv[1])),
            }
            for s in ("train", "val", "test")
        },
        "per_class_balance": per_class_balance,
        "group_crossing_violations": group_violations,
        "exact_hash_crossing_violations": sum(
            1 for splits in exact_hash_to_splits.values() if len(splits) > 1
        ),
        "_image_split": image_split,
    }


# --------------------------------------------------------------------------- #
# Report assembly
# --------------------------------------------------------------------------- #
def cleanup_private(obj):
    if isinstance(obj, dict):
        return {
            str(k): cleanup_private(v)
            for k, v in obj.items()
            if not str(k).startswith("_")
        }
    if isinstance(obj, list):
        return [cleanup_private(v) for v in obj]
    return obj


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="S4-T3A dataset policy audit (read-only)")
    parser.add_argument("--raw", type=Path, default=RAW_DEFAULT)
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT)
    parser.add_argument("--countries", nargs="*", default=None)
    parser.add_argument("--refresh-hashes", action="store_true")
    parser.add_argument("--pixel-pairs", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    root: Path = args.raw.resolve()
    out_dir: Path = args.out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()

    print(f"root: {root}", flush=True)
    files = [p for p in root.rglob("*") if p.is_file()]
    image_paths = sorted(p for p in files if p.suffix.lower() in IMAGE_EXTS)
    xml_paths = sorted(p for p in files if p.suffix.lower() == ".xml")
    if args.countries:
        keep = {c.lower() for c in args.countries}
        image_paths = [p for p in image_paths if classify(p, root)[0].lower() in keep]
        xml_paths = [p for p in xml_paths if classify(p, root)[0].lower() in keep]
    print(f"images={len(image_paths)} xml={len(xml_paths)}", flush=True)

    # ---- Part B step 1: hashes (also yields true dimensions for Part A) ----
    print("\n[1/5] hashing images", flush=True)
    cache = build_hash_cache(root, image_paths, out_dir / "image_hash_cache.json", args.refresh_hashes)
    hash_check = verify_hash_implementation(root, cache)

    dims = {
        k: (v[2], v[3])
        for k, v in cache.items()
        if v[1] is not None and v[2] and v[3]
    }

    # ---- Part A ----
    print("\n[2/5] auditing annotations", flush=True)
    part_a = audit_annotations(root, xml_paths, image_paths, dims)
    paths = part_a.pop("_paths")
    per_image = part_a.pop("_per_image")

    # ---- Part B step 2: duplicates ----
    print("\n[3/5] duplicate analysis", flush=True)
    scope = {rel_key(p, root) for p in image_paths}
    hash_to_paths: dict[int, list[str]] = collections.defaultdict(list)
    sha_to_paths: dict[str, list[str]] = collections.defaultdict(list)
    for key in sorted(scope):
        entry = cache.get(key)
        if not entry:
            continue
        sha, dh = entry[0], entry[1]
        sha_to_paths[sha].append(key)
        if dh is not None:
            hash_to_paths[dh].append(key)

    exact_groups = [sorted(v) for v in sha_to_paths.values() if len(v) > 1]
    exact_groups.sort(key=lambda g: -len(g))
    unique_hashes = sorted(hash_to_paths)
    print(f"  unique sha256: {len(sha_to_paths)}  unique dhash: {len(unique_hashes)}", flush=True)

    edges, bucket_stats = enumerate_candidate_edges(unique_hashes, MAX_DISTANCE)
    print(f"  candidate pairs: {bucket_stats['pairs_within_max_distance']} "
          f"({bucket_stats['pairwise_comparisons']} comparisons)", flush=True)

    distance_histogram = collections.Counter(edges.values())
    identical_hash_pairs = sum(
        len(v) * (len(v) - 1) // 2 for v in hash_to_paths.values()
    )

    threshold_study: dict[str, dict] = {}
    group_cache: dict[int, list[list[int]]] = {}
    for threshold in range(0, MAX_DISTANCE + 1):
        groups = groups_at_threshold(unique_hashes, edges, threshold, hash_to_paths)
        group_cache[threshold] = groups
        threshold_study[str(threshold)] = {
            "groups": len(groups),
            "images_in_groups": sum(
                len(hash_to_paths[unique_hashes[idx]]) for members in groups for idx in members
            ),
            "largest_group": max(
                (sum(len(hash_to_paths[unique_hashes[i]]) for i in members)
                 for members in groups), default=0
            ),
            "pairs_at_distance_0_identical_hash": identical_hash_pairs,
            "pairs_with_hamming_1_to_threshold": sum(
                count for dist, count in distance_histogram.items() if 0 < dist <= threshold
            ),
        }

    final_groups = group_cache[FINAL_THRESHOLD]
    near = near_group_analysis(
        final_groups, unique_hashes, hash_to_paths, per_image, edges, FINAL_THRESHOLD
    )
    near_pathological = set(near.pop("_pathological_ids"))
    near_groups_paths = near.pop("_image_groups")

    # exact duplicate grouping across all images (already in near groups at d=0)
    exact_summary = []
    for group in exact_groups[:20]:
        exact_summary.append(
            {
                "size": len(group),
                "members": group[:8],
                "splits": sorted(
                    {per_image[p]["split"] if p in per_image else f"{p.split('/')[0]}/no_xml"
                     for p in group}
                ),
                "categories": dict(collections.Counter(
                    per_image[p]["category"] if p in per_image else "no_xml" for p in group
                )),
            }
        )

    print("  pixel verification of hash-distance samples", flush=True)
    pixel = verify_threshold_pairs(
        root, edges, unique_hashes, hash_to_paths, args.pixel_pairs, args.seed
    )
    print("  consecutive-frame hash distances", flush=True)
    sequential = sequential_pair_analysis(root, image_paths, cache, args.seed)

    # Uncertainty propagation into Part A policies:
    # an empty-XML image is contradicted when a near-duplicate of it carries
    # target boxes, or when the near-duplicate carries out-of-scope damage
    # (both mean "damage is visible but this frame says nothing").
    uncertain_set: set[str] = set()
    for group in near_groups_paths:
        empties = [p for p in group if per_image.get(p, {}).get("category") == "empty_xml"]
        if not empties:
            continue
        has_target = any(per_image.get(p, {}).get("target_objects", 0) > 0 for p in group)
        has_only_oos = any(
            per_image.get(p, {}).get("category") == "only_oos" for p in group
        )
        if has_target or has_only_oos:
            uncertain_set.update(empties)
    verified_empty = [p for p in paths["empty"] if p not in uncertain_set]

    # How often does an out-of-scope-only frame have a near-identical frame that
    # carries target boxes?  That is direct evidence the OOS frame's label is
    # incomplete rather than "this frame is clean".
    group_of_path: dict[str, int] = {}
    for gi, group in enumerate(near_groups_paths):
        for p in group:
            group_of_path[p] = gi
    only_oos_contradicted: list[str] = []
    for p in paths["only_oos"]:
        gi = group_of_path.get(p)
        if gi is None:
            continue
        if any(
            per_image.get(q, {}).get("target_objects", 0) > 0
            for q in near_groups_paths[gi]
        ):
            only_oos_contradicted.append(p)

    part_b = {
        "hash_parameters": {
            "exact_duplicate_hash": "sha256 over raw file bytes",
            "near_duplicate_hash": "64-bit dHash: grayscale, 9x8 INTER_AREA resize, "
                                   "bit = right pixel > left pixel, packbits big-endian",
            "candidate_generation": f"pigeonhole over {HASH_CHUNKS} x {CHUNK_BITS}-bit chunks "
                                    f"(exact for Hamming <= {HASH_CHUNKS - 1})",
            "grouping": "union-find transitive closure over unique hash values",
            "bucket_cap": "none; identical hashes collapsed before comparison",
            "implementation_check": hash_check,
        },
        "bucket_statistics": bucket_stats,
        "distance_histogram": dict(sorted(distance_histogram.items())),
        "threshold_study": threshold_study,
        "threshold_pixel_verification": pixel,
        "sequential_frame_analysis": sequential,
        "exact_duplicate_groups": len(exact_groups),
        "exact_duplicate_extra_files": sum(len(g) - 1 for g in exact_groups),
        "exact_duplicate_examples": exact_summary,
        "near_duplicates_at_threshold_3": {
            k: v
            for k, v in near.items()
            if k
            not in {
                "cross_split_groups",
                "cross_country_groups",
                "chained_groups",
                "label_inconsistent_groups",
            }
        },
        "near_cross_split_groups": near["cross_split_groups"],
        "near_cross_country_groups": near["cross_country_groups"],
        "chained_groups": near["chained_groups"][:20],
        "chained_group_count": near["chained_group_count"],
        "label_inconsistent_groups": near["label_inconsistent_groups"][:20],
        "label_inconsistent_group_count": near["label_inconsistent_group_count"],
        "s4t2_comparison": {
            "s4t2_near_groups": 635,
            "s4t2_images_in_groups": 2395,
            "s4t2_skipped_buckets": 3,
            "s4t2_skipped_images": 2077,
            "delta_groups": near["groups"] - 635,
            "delta_images": near["images_in_groups"] - 2395,
        },
        "uncertainty": {
            "empty_xml_images": len(paths["empty"]),
            "empty_xml_flagged_by_duplicate_evidence": len(uncertain_set & set(paths["empty"])),
            "verified_empty_xml_candidates": len(verified_empty),
            "only_oos_images": len(paths["only_oos"]),
            "only_oos_contradicted_by_near_duplicate_target_image": len(only_oos_contradicted),
        },
    }

    # ---- Part C ----
    print("\n[4/5] split simulation", flush=True)
    policy_pool = paths["pool_a"]
    sha_of = {key: entry[0] for key, entry in cache.items() if entry}
    split_a = split_simulation(
        per_image, policy_pool, near_groups_paths, args.seed, sha_of=sha_of
    )
    print("  policy C simulation (with verified negatives)", flush=True)
    policy_c_pool = paths["pool_a"] + verified_empty
    split_c = split_simulation(
        {
            **per_image,
            **{
                p: {
                    "country": p.split("/")[0],
                    "split": "train",
                    "category": "empty_xml",
                    "codes": [],
                    "objects": 0,
                    "target_objects": 0,
                    "target_retained": 0,
                    "oos_objects": 0,
                    "kept_by_code": {},
                }
                for p in verified_empty
            },
        },
        policy_c_pool,
        near_groups_paths,
        args.seed,
        sha_of=sha_of,
    )

    # policy variants: sizes only
    policy_sizes = {
        "policy_a_images": len(paths["pool_a"]),
        "policy_b_images": len(paths["pool_a"]) + len(paths["only_oos"]),
        "policy_c_images": len(paths["pool_a"]) + len(verified_empty),
        "empty_xml_total": len(paths["empty"]),
        "only_oos_total": len(paths["only_oos"]),
        "no_xml_total": len(paths["no_xml"]),
        "annotated_total": part_a["annotated_images"],
        "images_total": len(image_paths),
    }

    part_c = {
        "policy_pool_sizes": policy_sizes,
        "simulations": {
            "policy_a": split_a,
            "policy_c": split_c,
        },
        "frozen_validation_test_policy": {
            "written_once": False,
            "note": "audit only - no split files were created",
        },
    }

    summary = {
        "meta": {
            "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "root": str(root),
            "elapsed_s": round(time.perf_counter() - started, 1),
            "countries_filter": args.countries,
            "python": sys.version.split()[0],
            "cv2": cv2.__version__,
            "numpy": np.__version__,
        },
        "part_a": part_a,
        "part_b": part_b,
        "part_c": part_c,
    }

    payload = cleanup_private(summary)
    json_path = out_dir / "policy_audit.json"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    groups_path = out_dir / "duplicate_groups.json"
    groups_path.write_text(
        json.dumps(
            {
                "exact_groups": exact_groups,
                "near_groups_threshold_3": near_groups_paths,
                "near_groups_threshold_4": [
                    sorted(p for idx in members for p in hash_to_paths[unique_hashes[idx]])
                    for members in group_cache.get(4, [])
                ],
                "chained_group_ids": sorted(near_pathological),
            },
            indent=1,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(f"\nwritten: {json_path}")
    print(f"written: {groups_path}")
    print(f"total elapsed: {round(time.perf_counter() - started, 1)} s")

    # console digest
    print("\n=== PART A ===")
    for key in (
        "xml_files", "annotated_images", "images_without_xml", "objects_total",
        "target_objects", "target_objects_retained_after_rules", "target_objects_excluded",
        "oos_objects", "images_with_retained_target", "images_with_target_but_zero_retained",
    ):
        print(f"  {key}: {part_a[key]}")
    print(f"  image_categories: {part_a['image_categories']}")
    print("\n=== PART B ===")
    print(f"  exact groups: {part_b['exact_duplicate_groups']}")
    print(f"  near groups @3: {near['groups']} images={near['images_in_groups']} "
          f"largest={near['largest_group']}")
    print(f"  cross-split={near['cross_split_group_count']} "
          f"cross-country={near['cross_country_group_count']} "
          f"label-inconsistent={near['label_inconsistent_group_count']} "
          f"chained={near['chained_group_count']}")
    print(f"  threshold study: {json.dumps(part_b['threshold_study'], sort_keys=True)}")
    print("\n=== PART C ===")
    for policy_name, block in (("policy_a", split_a), ("policy_c", split_c)):
        print(f"  [{policy_name}] pool images={block['pool_images']} groups={block['pool_groups']}")
        for name, row in block["splits"].items():
            print(f"    {name}: images={row['images']} groups={row['groups']} "
                  f"objects={row['retained_objects']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
