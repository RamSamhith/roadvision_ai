"""Unit tests for Image Processing & Validation Engine (S5-M1)."""

import io
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest
from PIL import Image
from app.services.vision.config import MAX_IMAGE_BYTES, MAX_IMAGE_DIMENSION
from app.services.vision.errors import (
    ImageDecodeError,
    ImageDimensionExceededError,
    ImageSizeExceededError,
    ImageValidationError,
    UnsupportedImageFormatError,
)
from app.services.vision.image_engine import (
    ImageEngine,
    decode_image_bytes,
    validate_image_payload,
)
from app.services.vision.types import DetectionResult


def make_test_jpeg(width: int = 100, height: int = 100) -> bytes:
    img = Image.new("RGB", (width, height), color=(128, 128, 128))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_validate_image_payload_valid():
    raw = make_test_jpeg(200, 150)
    w, h, fmt = validate_image_payload(raw, filename="test.jpg")
    assert w == 200
    assert h == 150
    assert fmt == "JPEG"


def test_validate_image_payload_empty():
    with pytest.raises(ImageValidationError, match="empty image payload"):
        validate_image_payload(b"")


def test_validate_image_payload_size_exceeded():
    with pytest.raises(ImageSizeExceededError):
        # Pass a byte buffer exceeding MAX_IMAGE_BYTES
        validate_image_payload(b"0" * (MAX_IMAGE_BYTES + 10))


def test_validate_image_payload_unsupported_format():
    with pytest.raises(UnsupportedImageFormatError):
        raw = make_test_jpeg(50, 50)
        validate_image_payload(raw, filename="road.gif")


def test_validate_image_payload_corrupt():
    with pytest.raises(ImageDecodeError):
        validate_image_payload(b"not_a_valid_image_stream", filename="corrupt.jpg")


def test_decode_image_bytes():
    raw = make_test_jpeg(64, 48)
    img_bgr = decode_image_bytes(raw)
    assert isinstance(img_bgr, np.ndarray)
    assert img_bgr.shape == (48, 64, 3)


def test_image_engine_process_empty_detections():
    mock_mgr = MagicMock()
    mock_mgr.active = "YOLO26m"
    mock_mgr.device = "cpu"
    mock_mgr.models_used = ["YOLO26m"]

    empty_result = DetectionResult(
        model="YOLO26m",
        total_detections=0,
        class_counts={"D00": 0, "D10": 0, "D20": 0, "D40": 0},
        detections=[],
        image_dimensions=(64, 48),
    )
    mock_mgr.predict.return_value = empty_result

    engine = ImageEngine(mock_mgr)
    raw = make_test_jpeg(64, 48)
    insp = engine.process_image(raw, conf=0.25, annotate=True)

    assert insp.success is True
    assert insp.result.total_detections == 0
    assert insp.models_used == ["YOLO26m"]
    assert insp.annotated_image_bytes is not None

