"""RDD2022 dataset inspection for RoadVision AI (TDD v1.1 Section 4.2).

Read-only inventory of the extracted dataset. It does NOT convert annotations, does NOT
split the dataset and does NOT train anything.

What it reports
---------------
* image and annotation counts (overall, per country, per split);
* image formats and dimension statistics;
* annotation (XML) structure, class names and object counts;
* images without an annotation and annotations without an image;
* unreadable / corrupt images and malformed XML, with paths;
* duplicate file names;
* exact duplicate images (SHA-256) and near-duplicate images (64-bit dHash);
* the PRD v1.1 Table 7 fields that can be filled before conversion.

Outputs
-------
``<out>.json``  machine-readable summary
``<out>.md``    human-readable report

Usage
-----
    .\\.venv\\Scripts\\python.exe training\\inspect_dataset.py \
        --raw data\\raw\\RDD2022 --out data\\reports\\dataset_inspection

All input paths are resolved to absolute paths. No file in the dataset is modified.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import statistics
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
ROADVISION_CODES = ("D00", "D10", "D20", "D40")
DEFAULT_HASH_SIZE = 8
DEFAULT_HAMMING = 3
MAX_BUCKET = 500
MAX_LIST = 50
PROGRESS_EVERY = 5000

PairKey = tuple[str, str, str]  # (country, split, lower-case file stem)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def sha256_file(path: Path, chunk_size: int = 4 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def dhash(bgr: np.ndarray, hash_size: int = DEFAULT_HASH_SIZE) -> int:
    """64-bit difference hash: 8x8 gradient bits from a 9x8 grayscale resize."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (hash_size + 1, hash_size), interpolation=cv2.INTER_AREA)
    diff = resized[:, 1:] > resized[:, :-1]
    packed = np.packbits(diff.reshape(-1)).tobytes()
    return int.from_bytes(packed, "big")


class UnionFind:
    """Minimal disjoint-set structure over integer nodes with path compression."""

    def __init__(self) -> None:
        self.parent: dict[int, int] = {}

    def find(self, x: int) -> int:
        root = x
        while self.parent.get(root, root) != root:
            root = self.parent[root]
        while self.parent.get(x, x) != x:
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra

    def groups(self) -> list[list[int]]:
        out: dict[int, list[int]] = collections.defaultdict(list)
        for node in list(self.parent):
            out[self.find(node)].append(node)
        return [members for members in out.values() if len(members) > 1]


def classify(path: Path, root: Path) -> tuple[str, str]:
    """Return (country, split) from the dataset-relative path."""
    rel = path.relative_to(root).parts
    country = rel[0] if rel else "<unknown>"
    split = "<unknown>"
    for part in rel[1:-1]:
        lowered = part.lower()
        if lowered in {"train", "training"}:
            return country, "train"
        if lowered in {"test", "testing"}:
            return country, "test"
        if lowered in {"val", "valid", "validation"}:
            return country, "val"
    return country, split


def iter_files(root: Path):
    for path in root.rglob("*"):
        if path.is_file():
            yield path


def read_xml(xml_path: Path) -> dict:
    """Parse one Pascal VOC XML file and return its raw content."""
    root = ET.parse(xml_path).getroot()
    width = height = None
    size = root.find("size")
    if size is not None:
        try:
            width = int(float(size.findtext("width")))
            height = int(float(size.findtext("height")))
        except (TypeError, ValueError):
            width = height = None
    names = []
    for obj in root.findall("object"):
        names.append((obj.findtext("name") or "").strip())
    return {
        "root_tag": root.tag,
        "child_tags": [child.tag for child in root],
        "width": width,
        "height": height,
        "has_size": size is not None,
        "names": names,
    }


# --------------------------------------------------------------------------- #
# Inspection state
# --------------------------------------------------------------------------- #
@dataclass
class GroupStats:
    country: str
    split: str
    images: int = 0
    annotations: int = 0
    objects: int = 0
    classes: collections.Counter = field(default_factory=collections.Counter)


