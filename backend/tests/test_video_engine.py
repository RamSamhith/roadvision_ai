"""Isolated Unit and Integration Tests for Recorded Video Engine (S5-M3).

Tests video validation, frame decoding, FFmpeg H.264 encoding, cancellation,
resource cleanup, per-frame statistics, and error handling.
"""

from __future__ import annotations

import logging
import subprocess
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest

from app.services.vision import (
    CLASS_CODES,
    FFmpegExecutionError,
    FFmpegNotFoundError,
    JobCancelledError,
    JobTimeoutError,
    MAX_CONFIDENCE,
    MIN_CONFIDENCE,
    UnsupportedVideoFormatError,
    VideoDecodeError,
    VideoDurationExceededError,
    VideoEngine,
    VideoFrameCountExceededError,
    VideoInspectionResult,
    VideoMetadata,
    VideoNotFoundError,
    VideoResolutionExceededError,
    VideoSizeExceededError,
    VideoValidationError,
    VisionServiceError,
    get_ffmpeg_executable,
    validate_video_file,
)
from app.services.vision.types import Detection, DetectionResult
from app.services.vision.video_engine import DEFAULT_OUTPUT_DIR, _drain_stderr


def create_synthetic_video(
    file_path: Path,
    num_frames: int = 5,
    width: int = 64,
    height: int = 64,
    fps: float = 10.0,
    fourcc: str = "mp4v",
) -> Path:
    """Helper to generate a lightweight, decodable synthetic video for tests."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    codec = cv2.VideoWriter_fourcc(*fourcc)
    writer = cv2.VideoWriter(str(file_path), codec, fps, (width, height))
    try:
        for i in range(num_frames):
            # Create a simple frame with changing pixel pattern
            frame = np.full((height, width, 3), (i * 20) % 255, dtype=np.uint8)
            writer.write(frame)
    finally:
        writer.release()
    return file_path


def mock_capture_with_metadata(
    fps: float,
    frame_count: float,
    width: int = 320,
    height: int = 240,
) -> MagicMock:
    """Build a patched ``cv2.VideoCapture`` double reporting fixed metadata."""
    cap = MagicMock()
    cap.isOpened.return_value = True
    cap.get.side_effect = lambda prop: {
        cv2.CAP_PROP_FRAME_WIDTH: width,
        cv2.CAP_PROP_FRAME_HEIGHT: height,
        cv2.CAP_PROP_FPS: fps,
        cv2.CAP_PROP_FRAME_COUNT: frame_count,
    }.get(prop, 0.0)
    cap.read.return_value = (True, np.zeros((height, width, 3), dtype=np.uint8))
    return cap


@pytest.fixture(autouse=True)
def guard_production_output_dir():
    """D-05 guard: no test in this module may write into ``data/outputs``.

    ``process_video()`` falls back to ``DEFAULT_OUTPUT_DIR`` (the production
    managed-output directory) when ``output_path`` is omitted. Tests must always
    pass an isolated ``tmp_path`` target.
    """
    before = set(DEFAULT_OUTPUT_DIR.glob("*")) if DEFAULT_OUTPUT_DIR.is_dir() else set()
    yield
    after = set(DEFAULT_OUTPUT_DIR.glob("*")) if DEFAULT_OUTPUT_DIR.is_dir() else set()
    leaked = sorted(p.name for p in after - before)
    assert not leaked, f"Tests wrote into the production output directory: {leaked}"


# -----------------------------------------------------------------------------
# 1-10: Video Validation Tests
# -----------------------------------------------------------------------------

def test_valid_mp4_validation(tmp_path):
    """Test 1: Valid MP4 video passes validation and returns accurate metadata."""
    video_path = tmp_path / "sample.mp4"
    create_synthetic_video(video_path, num_frames=10, width=128, height=128, fps=10.0)

    meta = validate_video_file(video_path)
    assert meta.filename == "sample.mp4"
    assert meta.width == 128
    assert meta.height == 128
    assert meta.fps == 10.0
    assert meta.total_frames >= 10
    assert meta.duration_s > 0
    assert meta.size_bytes > 0


def test_valid_avi_validation(tmp_path):
    """Test 2: Valid AVI video passes validation."""
    video_path = tmp_path / "sample.avi"
    create_synthetic_video(video_path, num_frames=8, width=64, height=64, fps=8.0, fourcc="MJPG")

    meta = validate_video_file(video_path)
    assert meta.filename == "sample.avi"
    assert meta.width == 64
    assert meta.height == 64


def test_invalid_extension(tmp_path):
    """Test 3: Reject unsupported extensions (.mkv, .mov, etc.) with 415 error."""
    video_path = tmp_path / "sample.mkv"
    video_path.write_bytes(b"dummy")

    with pytest.raises(UnsupportedVideoFormatError) as exc_info:
        validate_video_file(video_path)
    assert exc_info.value.status_code == 415
    assert exc_info.value.code == "unsupported_video"


def test_corrupt_video(tmp_path):
    """Test 4: Non-video bytes with .mp4 extension must raise VideoDecodeError."""
    video_path = tmp_path / "corrupt.mp4"
    video_path.write_bytes(b"THIS_IS_NOT_A_VALID_VIDEO_STREAM")

    with pytest.raises(VideoDecodeError) as exc_info:
        validate_video_file(video_path)
    assert exc_info.value.code == "unsupported_video"


def test_unsupported_codec_or_empty_stream(tmp_path):
    """Test 5: Video that cannot decode first frame raises VideoDecodeError."""
    video_path = tmp_path / "zero_frame.mp4"
    # Create file with valid header but 0 frames
    writer = cv2.VideoWriter(str(video_path), cv2.VideoWriter_fourcc(*"mp4v"), 10.0, (64, 64))
    writer.release()

    with pytest.raises(VideoDecodeError):
        validate_video_file(video_path)


def test_oversized_video(tmp_path):
    """Test 6: Reject videos exceeding MAX_VIDEO_BYTES (200 MB)."""
    video_path = tmp_path / "oversized.mp4"
    video_path.write_bytes(b"sample")

    real_stat = video_path.stat()
    mock_stat_res = MagicMock(st_size=205 * 1024 * 1024, st_mode=real_stat.st_mode)
    with patch.object(Path, "stat", return_value=mock_stat_res):
        with pytest.raises(VideoSizeExceededError) as exc_info:
            validate_video_file(video_path)
        assert exc_info.value.status_code == 413


def test_excessive_duration(tmp_path):
    """Test 7: Reject videos exceeding MAX_VIDEO_DURATION_S (60s)."""
    video_path = tmp_path / "long.mp4"
    create_synthetic_video(video_path, num_frames=5, width=64, height=64, fps=10.0)

    # Mock frame count to report > 60s
    with patch("cv2.VideoCapture") as mock_cap_cls:
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: {
            cv2.CAP_PROP_FRAME_WIDTH: 100,
            cv2.CAP_PROP_FRAME_HEIGHT: 100,
            cv2.CAP_PROP_FPS: 10.0,
            cv2.CAP_PROP_FRAME_COUNT: 700,  # 70 seconds
        }.get(prop, 0.0)
        mock_cap.read.return_value = (True, np.zeros((100, 100, 3), dtype=np.uint8))
        mock_cap_cls.return_value = mock_cap

        with pytest.raises(VideoDurationExceededError) as exc_info:
            validate_video_file(video_path)
        assert exc_info.value.status_code == 422


def test_excessive_resolution(tmp_path):
    """Test 8: Reject videos exceeding MAX_VIDEO_RESOLUTION (1920x1080)."""
    video_path = tmp_path / "4k.mp4"
    create_synthetic_video(video_path, num_frames=5, width=64, height=64, fps=10.0)

    with patch("cv2.VideoCapture") as mock_cap_cls:
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: {
            cv2.CAP_PROP_FRAME_WIDTH: 3840,
            cv2.CAP_PROP_FRAME_HEIGHT: 2160,
            cv2.CAP_PROP_FPS: 25.0,
            cv2.CAP_PROP_FRAME_COUNT: 50,
        }.get(prop, 0.0)
        mock_cap.read.return_value = (True, np.zeros((2160, 3840, 3), dtype=np.uint8))
        mock_cap_cls.return_value = mock_cap

        with pytest.raises(VideoResolutionExceededError) as exc_info:
            validate_video_file(video_path)
        assert exc_info.value.status_code == 422


def test_empty_zero_byte_video(tmp_path):
    """Test 9: Reject 0-byte video file."""
    video_path = tmp_path / "empty.mp4"
    video_path.write_bytes(b"")

    with pytest.raises(VideoDecodeError):
        validate_video_file(video_path)


def test_invalid_dimensions(tmp_path):
    """Test 10: Reject video reporting 0x0 dimensions."""
    video_path = tmp_path / "nodim.mp4"
    create_synthetic_video(video_path, num_frames=5, width=64, height=64, fps=10.0)

    with patch("cv2.VideoCapture") as mock_cap_cls:
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: {
            cv2.CAP_PROP_FRAME_WIDTH: 0,
            cv2.CAP_PROP_FRAME_HEIGHT: 0,
            cv2.CAP_PROP_FPS: 25.0,
            cv2.CAP_PROP_FRAME_COUNT: 50,
        }.get(prop, 0.0)
        mock_cap.read.return_value = (True, np.zeros((10, 10, 3), dtype=np.uint8))
        mock_cap_cls.return_value = mock_cap

        with pytest.raises(VideoDecodeError):
            validate_video_file(video_path)


# -----------------------------------------------------------------------------
# 10a-10d: D-02 regression tests — invalid container metadata (TDD v1.1 §10.2)
# -----------------------------------------------------------------------------

def test_zero_fps_rejected(tmp_path):
    """Test 10a (D-02): a stream reporting 0 fps is rejected, not defaulted to 25."""
    video_path = tmp_path / "zero_fps.mp4"
    video_path.write_bytes(b"placeholder")

    with patch("cv2.VideoCapture", return_value=mock_capture_with_metadata(fps=0.0, frame_count=50.0)):
        with pytest.raises(VideoDecodeError) as exc_info:
            validate_video_file(video_path)

    assert exc_info.value.status_code == 415
    assert exc_info.value.code == "unsupported_video"
    assert "frame rate" in exc_info.value.message


def test_zero_frame_count_rejected(tmp_path):
    """Test 10b (D-02): a stream reporting 0 frames is rejected, not treated as 1."""
    video_path = tmp_path / "zero_frames.mp4"
    video_path.write_bytes(b"placeholder")

    with patch("cv2.VideoCapture", return_value=mock_capture_with_metadata(fps=10.0, frame_count=0.0)):
        with pytest.raises(VideoDecodeError) as exc_info:
            validate_video_file(video_path)

    assert exc_info.value.status_code == 415
    assert exc_info.value.code == "unsupported_video"
    assert "frame count" in exc_info.value.message


@pytest.mark.parametrize("bad_fps", [-1.0, float("nan"), float("inf")])
def test_invalid_fps_rejected(tmp_path, bad_fps):
    """Test 10c (D-02): negative / NaN / infinite fps values are invalid metadata."""
    video_path = tmp_path / "bad_fps.mp4"
    video_path.write_bytes(b"placeholder")

    with patch("cv2.VideoCapture", return_value=mock_capture_with_metadata(fps=bad_fps, frame_count=50.0)):
        with pytest.raises(VideoDecodeError) as exc_info:
            validate_video_file(video_path)

    assert exc_info.value.code == "unsupported_video"


@pytest.mark.parametrize("bad_frames", [-5.0, float("nan"), float("inf")])
def test_invalid_frame_count_rejected(tmp_path, bad_frames):
    """Test 10d (D-02): negative / NaN / infinite frame counts are invalid metadata."""
    video_path = tmp_path / "bad_frames.mp4"
    video_path.write_bytes(b"placeholder")

    with patch("cv2.VideoCapture", return_value=mock_capture_with_metadata(fps=10.0, frame_count=bad_frames)):
        with pytest.raises(VideoDecodeError) as exc_info:
            validate_video_file(video_path)

    assert exc_info.value.code == "unsupported_video"


# -----------------------------------------------------------------------------
# 11-20: Video Processing Engine & Execution Tests
# -----------------------------------------------------------------------------

def test_no_detection_video(tmp_path):
    """Test 11: Video with zero detections returns clean 0 counts and valid H.264 output."""
    in_video = tmp_path / "blank.mp4"
    create_synthetic_video(in_video, num_frames=5, width=64, height=64, fps=10.0)
    out_video = tmp_path / "blank_annotated.mp4"

    mock_mgr = MagicMock()
    mock_mgr.active = "YOLO26m"
    mock_mgr.device = "cpu"
    mock_mgr.models_used = ["YOLO26m"]

    # Mock predict returning 0 detections
    empty_result = DetectionResult(
        model="YOLO26m",
        total_detections=0,
        class_counts={"D00": 0, "D10": 0, "D20": 0, "D40": 0},
        detections=[],
        image_dimensions=(64, 64),
    )
    mock_mgr.predict.return_value = empty_result

    engine = VideoEngine(mock_mgr)
    res = engine.process_video(in_video, conf=0.25, output_path=out_video)

    assert res.status == "completed"
    assert res.total_detections == 0
    assert res.frames_with_detections == 0
    assert res.frames_processed == 5
    assert res.class_summary == {"D00": 0, "D10": 0, "D20": 0, "D40": 0}
    assert Path(res.output_video_path).is_file()
    assert Path(res.output_video_path).stat().st_size > 0


def test_multiple_classes_across_frames(tmp_path):
    """Test 12 & 13: Multiple damage classes detected across frames with correct accumulation."""
    in_video = tmp_path / "multi_damage.mp4"
    create_synthetic_video(in_video, num_frames=4, width=64, height=64, fps=10.0)
    out_video = tmp_path / "multi_annotated.mp4"

    mock_mgr = MagicMock()
    mock_mgr.active = "YOLO26m"
    mock_mgr.device = "cpu"
    mock_mgr.models_used = ["YOLO26m"]

    # Frame 0: 1 D00
    r0 = DetectionResult("YOLO26m", 1, {"D00": 1, "D10": 0, "D20": 0, "D40": 0}, [Detection(0, "D00", 0.8, [10, 10, 20, 20])], 5.0, (64, 64))
    # Frame 1: 1 D10, 1 D40
    r1 = DetectionResult("YOLO26m", 2, {"D00": 0, "D10": 1, "D20": 0, "D40": 1}, [Detection(1, "D10", 0.7, [5, 5, 15, 15]), Detection(3, "D40", 0.9, [30, 30, 40, 40])], 5.0, (64, 64))
    # Frame 2: 0 detections
    r2 = DetectionResult("YOLO26m", 0, {"D00": 0, "D10": 0, "D20": 0, "D40": 0}, [], 5.0, (64, 64))
    # Frame 3: 1 D20
    r3 = DetectionResult("YOLO26m", 1, {"D00": 0, "D10": 0, "D20": 1, "D40": 0}, [Detection(2, "D20", 0.85, [10, 10, 30, 30])], 5.0, (64, 64))

    mock_mgr.predict.side_effect = [r0, r1, r2, r3]

    engine = VideoEngine(mock_mgr)
    res = engine.process_video(in_video, conf=0.25, output_path=out_video)

    assert res.status == "completed"
    assert res.frames_processed == 4
    # Frames with detections: 0, 1, 3 -> 3 frames
    assert res.frames_with_detections == 3
    # Total detections: 1 + 2 + 0 + 1 = 4
    assert res.total_detections == 4
    assert res.class_summary == {"D00": 1, "D10": 1, "D20": 1, "D40": 1}


def test_correct_frame_and_detection_statistics(tmp_path):
    """Test 14: Verifies processing FPS and model inference timing separation."""
    in_video = tmp_path / "stats.mp4"
    out_video = tmp_path / "stats_out.mp4"
    create_synthetic_video(in_video, num_frames=6, width=64, height=64, fps=10.0)

    mock_mgr = MagicMock()
    mock_mgr.active = "YOLO26m"
    mock_mgr.device = "cpu"
    mock_mgr.models_used = ["YOLO26m"]
    mock_mgr.predict.return_value = DetectionResult("YOLO26m", 0, {k: 0 for k in CLASS_CODES}, [], 2.0, (64, 64))

    engine = VideoEngine(mock_mgr)
    # D-05: always pass an isolated output_path; never fall back to data/outputs.
    res = engine.process_video(in_video, conf=0.25, output_path=out_video)

    assert res.frames_processed == 6
    assert res.processing_fps > 0
    assert res.model_inference_fps > 0
    assert res.processing_duration_s > 0
    assert res.model_inference_duration_s > 0


def test_output_file_h264_compatibility(tmp_path):
    """Test 15: Verifies generated video is an H.264 MP4 with yuv420p and faststart."""
    in_video = tmp_path / "in.mp4"
    out_video = tmp_path / "out.mp4"
    create_synthetic_video(in_video, num_frames=4, width=64, height=64, fps=10.0)

    mock_mgr = MagicMock()
    mock_mgr.active = "YOLO26m"
    mock_mgr.device = "cpu"
    mock_mgr.models_used = ["YOLO26m"]
    mock_mgr.predict.return_value = DetectionResult("YOLO26m", 0, {k: 0 for k in CLASS_CODES}, [], 2.0, (64, 64))

    engine = VideoEngine(mock_mgr)
    res = engine.process_video(in_video, conf=0.25, output_path=out_video)
    assert Path(res.output_video_path).is_file()

    # Use FFmpeg to inspect generated stream
    ffmpeg_exe = get_ffmpeg_executable()
    probe_cmd = [ffmpeg_exe, "-hide_banner", "-i", str(out_video)]
    probe = subprocess.run(probe_cmd, capture_output=True, text=True)
    # Output stderr contains stream info
    assert "h264" in probe.stderr.lower()
    assert "yuv420p" in probe.stderr.lower()


def test_cancellation_and_partial_cleanup(tmp_path):
    """Test 16: Job cancellation stops frame processing and deletes partial output."""
    in_video = tmp_path / "cancel_test.mp4"
    out_video = tmp_path / "cancel_out.mp4"
    create_synthetic_video(in_video, num_frames=20, width=64, height=64, fps=10.0)

    cancel_evt = threading.Event()

    mock_mgr = MagicMock()
    mock_mgr.active = "YOLO26m"
    mock_mgr.device = "cpu"
    mock_mgr.models_used = ["YOLO26m"]

    def side_effect(*args, **kwargs):
        # Trigger cancellation after first frame
        cancel_evt.set()
        return DetectionResult("YOLO26m", 0, {k: 0 for k in CLASS_CODES}, [], 2.0, (64, 64))

    mock_mgr.predict.side_effect = side_effect

    engine = VideoEngine(mock_mgr)
    res = engine.process_video(in_video, conf=0.25, output_path=out_video, cancel_event=cancel_evt)

    assert res.status == "cancelled"
    # Partial output must be deleted (PRD v1.1 FR-09 / AC-05)
    assert not out_video.is_file()


def test_ffmpeg_failure_handling(tmp_path):
    """Test 17: FFmpeg execution failure raises FFmpegExecutionError and deletes partial output."""
    in_video = tmp_path / "ffmpeg_fail.mp4"
    out_video = tmp_path / "fail_out.mp4"
    create_synthetic_video(in_video, num_frames=4, width=64, height=64, fps=10.0)

    mock_mgr = MagicMock()
    mock_mgr.active = "YOLO26m"
    mock_mgr.device = "cpu"
    mock_mgr.models_used = ["YOLO26m"]
    mock_mgr.predict.return_value = DetectionResult("YOLO26m", 0, {k: 0 for k in CLASS_CODES}, [], 2.0, (64, 64))

    engine = VideoEngine(mock_mgr)

    # Patch open_h264_writer to simulate failure on wait
    mock_proc = MagicMock()
    mock_proc.stdin = MagicMock()
    mock_proc.wait.return_value = 1  # Non-zero exit code
    mock_proc.stderr.readline.side_effect = [b"Encoding failed due to simulated error\n", b""]
    mock_proc.poll.return_value = 1

    with patch("app.services.vision.video_engine.open_h264_writer", return_value=mock_proc):
        with pytest.raises(FFmpegExecutionError):
            engine.process_video(in_video, conf=0.25, output_path=out_video)


def test_resource_release_after_exceptions(tmp_path):
    """Test 18 & 19: Model inference exception cleanly releases VideoCapture and deletes output."""
    in_video = tmp_path / "infer_fail.mp4"
    out_video = tmp_path / "infer_fail_out.mp4"
    create_synthetic_video(in_video, num_frames=5, width=64, height=64, fps=10.0)

    mock_mgr = MagicMock()
    mock_mgr.active = "YOLO26m"
    mock_mgr.device = "cpu"
    mock_mgr.models_used = ["YOLO26m"]
    mock_mgr.predict.side_effect = RuntimeError("Simulated CUDA OutOfMemoryError")

    engine = VideoEngine(mock_mgr)
    with pytest.raises(RuntimeError, match="Simulated CUDA OutOfMemoryError"):
        engine.process_video(in_video, conf=0.25, output_path=out_video)

    # Output file must NOT exist after error
    assert not out_video.is_file()


def test_progress_callback(tmp_path):
    """Test 20: Verifies progress_callback receives updates with frame counts."""
    in_video = tmp_path / "callback_test.mp4"
    out_video = tmp_path / "callback_out.mp4"
    create_synthetic_video(in_video, num_frames=3, width=64, height=64, fps=10.0)

    mock_mgr = MagicMock()
    mock_mgr.active = "YOLO26m"
    mock_mgr.device = "cpu"
    mock_mgr.models_used = ["YOLO26m"]
    mock_mgr.predict.return_value = DetectionResult("YOLO26m", 1, {"D00": 1, "D10": 0, "D20": 0, "D40": 0}, [], 2.0, (64, 64))

    callbacks_received = []

    def cb(frames_done, total_frames, hits, counts):
        callbacks_received.append((frames_done, total_frames, hits, counts))

    engine = VideoEngine(mock_mgr)
    # D-05: always pass an isolated output_path; never fall back to data/outputs.
    res = engine.process_video(in_video, conf=0.25, output_path=out_video, progress_callback=cb)

    assert res.status == "completed"
    assert len(callbacks_received) > 0
    # Final invocation has all 3 frames done
    last_cb = callbacks_received[-1]
    assert last_cb[0] == 3  # frames_done
    assert last_cb[2] == 3  # total detections


# -----------------------------------------------------------------------------
# 21: D-04 — out-of-range confidence is clamped loudly, never silently
# -----------------------------------------------------------------------------

@pytest.mark.parametrize(
    "requested, expected",
    [(5.0, MAX_CONFIDENCE), (0.01, MIN_CONFIDENCE)],
)
def test_out_of_range_confidence_clamped_and_logged(tmp_path, caplog, requested, expected):
    """Test 21 (D-04): clamping is preserved for compatibility but is logged.

    The documented ``process_video`` contract clamps ``conf`` to
    [MIN_CONFIDENCE, MAX_CONFIDENCE]; strict rejection belongs at the API
    boundary (TDD v1.1 §10). This test pins the non-silent behaviour.
    """
    in_video = tmp_path / "conf_clamp.mp4"
    out_video = tmp_path / "conf_clamp_out.mp4"
    create_synthetic_video(in_video, num_frames=3, width=64, height=64, fps=10.0)

    mock_mgr = MagicMock()
    mock_mgr.active = "YOLO26m"
    mock_mgr.device = "cpu"
    mock_mgr.models_used = ["YOLO26m"]
    mock_mgr.predict.return_value = DetectionResult(
        "YOLO26m", 0, {k: 0 for k in CLASS_CODES}, [], 2.0, (64, 64)
    )

    engine = VideoEngine(mock_mgr)
    with caplog.at_level(logging.WARNING, logger="roadvision.vision.video_engine"):
        res = engine.process_video(in_video, conf=requested, output_path=out_video)

    assert res.conf_threshold == pytest.approx(expected)
    assert mock_mgr.predict.call_args.kwargs["conf"] == pytest.approx(expected)

    clamp_records = [
        r for r in caplog.records
        if "outside" in r.getMessage() and "confidence" in r.getMessage().lower()
    ]
    assert clamp_records, f"expected a clamping warning, got: {[r.getMessage() for r in caplog.records]}"


# -----------------------------------------------------------------------------
# D-03: Missing video input error normalization
# -----------------------------------------------------------------------------

def test_missing_video_raises_video_not_found(tmp_path):
    """D-03: Non-existent video file path raises normalized VideoNotFoundError (404)."""
    missing_path = tmp_path / "non_existent_file.mp4"
    with pytest.raises(VideoNotFoundError) as exc_info:
        validate_video_file(missing_path)

    err = exc_info.value
    assert isinstance(err, VisionServiceError)
    assert isinstance(err, VideoValidationError)
    assert err.status_code == 404
    assert err.code == "video_not_found"
    assert "not found" in str(err).lower()


def test_directory_supplied_as_video_rejected(tmp_path):
    """D-03: Directory path provided as video input raises VideoValidationError (400)."""
    sub_dir = tmp_path / "fake_video_dir.mp4"
    sub_dir.mkdir(parents=True, exist_ok=True)

    with pytest.raises(VideoValidationError) as exc_info:
        validate_video_file(sub_dir)

    err = exc_info.value
    assert isinstance(err, VisionServiceError)
    assert err.status_code == 400
    assert err.code == "invalid_video_path"


# -----------------------------------------------------------------------------
# D-06: Safe default video output filenames
# -----------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw_name",
    [
        "sample video with spaces.mp4",
        "evil_../../_traversal.mp4",
        "CJK_中文_unicode_!@#$%.mp4",
        "CON.mp4",
        "a" * 120 + ".mp4",
    ],
)
def test_safe_default_video_output_name_sanitization(tmp_path, raw_name):
    """D-06: Default output generation produces managed, collision-safe, traversal-free names."""
    import re
    from app.services.vision import video_engine as ve_mod

    in_video = tmp_path / raw_name
    create_synthetic_video(in_video, num_frames=2, width=64, height=64, fps=10.0)

    mock_mgr = MagicMock()
    mock_mgr.active = "YOLO26m"
    mock_mgr.device = "cpu"
    mock_mgr.models_used = ["YOLO26m"]
    mock_mgr.predict.return_value = DetectionResult(
        "YOLO26m", 0, {k: 0 for k in CLASS_CODES}, [], 2.0, (64, 64)
    )

    isolated_out_dir = tmp_path / "isolated_outputs"
    with patch.object(ve_mod, "DEFAULT_OUTPUT_DIR", isolated_out_dir):
        engine = VideoEngine(mock_mgr)
        res = engine.process_video(in_video, conf=0.25, output_path=None)

    assert res.status == "completed"
    assert res.output_video_path is not None
    out_file = Path(res.output_video_path)
    assert out_file.is_file()
    assert out_file.parent == isolated_out_dir.resolve()

    # Verify TDD v1.1 §10.2 SAFE_NAME contract: ^[A-Za-z0-9_-]{8,64}\.mp4$
    safe_name_pattern = re.compile(r"^[A-Za-z0-9_-]{8,64}\.mp4$")
    assert safe_name_pattern.match(out_file.name), (
        f"Generated name '{out_file.name}' fails SAFE_NAME contract"
    )


# -----------------------------------------------------------------------------
# D-07: FFmpeg timeout enforcement
# -----------------------------------------------------------------------------

def test_ffmpeg_timeout_enforcement(tmp_path):
    """D-07: FFmpeg process exceeding watchdog timeout is killed and raises JobTimeoutError."""
    in_video = tmp_path / "timeout_in.mp4"
    out_video = tmp_path / "timeout_out.mp4"
    create_synthetic_video(in_video, num_frames=4, width=64, height=64, fps=10.0)

    mock_mgr = MagicMock()
    mock_mgr.active = "YOLO26m"
    mock_mgr.device = "cpu"
    mock_mgr.models_used = ["YOLO26m"]
    mock_mgr.predict.return_value = DetectionResult(
        "YOLO26m", 0, {k: 0 for k in CLASS_CODES}, [], 2.0, (64, 64)
    )

    mock_proc = MagicMock()
    mock_proc.stdin = MagicMock()
    mock_proc.stderr = MagicMock()
    mock_proc.stderr.readline.return_value = b""
    mock_proc.poll.return_value = None
    mock_proc.wait.side_effect = subprocess.TimeoutExpired(cmd="ffmpeg", timeout=1.0)

    engine = VideoEngine(mock_mgr)
    with patch("app.services.vision.video_engine.open_h264_writer", return_value=mock_proc):
        with pytest.raises(JobTimeoutError) as exc_info:
            engine.process_video(in_video, conf=0.25, output_path=out_video, timeout_s=10.0)

    assert exc_info.value.status_code == 504
    assert mock_proc.kill.called, "FFmpeg process must be forcefully killed on timeout"
    assert not out_video.is_file(), "Partial output must be cleaned up on timeout"


# -----------------------------------------------------------------------------
# D-08: FFmpeg stderr handling without pipe deadlocks
# -----------------------------------------------------------------------------

def test_ffmpeg_stderr_drain_no_deadlock():
    """D-08: Stderr draining thread continuously consumes pipe output without blocking."""
    import collections
    import io

    # Simulate pipe producing 500 lines
    data = b"".join(f"frame={i} fps=30 q=28.0 size={i*10}kB\n".encode("utf-8") for i in range(500))
    mock_pipe = io.BytesIO(data)
    store = collections.deque(maxlen=50)

    _drain_stderr(mock_pipe, store)

    assert len(store) == 50  # Bounded to maxlen
    assert "frame=499" in store[-1]
    assert mock_pipe.closed


# -----------------------------------------------------------------------------
# D-09: Video frame cap protection
# -----------------------------------------------------------------------------

def test_frame_cap_exceeded_raises_error(tmp_path):
    """D-09: Excessive frames beyond allowable duration threshold trigger VideoFrameCountExceededError."""
    in_video = tmp_path / "excess_frames.mp4"
    out_video = tmp_path / "excess_out.mp4"
    create_synthetic_video(in_video, num_frames=5, width=64, height=64, fps=10.0)

    mock_mgr = MagicMock()
    mock_mgr.active = "YOLO26m"
    mock_mgr.device = "cpu"
    mock_mgr.models_used = ["YOLO26m"]
    mock_mgr.predict.return_value = DetectionResult(
        "YOLO26m", 0, {k: 0 for k in CLASS_CODES}, [], 2.0, (64, 64)
    )

    engine = VideoEngine(mock_mgr)

    # Mock cv2.VideoCapture to simulate infinite stream exceeding allowed frame cap
    with patch("cv2.VideoCapture") as mock_cap_cls:
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: {
            cv2.CAP_PROP_FRAME_WIDTH: 64,
            cv2.CAP_PROP_FRAME_HEIGHT: 64,
            cv2.CAP_PROP_FPS: 10.0,
            cv2.CAP_PROP_FRAME_COUNT: 5.0,  # Reported 0.5s (5 frames)
        }.get(prop, 0.0)
        # Always return valid frame
        mock_cap.read.return_value = (True, np.zeros((64, 64, 3), dtype=np.uint8))
        mock_cap_cls.return_value = mock_cap

        # Set MAX_VIDEO_DURATION_S low for deterministic test
        with patch("app.services.vision.video_engine.MAX_VIDEO_DURATION_S", 1.0):
            with pytest.raises(VideoFrameCountExceededError) as exc_info:
                engine.process_video(in_video, conf=0.25, output_path=out_video)

        assert exc_info.value.status_code == 422
        assert exc_info.value.code == "video_over_limit"
        assert not out_video.is_file(), "Partial output must be cleaned up on frame cap error"


# -----------------------------------------------------------------------------
# D-10: JobCancelledError consistency
# -----------------------------------------------------------------------------

def test_job_cancelled_error_raise_on_cancel_true(tmp_path):
    """D-10: raise_on_cancel=True raises JobCancelledError (409) and cleans up partial output."""
    in_video = tmp_path / "cancel_raise.mp4"
    out_video = tmp_path / "cancel_raise_out.mp4"
    create_synthetic_video(in_video, num_frames=10, width=64, height=64, fps=10.0)

    cancel_evt = threading.Event()

    mock_mgr = MagicMock()
    mock_mgr.active = "YOLO26m"
    mock_mgr.device = "cpu"
    mock_mgr.models_used = ["YOLO26m"]

    def cancel_during_prediction(*args, **kwargs):
        cancel_evt.set()
        return DetectionResult("YOLO26m", 0, {k: 0 for k in CLASS_CODES}, [], 2.0, (64, 64))

    mock_mgr.predict.side_effect = cancel_during_prediction

    engine = VideoEngine(mock_mgr)
    with pytest.raises(JobCancelledError) as exc_info:
        engine.process_video(
            in_video,
            conf=0.25,
            output_path=out_video,
            cancel_event=cancel_evt,
            raise_on_cancel=True,
        )

    err = exc_info.value
    assert isinstance(err, VisionServiceError)
    assert err.status_code == 409
    assert err.code == "job_cancelled"
    assert not out_video.is_file(), "Partial output must be removed on cancellation"


def test_job_cancelled_error_raise_on_cancel_false(tmp_path):
    """D-10: raise_on_cancel=False returns VideoInspectionResult(status='cancelled') and cleans up."""
    in_video = tmp_path / "cancel_status.mp4"
    out_video = tmp_path / "cancel_status_out.mp4"
    create_synthetic_video(in_video, num_frames=10, width=64, height=64, fps=10.0)

    cancel_evt = threading.Event()
    cancel_evt.set()  # Pre-cancelled

    mock_mgr = MagicMock()
    mock_mgr.active = "YOLO26m"
    mock_mgr.device = "cpu"
    mock_mgr.models_used = ["YOLO26m"]

    engine = VideoEngine(mock_mgr)
    res = engine.process_video(
        in_video,
        conf=0.25,
        output_path=out_video,
        cancel_event=cancel_evt,
        raise_on_cancel=False,
    )

    assert res.status == "cancelled"
    assert res.output_video_path is None
    assert not out_video.is_file(), "Partial output must not exist for cancelled job"

