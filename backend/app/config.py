"""Central configuration for RoadVision — unified CV and application platform.

Consolidates CV engine constants, paths, thresholds, and runtime settings into a
single robust, environment-configurable interface.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Optional

# CV specific class mappings and constants
from app.services.vision.classes import (
    CLASS_CODES,
    CODE_TO_ID,
    CODE_TO_LABEL,
    ID_TO_CODE,
    ID_TO_LABEL,
    NUM_CLASSES,
    get_display_label,
)
from app.services.vision.config import (
    ALLOWED_IMAGE_EXTENSIONS,
    ALLOWED_VIDEO_EXTENSIONS,
    CLASSES_JSON_PATH,
    CONFIDENCE_BALANCED,
    CONFIDENCE_HIGH_RECALL,
    CONFIDENCE_MODES,
    DEFAULT_CONFIDENCE,
    DEFAULT_IMGSZ,
    DEVICE,
    MAX_CONCURRENT_JOBS,
    MAX_CONFIDENCE,
    MAX_IMAGE_BYTES,
    MAX_IMAGE_DIMENSION,
    MAX_IMAGE_PIXELS,
    MAX_VIDEO_BYTES,
    MAX_VIDEO_DURATION_S,
    MAX_VIDEO_JOB_SECONDS,
    MAX_VIDEO_RESOLUTION,
    MAX_WEBCAM_SESSION_SECONDS,
    MIN_CONFIDENCE,
    MIN_LIVE_FPS,
    MODEL_CHECKSUMS,
    MODEL_PATHS,
    MODEL_YOLO26M_EXPECTED_SHA256,
    MODEL_YOLO26M_NAME,
    MODEL_YOLO26M_PATH,
    MODEL_YOLO26N_NAME,
    MODEL_YOLO26N_PATH,
    NMS_ARGS,
    NMS_FREE_MODE,
    PROVISIONAL_LIMITS_NOTE,
    REPO_ROOT,
    YOLO26N_FALLBACK_ENABLED,
    validate_confidence,
)

# Human-readable labels for application frontend
CLASS_LABELS: Final[dict[str, str]] = {
    "D00": "Longitudinal Crack",
    "D10": "Transverse Crack",
    "D20": "Alligator Crack",
    "D40": "Pothole",
}

# Alias for TDD v1.1 §3.3 compatibility
IMGSZ = DEFAULT_IMGSZ


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime application settings; values are project-relative and environment-configurable."""

    project_root: Path
    data_dir: Path
    device: str = "cpu"
    image_size: int = DEFAULT_IMGSZ
    default_confidence: float = DEFAULT_CONFIDENCE
    min_confidence: float = MIN_CONFIDENCE
    max_confidence: float = MAX_CONFIDENCE
    image_max_bytes: int = MAX_IMAGE_BYTES
    image_max_side: int = MAX_IMAGE_DIMENSION
    video_max_bytes: int = MAX_VIDEO_BYTES
    video_max_seconds: int = int(MAX_VIDEO_DURATION_S)
    video_max_side: int = 1920
    job_timeout_seconds: int = int(MAX_VIDEO_JOB_SECONDS)
    webcam_max_seconds: int = int(MAX_WEBCAM_SESSION_SECONDS)
    webcam_watchdog_seconds: int = 10
    webcam_min_fps: float = MIN_LIVE_FPS
    camera_index: int = 0
    upload_chunk_bytes: int = 1024 * 1024

    @classmethod
    def from_environment(cls) -> "Settings":
        project_root = Path(__file__).resolve().parents[2]
        data_dir = Path(os.getenv("ROADVISION_DATA_DIR", str(project_root / "data"))).resolve()

        device_env = os.getenv("ROADVISION_DEVICE")
        if device_env:
            device = device_env
        else:
            try:
                import torch
                device = "cuda:0" if torch.cuda.is_available() else "cpu"
            except Exception:
                device = "cpu"

        return cls(
            project_root=project_root,
            data_dir=data_dir,
            device=device,
        )

    @property
    def database_path(self) -> Path:
        return self.data_dir / "db" / "roadvision.sqlite3"

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads_tmp"

    @property
    def outputs_dir(self) -> Path:
        return self.data_dir / "outputs"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    def model_path(self, model_name: str) -> Path:
        """Resolve the model checkpoint path with priority for internal repository weights."""
        env_override = os.getenv("ROADVISION_MODEL_PATH")
        if env_override and Path(env_override).is_file():
            return Path(env_override).resolve()

        # Primary location inside roadvision ai: models/weights/yolo26m.pt
        internal_primary = self.project_root / "models" / "weights" / "yolo26m.pt"
        if model_name == "YOLO26m" and internal_primary.is_file():
            return internal_primary

        filenames = {
            "YOLO26m": internal_primary if internal_primary.is_file() else (self.project_root / "weights" / "yolo26m" / "best.pt"),
            "YOLO26n": self.project_root / "weights" / "yolo26n" / "best.pt",
        }
        return filenames.get(model_name, self.project_root / "weights" / model_name.lower() / "best.pt")
