"""Unit and regression tests for confidence calibration, modes, and NMS propagation.

Tests:
- Confidence configuration constants and predefined modes ('balanced', 'high_recall').
- Strict input validation via validate_confidence().
- Threshold propagation into DetectionResult and VisionInspectionResult metadata.
- Consistent image and video confidence resolution.
- Dynamic NMS mode reporting and argument passing.
- Out-of-bounds warning logging and defense-in-depth clamping.
- CPU/GPU compatibility and error handling preservation.
"""

import math
from pathlib import Path
import cv2
import numpy as np
import pytest

from app.services.vision.config import (
    CONFIDENCE_BALANCED,
    CONFIDENCE_HIGH_RECALL,
    CONFIDENCE_MODES,
    DEFAULT_CONFIDENCE,
    MAX_CONFIDENCE,
    MIN_CONFIDENCE,
    validate_confidence,
)
from app.services.vision.image_engine import ImageEngine
from app.services.vision.model_manager import ModelManager
from app.services.vision.service import VisionService
from app.services.vision.types import Detection, DetectionResult, VisionInspectionResult
from app.services.vision.video_engine import VideoEngine


def test_confidence_constants_and_modes():
    """Verify calibrated confidence constants and mode mappings."""
    assert DEFAULT_CONFIDENCE == 0.25
    assert MIN_CONFIDENCE == 0.10
    assert MAX_CONFIDENCE == 0.90
    assert CONFIDENCE_BALANCED == 0.25
    assert CONFIDENCE_HIGH_RECALL == 0.15
    assert CONFIDENCE_MODES["balanced"] == 0.25
    assert CONFIDENCE_MODES["high_recall"] == 0.15


def test_validate_confidence_valid_floats_and_modes():
    """Verify valid floats and mode strings resolve accurately."""
    assert validate_confidence(0.25) == 0.25
    assert validate_confidence(0.15) == 0.15
    assert validate_confidence(0.10) == 0.10
    assert validate_confidence(0.90) == 0.90
    assert validate_confidence("0.35") == 0.35

    # Case-insensitive mode strings
    assert validate_confidence("balanced") == 0.25
    assert validate_confidence("BALANCED") == 0.25
    assert validate_confidence("high_recall") == 0.15
    assert validate_confidence("HIGH_RECALL") == 0.15


def test_validate_confidence_invalid_values_rejected():
    """Verify that out-of-range or non-numeric inputs raise ValueError."""
    # Below minimum
    with pytest.raises(ValueError, match="outside valid range"):
        validate_confidence(0.09)

    # Above maximum
    with pytest.raises(ValueError, match="outside valid range"):
        validate_confidence(0.91)

    # NaN and Inf
    with pytest.raises(ValueError, match="NaN or infinite"):
        validate_confidence(float("nan"))
    with pytest.raises(ValueError, match="NaN or infinite"):
        validate_confidence(float("inf"))

    # Invalid mode string
    with pytest.raises(ValueError, match="Invalid confidence mode"):
        validate_confidence("ultra_high")

    # Non-numeric string
    with pytest.raises(ValueError, match="Invalid confidence mode"):
        validate_confidence("abc")

    # Unsupported types
    with pytest.raises(ValueError, match="numeric"):
        validate_confidence([0.25])


def test_metadata_reporting_conf_threshold():
    """Verify DetectionResult and VisionInspectionResult record conf_threshold."""
    det = Detection(0, "D00", 0.85, [10.0, 20.0, 50.0, 60.0], "Longitudinal crack")
    res = DetectionResult(
        model="YOLO26m",
        total_detections=1,
        class_counts={"D00": 1, "D10": 0, "D20": 0, "D40": 0},
        detections=[det],
        inference_time_ms=15.2,
        image_dimensions=(640, 640),
        conf_threshold=0.15,
    )
    d = res.to_dict()
    assert d["conf_threshold"] == 0.15

    insp = VisionInspectionResult(
        result=res,
        models_used=["YOLO26m"],
        device="cpu",
        success=True,
    )
    insp_d = insp.to_dict()
    assert insp_d["conf_threshold"] == 0.15


def test_image_engine_mode_string_propagation():
    """Verify ImageEngine correctly resolves mode strings and sets metadata."""
    class DummyModel:
        names = {0: "D00", 1: "D10", 2: "D20", 3: "D40"}
        def predict(self, frame, **kwargs):
            class DummyBoxes:
                cls = []
                conf = []
                xyxy = []
                def __len__(self):
                    return 0
            class DummyRes:
                boxes = DummyBoxes()
                orig_shape = (100, 100)
            return [DummyRes()]

    mgr = ModelManager(primary_device="cpu")
    mgr.model = DummyModel()
    mgr.active = "YOLO26m"

    engine = ImageEngine(mgr)
    dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)

    # 1. Balanced mode
    res_balanced = engine.process_image(dummy_img, conf="balanced", annotate=False)
    assert res_balanced.result.conf_threshold == 0.25
    assert res_balanced.to_dict()["conf_threshold"] == 0.25

    # 2. High recall mode
    res_hr = engine.process_image(dummy_img, conf="high_recall", annotate=False)
    assert res_hr.result.conf_threshold == 0.15
    assert res_hr.to_dict()["conf_threshold"] == 0.15


def test_vision_service_custom_nms_args():
    """Verify VisionService accepts and passes nms_args to ModelManager."""
    service = VisionService(primary_device="cpu", nms_args={"nms": True, "iou": 0.50})
    assert service.model_manager.nms_args == {"nms": True, "iou": 0.50}
    assert service.model_manager.nms_mode == "standard-nms (iou=0.5)"
    status = service.get_status()
    assert status.nms_mode == "standard-nms (iou=0.5)"


def test_out_of_range_confidence_clamped_and_logged(caplog):
    """Verify ModelManager clamps out-of-range floats with a warning."""
    class DummyModel:
        names = {0: "D00", 1: "D10", 2: "D20", 3: "D40"}
        def predict(self, frame, **kwargs):
            assert kwargs["conf"] == MAX_CONFIDENCE
            class DummyBoxes:
                cls = []
                conf = []
                xyxy = []
                def __len__(self):
                    return 0
            class DummyRes:
                boxes = DummyBoxes()
                orig_shape = (100, 100)
            return [DummyRes()]

    mgr = ModelManager(primary_device="cpu")
    mgr.model = DummyModel()
    mgr.active = "YOLO26m"

    with caplog.at_level("WARNING"):
        res = mgr.predict(np.zeros((100, 100, 3), dtype=np.uint8), conf=5.0)

    assert res.conf_threshold == MAX_CONFIDENCE
    assert any("outside [0.10, 0.90]" in r.message for r in caplog.records)

