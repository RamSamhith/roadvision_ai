"""RoadVision AI — Model Manager and Inference Engine (S5-M1).

Manages YOLO26m production model loading, checkpoint checksum verification,
class order validation, warm-up, thread-safe inference lock, CUDA/CPU execution,
and append-only model tracking (C-01).
"""

from __future__ import annotations

import hashlib
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import torch

from .classes import CLASS_CODES, CODE_TO_LABEL, validate_model_classes
from .config import (
    DEFAULT_CONFIDENCE,
    DEFAULT_IMGSZ,
    DEVICE,
    LOCAL_YOLO_CONFIG_DIR,
    MAX_CONFIDENCE,
    MIN_CONFIDENCE,
    MODEL_CHECKSUMS,
    MODEL_PATHS,
    MODEL_YOLO26M_NAME,
    MODEL_YOLO26N_NAME,
    NMS_ARGS,
    NMS_FREE_MODE,
    YOLO26N_FALLBACK_ENABLED,
)
from .errors import (
    InferenceRuntimeError,
    ModelChecksumError,
    ModelClassMismatchError,
    ModelLoadError,
    ModelUnavailableError,
)
from .types import Detection, DetectionResult, ModelStatus

# Ensure environment is configured before importing Ultralytics
os.environ["YOLO_CONFIG_DIR"] = str(LOCAL_YOLO_CONFIG_DIR)
os.environ["YOLO_OFFLINE"] = "1"
os.environ["YOLO_AUTOINSTALL"] = "0"

# D-12: bind the module logger before the guarded Ultralytics import. The
# handlers below use `log`, so binding it afterwards turned an import or
# settings failure into a NameError instead of a graceful `YOLO = None`.
log = logging.getLogger("roadvision.vision.model_manager")

try:
    from ultralytics import YOLO, settings
    # Enforce offline settings
    settings.update({"sync": False})
except Exception as _e:
    log.warning("Ultralytics import / settings update warning: %s", _e)
    try:
        from ultralytics import YOLO
    except Exception as _e2:
        YOLO = None
        log.error("Failed to import YOLO from ultralytics: %s", _e2)

# Process-wide inference lock (one forward pass at a time on GPU / CPU)
inference_lock = threading.Lock()


