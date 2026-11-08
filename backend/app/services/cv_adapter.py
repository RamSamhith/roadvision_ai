"""RoadVision Application Backend — CV Subsystem Adapter.

Directly bridges the CV VisionService into the application's
ImageInferenceProvider and FrameInferenceProvider protocols.
"""

from __future__ import annotations

import hashlib
import logging
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from app.config import (
    CLASS_CODES,
    MODEL_YOLO26M_EXPECTED_SHA256,
    Settings,
)
from app.services.inference_service import Detection, InferenceFailed, InferenceResult, ModelUnavailable
from app.services.vision.service import VisionService

log = logging.getLogger("roadvision.cv_adapter")


def compute_sha256(path: Path) -> str:
    """Compute the SHA-256 hex digest of a local checkpoint file."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest().upper()


class CVVisionAdapter:
    """Adapts VisionService into ImageInferenceProvider and FrameInferenceProvider."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._lock = threading.RLock()
        self._active_model: Optional[str] = None
        self._errors: Dict[str, str] = {}
        self._fallback_active: bool = False
        self._vision_service: Optional[VisionService] = None
        self._verified_sha256: Optional[str] = None

    def startup(self) -> None:
        """Initialize the CV VisionService and verify weights."""
        with self._lock:
            self._errors.clear()
            self._active_model = None
            self._fallback_active = False

            model_path = self._settings.model_path("YOLO26m")
            if not model_path.is_file():
                self._errors["YOLO26m"] = "Model checkpoint is unavailable."
                self._errors["YOLO26n"] = "Model checkpoint is unavailable."
                log.warning("Primary model checkpoint not found at %s", model_path)
                return

            try:
                calculated_hash = compute_sha256(model_path)
                if calculated_hash != MODEL_YOLO26M_EXPECTED_SHA256:
                    err = f"Model checkpoint hash mismatch (expected {MODEL_YOLO26M_EXPECTED_SHA256[:8]}..., got {calculated_hash[:8]}...)."
                    self._errors["YOLO26m"] = err
                    log.error(err)
                    return
                self._verified_sha256 = calculated_hash
            except Exception as exc:
                self._errors["YOLO26m"] = f"Failed to verify model hash: {exc}"
                log.exception("Hash computation error on %s", model_path)
                return

            try:
                self._vision_service = VisionService(primary_device=self._settings.device)
                initialized = self._vision_service.initialize()
                if not initialized:
                    status = self._vision_service.get_status()
                    self._errors.update(status.errors)
                    self._errors["YOLO26m"] = "Model initialization failed."
                    log.error("VisionService initialization failed: %s", status.errors)
                    return

                self._active_model = "YOLO26m"
                log.info("CVVisionAdapter successfully started with active model YOLO26m on %s", self._settings.device)
            except Exception as exc:
                self._errors["YOLO26m"] = f"Failed to initialize CV VisionService: {exc}"
                log.exception("Exception initializing CV VisionService")

            # Fallback model YOLO26n is permanently unexecuted in CV repo
            self._errors["YOLO26n"] = "Model checkpoint is unavailable."

    def status(self) -> Dict[str, Any]:
        """Report runtime model status matching ModelStatusResponse."""
        with self._lock:
            is_avail = self._active_model is not None and self._vision_service is not None
            return {
                "primary_model": "YOLO26m",
                "fallback_model": "YOLO26n",
                "active_model": self._active_model,
                "primary_loaded": self._active_model == "YOLO26m",
                "fallback_loaded": False,
                "fallback_active": self._fallback_active,
                "initialization_errors": dict(self._errors),
                "available": is_avail,
            }

    def detect_image(self, image: Any, confidence: float) -> InferenceResult:
        """Run road damage detection on an image input (numpy ndarray or PIL)."""
        with self._lock:
            if not self._active_model or self._vision_service is None:
                raise ModelUnavailable("no validated RoadVision model is available")
            service = self._vision_service

        try:
            inspection_result = service.detect_image(
                image_input=image,
                conf=confidence,
                annotate=True,
            )

            if not inspection_result.success:
                raise InferenceFailed(inspection_result.error_message or "image inference failed")

            raw_detections = inspection_result.result.detections
            detections = tuple(
                Detection(
                    class_id=d.class_id,
                    class_name=d.class_name,
                    confidence=round(float(d.confidence), 4),
                    bbox=tuple(round(float(v), 1) for v in d.box),
                )
                for d in raw_detections
            )

            annotated_image = None
            if inspection_result.annotated_image_bytes:
                import cv2
                import numpy as np
                nparr = np.frombuffer(inspection_result.annotated_image_bytes, np.uint8)
                annotated_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if annotated_image is None:
                annotated_image = image

            return InferenceResult(
                model=inspection_result.result.model or "YOLO26m",
                detections=detections,
                annotated_image=annotated_image,
            )
        except Exception as exc:
            if isinstance(exc, (ModelUnavailable, InferenceFailed)):
                raise
            log.exception("Inference error in CVVisionAdapter.detect_image")
            raise InferenceFailed("image inference failed") from exc

    def detect_frame(self, frame: Any, confidence: float) -> InferenceResult:
        """Detect on a decoded video frame using the shared vision service."""
        return self.detect_image(frame, confidence)

    def detect_video_frame(self, frame: Any, confidence: float) -> InferenceResult:
        """Detect on a video frame without model switching."""
        return self.detect_image(frame, confidence)

    def switch_video_to_fallback(self, reason: str) -> bool:
        """Fallback model YOLO26n is unavailable."""
        return False

    def switch_camera_to_fallback(self, reason: str) -> bool:
        """Fallback model YOLO26n is unavailable."""
        return False
