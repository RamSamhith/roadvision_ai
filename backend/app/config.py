"""RoadVision AI — Application Configuration Bridge (TDD v1.1 §13).

Provides application-wide access to CV constants, limits, paths, and class definitions.
"""

from __future__ import annotations

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
    DEFAULT_CONFIDENCE,
    DEFAULT_IMGSZ,
    DEVICE,
    MAX_CONCURRENT_JOBS,
    MAX_IMAGE_BYTES,
    MAX_IMAGE_DIMENSION,
    MAX_IMAGE_PIXELS,
    MAX_VIDEO_BYTES,
    MAX_VIDEO_DURATION_S,
    MAX_VIDEO_JOB_SECONDS,
    MAX_VIDEO_RESOLUTION,
    MAX_WEBCAM_SESSION_SECONDS,
    MIN_CONFIDENCE,
    MAX_CONFIDENCE,
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
)

# Alias for TDD v1.1 §3.3 compatibility
IMGSZ = DEFAULT_IMGSZ