def compute_sha256(file_path: Union[str, Path], chunk_size: int = 1024 * 1024) -> str:
    """Compute the uppercase hexadecimal SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            sha256.update(chunk)
    return sha256.hexdigest().upper()


def to_result(
    res: Any,
    model_name: str,
    original_shape: Optional[Tuple[int, int]] = None,
    inference_time_ms: float = 0.0,
) -> DetectionResult:
    """Convert an Ultralytics Results object into a standardized DetectionResult.

    Box coordinates in Ultralytics are in original-image pixel coordinates (xyxy).
    """
    class_counts = {k: 0 for k in CLASS_CODES}
    detections: List[Detection] = []

    boxes = getattr(res, "boxes", None)
    if boxes is not None and len(boxes) > 0:
        cls_list = boxes.cls.tolist()
        conf_list = boxes.conf.tolist()
        xyxy_list = boxes.xyxy.tolist()

        for c_raw, s_raw, xy in zip(cls_list, conf_list, xyxy_list):
            cid = int(c_raw)
            if 0 <= cid < len(CLASS_CODES):
                code = CLASS_CODES[cid]
            else:
                code = f"UNKNOWN_{cid}"

            class_counts[code] = class_counts.get(code, 0) + 1
            conf = round(float(s_raw), 4)
            box_coords = [round(float(v), 1) for v in xy]
            label = CODE_TO_LABEL.get(code, code)

            detections.append(
                Detection(
                    class_id=cid,
                    class_name=code,
                    confidence=conf,
                    box=box_coords,
                    label=label,
                )
            )

    w, h = (0, 0)
    if original_shape is not None:
        h, w = original_shape[:2]
    elif hasattr(res, "orig_shape") and res.orig_shape is not None:
        h, w = res.orig_shape[:2]

    return DetectionResult(
        model=model_name,
        total_detections=len(detections),
        class_counts=class_counts,
        detections=detections,
        inference_time_ms=inference_time_ms,
        image_dimensions=(w, h),
    )


class ModelManager:
    """Manages road damage detection model lifecycle, verification, and inference."""

    ORDER: Tuple[str, ...] = (MODEL_YOLO26M_NAME, MODEL_YOLO26N_NAME)

    def __init__(
        self,
        primary_device: Optional[str] = None,
        nms_args: Optional[Dict[str, Any]] = None,
    ):
        self.model: Optional[Any] = None
        self.active: Optional[str] = None
        self.device: str = primary_device or DEVICE
        self.errors: Dict[str, str] = {}
        self.switched: bool = False
        # C-01: Append-only model tracking list
        self.models_used: List[str] = []
        self._loaded_models: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self.nms_args: Dict[str, Any] = dict(NMS_ARGS) if nms_args is None else dict(nms_args)

    @property
    def nms_mode(self) -> str:
        """Derive the human-readable NMS mode description from active configuration (D-14)."""
        if self.nms_args.get("nms") is False or (NMS_FREE_MODE and "nms" not in self.nms_args):
            return "end-to-end (nms=False)"
        elif self.nms_args.get("nms") is True:
            iou_thresh = self.nms_args.get("iou", 0.45)
            return f"standard-nms (iou={iou_thresh})"
        return "custom-nms"

    def _verify_checkpoint_hash(self, name: str, path: Path) -> None:
        """Verify the SHA-256 hash if a known reference hash is registered."""
        expected_hash = MODEL_CHECKSUMS.get(name)
        if expected_hash:
            actual_hash = compute_sha256(path)
            if actual_hash.upper() != expected_hash.upper():
                raise ModelChecksumError(name, expected_hash, actual_hash)
            log.info("Checkpoint SHA-256 verified for %s: %s", name, actual_hash)

    def _load(self, name: str, device: Optional[str] = None) -> Any:
        """Load, verify, and warm up a specific YOLO model."""
        if YOLO is None:
            raise ModelLoadError("Ultralytics library is not installed or failed to import")

        target_device = device or self.device
        path = MODEL_PATHS.get(name)
        if not path or not path.is_file():
            raise FileNotFoundError(f"Checkpoint for {name} not found at {path}")

        # 1. Verify Checkpoint SHA-256
        self._verify_checkpoint_hash(name, path)

        # 2. Instantiate YOLO
        try:
            m = YOLO(str(path))
        except Exception as e:
            raise ModelLoadError(f"Failed to load weights for {name}: {e}") from e

        # 3. Verify Class Order and Count
        try:
            validate_model_classes(m.names)
        except Exception as e:
            raise ModelClassMismatchError(f"Class validation failed for {name}: {e}") from e

        # 4. Warm-up forward pass
        try:
            dummy_input = np.zeros((DEFAULT_IMGSZ, DEFAULT_IMGSZ, 3), dtype=np.uint8)
            with inference_lock:
                m.predict(
                    dummy_input,
                    device=target_device,
                    imgsz=DEFAULT_IMGSZ,
                    verbose=False,
                    **self.nms_args,
                )
            log.info("Warm-up inference successful for %s on %s", name, target_device)
        except Exception as e:
            raise InferenceRuntimeError(
                f"Warm-up inference failed for {name} on {target_device}: {e}"
            ) from e

        return m

    def startup(self, start_from: str = MODEL_YOLO26M_NAME, device: Optional[str] = None) -> bool:
        """Initialize and load the primary model with fallback sequence.

        C-01 fix: models_used is tracked strictly append-only.
        """
        with self._lock:
            if device:
                self.device = device

            start_idx = self.ORDER.index(start_from) if start_from in self.ORDER else 0
            for name in self.ORDER[start_idx:]:
                # If secondary model fallback is explicitly disabled and un-trained, skip it
                if name == MODEL_YOLO26N_NAME and not YOLO26N_FALLBACK_ENABLED:
                    log.info("YOLO26n fallback is currently disabled pending transfer learning.")
                    continue

                try:
                    log.info("Loading detection model %s on %s...", name, self.device)
                    model_instance = self._load(name, device=self.device)
                    self.model = model_instance
                    self.active = name
                    self._loaded_models[name] = model_instance

                    # C-01: Append-only model tracking
                    if name not in self.models_used:
                        self.models_used.append(name)

                    if name != MODEL_YOLO26M_NAME:
                        self.switched = True
                        log.warning("FALLBACK ACTIVE: %s (prior errors: %s)", name, self.errors)
                    else:
                        log.info("Primary model %s loaded and ready.", name)
                    return True
                except Exception as e:
                    self.errors[name] = str(e)
                    log.warning("Model %s initialization failed: %s", name, e)

            # If all attempted models failed
            self.model = None
            self.active = None
            return False

    def switch_to_cpu(self) -> bool:
        """Switch current active model from CUDA to CPU execution on error or request."""
        with self._lock:
            if not self.active:
                return False
            name = self.active
            log.warning("Switching model %s execution from %s to cpu...", name, self.device)
            try:
                self.device = "cpu"
                model_instance = self._load(name, device="cpu")
                self.model = model_instance
                self._loaded_models[name] = model_instance
                log.info("Successfully switched %s to CPU.", name)
                return True
            except Exception as e:
                log.exception("Failed to switch %s to CPU: %s", name, e)
                return False

    def switch_to_fallback(self, reason: str) -> bool:
        """Switch from primary YOLO26m to secondary YOLO26n (C-01 append-only)."""
        with self._lock:
            if self.active != MODEL_YOLO26M_NAME:
                return False
            if not YOLO26N_FALLBACK_ENABLED:
                log.warning(
                    "Fallback to YOLO26n requested but disabled: YOLO26n is not yet fine-tuned for RDD2022."
                )
                return False

            log.error("Switching to YOLO26n fallback. Reason: %s", reason)
            self.errors[MODEL_YOLO26M_NAME] = reason
            success = self.startup(start_from=MODEL_YOLO26N_NAME)
            return success

    def predict(
        self,
        frame: np.ndarray,
        conf: float = DEFAULT_CONFIDENCE,
        device: Optional[str] = None,
    ) -> DetectionResult:
        """Execute forward pass detection on an image frame.

        Args:
            frame: BGR image matrix (np.ndarray).
            conf: Confidence threshold. Values outside
                [MIN_CONFIDENCE, MAX_CONFIDENCE] are clamped and logged rather
                than silently corrected.
            device: Optional device override.

        Returns:
            Structured DetectionResult.
        """
        if self.model is None:
            raise ModelUnavailableError("No detection model is loaded or available")

        # D-04: clamp to the documented range, but never silently. Strict
        # rejection belongs at the API boundary (TDD v1.1 §10).
        requested_conf = float(conf)
        clamped_conf = max(MIN_CONFIDENCE, min(requested_conf, MAX_CONFIDENCE))
        if clamped_conf != requested_conf:
            log.warning(
                "Requested confidence %.3f is outside [%.2f, %.2f]; using %.2f.",
                requested_conf,
                MIN_CONFIDENCE,
                MAX_CONFIDENCE,
                clamped_conf,
            )
        target_device = device or self.device

        # Track models attempted for this specific inspection
        inspection_models_used: List[str] = []
        if self.active and self.active not in inspection_models_used:
            inspection_models_used.append(self.active)

        for attempt in range(3):
            try:
                t0 = time.perf_counter()
                with inference_lock:
                    raw_res = self.model.predict(
                        frame,
                        conf=clamped_conf,
                        imgsz=DEFAULT_IMGSZ,
                        device=target_device,
                        verbose=False,
                        **self.nms_args,
                    )[0]
                elapsed_ms = (time.perf_counter() - t0) * 1000.0

                return to_result(
                    raw_res,
                    model_name=self.active or "unknown",
                    original_shape=frame.shape[:2],
                    inference_time_ms=elapsed_ms,
                )
            except RuntimeError as e:
                err_str = str(e)
                log.warning("Inference runtime error on attempt %d: %s", attempt + 1, err_str)
                # Attempt 0: clear CUDA cache and retry once
                if attempt == 0 and torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    continue
                # Attempt 1: if on CUDA, try switching same model to CPU
                if attempt == 1 and target_device != "cpu":
                    log.warning("Attempting same-model CPU execution for %s...", self.active)
                    if self.switch_to_cpu():
                        target_device = "cpu"
                        continue
                # Attempt 2: if fallback model is enabled and ready, try switching
                if self.active == MODEL_YOLO26M_NAME and YOLO26N_FALLBACK_ENABLED:
                    if self.switch_to_fallback(err_str):
                        if self.active and self.active not in inspection_models_used:
                            inspection_models_used.append(self.active)
                        continue

                raise InferenceRuntimeError(f"Inference failed after retries: {err_str}") from e
            except Exception as e:
                raise InferenceRuntimeError(f"Unexpected inference failure: {e}") from e

        raise ModelUnavailableError("Inference failed: all retry attempts exhausted")

    def get_status(self) -> ModelStatus:
        """Return the current health and configuration status of the model manager."""
        return ModelStatus(
            active_model=self.active,
            is_available=self.model is not None,
            device=self.device,
            nms_mode=self.nms_mode,
            classes=list(CLASS_CODES),
            fallback_active=self.switched,
            models_used=list(self.models_used),
            errors=dict(self.errors),
        )
