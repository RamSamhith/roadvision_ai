#!/usr/bin/env python3
"""Regenerate S4-T3A inspection artifacts from existing audit records.

This tool does NOT re-run duplicate detection.  It treats the completed audit
artifacts as the source of truth:

  * ``data/reports/audit/duplicate_groups.json``   group membership
  * ``data/reports/audit/policy_audit.json``       cross-country group ids
  * ``data/reports/audit/contact_sheets/ambiguous_groups_report.json``
                                                    recorded group statistics
                                                    and heuristic verdicts

It regenerates contact sheets for every inspected group (by default only the
missing ones, so existing evidence is preserved) and rewrites
``ambiguous_groups_report.json`` with contact-sheet paths and an explicit
visual-inspection status.  Visual verdicts are never invented: groups without
a recorded visual conclusion are marked ``"not inspected"``.

Usage
-----
    .\\.venv\\Scripts\\python.exe training\\make_inspection_artifacts.py
    .\\.venv\\Scripts\\python.exe training\\make_inspection_artifacts.py --check
    .\\.venv\\Scripts\\python.exe training\\make_inspection_artifacts.py --force

The default run only writes sheets that are absent.  ``--force`` rebuilds all
selected sheets.  ``--check`` validates the current artifacts and writes
nothing.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

# Existing contact-sheet convention (measured from the S4-T3A artifacts).
TILE = 150
COLUMNS = 10
MAX_TILES = 40
JPEG_QUALITY = 95

# Groups with a recorded visual conclusion in
# docs/project/ROADVISION_S4_T3A_POLICY_AUDIT.md section 4.10:
#   - groups 54 and 52: genuine single-route dashcam sequences
#   - groups 418, 404, 278, 130, 240, 0, 30, 263, 36, 473, 524, 525, 526:
#     hash-degenerate pavement clusters
#   - group 447: coherent visual duplicates (verdict recorded in the JSON)
# Every other selected group has no recorded visual verdict and is marked
# "not inspected".
VISUALLY_INSPECTED = {
    54, 52,
    418, 404, 278, 130, 240, 0, 30, 263, 36, 473, 524, 525, 526,
    447,
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_json(path: Path):
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def selected_group_ids(policy_audit: dict, groups: list[list[str]]) -> list[int]:
    """Groups with >= 8 images plus every cross-country group (29 total)."""
    ids = {i for i, members in enumerate(groups) if len(members) >= 8}
    cross = policy_audit["part_b"]["near_cross_country_groups"]
    ids.update(int(g["group_id"]) for g in cross)
    return sorted(ids)


def sheet_dimensions(n_members: int) -> tuple[int, int]:
    rows = max(1, (min(n_members, MAX_TILES) + COLUMNS - 1) // COLUMNS)
    return COLUMNS * TILE, rows * TILE


def build_sheet(members: list[Path], out_path: Path) -> tuple[int, int]:
    width, height = sheet_dimensions(len(members))
    canvas = np.zeros((height, width, 3), dtype=np.uint8)
    for idx, image_path in enumerate(members[:MAX_TILES]):
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            raise RuntimeError(f"cannot read image: {image_path}")
        thumb = cv2.resize(image, (TILE, TILE), interpolation=cv2.INTER_AREA)
        row, col = divmod(idx, COLUMNS)
        canvas[row * TILE:(row + 1) * TILE, col * TILE:(col + 1) * TILE] = thumb
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(out_path), canvas, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]):
        raise RuntimeError(f"failed to write contact sheet: {out_path}")
    return width, height


def verify_sheet(path: Path, expected: tuple[int, int]) -> None:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f"contact sheet does not open: {path}")
    if (image.shape[1], image.shape[0]) != expected:
        raise RuntimeError(
            f"contact sheet has wrong size: {path} "
            f"{image.shape[1]}x{image.shape[0]}, expected {expected[0]}x{expected[1]}"
        )
    if not image.any():
        raise RuntimeError(f"contact sheet is blank: {path}")


def run(args: argparse.Namespace) -> int:
    root = repo_root()
    duplicate_groups_path = Path(args.duplicate_groups).resolve()
    policy_audit_path = Path(args.policy_audit).resolve()
    report_path = Path(args.report).resolve()
    raw_root = Path(args.raw_root).resolve()
    out_dir = Path(args.out_dir).resolve()

    groups = load_json(duplicate_groups_path)["near_groups_threshold_3"]
    policy_audit = load_json(policy_audit_path)
    recorded_list = load_json(report_path)
    recorded = {int(item["group_id"]): item for item in recorded_list}

    selected = set(selected_group_ids(policy_audit, groups))
    if len(selected) != 29:
        raise RuntimeError(
            f"expected 29 inspected groups, found {len(selected)}: {sorted(selected)}"
        )
    # Preserve the recorded order; append any newly selected group at the end.
    recorded_order = [int(item["group_id"]) for item in recorded_list]
    ids = [gid for gid in recorded_order if gid in selected]
    ids += [gid for gid in sorted(selected) if gid not in set(recorded_order)]
    if len(ids) != 29:
        raise RuntimeError(f"expected 29 report entries, found {len(ids)}: {ids}")

    missing_members: list[str] = []
    written: list[Path] = []
    skipped: list[Path] = []

    for group_id in ids:
        members = [raw_root / rel for rel in groups[group_id]]
        for member in members:
            if not member.is_file():
                missing_members.append(str(member))
        if missing_members:
            continue

        expected = sheet_dimensions(len(members))
        out_path = out_dir / f"group_{group_id:04d}_size{len(members)}.jpg"

        if args.check:
            verify_sheet(out_path, expected)
            skipped.append(out_path)
        elif args.force or not out_path.is_file():
            size = build_sheet(members, out_path)
            if size != expected:
                raise RuntimeError(f"generator produced wrong size for group {group_id}")
            verify_sheet(out_path, expected)
            written.append(out_path)
        else:
            verify_sheet(out_path, expected)
            skipped.append(out_path)

    if missing_members:
        raise RuntimeError(
            "missing source images:\n" + "\n".join(missing_members[:20])
        )

    if args.check:
        print(f"validated {len(skipped)} contact sheets; no files written")
        return 0

    # Rewrite the report, preserving every recorded statistic and verdict.
    updated = []
    for group_id in ids:
        item = dict(recorded[group_id])
        members = groups[group_id]
        item["group_id"] = group_id
        item["size"] = len(members)
        item["contact_sheet"] = str(
            out_dir / f"group_{group_id:04d}_size{len(members)}.jpg"
        )
        item["visual_inspection"] = (
            "inspected" if group_id in VISUALLY_INSPECTED else "not inspected"
        )
        updated.append(item)

    report_path.write_text(
        json.dumps(updated, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"groups selected: {len(ids)}")
    print(f"sheets written: {len(written)}")
    print(f"sheets preserved/validated: {len(skipped)}")
    print(f"report rewritten: {report_path}")
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    root = repo_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--duplicate-groups",
        default=str(root / "data" / "reports" / "audit" / "duplicate_groups.json"),
    )
    parser.add_argument(
        "--policy-audit",
        default=str(root / "data" / "reports" / "audit" / "policy_audit.json"),
    )
    parser.add_argument(
        "--report",
        default=str(
            root / "data" / "reports" / "audit" / "contact_sheets"
            / "ambiguous_groups_report.json"
        ),
    )
    parser.add_argument(
        "--raw-root",
        default=str(root / "data" / "raw" / "RDD2022"),
    )
    parser.add_argument(
        "--out-dir",
        default=str(root / "data" / "reports" / "audit" / "contact_sheets"),
    )
    parser.add_argument("--force", action="store_true", help="rebuild existing sheets")
    parser.add_argument("--check", action="store_true", help="validate only, write nothing")
    return parser.parse_args(argv)


if __name__ == "__main__":
    try:
        raise SystemExit(run(parse_args(sys.argv[1:])))
    except Exception as exc:  # noqa: BLE001 - CLI tool reports a single clear error
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
