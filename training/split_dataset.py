#!/usr/bin/env python3
"""Deterministic, duplicate-aware split generation for RoadVision AI (TDD v1.1 section 4.4).

The implementation deliberately mirrors the S4-T3A split simulation so that the
generated split reconciles with the audit:

* duplicate groups come from ``data/reports/audit/duplicate_groups.json``
  (64-bit dHash, Hamming <= 3, transitive closure, no bucket cap);
* every member of a near-duplicate group that is in the policy pool is placed
  in one split - groups are never broken;
* ``StratifiedGroupKFold(n_splits=10, shuffle=True, random_state=42)``;
* ``folds[0]`` is test, ``folds[1]`` is validation, the remaining folds are
  training (approximately 80 / 10 / 10);
* stratification label is the rarest retained class present in the group.

Group order and pool order are preserved exactly as the audit produced them, so
seed 42 reproduces the audit's 19,017 / 2,401 / 2,349 image split.

CLI (dry run against a per-image JSON produced by the pipeline)::

    .\\.venv\\Scripts\\python.exe training\\split_dataset.py ^
        --per-image dataset\\reports\\per_image.json ^
        --duplicate-groups data\\reports\\audit\\duplicate_groups.json ^
        --out split_preview.json
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SEED = 42
DEFAULT_N_SPLITS = 10
DEFAULT_RATIO = (0.8, 0.1, 0.1)
SPLIT_ORDER = ("train", "val", "test")


def pct(part: float, total: float, digits: int = 2) -> float:
    return round(100.0 * part / total, digits) if total else 0.0


def build_pool_groups(
    pool: list[str],
    near_groups: list[list[str]],
    exact_groups: list[list[str]] | None = None,
) -> tuple[list[list[str]], dict[str, int]]:
    """Group the policy pool exactly like the S4-T3A audit.

    Every pool member of a near-duplicate group is kept in the same group.  A
    group whose members are all excluded disappears; an image outside every
    group becomes a singleton.  Order is preserved so seed 42 is reproducible.
    """
    pool_set = set(pool)
    group_of: dict[str, int] = {}
    groups: list[list[str]] = []

    for members in near_groups:
        kept = [member for member in members if member in pool_set]
        if not kept:
            continue
        gid = len(groups)
        groups.append(kept)
        for member in kept:
            group_of[member] = gid

    for path in pool:
        if path not in group_of:
            group_of[path] = len(groups)
            groups.append([path])

    if exact_groups:
        for exact in exact_groups:
            present = [member for member in exact if member in pool_set]
            gids = {group_of[member] for member in present}
            if len(gids) > 1:
                raise ValueError(
                    "exact-duplicate files are not in one near-duplicate group: "
                    f"{sorted(gids)} for {exact}"
                )

    if len(group_of) != len(pool):
        missing = sorted(set(pool) - set(group_of))
        raise ValueError(f"{len(missing)} pool images were not assigned a group")

    return groups, group_of


@dataclass
class SplitResult:
    seed: int
    n_splits: int
    pool: list[str]
    groups: list[list[str]]
    labels: list[str]
    image_split: dict[str, str]
    group_split: dict[int, str]
    stats: dict
    per_class_balance: dict
    group_crossing_violations: int
    exact_hash_crossing_violations: int
    exact_hash_crossings: list[dict] = field(default_factory=list)


def assign_splits(
    per_image: dict[str, dict],
    pool: list[str],
    near_groups: list[list[str]],
    seed: int = DEFAULT_SEED,
    n_splits: int = DEFAULT_N_SPLITS,
    sha_of: dict[str, str] | None = None,
    exact_groups: list[list[str]] | None = None,
) -> SplitResult:
    """Assign every pool image to train/val/test with group-level splitting."""
    from sklearn.model_selection import StratifiedGroupKFold

    sha_of = sha_of or {}
    groups, group_of = build_pool_groups(pool, near_groups, exact_groups)

    def retained_codes(path: str) -> list[str]:
        return sorted(per_image[path].get("kept_by_code", {}))

    image_counts: collections.Counter = collections.Counter()
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
        labels.append(min(present, key=lambda code: (image_counts.get(code, 0), code)))

    label_index = {label: index for index, label in enumerate(sorted(set(labels)))}
    y = np.array([label_index[label] for label in labels])
    group_ids = np.array([str(index) for index in range(len(groups))])

    splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    folds = [set(test) for _, test in splitter.split(np.zeros(len(groups)), y, group_ids)]

    group_split: dict[int, str] = {}
    for gid in range(len(groups)):
        if gid in folds[0]:
            group_split[gid] = "test"
        elif gid in folds[1]:
            group_split[gid] = "val"
        else:
            group_split[gid] = "train"

    buckets = {
        split: {
            "groups": 0,
            "images": 0,
            "objects": 0,
            "class_images": collections.Counter(),
            "class_objects": collections.Counter(),
            "countries": collections.Counter(),
            "official_splits": collections.Counter(),
        }
        for split in SPLIT_ORDER
    }

    image_split: dict[str, str] = {}
    for gid, members in enumerate(groups):
        split_name = group_split[gid]
        bucket = buckets[split_name]
        bucket["groups"] += 1
        for path in members:
            info = per_image[path]
            bucket["images"] += 1
            bucket["objects"] += int(info.get("target_retained", 0))
            bucket["countries"][info["country"]] += 1
            bucket["official_splits"][info.get("official_split", "<unknown>")] += 1
            image_split[path] = split_name
            for code, count in info.get("kept_by_code", {}).items():
                bucket["class_images"][code] += 1
                bucket["class_objects"][code] += count

    totals_images = sum(bucket["images"] for bucket in buckets.values())
    totals_objects = sum(bucket["objects"] for bucket in buckets.values())

    per_class_balance: dict[str, dict] = {}
    for code in ("D00", "D10", "D20", "D40"):
        global_images = sum(buckets[split]["class_images"][code] for split in SPLIT_ORDER)
        global_objects = sum(buckets[split]["class_objects"][code] for split in SPLIT_ORDER)
        row: dict[str, dict] = {}
        for split_name in SPLIT_ORDER:
            count = buckets[split_name]["class_images"][code]
            objects = buckets[split_name]["class_objects"][code]
            row[split_name] = {
                "images": count,
                "objects": objects,
                "share_of_split_pct": pct(count, buckets[split_name]["images"]),
                "global_share_pct": pct(global_images, totals_images),
                "deviation_pp": round(
                    pct(count, buckets[split_name]["images"])
                    - pct(global_images, totals_images),
                    2,
                ),
                "object_share_of_class_pct": pct(objects, global_objects),
            }
        per_class_balance[code] = row

    # Group leakage: every group must map to exactly one split.
    seen_group: dict[int, str] = {}
    group_violations = 0
    violation_examples: list[dict] = []
    for path, split_name in image_split.items():
        gid = group_of[path]
        previous = seen_group.setdefault(gid, split_name)
        if previous != split_name:
            group_violations += 1
            if len(violation_examples) < 25:
                violation_examples.append({"group_id": gid, "splits": sorted({previous, split_name})})

    # Exact-file-hash leakage: a SHA-256 must not appear in two splits.
    hash_splits: dict[str, set[str]] = collections.defaultdict(set)
    for path, split_name in image_split.items():
        hash_splits[sha_of.get(path, path)].add(split_name)
    exact_crossings = [
        {"sha256": digest, "splits": sorted(splits)}
        for digest, splits in sorted(hash_splits.items())
        if len(splits) > 1
    ]

    stats = {
        "seed": seed,
        "n_splits": n_splits,
        "target_ratio": {"train": 0.8, "val": 0.1, "test": 0.1},
        "pool_images": len(pool),
        "pool_groups": len(groups),
        "group_size_distribution": dict(
            sorted(collections.Counter(len(group) for group in groups).items())
        ),
        "stratification_labels": dict(sorted(collections.Counter(labels).items())),
        "totals": {
            "images": totals_images,
            "retained_objects": totals_objects,
        },
        "splits": {
            split: {
                "groups": buckets[split]["groups"],
                "images": buckets[split]["images"],
                "retained_objects": buckets[split]["objects"],
                "images_pct": pct(buckets[split]["images"], totals_images),
                "objects_pct": pct(buckets[split]["objects"], totals_objects),
                "class_images": dict(sorted(buckets[split]["class_images"].items())),
                "class_objects": dict(sorted(buckets[split]["class_objects"].items())),
                "countries": dict(
                    sorted(buckets[split]["countries"].items(), key=lambda kv: (-kv[1], kv[0]))
                ),
                "official_splits": dict(sorted(buckets[split]["official_splits"].items())),
            }
            for split in SPLIT_ORDER
        },
        "per_class_balance": per_class_balance,
        "group_crossing_violations": group_violations,
        "group_crossing_examples": violation_examples,
        "exact_hash_crossing_violations": len(exact_crossings),
        "exact_hash_crossings": exact_crossings,
    }

    return SplitResult(
        seed=seed,
        n_splits=n_splits,
        pool=list(pool),
        groups=groups,
        labels=labels,
        image_split=image_split,
        group_split=group_split,
        stats=stats,
        per_class_balance=per_class_balance,
        group_crossing_violations=group_violations,
        exact_hash_crossing_violations=len(exact_crossings),
        exact_hash_crossings=exact_crossings,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-image", type=Path, required=True)
    parser.add_argument(
        "--duplicate-groups",
        type=Path,
        default=PROJECT_ROOT / "data" / "reports" / "audit" / "duplicate_groups.json",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    try:
        with args.per_image.open(encoding="utf-8") as fh:
            per_image = json.load(fh)
        with args.duplicate_groups.open(encoding="utf-8") as fh:
            duplicates = json.load(fh)
        pool = sorted(per_image)
        result = assign_splits(
            per_image,
            pool,
            duplicates["near_groups_threshold_3"],
            seed=args.seed,
            exact_groups=duplicates.get("exact_groups", []),
        )
        payload = dict(result.stats)
        payload["image_split"] = result.image_split
        text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(text, encoding="utf-8", newline="\n")
            print(f"wrote {args.out}")
        else:
            print(text)
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI reports one clear error
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
