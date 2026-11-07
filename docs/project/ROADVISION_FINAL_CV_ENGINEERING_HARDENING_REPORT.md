# RoadVision AI — Final CV Engineering Hardening, Defect Repair & Verification Report

**Document**: `docs/project/ROADVISION_FINAL_CV_ENGINEERING_HARDENING_REPORT.md`  
**Date**: November 8, 2026  
**Author**: Ram (Lead Computer Vision & Model Operations Engineer)  
**Track**: CV & Inference Engineering (`backend/app/services/vision/**`, `training/**`, `backend/tests/**`)  
**Hardware Platform**: ASUS ROG Zephyrus G14, Windows 11 Home, AMD Ryzen 9 8945HS, NVIDIA GeForce RTX 5060 Laptop GPU (8 GB GDDR6 VRAM, Driver 581.57, CUDA 12.8), 16 GB DDR5 RAM  
**Software Stack**: Python 3.11.9, PyTorch 2.11.0+cu128, Ultralytics 8.4.202, FFmpeg 9.0.2 (`imageio_ffmpeg`), OpenCV 5.0.0.93  
**Production Checkpoint**: `models/weights/yolo26m.pt` (SHA-256: `1BC41287DBDBC5EC5793D5D8F14CBA770E9E71E9C9E0CC0188B7146DA592D233`)

---

## 1. Executive Summary & Readiness Verdict

This report documents the completion of all Ram-owned Computer Vision engineering repairs, reliability hardenings, regression testing, and real hardware verifications for RoadVision AI.

### Final Readiness Verdict:
- **CV Subsystem & Inference Engines**: **PRODUCTION-READY (VERIFIED)**.
  - Image Inference Engine: Sub-60 ms total latency on RTX 5060, pixel-exact CPU parity, 100% C-01 append-only model tracking.
  - Recorded Video Engine: 60.87 FPS end-to-end processing throughput (exceeds PRD v1.1 requirement of ≥15 FPS by >4×), progressive browser-streamable H.264 video (`yuv420p`, `+faststart`), genuine mid-stream cancellation with zero partial artifact leaks, non-blocking stderr draining, watchdog timeout enforcement, and decoded frame-count capping.
  - Quality Assurance: **94 automated unit and integration tests passing** (0 failures, 1 deprecation warning, exit code 0).
  - Cross-Layer Truthfulness: Eliminated false PASS in cross-layer consistency verification; placeholder files now truthfully report `PENDING`.
- **Full End-to-End Application**: **PENDING EXTERNAL INTEGRATION (SHAKIB OWNERSHIP)**.
  - FastAPI application entrypoint (`backend/app/main.py`), API routes (`backend/app/api/*`), SQLite persistence (`backend/app/database/*`), file helpers (`backend/app/utils/*`), and React dashboard (`frontend/*`) remain unpopulated placeholders in Shakib's track. Ram's CV service is fully decoupled, hardened, and ready for immediate binding.

---

## 2. Complete Defect Register (D-01 through D-14)

