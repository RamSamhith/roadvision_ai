"""RoadVision AI — Recorded Video Inference & Processing Engine (S5-M3).

Implements TDD v1.1 §8 and PRD v1.1:
- Video input validation (formats, size, duration, resolution, decodability)
- Sequential frame decoding with OpenCV
- YOLO26m forward-pass detection under inference lock
- Non-destructive frame annotation
- Browser-playable H.264 MP4 encoding via FFmpeg (+faststart, yuv420p)
- Comprehensive statistics (processing FPS, model FPS, per-class counts)
- Clean cancellation and partial output deletion
"""

from __future__ import annotations

import collections
import logging
import math
import os
import re
import shutil
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, Final, List, Optional, Tuple, Union

import cv2
import imageio_ffmpeg
import numpy as np

from .annotate import annotate_image
from .classes import CLASS_CODES
from .config import (
    ALLOWED_VIDEO_EXTENSIONS,
    CONFIDENCE_BALANCED,
    CONFIDENCE_HIGH_RECALL,
    CONFIDENCE_MODES,
    DEFAULT_CONFIDENCE,
    MAX_CONFIDENCE,
    MAX_VIDEO_BYTES,
    MAX_VIDEO_DURATION_S,
    MAX_VIDEO_FRAME_CAP,
    MAX_VIDEO_JOB_SECONDS,
    MAX_VIDEO_RESOLUTION,
    MIN_CONFIDENCE,
    REPO_ROOT,
    validate_confidence,
)
from .errors import (
    FFmpegExecutionError,
    FFmpegNotFoundError,
    JobCancelledError,
    JobTimeoutError,
    UnsupportedVideoFormatError,
    VideoDecodeError,
    VideoDurationExceededError,
    VideoFrameCountExceededError,
    VideoNotFoundError,
    VideoResolutionExceededError,
    VideoSizeExceededError,
    VideoValidationError,
)
from .model_manager import ModelManager
from .types import DetectionResult, VideoInspectionResult, VideoMetadata

log = logging.getLogger("roadvision.vision.video_engine")

DEFAULT_OUTPUT_DIR: Final[Path] = REPO_ROOT / "data" / "outputs"


def _drain_stderr(pipe: Any, store: collections.deque[str]) -> None:
    """Continuously drain subprocess stderr pipe to avoid OS buffer deadlocks (D-08)."""
    try:
        for line in iter(pipe.readline, b""):
            if not line:
                break
            try:
                if isinstance(line, (bytes, bytearray)):
                    decoded = line.decode("utf-8", errors="replace").strip()
                elif isinstance(line, str):
                    decoded = line.strip()
                else:
                    decoded = str(line).strip()
                if decoded:
                    store.append(decoded)
            except Exception:
                pass
    except Exception:
        pass
    finally:
        try:
            pipe.close()
        except Exception:
            pass


def get_ffmpeg_executable() -> str:
    """Resolve a functional FFmpeg executable from imageio_ffmpeg or system PATH."""
    try:
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and Path(exe).is_file():
            return str(exe)
    except Exception as e:
        log.warning("imageio_ffmpeg resolution failed: %s", e)

    sys_exe = shutil.which("ffmpeg")
    if sys_exe:
        return sys_exe

    raise FFmpegNotFoundError("FFmpeg executable could not be found.")


def open_h264_writer(
    out_path: Path,
    width: int,
    height: int,
    fps: float,
) -> subprocess.Popen:
    """Open an FFmpeg subprocess that receives raw BGR frames and encodes H.264 MP4.

    Enforces:
    - -vf pad=ceil(iw/2)*2:ceil(ih/2)*2: even dimensions required for yuv420p
    - -pix_fmt yuv420p: universal browser playback compatibility
    - -movflags +faststart: moves moov atom to start for instant streaming
    - -preset veryfast -crf 23: standard speed/quality balance
    """
    ffmpeg_exe = get_ffmpeg_executable()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        ffmpeg_exe,
        "-y",
        "-loglevel", "error",
        "-f", "rawvideo",
        "-pix_fmt", "bgr24",
        "-s", f"{width}x{height}",
        "-r", f"{fps:.3f}",
        "-i", "-",
        "-an",
        "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(out_path),
    ]

    return subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )


