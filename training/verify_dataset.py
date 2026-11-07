#!/usr/bin/env python3
"""Consolidated S4-T3B dataset verification.

One run checks every requirement:

1. every generated label follows YOLO format;
2. all class ids are valid;
3. every box is normalised and geometrically valid;
4. every image has exactly one label and every label one image;
5. every exclusion follows the approved Q-03 policy;
6. no confirmed duplicate group (or exact file hash) crosses splits;
7. split manifests reconcile with the actual files;
8. the pipeline is deterministic (in-memory re-derivation, plus a full
   second run when ``--repro-dir`` is supplied);
9. the original RDD2022 images and XMLs are unchanged.

Usage::

    .\\.venv\\Scripts\\python.exe training\\verify_dataset.py --dataset dataset

    # full determinism check against a second, independent run:
    .\\.venv\\Scripts\\python.exe training\\verify_dataset.py ^
        --dataset dataset --repro-dir dataset_repro

The machine-readable result is written to ``dataset/reports/verification.json``.
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

from convert_annotations import (
    CODE_TO_ID,
    CLASSES_DEFAULT,
    IMAGE_EXTS,
    KNOWN_CODES,
    TARGET_CODES,
    build_image_index,
    classify_path,
    iter_dataset_files,
    label_text,
    load_classes,
    parse_voc,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = PROJECT_ROOT / "dataset"
DEFAULT_RAW = PROJECT_ROOT / "data" / "raw" / "RDD2022"
DEFAULT_AUDIT = PROJECT_ROOT / "data" / "reports" / "audit"
DEFAULT_DUPLICATES = DEFAULT_AUDIT / "duplicate_groups.json"
DEFAULT_HASH_CACHE = DEFAULT_AUDIT / "image_hash_cache.json"
DEFAULT_POLICY_AUDIT = DEFAULT_AUDIT / "policy_audit.json"
SPLIT_ORDER = ("train", "val", "test")
TOLERANCE = 1e-6


class VerificationError(RuntimeError):
    pass


# --------------------------------------------------------------------------- #
# Helpers
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


def load_json(path: Path):
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
    path.write_text(text + "\n", encoding="utf-8", newline="\n")


def image_size_from_file(path: Path) -> tuple[int, int]:
    try:
        from PIL import Image

        with Image.open(path) as image:
            width, height = image.size
        return int(width), int(height)
    except Exception:  # noqa: BLE001
        import cv2

        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is None:
            raise VerificationError(f"cannot read image: {path}")
        height, width = image.shape[:2]
        return int(width), int(height)


def split_country(source_rel: str) -> str:
    return source_rel.split("/", 1)[0]


# --------------------------------------------------------------------------- #
# Re-scan (independent reconstruction of the policy pool)
# --------------------------------------------------------------------------- #
def rescan_annotations(raw_root: Path, cache: dict) -> dict:
    image_paths, xml_paths = iter_dataset_files(raw_root)
    image_index = build_image_index(image_paths, raw_root)
    categories: collections.Counter = collections.Counter()
    per_image: dict[str, dict] = {}
    pool_a: list[str] = []
    empty_paths: list[str] = []
    only_oos_paths: list[str] = []
    parse_errors: list[dict] = []
    counts = collections.Counter()

    for xml_path in xml_paths:
        country, official_split = classify_path(xml_path, raw_root)
        source_rel = image_index.get((country, official_split, xml_path.stem.lower()))
        if source_rel is None:
            counts["xml_without_image"] += 1
            continue
        entry = cache.get(source_rel)
        image_size = (int(entry[2]), int(entry[3])) if entry and entry[2] and entry[3] else None
        if image_size is None:
            image_size = image_size_from_file(raw_root / source_rel)
        try:
            parsed = parse_voc(xml_path, image_size=image_size)
        except Exception as exc:  # noqa: BLE001
            parse_errors.append({"xml": xml_path.as_posix(), "error": str(exc)})
            continue

        counts["objects_total"] += parsed.objects_total
        counts["target_objects"] += parsed.target_objects
        counts["target_retained"] += parsed.target_retained
        counts["oos_objects"] += parsed.oos_objects
        counts["clipped_objects"] += parsed.clipped_objects
        counts["xml_size_mismatch"] += 1 if parsed.warnings else 0
        counts["missing_name_objects"] += sum(
            1 for item in parsed.exclusions if item["reason"] == "missing_name"
        )
        for item in parsed.exclusions:
            if item.get("is_target") and item["reason"] != "out_of_scope_class":
                counts[f"target_exclusion_{item['reason']}"] += 1
            if not item.get("is_target") and item["reason"] != "out_of_scope_class":
                counts[f"oos_geometry_{item['reason']}"] += 1
        categories[parsed.category] += 1
        per_image[source_rel] = {
            "source_rel": source_rel,
            "country": country,
            "official_split": official_split,
            "category": parsed.category,
            "codes": list(parsed.codes),
            "objects_total": parsed.objects_total,
            "target_objects": parsed.target_objects,
            "target_retained": parsed.target_retained,
            "oos_objects": parsed.oos_objects,
            "kept_by_code": dict(parsed.kept_by_code),
            "yolo_lines": label_text(parsed).splitlines(),
            "label_text": label_text(parsed),
        }
        if parsed.category == "empty_xml":
            empty_paths.append(source_rel)
        if parsed.category == "only_oos":
            only_oos_paths.append(source_rel)
        if parsed.is_pool_a:
            pool_a.append(source_rel)

    no_xml = [path for path in image_index.values() if path not in per_image]
    return {
        "image_paths": image_paths,
        "xml_paths": xml_paths,
        "image_index": image_index,
        "no_xml": no_xml,
        "per_image": per_image,
        "pool_a": pool_a,
        "empty_paths": empty_paths,
        "only_oos_paths": only_oos_paths,
        "categories": dict(categories),
        "counts": dict(counts),
        "parse_errors": parse_errors,
    }


def verified_empty_paths(rescan: dict, near_groups: list[list[str]]) -> tuple[list[str], set[str]]:
    uncertain: set[str] = set()
    for members in near_groups:
        empties = [
            member
            for member in members
            if rescan["per_image"].get(member, {}).get("category") == "empty_xml"
        ]
        if not empties:
            continue
        has_target = any(
            rescan["per_image"].get(member, {}).get("target_objects", 0) > 0
            for member in members
        )
        has_only_oos = any(
            rescan["per_image"].get(member, {}).get("category") == "only_oos"
            for member in members
        )
        if has_target or has_only_oos:
            uncertain.update(empties)
    return [path for path in rescan["empty_paths"] if path not in uncertain], uncertain


# --------------------------------------------------------------------------- #
# Individual checks
# --------------------------------------------------------------------------- #
def check_classes(dataset: Path, classes_path: Path) -> dict:
    import yaml

    classes = load_classes(classes_path)
    names = list(classes["names"])
    data_yaml = dataset / "data.yaml"
    if not data_yaml.is_file():
        raise VerificationError(f"missing {data_yaml}")
    doc = yaml.safe_load(data_yaml.read_text(encoding="utf-8"))
    yaml_names = doc.get("names")
    if isinstance(yaml_names, dict):
        yaml_list = [yaml_names[index] for index in range(len(yaml_names))]
    elif isinstance(yaml_names, list):
        yaml_list = list(yaml_names)
    else:
        raise VerificationError("data.yaml 'names' is neither a list nor a mapping")

    errors = []
    if yaml_list != names:
        errors.append(f"data.yaml names {yaml_list} != classes.json {names}")
    if doc.get("nc") != len(names):
        errors.append(f"data.yaml nc {doc.get('nc')} != {len(names)}")
    for key in ("train", "val", "test"):
        if not doc.get(key):
            errors.append(f"data.yaml missing '{key}'")
    if errors:
        raise VerificationError("; ".join(errors))
    return {
        "classes": names,
        "data_yaml": str(data_yaml),
        "data_yaml_sha256": sha256_file(data_yaml),
    }


def load_manifest(dataset: Path) -> tuple[list[dict], Path]:
    manifest_path = dataset / "manifests" / "split_manifest.csv"
    if not manifest_path.is_file():
        raise VerificationError(f"missing {manifest_path}")
    with manifest_path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
    expected = {
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
    }
    if rows and set(rows[0].keys()) != expected:
        raise VerificationError(f"manifest header {list(rows[0].keys())} != {sorted(expected)}")
    return rows, manifest_path


def check_correspondence(dataset: Path, rows: list[dict]) -> dict:
    by_split: dict[str, dict[str, dict]] = {split: {} for split in SPLIT_ORDER}
    errors: list[str] = []
    seen_names: set[str] = set()
    seen_sources: set[str] = set()
    image_count = 0
    label_count = 0

    for row in rows:
        split = row["split"]
        if split not in by_split:
            errors.append(f"invalid split {split!r} in manifest")
            continue
        name = row["output_name"]
        if name in seen_names:
            errors.append(f"duplicate output name {name}")
        seen_names.add(name)
        if row["source_rel"] in seen_sources:
            errors.append(f"duplicate source {row['source_rel']}")
        seen_sources.add(row["source_rel"])
        by_split[split][name] = row

    for split in SPLIT_ORDER:
        image_dir = dataset / "images" / split
        label_dir = dataset / "labels" / split
        images = {
            path.name: path
            for path in image_dir.iterdir()
            if path.is_file() and path.suffix.lower() in IMAGE_EXTS
        }
        labels = {
            path.stem: path for path in label_dir.iterdir() if path.is_file() and path.suffix == ".txt"
        }
        image_count += len(images)
        label_count += len(labels)
        image_stems = {Path(name).stem for name in images}
        if image_stems != set(labels):
            missing_labels = sorted(image_stems - set(labels))[:10]
            orphan_labels = sorted(set(labels) - image_stems)[:10]
            errors.append(
                f"{split}: image/label stem mismatch; missing labels={missing_labels}, "
                f"orphan labels={orphan_labels}"
            )
        expected_names = set(by_split[split])
        if set(images) != expected_names:
            errors.append(
                f"{split}: manifest names differ from image files "
                f"(manifest-only={sorted(expected_names - set(images))[:5]}, "
                f"file-only={sorted(set(images) - expected_names)[:5]})"
            )
        for name, path in images.items():
            try:
                width, height = image_size_from_file(path)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{split}/{name}: unreadable image ({exc})")
                continue
            if width <= 0 or height <= 0:
                errors.append(f"{split}/{name}: invalid dimensions {width}x{height}")

    if image_count != len(rows):
        errors.append(f"image files {image_count} != manifest rows {len(rows)}")
    if label_count != len(rows):
        errors.append(f"label files {label_count} != manifest rows {len(rows)}")
    if errors:
        raise VerificationError("; ".join(errors[:20]))
    return {
        "images": image_count,
        "labels": label_count,
        "per_split": {
            split: len(by_split[split]) for split in SPLIT_ORDER
        },
    }


def check_labels(dataset: Path, rows: list[dict], class_names: list[str]) -> dict:
    errors: list[str] = []
    total_lines = 0
    empty_labels = 0
    class_counts: collections.Counter = collections.Counter()
    class_images: collections.Counter = collections.Counter()
    box_violations = 0

    for row in rows:
        split = row["split"]
        path = dataset / "labels" / split / f"{Path(row['output_name']).stem}.txt"
        if not path.is_file():
            errors.append(f"missing label {path}")
            continue
        text = path.read_text(encoding="utf-8")
        if text and not text.endswith("\n"):
            errors.append(f"{path}: missing final newline")
        lines = text.splitlines()
        if text and any(not line.strip() for line in lines):
            errors.append(f"{path}: blank line in label")
        if not lines:
            empty_labels += 1
            continue
        if len(lines) != int(row["n_objects"]):
            errors.append(
                f"{path}: {len(lines)} lines != manifest n_objects {row['n_objects']}"
            )
        total_lines += len(lines)
        present_classes: set[int] = set()
        for line_number, line in enumerate(lines, 1):
            parts = line.split()
            if len(parts) != 5:
                errors.append(f"{path}:{line_number}: expected 5 tokens, got {len(parts)}")
                continue
            if parts[0] not in {str(index) for index in range(len(class_names))}:
                errors.append(f"{path}:{line_number}: invalid class id {parts[0]!r}")
                continue
            class_id = int(parts[0])
            present_classes.add(class_id)
            try:
                x_center, y_center, width, height = (float(value) for value in parts[1:])
            except ValueError:
                errors.append(f"{path}:{line_number}: non-numeric coordinate")
                continue
            if not all(math.isfinite(value) for value in (x_center, y_center, width, height)):
                errors.append(f"{path}:{line_number}: non-finite coordinate")
                continue
            if not (0.0 <= x_center <= 1.0 and 0.0 <= y_center <= 1.0):
                errors.append(f"{path}:{line_number}: centre outside [0,1]")
                box_violations += 1
            if not (0.0 < width <= 1.0 and 0.0 < height <= 1.0):
                errors.append(f"{path}:{line_number}: width/height outside (0,1]")
                box_violations += 1
            if (
                x_center - width / 2 < -TOLERANCE
                or x_center + width / 2 > 1 + TOLERANCE
                or y_center - height / 2 < -TOLERANCE
                or y_center + height / 2 > 1 + TOLERANCE
            ):
                errors.append(f"{path}:{line_number}: box extends outside [0,1]")
                box_violations += 1
            class_counts[class_names[class_id]] += 1
        for code in present_classes:
            class_images[class_names[code]] += 1

    if errors:
        raise VerificationError("; ".join(errors[:25]))
    return {
        "label_files": len(rows),
        "label_lines": total_lines,
        "empty_label_files": empty_labels,
        "class_objects": dict(sorted(class_counts.items())),
        "class_images": dict(sorted(class_images.items())),
        "box_violations": box_violations,
    }


def check_reconciliation(
    dataset: Path,
    rescan: dict,
    rows: list[dict],
    policy_applied: str,
    near_groups: list[list[str]],
    cache: dict,
    audit: dict,
) -> dict:
    conversion = load_json(dataset / "reports" / "conversion_summary.json")
    decision = load_json(dataset / "reports" / "policy_decision.json")
    exclusion = load_json(dataset / "reports" / "exclusion_report.json")

    errors: list[str] = []
    counts = conversion["counts"]
    recomputed = rescan["counts"]

    # Independent reconciliation with the S4-T3A audit (not just the report).
    part_a = audit["part_a"]
    for key, actual, expected in (
        ("xml_files", len(rescan["xml_paths"]), part_a["xml_files"]),
        ("annotated_images", len(rescan["per_image"]), part_a["annotated_images"]),
        ("images_without_xml", len(rescan["no_xml"]), part_a["images_without_xml"]),
        ("objects_total", recomputed["objects_total"], part_a["objects_total"]),
        ("target_objects", recomputed["target_objects"], part_a["target_objects"]),
        ("target_retained", recomputed["target_retained"], part_a["target_objects_retained_after_rules"]),
        ("oos_objects", recomputed["oos_objects"], part_a["oos_objects"]),
        ("images_with_retained_target", len(rescan["pool_a"]), part_a["images_with_retained_target"]),
    ):
        if actual != expected:
            errors.append(f"audit {key}: re-scan {actual} != audit {expected}")
    for category, expected in part_a["image_categories"].items():
        if category == "check_sum_equals_annotated":
            continue
        actual = rescan["categories"].get(category, 0)
        if actual != expected:
            errors.append(f"audit category {category}: {actual} != {expected}")
    pool_sizes = audit["part_c"]["policy_pool_sizes"]
    if len(rescan["pool_a"]) != pool_sizes["policy_a_images"]:
        errors.append(
            f"audit Policy A pool {len(rescan['pool_a'])} != {pool_sizes['policy_a_images']}"
        )
    if len(rescan["pool_a"]) + len(verified_empty_paths(rescan, near_groups)[0]) != pool_sizes["policy_c_images"]:
        errors.append("audit Policy C pool size does not reconcile")

    # Core counts must match the conversion report.
    for key, actual in (
        ("objects_total", recomputed["objects_total"]),
        ("target_objects", recomputed["target_objects"]),
        ("target_retained", recomputed["target_retained"]),
        ("oos_objects", recomputed["oos_objects"]),
    ):
        if counts[key] != actual:
            errors.append(f"conversion {key} {counts[key]} != re-scan {actual}")
    for category in ("only_target", "mixed_target_oos", "only_oos", "empty_xml"):
        if counts["categories"][category] != rescan["categories"].get(category, 0):
            errors.append(
                f"category {category} {counts['categories'][category]} != "
                f"re-scan {rescan['categories'].get(category, 0)}"
            )
    if counts["xml_files"] != len(rescan["xml_paths"]):
        errors.append("xml file count differs from re-scan")
    if counts["images_without_xml"] != len(rescan["no_xml"]):
        errors.append("no-XML image count differs from re-scan")
    if rescan["parse_errors"]:
        errors.append(f"{len(rescan['parse_errors'])} XML parse errors in re-scan")

    # Build the expected included set for the applied policy.
    verified_empty, uncertain = verified_empty_paths(rescan, near_groups)
    if policy_applied == "A":
        expected_included = set(rescan["pool_a"])
    else:
        expected_included = set(rescan["pool_a"]) | set(verified_empty)
    manifest_sources = {row["source_rel"] for row in rows}
    if manifest_sources != expected_included:
        errors.append(
            "manifest source set does not equal the policy pool "
            f"(manifest-only={sorted(manifest_sources - expected_included)[:5]}, "
            f"pool-only={sorted(expected_included - manifest_sources)[:5]})"
        )

    # Every included source image must have exactly the generated label.
    for row in rows:
        record = rescan["per_image"].get(row["source_rel"])
        if record is None:
            errors.append(f"included source has no annotation: {row['source_rel']}")
            continue
        expected_text = record["label_text"]
        actual_path = dataset / "labels" / row["split"] / f"{Path(row['output_name']).stem}.txt"
        actual_text = actual_path.read_text(encoding="utf-8") if actual_path.is_file() else None
        if actual_text != expected_text:
            errors.append(f"label mismatch for {row['source_rel']}")
        if row["category"] != record["category"]:
            errors.append(f"category mismatch for {row['source_rel']}")
        if any(code not in TARGET_CODES for code in record["kept_by_code"]):
            errors.append(f"out-of-scope code in kept boxes for {row['source_rel']}")
        if int(row["source_target_objects"]) != record["target_objects"]:
            errors.append(f"target object mismatch for {row['source_rel']}")
        if int(row["source_oos_objects"]) != record["oos_objects"]:
            errors.append(f"OOS object mismatch for {row['source_rel']}")
        expected_classes = "|".join(
            f"{code}:{record['kept_by_code'][code]}"
            for code in sorted(record["kept_by_code"], key=lambda value: CODE_TO_ID[value])
        )
        if row["classes"] != expected_classes:
            errors.append(f"class summary mismatch for {row['source_rel']}")

    # Every excluded source image must be listed exactly once with a valid reason.
    excluded_rows = exclusion["images"]
    excluded_sources = [item["source_rel"] for item in excluded_rows]
    if len(excluded_sources) != len(set(excluded_sources)):
        errors.append("duplicate source in exclusion report")
    expected_excluded = set(rescan["image_index"].values()) - expected_included
    if set(excluded_sources) != expected_excluded:
        errors.append(
            "exclusion report does not cover exactly the excluded images "
            f"(report-only={sorted(set(excluded_sources) - expected_excluded)[:5]}, "
            f"missing={sorted(expected_excluded - set(excluded_sources))[:5]})"
        )
    reason_counts: collections.Counter = collections.Counter()
    allowed_reasons = {
        "no_annotation_official_test",
        "empty_annotation_excluded_policy_a",
        "empty_annotation_contradicted_by_duplicate_evidence",
        "out_of_scope_only",
        "target_boxes_all_invalid",
    }
    for item in excluded_rows:
        reason = item["reason"]
        reason_counts[reason] += 1
        if reason not in allowed_reasons:
            errors.append(f"unknown exclusion reason {reason!r} for {item['source_rel']}")
        if reason == "no_annotation_official_test":
            if item["official_split"] != "test":
                errors.append(f"no-XML image outside official test: {item['source_rel']}")
        elif reason == "empty_annotation_excluded_policy_a":
            if policy_applied != "A":
                errors.append("Policy C dataset uses a Policy A exclusion reason")
            if item["category"] != "empty_xml":
                errors.append(f"non-empty image marked as empty: {item['source_rel']}")
        elif reason == "empty_annotation_contradicted_by_duplicate_evidence":
            if item["category"] != "empty_xml" or item["source_rel"] not in uncertain:
                errors.append(f"invalid contradicted-empty exclusion: {item['source_rel']}")
        elif reason == "out_of_scope_only":
            if item["category"] != "only_oos":
                errors.append(f"non-only_oos image marked out_of_scope_only: {item['source_rel']}")
        elif reason == "target_boxes_all_invalid":
            if rescan["per_image"].get(item["source_rel"], {}).get("target_retained", 1) != 0:
                errors.append(f"invalid target_boxes_all_invalid exclusion: {item['source_rel']}")

    if exclusion["counts"]["excluded_images"] != len(excluded_rows):
        errors.append("exclusion count does not match exclusion rows")
    if exclusion["counts"]["included_images"] != len(rows):
        errors.append("inclusion count does not match manifest rows")
    if exclusion["counts"]["by_reason"] != dict(sorted(reason_counts.items())):
        errors.append("exclusion reason counts do not reconcile")

    # Policy disclosure must be explicit.
    if decision["q03_filtering"]["requested"] != "C":
        errors.append("policy_decision does not record the requested Policy C")
    if decision["q03_filtering"]["applied"] != policy_applied:
        errors.append("policy_decision applied policy differs from dataset_report")
    if policy_applied == "A":
        if not decision["q03_filtering"]["fallback_reason"]:
            errors.append("Policy A fallback has no recorded reason")
        if decision["q03_filtering"]["v2_gate"]["closed"]:
            errors.append("Policy A dataset claims the V2 gate is closed")
        if decision["q03_filtering"]["background_images_included"] != 0:
            errors.append("Policy A dataset includes background images")
        if uncertain and len(uncertain & set(rescan["empty_paths"])) != counts[
            "empty_contradicted_by_duplicates"
        ]:
            errors.append("contradicted-empty count does not reconcile")

    if errors:
        raise VerificationError("; ".join(errors[:25]))
    return {
        "included": len(rows),
        "excluded": len(excluded_rows),
        "exclusion_reasons": dict(sorted(reason_counts.items())),
        "empty_contradicted": len(uncertain & set(rescan["empty_paths"])),
        "policy_applied": policy_applied,
        "labels_match_recomputation": True,
    }


def check_duplicates(
    dataset: Path,
    rows: list[dict],
    duplicates: dict,
    near_groups: list[list[str]],
    exact_groups: list[list[str]],
) -> dict:
    manifest = {row["source_rel"]: row for row in rows}
    errors: list[str] = []

    group_splits: dict[int, set[str]] = collections.defaultdict(set)
    group_ids: set[int] = set()
    for row in rows:
        group_id = int(row["group_id"])
        group_ids.add(group_id)
        group_splits[group_id].add(row["split"])
    spanning = {
        group_id: sorted(splits)
        for group_id, splits in group_splits.items()
        if len(splits) > 1
    }
    if spanning:
        errors.append(f"{len(spanning)} split groups cross splits")

    # Artifact near groups: all included members must be in one split.
    near_violations = []
    near_group_ids: dict[int, set[int]] = {}
    for group_id, members in enumerate(near_groups):
        included = [member for member in members if member in manifest]
        if not included:
            continue
        splits = {manifest[member]["split"] for member in included}
        if len(splits) > 1:
            near_violations.append({"group_id": group_id, "splits": sorted(splits)})
        ids = {int(manifest[member]["group_id"]) for member in included}
        near_group_ids[group_id] = ids
        if len(ids) > 1:
            errors.append(f"near group {group_id} maps to multiple split group ids {sorted(ids)}")

    exact_violations = []
    for group in exact_groups:
        included = [member for member in group if member in manifest]
        splits = {manifest[member]["split"] for member in included}
        if len(splits) > 1:
            exact_violations.append({"members": included, "splits": sorted(splits)})

    sha_splits: dict[str, set[str]] = collections.defaultdict(set)
    for row in rows:
        sha_splits[row["image_sha256"]].add(row["split"])
    sha_violations = {
        digest: sorted(splits)
        for digest, splits in sha_splits.items()
        if len(splits) > 1
    }
    if sha_violations:
        errors.append(f"{len(sha_violations)} exact image hashes cross splits")

    report = load_json(dataset / "reports" / "duplicate_leakage.json")
    if report["status"] != "PASS":
        errors.append("duplicate_leakage.json status is not PASS")
    if report["groups_spanning_splits"] != len(spanning):
        errors.append("duplicate_leakage group count does not reconcile")
    if report["exact_hashes_spanning_splits"] != len(sha_violations):
        errors.append("duplicate_leakage exact-hash count does not reconcile")

    if errors:
        raise VerificationError("; ".join(errors[:20]))
    return {
        "split_groups": len(group_ids),
        "groups_spanning_splits": len(spanning),
        "artifact_near_groups": len(near_groups),
        "near_group_violations": len(near_violations),
        "exact_group_violations": len(exact_violations),
        "exact_hash_crossings": len(sha_violations),
        "status": "PASS",
    }


def check_split_manifest(dataset: Path, rows: list[dict], class_names: list[str]) -> dict:
    errors: list[str] = []
    split_manifest = load_json(dataset / "manifests" / "split_manifest.json")
    dataset_report = load_json(dataset / "reports" / "dataset_report.json")
    distribution = load_json(dataset / "reports" / "class_distribution.json")

    manifest_csv = dataset / "manifests" / "split_manifest.csv"
    if split_manifest["manifest_csv_sha256"] != sha256_file(manifest_csv):
        errors.append("split_manifest.json CSV hash does not match")
    if split_manifest["rows"] != len(rows):
        errors.append("split_manifest.json row count does not match CSV")
    if split_manifest["classes"] != class_names:
        errors.append("split_manifest.json classes do not match data.yaml")
    if split_manifest["data_yaml_sha256"] != sha256_file(dataset / "data.yaml"):
        errors.append("split_manifest.json data.yaml hash does not match")

    csv_by_split = collections.Counter(row["split"] for row in rows)
    csv_objects = collections.Counter()
    csv_class_objects: dict[str, collections.Counter] = {
        split: collections.Counter() for split in SPLIT_ORDER
    }
    csv_class_images: dict[str, collections.Counter] = {
        split: collections.Counter() for split in SPLIT_ORDER
    }
    for row in rows:
        split = row["split"]
        csv_objects[split] += int(row["n_objects"])
        for token in filter(None, row["classes"].split("|")):
            code, _, count = token.partition(":")
            csv_class_objects[split][code] += int(count)
            csv_class_images[split][code] += 1

    for split in SPLIT_ORDER:
        if csv_by_split[split] != split_manifest["splits"][split]["images"]:
            errors.append(f"{split}: CSV image count differs from split_manifest.json")
        if csv_objects[split] != split_manifest["splits"][split]["retained_objects"]:
            errors.append(f"{split}: CSV object count differs from split_manifest.json")
        if csv_by_split[split] != distribution["splits"][split]["images"]:
            errors.append(f"{split}: CSV image count differs from class_distribution.json")
        if csv_objects[split] != distribution["splits"][split]["retained_objects"]:
            errors.append(f"{split}: CSV object count differs from class_distribution.json")
        if dict(sorted(csv_class_objects[split].items())) != distribution["splits"][split]["class_objects"]:
            errors.append(f"{split}: class objects differ from class_distribution.json")
        if dict(sorted(csv_class_images[split].items())) != distribution["splits"][split]["class_images"]:
            errors.append(f"{split}: class images differ from class_distribution.json")
        list_path = dataset / "manifests" / f"{split}.txt"
        listed = [line for line in list_path.read_text(encoding="utf-8").splitlines() if line]
        expected = sorted(
            f"images/{split}/{row['output_name']}" for row in rows if row["split"] == split
        )
        if listed != expected:
            errors.append(f"{split}.txt does not match the manifest")

        if csv_by_split[split] != dataset_report["splits"][split]["images"]:
            errors.append(f"{split}: dataset_report image count differs")

    total = sum(csv_by_split.values())
    for split, target in (("train", 0.8), ("val", 0.1), ("test", 0.1)):
        share = 100.0 * csv_by_split[split] / total if total else 0.0
        if abs(share - 100.0 * target) > 5.0:
            errors.append(f"{split}: share {share:.2f}% is more than 5 pp from target")

    if errors:
        raise VerificationError("; ".join(errors[:20]))
    return {
        "rows": len(rows),
        "per_split": dict(csv_by_split),
        "objects_per_split": dict(csv_objects),
        "shares_pct": {
            split: round(100.0 * csv_by_split[split] / total, 2) for split in SPLIT_ORDER
        },
        "manifest_csv_sha256": sha256_file(manifest_csv),
    }


def check_determinism(
    dataset: Path,
    rows: list[dict],
    rescan: dict,
    near_groups: list[list[str]],
    exact_groups: list[list[str]],
    cache: dict,
    seed: int,
    repro_dir: Path | None,
) -> dict:
    from split_dataset import assign_splits

    sha_of = {key: value[0] for key, value in cache.items() if value and value[0]}
    per_image = {
        path: {
            "country": record["country"],
            "official_split": record["official_split"],
            "target_retained": record["target_retained"],
            "kept_by_code": record["kept_by_code"],
        }
        for path, record in rescan["per_image"].items()
    }
    decision = load_json(dataset / "reports" / "policy_decision.json")
    policy = decision["q03_filtering"]["applied"]
    if policy == "A":
        pool = list(rescan["pool_a"])
    else:
        verified_empty, _ = verified_empty_paths(rescan, near_groups)
        pool = list(rescan["pool_a"]) + verified_empty
    result = assign_splits(
        per_image,
        pool,
        near_groups,
        seed=seed,
        sha_of=sha_of,
        exact_groups=exact_groups,
    )
    manifest_split = {row["source_rel"]: row["split"] for row in rows}
    if result.image_split != manifest_split:
        differing = [
            path
            for path in manifest_split
            if result.image_split.get(path) != manifest_split[path]
        ]
        raise VerificationError(
            f"in-memory re-run does not reproduce the split ({len(differing)} differences)"
        )

    details = {
        "in_memory_rerun": "PASS",
        "seed": seed,
        "pool_images": len(pool),
        "pool_groups": len(result.groups),
        "full_pipeline_rerun_compared": False,
    }

    if repro_dir is None:
        details["note"] = (
            "pass --repro-dir <second-run-output> to compare a complete second "
            "pipeline run byte-for-byte"
        )
        return details

    errors: list[str] = []
    repro_dir = repro_dir.resolve()
    for rel in ("manifests/split_manifest.csv", "manifests/split_manifest.json", "data.yaml"):
        first = dataset / rel
        second = repro_dir / rel
        if not second.is_file():
            errors.append(f"missing repro file {second}")
            continue
        if first.read_bytes() != second.read_bytes():
            errors.append(f"{rel} differs between runs")

    for split in SPLIT_ORDER:
        for rel in (f"manifests/{split}.txt",):
            if (dataset / rel).read_bytes() != (repro_dir / rel).read_bytes():
                errors.append(f"{rel} differs between runs")

    def tree(root: Path, sub: str, suffix: str) -> dict[str, str]:
        return {
            path.relative_to(root).as_posix(): sha256_file(path)
            for path in (root / sub).rglob(f"*{suffix}")
            if path.is_file()
        }

    first_labels = tree(dataset, "labels", ".txt")
    second_labels = tree(repro_dir, "labels", ".txt")
    if first_labels != second_labels:
        errors.append("label tree differs between runs")

    first_images = {
        path.relative_to(dataset).as_posix(): path.stat().st_size
        for path in (dataset / "images").rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS
    }
    second_images = {
        path.relative_to(repro_dir).as_posix(): path.stat().st_size
        for path in (repro_dir / "images").rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS
    }
    if first_images != second_images:
        errors.append("image tree names/sizes differ between runs")

    first_dist = load_json(dataset / "reports" / "class_distribution.json")
    second_dist = load_json(repro_dir / "reports" / "class_distribution.json")
    first_dist.pop("generated_utc", None)
    second_dist.pop("generated_utc", None)
    if first_dist != second_dist:
        errors.append("class_distribution.json differs between runs")

    first_report = load_json(dataset / "reports" / "conversion_summary.json")
    second_report = load_json(repro_dir / "reports" / "conversion_summary.json")
    first_report.pop("generated_utc", None)
    second_report.pop("generated_utc", None)
    if first_report != second_report:
        errors.append("conversion_summary.json differs between runs")

    if errors:
        raise VerificationError("; ".join(errors[:20]))
    details["full_pipeline_rerun_compared"] = True
    details["label_files_compared"] = len(first_labels)
    details["image_files_compared"] = len(first_images)
    return details


def check_original_integrity(
    dataset: Path,
    rescan: dict,
    cache: dict,
    sample_size: int,
) -> dict:
    errors: list[str] = []
    integrity = load_json(dataset / "reports" / "source_integrity.json")
    dataset_report = load_json(dataset / "reports" / "dataset_report.json")
    raw_root = Path(integrity["raw_root"])

    xml_hashes = []
    xml_total_bytes = 0
    from prepare_dataset import hash_xml_tree

    xml_tree_sha, xml_total_bytes, xml_count = hash_xml_tree(
        rescan["xml_paths"], raw_root
    )
    if xml_tree_sha != integrity["xml_tree_sha256"]:
        errors.append("XML tree digest changed since conversion")
    if xml_total_bytes != integrity["xml_total_bytes"]:
        errors.append("XML total bytes changed since conversion")
    if xml_count != integrity["xml_files"]:
        errors.append("XML file count changed since conversion")

    current_max_mtime = max(
        (path.stat().st_mtime for path in raw_root.rglob("*") if path.is_file()),
        default=0.0,
    )
    current_max_iso = datetime.fromtimestamp(current_max_mtime, timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    if current_max_iso != integrity["raw_max_mtime_utc"]:
        errors.append(
            f"raw tree mtime ceiling changed ({integrity['raw_max_mtime_utc']} -> {current_max_iso})"
        )
    started = datetime.strptime(
        dataset_report["pipeline_started_utc"], "%Y-%m-%dT%H:%M:%SZ"
    ).replace(tzinfo=timezone.utc)
    newest = datetime.fromtimestamp(current_max_mtime, timezone.utc)
    if newest > started:
        errors.append(
            f"a raw file is newer than the pipeline start ({current_max_iso} > "
            f"{dataset_report['pipeline_started_utc']})"
        )

    # Deterministic stratified sample of source images against the S4-T3A cache.
    by_country: dict[str, list[str]] = collections.defaultdict(list)
    for path in sorted(rescan["image_index"].values()):
        by_country[split_country(path)].append(path)
    per_country = max(1, sample_size // max(1, len(by_country)))
    sample: list[str] = []
    for country in sorted(by_country):
        paths = by_country[country]
        step = max(1, len(paths) // per_country)
        sample.extend(paths[::step][:per_country])
    sample = sample[:sample_size]

    image_matches = 0
    dataset_matches = 0
    manifest = {}
    with (dataset / "manifests" / "split_manifest.csv").open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            manifest[row["source_rel"]] = row
    for source_rel in sample:
        entry = cache.get(source_rel)
        if not entry:
            errors.append(f"source image missing from cache: {source_rel}")
            continue
        actual = sha256_file(raw_root / source_rel)
        if actual != entry[0]:
            errors.append(f"source image changed: {source_rel}")
        else:
            image_matches += 1
        row = manifest.get(source_rel)
        if row:
            copied = dataset / "images" / row["split"] / row["output_name"]
            if sha256_file(copied) != entry[0]:
                errors.append(f"dataset copy differs from source: {source_rel}")
            else:
                dataset_matches += 1

    if errors:
        raise VerificationError("; ".join(errors[:20]))
    return {
        "xml_files_hashed": len(rescan["xml_paths"]),
        "xml_tree_sha256": xml_tree_sha,
        "raw_max_mtime_utc": current_max_iso,
        "raw_newer_than_pipeline_start": 0,
        "sample_images": len(sample),
        "sample_source_hash_matches": image_matches,
        "sample_dataset_hash_matches": dataset_matches,
        "image_cache_sha256": integrity.get("image_cache_sha256"),
    }


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def run(args: argparse.Namespace) -> int:
    dataset = args.dataset.resolve()
    raw_root = args.raw_root.resolve()
    if not (dataset / "data.yaml").is_file():
        raise VerificationError(f"{dataset} is not a prepared dataset")

    classes = load_classes(args.classes)
    class_names = list(classes["names"])
    duplicates = load_json(args.duplicate_groups)
    audit = load_json(args.policy_audit)
    near_groups = duplicates["near_groups_threshold_3"]
    exact_groups = duplicates.get("exact_groups", [])
    cache_doc = load_json(args.hash_cache)
    cache = cache_doc.get("entries", cache_doc)

    rows, manifest_path = load_manifest(dataset)
    report = load_json(dataset / "reports" / "dataset_report.json")
    policy_applied = report["policy"]["applied"]

    checks: dict[str, dict] = {}
    failures: list[str] = []

    def run_check(name: str, function) -> None:
        try:
            details = function()
            checks[name] = {"status": "PASS", "details": details}
            print(f"  [PASS] {name}", flush=True)
        except Exception as exc:  # noqa: BLE001
            checks[name] = {"status": "FAIL", "error": str(exc)}
            failures.append(f"{name}: {exc}")
            print(f"  [FAIL] {name}: {exc}", flush=True)

    print(f"verifying {dataset}", flush=True)
    run_check("classes_config", lambda: check_classes(dataset, args.classes))
    run_check("image_label_correspondence", lambda: check_correspondence(dataset, rows))
    label_details = None
    try:
        label_details = check_labels(dataset, rows, class_names)
        checks["yolo_format_and_boxes"] = {"status": "PASS", "details": label_details}
        print("  [PASS] yolo_format_and_boxes", flush=True)
    except Exception as exc:  # noqa: BLE001
        checks["yolo_format_and_boxes"] = {"status": "FAIL", "error": str(exc)}
        failures.append(f"yolo_format_and_boxes: {exc}")
        print(f"  [FAIL] yolo_format_and_boxes: {exc}", flush=True)

    print("  re-scanning source annotations", flush=True)
    rescan = rescan_annotations(raw_root, cache)
    run_check(
        "conversion_and_exclusions",
        lambda: check_reconciliation(
            dataset, rescan, rows, policy_applied, near_groups, cache, audit
        ),
    )
    run_check(
        "duplicate_leakage",
        lambda: check_duplicates(dataset, rows, duplicates, near_groups, exact_groups),
    )
    run_check(
        "split_manifest_reconciliation",
        lambda: check_split_manifest(dataset, rows, class_names),
    )
    run_check(
        "determinism",
        lambda: check_determinism(
            dataset,
            rows,
            rescan,
            near_groups,
            exact_groups,
            cache,
            args.seed,
            args.repro_dir,
        ),
    )
    run_check(
        "original_data_integrity",
        lambda: check_original_integrity(dataset, rescan, cache, args.sample_size),
    )

    verdict = "PASS" if not failures else "FAIL"
    payload = {
        "stage": "S4-T3B",
        "generated_utc": utc_now(),
        "dataset": str(dataset),
        "manifest": str(manifest_path),
        "policy_applied": policy_applied,
        "verdict": verdict,
        "checks": checks,
        "failures": failures,
        "summary": {
            "checks_run": len(checks),
            "checks_passed": sum(1 for check in checks.values() if check["status"] == "PASS"),
            "checks_failed": len(failures),
            "rows": len(rows),
            "policy_requested": report["policy"]["requested"],
            "policy_applied": policy_applied,
            "v2_gate_closed": report["policy"]["v2_gate"]["closed"],
            "fallback_reason": report["policy"]["fallback_reason"],
        },
    }
    write_json(dataset / "reports" / "verification.json", payload)

    print()
    print(f"verdict: {verdict}")
    for name, check in checks.items():
        print(f"  {check['status']:<4} {name}")
    if failures:
        print("\nfailures:")
        for failure in failures:
            print(f"  - {failure}")
    print(f"\nreport: {dataset / 'reports' / 'verification.json'}")
    return 0 if verdict == "PASS" else 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--classes", type=Path, default=CLASSES_DEFAULT)
    parser.add_argument("--duplicate-groups", type=Path, default=DEFAULT_DUPLICATES)
    parser.add_argument("--hash-cache", type=Path, default=DEFAULT_HASH_CACHE)
    parser.add_argument("--policy-audit", type=Path, default=DEFAULT_POLICY_AUDIT)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--sample-size", type=int, default=250)
    parser.add_argument(
        "--repro-dir",
        type=Path,
        help="second independent pipeline output to compare for determinism",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        return run(parse_args(argv))
    except VerificationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"UNEXPECTED ERROR: {exc}", file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