@dataclass
class Inspection:
    root: Path
    started: float = field(default_factory=time.perf_counter)
    groups: dict[tuple[str, str], GroupStats] = field(default_factory=dict)

    images: int = 0
    annotations: int = 0
    objects: int = 0
    images_with_annotation: int = 0
    images_without_annotation: int = 0
    annotations_without_image: int = 0

    unreadable_images: list[dict] = field(default_factory=list)
    malformed_xml: list[dict] = field(default_factory=list)
    missing_annotation: list[str] = field(default_factory=list)
    missing_image: list[str] = field(default_factory=list)

    class_counts: collections.Counter = field(default_factory=collections.Counter)
    class_image_counts: collections.Counter = field(default_factory=collections.Counter)
    class_countries: dict[str, set] = field(default_factory=dict)

    xml_root_tags: collections.Counter = field(default_factory=collections.Counter)
    xml_child_tags: collections.Counter = field(default_factory=collections.Counter)
    xml_size_missing: int = 0
    xml_size_unparsable: int = 0
    xml_size_mismatch: int = 0
    xml_objects_without_name: int = 0
    xml_images_without_objects: int = 0

    widths: list[int] = field(default_factory=list)
    heights: list[int] = field(default_factory=list)
    dimension_pairs: collections.Counter = field(default_factory=collections.Counter)
    extensions: collections.Counter = field(default_factory=collections.Counter)
    total_image_bytes: int = 0
    total_xml_bytes: int = 0

    names: collections.Counter = field(default_factory=collections.Counter)
    hashes: dict[str, list[str]] = field(default_factory=dict)
    dh_entries: list[tuple[int, str]] = field(default_factory=list)

    near_groups: list[list[str]] = field(default_factory=list)
    near_edges: int = 0
    near_skipped_buckets: int = 0
    near_skipped_images: int = 0


# --------------------------------------------------------------------------- #
# Inspection pipeline
# --------------------------------------------------------------------------- #
def inspect_annotations(inspection: Inspection, xml_paths: list[Path]) -> dict[PairKey, dict]:
    """Parse every XML once; return pairing metadata keyed by (country, split, stem)."""
    root = inspection.root
    parsed: dict[PairKey, dict] = {}

    for idx, xml_path in enumerate(xml_paths, 1):
        country, split = classify(xml_path, root)
        stat = inspection.groups.setdefault(f"{country}/{split}", GroupStats(country, split))
        inspection.total_xml_bytes += xml_path.stat().st_size

        try:
            data = read_xml(xml_path)
        except ET.ParseError as exc:
            inspection.malformed_xml.append({"path": str(xml_path), "error": str(exc)})
            continue

        inspection.annotations += 1
        stat.annotations += 1
        inspection.xml_root_tags[data["root_tag"]] += 1
        if len(inspection.xml_root_tags) <= 3:
            for tag in data["child_tags"]:
                inspection.xml_child_tags[tag] += 1

        if not data["has_size"]:
            inspection.xml_size_missing += 1
        elif data["width"] is None or data["height"] is None:
            inspection.xml_size_unparsable += 1

        if not data["names"]:
            inspection.xml_images_without_objects += 1

        seen_codes: set[str] = set()
        for name in data["names"]:
            if not name:
                inspection.xml_objects_without_name += 1
                continue
            inspection.class_counts[name] += 1
            inspection.objects += 1
            stat.objects += 1
            stat.classes[name] += 1
            inspection.class_countries.setdefault(name, set()).add(country)
            seen_codes.add(name)
        for code in seen_codes:
            inspection.class_image_counts[code] += 1

        parsed[(country, split, xml_path.stem.lower())] = {
            "path": str(xml_path),
            "width": data["width"],
            "height": data["height"],
        }

        if idx % PROGRESS_EVERY == 0:
            print(f"  xml parsed: {idx}/{len(xml_paths)}", flush=True)

    return parsed


