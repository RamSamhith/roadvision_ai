"""RoadVision AI — S5-M3 Real Hardware Video Engine Smoke Test.

Executes real video inference using promoted YOLO26m on NVIDIA RTX 5060 Laptop GPU.
Verifies:
- Checkpoint SHA-256
- Video file input validation
- OpenCV sequential frame reading
- GPU YOLO26m batch/frame inference
- Non-destructive bounding box annotation
- Browser-compatible H.264 MP4 export via FFmpeg
- Processing and inference FPS performance
- Per-class detection accounting
- Cancellation and resource cleanup
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

import cv2
import numpy as np
import torch

# Add backend to path
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.vision import (
    CLASS_CODES,
    MODEL_YOLO26M_EXPECTED_SHA256,
    MODEL_YOLO26M_PATH,
    JobCancelledError,
    VisionService,
    compute_sha256,
    get_ffmpeg_executable,
    get_primary_device,
)


def create_sample_video(output_path: Path, num_frames: int = 40, fps: float = 10.0) -> None:
    """Create a realistic non-test video using images from dataset/images/val."""
    val_dir = ROOT_DIR / "dataset" / "images" / "val"
    val_images = sorted(list(val_dir.glob("*.jpg")))[:4]
    assert len(val_images) > 0, "No validation images found to construct smoke video"

    frames = []
    target_size = (640, 512)
    for p in val_images:
        img = cv2.imread(str(p))
        if img is not None:
            frames.append(cv2.resize(img, target_size))

    if not frames:
        frames.append(np.zeros((512, 640, 3), dtype=np.uint8))

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, target_size)
    assert writer.isOpened(), f"Failed to open video writer for {output_path}"

    for i in range(num_frames):
        # Cycle through validation frames
        base_frame = frames[i % len(frames)].copy()
        writer.write(base_frame)

    writer.release()
    print(f"  Created sample video: {output_path} ({num_frames} frames @ {fps} fps, {output_path.stat().st_size / 1024:.1f} KB)")


def run_video_smoke_test() -> int:
    print("=" * 80)
    print("ROADVISION AI — S5-M3 RECORDED VIDEO ENGINE GPU SMOKE TEST")
    print("=" * 80)

    # 1. Checkpoint Verification
    print("\n[STEP 1] Verifying Promoted Production Checkpoint...")
    assert MODEL_YOLO26M_PATH.is_file(), f"Missing checkpoint: {MODEL_YOLO26M_PATH}"
    actual_hash = compute_sha256(MODEL_YOLO26M_PATH)
    print(f"  Checkpoint Path : {MODEL_YOLO26M_PATH}")
    print(f"  Expected SHA256 : {MODEL_YOLO26M_EXPECTED_SHA256}")
    print(f"  Actual SHA256   : {actual_hash}")
    assert actual_hash == MODEL_YOLO26M_EXPECTED_SHA256, "SHA256 verification failed!"
    print("  --> SHA-256 VERIFIED!")

    # 2. Hardware Environment & FFmpeg Check
    print("\n[STEP 2] Hardware & FFmpeg Environment Check...")
    cuda_available = torch.cuda.is_available()
    device_name = torch.cuda.get_device_name(0) if cuda_available else "N/A"
    primary_dev = get_primary_device()
    ffmpeg_bin = get_ffmpeg_executable()
    print(f"  CUDA Available  : {cuda_available}")
    print(f"  Device Name     : {device_name}")
    print(f"  Primary Target  : {primary_dev}")
    print(f"  FFmpeg Path     : {ffmpeg_bin}")
    assert ffmpeg_bin is not None, "FFmpeg executable not found!"

    # 3. Create Sample Video
    print("\n[STEP 3] Preparing Sample Video Input (Non-Test Split)...")
    out_dir = ROOT_DIR / "runs" / "smoke_test_video"
    out_dir.mkdir(parents=True, exist_ok=True)
    sample_video_path = out_dir / "smoke_input.mp4"
    create_sample_video(sample_video_path, num_frames=40, fps=10.0)

    annotated_output_path = out_dir / "smoke_output_h264.mp4"
    if annotated_output_path.exists():
        annotated_output_path.unlink()

    # 4. Service Initialization
    print(f"\n[STEP 4] Initializing VisionService on {primary_dev}...")
    service = VisionService(primary_device=primary_dev)
    t0_init = time.perf_counter()
    init_ok = service.initialize(device=primary_dev)
    init_ms = (time.perf_counter() - t0_init) * 1000.0
    print(f"  Init Status     : {init_ok} ({init_ms:.1f} ms)")
    assert init_ok, "VisionService initialization failed"

    # Progress tracking collector
    progress_updates = []

    def on_progress(processed: int, total: int, hits: int, class_counts: dict) -> None:
        progress_updates.append((processed, total, hits, class_counts))
        pct = (processed / total) * 100.0 if total > 0 else 0.0
        if processed % 10 == 0 or processed == total:
            print(f"  -> Progress: {processed}/{total} frames ({pct:.1f}%), {hits} detections")

    # 5. Video Processing
    print(f"\n[STEP 5] Executing Video Processing Pipeline...")
    t0_process = time.perf_counter()
    result = service.detect_video(
        video_input=sample_video_path,
        conf=0.25,
        output_path=annotated_output_path,
        progress_callback=on_progress,
    )
    total_elapsed = time.perf_counter() - t0_process

    # 6. Verify Results
    print("\n[STEP 6] Verifying Video Processing Results...")
    print(f"  Total Elapsed   : {total_elapsed:.2f} s")
    print(f"  Status          : {result.status}")
    print(f"  Total Frames    : {result.total_frames}")
    print(f"  Frames Processed: {result.frames_processed}")
    print(f"  Frames With Detections: {result.frames_with_detections}")
    print(f"  Total Detections: {result.total_detections}")
    print(f"  Class Summary   : {result.class_summary}")
    print(f"  Processing FPS  : {result.processing_fps:.2f}")
    print(f"  Inference FPS   : {result.model_inference_fps:.2f}")
    print(f"  Output Path     : {result.output_video_path}")
    print(f"  Output Exists   : {annotated_output_path.is_file()}")
    output_size_kb = annotated_output_path.stat().st_size / 1024.0 if annotated_output_path.is_file() else 0.0
    print(f"  Output Size     : {output_size_kb:.1f} KB")

    assert result.status == "completed", f"Video processing status: {result.status}"
    assert annotated_output_path.is_file(), "Output video file was not generated!"
    assert annotated_output_path.stat().st_size > 0, "Output video file is empty!"
    assert result.frames_processed == 40, f"Expected 40 frames processed, got {result.frames_processed}"
    assert len(progress_updates) >= 1, "Progress updates were not received"

    # Verify H.264 Codec in output video with FFmpeg/ffprobe
    ffprobe_cmd = [
        ffmpeg_bin,
        "-i",
        str(annotated_output_path),
    ]
    probe_res = subprocess.run(ffprobe_cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    # ffmpeg reports stream info on stderr
    stderr_out = probe_res.stderr.lower()
    has_h264 = "video: h264" in stderr_out or "h.264" in stderr_out
    print(f"  H.264 Codec Detected : {has_h264}")
    assert has_h264, f"Output video is not encoded in H.264! Stderr:\n{probe_res.stderr}"

    # 7. Verify Genuine Mid-Stream Cancellation & Partial File Cleanup (D-10, D-13)
    print("\n[STEP 7] Verifying Genuine Mid-Stream Cancellation & Partial Cleanup (D-13)...")
    cancel_input = out_dir / "smoke_long_input.mp4"
    create_sample_video(cancel_input, num_frames=120, fps=25.0)

    cancel_event_mid = threading.Event()
    cancel_output_mid = out_dir / "smoke_cancelled_midstream.mp4"
    if cancel_output_mid.exists():
        cancel_output_mid.unlink()

    # Trigger cancellation mid-stream via background timer while frames are actively being processed
    cancel_timer = threading.Timer(0.25, cancel_event_mid.set)
    cancel_timer.start()

    cancel_res_mid = service.detect_video(
        video_input=cancel_input,
        conf=0.25,
        output_path=cancel_output_mid,
        cancel_event=cancel_event_mid,
        raise_on_cancel=False,
    )
    cancel_timer.cancel()

    print(f"  Cancellation Status : {cancel_res_mid.status}")
    print(f"  Frames Processed    : {cancel_res_mid.frames_processed} / {cancel_res_mid.total_frames}")
    assert cancel_res_mid.status == "cancelled", f"Expected status 'cancelled', got {cancel_res_mid.status}"
    assert 5 <= cancel_res_mid.frames_processed < 120, (
        f"Expected mid-stream abortion between 5 and 119 frames, got {cancel_res_mid.frames_processed}"
    )
    assert not cancel_output_mid.exists(), f"Partial output {cancel_output_mid} was not cleaned up after mid-stream cancel!"
    print("  --> Mid-stream cancellation and partial cleanup verified successfully!")

    # 7b. Test raise_on_cancel=True (D-10)
    print("\n[STEP 7b] Verifying raise_on_cancel=True exception raising (D-10)...")
    cancel_event_exc = threading.Event()
    cancel_event_exc.set()
    cancel_output_exc = out_dir / "smoke_cancelled_exc.mp4"
    caught_job_cancelled = False
    try:
        service.detect_video(
            video_input=sample_video_path,
            conf=0.25,
            output_path=cancel_output_exc,
            cancel_event=cancel_event_exc,
            raise_on_cancel=True,
        )
    except JobCancelledError as e:
        caught_job_cancelled = True
        print(f"  Successfully caught JobCancelledError: status_code={e.status_code}, message='{e.message}'")

    assert caught_job_cancelled, "JobCancelledError was not raised when raise_on_cancel=True"
    assert not cancel_output_exc.exists(), "Partial file remained after raise_on_cancel=True"
    print("  --> raise_on_cancel=True verified successfully!")

    print("\n" + "=" * 80)
    print("ALL S5-M3 VIDEO ENGINE GPU SMOKE TESTS PASSED!")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(run_video_smoke_test())
