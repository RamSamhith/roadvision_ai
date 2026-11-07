"""RoadVision AI — Detection Classes & Single Source of Truth (S5-M1).

Implements PRD v1.1 §4.4, TDD v1.1 §4.3 Table 3, and AC-08 cross-layer contract.
Loads backend/app/classes.json and provides runtime constants and validation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

from .config import CLASSES_JSON_PATH

# -----------------------------------------------------------------------------
# Load Canonical classes.json
# -----------------------------------------------------------------------------
def load_canonical_classes(path: Path = CLASSES_JSON_PATH) -> Dict[str, Any]:
    """Load and validate the canonical classes.json definition."""
    if not path.is_file():
        raise FileNotFoundError(f"Canonical classes file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "names" not in data or not isinstance(data["names"], list):
        raise ValueError(f"Invalid classes.json: missing 'names' list in {path}")

    return data

_CANONICAL_DATA = load_canonical_classes()

# Fixed 4-class code tuple in strict index order
CLASS_CODES: Tuple[str, ...] = tuple(_CANONICAL_DATA["names"])
NUM_CLASSES: int = len(CLASS_CODES)

# Mappings
CODE_TO_ID: Dict[str, int] = {
    code: idx for idx, code in enumerate(CLASS_CODES)
}
ID_TO_CODE: Dict[int, str] = {
    idx: code for idx, code in enumerate(CLASS_CODES)
}

# Display labels mapping
CODE_TO_LABEL: Dict[str, str] = {
    item["code"]: item["label"] for item in _CANONICAL_DATA.get("classes", [])
}
ID_TO_LABEL: Dict[int, str] = {
    item["id"]: item["label"] for item in _CANONICAL_DATA.get("classes", [])
}

# Fallbacks if classes list was not populated
if not CODE_TO_LABEL:
    # Table 3 canonical defaults
    _DEFAULTS = {
        "D00": "Longitudinal crack",
        "D10": "Transverse crack",
        "D20": "Alligator crack",
        "D40": "Pothole",
    }
    CODE_TO_LABEL = _DEFAULTS
    ID_TO_LABEL = {CODE_TO_ID[k]: v for k, v in _DEFAULTS.items()}


def get_display_label(identifier: Union[int, str]) -> str:
    """Return the human-readable display label for a class id or class code."""
    if isinstance(identifier, int):
        return ID_TO_LABEL.get(identifier, f"Unknown ({identifier})")
    return CODE_TO_LABEL.get(identifier, f"Unknown ({identifier})")


def validate_model_classes(model_names: Union[Dict[int, str], List[str]]) -> None:
    """Validate that model class names exactly match the canonical CLASS_CODES.

    Raises:
        ValueError: If model classes do not match count, naming, or ordering.
    """
    if isinstance(model_names, dict):
        ordered_names = [model_names[i] for i in sorted(model_names.keys())]
    elif isinstance(model_names, list):
        ordered_names = list(model_names)
    else:
        raise TypeError(f"Expected dict or list for model_names, got {type(model_names)}")

    if ordered_names != list(CLASS_CODES):
        raise ValueError(
            f"Model class mismatch! Expected {list(CLASS_CODES)}, "
            f"got {ordered_names}. Model must be fine-tuned specifically "
            f"for RoadVision AI classes (PRD v1.1 §4.4, AC-08)."
        )