def inspect_images(
    inspection: Inspection,
    image_paths: list[Path],
    xml_meta: dict[PairKey, dict],
    hamming: int,
    max_bucket: int,
    skip_near_duplicates: bool,
) -> None:
    root = inspection.root
    image_keys: set[PairKey] = set()

    for idx, image_path in enumerate(image_paths, 1):
        country, split = classify(image_path, root)
        key = (country, split, image_path.stem.lower())
        image_keys.add(key)

        stat = inspection.groups.setdefault(f"{country}/{split}", GroupStats(country, split))
        inspection.images += 1
        stat.images += 1
        inspection.names[image_path.name] += 1
        inspection.total_image_bytes += image_path.stat().st_size
        inspection.extensions[image_path.suffix.lower()] += 1

        meta = xml_meta.get(key)
        if meta is None:
            inspection.images_without_annotation += 1
            if len(inspection.missing_annotation) < MAX_LIST:
                inspection.missing_annotation.append(str(image_path))
        else:
            inspection.images_with_annotation += 1

        image = cv2.imread(str(image_path))
        if image is None:
            if len(inspection.unreadable_images) < MAX_LIST:
                inspection.unreadable_images.append({"path": str(image_path)})
            inspection.unreadable_count = getattr(inspection, "unreadable_count", 0) + 1
            continue

        height, width = image.shape[:2]
        inspection.widths.append(width)
        inspection.heights.append(height)
        inspection.dimension_pairs[f"{width}x{height}"] += 1

        if meta is not None and meta["width"] is not None and meta["height"] is not None:
            if (meta["width"], meta["height"]) != (width, height):
                inspection.xml_size_mismatch += 1

        digest = sha256_file(image_path)
        inspection.hashes.setdefault(digest, []).append(str(image_path))

        if not skip_near_duplicates:
            inspection.dh_entries.append((dhash(image), str(image_path)))

        if idx % PROGRESS_EVERY == 0:
            print(f"  images processed: {idx}/{len(image_paths)}", flush=True)

    # annotations with no matching image
    for key, meta in xml_meta.items():
        if key not in image_keys:
            inspection.annotations_without_image += 1
            if len(inspection.missing_image) < MAX_LIST:
                inspection.missing_image.append(meta["path"])


def find_near_duplicates(inspection: Inspection, hamming: int, max_bucket: int) -> None:
    """Pigeonhole bucketing over 4 x 16-bit chunks; Hamming <= threshold union-find."""
    entries = inspection.dh_entries
    if not entries:
        return
    hashes = [h for h, _ in entries]
    paths = [p for _, p in entries]
    nodes = range(len(entries))
    dsu = UnionFind()
    for node in nodes:
        dsu.parent[node] = node

    for chunk in range(4):
        buckets: dict[int, list[int]] = collections.defaultdict(list)
        for node in nodes:
            buckets[(hashes[node] >> (chunk * 16)) & 0xFFFF].append(node)
        for bucket in buckets.values():
            if len(bucket) < 2:
                continue
            if len(bucket) > max_bucket:
                inspection.near_skipped_buckets += 1
                inspection.near_skipped_images += len(bucket)
                continue
            for i in range(len(bucket)):
                for j in range(i + 1, len(bucket)):
                    if (hashes[bucket[i]] ^ hashes[bucket[j]]).bit_count() <= hamming:
                        dsu.union(bucket[i], bucket[j])
                        inspection.near_edges += 1

    inspection.near_groups = [[paths[n] for n in members] for members in dsu.groups()]


