# RoadVision AI — S5-M3: Recorded Video Inference Engine Report

**Milestone**: Stage 5, Milestone 3 (S5-M3)  
**Date**: November 7, 2026  
**Author / CV Lead**: Ram (Computer Vision & Model Operations)  
**System Environment**: ASUS ROG Zephyrus G14, Windows 11 Home, AMD Ryzen 9 8945HS, NVIDIA GeForce RTX 5060 Laptop GPU (8GB GDDR6 VRAM, Driver 581.57, CUDA 12.8), 16GB DDR5 RAM, Python 3.11.9, PyTorch 2.11.0+cu128, Ultralytics 8.4.202, FFmpeg 9.0.2 (`imageio_ffmpeg`).

---

## 1. Executive Summary

Milestone S5-M3 delivers the **Recorded Video Computer Vision Engine** for RoadVision AI. Built strictly within Ram's architectural ownership boundaries (`backend/app/services/vision/**`), the engine enables robust, high-throughput, non-destructive inference on uploaded road inspection video files.

Key achievements:
1. **Isolated & Dedicated Module**: Created `backend/app/services/vision/video_engine.py` integrated directly with the production `VisionService` facade.
2. **Production Checkpoint Invariance**: Uses the verified primary `models/weights/yolo26m.pt` (SHA-256: `1BC41287DBDBC5EC5793D5D8F14CBA770E9E71E9C9E0CC0188B7146DA592D233`) under process-wide thread locks, guaranteeing zero model reloading and strict C-01 append-only model usage tracking.
3. **Browser-Ready H.264 Delivery**: Employs FFmpeg subprocess piping to encode progressive, web-optimized MP4 files (`-c:v libx264 -pix_fmt yuv420p -movflags +faststart`) with automatic dimension padding to prevent odd-dimension encoder crashes.
4. **Performance on RTX 5060**:
   - **Video Processing Throughput**: **49.87 FPS** (end-to-end decode + infer + annotate + encode).
   - **Pure GPU Inference Speed**: **58.96 FPS** (~16.96 ms/frame).
5. **Quality & Safety Assurance**: 18 comprehensive video engine tests + 41 existing tests = **59/59 passing automated tests**; clean cancellation handling and zero residual file leakage on failure.

---

## 2. Architecture & Design

### 2.1 Component Interaction Diagram

```mermaid
flowchart TD
    subgraph Client / Shakib Background Worker
        JobWorker[Background Job Task]
        CancelEvt[threading.Event: Cancel]
        ProgressCb[Progress Callback: Rate-limited 1s]
    end

    subgraph Ram CV Service: backend/app/services/vision/
        VS[VisionService Facade: service.py]
        VE[VideoEngine: video_engine.py]
        MM[ModelManager: model_manager.py]
        AN[Annotator: annotate.py]
    end

    subgraph Video Subsystems
        CVReader[OpenCV VideoCapture: Sequential Frames]
        FFmpegProc[FFmpeg Subprocess: libx264, yuv420p, +faststart]
        DiskIn[(Input MP4/AVI)]
        DiskOut[(Annotated H.264 MP4)]
    end

    JobWorker -->|detect_video| VS
    VS -->|process_video| VE
    VE -->|1. validate_video_file| DiskIn
    VE -->|2. Open stream| CVReader
    VE -->|3. Spawn pipe| FFmpegProc
    
    loop Frame by Frame
        CVReader -->|raw frame| VE
        VE -->|predict under lock| MM
        MM -->|DetectionResult| VE
        VE -->|non-destructive draw| AN
        AN -->|annotated frame bytes| FFmpegProc
        VE -->|periodic update| ProgressCb
        CancelEvt -.->|poll cancel| VE
    end

    FFmpegProc -->|finalize container| DiskOut
    VE -->|return VideoInspectionResult| VS
    VS -->|return VideoInspectionResult| JobWorker
```

### 2.2 Core Modules & Artifacts Added

