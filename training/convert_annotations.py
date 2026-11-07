#!/usr/bin/env python3
"""Pascal VOC -> YOLO conversion for RoadVision AI (TDD v1.1 section 4.3).

This module is the single source of truth for the four-class mapping and for
the annotation validation rules used by the S4-T3B pipeline.  It is importable
by ``prepare_dataset.py`` and ``verify_dataset.py`` and also provides a small
CLI for converting one XML file.

Rules implemented (identical to ``training/audit_dataset_policy.py`` so the
conversion reconciles with the S4-T3A audit):

* exact string match against ``{"D00": 0, "D10": 1, "D20": 2, "D40": 3}``;
* ``xmin``/``xmax`` and ``ymin``/``ymax`` swapped values are reordered;
* boxes more than ``TOL_PX`` outside the real image are excluded;
* boxes within tolerance are clipped to the image;
* zero-area boxes (< 1 px wide or high) are excluded;
* non-numeric boxes and objects without a name are excluded;
* out-of-scope codes are never relabelled as target classes.

The converter only reads source files.  Labels are written to a caller-supplied
path, never next to the source annotation.

Usage
-----
Convert one XML and print a JSON summary::

    .\\.venv\\Scripts\\python.exe training\\convert_annotations.py ^
        --xml data\\raw\\RDD2022\\India\\train\\annotations\\India_000001.xml ^
        --image data\\raw\\RDD2022\\India\\train\\images\\India_000001.jpg

Write the label as well::

    .\\.venv\\Scripts\\python.exe training\\convert_annotations.py --xml ... --image ... --out label.txt

Validate the class configuration only::

    .\\.venv\\Scripts\\python.exe training\\convert_annotations.py --check-classes
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DEFAULT = PROJECT_ROOT / "data" / "raw" / "RDD2022"
CLASSES_DEFAULT = PROJECT_ROOT / "training" / "classes.json"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}

# TDD v1.1 section 4.3 - fixed mapping.  Exact string equality only.
CODE_TO_ID = {"D00": 0, "D10": 1, "D20": 2, "D40": 3}
TARGET_CODES = tuple(CODE_TO_ID)
TOL_PX = 2.0

# Every code observed in RDD2022 (S4-T2 inspection / S4-T3A audit).
KNOWN_CODES = {
    "D00", "D10", "D20", "D40",
    "D01", "D0w0", "D11", "D43", "D44", "D50",
    "Repair", "Block crack",
}


class AnnotationError(RuntimeError):
    """Raised when an XML cannot be parsed or lacks usable image dimensions."""


@dataclass(frozen=True)
class KeptBox:
    """A validated, clipped target box in pixel coordinates."""

    class_id: int
    code: str
    x1: float
    y1: float
    x2: float
    y2: float
    clipped: bool


@dataclass
class ParsedAnnotation:
    """Result of parsing one Pascal VOC XML file."""

    xml_path: Path
    image_size: tuple[int, int] | None
    xml_size: tuple[int, int] | None
    category: str
    objects_total: int
    target_objects: int
    target_retained: int
    oos_objects: int
    codes: tuple[str, ...]
    kept_by_code: dict[str, int]
    kept_boxes: list[KeptBox] = field(default_factory=list)
    exclusions: list[dict] = field(default_factory=list)
    clipped_objects: int = 0
    warnings: list[str] = field(default_factory=list)

    @property
    def is_pool_a(self) -> bool:
        """True when the image has at least one retained target box."""
        return self.target_retained >= 1


def load_classes(path: Path | str = CLASSES_DEFAULT) -> dict:
    """Load and validate ``training/classes.json``.

    The file is the project-facing class contract.  The hard-coded mapping in
    this module is the executable contract; the two must agree exactly.
    """
    path = Path(path)
    with path.open(encoding="utf-8") as fh:
        config = json.load(fh)

    names = config.get("names")
    code_to_id = config.get("code_to_id")
    if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
        raise ValueError(f"{path}: 'names' must be a list of strings")
    if not isinstance(code_to_id, dict):
        raise ValueError(f"{path}: 'code_to_id' must be an object")
    if len(names) != len(set(names)):
        raise ValueError(f"{path}: duplicate class names: {names}")
    expected = {name: idx for idx, name in enumerate(names)}
    if code_to_id != expected:
        raise ValueError(
            f"{path}: code_to_id {code_to_id} does not match names {names}"
        )
    if code_to_id != CODE_TO_ID:
        raise ValueError(
            f"{path}: class mapping {code_to_id} disagrees with the TDD mapping {CODE_TO_ID}"
        )
    return config


def rel_key(path: Path, root: Path) -> str:
    """Return a dataset-relative POSIX path."""
    return path.relative_to(root).as_posix()


def classify_path(path: Path, root: Path) -> tuple[str, str]:
    """Return ``(country, official_split)`` for a path under ``root``."""
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


def iter_dataset_files(root: Path) -> tuple[list[Path], list[Path]]:
    """Return sorted ``(image_paths, xml_paths)`` under ``root``."""
    files = [p for p in root.rglob("*") if p.is_file()]
    images = sorted(p for p in files if p.suffix.lower() in IMAGE_EXTS)
    xmls = sorted(p for p in files if p.suffix.lower() == ".xml")
    return images, xmls


def build_image_index(
    image_paths: list[Path], root: Path
) -> dict[tuple[str, str, str], str]:
    """Map ``(country, split, lower-case stem)`` to a relative image path."""
    index: dict[tuple[str, str, str], str] = {}
    for path in image_paths:
        country, split = classify_path(path, root)
        key = (country, split, path.stem.lower())
        if key in index:
            raise AnnotationError(
                "duplicate image stem for key "
                f"{key}: {index[key]} and {rel_key(path, root)}"
            )
        index[key] = rel_key(path, root)
    return index


def _read_xml_size(root: ET.Element) -> tuple[int, int] | None:
    size = root.find("size")
    if size is None:
        return None
    try:
        width = int(float(size.findtext("width")))
        height = int(float(size.findtext("height")))
    except (TypeError, ValueError):
        return None
    if width <= 0 or height <= 0:
        return None
    return width, height


def parse_voc(
    xml_path: Path | str,
    image_size: tuple[int, int] | None = None,
) -> ParsedAnnotation:
    """Parse one Pascal VOC XML file and apply the TDD validation rules.

    ``image_size`` must be the real ``(width, height)`` of the image.  When it
    is ``None`` the XML ``<size>`` element is used, matching the audit's
    fallback path.  If neither is available the annotation is rejected.
    """
    xml_path = Path(xml_path)
    try:
        root = ET.parse(xml_path).getroot()
    except (ET.ParseError, OSError) as exc:
        raise AnnotationError(f"cannot parse {xml_path}: {exc}") from exc

    xml_size = _read_xml_size(root)
    true_wh = image_size or xml_size
    warnings: list[str] = []
    if image_size is not None and xml_size is not None and image_size != xml_size:
        warnings.append(
            f"xml size {xml_size[0]}x{xml_size[1]} != image size "
            f"{image_size[0]}x{image_size[1]}"
        )

    objects = list(root.iter("object"))
    codes: set[str] = set()
    kept_by_code: dict[str, int] = {}
    kept_boxes: list[KeptBox] = []
    exclusions: list[dict] = []
    n_target = 0
    n_target_kept = 0
    n_oos = 0
    clipped_objects = 0

    for index, obj in enumerate(objects):
        raw_name = obj.findtext("name")
        code = (raw_name or "").strip()
        if not code:
            exclusions.append(
                {
                    "object_index": index,
                    "code": "",
                    "reason": "missing_name",
                    "is_target": False,
                }
            )
            continue

        is_target = code in CODE_TO_ID
        if is_target:
            n_target += 1
        else:
            n_oos += 1
        codes.add(code)

        box = obj.find("bndbox")
        try:
            x1 = float(box.findtext("xmin"))
            y1 = float(box.findtext("ymin"))
            x2 = float(box.findtext("xmax"))
            y2 = float(box.findtext("ymax"))
        except (AttributeError, TypeError, ValueError):
            exclusions.append(
                {
                    "object_index": index,
                    "code": code,
                    "reason": "out_of_scope_class" if not is_target else "bad_box_values",
                    "is_target": is_target,
                }
            )
            continue

        x1, x2 = sorted((x1, x2))
        y1, y2 = sorted((y1, y2))

        if true_wh is None:
            exclusions.append(
                {
                    "object_index": index,
                    "code": code,
                    "reason": "missing_image_size",
                    "is_target": is_target,
                }
            )
            continue

        width, height = true_wh
        if x1 < -TOL_PX or y1 < -TOL_PX or x2 > width + TOL_PX or y2 > height + TOL_PX:
            exclusions.append(
                {
                    "object_index": index,
                    "code": code,
                    "reason": "out_of_scope_class" if not is_target else "out_of_bounds",
                    "is_target": is_target,
                }
            )
            continue

        cx1 = max(0.0, x1)
        cy1 = max(0.0, y1)
        cx2 = min(float(width), x2)
        cy2 = min(float(height), y2)
        clipped = (cx1, cy1, cx2, cy2) != (x1, y1, x2, y2)
        if clipped:
            clipped_objects += 1

        if cx2 - cx1 < 1 or cy2 - cy1 < 1:
            exclusions.append(
                {
                    "object_index": index,
                    "code": code,
                    "reason": "out_of_scope_class" if not is_target else "degenerate",
                    "is_target": is_target,
                }
            )
            continue

        if not is_target:
            # Valid geometry, but the class is outside the four-class contract.
            exclusions.append(
                {
                    "object_index": index,
                    "code": code,
                    "reason": "out_of_scope_class",
                    "is_target": False,
                }
            )
            continue

        n_target_kept += 1
        kept_by_code[code] = kept_by_code.get(code, 0) + 1
        kept_boxes.append(
            KeptBox(
                class_id=CODE_TO_ID[code],
                code=code,
                x1=cx1,
                y1=cy1,
                x2=cx2,
                y2=cy2,
                clipped=clipped,
            )
        )

    if not objects:
        category = "empty_xml"
    elif n_target and n_oos:
        category = "mixed_target_oos"
    elif n_target:
        category = "only_target"
    else:
        category = "only_oos"

    return ParsedAnnotation(
        xml_path=xml_path,
        image_size=true_wh,
        xml_size=xml_size,
        category=category,
        objects_total=len(objects),
        target_objects=n_target,
        target_retained=n_target_kept,
        oos_objects=n_oos,
        codes=tuple(sorted(codes)),
        kept_by_code=dict(sorted(kept_by_code.items())),
        kept_boxes=kept_boxes,
        exclusions=exclusions,
        clipped_objects=clipped_objects,
        warnings=warnings,
    )


def to_yolo_lines(parsed: ParsedAnnotation) -> list[str]:
    """Return YOLO label lines (``class_id xc yc w h``) for retained boxes."""
    if parsed.image_size is None:
        raise AnnotationError(f"{parsed.xml_path}: no image size available")
    width, height = parsed.image_size
    lines: list[str] = []
    for box in parsed.kept_boxes:
        x_center = (box.x1 + box.x2) / 2.0 / width
        y_center = (box.y1 + box.y2) / 2.0 / height
        box_width = (box.x2 - box.x1) / width
        box_height = (box.y2 - box.y1) / height
        lines.append(
            f"{box.class_id} {x_center:.6f} {y_center:.6f} "
            f"{box_width:.6f} {box_height:.6f}"
        )
    return lines


def label_text(parsed: ParsedAnnotation) -> str:
    """Return the complete label file text (empty string for background)."""
    lines = to_yolo_lines(parsed)
    return "".join(f"{line}\n" for line in lines)


def write_label(path: Path | str, text: str) -> None:
    """Write a label file with LF line endings and UTF-8 encoding."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def annotation_summary(parsed: ParsedAnnotation) -> dict:
    """Return a JSON-safe summary of one parsed annotation."""
    return {
        "xml": str(parsed.xml_path),
        "image_size": list(parsed.image_size) if parsed.image_size else None,
        "xml_size": list(parsed.xml_size) if parsed.xml_size else None,
        "category": parsed.category,
        "objects_total": parsed.objects_total,
        "target_objects": parsed.target_objects,
        "target_retained": parsed.target_retained,
        "oos_objects": parsed.oos_objects,
        "codes": list(parsed.codes),
        "kept_by_code": parsed.kept_by_code,
        "kept_boxes": len(parsed.kept_boxes),
        "clipped_objects": parsed.clipped_objects,
        "exclusions": parsed.exclusions,
        "warnings": parsed.warnings,
        "yolo_lines": to_yolo_lines(parsed),
    }