| Defect ID | Severity | Category | Description | Final Status | Verification Method |
|---|---|---|---|---|---|
| **D-01** | S3 | Config | `MAX_CONFIDENCE` missing from app config bridge (`backend/app/config.py`) | **FIXED & VERIFIED** | Unit test `test_bridge_exports_max_confidence` |
| **D-02** | S2 | Validation | Invalid/zero FPS or frame counts accepted by video validator | **FIXED & VERIFIED** | 8 regression tests covering zero, negative, NaN, Inf values |
| **D-03** | S2 | Error Handling | Missing video files raised raw built-in `FileNotFoundError` instead of structured `VisionServiceError` | **FIXED & VERIFIED** | `VideoNotFoundError` (HTTP 404), unit tests for missing paths & directories |
| **D-04** | S3 | API Contract | Confidence validation boundary: CV clamps and logs; API must reject | **VERIFIED & DOCUMENTED** | Clamping logged loudly (`test_out_of_range_confidence_clamped_and_logged`); API contract handoff in §18 |
| **D-05** | S3 | Test Safety | Video tests wrote directly into production `data/outputs/` directory | **FIXED & VERIFIED** | Explicit temp paths + autouse guard fixture; 11 production files byte-identical |
| **D-06** | S2 | Security/Safety | Raw video input stems interpolated into default output names without sanitization | **FIXED & VERIFIED** | Sanitization regex `[A-Za-z0-9_-]`, length clamp (24 chars), uuid8 token, SAFE_NAME compliance tests |
| **D-07** | S2 | Reliability | FFmpeg subprocess could hang or exceed watchdog deadline during finalization | **FIXED & VERIFIED** | Watchdog deadline tracked across write + wait; `proc.kill()` and `JobTimeoutError` on expiry |
| **D-08** | S2 | Concurrency | Piped FFmpeg stderr could saturate OS pipe buffer causing subprocess deadlock | **FIXED & VERIFIED** | Dedicated daemon thread drains `stderr` into bounded deque; error diagnostics preserved |
| **D-09** | S2 | Resource Limit | No protection against excessive frames beyond duration/FPS limits | **FIXED & VERIFIED** | `VideoFrameCountExceededError` (HTTP 422) raised when frames exceed duration cap |
| **D-10** | S3 | Architecture | `JobCancelledError` was dead code; cancellation returned result dict only | **FIXED & VERIFIED** | `raise_on_cancel: bool` parameter added; supports both exception and status return flows |
| **D-11** | S2 | Truthfulness | Cross-layer class verifier printed `PASSED` for 0-byte placeholder files | **FIXED & VERIFIED** | File content inspection; empty files report `PENDING (Honest reporting: layer not yet authored)` |
| **D-12** | S1 | Bug | `log` used before logger definition in `model_manager.py` | **FIXED & VERIFIED** | Logger bound before imports; verified via induced import failure test |
| **D-13** | S3 | Verification | Video smoke test pre-set cancellation event before starting, bypassing mid-stream check | **FIXED & VERIFIED** | Genuine mid-stream cancellation executed on RTX 5060 GPU; aborted at frame 15/120 |
| **D-14** | S4 | Diagnostic | `nms_mode` string was hardcoded literal in `ModelStatus` | **FIXED & VERIFIED** | Dynamically derived from `ModelManager.nms_args` and `NMS_FREE_MODE`; unit tested |

---

## 3. Exact Source Files Changed & SHA-256 Hashes

All modifications were restricted strictly to Ram-owned paths:

