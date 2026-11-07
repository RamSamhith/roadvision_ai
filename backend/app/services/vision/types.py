"""RoadVision AI — Data Structures and Type Definitions (S5-M1).

Implements TDD v1.1 §6 inference engine detection result structure and C-01
append-only model tracking contracts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class Detection:
    """Single detected road-damage bounding box in original-image pixel coordinates."""
    class_id: int
    class_name: str
    confidence: float
    box: List[float]  # [x1, y1, x2, y2] in original pixels
    label: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert detection to JSON-serializable dictionary matching TDD v1.1 §6."""
        return {
            "class_id": self.class_id,
            "class_name": self.class_name,
            "label": self.label,
            "confidence": round(self.confidence, 4),
            "box": [round(float(v), 1) for v in self.box],
        }


@dataclass
class DetectionResult:
    """Standardized detection result structure matching TDD v1.1 §6."""
    model: str
    total_detections: int
    class_counts: Dict[str, int]
    detections: List[Detection]
    inference_time_ms: float = 0.0
    image_dimensions: Tuple[int, int] = (0, 0)  # (width, height)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary matching TDD v1.1 §6 and §10.3 specification."""
        counts = dict(self.class_counts)
        return {
            "model": self.model,
            "total_detections": self.total_detections,
            "class_counts": counts,
            "class_summary": counts,
            "detections": [d.to_dict() for d in self.detections],
            "inference_time_ms": round(self.inference_time_ms, 2),
            "image_dimensions": list(self.image_dimensions),
        }


@dataclass
class VisionInspectionResult:
    """High-level inspection result returned by VisionService."""
    result: DetectionResult
    annotated_image_bytes: Optional[bytes] = None
    annotated_output_path: Optional[str] = None
    models_used: List[str] = field(default_factory=list)  # C-01 append-only tracking
    device: str = "cpu"
    success: bool = True
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert inspection result to dictionary."""
        d = self.result.to_dict()
        d["models_used"] = list(self.models_used)
        d["device"] = self.device
        d["success"] = self.success
        if self.annotated_output_path:
            d["annotated_output_path"] = self.annotated_output_path
        if self.error_message:
            d["error_message"] = self.error_message
        return d


@dataclass(frozen=True)
class ModelStatus:
    """Current runtime status of the vision detection service."""
    active_model: Optional[str]
    is_available: bool
    device: str
    nms_mode: str
    classes: List[str]
    fallback_active: bool
    models_used: List[str]
    errors: Dict[str, str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_model": self.active_model,
            "is_available": self.is_available,
            "device": self.device,
            "nms_mode": self.nms_mode,
            "classes": list(self.classes),
            "fallback_active": self.fallback_active,
            "models_used": list(self.models_used),
            "errors": dict(self.errors),
        }


@dataclass(frozen=True)
class VideoMetadata:
    """Extracted container and stream metadata for an input video."""
    filename: str
    width: int
    height: int
    fps: float
    total_frames: int
    duration_s: float
    size_bytes: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "filename": self.filename,
            "width": self.width,
            "height": self.height,
            "fps": round(self.fps, 2),
            "total_frames": self.total_frames,
            "duration_s": round(self.duration_s, 2),
            "size_bytes": self.size_bytes,
        }


@dataclass
class VideoInspectionResult:
    """Complete summary and metrics for a recorded video inference run."""
    input_filename: str
    output_video_path: Optional[str]
    status: str  # 'completed', 'cancelled', 'failed'
    total_frames: int
    frames_processed: int
    frames_with_detections: int
    total_detections: int
    class_summary: Dict[str, int]
    processing_duration_s: float
    processing_fps: float
    model_inference_duration_s: float
    model_inference_fps: float
    models_used: List[str]
    device: str
    conf_threshold: float
    error_message: Optional[str] = None
    metadata: Optional[VideoMetadata] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "input_filename": self.input_filename,
            "output_video_path": self.output_video_path,
            "status": self.status,
            "total_frames": self.total_frames,
            "frames_processed": self.frames_processed,
            "frames_with_detections": self.frames_with_detections,
            "total_detections": self.total_detections,
            "class_summary": dict(self.class_summary),
            "processing_duration_s": round(self.processing_duration_s, 2),
            "processing_fps": round(self.processing_fps, 2),
            "model_inference_duration_s": round(self.model_inference_duration_s, 2),
            "model_inference_fps": round(self.model_inference_fps, 2),
            "models_used": list(self.models_used),
            "device": self.device,
            "conf_threshold": self.conf_threshold,
            "error_message": self.error_message,
            "metadata": self.metadata.to_dict() if self.metadata else None,
        }

