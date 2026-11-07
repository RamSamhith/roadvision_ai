"""RoadVision AI — Bounding Box and Detection Annotation Engine (S5-M1).

Draws high-contrast, professional bounding boxes, class labels, and confidence tags
on road images without mutating original inputs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import cv2
import numpy as np

from .classes import CODE_TO_LABEL, ID_TO_CODE
from .types import Detection, DetectionResult

# -----------------------------------------------------------------------------
# Color Palette (BGR format for OpenCV)
# -----------------------------------------------------------------------------
CLASS_COLORS_BGR: Dict[str, Tuple[int, int, int]] = {
    "D00": (235, 160, 52),   # Sky Blue / Cyan (Longitudinal crack)
    "D10": (50, 205, 50),     # Lime Green (Transverse crack)
    "D20": (0, 140, 255),     # Deep Orange / Amber (Alligator crack)
    "D40": (34, 34, 220),     # Crimson Red (Pothole)
}
DEFAULT_COLOR_BGR: Tuple[int, int, int] = (200, 200, 200)


def get_class_color(class_identifier: Union[str, int]) -> Tuple[int, int, int]:
    """Retrieve BGR color tuple for a class code or ID."""
    if isinstance(class_identifier, int):
        code = ID_TO_CODE.get(class_identifier, "")
    else:
        code = str(class_identifier)
    return CLASS_COLORS_BGR.get(code, DEFAULT_COLOR_BGR)


def annotate_image(
    image: np.ndarray,
    detections: Union[List[Detection], DetectionResult],
    show_labels: bool = True,
    show_confidence: bool = True,
    font_scale_multiplier: float = 1.0,
    thickness_multiplier: float = 1.0,
) -> np.ndarray:
    """Draw bounding boxes and class tags on an image.

    Args:
        image: Original BGR image (numpy ndarray).
        detections: List of Detection objects or a DetectionResult.
        show_labels: Whether to render class text tags.
        show_confidence: Whether to include confidence percentages in tags.
        font_scale_multiplier: Fine-tuning scalar for font size.
        thickness_multiplier: Fine-tuning scalar for line width.

    Returns:
        New np.ndarray with annotations drawn (input image is NOT modified).
    """
    if image is None or image.size == 0:
        raise ValueError("Cannot annotate empty or None image")

    # Always copy to prevent mutating the original input matrix
    annotated = image.copy()
    h, w = annotated.shape[:2]

    # Dynamic scaling based on image dimensions
    base_dim = max(h, w)
    thickness = max(1, int(round((base_dim / 700.0) * thickness_multiplier)))
    font_scale = max(0.4, (base_dim / 1400.0) * font_scale_multiplier)
    font_thickness = max(1, int(round(thickness * 0.75)))

    det_list: List[Detection] = (
        detections.detections if isinstance(detections, DetectionResult) else detections
    )

    for det in det_list:
        code = det.class_name
        color = get_class_color(code)
        x1, y1, x2, y2 = [int(round(v)) for v in det.box]

        # Clamp box coordinates to image boundaries
        x1 = max(0, min(x1, w - 1))
        y1 = max(0, min(y1, h - 1))
        x2 = max(0, min(x2, w - 1))
        y2 = max(0, min(y2, h - 1))

        # Draw bounding rectangle
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, thickness)

        if not show_labels:
            continue

        # Compose label text
        display_label = det.label or CODE_TO_LABEL.get(code, code)
        text_parts = [code]
        if show_confidence:
            text_parts.append(f"{det.confidence * 100:.1f}%")
        label_text = " | ".join(text_parts)

        # Measure text size for background pill
        (txt_w, txt_h), baseline = cv2.getTextSize(
            label_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, font_thickness
        )
        pad = max(2, int(round(thickness * 1.5)))

        # Position pill above box; if too close to top, position inside
        pill_y2 = y1
        pill_y1 = y1 - txt_h - 2 * pad
        if pill_y1 < 0:
            pill_y1 = y1
            pill_y2 = y1 + txt_h + 2 * pad

        pill_x1 = x1
        pill_x2 = min(w - 1, x1 + txt_w + 2 * pad)

        # Draw filled background pill
        cv2.rectangle(annotated, (pill_x1, pill_y1), (pill_x2, pill_y2), color, cv2.FILLED)

        # Draw contrasting white text on top of pill
        txt_pos = (pill_x1 + pad, pill_y2 - pad - baseline // 2)
        cv2.putText(
            annotated,
            label_text,
            txt_pos,
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            (255, 255, 255),
            font_thickness,
            cv2.LINE_AA,
        )

    return annotated


def encode_image_bytes(image: np.ndarray, format_ext: str = ".jpg", quality: int = 90) -> bytes:
    """Encode an annotated image matrix into compressed bytes."""
    ext = format_ext.lower()
    if not ext.startswith("."):
        ext = f".{ext}"

    params = []
    if ext in (".jpg", ".jpeg"):
        params = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    elif ext == ".png":
        params = [int(cv2.IMWRITE_PNG_COMPRESSION), 4]

    success, buf = cv2.imencode(ext, image, params)
    if not success:
        raise RuntimeError(f"Failed to encode image to {ext}")
    return buf.tobytes()


def save_annotated_image(
    image: np.ndarray,
    output_path: Union[str, Path],
    format_ext: str = ".jpg",
    quality: int = 90,
) -> Path:
    """Save an annotated image to disk, ensuring directory existence and non-overwrite of source."""
    out_p = Path(output_path).resolve()
    out_p.parent.mkdir(parents=True, exist_ok=True)

    encoded_bytes = encode_image_bytes(image, format_ext=format_ext, quality=quality)
    with open(out_p, "wb") as f:
        f.write(encoded_bytes)

    return out_p

