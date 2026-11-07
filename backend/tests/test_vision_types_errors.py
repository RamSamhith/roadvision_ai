"""Unit tests for Vision types and errors (S5-M1)."""

from app.services.vision.errors import (
    ImageDecodeError,
    ImageDimensionExceededError,
    ImageSizeExceededError,
    ImageValidationError,
    InferenceRuntimeError,
    ModelChecksumError,
    ModelClassMismatchError,
    ModelLoadError,
    ModelUnavailableError,
    UnsupportedImageFormatError,
    VisionServiceError,
)
from app.services.vision.types import (
    Detection,
    DetectionResult,
    ModelStatus,
    VisionInspectionResult,
)


def test_detection_to_dict():
    det = Detection(
        class_id=0,
        class_name="D00",
        confidence=0.87654,
        box=[10.123, 20.456, 100.789, 200.123],
        label="Longitudinal crack",
    )
    d = det.to_dict()
    assert d["class_id"] == 0
    assert d["class_name"] == "D00"
    assert d["confidence"] == 0.8765
    assert d["box"] == [10.1, 20.5, 100.8, 200.1]
    assert d["label"] == "Longitudinal crack"


def test_detection_result_to_dict():
    det = Detection(0, "D00", 0.9, [10, 20, 100, 200], "Longitudinal crack")
    res = DetectionResult(
        model="YOLO26m",
        total_detections=1,
        class_counts={"D00": 1, "D10": 0, "D20": 0, "D40": 0},
        detections=[det],
        inference_time_ms=12.345,
        image_dimensions=(640, 480),
    )
    d = res.to_dict()
    assert d["model"] == "YOLO26m"
    assert d["total_detections"] == 1
    assert d["class_counts"]["D00"] == 1
    assert d["class_counts"]["D40"] == 0
    assert len(d["detections"]) == 1
    assert d["inference_time_ms"] == 12.35
    assert d["image_dimensions"] == [640, 480]


def test_vision_inspection_result_c01_tracking():
    det_res = DetectionResult(
        model="YOLO26m",
        total_detections=0,
        class_counts={"D00": 0, "D10": 0, "D20": 0, "D40": 0},
        detections=[],
    )
    insp = VisionInspectionResult(
        result=det_res,
        models_used=["YOLO26m", "YOLO26n"],
        device="cuda:0",
        success=True,
    )
    d = insp.to_dict()
    assert d["models_used"] == ["YOLO26m", "YOLO26n"]
    assert d["device"] == "cuda:0"
    assert d["success"] is True


def test_errors_hierarchy():
    err = ModelChecksumError("YOLO26m", "AAA", "BBB")
    assert isinstance(err, ModelLoadError)
    assert isinstance(err, VisionServiceError)
    assert err.code == "model_checksum_mismatch"
    assert err.status_code == 500

    img_err = UnsupportedImageFormatError(".gif", {".jpg", ".png"})
    assert isinstance(img_err, ImageValidationError)
    assert img_err.status_code == 415

    size_err = ImageSizeExceededError(25000000, 20000000)
    assert size_err.status_code == 413

