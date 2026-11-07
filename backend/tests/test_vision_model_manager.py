"""Unit tests for ModelManager (S5-M1)."""

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from app.services.vision.classes import CLASS_CODES
from app.services.vision.errors import (
    ModelChecksumError,
    ModelClassMismatchError,
    ModelLoadError,
    ModelUnavailableError,
)
from app.services.vision.model_manager import (
    ModelManager,
    compute_sha256,
    to_result,
)


def test_compute_sha256(tmp_path):
    test_file = tmp_path / "sample.bin"
    test_file.write_bytes(b"RoadVisionAI")
    h = compute_sha256(test_file)
    assert len(h) == 64
    assert h.isupper()


def test_to_result_empty():
    mock_res = MagicMock()
    mock_res.boxes = None
    mock_res.orig_shape = (480, 640)

    res = to_result(mock_res, model_name="YOLO26m")
    assert res.model == "YOLO26m"
    assert res.total_detections == 0
    assert res.class_counts == {"D00": 0, "D10": 0, "D20": 0, "D40": 0}
    assert res.detections == []
    assert res.image_dimensions == (640, 480)


def test_to_result_with_boxes():
    mock_res = MagicMock()
    mock_boxes = MagicMock()
    mock_boxes.cls.tolist.return_value = [0, 3]
    mock_boxes.conf.tolist.return_value = [0.8521, 0.9124]
    mock_boxes.xyxy.tolist.return_value = [
        [10.2, 20.4, 100.6, 200.8],
        [300.1, 400.3, 500.5, 600.7],
    ]
    mock_boxes.__len__.return_value = 2
    mock_res.boxes = mock_boxes
    mock_res.orig_shape = (720, 1280)

    res = to_result(mock_res, model_name="YOLO26m", inference_time_ms=15.2)
    assert res.total_detections == 2
    assert res.class_counts["D00"] == 1
    assert res.class_counts["D40"] == 1
    assert res.class_counts["D10"] == 0
    assert len(res.detections) == 2
    assert res.detections[0].class_name == "D00"
    assert res.detections[1].class_name == "D40"


def test_model_manager_c01_append_only_tracking():
    """Verify C-01: models_used is tracked append-only and never wiped on fallback."""
    mgr = ModelManager(primary_device="cpu")

    # Mock _load to succeed for both models
    mock_yolo = MagicMock()
    with patch.object(mgr, "_load", return_value=mock_yolo):
        # Startup with primary
        success = mgr.startup(start_from="YOLO26m")
        assert success is True
        assert mgr.active == "YOLO26m"
        assert mgr.models_used == ["YOLO26m"]

        # Enable fallback for test and simulate switch
        with patch("app.services.vision.model_manager.YOLO26N_FALLBACK_ENABLED", True):
            mgr.switch_to_fallback("simulated_oom")
            assert mgr.active == "YOLO26n"
            # C-01: Primary model YOLO26m must NOT be wiped!
            assert mgr.models_used == ["YOLO26m", "YOLO26n"]


def test_model_manager_class_mismatch_rejection():
    mgr = ModelManager(primary_device="cpu")

    # Mock YOLO model with COCO classes (person, car, etc.)
    mock_yolo = MagicMock()
    mock_yolo.names = {0: "person", 1: "car"}

    with patch("app.services.vision.model_manager.YOLO", return_value=mock_yolo):
        with patch.object(mgr, "_verify_checkpoint_hash"):
            with pytest.raises(ModelClassMismatchError):
                mgr._load("YOLO26m")


def test_model_manager_predict_without_model_raises():
    mgr = ModelManager(primary_device="cpu")
    mgr.model = None
    with pytest.raises(ModelUnavailableError):
        dummy = np.zeros((100, 100, 3), dtype=np.uint8)
        mgr.predict(dummy)


def test_logger_bound_before_ultralytics_import():
    """D-12: the module logger must be bound before the guarded import.

    ``log`` was previously bound after the ``try: from ultralytics import ...``
    block, so an import or settings failure hit ``NameError`` inside the
    ``except`` handler instead of degrading to ``YOLO = None``.
    """
    import app.services.vision.model_manager as mm

    source = Path(mm.__file__).read_text(encoding="utf-8")
    log_index = source.index('log = logging.getLogger("roadvision.vision.model_manager")')
    yolo_index = source.index("from ultralytics import YOLO, settings")

    assert log_index < yolo_index, "logger must be defined before the Ultralytics import guard"
    assert mm.log.name == "roadvision.vision.model_manager"


def test_ultralytics_import_failure_degrades_gracefully(tmp_path):
    """D-12 behavioural proof: a failed Ultralytics import must not raise NameError.

    A stub ``ultralytics`` package on ``PYTHONPATH`` raises ``ImportError``. The
    module must log through the already-bound logger and set ``YOLO = None``.
    Before the fix this subprocess exited non-zero with ``NameError: log``.
    """
    stub_pkg = tmp_path / "stub" / "ultralytics"
    stub_pkg.mkdir(parents=True)
    (stub_pkg / "__init__.py").write_text(
        'raise ImportError("simulated ultralytics import failure")',
        encoding="utf-8",
    )

    backend_dir = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(stub_pkg.parent), str(backend_dir)])
    code = (
        "import app.services.vision.model_manager as m;"
        "print('YOLO_IS_NONE=' + str(m.YOLO is None));"
        "print('LOG_NAME=' + m.log.name)"
    )

    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=env,
        timeout=180,
    )

    assert proc.returncode == 0, proc.stderr
    assert "YOLO_IS_NONE=True" in proc.stdout
    assert "LOG_NAME=roadvision.vision.model_manager" in proc.stdout
    assert "simulated ultralytics import failure" in proc.stderr


def test_model_manager_dynamic_nms_mode_default():
    """D-14: ModelManager status reports derived mode rather than hardcoded string."""
    mgr = ModelManager()
    assert mgr.nms_mode == "end-to-end (nms=False)"
    status = mgr.get_status()
    assert status.nms_mode == "end-to-end (nms=False)"


def test_model_manager_dynamic_nms_mode_standard():
    """D-14: ModelManager configured with standard NMS reports correct mode and threshold."""
    mgr = ModelManager(nms_args={"nms": True, "iou": 0.55})
    assert mgr.nms_mode == "standard-nms (iou=0.55)"
    status = mgr.get_status()
    assert status.nms_mode == "standard-nms (iou=0.55)"