| File Path | Layer / Owner | Size (Bytes) | SHA-256 Hash |
|---|---|---|---|
| `backend/app/config.py` | App Config Bridge (Ram) | 1,175 B | `cc10737b7bf7b85ff6dd945269e05e3b6c21283a3ec312cf328b6ba9476d5164` |
| `backend/app/services/vision/config.py` | Vision Config (Ram) | 5,060 B | `86dd85de452adc5abea3a5bba56fef84a955a9bf00650d5326c94368fedc851b` |
| `backend/app/services/vision/errors.py` | Vision Errors (Ram) | 8,472 B | `190e93ea58845f1db7f60fc8a02357cfa073ea3f810fb1d003a18fb0d7e33b14` |
| `backend/app/services/vision/types.py` | Vision Types (Ram) | 5,750 B | `8040f666b9b99ef4cb6c49b73370a1ad650110be6681241ce68d05df0a5de6f3` |
| `backend/app/services/vision/model_manager.py` | Model Manager (Ram) | 15,196 B | `3a42264bc2dea9080eb153873b33a3f17055b7becc7ea96d570533e60dc30f2b` |
| `backend/app/services/vision/video_engine.py` | Video Engine (Ram) | 20,125 B | `2deebc696225c2ec48b07f04a31fde39e8913b9ba2f4cce00695e4028abf4df9` |
| `backend/app/services/vision/service.py` | Service Facade (Ram) | 4,017 B | `870241e7d82c5de1e83bb0af67525b8191deaf5d87f70c3750979bc770b35f8e` |
| `backend/app/services/vision/__init__.py` | Module Exports (Ram) | 4,444 B | `5402020b79d830d2edc873a6ba901d0a7191f1a880c1af1436603a0e40fe0fa4` |
| `training/verify_classes.py` | Class Verifier (Ram) | 10,190 B | `50f27e6e3add39fa96c25faac7daa89499cec27027ff58215108632c4d606097` |
| `training/smoke_gpu_video.py` | GPU Video Smoke (Ram) | 9,800 B | `d3db7de4623e3df477d34f1c4de1327f1ffbafaa5b0a79b856a6537a5e3ed096` |
| `training/smoke_gpu_inference.py` | GPU Image Smoke (Ram) | 6,181 B | `a23842c4809f4faedafc9ab3245cfc8aac77be751c5bef996b24982d83134e14` |
| `backend/tests/test_verify_classes.py` | Verifier Tests (Ram) | 4,132 B | `a5b8ef089f50ee749059089f5ff0226343e18018bb8bef982703bdc631ec4703` |
| `backend/tests/test_video_engine.py` | Video Engine Tests (Ram) | 31,852 B | `79a10d1a3c2b85ec0c18f6eaab76f1ad3a05014c31fae90276fd1840b41b50fd` |
| `backend/tests/test_vision_model_manager.py` | Model Tests (Ram) | 6,258 B | `6b6d34c5d8d01b01ca4dd31eb66a0584ef7b575c755dcfdc2f2497528d48d6bd` |
| `backend/tests/test_vision_config_classes.py` | Config Tests (Ram) | 3,170 B | `8a602caef2660f996e25272b2f3e4a5fc126b1398d54e5989400b9dc380ec539` |
| `models/weights/yolo26m.pt` | Production Checkpoint | 44,031,321 B | `1bc41287dbdbc5ec5793d5d8f14cba770e9e71e9c9e0cc0188b7146da592d233` |

---

## 4. Technical Explanation of Engineering Repairs

### 4.1 D-03: Missing Video Input Error Normalization
- **Root Cause**: `validate_video_file` raised Python's built-in `FileNotFoundError`, which does not inherit from `VisionServiceError`. In FastAPI routes, this caused an unhandled 500 Internal Server Error rather than a standard JSON error response.
- **Solution**: Introduced `VideoNotFoundError(VideoValidationError)` with `status_code = 404` and `code = "video_not_found"`. Also added validation rejecting directories passed as file paths with `status_code = 400` (`code = "invalid_video_path"`).

### 4.2 D-06: Safe Default Video Output Filenames
- **Root Cause**: When `output_path` was `None`, `video_engine.py` interpolated raw `input_path.stem` directly into the output filename. Stems containing spaces, CJK/Cyrillic characters, path traversal tokens (`../../`), or reserved Windows devices (`CON`, `NUL`) failed the contract and risked filesystem errors.
- **Solution**: Added strict sanitization using `re.sub(r"[^A-Za-z0-9_-]", "_", stem).strip("_")`, reserved-device fallback (`"video"`), length clamping (24 characters), and random 8-character hex tokenization (`uuid.uuid4().hex[:8]`). Output names conform strictly to the TDD v1.1 §10.2 contract: `^[A-Za-z0-9_-]{8,64}\.mp4$`.

### 4.3 D-07: FFmpeg Timeout Enforcement
- **Root Cause**: FFmpeg finalization (`proc.wait(timeout=60)`) used a hardcoded 60s timeout disconnected from the overall job timeout budget (`timeout_s`), allowing jobs to run indefinitely.
- **Solution**: Implemented monotonic deadline calculation (`deadline = time.monotonic() + timeout_s`). Both the frame writing loop and container finalization enforce the remaining deadline. If `proc.wait()` expires, `proc.kill()` is invoked with a short cleanup wait, and `JobTimeoutError` (HTTP 504) is raised.

