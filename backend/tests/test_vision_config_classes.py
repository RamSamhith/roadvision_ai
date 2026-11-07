"""Unit tests for Vision Configuration and Classes modules (S5-M1)."""

import pytest
from app.services.vision.classes import (
    CLASS_CODES,
    CODE_TO_ID,
    CODE_TO_LABEL,
    ID_TO_CODE,
    ID_TO_LABEL,
    NUM_CLASSES,
    get_display_label,
    validate_model_classes,
)
from app.services.vision.config import (
    ALLOWED_IMAGE_EXTENSIONS,
    DEFAULT_CONFIDENCE,
    MAX_IMAGE_BYTES,
    MAX_IMAGE_DIMENSION,
    MODEL_YOLO26M_EXPECTED_SHA256,
    MODEL_YOLO26M_NAME,
    NMS_ARGS,
    NMS_FREE_MODE,
)


def test_canonical_class_codes():
    """Verify exact 4 classes in canonical index order (PRD v1.1 §4.4, TDD Table 3)."""
    assert CLASS_CODES == ("D00", "D10", "D20", "D40")
    assert NUM_CLASSES == 4
    assert CODE_TO_ID == {"D00": 0, "D10": 1, "D20": 2, "D40": 3}
    assert ID_TO_CODE == {0: "D00", 1: "D10", 2: "D20", 3: "D40"}


def test_canonical_labels():
    """Verify human-readable display labels."""
    assert CODE_TO_LABEL["D00"] == "Longitudinal crack"
    assert CODE_TO_LABEL["D10"] == "Transverse crack"
    assert CODE_TO_LABEL["D20"] == "Alligator crack"
    assert CODE_TO_LABEL["D40"] == "Pothole"
    assert get_display_label(0) == "Longitudinal crack"
    assert get_display_label("D40") == "Pothole"
    assert get_display_label(999) == "Unknown (999)"


def test_validate_model_classes_success():
    """Valid class dicts or lists must pass validation without error."""
    valid_dict = {0: "D00", 1: "D10", 2: "D20", 3: "D40"}
    validate_model_classes(valid_dict)

    valid_list = ["D00", "D10", "D20", "D40"]
    validate_model_classes(valid_list)


def test_validate_model_classes_failure():
    """Mismatched, reordered, or foreign classes must raise ValueError (AC-08)."""
    # Foreign COCO classes
    with pytest.raises(ValueError, match="Model class mismatch"):
        validate_model_classes({0: "person", 1: "bicycle"})

    # Reordered classes
    with pytest.raises(ValueError, match="Model class mismatch"):
        validate_model_classes(["D10", "D00", "D20", "D40"])

    # Incomplete classes
    with pytest.raises(ValueError, match="Model class mismatch"):
        validate_model_classes(["D00", "D10"])


def test_config_defaults():
    """Verify operational configuration limits and parameters."""
    assert NMS_FREE_MODE is True
    assert NMS_ARGS == {}
    assert DEFAULT_CONFIDENCE == 0.25
    assert ".jpg" in ALLOWED_IMAGE_EXTENSIONS
    assert ".png" in ALLOWED_IMAGE_EXTENSIONS
    assert MAX_IMAGE_BYTES == 20 * 1024 * 1024
    assert MAX_IMAGE_DIMENSION == 8192
    assert len(MODEL_YOLO26M_EXPECTED_SHA256) == 64


def test_app_config_bridge_exports_confidence_bounds():
    """D-01: the Ram-owned ``app.config`` bridge re-exports both confidence bounds.

    ``backend/app/api/detect.py`` previously did ``from app.config import
    MAX_CONFIDENCE``, which raised ``ImportError`` at import time because the
    bridge omitted that name.
    """
    import app.config as app_config
    from app.services.vision.config import MAX_CONFIDENCE, MIN_CONFIDENCE

    assert app_config.MIN_CONFIDENCE == MIN_CONFIDENCE == 0.10
    assert app_config.MAX_CONFIDENCE == MAX_CONFIDENCE == 0.90

