"""Unit tests for Detection Annotation Engine (S5-M1)."""

import numpy as np
import pytest
from app.services.vision.annotate import (
    annotate_image,
    encode_image_bytes,
    get_class_color,
    save_annotated_image,
)
from app.services.vision.types import Detection, DetectionResult


def test_get_class_color():
    c0 = get_class_color("D00")
    c1 = get_class_color("D10")
    c2 = get_class_color("D20")
    c4 = get_class_color("D40")
    assert len(c0) == 3
    assert len(c4) == 3
    assert c0 != c4  # Colors are distinct


def test_annotate_image_non_destructive(tmp_path):
    # Create synthetic blank BGR image
    original = np.zeros((480, 640, 3), dtype=np.uint8)
    original_copy = original.copy()

    dets = [
        Detection(0, "D00", 0.85, [50, 50, 200, 200], "Longitudinal crack"),
        Detection(3, "D40", 0.92, [300, 150, 450, 300], "Pothole"),
    ]

    annotated = annotate_image(original, dets)

    # Must NOT modify the original input array
    assert np.array_equal(original, original_copy)
    # Annotated must contain drawings (non-zero pixels)
    assert not np.array_equal(annotated, original)
    assert annotated.shape == (480, 640, 3)


def test_annotate_image_clamping():
    # Box coordinates with coordinates outside frame boundaries
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    dets = [Detection(1, "D10", 0.5, [-50, -50, 500, 500], "Transverse crack")]
    annotated = annotate_image(img, dets)
    assert annotated.shape == (100, 100, 3)


def test_encode_and_save_annotated_image(tmp_path):
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    encoded_jpg = encode_image_bytes(img, format_ext=".jpg")
    assert isinstance(encoded_jpg, bytes)
    assert len(encoded_jpg) > 0

    out_file = tmp_path / "annotated_sample.jpg"
    saved = save_annotated_image(img, out_file)
    assert saved.is_file()
    assert saved.stat().st_size > 0