### 4.4 D-08: Non-Blocking FFmpeg Stderr Drain
- **Root Cause**: FFmpeg subprocess was spawned with `stderr=subprocess.PIPE`. If FFmpeg emitted copious warnings or log lines on long videos, the operating system's pipe buffer (~64 KB) filled up, causing FFmpeg to block on `write()` and permanently deadlocking the encoding process.
- **Solution**: Spawned a dedicated daemon thread `_drain_stderr` that continuously reads `proc.stderr` line by line into a memory-bounded `collections.deque(maxlen=100)`. Stderr lines are safely captured for error reporting upon exit without any risk of pipe buffer deadlock.

### 4.5 D-09: Decoded Video Frame Cap
- **Root Cause**: Video duration was validated solely using container metadata (`raw_frames / fps`). If metadata was missing, misleading, or a corrupt file produced infinite frames, the decoding loop could process unbounded frames.
- **Solution**: Introduced `MAX_VIDEO_FRAME_CAP = 3600` frames and computed dynamic per-video limits: `min(MAX_VIDEO_FRAME_CAP, int(fps * MAX_VIDEO_DURATION_S) + int(fps * 2.0))`. If the reading loop exceeds this limit, `VideoFrameCountExceededError` (HTTP 422, `code = "video_over_limit"`) is raised, and partial output is unlinked.

### 4.6 D-10: `JobCancelledError` Consistency
- **Root Cause**: `JobCancelledError` (HTTP 409) was defined and exported but never raised, because `process_video` returned `VideoInspectionResult(status="cancelled")`. Callers expecting exception-based flow had no mechanism to catch cancellation.
- **Solution**: Added `raise_on_cancel: bool = False` to `process_video` and `detect_video`. When `raise_on_cancel=True`, the engine raises `JobCancelledError` upon cancellation; when `False`, it returns `VideoInspectionResult(status="cancelled")`. In both modes, partial files are deleted and resources released.

### 4.7 D-11: Cross-Layer Class Verifier Truthfulness
- **Root Cause**: `training/verify_classes.py` returned `True` as long as candidate files existed on disk, falsely marking 0-byte placeholders (`schema.sql`, `classes.ts`) as `PASSED`.
- **Solution**: Updated `verify_database_layer()` and `verify_frontend_layer()` to check file sizes (`st_size > 0`) and parse contents for all 4 canonical class codes (`EXPECTED_CLASSES = ['D00', 'D10', 'D20', 'D40']`). Placeholder files are now truthfully reported as `PENDING (Honest reporting: layer not yet authored)`.

### 4.8 D-14: Dynamic NMS Mode Reporting
- **Root Cause**: `ModelStatus.nms_mode` was hardcoded to `"end-to-end (nms=False)"` regardless of what was configured or executed.
- **Solution**: Added `nms_mode` property to `ModelManager` that inspects `self.nms_args` and `NMS_FREE_MODE`. Returns `"end-to-end (nms=False)"` when NMS-free mode is active, `"standard-nms (iou={threshold})"` when standard NMS is configured, or `"custom-nms"`.

---

## 5. Automated Regression Test Suite Results

Executed via `.venv\Scripts\python.exe -m pytest backend/tests -q -o "pythonpath=backend"`:

```text
........................................................................ [ 76%]
......................                                                   [100%]
============================== warnings summary ===============================
.venv\Lib\site-packages\fastapi\testclient.py:1
  C:\Users\ramsa\Desktop\roadvision ai\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
94 passed, 1 warning in 10.62s
```

### Test Suite Evolution:
- Baseline (S5-M3): 59 tests passed.
- After Batch 1 (D-01, D-02, D-05, D-12): 72 tests passed (+13).
- After Final Hardening (D-03, D-06, D-07, D-08, D-09, D-10, D-11, D-14): **94 tests passed (+22)**.

---

## 6. Real Hardware Verification Results (NVIDIA RTX 5060)