| Module | Location | Purpose |
|---|---|---|
| `video_engine.py` | `backend/app/services/vision/video_engine.py` | Validation, sequential frame decoding, YOLO26m inference, annotation, FFmpeg piping, cancellation, and metrics collation. |
| `errors.py` (Updated) | `backend/app/services/vision/errors.py` | Added structured video errors: `VideoValidationError`, `VideoSizeExceededError`, `VideoDurationExceededError`, `VideoResolutionExceededError`, `VideoDecodeError`, `FFmpegNotFoundError`, `FFmpegExecutionError`, `JobCancelledError`, `JobTimeoutError`. |
| `types.py` (Updated) | `backend/app/services/vision/types.py` | Added dataclasses `VideoMetadata` and `VideoInspectionResult` with serialization methods. |
| `service.py` (Updated) | `backend/app/services/vision/service.py` | Extended `VisionService` with `detect_video()` facade method. |
| `__init__.py` (Updated) | `backend/app/services/vision/__init__.py` | Exported public video engine interfaces and types. |
| `test_video_engine.py` | `backend/tests/test_video_engine.py` | 18 unit tests covering all operational constraints and failure modes. |
| `smoke_gpu_video.py` | `training/smoke_gpu_video.py` | Real hardware verification script validating GPU inference, FFmpeg encoding, cancellation, and metrics. |

---

## 3. Operating Limits & Validation Rules (Q-01 / PRD v1.1)

In compliance with PRD v1.1 and provisional decision **Q-01**, all limits are centralized in `config.py` and strictly enforced prior to starting decoding:

| Parameter | Configuration Constant | Allowed Limit | Error Raised on Violation | HTTP Status Code |
|---|---|---|---|---|
| **File Formats** | `ALLOWED_VIDEO_EXTENSIONS` | `.mp4`, `.avi` | `UnsupportedVideoFormatError` | `415 Unsupported Media Type` |
| **File Size** | `MAX_VIDEO_BYTES` | 200 MB (209,715,200 bytes) | `VideoSizeExceededError` | `413 Payload Too Large` |
| **Duration** | `MAX_VIDEO_DURATION_S` | 60.0 seconds | `VideoDurationExceededError` | `422 Unprocessable Entity` |
| **Resolution** | `MAX_VIDEO_RESOLUTION` | 1920 × 1080 (1080p) | `VideoResolutionExceededError` | `422 Unprocessable Entity` |
| **Job Timeout** | `MAX_VIDEO_JOB_SECONDS` | 600.0 seconds (10 min) | `JobTimeoutError` | `504 Gateway Timeout` |
| **Decodability** | Open & Read Frame 0 | Must yield valid ndarray | `VideoDecodeError` | `422 Unprocessable Entity` |

---

## 4. Video Output & Browser Compatibility Pipeline

### 4.1 FFmpeg Piping Architecture
Writing browser-compatible MP4 files directly from OpenCV VideoWriter often fails on Windows due to missing `openh264` or unconfigured codecs. `video_engine.py` resolves this deterministically by discovering the system/bundled FFmpeg (`imageio_ffmpeg`) and piping raw BGR frames to FFmpeg stdin:

```bash
ffmpeg -y -f rawvideo -vcodec rawvideo -s {width}x{height} -pix_fmt bgr24 -r {fps} \
  -i - \
  -vf pad="ceil(iw/2)*2:ceil(ih/2)*2" \
  -c:v libx264 \
  -pix_fmt yuv420p \
  -movflags +faststart \
  {output_path}
```

Key features:
1. `-c:v libx264`: Universally supported H.264 video codec across Chrome, Edge, Firefox, and Safari.
2. `-pix_fmt yuv420p`: Ensures 8-bit 4:2:0 planar chroma subsampling required by HTML5 `<video>` tags.
3. `-movflags +faststart`: Relocates the `moov` atom to the beginning of the file, allowing instant video playback in the browser without downloading the complete file.
4. `-vf pad="ceil(iw/2)*2:ceil(ih/2)*2"`: Pads odd dimensions (e.g., 641×481) to even numbers, preventing H.264 macroblock alignment crashes.

---

## 5. Automated Test Suite Results

The full backend test suite was executed via `.venv\Scripts\python.exe -m pytest backend/tests -v -o "pythonpath=backend"`:

```text
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\Users\ramsa\Desktop\roadvision ai
plugins: anyio-4.16.0, cov-7.1.0
collected 59 items

backend/tests/test_api_image_integration.py::test_api_health PASSED      [  1%]
backend/tests/test_api_image_integration.py::test_api_model_status PASSED [  3%]
backend/tests/test_api_image_integration.py::test_api_detect_image_valid_jpg PASSED [  5%]
backend/tests/test_api_image_integration.py::test_api_detect_image_valid_png PASSED [  6%]
backend/tests/test_api_image_integration.py::test_api_detect_image_unsupported_format PASSED [  8%]
backend/tests/test_api_image_integration.py::test_api_detect_image_corrupt_payload PASSED [ 10%]
backend/tests/test_api_image_integration.py::test_api_detect_image_size_limit PASSED [ 11%]
backend/tests/test_api_image_integration.py::test_api_detect_image_dimension_limit PASSED [ 13%]
backend/tests/test_api_image_integration.py::test_api_detect_image_invalid_confidence PASSED [ 15%]
backend/tests/test_api_image_integration.py::test_api_detect_image_model_unavailable PASSED [ 16%]
backend/tests/test_api_image_integration.py::test_api_results_retrieval_and_safety PASSED [ 18%]
backend/tests/test_app_startup.py::test_app_startup_success PASSED       [ 20%]
backend/tests/test_app_startup.py::test_app_startup_model_failure_handling PASSED [ 22%]
backend/tests/test_video_engine.py::test_valid_mp4_validation PASSED     [ 23%]
backend/tests/test_video_engine.py::test_valid_avi_validation PASSED     [ 25%]
backend/tests/test_video_engine.py::test_invalid_extension PASSED        [ 27%]
backend/tests/test_video_engine.py::test_corrupt_video PASSED            [ 28%]
backend/tests/test_video_engine.py::test_unsupported_codec_or_empty_stream PASSED [ 30%]
backend/tests/test_video_engine.py::test_oversized_video PASSED          [ 32%]
backend/tests/test_video_engine.py::test_excessive_duration PASSED       [ 33%]
backend/tests/test_video_engine.py::test_excessive_resolution PASSED     [ 35%]
backend/tests/test_video_engine.py::test_empty_zero_byte_video PASSED    [ 37%]
backend/tests/test_video_engine.py::test_invalid_dimensions PASSED       [ 38%]
backend/tests/test_video_engine.py::test_no_detection_video PASSED       [ 40%]
backend/tests/test_video_engine.py::test_multiple_classes_across_frames PASSED [ 42%]
backend/tests/test_video_engine.py::test_correct_frame_and_detection_statistics PASSED [ 44%]
backend/tests/test_video_engine.py::test_output_file_h264_compatibility PASSED [ 45%]
backend/tests/test_video_engine.py::test_cancellation_and_partial_cleanup PASSED [ 47%]
backend/tests/test_video_engine.py::test_ffmpeg_failure_handling PASSED  [ 49%]
backend/tests/test_video_engine.py::test_resource_release_after_exceptions PASSED [ 50%]
backend/tests/test_video_engine.py::test_progress_callback PASSED        [ 52%]
backend/tests/test_vision_annotate.py::test_get_class_color PASSED       [ 54%]
backend/tests/test_vision_annotate.py::test_annotate_image_non_destructive PASSED [ 55%]
backend/tests/test_vision_annotate.py::test_annotate_image_clamping PASSED [ 57%]
backend/tests/test_vision_annotate.py::test_encode_and_save_annotated_image PASSED [ 59%]
backend/tests/test_vision_config_classes.py::test_canonical_class_codes PASSED [ 61%]
backend/tests/test_vision_config_classes.py::test_canonical_labels PASSED [ 62%]
backend/tests/test_vision_config_classes.py::test_validate_model_classes_success PASSED [ 64%]
backend/tests/test_vision_config_classes.py::test_validate_model_classes_failure PASSED [ 66%]
backend/tests/test_vision_config_classes.py::test_config_defaults PASSED [ 67%]
backend/tests/test_vision_image_engine.py::test_validate_image_payload_valid PASSED [ 69%]
backend/tests/test_vision_image_engine.py::test_validate_image_payload_empty PASSED [ 71%]
backend/tests/test_vision_image_engine.py::test_validate_image_payload_size_exceeded PASSED [ 72%]
backend/tests/test_vision_image_engine.py::test_validate_image_payload_unsupported_format PASSED [ 74%]
backend/tests/test_vision_image_engine.py::test_validate_image_payload_corrupt PASSED [ 76%]
backend/tests/test_vision_image_engine.py::test_decode_image_bytes PASSED [ 77%]
backend/tests/test_vision_image_engine.py::test_image_engine_process_empty_detections PASSED [ 79%]
backend/tests/test_vision_model_manager.py::test_compute_sha256 PASSED   [ 81%]
backend/tests/test_vision_model_manager.py::test_to_result_empty PASSED  [ 83%]
backend/tests/test_vision_model_manager.py::test_to_result_with_boxes PASSED [ 84%]
backend/tests/test_vision_model_manager.py::test_model_manager_c01_append_only_tracking PASSED [ 86%]
backend/tests/test_vision_model_manager.py::test_model_manager_class_mismatch_rejection PASSED [ 88%]
backend/tests/test_vision_model_manager.py::test_model_manager_predict_without_model_raises PASSED [ 89%]
backend/tests/test_vision_service_mocked.py::test_vision_service_mocked_lifecycle PASSED [ 91%]
backend/tests/test_vision_service_mocked.py::test_get_vision_service_singleton PASSED [ 93%]
backend/tests/test_vision_types_errors.py::test_detection_to_dict PASSED [ 94%]
backend/tests/test_vision_types_errors.py::test_detection_result_to_dict PASSED [ 96%]
backend/tests/test_vision_types_errors.py::test_vision_inspection_result_c01_tracking PASSED [ 98%]
backend/tests/test_vision_types_errors.py::test_errors_hierarchy PASSED  [100%]

======================== 59 passed, 1 warning in 9.66s ========================
```