def run_inspection(
    root: Path,
    hamming: int,
    max_bucket: int,
    skip_near_duplicates: bool,
) -> Inspection:
    inspection = Inspection(root=root)

    files = list(iter_files(root))
    image_paths = sorted(p for p in files if p.suffix.lower() in IMAGE_EXTS)
    xml_paths = sorted(p for p in files if p.suffix.lower() == ".xml")
    print(f"files={len(files)} images={len(image_paths)} xml={len(xml_paths)}", flush=True)

    t0 = time.perf_counter()
    xml_meta = inspect_annotations(inspection, xml_paths)
    print(f"annotation stage {time.perf_counter() - t0:.1f}s", flush=True)

    t0 = time.perf_counter()
    inspect_images(
        inspection, image_paths, xml_meta, hamming, max_bucket, skip_near_duplicates
    )
    print(f"image stage {time.perf_counter() - t0:.1f}s", flush=True)

    if not skip_near_duplicates:
        t0 = time.perf_counter()
        find_near_duplicates(inspection, hamming, max_bucket)
        print(f"near-duplicate stage {time.perf_counter() - t0:.1f}s", flush=True)

    return inspection


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #
def build_summary(inspection: Inspection, args: argparse.Namespace) -> dict:
    def stats(values: list[int]) -> dict:
        if not values:
            return {}
        return {
            "min": min(values),
            "max": max(values),
            "mean": round(statistics.fmean(values), 1),
            "median": statistics.median(values),
        }

    exact_groups = {h: paths for h, paths in inspection.hashes.items() if len(paths) > 1}
    exact_extra = sum(len(paths) - 1 for paths in exact_groups.values())
    near_sizes = sorted((len(g) for g in inspection.near_groups), reverse=True)
    duplicate_names = {n: c for n, c in inspection.names.items() if c > 1}

    groups = []
    for stat in sorted(inspection.groups.values(), key=lambda s: (s.country, s.split)):
        groups.append(
            {
                "country": stat.country,
                "split": stat.split,
                "images": stat.images,
                "annotations": stat.annotations,
                "objects": stat.objects,
                "classes": dict(sorted(stat.classes.items())),
            }
        )

    return {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "root": str(inspection.root),
        "parameters": {
            "dhash_bits": DEFAULT_HASH_SIZE * DEFAULT_HASH_SIZE,
            "hamming_threshold": args.hamming,
            "max_bucket": args.max_bucket,
            "near_duplicates_skipped": bool(args.skip_near_duplicates),
        },
        "elapsed_s": round(time.perf_counter() - inspection.started, 1),
        "totals": {
            "images": inspection.images,
            "annotations_parsed": inspection.annotations,
            "annotations_found": inspection.annotations + len(inspection.malformed_xml),
            "objects": inspection.objects,
            "images_with_annotation": inspection.images_with_annotation,
            "images_without_annotation": inspection.images_without_annotation,
            "annotations_without_image": inspection.annotations_without_image,
            "unreadable_images": getattr(inspection, "unreadable_count", 0),
            "malformed_xml": len(inspection.malformed_xml),
            "images_without_objects": inspection.xml_images_without_objects,
            "objects_without_name": inspection.xml_objects_without_name,
            "xml_size_missing": inspection.xml_size_missing,
            "xml_size_unparsable": inspection.xml_size_unparsable,
            "xml_size_mismatch": inspection.xml_size_mismatch,
            "total_image_bytes": inspection.total_image_bytes,
            "total_xml_bytes": inspection.total_xml_bytes,
            "total_bytes": inspection.total_image_bytes + inspection.total_xml_bytes,
        },
        "groups": groups,
        "classes": {
            code: {
                "objects": count,
                "images": inspection.class_image_counts.get(code, 0),
                "countries": sorted(inspection.class_countries.get(code, [])),
                "in_roadvision_scope": code in ROADVISION_CODES,
            }
            for code, count in sorted(inspection.class_counts.items())
        },
        "class_codes_outside_scope": sorted(
            {c for c in inspection.class_counts if c not in ROADVISION_CODES}
        ),
        "xml_structure": {
            "root_tags": dict(inspection.xml_root_tags),
            "child_tags_sample": dict(inspection.xml_child_tags),
        },
        "images": {
            "extensions": dict(inspection.extensions),
            "width": stats(inspection.widths),
            "height": stats(inspection.heights),
            "top_dimensions": inspection.dimension_pairs.most_common(10),
        },
        "duplicates": {
            "exact_hash_groups": len(exact_groups),
            "exact_duplicate_extra_files": exact_extra,
            "exact_examples": [
                paths[:3] for paths in sorted(exact_groups.values(), key=len, reverse=True)[:5]
            ],
            "near_duplicate_groups": len(inspection.near_groups),
            "near_duplicate_images_in_groups": sum(near_sizes),
            "near_duplicate_pair_edges": inspection.near_edges,
            "near_largest_group": near_sizes[0] if near_sizes else 0,
            "near_skipped_buckets": inspection.near_skipped_buckets,
            "near_skipped_images": inspection.near_skipped_images,
            "near_examples": sorted(inspection.near_groups, key=len, reverse=True)[:5],
            "duplicate_filenames": len(duplicate_names),
            "duplicate_filename_examples": dict(list(duplicate_names.items())[:10]),
        },
        "problems": {
            "unreadable_images": inspection.unreadable_images,
            "malformed_xml": inspection.malformed_xml,
            "images_without_annotation": inspection.missing_annotation,
            "annotations_without_image": inspection.missing_image,
            "lists_truncated_at": MAX_LIST,
        },
    }


