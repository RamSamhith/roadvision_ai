"""RoadVision AI — Computer Vision Configuration (S5-M1).

Configures Ultralytics runtime paths, offline flags, model paths, checksums,
device resolution, and configuration-driven provisional operational limits (Q-01).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Final, Set, Tuple

import torch

# -----------------------------------------------------------------------------
# Base Directories
# -----------------------------------------------------------------------------
_CURRENT_DIR = Path(__file__).resolve().parent
# backend/app/services/vision -> backend -> roadvision ai
REPO_ROOT: Final[Path] = _CURRENT_DIR.parents[3]
BACKEND_DIR: Final[Path] = _CURRENT_DIR.parents[2]
APP_DIR: Final[Path] = _CURRENT_DIR.parents[1]

# -----------------------------------------------------------------------------
# Ultralytics Offline and Local Config Configuration
# Must be set before any Ultralytics module import across the application.
# -----------------------------------------------------------------------------
LOCAL_YOLO_CONFIG_DIR: Final[Path] = REPO_ROOT / ".ultralytics"
LOCAL_YOLO_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

os.environ["YOLO_CONFIG_DIR"] = str(LOCAL_YOLO_CONFIG_DIR)
os.environ["YOLO_OFFLINE"] = "1"
os.environ["YOLO_AUTOINSTALL"] = "0"

# -----------------------------------------------------------------------------
# Model Specifications & Checkpoint Verification Hashes
# -----------------------------------------------------------------------------
MODELS_DIR: Final[Path] = REPO_ROOT / "models" / "weights"

MODEL_YOLO26M_NAME: Final[str] = "YOLO26m"
MODEL_YOLO26M_PATH: Final[Path] = MODELS_DIR / "yolo26m.pt"
MODEL_YOLO26M_EXPECTED_SHA256: Final[str] = (
    "1BC41287DBDBC5EC5793D5D8F14CBA770E9E71E9C9E0CC0188B7146DA592D233"
)

MODEL_YOLO26N_NAME: Final[str] = "YOLO26n"
MODEL_YOLO26N_PATH: Final[Path] = MODELS_DIR / "yolo26n.pt"
# YOLO26n transfer learning is not yet executed; fallback is disabled until trained.
YOLO26N_FALLBACK_ENABLED: bool = False

MODEL_PATHS: Final[Dict[str, Path]] = {
    MODEL_YOLO26M_NAME: MODEL_YOLO26M_PATH,
    MODEL_YOLO26N_NAME: MODEL_YOLO26N_PATH,
}

MODEL_CHECKSUMS: Final[Dict[str, str]] = {
    MODEL_YOLO26M_NAME: MODEL_YOLO26M_EXPECTED_SHA256,
}

# -----------------------------------------------------------------------------
# Inference Parameters
# -----------------------------------------------------------------------------
DEFAULT_IMGSZ: Final[int] = 640
DEFAULT_CONFIDENCE: Final[float] = 0.25
MIN_CONFIDENCE: Final[float] = 0.10
MAX_CONFIDENCE: Final[float] = 0.90

# End-to-end NMS-free mode (TDD v1.1 §3.4, Q-02 ratified).
# When nms=False, Ultralytics uses native end-to-end head output without traditional IoU clustering.
NMS_FREE_MODE: Final[bool] = True
NMS_ARGS: Final[Dict[str, Any]] = {}

# -----------------------------------------------------------------------------
# Hardware Device Resolution (CUDA primary with dynamic CPU fallback)
# -----------------------------------------------------------------------------
def get_primary_device() -> str:
    """Return 'cuda:0' if CUDA is available, otherwise 'cpu'."""
    return "cuda:0" if torch.cuda.is_available() else "cpu"

DEVICE: str = get_primary_device()

# -----------------------------------------------------------------------------
# Classes File Location
# -----------------------------------------------------------------------------
CLASSES_JSON_PATH: Final[Path] = APP_DIR / "classes.json"

# -----------------------------------------------------------------------------
# Q-01 Provisional Operational Limits
# NOTE: These values are configuration-driven provisional defaults per PRD v1.1 §4.11
# and TDD v1.1 §10.2. They are subject to formal team benchmark review and ratification
# under OPEN_QUESTIONS.md Q-01. They are NOT silently marked as ratified.
# -----------------------------------------------------------------------------
PROVISIONAL_LIMITS_NOTE: Final[str] = (
    "Provisional defaults per PRD v1.1 §4.11 / TDD v1.1 §10.2; "
    "pending formal Q-01 benchmark review."
)

ALLOWED_IMAGE_EXTENSIONS: Final[Set[str]] = {".jpg", ".jpeg", ".png"}
MAX_IMAGE_BYTES: Final[int] = 20 * 1024 * 1024  # 20 MB
MAX_IMAGE_DIMENSION: Final[int] = 8192          # 8192 px longest side
MAX_IMAGE_PIXELS: Final[int] = 8192 * 8192      # 67,108,864 px (PIL DecompressionBomb check)

ALLOWED_VIDEO_EXTENSIONS: Final[Set[str]] = {".mp4", ".avi"}
MAX_VIDEO_BYTES: Final[int] = 200 * 1024 * 1024 # 200 MB
MAX_VIDEO_DURATION_S: Final[float] = 60.0       # 60 s
MAX_VIDEO_RESOLUTION: Final[Tuple[int, int]] = (1920, 1080)
MAX_VIDEO_JOB_SECONDS: Final[float] = 600.0     # 10 min watchdog timeout
MAX_VIDEO_FRAME_CAP: Final[int] = int(MAX_VIDEO_DURATION_S * 60) # 3600 frames (60s @ 60 fps limit)

MAX_WEBCAM_SESSION_SECONDS: Final[float] = 600.0# 10 min session limit
MIN_LIVE_FPS: Final[float] = 5.0                # F5 fallback trigger threshold
MAX_CONCURRENT_JOBS: Final[int] = 1             # Single active video/webcam job slot