---

## 6. Real Hardware GPU Smoke Test Verification

Executed via `.venv\Scripts\python.exe training/smoke_gpu_video.py`:

```text
================================================================================
ROADVISION AI — S5-M3 RECORDED VIDEO ENGINE GPU SMOKE TEST
================================================================================

[STEP 1] Verifying Promoted Production Checkpoint...
  Checkpoint Path : C:\Users\ramsa\Desktop\roadvision ai\models\weights\yolo26m.pt
  Expected SHA256 : 1BC41287DBDBC5EC5793D5D8F14CBA770E9E71E9C9E0CC0188B7146DA592D233
  Actual SHA256   : 1BC41287DBDBC5EC5793D5D8F14CBA770E9E71E9C9E0CC0188B7146DA592D233
  --> SHA-256 VERIFIED!

[STEP 2] Hardware & FFmpeg Environment Check...
  CUDA Available  : True
  Device Name     : NVIDIA GeForce RTX 5060 Laptop GPU
  Primary Target  : cuda:0
  FFmpeg Path     : .../imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v9.0.2.exe

[STEP 3] Preparing Sample Video Input (Non-Test Split)...
  Created sample video: .../runs/smoke_test_video/smoke_input.mp4 (40 frames @ 10.0 fps, 1156.5 KB)

[STEP 4] Initializing VisionService on cuda:0...
  Init Status     : True (2543.6 ms)

[STEP 5] Executing Video Processing Pipeline...
  -> Progress: 40/40 frames (100.0%), 70 detections

[STEP 6] Verifying Video Processing Results...
  Total Elapsed   : 0.84 s
  Status          : completed
  Total Frames    : 40
  Frames Processed: 40
  Frames With Detections: 40
  Total Detections: 70
  Class Summary   : {'D00': 50, 'D10': 20, 'D20': 0, 'D40': 0}
  Processing FPS  : 49.87
  Inference FPS   : 58.96
  Output Path     : .../runs/smoke_test_video/smoke_output_h264.mp4
  Output Exists   : True
  Output Size     : 907.6 KB
  H.264 Codec Detected : True

[STEP 7] Verifying Cancellation & Partial File Cleanup...
  Cancellation Status: cancelled
  --> Cancellation and cleanup verified successfully!

================================================================================
ALL S5-M3 VIDEO ENGINE GPU SMOKE TESTS PASSED!
================================================================================
```

