#!/usr/bin/env python3
"""Build the RoadVision AI YOLO dataset (S4-T3B).

Pipeline
--------
1. Read the immutable RDD2022 tree and the S4-T3A audit artifacts.
2. Parse every Pascal VOC XML with ``convert_annotations.parse_voc`` and
   reconcile the counts against ``policy_audit.json`` (abort on any mismatch).
3. Apply the approved filtering policy.  The requested Q-03 policy is C, but
   Policy C is gated on the V2 visual-inspection sign-off.  Without that
   sign-off the documented Policy A fallback is used and the reason is recorded
   in every report.  No out-of-scope class is ever relabelled.
4. Split duplicate groups (Hamming <= 3, no bucket cap) with
   ``StratifiedGroupKFold`` at seed 42; ``folds[0]`` is test.
5. Copy images and write YOLO labels, ``data.yaml``, manifests and reports.

Outputs (all deterministic; no timestamps in the split manifest)::

    dataset/
      images/{train,val,test}/
      labels/{train,val,test}/
      data.yaml
      manifests/split_manifest.csv
      manifests/split_manifest.json
      manifests/{train,val,test}.txt
      reports/conversion_summary.json
      reports/class_distribution.json
      reports/exclusion_report.json
      reports/duplicate_leakage.json
      reports/policy_decision.json
      reports/source_integrity.json
      reports/per_image_index.json
      reports/dataset_report.json

Usage::

    .\\.venv\\Scripts\\python.exe training\\prepare_dataset.py --force

    # Policy C is only permitted with an explicit V2 gate sign-off:
    .\\.venv\\Scripts\\python.exe training\\prepare_dataset.py --policy C ^
        --v2-signoff data\\reports\\audit\\v2_gate_signoff.json --force
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import os
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from convert_annotations import (
    CODE_TO_ID,
    CLASSES_DEFAULT,
    KNOWN_CODES,
    PROJECT_ROOT,
    RAW_DEFAULT,
    TARGET_CODES,
    build_image_index,
    classify_path,
    iter_dataset_files,
    label_text,
    load_classes,
    parse_voc,
)

DEFAULT_OUT = PROJECT_ROOT / "dataset"
DEFAULT_AUDIT = PROJECT_ROOT / "data" / "reports" / "audit"
DEFAULT_DUPLICATES = DEFAULT_AUDIT / "duplicate_groups.json"
DEFAULT_HASH_CACHE = DEFAULT_AUDIT / "image_hash_cache.json"
DEFAULT_POLICY_AUDIT = DEFAULT_AUDIT / "policy_audit.json"

SPLIT_ORDER = ("train", "val", "test")
SPLIT_RANK = {split: index for index, split in enumerate(SPLIT_ORDER)}


class PipelineError(RuntimeError):
    """Raised when the dataset cannot be built safely."""


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path, chunk: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash_xml_tree(
    xml_paths: list[Path], raw_root: Path, workers: int = 16
) -> tuple[str, int, int]:
    """Return ``(tree_sha256, total_bytes, file_count)`` for the XML tree.

    The digest is SHA-256 over sorted ``'<relative-path>\\t<sha256>\\n'`` lines.
    Hashing is parallelised because tens of thousands of small files are
    open/close-bound on Windows.
    """

    def hash_one(path: Path) -> tuple[str, str, int]:
        data = path.read_bytes()
        return (
            path.relative_to(raw_root).as_posix(),
            hashlib.sha256(data).hexdigest(),
            len(data),
        )

    with ThreadPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(hash_one, xml_paths))
    results.sort(key=lambda item: item[0])
    lines = "".join(f"{rel}\t{digest}\n" for rel, digest, _ in results)
    total_bytes = sum(size for _, _, size in results)
    return sha256_text(lines), total_bytes, len(results)


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
    path.write_text(text + "\n", encoding="utf-8", newline="\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def load_json(path: Path):
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def image_size_from_file(path: Path) -> tuple[int, int]:
    try:
        from PIL import Image

        with Image.open(path) as image:
            width, height = image.size
        return int(width), int(height)
    except Exception:  # noqa: BLE001 - fall back to OpenCV
        import cv2

        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is None:
            raise PipelineError(f"cannot read image: {path}")
        height, width = image.shape[:2]
        return int(width), int(height)


def clean_managed_output(out: Path, force: bool, keep_images: bool = False) -> None:
    managed = (
        ("manifests", "reports", "data.yaml")
        if keep_images
        else ("images", "labels", "manifests", "reports", "data.yaml")
    )
    existing = [out / name for name in managed if (out / name).exists()]
    if existing and not force:
        raise PipelineError(
            f"{out} already contains generated dataset files; pass --force to regenerate"
        )
    for path in existing:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    for sub in ("images", "labels", "manifests", "reports"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    for split in SPLIT_ORDER:
        (out / "images" / split).mkdir(parents=True, exist_ok=True)
        (out / "labels" / split).mkdir(parents=True, exist_ok=True)


def copy_image(src: Path, dst: Path, mode: str) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if mode == "hardlink":
        try:
            os.link(src, dst)
            return
        except OSError:
            pass  # cross-volume or filesystem limitation -> copy below
    shutil.copy2(src, dst)


# --------------------------------------------------------------------------- #
# Reconciliation
# --------------------------------------------------------------------------- #
def reconcile_audit(
    audit: dict,
    counts: dict,
    split_result,
    policy: str,
) -> dict:
    """Compare the conversion and split against the S4-T3A audit."""
    part_a = audit["part_a"]
    part_c = audit["part_c"]
    mismatches: list[dict] = []

    def expect(name: str, actual, expected) -> None:
        if actual != expected:
            mismatches.append({"item": name, "actual": actual, "expected": expected})

    expect("part_a.xml_files", counts["xml_files"], part_a["xml_files"])
    expect("part_a.annotated_images", counts["annotated_images"], part_a["annotated_images"])
    expect("part_a.images_without_xml", counts["images_without_xml"], part_a["images_without_xml"])
    expect("part_a.objects_total", counts["objects_total"], part_a["objects_total"])
    for category, value in part_a["image_categories"].items():
        if category == "check_sum_equals_annotated":
            continue
        expect(f"part_a.image_categories.{category}", counts["categories"].get(category, 0), value)
    expect("part_a.target_objects", counts["target_objects"], part_a["target_objects"])
    expect(
        "part_a.target_objects_retained_after_rules",
        counts["target_retained"],
        part_a["target_objects_retained_after_rules"],
    )
    expect("part_a.oos_objects", counts["oos_objects"], part_a["oos_objects"])
    expect(
        "part_a.objects_without_name",
        counts["missing_name_objects"],
        part_a["objects_without_name"],
    )
    expect(
        "part_a.unknown_codes_not_in_known_set",
        counts["unknown_codes"],
        part_a["unknown_codes_not_in_known_set"],
    )
    expect(
        "part_a.target_boxes_clipped",
        counts["target_boxes_clipped"],
        part_a["target_boxes_clipped"],
    )
    expect(
        "part_a.oos_boxes_clipped",
        counts["oos_boxes_clipped"],
        part_a["oos_boxes_clipped"],
    )
    for reason, value in part_a["target_exclusion_reasons"].items():
        expect(
            f"part_a.target_exclusion_reasons.{reason}",
            counts["target_exclusion_reasons"].get(reason, 0),
            value,
        )
    for reason in counts["target_exclusion_reasons"]:
        if reason not in part_a["target_exclusion_reasons"]:
            expect(f"part_a.target_exclusion_reasons.{reason}", counts["target_exclusion_reasons"][reason], 0)
    expect(
        "part_a.oos_exclusion_reasons",
        counts["oos_geometry_reasons"],
        part_a["oos_exclusion_reasons"],
    )
    expect(
        "part_a.images_with_retained_target",
        counts["images_with_retained_target"],
        part_a["images_with_retained_target"],
    )
    expect(
        "part_a.images_with_target_but_zero_retained",
        counts["images_with_target_but_zero_retained"],
        part_a["images_with_target_but_zero_retained"],
    )
    expect(
        "part_a.xml_size_mismatch",
        counts["xml_size_mismatch"],
        part_a["xml_size_mismatch"],
    )
    expect(
        "part_b.near_duplicate_groups",
        counts["near_groups"],
        audit["part_b"]["near_duplicates_at_threshold_3"]["groups"],
    )
    expect(
        "part_b.verified_empty_candidates",
        counts["verified_empty_candidates"],
        audit["part_b"]["uncertainty"]["verified_empty_xml_candidates"],
    )

    simulation = part_c["simulations"]["policy_a" if policy == "A" else "policy_c"]
    expect("split.pool_images", split_result.stats["pool_images"], simulation["pool_images"])
    expect("split.pool_groups", split_result.stats["pool_groups"], simulation["pool_groups"])
    for split in SPLIT_ORDER:
        actual = split_result.stats["splits"][split]
        expected = simulation["splits"][split]
        expect(f"split.{split}.groups", actual["groups"], expected["groups"])
        expect(f"split.{split}.images", actual["images"], expected["images"])
        expect(
            f"split.{split}.retained_objects",
            actual["retained_objects"],
            expected["retained_objects"],
        )
        expect(
            f"split.{split}.class_images",
            actual["class_images"],
            expected["class_images"],
        )

    return {
        "checked": True,
        "status": "PASS" if not mismatches else "FAIL",
        "policy": policy,
        "mismatches": mismatches,
        "audit_report": str(DEFAULT_POLICY_AUDIT),
    }


# --------------------------------------------------------------------------- #
# Main pipeline
# --------------------------------------------------------------------------- #
def run(args: argparse.Namespace) -> int:
    started = utc_now()
    started_perf = time.perf_counter()

    classes = load_classes(args.classes)
    class_names = list(classes["names"])
    if class_names != list(TARGET_CODES):
        raise PipelineError(f"class names {class_names} != TDD mapping {list(TARGET_CODES)}")

    audit = load_json(args.policy_audit)
    duplicates = load_json(args.duplicate_groups)
    near_groups = duplicates["near_groups_threshold_3"]
    exact_groups = duplicates.get("exact_groups", [])

    cache_doc = load_json(args.hash_cache)
    cache = cache_doc.get("entries", cache_doc)
    image_dimensions = {
        key: (int(value[2]), int(value[3]))
        for key, value in cache.items()
        if value and value[2] and value[3]
    }
    sha_of = {key: value[0] for key, value in cache.items() if value and value[0]}

    raw_root = args.raw_root.resolve()
    if not raw_root.is_dir():
        raise PipelineError(f"raw dataset root does not exist: {raw_root}")

    print(f"[1/5] enumerating {raw_root}", flush=True)
    image_paths, xml_paths = iter_dataset_files(raw_root)
    image_index = build_image_index(image_paths, raw_root)
    print(f"      images={len(image_paths)} xmls={len(xml_paths)}", flush=True)

    # ---- Parse every annotation ------------------------------------------- #
    print("[2/5] parsing annotations", flush=True)
    per_image: dict[str, dict] = {}
    category_counts: collections.Counter = collections.Counter()
    country_stats: dict[str, dict] = collections.defaultdict(
        lambda: collections.Counter()
    )
    class_objects: collections.Counter = collections.Counter()
    class_images: collections.Counter = collections.Counter()
    target_exclusion_reasons: collections.Counter = collections.Counter()
    oos_geometry_reasons: collections.Counter = collections.Counter()
    missing_name_objects = 0
    unknown_codes: collections.Counter = collections.Counter()
    clipped_objects = 0
    target_clipped = 0
    oos_clipped = 0
    xml_size_mismatch = 0
    xml_without_image: list[str] = []
    parse_errors: list[dict] = []
    objects_total = 0
    target_objects = 0
    target_retained = 0
    oos_objects = 0
    pool_a_paths: list[str] = []
    empty_paths: list[str] = []
    only_oos_paths: list[str] = []
    mapping_zero_paths: list[str] = []

    for index, xml_path in enumerate(xml_paths, 1):
        country, official_split = classify_path(xml_path, raw_root)
        xml_rel = xml_path.relative_to(raw_root).as_posix()
        source_rel = image_index.get((country, official_split, xml_path.stem.lower()))
        if source_rel is None:
            xml_without_image.append(xml_rel)
            continue

        image_size = image_dimensions.get(source_rel)
        if image_size is None:
            image_size = image_size_from_file(raw_root / source_rel)

        try:
            parsed = parse_voc(xml_path, image_size=image_size)
        except Exception as exc:  # noqa: BLE001 - record and reject the image
            parse_errors.append({"xml": xml_rel, "error": str(exc)})
            continue

        lines = label_text(parsed).splitlines()
        for item in parsed.exclusions:
            if item.get("is_target"):
                if item["reason"] != "out_of_scope_class":
                    target_exclusion_reasons[item["reason"]] += 1
            else:
                if item["reason"] != "out_of_scope_class":
                    oos_geometry_reasons[item["reason"]] += 1
            if item["reason"] == "missing_name":
                missing_name_objects += 1
        for code in parsed.codes:
            if code not in KNOWN_CODES:
                unknown_codes[code] += 1

        objects_total += parsed.objects_total
        target_objects += parsed.target_objects
        target_retained += parsed.target_retained
        oos_objects += parsed.oos_objects
        clipped_objects += parsed.clipped_objects
        parsed_target_clipped = sum(1 for box in parsed.kept_boxes if box.clipped)
        target_clipped += parsed_target_clipped
        oos_clipped += parsed.clipped_objects - parsed_target_clipped
        if parsed.warnings:
            xml_size_mismatch += 1
        category_counts[parsed.category] += 1
        country_stats[country]["images_total"] += 1
        country_stats[country]["objects_total"] += parsed.objects_total
        country_stats[country]["target_objects"] += parsed.target_objects
        country_stats[country]["target_retained"] += parsed.target_retained
        country_stats[country]["oos_objects"] += parsed.oos_objects
        country_stats[country][f"category_{parsed.category}"] += 1
        for code, count in parsed.kept_by_code.items():
            class_objects[code] += count

        per_image[source_rel] = {
            "source_rel": source_rel,
            "country": country,
            "official_split": official_split,
            "xml_rel": xml_rel,
            "category": parsed.category,
            "codes": list(parsed.codes),
            "objects_total": parsed.objects_total,
            "target_objects": parsed.target_objects,
            "target_retained": parsed.target_retained,
            "oos_objects": parsed.oos_objects,
            "kept_by_code": dict(parsed.kept_by_code),
            "clipped_objects": parsed.clipped_objects,
            "exclusions": parsed.exclusions,
            "warnings": parsed.warnings,
            "image_size": list(parsed.image_size) if parsed.image_size else None,
            "yolo_lines": lines,
        }
        if parsed.category == "empty_xml":
            empty_paths.append(source_rel)
        if parsed.category == "only_oos":
            only_oos_paths.append(source_rel)
        if parsed.is_pool_a:
            pool_a_paths.append(source_rel)
            for code in parsed.kept_by_code:
                class_images[code] += 1
        elif parsed.target_objects >= 1:
            mapping_zero_paths.append(source_rel)

        if index % 4000 == 0:
            print(f"      parsed {index}/{len(xml_paths)}", flush=True)

    no_xml_paths = [path for path in image_index.values() if path not in per_image]
    no_xml_by_official = collections.Counter(
        classify_path(raw_root / path, raw_root)[1] for path in no_xml_paths
    )

    # Policy C candidate: structurally empty XML not contradicted by a
    # near-duplicate that carries target or out-of-scope damage.
    uncertain_empties: set[str] = set()
    group_index: dict[str, int] = {}
    for group_id, members in enumerate(near_groups):
        for member in members:
            group_index[member] = group_id
        empties = [
            member
            for member in members
            if per_image.get(member, {}).get("category") == "empty_xml"
        ]
        if not empties:
            continue
        has_target = any(
            per_image.get(member, {}).get("target_objects", 0) > 0 for member in members
        )
        has_only_oos = any(
            per_image.get(member, {}).get("category") == "only_oos" for member in members
        )
        if has_target or has_only_oos:
            uncertain_empties.update(empties)
    verified_empty = [path for path in empty_paths if path not in uncertain_empties]

    only_oos_contradicted = []
    for path in only_oos_paths:
        group_id = group_index.get(path)
        if group_id is None:
            continue
        if any(
            per_image.get(member, {}).get("target_objects", 0) > 0
            for member in near_groups[group_id]
        ):
            only_oos_contradicted.append(path)

    counts = {
        "images_total": len(image_paths),
        "xml_files": len(xml_paths),
        "annotated_images": len(per_image),
        "images_without_xml": len(no_xml_paths),
        "objects_total": objects_total,
        "categories": {
            key: category_counts.get(key, 0)
            for key in ("only_target", "mixed_target_oos", "only_oos", "empty_xml")
        },
        "target_objects": target_objects,
        "target_retained": target_retained,
        "target_excluded": target_objects - target_retained,
        "target_exclusion_reasons": dict(sorted(target_exclusion_reasons.items())),
        "oos_geometry_reasons": dict(sorted(oos_geometry_reasons.items())),
        "oos_objects": oos_objects,
        "clipped_objects": clipped_objects,
        "target_boxes_clipped": target_clipped,
        "oos_boxes_clipped": oos_clipped,
        "xml_size_mismatch": xml_size_mismatch,
        "xml_without_image": len(xml_without_image),
        "parse_errors": len(parse_errors),
        "missing_name_objects": missing_name_objects,
        "unknown_codes": dict(sorted(unknown_codes.items())),
        "images_with_retained_target": len(pool_a_paths),
        "images_with_target_but_zero_retained": len(mapping_zero_paths),
        "empty_xml_total": len(empty_paths),
        "only_oos_total": len(only_oos_paths),
        "empty_contradicted_by_duplicates": len(uncertain_empties & set(empty_paths)),
        "verified_empty_candidates": len(verified_empty),
        "only_oos_contradicted_by_target_duplicate": len(only_oos_contradicted),
        "near_groups": len(near_groups),
        "policy_a_images": len(pool_a_paths),
        "policy_c_images": len(pool_a_paths) + len(verified_empty),
    }

    if xml_without_image:
        raise PipelineError(
            f"{len(xml_without_image)} XML files have no matching image; "
            f"first: {xml_without_image[:5]}"
        )
    if parse_errors:
        raise PipelineError(
            f"{len(parse_errors)} XML files could not be parsed; first: {parse_errors[:5]}"
        )
    if any(split != "test" for split in no_xml_by_official):
        raise PipelineError(
            "images without XML are not all in the official test folders: "
            f"{dict(no_xml_by_official)}"
        )
    if (
        sum(category_counts.get(key, 0) for key in ("only_target", "mixed_target_oos", "only_oos", "empty_xml"))
        != len(per_image)
    ):
        raise PipelineError("internal category accounting error")

    # ---- Policy selection -------------------------------------------------- #
    v2_signoff_path = args.v2_signoff
    v2_info = {"required_for": "C", "closed": False, "signoff": None}
    if v2_signoff_path:
        if not v2_signoff_path.is_file():
            raise PipelineError(f"V2 sign-off does not exist: {v2_signoff_path}")
        signoff = load_json(v2_signoff_path)
        if signoff.get("gate") != "V2" or signoff.get("complete") is not True:
            raise PipelineError(
                f"{v2_signoff_path} is not a complete V2 gate sign-off "
                "(expected {\"gate\": \"V2\", \"complete\": true, ...})"
            )
        v2_info = {
            "required_for": "C",
            "closed": True,
            "signoff": str(v2_signoff_path),
            "signoff_sha256": sha256_file(v2_signoff_path),
        }

    requested = args.policy
    cli_policy = args.policy
    requested_policy = "C" if args.policy == "auto" else args.policy
    if requested == "C" and not v2_info["closed"]:
        raise PipelineError(
            "Policy C requires the V2 visual-inspection gate; pass --v2-signoff "
            "with a completed sign-off, or use --policy A (the documented fallback)"
        )
    if requested == "auto":
        policy = "C" if v2_info["closed"] else "A"
        fallback_reason = (
            None
            if policy == "C"
            else "V2 visual-inspection gate not closed; Policy A fallback applied"
        )
    else:
        policy = requested
        fallback_reason = (
            "V2 visual-inspection gate not closed; Policy A fallback applied"
            if policy == "A" and not v2_info["closed"]
            else None
        )

    if policy == "C":
        pool = pool_a_paths + verified_empty
        background_images = len(verified_empty)
    else:
        pool = list(pool_a_paths)
        background_images = 0

    if len(pool) != (counts["policy_a_images"] if policy == "A" else counts["policy_c_images"]):
        raise PipelineError("policy pool size mismatch")

    # ---- Split ------------------------------------------------------------- #
    print("[3/5] assigning duplicate-aware splits", flush=True)
    from split_dataset import assign_splits

    per_image_for_split = {
        path: {
            "country": record["country"],
            "official_split": record["official_split"],
            "target_retained": record["target_retained"],
            "kept_by_code": record["kept_by_code"],
        }
        for path, record in per_image.items()
    }
    split_result = assign_splits(
        per_image_for_split,
        pool,
        near_groups,
        seed=args.seed,
        sha_of=sha_of,
        exact_groups=exact_groups,
    )
    if split_result.group_crossing_violations:
        raise PipelineError(
            f"{split_result.group_crossing_violations} duplicate groups cross splits"
        )
    if split_result.exact_hash_crossing_violations:
        raise PipelineError(
            f"{split_result.exact_hash_crossing_violations} exact hashes cross splits"
        )

    reconciliation = reconcile_audit(audit, counts, split_result, policy)
    if reconciliation["status"] != "PASS":
        raise PipelineError(
            "dataset does not reconcile with the S4-T3A audit: "
            f"{reconciliation['mismatches'][:10]}"
        )

    if args.dry_run:
        print("\nS4-T3B dry run (no files written)")
        print(f"  policy:      {requested_policy} -> {policy}")
        print(f"  counts:      {json.dumps(counts, sort_keys=True)}")
        print(f"  pool images: {len(pool)}  groups: {len(split_result.groups)}")
        for split in SPLIT_ORDER:
            stats = split_result.stats["splits"][split]
            print(
                f"  {split:<5}: images={stats['images']} objects={stats['retained_objects']} "
                f"groups={stats['groups']} ({stats['images_pct']}%)"
            )
        print(f"  reconciliation: {reconciliation['status']}")
        return 0

    # ---- Output names ------------------------------------------------------ #
    used_names: dict[str, str] = {}
    output_names: dict[str, str] = {}
    for source_rel in pool:
        record = per_image[source_rel]
        suffix = Path(source_rel).suffix.lower()
        base = f"{record['country']}__{Path(source_rel).stem}"
        candidate = base
        if candidate in used_names:
            candidate = f"{base}__{record['official_split']}"
        if candidate in used_names:
            candidate = f"{base}__{sha_of.get(source_rel, sha256_text(source_rel))[:8]}"
        if candidate in used_names:
            raise PipelineError(f"cannot make a unique output name for {source_rel}")
        used_names[candidate] = source_rel
        output_names[source_rel] = candidate + suffix

    # ---- Write ------------------------------------------------------------- #
    print("[4/5] writing images, labels and manifests", flush=True)
    out = args.out.resolve()
    clean_managed_output(out, args.force, keep_images=args.reports_only)
    for sub in ("images", "labels", "manifests", "reports"):
        (out / sub).mkdir(parents=True, exist_ok=True)

    label_texts: dict[str, str] = {}
    rows: list[dict] = []
    for source_rel in pool:
        record = per_image[source_rel]
        split = split_result.image_split[source_rel]
        output_name = output_names[source_rel]
        lines = record["yolo_lines"]
        text = "".join(f"{line}\n" for line in lines)
        label_texts[output_name] = text
        (out / "labels" / split).mkdir(parents=True, exist_ok=True)
        (out / "images" / split).mkdir(parents=True, exist_ok=True)
        rows.append(
            {
                "split": split,
                "output_name": output_name,
                "source_rel": source_rel,
                "country": record["country"],
                "official_split": record["official_split"],
                "category": record["category"],
                "group_id": -1,
                "n_objects": len(lines),
                "classes": "|".join(
                    f"{code}:{record['kept_by_code'][code]}"
                    for code in sorted(record["kept_by_code"], key=lambda c: CODE_TO_ID[c])
                ),
                "source_target_objects": record["target_objects"],
                "source_oos_objects": record["oos_objects"],
                "image_sha256": sha_of.get(source_rel, ""),
                "label_sha256": sha256_text(text),
            }
        )

    # group_id is not exposed on SplitResult; derive it deterministically.
    group_of: dict[str, int] = {}
    for group_id, members in enumerate(split_result.groups):
        for member in members:
            group_of[member] = group_id
    for row in rows:
        row["group_id"] = group_of[row["source_rel"]]

    rows.sort(key=lambda row: (SPLIT_RANK[row["split"]], row["output_name"]))
    for row in rows:
        write_text(out / "labels" / row["split"] / f"{Path(row['output_name']).stem}.txt",
                   label_texts[row["output_name"]])

    copy_jobs = []
    for row in rows:
        source = raw_root / row["source_rel"]
        destination = out / "images" / row["split"] / row["output_name"]
        copy_jobs.append((source, destination))
    if args.reports_only:
        missing = [str(destination) for _, destination in copy_jobs if not destination.is_file()]
        if missing:
            raise PipelineError(
                f"{len(missing)} expected dataset images are missing; "
                "run without --reports-only to materialise them"
            )
    else:
        workers = min(16, max(4, (os.cpu_count() or 4) * 2))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(copy_image, src, dst, args.copy_mode) for src, dst in copy_jobs]
            for done, future in enumerate(as_completed(futures), 1):
                future.result()
                if done % 4000 == 0:
                    print(f"      copied {done}/{len(futures)}", flush=True)

    # ---- Manifests --------------------------------------------------------- #
    manifest_csv = out / "manifests" / "split_manifest.csv"
    fieldnames = [
        "split",
        "output_name",
        "source_rel",
        "country",
        "official_split",
        "category",
        "group_id",
        "n_objects",
        "classes",
        "source_target_objects",
        "source_oos_objects",
        "image_sha256",
        "label_sha256",
    ]
    with manifest_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    manifest_sha = sha256_file(manifest_csv)

    for split in SPLIT_ORDER:
        names = sorted(
            f"images/{split}/{row['output_name']}"
            for row in rows
            if row["split"] == split
        )
        write_text(out / "manifests" / f"{split}.txt", "".join(f"{name}\n" for name in names))

    yaml_lines = [
        "# RoadVision AI dataset configuration (S4-T3B, generated by training/prepare_dataset.py)",
        "# Source: RDD2022 Pascal VOC annotations. Original data is read-only.",
        "path: .",
        "train: images/train",
        "val: images/val",
        "test: images/test",
        "nc: 4",
        "names:",
        *[f"  {index}: {name}" for index, name in enumerate(class_names)],
        "",
    ]
    write_text(out / "data.yaml", "\n".join(yaml_lines))
    data_yaml_sha = sha256_file(out / "data.yaml")

    # ---- Reports ----------------------------------------------------------- #
    print("[5/5] writing reports", flush=True)
    reports = out / "reports"

    per_country = {}
    for country in sorted(country_stats):
        stats = country_stats[country]
        per_country[country] = {
            "images_total": int(stats["images_total"]),
            "objects_total": int(stats["objects_total"]),
            "target_objects": int(stats["target_objects"]),
            "target_retained": int(stats["target_retained"]),
            "oos_objects": int(stats["oos_objects"]),
            "categories": {
                key: int(stats[f"category_{key}"])
                for key in ("only_target", "mixed_target_oos", "only_oos", "empty_xml")
            },
            "pool_a_images": sum(
                1
                for record in per_image.values()
                if record["country"] == country and record["target_retained"] >= 1
            ),
            "no_xml_images": sum(1 for path in no_xml_paths if path.startswith(country + "/")),
        }

    conversion_summary = {
        "generated_utc": utc_now(),
        "policy": {
            "cli": cli_policy,
            "requested": requested_policy,
            "applied": policy,
            "fallback_reason": fallback_reason,
            "v2_gate": v2_info,
        },
        "counts": counts,
        "class_objects_after_conversion": dict(sorted(class_objects.items())),
        "class_images_after_conversion": dict(sorted(class_images.items())),
        "per_country": per_country,
        "reconciliation": reconciliation,
        "source_hashes": {
            "policy_audit_json": sha256_file(args.policy_audit),
            "duplicate_groups_json": sha256_file(args.duplicate_groups),
            "image_hash_cache_json": sha256_file(args.hash_cache),
        },
    }
    write_json(reports / "conversion_summary.json", conversion_summary)

    # Exclusions: every source image that is not in the dataset, with a reason.
    included = set(pool)
    exclusion_rows = []
    reason_counts: collections.Counter = collections.Counter()
    for source_rel in sorted(image_index.values()):
        if source_rel in included:
            continue
        record = per_image.get(source_rel)
        if record is None:
            country, official_split = classify_path(raw_root / source_rel, raw_root)
            row = {
                "source_rel": source_rel,
                "country": country,
                "official_split": official_split,
                "category": "no_xml",
                "reason": "no_annotation_official_test",
                "codes": [],
            }
        else:
            category = record["category"]
            if category == "empty_xml":
                reason = (
                    "empty_annotation_contradicted_by_duplicate_evidence"
                    if policy == "C" and source_rel in uncertain_empties
                    else "empty_annotation_excluded_policy_a"
                )
            elif category == "only_oos":
                reason = "out_of_scope_only"
            elif record["target_retained"] == 0:
                reason = "target_boxes_all_invalid"
            else:
                reason = "excluded_unknown"
            row = {
                "source_rel": source_rel,
                "country": record["country"],
                "official_split": record["official_split"],
                "category": category,
                "reason": reason,
                "codes": record["codes"],
            }
        reason_counts[row["reason"]] += 1
        exclusion_rows.append(row)

    exclusion_report = {
        "generated_utc": utc_now(),
        "policy": policy,
        "counts": {
            "total_source_images": len(image_paths),
            "included_images": len(included),
            "excluded_images": len(exclusion_rows),
            "by_reason": dict(sorted(reason_counts.items())),
            "no_xml_by_official_split": dict(sorted(no_xml_by_official.items())),
            "empty_contradicted_by_duplicates": len(uncertain_empties & set(empty_paths)),
            "only_oos_contradicted_by_target_duplicate": len(only_oos_contradicted),
        },
        "objects": {
            "total_objects": counts["objects_total"],
            "target_objects": counts["target_objects"],
            "target_retained": counts["target_retained"],
            "target_excluded": counts["target_excluded"],
            "target_exclusion_reasons": counts["target_exclusion_reasons"],
            "out_of_scope_objects": counts["oos_objects"],
            "missing_name_objects": counts["missing_name_objects"],
            "unknown_codes": counts["unknown_codes"],
        },
        "images": exclusion_rows,
    }
    write_json(reports / "exclusion_report.json", exclusion_report)

    class_distribution = {
        "generated_utc": utc_now(),
        "policy": policy,
        "seed": args.seed,
        "splits": split_result.stats["splits"],
        "per_class_balance": split_result.per_class_balance,
        "totals": split_result.stats["totals"],
        "max_abs_deviation_pp": max(
            abs(row[split]["deviation_pp"])
            for row in split_result.per_class_balance.values()
            for split in SPLIT_ORDER
        ),
        "ratio_note": (
            "80/10/10 is a target; duplicate groups are never broken to force "
            "exact percentages. Actual shares are reported above."
        ),
    }
    write_json(reports / "class_distribution.json", class_distribution)

    group_splits: dict[int, set[str]] = collections.defaultdict(set)
    for row in rows:
        group_splits[row["group_id"]].add(row["split"])
    spanning_groups = [
        {"group_id": group_id, "splits": sorted(splits)}
        for group_id, splits in sorted(group_splits.items())
        if len(splits) > 1
    ]
    multi_image_groups = [
        group for group in split_result.groups if len(group) > 1
    ]
    largest_group = max(split_result.groups, key=len) if split_result.groups else []
    duplicate_leakage = {
        "generated_utc": utc_now(),
        "source": "data/reports/audit/duplicate_groups.json",
        "parameters": {
            "exact_duplicate_hash": "sha256 over raw file bytes",
            "near_duplicate_hash": "64-bit dHash",
            "hamming_threshold": 3,
            "bucket_cap": "none",
            "grouping": "union-find transitive closure (S4-T3A artifact reused)",
        },
        "artifact_near_groups": len(near_groups),
        "artifact_exact_groups": len(exact_groups),
        "pool_groups": len(split_result.groups),
        "pool_groups_with_multiple_images": len(multi_image_groups),
        "largest_pool_group": {
            "size": len(largest_group),
            "splits": sorted({split_result.image_split[member] for member in largest_group}),
        },
        "groups_spanning_splits": len(spanning_groups),
        "group_spanning_examples": spanning_groups[:10],
        "exact_hashes_spanning_splits": split_result.exact_hash_crossing_violations,
        "exact_hash_examples": split_result.exact_hash_crossings[:10],
        "status": "PASS"
        if not spanning_groups and not split_result.exact_hash_crossings
        else "FAIL",
    }
    write_json(reports / "duplicate_leakage.json", duplicate_leakage)

    # Source integrity: hash every XML and record the raw-tree mtime ceiling.
    print("      hashing source XMLs for the integrity baseline", flush=True)
    xml_tree_sha, xml_total_bytes, xml_count = hash_xml_tree(xml_paths, raw_root)
    raw_max_mtime = max(
        (path.stat().st_mtime for path in raw_root.rglob("*") if path.is_file()),
        default=0.0,
    )
    source_integrity = {
        "generated_utc": utc_now(),
        "pipeline_started_utc": started,
        "raw_root": str(raw_root),
        "xml_files": xml_count,
        "xml_total_bytes": xml_total_bytes,
        "xml_tree_sha256": xml_tree_sha,
        "raw_max_mtime_utc": datetime.fromtimestamp(
            raw_max_mtime, timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "image_cache_entries": len(cache),
        "image_cache_sha256": sha256_file(args.hash_cache) if args.hash_cache.is_file() else None,
        "method": (
            "XML tree digest = SHA-256 over sorted '<relative-path>\\t<sha256>\\n' lines. "
            "Image content is covered by the pre-existing S4-T3A image_hash_cache.json; "
            "verification re-hashes a deterministic stratified sample and checks that no "
            "raw file mtime is newer than the pipeline start."
        ),
    }
    write_json(reports / "source_integrity.json", source_integrity)

    per_image_index = {
        path: {
            "country": record["country"],
            "official_split": record["official_split"],
            "category": record["category"],
            "codes": record["codes"],
            "objects_total": record["objects_total"],
            "target_objects": record["target_objects"],
            "target_retained": record["target_retained"],
            "oos_objects": record["oos_objects"],
            "kept_by_code": record["kept_by_code"],
        }
        for path, record in sorted(per_image.items())
    }
    write_json(reports / "per_image_index.json", per_image_index)

    # Every excluded object, not just every excluded image.
    object_exclusions = []
    object_reason_counts: collections.Counter = collections.Counter()
    for source_rel, record in sorted(per_image.items()):
        for item in record["exclusions"]:
            object_exclusions.append(
                {
                    "source_rel": source_rel,
                    "object_index": item["object_index"],
                    "code": item["code"],
                    "reason": item["reason"],
                    "is_target": bool(item["is_target"]),
                }
            )
            object_reason_counts[item["reason"]] += 1
    write_json(
        reports / "object_exclusions.json",
        {
            "generated_utc": utc_now(),
            "policy": policy,
            "count": len(object_exclusions),
            "by_reason": dict(sorted(object_reason_counts.items())),
            "objects": object_exclusions,
        },
    )

    policy_decision = {
        "generated_utc": utc_now(),
        "q03_filtering": {
            "cli": cli_policy,
            "requested": requested_policy,
            "applied": policy,
            "fallback_reason": fallback_reason,
            "v2_gate": v2_info,
            "policy_a_images": counts["policy_a_images"],
            "policy_c_images": counts["policy_c_images"],
            "background_images_included": background_images,
            "background_treatment": (
                "Policy A: no background-only images are included. "
                "Empty XMLs and out-of-scope-only images are excluded and listed individually."
                if policy == "A"
                else "Policy C: structurally empty XMLs not contradicted by duplicate evidence "
                "are included as background with empty label files."
            ),
            "excluded_images": len(exclusion_rows),
            "excluded_objects": {
                "out_of_scope": counts["oos_objects"],
                "target_invalid": counts["target_excluded"],
            },
        },
        "q04_splitting": {
            "near_duplicate_threshold": 3,
            "hash": "64-bit dHash, 8x8 pigeonhole, no bucket cap",
            "seed": args.seed,
            "n_splits": 10,
            "folds": {"0": "test", "1": "val", "2-9": "train"},
            "target_ratio": {"train": 0.8, "val": 0.1, "test": 0.1},
            "group_level": True,
            "groups_spanning_splits": len(spanning_groups),
            "exact_hashes_spanning_splits": split_result.exact_hash_crossing_violations,
            "max_abs_class_deviation_pp": class_distribution["max_abs_deviation_pp"],
        },
        "evidence": {
            "policy_audit_report": "docs/project/ROADVISION_S4_T3A_POLICY_AUDIT.md",
            "policy_audit_json": {
                "path": str(args.policy_audit),
                "sha256": sha256_file(args.policy_audit),
            },
            "duplicate_groups_json": {
                "path": str(args.duplicate_groups),
                "sha256": sha256_file(args.duplicate_groups),
            },
            "image_hash_cache_json": {
                "path": str(args.hash_cache),
                "sha256": sha256_file(args.hash_cache),
            },
        },
    }
    write_json(reports / "policy_decision.json", policy_decision)

    split_manifest = {
        "seed": args.seed,
        "policy": policy,
        "near_duplicate_threshold": 3,
        "rows": len(rows),
        "splits": split_result.stats["splits"],
        "totals": split_result.stats["totals"],
        "pool_groups": split_result.stats["pool_groups"],
        "manifest_csv": "manifests/split_manifest.csv",
        "manifest_csv_sha256": manifest_sha,
        "image_lists": {
            split: f"manifests/{split}.txt" for split in SPLIT_ORDER
        },
        "data_yaml_sha256": data_yaml_sha,
        "classes": class_names,
    }
    write_json(out / "manifests" / "split_manifest.json", split_manifest)

    import cv2
    import numpy as np
    import sklearn

    dataset_report = {
        "stage": "S4-T3B",
        "generated_utc": utc_now(),
        "pipeline_started_utc": started,
        "elapsed_s": round(time.perf_counter() - started_perf, 1),
        "environment": {
            "python": sys.version.split()[0],
            "opencv": cv2.__version__,
            "numpy": np.__version__,
            "scikit_learn": sklearn.__version__,
        },
        "policy": {
            "cli": cli_policy,
            "requested": requested_policy,
            "applied": policy,
            "fallback_reason": fallback_reason,
            "v2_gate": v2_info,
        },
        "counts": counts,
        "splits": split_result.stats["splits"],
        "pool_groups": len(split_result.groups),
        "max_abs_class_deviation_pp": class_distribution["max_abs_deviation_pp"],
        "outputs": {
            "dataset_root": str(out),
            "data_yaml": "data.yaml",
            "data_yaml_sha256": data_yaml_sha,
            "manifest_csv": "manifests/split_manifest.csv",
            "manifest_csv_sha256": manifest_sha,
            "image_lists": {split: f"manifests/{split}.txt" for split in SPLIT_ORDER},
            "reports": sorted(
                path.name for path in (out / "reports").glob("*.json")
            ),
        },
        "reconciliation": reconciliation,
        "verification": {
            "status": "NOT RUN",
            "expected_report": "reports/verification.json",
            "command": (
                ".venv\\Scripts\\python.exe training\\verify_dataset.py "
                f"--dataset {out}"
            ),
        },
    }
    write_json(reports / "dataset_report.json", dataset_report)

    print("\nS4-T3B dataset written")
    print(f"  output:        {out}")
    print(f"  policy:        {requested_policy} -> {policy}" + (f" ({fallback_reason})" if fallback_reason else ""))
    print(f"  pool images:   {len(pool)}  groups: {len(split_result.groups)}")
    for split in SPLIT_ORDER:
        stats = split_result.stats["splits"][split]
        print(
            f"  {split:<5}: images={stats['images']:>6} "
            f"objects={stats['retained_objects']:>6} groups={stats['groups']:>6} "
            f"({stats['images_pct']}%)"
        )
    print(f"  manifest:      {manifest_csv} (sha256 {manifest_sha[:16]}...)")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-root", type=Path, default=RAW_DEFAULT)
    parser.add_argument("--classes", type=Path, default=CLASSES_DEFAULT)
    parser.add_argument("--duplicate-groups", type=Path, default=DEFAULT_DUPLICATES)
    parser.add_argument("--hash-cache", type=Path, default=DEFAULT_HASH_CACHE)
    parser.add_argument("--policy-audit", type=Path, default=DEFAULT_POLICY_AUDIT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--policy",
        choices=("auto", "A", "C"),
        default="auto",
        help="Q-03 policy; auto uses C only when a V2 sign-off is supplied",
    )
    parser.add_argument(
        "--v2-signoff",
        type=Path,
        help="completed V2 gate JSON required by Policy C",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--copy-mode",
        choices=("copy", "hardlink"),
        default="copy",
        help="image materialisation mode; hardlink is intended for reproducibility checks",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="remove previously generated images/labels/manifests/reports before writing",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="parse, filter, split and reconcile, but write no dataset files",
    )
    parser.add_argument(
        "--reports-only",
        action="store_true",
        help="rewrite labels/manifests/reports without re-copying images (images must exist)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        return run(parse_args(argv))
    except PipelineError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 - CLI reports one clear error
        print(f"UNEXPECTED ERROR: {exc}", file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