def _image_size_from_file(path: Path) -> tuple[int, int]:
    try:
        import cv2
    except ImportError as exc:  # pragma: no cover - opencv is a project dependency
        raise AnnotationError("opencv is required to read image dimensions") from exc
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise AnnotationError(f"cannot read image: {path}")
    height, width = image.shape[:2]
    return int(width), int(height)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xml", type=Path, help="Pascal VOC XML file to parse")
    parser.add_argument("--image", type=Path, help="matching image (for true dimensions)")
    parser.add_argument("--out", type=Path, help="optional YOLO label output path")
    parser.add_argument("--classes", type=Path, default=CLASSES_DEFAULT)
    parser.add_argument(
        "--check-classes",
        action="store_true",
        help="validate training/classes.json and exit",
    )
    args = parser.parse_args(argv)

    try:
        config = load_classes(args.classes)
        if args.check_classes:
            print(json.dumps({"classes": config, "status": "valid"}, indent=2))
            return 0
        if not args.xml:
            parser.error("--xml is required unless --check-classes is used")

        image_size = None
        if args.image:
            image_size = _image_size_from_file(args.image)
        parsed = parse_voc(args.xml, image_size=image_size)
        summary = annotation_summary(parsed)
        if args.out:
            write_label(args.out, label_text(parsed))
            summary["written"] = str(args.out)
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0
    except (AnnotationError, ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