def render_markdown(summary: dict) -> str:
    t = summary["totals"]
    lines: list[str] = []
    add = lines.append

    add("# RDD2022 dataset inspection")
    add("")
    add(f"Generated: {summary['generated_utc']}  ")
    add(f"Root: `{summary['root']}`  ")
    add(f"Elapsed: {summary['elapsed_s']} s  ")
    add(
        f"Near-duplicate settings: dHash {summary['parameters']['dhash_bits']} bits, "
        f"Hamming <= {summary['parameters']['hamming_threshold']}, "
        f"max bucket {summary['parameters']['max_bucket']}"
    )
    add("")
    add("## Totals")
    add("")
    add("| Metric | Value |")
    add("| :--- | ---: |")
    for key, value in t.items():
        add(f"| {key} | {value:,} |" if isinstance(value, int) else f"| {key} | {value} |")
    add("")

    add("## Images and annotations per country and split")
    add("")
    add("| Country | Split | Images | Annotations | Objects | Classes |")
    add("| :--- | :--- | ---: | ---: | ---: | :--- |")
    for group in summary["groups"]:
        classes = ", ".join(f"{k}={v}" for k, v in group["classes"].items()) or "-"
        add(
            f"| {group['country']} | {group['split']} | {group['images']:,} | "
            f"{group['annotations']:,} | {group['objects']:,} | {classes} |"
        )
    add("")

    add("## Class distribution")
    add("")
    add("| Code | Objects | Images | Countries | In scope |")
    add("| :--- | ---: | ---: | :--- | :--- |")
    for code, info in summary["classes"].items():
        add(
            f"| {code} | {info['objects']:,} | {info['images']:,} | "
            f"{', '.join(info['countries']) or '-'} | {info['in_roadvision_scope']} |"
        )
    add("")
    if summary["class_codes_outside_scope"]:
        add(f"Codes outside the RoadVision four: {', '.join(summary['class_codes_outside_scope'])}")
        add("")

    add("## Image properties")
    add("")
    add("| Property | Value |")
    add("| :--- | :--- |")
    add(f"| Extensions | {summary['images']['extensions']} |")
    add(f"| Width min/max/mean/median | {summary['images']['width']} |")
    add(f"| Height min/max/mean/median | {summary['images']['height']} |")
    add(f"| Top dimensions | {summary['images']['top_dimensions']} |")
    add("")

    add("## XML structure")
    add("")
    add(f"Root tags: `{summary['xml_structure']['root_tags']}`  ")
    add(f"First-sample child tags: `{summary['xml_structure']['child_tags_sample']}`")
    add("")

    add("## Duplicates")
    add("")
    d = summary["duplicates"]
    add("| Check | Result |")
    add("| :--- | ---: |")
    add(f"| Exact duplicate groups (SHA-256) | {d['exact_hash_groups']:,} |")
    add(f"| Extra copies beyond the first | {d['exact_duplicate_extra_files']:,} |")
    add(f"| Near-duplicate groups (dHash) | {d['near_duplicate_groups']:,} |")
    add(f"| Images in near-duplicate groups | {d['near_duplicate_images_in_groups']:,} |")
    add(f"| Near-duplicate pair edges | {d['near_duplicate_pair_edges']:,} |")
    add(f"| Largest near-duplicate group | {d['near_largest_group']:,} |")
    add(f"| Skipped buckets (too large) | {d['near_skipped_buckets']:,} |")
    add(f"| Images in skipped buckets | {d['near_skipped_images']:,} |")
    add(f"| Duplicate file names | {d['duplicate_filenames']:,} |")
    add("")

    add("## Problems")
    add("")
    p = summary["problems"]
    add(f"- Unreadable images: **{t['unreadable_images']:,}**")
    add(f"- Malformed XML: **{t['malformed_xml']:,}**")
    add(f"- Images without annotation: **{t['images_without_annotation']:,}**")
    add(f"- Annotations without image: **{t['annotations_without_image']:,}**")
    add(f"- XML images with zero objects: **{t['images_without_objects']:,}**")
    add(f"- Objects without a class name: **{t['objects_without_name']:,}**")
    add(f"- XML size element missing: **{t['xml_size_missing']:,}**")
    add(f"- XML size unparsable: **{t['xml_size_unparsable']:,}**")
    add(f"- XML size vs real image mismatch: **{t['xml_size_mismatch']:,}**")
    add("")
    if p["unreadable_images"]:
        add("### Unreadable image paths (first entries)")
        add("")
        for entry in p["unreadable_images"]:
            add(f"- `{entry['path']}`")
        add("")
    if p["malformed_xml"]:
        add("### Malformed XML (first entries)")
        add("")
        for entry in p["malformed_xml"]:
            add(f"- `{entry['path']}` - {entry['error']}")
        add("")
    if p["images_without_annotation"]:
        add("### Images without annotation (first entries)")
        add("")
        for path in p["images_without_annotation"]:
            add(f"- `{path}`")
        add("")

    add("## PRD v1.1 Table 7 fields available at this stage")
    add("")
    add("| Field | Value from this inspection |")
    add("| :--- | :--- |")
    add(f"| Images downloaded | {t['images']:,} |")
    add(f"| Images with an annotation file | {t['images_with_annotation']:,} |")
    add(f"| Objects across all annotations | {t['objects']:,} |")
    add("| Exclusions and reasons | not applicable yet: nothing was converted or excluded |")
    add("| Training / validation / test counts | not applicable yet: no split was created |")
    add("| Class distribution per split | not applicable yet: no split was created |")
    add("| Subset size and selection | not applicable yet: no training |")
    add("| Random seed and split file | not applicable yet |")
    add("| Leakage check | exact + dHash duplicate counts reported above; split-level check deferred |")
    add("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect the extracted RDD2022 dataset.")
    parser.add_argument("--raw", required=True, help="extracted dataset root")
    parser.add_argument("--out", required=True, help="output prefix, without extension")
    parser.add_argument("--hamming", type=int, default=DEFAULT_HAMMING, help="dHash Hamming threshold")
    parser.add_argument(
        "--max-bucket", type=int, default=MAX_BUCKET, help="skip dHash buckets larger than this"
    )
    parser.add_argument(
        "--skip-near-duplicates",
        action="store_true",
        help="skip the dHash pass (exact SHA-256 duplicates are still computed)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(args.raw).resolve()
    out = Path(args.out).resolve()

    if not root.is_dir():
        print(f"ERROR: dataset root does not exist: {root}", file=sys.stderr)
        return 2

    print(f"root: {root}")
    print(f"out : {out}.json / {out}.md")

    inspection = run_inspection(
        root,
        hamming=args.hamming,
        max_bucket=args.max_bucket,
        skip_near_duplicates=args.skip_near_duplicates,
    )
    summary = build_summary(inspection, args)

    out.parent.mkdir(parents=True, exist_ok=True)
    json_path = out.with_suffix(".json")
    md_path = out.with_suffix(".md")
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_markdown(summary), encoding="utf-8")

    print()
    print(f"images            : {inspection.images:,}")
    print(f"annotations       : {inspection.annotations:,}")
    print(f"objects           : {inspection.objects:,}")
    print(f"images w/o annot. : {inspection.images_without_annotation:,}")
    print(f"unreadable images : {getattr(inspection, 'unreadable_count', 0):,}")
    print(f"malformed xml     : {len(inspection.malformed_xml):,}")
    print(f"classes           : {dict(sorted(inspection.class_counts.items()))}")
    print(f"wrote             : {json_path}")
    print(f"wrote             : {md_path}")
    print("INSPECTION COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