def validate_video_file(video_path: Union[str, Path]) -> VideoMetadata:
    """Validate video file integrity, extension, size, resolution, and decodability.

    Raises:
        VideoNotFoundError: If file does not exist (D-03).
        VideoValidationError: If directory path is provided or input is invalid.
        UnsupportedVideoFormatError: If extension is not allowed (.mp4, .avi).
        VideoSizeExceededError: If file exceeds MAX_VIDEO_BYTES (200 MB).
        VideoDecodeError: If OpenCV cannot open or read the stream, or if the
            stream reports an fps or frame count that is not above zero
            (TDD v1.1 §10.2).
        VideoResolutionExceededError: If resolution exceeds MAX_VIDEO_RESOLUTION (1920x1080).
        VideoDurationExceededError: If duration exceeds MAX_VIDEO_DURATION_S (60s).
    """
    path = Path(video_path).resolve()
    if not path.exists():
        raise VideoNotFoundError(str(path))
    if path.is_dir():
        raise VideoValidationError(
            f"Expected a video file, but found a directory: '{path.name}'",
            code="invalid_video_path",
            status_code=400,
        )
    if not path.is_file():
        raise VideoNotFoundError(str(path))

    # 1. Extension validation
    ext = path.suffix.lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise UnsupportedVideoFormatError(ext, ALLOWED_VIDEO_EXTENSIONS)

    # 2. File size validation
    size_bytes = path.stat().st_size
    if size_bytes <= 0:
        raise VideoDecodeError("Video file is empty (0 bytes).")
    if size_bytes > MAX_VIDEO_BYTES:
        raise VideoSizeExceededError(size_bytes, MAX_VIDEO_BYTES)

    # 3. OpenCV decodability validation
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise VideoDecodeError(f"OpenCV failed to open video stream for '{path.name}'.")

    try:
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        raw_fps = float(cap.get(cv2.CAP_PROP_FPS))
        raw_frames = float(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # 3a. Metadata sanity (TDD v1.1 §10.2: fps and frame count above zero).
        # A container that cannot report both cannot be validated for duration
        # or progress, so it is rejected instead of silently substituted.
        if not math.isfinite(raw_fps) or raw_fps <= 0.0:
            raise VideoDecodeError(
                f"Video stream reports an invalid frame rate ({raw_fps}); "
                "an fps above zero is required (TDD v1.1 §10.2)."
            )
        if not math.isfinite(raw_frames) or raw_frames <= 0.0:
            raise VideoDecodeError(
                f"Video stream reports an invalid frame count ({raw_frames}); "
                "a frame count above zero is required (TDD v1.1 §10.2)."
            )
        fps = raw_fps
        reported_frames = int(raw_frames)

        # Test read first frame to verify decodability
        ok, first_frame = cap.read()
        if not ok or first_frame is None or first_frame.size == 0:
            raise VideoDecodeError(f"Failed to decode first frame of '{path.name}'.")

        # Basic dimension sanity
        if width <= 0 or height <= 0:
            raise VideoDecodeError(f"Invalid video dimensions: {width}x{height}")

        # 4. Resolution check (PRD v1.1 §4.11 / TDD v1.1 §10.2: max 1920x1080)
        max_w, max_h = MAX_VIDEO_RESOLUTION
        if width > max_w or height > max_h:
            raise VideoResolutionExceededError(width, height, max_w, max_h)

        # 5. Duration check (frame count and fps are guaranteed above zero by step 3a)
        duration_s = reported_frames / fps
        if duration_s > MAX_VIDEO_DURATION_S:
            raise VideoDurationExceededError(duration_s, MAX_VIDEO_DURATION_S)

        return VideoMetadata(
            filename=path.name,
            width=width,
            height=height,
            fps=fps,
            total_frames=reported_frames,
            duration_s=duration_s,
            size_bytes=size_bytes,
        )
    finally:
        cap.release()


class VideoEngine:
    """Processes recorded video files through YOLO26m road-damage detection."""

    def __init__(self, model_manager: ModelManager):
        self.model_manager = model_manager

    def process_video(
        self,
        video_input: Union[str, Path],
        conf: Union[float, str] = DEFAULT_CONFIDENCE,
        output_path: Optional[Union[str, Path]] = None,
        cancel_event: Optional[threading.Event] = None,
        progress_callback: Optional[Callable[[int, int, int, Dict[str, int]], None]] = None,
        timeout_s: float = MAX_VIDEO_JOB_SECONDS,
        raise_on_cancel: bool = False,
    ) -> VideoInspectionResult:
        """Execute full video processing pipeline with H.264 MP4 export.

        Args:
            video_input: Path to source video file (MP4 or AVI).
            conf: Confidence threshold as a float [0.10, 0.90] or mode string
                ('balanced' -> 0.25, 'high_recall' -> 0.15). Values outside the
                range are clamped and logged; strict rejection is enforced at the
                API boundary (TDD v1.1 §10).
            output_path: Target path for the annotated MP4 video.
            cancel_event: Optional threading.Event to signal job cancellation.
            progress_callback: Optional callback(frames_done, total_frames, hits, counts).
            timeout_s: Maximum execution duration before timing out.
            raise_on_cancel: If True, raises JobCancelledError upon cancellation.

        Returns:
            VideoInspectionResult with full per-frame counts and timing metrics.
        """
        input_path = Path(video_input).resolve()
        # 1. Validate video input
        meta = validate_video_file(input_path)

        # 2. Resolve output path safely (D-06: Safe default filenames)
        if output_path is None:
            DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            timestamp_str = time.strftime("%Y%m%d_%H%M%S")
            sanitized = re.sub(r"[^A-Za-z0-9_-]", "_", input_path.stem).strip("_")
            reserved_names = {
                "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4",
                "COM5", "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2",
                "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
            }
            if not sanitized or sanitized.upper() in reserved_names:
                sanitized = "video"
            sanitized = sanitized[:24]
            unique_hex = uuid.uuid4().hex[:8]
            safe_name = f"{timestamp_str}_{sanitized}_{unique_hex}_annotated.mp4"
            out_p = (DEFAULT_OUTPUT_DIR / safe_name).resolve()
        else:
            out_p = Path(output_path).resolve()

        # D-04: Resolve mode strings or validate/clamp confidence
        if isinstance(conf, str):
            try:
                requested_conf = validate_confidence(conf)
            except ValueError:
                requested_conf = float(conf)
        else:
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

        # 3. Check for immediate pre-start cancellation (D-10)
        if cancel_event is not None and cancel_event.is_set():
            if raise_on_cancel:
                raise JobCancelledError("Job cancelled by request before processing started.")
            return VideoInspectionResult(
                input_filename=input_path.name,
                output_video_path=None,
                status="cancelled",
                total_frames=meta.total_frames,
                frames_processed=0,
                frames_with_detections=0,
                total_detections=0,
                class_summary={k: 0 for k in CLASS_CODES},
                processing_duration_s=0.0,
                processing_fps=0.0,
                model_inference_duration_s=0.0,
                model_inference_fps=0.0,
                models_used=list(self.model_manager.models_used),
                device=self.model_manager.device,
                conf_threshold=clamped_conf,
                error_message="Cancelled before processing started.",
                metadata=meta,
            )

        # D-09: Frame count cap protection based on metadata fps and duration limit
        max_allowed_frames = min(
            MAX_VIDEO_FRAME_CAP,
            int(meta.fps * MAX_VIDEO_DURATION_S) + int(meta.fps * 2.0),
        )

        cap: Optional[cv2.VideoCapture] = None
        proc: Optional[subprocess.Popen] = None
        status = "failed"
        err_msg: Optional[str] = None

        frames_processed = 0
        frames_with_detections = 0
        total_detections = 0
        class_summary = {k: 0 for k in CLASS_CODES}

        t_start = time.perf_counter()
        total_model_time = 0.0
        deadline = time.monotonic() + timeout_s
        last_progress_time = 0.0
        stderr_lines: collections.deque[str] = collections.deque(maxlen=100)

        try:
            cap = cv2.VideoCapture(str(input_path))
            proc = open_h264_writer(out_p, meta.width, meta.height, meta.fps)

            # D-08: Continuously drain FFmpeg stderr in background to avoid pipe deadlock
            if proc.stderr is not None:
                drain_thread = threading.Thread(
                    target=_drain_stderr,
                    args=(proc.stderr, stderr_lines),
                    daemon=True,
                )
                drain_thread.start()

            while True:
                # Check cancellation (D-10)
                if cancel_event is not None and cancel_event.is_set():
                    status = "cancelled"
                    err_msg = "Job cancelled by request."
                    break

                # Check timeout (D-07)
                if time.monotonic() > deadline:
                    raise JobTimeoutError(timeout_s)

                ok, frame = cap.read()
                if not ok or frame is None:
                    # Normal completion of video stream
                    status = "completed"
                    break

                # D-09: Enforce decoded frame cap
                if frames_processed >= max_allowed_frames:
                    log.warning(
                        "Video stream produced %d frames, exceeding maximum frame cap of %d.",
                        frames_processed + 1,
                        max_allowed_frames,
                    )
                    raise VideoFrameCountExceededError(frames_processed + 1, max_allowed_frames)

                # Inference pass
                t0_inf = time.perf_counter()
                det_res: DetectionResult = self.model_manager.predict(frame, conf=clamped_conf)
                total_model_time += (time.perf_counter() - t0_inf)

                # Accumulate counts
                num_hits = det_res.total_detections
                total_detections += num_hits
                if num_hits > 0:
                    frames_with_detections += 1
                for k, v in det_res.class_counts.items():
                    class_summary[k] += v

                # Draw non-destructive annotations
                annotated_frame = annotate_image(frame, det_res)

                # Pipe to FFmpeg stdin
                try:
                    proc.stdin.write(annotated_frame.tobytes())
                except (BrokenPipeError, OSError) as e:
                    raise FFmpegExecutionError(f"Broken pipe while writing frame: {e}") from e

                frames_processed += 1

                # Periodic progress callback (~once per second)
                now = time.monotonic()
                if progress_callback is not None and (now - last_progress_time >= 1.0):
                    try:
                        progress_callback(
                            frames_processed,
                            meta.total_frames,
                            total_detections,
                            dict(class_summary),
                        )
                    except Exception as cb_err:
                        log.warning("Progress callback raised: %s", cb_err)
                    last_progress_time = now

            # Close stdin and wait for FFmpeg to finalize container and faststart (D-07)
            if proc and proc.stdin:
                try:
                    proc.stdin.close()
                except Exception:
                    pass

            if proc:
                remaining_s = max(0.5, deadline - time.monotonic())
                try:
                    retcode = proc.wait(timeout=min(remaining_s, 60.0))
                except subprocess.TimeoutExpired:
                    log.warning("FFmpeg process wait timed out; terminating forcefully.")
                    proc.kill()
                    try:
                        proc.wait(timeout=5.0)
                    except Exception:
                        pass
                    raise JobTimeoutError(timeout_s)

                if retcode != 0 and status != "cancelled":
                    stderr_txt = "\n".join(stderr_lines)[:500] if stderr_lines else ""
                    raise FFmpegExecutionError(f"FFmpeg exited with code {retcode}: {stderr_txt}")

        except Exception as e:
            status = "failed"
            err_msg = str(e)
            log.exception("Video processing failed: %s", e)
            raise
        finally:
            if cap is not None:
                cap.release()
            if proc is not None and proc.poll() is None:
                try:
                    proc.kill()
                    proc.wait(timeout=5.0)
                except Exception:
                    pass

            # PRD v1.1 FR-09 / AC-05: never leave partial output on failure or cancellation
            if status != "completed" and out_p.is_file():
                try:
                    out_p.unlink(missing_ok=True)
                    log.info("Cleaned up partial output video at: %s", out_p)
                except Exception as del_err:
                    log.warning("Failed to delete partial output: %s", del_err)

        total_duration = time.perf_counter() - t_start
        proc_fps = (frames_processed / total_duration) if total_duration > 0 else 0.0
        model_fps = (frames_processed / total_model_time) if total_model_time > 0 else 0.0

        # Final progress callback invocation upon completion
        if progress_callback is not None and status == "completed":
            try:
                progress_callback(
                    frames_processed,
                    meta.total_frames,
                    total_detections,
                    dict(class_summary),
                )
            except Exception:
                pass

        if status == "cancelled" and raise_on_cancel:
            raise JobCancelledError(err_msg or "Job cancelled by request.")

        return VideoInspectionResult(
            input_filename=input_path.name,
            output_video_path=str(out_p) if status == "completed" else None,
            status=status,
            total_frames=meta.total_frames,
            frames_processed=frames_processed,
            frames_with_detections=frames_with_detections,
            total_detections=total_detections,
            class_summary=class_summary,
            processing_duration_s=total_duration,
            processing_fps=proc_fps,
            model_inference_duration_s=total_model_time,
            model_inference_fps=model_fps,
            models_used=list(self.model_manager.models_used),
            device=self.model_manager.device,
            conf_threshold=clamped_conf,
            error_message=err_msg,
            metadata=meta,
        )

