"""RoadVision AI — Vision Service Interface (S5-M1).

Provides the unified, high-level Computer Vision service used by image, video,
and live-webcam pipelines.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Callable, Dict, Optional, Union

import numpy as np

from .config import DEFAULT_CONFIDENCE, DEVICE, MAX_VIDEO_JOB_SECONDS
from .image_engine import ImageEngine
from .model_manager import ModelManager
from .types import ModelStatus, VideoInspectionResult, VisionInspectionResult
from .video_engine import VideoEngine

log = logging.getLogger("roadvision.vision.service")


class VisionService:
    """High-level facade for RoadVision AI computer vision capabilities."""

    def __init__(self, primary_device: Optional[str] = None):
        self.device = primary_device or DEVICE
        self.model_manager = ModelManager(primary_device=self.device)
        self.image_engine = ImageEngine(self.model_manager)
        self.video_engine = VideoEngine(self.model_manager)
        self._is_initialized = False

    def initialize(self, device: Optional[str] = None) -> bool:
        """Start up and verify model weights on the requested hardware device."""
        target_device = device or self.device
        log.info("Initializing VisionService on device %s...", target_device)
        success = self.model_manager.startup(device=target_device)
        self._is_initialized = success
        if success:
            log.info("VisionService successfully initialized with active model: %s", self.model_manager.active)
        else:
            log.error("VisionService initialization failed! Errors: %s", self.model_manager.errors)
        return success

    def detect_image(
        self,
        image_input: Union[bytes, Path, str, np.ndarray],
        conf: float = DEFAULT_CONFIDENCE,
        filename: Optional[str] = None,
        annotate: bool = True,
        output_path: Optional[Union[str, Path]] = None,
    ) -> VisionInspectionResult:
        """Execute road damage detection and annotation on an image input."""
        if not self._is_initialized or self.model_manager.model is None:
            # Auto-initialize on first call if not explicitly called
            self.initialize()

        return self.image_engine.process_image(
            image_input=image_input,
            conf=conf,
            filename=filename,
            annotate=annotate,
            output_path=output_path,
        )

    def detect_video(
        self,
        video_input: Union[Path, str],
        conf: float = DEFAULT_CONFIDENCE,
        output_path: Optional[Union[str, Path]] = None,
        cancel_event: Optional[threading.Event] = None,
        progress_callback: Optional[Callable[[int, int, int, Dict[str, int]], None]] = None,
        timeout_s: float = MAX_VIDEO_JOB_SECONDS,
        raise_on_cancel: bool = False,
    ) -> VideoInspectionResult:
        """Execute road damage detection and annotation on a recorded video file."""
        if not self._is_initialized or self.model_manager.model is None:
            self.initialize()

        return self.video_engine.process_video(
            video_input=video_input,
            conf=conf,
            output_path=output_path,
            cancel_event=cancel_event,
            progress_callback=progress_callback,
            timeout_s=timeout_s,
            raise_on_cancel=raise_on_cancel,
        )

    def get_status(self) -> ModelStatus:
        """Query current runtime model and system status."""
        return self.model_manager.get_status()


# Module-level singleton instance
_GLOBAL_VISION_SERVICE: Optional[VisionService] = None


def get_vision_service(device: Optional[str] = None) -> VisionService:
    """Retrieve or create the global singleton VisionService instance."""
    global _GLOBAL_VISION_SERVICE
    if _GLOBAL_VISION_SERVICE is None:
        _GLOBAL_VISION_SERVICE = VisionService(primary_device=device)
    return _GLOBAL_VISION_SERVICE