### Performance Benchmarks Measured:
- **Total Pipeline Latency**: `0.84 s` for 40 frames (640×512 resolution).
- **End-to-End Processing FPS**: **49.87 FPS** (Exceeds PRD v1.1 target of ≥15 FPS by >3x).
- **YOLO26m GPU Inference FPS**: **58.96 FPS** (~16.96 ms per frame).
- **Output Video Size**: `907.6 KB` (progressive H.264 video with `yuv420p` and faststart).

---

## 7. Integration Contract for Application Layer (Shakib Handoff)

Shakib can directly integrate the video engine into background jobs (e.g., Celery, RQ, or FastAPI background tasks) using the following contract:

### 7.1 Python Calling Signature

```python
from pathlib import Path
import threading
from app.services.vision import (
    get_vision_service,
    VideoInspectionResult,
    JobCancelledError,
    VideoValidationError,
    FFmpegExecutionError,
)

service = get_vision_service()

# Optional cancellation token
cancel_event = threading.Event()

# Optional rate-limited progress callback
def on_progress(processed: int, total: int, hits: int, class_counts: dict):
    percent = (processed / total) * 100.0 if total > 0 else 0.0
    # Update DB or websocket...

try:
    result: VideoInspectionResult = service.detect_video(
        video_input=Path("uploads/inspection.mp4"),
        conf=0.25,
        output_path=Path("static/annotated/inspection_h264.mp4"),
        cancel_event=cancel_event,
        progress_callback=on_progress,
        timeout_s=600.0,
    )
    if result.status == "completed":
        # Save result.to_dict() to DB
        pass
except VideoValidationError as e:
    # HTTP 413, 415, 422 depending on e.status_code
    pass
except JobCancelledError as e:
    # Partial files are already deleted automatically
    pass
```

### 7.2 Result Data Contract (`result.to_dict()`)

```json
{
  "input_filename": "inspection.mp4",
  "output_video_path": "static/annotated/inspection_h264.mp4",
  "status": "completed",
  "total_frames": 40,
  "frames_processed": 40,
  "frames_with_detections": 40,
  "total_detections": 70,
  "class_summary": {
    "D00": 50,
    "D10": 20,
    "D20": 0,
    "D40": 0
  },
  "processing_duration_s": 0.84,
  "processing_fps": 49.87,
  "model_inference_duration_s": 0.68,
  "model_inference_fps": 58.96,
  "models_used": [
    "YOLO26m"
  ],
  "device": "cuda:0",
  "conf_threshold": 0.25,
  "error_message": null,
  "metadata": {
    "filename": "inspection.mp4",
    "width": 640,
    "height": 512,
    "fps": 10.0,
    "total_frames": 40,
    "duration_s": 4.0,
    "size_bytes": 1184256
  }
}
```

---

## 8. Cleanliness & Boundaries

- **Zero Shakib Modifications**: Verified via `git status` that no files under `backend/app/api/`, `backend/app/database/`, or `frontend/` were modified.
- **Zero Dataset Changes**: No modifications to `dataset/` or split manifests.
- **Zero Unsanctioned Git Commits**: No `git commit` or `git push` executed.
- **Cross-Layer Class Verification**: Ran `verify_classes.py` verifying all 5 layers match the 4 canonical classes (`0: D00`, `1: D10`, `2: D20`, `3: D40`).

---

## 9. Next Steps & Recommendations

1. **Shakib API Integration**: Shakib can now implement `POST /api/v1/detect/video` and `GET /api/v1/jobs/{job_id}` in `backend/app/api/` backed by SQLite and `service.detect_video`.
2. **Milestone S5-M4**: Real-time webcam/live video stream processing with OpenCV video capture and WebSocket or streaming responses.
3. **Milestone S5-M5**: Secondary model (`yolo26n`) transfer learning training and verification for dynamic fallback.