### 6.1 GPU & CPU Image Inference Parity (`training/smoke_gpu_inference.py`)
- **Device**: NVIDIA GeForce RTX 5060 Laptop GPU (`cuda:0`).
- **Checkpoint SHA-256**: `1BC41287DBDBC5EC5793D5D8F14CBA770E9E71E9C9E0CC0188B7146DA592D233` (Verified match).
- **Test Sample**: `dataset/images/val/China_Drone__China_Drone_000005.jpg` (512×512).
- **GPU Latency**: Total: **53.27 ms** | Engine forward pass: **23.13 ms**.
- **CPU Latency**: Total: **208.24 ms** | Engine forward pass: **202.76 ms**.
- **Speedup**: **3.91×** faster on GPU.
- **Parity**: Exactly 2 detections on both GPU and CPU:
  - D00 (Longitudinal crack): conf 0.6045 | box: `[132.0, 178.0, 166.2, 512.0]`
  - D10 (Transverse crack): conf 0.5918 | box: `[0.0, 265.0, 209.3, 295.7]`

### 6.2 GPU Video Inference & Mid-Stream Cancellation (`training/smoke_gpu_video.py`)
- **Input Video**: 40 frames @ 10.0 FPS (640×512 resolution).
- **Processing Time**: **0.68 s** total elapsed.
- **End-to-End Processing Throughput**: **60.87 FPS** (PRD v1.1 target: ≥15 FPS).
- **GPU Inference Speed**: **71.50 FPS** (~13.98 ms per frame).
- **Detections**: 70 total detections (`D00`: 50, `D10`: 20, `D20`: 0, `D40`: 0).
- **Output Video**: 907.6 KB, progressive H.264 video.

### 6.3 FFprobe Output Video Verification
- **Command**: `ffmpeg -i runs/smoke_test_video/smoke_output_h264.mp4`
- **Container**: `mov,mp4,m4a,3gp,3g2,mj2`, `major_brand: isom`
- **Video Stream**: `h264 (High) (avc1 / 0x31637661)`
- **Pixel Format**: `yuv420p(progressive)`
- **Resolution**: `640x512`
- **FastStart Atom Placement**: Verified `moov` atom at byte **36**, preceding `mdat` atom at byte **1019**, confirming browser streaming and scrubability without full download.

### 6.4 D-13 Mid-Stream Cancellation Evidence
- **Scenario**: 120-frame video @ 25 FPS (3.49 MB). A background timer fired mid-stream at `t = 0.25 s`.
- **Observed Behavior**:
  - Processing halted at frame **15 / 120**.
  - Status returned: `"cancelled"`.
  - Output path: `None`.
  - Partial output file `runs/smoke_test_video/smoke_cancelled_midstream.mp4` was automatically deleted (`unlink`).
  - Zero zombie subprocesses or unclosed file descriptors.
- **`raise_on_cancel=True` Path**: `JobCancelledError` caught with `status_code = 409` and clean file cleanup.

---

## 7. Cross-Layer Class Verifier Output (`training/verify_classes.py`)

Executed via `.venv\Scripts\python.exe training/verify_classes.py`:

```text
================================================================================
ROADVISION AI — C-04 / AC-08 CROSS-LAYER CLASS CONSISTENCY VERIFIER
================================================================================

[1] Checking backend/app/classes.json (backend/app/classes.json)...
  PASSED: backend/app/classes.json matches canonical class order: ['D00', 'D10', 'D20', 'D40']

[1] Checking training/classes.json (training/classes.json)...
  PASSED: training/classes.json matches canonical class order: ['D00', 'D10', 'D20', 'D40']

[2] Checking Model Checkpoint: Production YOLO26m (models/weights/yolo26m.pt)...
  PASSED: Production YOLO26m classes match exactly: ['D00', 'D10', 'D20', 'D40']

[Diagnostic] Checking Secondary YOLO26n Pretrained Weights...

[2] Checking Model Checkpoint: Pretrained YOLO26n (Diagnostic) (models/weights/yolo26n_pretrained.pt)...
  WARNING / MISMATCH: Pretrained YOLO26n (Diagnostic) classes are: ['person', 'bicycle', 'car', 'motorcycle', 'airplane']... (count: 80)
  Expected exactly: ['D00', 'D10', 'D20', 'D40']

[3] Checking Backend CV Layer (backend/app/services/vision/classes.py)...
  PASSED: Backend CV layer matches canonical class order: ['D00', 'D10', 'D20', 'D40']

[4] Checking Database Layer...
  HONEST REPORT: Database files found ['schema.sql'] but all are 0 bytes (empty placeholders).
  Status: PENDING implementation by Shakib. Empty files cannot satisfy consistency check.

[5] Checking Frontend Layer...
  HONEST REPORT: Frontend files found ['classes.ts'] but all are 0 bytes (empty placeholders).
  Status: PENDING implementation by Shakib. Empty files cannot satisfy consistency check.

================================================================================
CROSS-LAYER CONSISTENCY SUMMARY:
================================================================================
  - backend_classes_json     : PASSED
  - training_classes_json    : PASSED
  - yolo26m_checkpoint       : PASSED
  - backend_cv_layer         : PASSED
  - database_layer           : PENDING (Honest reporting: layer not yet authored)
  - frontend_layer           : PENDING (Honest reporting: layer not yet authored)

CV SUBSYSTEM: FULLY CONSISTENT (PASS)
APPLICATION LAYERS: PENDING IMPLEMENTATION (Database and Frontend layers are unpopulated placeholders)
C-04 / AC-08 TRUTHFUL AUDIT: CV VERIFIED / APPLICATION PENDING
```

