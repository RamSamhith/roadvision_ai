"""RoadVision AI — Computer Vision Service Error Hierarchy (S5-M1).

Implements FR-10 and TDD v1.1 error handling standards for the vision engine.
"""

from __future__ import annotations

from typing import Optional


class VisionServiceError(Exception):
    """Base exception for all RoadVision AI vision service failures."""

    def __init__(self, message: str, code: str = "vision_error", status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code

    def to_dict(self) -> dict:
        return {
            "error": self.code,
            "message": self.message,
            "status_code": self.status_code,
        }


class ModelLoadError(VisionServiceError):
    """Raised when a model checkpoint cannot be loaded or initialized."""

    def __init__(self, message: str, code: str = "model_load_failed"):
        super().__init__(message, code=code, status_code=500)


class ModelChecksumError(ModelLoadError):
    """Raised when a model checkpoint file fails SHA-256 verification."""

    def __init__(self, model_name: str, expected: str, actual: str):
        message = (
            f"Checkpoint checksum mismatch for {model_name}! "
            f"Expected SHA256: {expected}, Actual: {actual}"
        )
        super().__init__(message, code="model_checksum_mismatch")
        self.model_name = model_name
        self.expected = expected
        self.actual = actual


class ModelClassMismatchError(ModelLoadError):
    """Raised when loaded model classes do not match the canonical 4 classes."""

    def __init__(self, message: str):
        super().__init__(message, code="model_class_mismatch")


class ModelUnavailableError(VisionServiceError):
    """Raised when no functional detection model is available in the manager."""

    def __init__(self, message: str = "No road-damage detection model is currently available"):
        super().__init__(message, code="model_unavailable", status_code=503)


class InferenceRuntimeError(VisionServiceError):
    """Raised when a runtime error (e.g. CUDA failure) occurs during forward pass."""

    def __init__(self, message: str):
        super().__init__(message, code="inference_runtime_error", status_code=500)


class ImageValidationError(VisionServiceError):
    """Raised when an input image fails validation checks."""

    def __init__(self, message: str, code: str = "image_validation_failed", status_code: int = 400):
        super().__init__(message, code=code, status_code=status_code)


class UnsupportedImageFormatError(ImageValidationError):
    """Raised when an uploaded file is not one of the allowed image extensions."""

    def __init__(self, ext: str, allowed: set):
        super().__init__(
            f"Unsupported image format '{ext}'. Allowed formats: {sorted(allowed)}",
            code="unsupported_image_format",
            status_code=415,
        )


class ImageSizeExceededError(ImageValidationError):
    """Raised when an image payload exceeds the maximum byte limit."""

    def __init__(self, actual_bytes: int, max_bytes: int):
        super().__init__(
            f"Image payload size ({actual_bytes} bytes) exceeds limit ({max_bytes} bytes).",
            code="image_size_exceeded",
            status_code=413,
        )


class ImageDimensionExceededError(ImageValidationError):
    """Raised when image dimensions or total pixel count exceed limits."""

    def __init__(self, width: int, height: int, max_dim: int):
        super().__init__(
            f"Image dimensions ({width}x{height}) exceed maximum allowed dimension ({max_dim}px).",
            code="image_dimension_exceeded",
            status_code=422,
        )


class ImageDecodeError(ImageValidationError):
    """Raised when image bytes cannot be decoded into a valid pixel matrix."""

    def __init__(self, details: Optional[str] = None):
        msg = "Failed to decode image data into valid pixel matrix."
        if details:
            msg += f" Details: {details}"
        super().__init__(msg, code="image_decode_failed", status_code=400)


# -----------------------------------------------------------------------------
# Video Engine Error Hierarchy (TDD v1.1 §8, §10.2)
# -----------------------------------------------------------------------------
class VideoValidationError(VisionServiceError):
    """Raised when an input video fails validation checks."""

    def __init__(self, message: str, code: str = "video_validation_failed", status_code: int = 400):
        super().__init__(message, code=code, status_code=status_code)


class VideoNotFoundError(VideoValidationError):
    """Raised when the specified video file path does not exist or is not a regular file."""

    def __init__(self, path: str):
        super().__init__(
            f"Video file not found at: {path}",
            code="video_not_found",
            status_code=404,
        )
        self.path = path


class UnsupportedVideoFormatError(VideoValidationError):
    """Raised when an uploaded video has an unsupported extension or container."""

    def __init__(self, ext: str, allowed: set):
        super().__init__(
            f"Unsupported video format '{ext}'. Allowed formats: {sorted(allowed)}",
            code="unsupported_video",
            status_code=415,
        )


class VideoSizeExceededError(VideoValidationError):
    """Raised when a video payload exceeds the maximum byte limit."""

    def __init__(self, actual_bytes: int, max_bytes: int):
        super().__init__(
            f"Video payload size ({actual_bytes} bytes) exceeds limit ({max_bytes} bytes).",
            code="video_size_exceeded",
            status_code=413,
        )


class VideoDurationExceededError(VideoValidationError):
    """Raised when a video duration exceeds the maximum duration limit."""

    def __init__(self, duration_s: float, max_duration_s: float):
        super().__init__(
            f"Video duration ({duration_s:.1f}s) exceeds maximum limit ({max_duration_s:.1f}s).",
            code="video_over_limit",
            status_code=422,
        )


class VideoFrameCountExceededError(VideoValidationError):
    """Raised when the decoded frame count exceeds the maximum allowable threshold."""

    def __init__(self, count: int, max_frames: int):
        super().__init__(
            f"Video frame count ({count}) exceeds maximum threshold ({max_frames} frames).",
            code="video_over_limit",
            status_code=422,
        )
        self.count = count
        self.max_frames = max_frames


class VideoResolutionExceededError(VideoValidationError):
    """Raised when video resolution exceeds limits (e.g. 1920x1080)."""

    def __init__(self, width: int, height: int, max_w: int, max_h: int):
        super().__init__(
            f"Video resolution ({width}x{height}) exceeds maximum limit ({max_w}x{max_h}).",
            code="video_over_limit",
            status_code=422,
        )


class VideoDecodeError(VideoValidationError):
    """Raised when video file cannot be opened or decoded via OpenCV."""

    def __init__(self, details: str = "The video file could not be decoded."):
        super().__init__(details, code="unsupported_video", status_code=415)


class FFmpegNotFoundError(VisionServiceError):
    """Raised when FFmpeg executable is missing or cannot be invoked."""

    def __init__(self, message: str = "FFmpeg executable is unavailable for video encoding."):
        super().__init__(message, code="ffmpeg_unavailable", status_code=503)


class FFmpegExecutionError(VisionServiceError):
    """Raised when FFmpeg subprocess returns a non-zero exit code or fails pipe write."""

    def __init__(self, message: str):
        super().__init__(f"Video encoding failed: {message}", code="video_encoder_failed", status_code=500)


class JobCancelledError(VisionServiceError):
    """Raised when video processing is stopped by user or system cancellation."""

    def __init__(self, message: str = "Video processing was cancelled."):
        super().__init__(message, code="job_cancelled", status_code=409)


class JobTimeoutError(VisionServiceError):
    """Raised when video processing exceeds the maximum job deadline."""

    def __init__(self, timeout_s: float):
        super().__init__(
            f"Video processing exceeded maximum timeout ({timeout_s}s).",
            code="job_timeout",
            status_code=504,
        )

