"""Unit tests for VisionService facade (S5-M1)."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from app.services.vision.service import VisionService, get_vision_service
from app.services.vision.types import Detection, DetectionResult


def test_vision_service_mocked_lifecycle():
    service = VisionService(primary_device="cpu")

    mock_mgr = MagicMock()
    mock_mgr.active = "YOLO26m"
    mock_mgr.device = "cpu"
    mock_mgr.models_used = ["YOLO26m"]
    mock_mgr.startup.return_value = True

    mock_res = DetectionResult(
        model="YOLO26m",
        total_detections=1,
        class_counts={"D00": 1, "D10": 0, "D20": 0, "D40": 0},
        detections=[Detection(0, "D00", 0.88, [10, 10, 50, 50], "Longitudinal crack")],
        image_dimensions=(100, 100),
    )
    mock_mgr.predict.return_value = mock_res

    service.model_manager = mock_mgr
    service.image_engine.model_manager = mock_mgr

    # Initialize
    ok = service.initialize()
    assert ok is True

    # Detect on synthetic BGR image
    dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
    insp = service.detect_image(dummy_img, conf=0.25, annotate=True)

    assert insp.success is True
    assert insp.result.total_detections == 1
    assert insp.result.class_counts["D00"] == 1
    assert insp.annotated_image_bytes is not None


def test_get_vision_service_singleton():
    s1 = get_vision_service()
    s2 = get_vision_service()
    assert s1 is s2