---

## 8. Integrity and Ownership Verification

### 8.1 Production Model Weights
- File: `models/weights/yolo26m.pt`
- Size: 44,031,321 bytes
- SHA-256: `1BC41287DBDBC5EC5793D5D8F14CBA770E9E71E9C9E0CC0188B7146DA592D233` (100% verified match).

### 8.2 Production Output Directory (`data/outputs/`)
All 11 pre-existing files were preserved byte-for-byte with zero deletions, modifications, or stray test artifact additions:

| SHA-256 Hash | File Name |
|---|---|
| `b139f900e1a6352c41dd27684f4834b1887dc0da0d965ac0a106f5503fda6be8` | `data/outputs/20261107_232736_214facb8.jpg` |
| `91cc4c34ff2674dd4d72749b3b4896760e6bcb6b39431232e189cd96e7c83d25` | `data/outputs/20261107_233904_callback_test_annotated.mp4` |
| `2b2534f05e9da8fe6732d631efa3820cea58b2d35f3e92d77ec57ebea29e2d87` | `data/outputs/20261107_233904_stats_annotated.mp4` |
| `91cc4c34ff2674dd4d72749b3b4896760e6bcb6b39431232e189cd96e7c83d25` | `data/outputs/20261107_233954_callback_test_annotated.mp4` |
| `2b2534f05e9da8fe6732d631efa3820cea58b2d35f3e92d77ec57ebea29e2d87` | `data/outputs/20261107_233954_stats_annotated.mp4` |
| `91cc4c34ff2674dd4d72749b3b4896760e6bcb6b39431232e189cd96e7c83d25` | `data/outputs/20261107_234009_callback_test_annotated.mp4` |
| `2b2534f05e9da8fe6732d631efa3820cea58b2d35f3e92d77ec57ebea29e2d87` | `data/outputs/20261107_234009_stats_annotated.mp4` |
| `2b2534f05e9da8fe6732d631efa3820cea58b2d35f3e92d77ec57ebea29e2d87` | `data/outputs/20261108_001641_stats_annotated.mp4` |
| `91cc4c34ff2674dd4d72749b3b4896760e6bcb6b39431232e189cd96e7c83d25` | `data/outputs/20261108_001642_callback_test_annotated.mp4` |
| `2b2534f05e9da8fe6732d631efa3820cea58b2d35f3e92d77ec57ebea29e2d87` | `data/outputs/20261108_002505_stats_annotated.mp4` |
| `91cc4c34ff2674dd4d72749b3b4896760e6bcb6b39431232e189cd96e7c83d25` | `data/outputs/20261108_002506_callback_test_annotated.mp4` |

### 8.3 Shakib-Owned Application Files
All Shakib-owned application files remain untouched (0 bytes, timestamps unshifted):
- `backend/app/main.py`
- `backend/app/api/{health,detect,model,results}.py`, `__init__.py`
- `backend/app/database/{db.py,schema.sql,__init__.py}`
- `backend/app/utils/{files.py,__init__.py}`
- `frontend/**`

### 8.4 Git Governance
- Zero commits and zero pushes executed. Working tree contains only authorized modifications.

---

## 9. Handoff Specifications for Shakib (Application Owner)

The following precise specifications are provided for Shakib's integration in his separate repository:

### 9.1 Boundary Validation for Confidence Parameter (D-04)
- **Requirement**: The API routes (`POST /api/detect/image` and `POST /api/detect/video`) must strictly validate `conf: float`.
- **Allowed Range**: `0.10 <= conf <= 0.90` (recommended default: `0.25`).
- **Behavior**: If `conf < 0.10` or `conf > 0.90`, the route must immediately return HTTP **422 Unprocessable Entity** with JSON body:
  ```json
  {
    "detail": [
      {
        "loc": ["body", "conf"],
        "msg": "confidence threshold must be between 0.10 and 0.90",
        "type": "value_error"
      }
    ]
  }
  ```
- **Note**: The CV engine clamps and logs warnings as a defensive fallback, but the API boundary must reject.

### 9.2 Managed Video Output Paths (D-06)
- **Requirement**: Always pass `output_path` explicitly when calling `service.detect_video(...)`.
- **Target Path**: `OUTPUT_DIR / new_output_name("mp4")`, generating names compliant with `SAFE_NAME = ^[A-Za-z0-9_-]{8,64}\.(jpg|png|mp4)$`.
- **DB Persistence**: Store only the filename in the SQLite database; never expose absolute server paths to the client.

### 9.3 Video Job Lifecycle & Cancellation (D-10)
- **Calling Pattern**:
  ```python
  from app.services.vision import get_vision_service, JobCancelledError, VideoInspectionResult

  service = get_vision_service()
  slot_cancel_event = threading.Event()

  try:
      result: VideoInspectionResult = service.detect_video(
          video_input=uploaded_path,
          conf=valid_conf,
          output_path=managed_output_path,
          cancel_event=slot_cancel_event,
          progress_callback=slot_progress_update,
          timeout_s=600.0,
          raise_on_cancel=False,
      )
      if result.status == "cancelled":
          # Update DB inspection status to 'cancelled'
          pass
      elif result.status == "completed":
          # Update DB inspection status to 'completed' with detection statistics
          pass
  except VisionServiceError as e:
      # Map e.status_code and e.to_dict() to HTTP client response
      pass
  ```

---

## 10. Commands to Reproduce Verification

```powershell
# 1. Run complete CV unit and integration test suite (94 tests)
.venv\Scripts\python.exe -m pytest backend/tests -v -o "pythonpath=backend"

# 2. Run cross-layer class consistency verifier
.venv\Scripts\python.exe training/verify_classes.py

# 3. Run real hardware GPU image inference smoke test
.venv\Scripts\python.exe training/smoke_gpu_inference.py

# 4. Run real hardware GPU video inference and mid-stream cancellation smoke test
.venv\Scripts\python.exe training/smoke_gpu_video.py

# 5. Verify output video stream with FFprobe
& (.\.venv\Scripts\python.exe -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())") -i runs/smoke_test_video/smoke_output_h264.mp4
```

---

## 11. Final Sign-Off

- [x] All 14 defects D-01 through D-14 addressed and documented.
- [x] 94/94 automated tests passed without failure.
- [x] Production YOLO26m model weights SHA-256 verified.
- [x] GPU image inference parity verified on NVIDIA RTX 5060 (3.91× speedup).
- [x] GPU video engine throughput benchmarked at 60.87 FPS (H.264 High, progressive yuv420p, faststart).
- [x] Mid-stream cancellation and partial cleanup verified on active video processing.
- [x] Cross-layer verifier updated to eliminate false PASS on placeholder files.
- [x] Production `data/outputs/` directory 100% verified byte-identical.
- [x] Zero Shakib-owned files modified or created.
- [x] Zero Git commits or pushes executed.
- [x] Comprehensive final report delivered.

**Final Engineering Verdict: CV Subsystem is Hardened, Fully Tested, and Production-Ready.**

