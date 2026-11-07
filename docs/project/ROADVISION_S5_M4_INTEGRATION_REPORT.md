# RoadVision AI — S5-M4 Integration Readiness Report

**Milestone:** S5-M4 — Verified integration readiness audit of the CV subsystem (image + recorded video) against TDD v1.1 / PRD v1.1, plus the application-layer integration contract for the separate repository.

**Status:** **CV SUBSYSTEM: COMPONENT-READY (conditional)** · **APPLICATION E2E: BLOCKED**

**Audit date:** 2026-11-08
**Auditor:** Ram (CV owner) — read-only audit
**Authority:** `docs/reference/TDD_v1.1.md`, `docs/reference/PRD_v1.1.md`

---

## 0. Audit scope, method and honesty statement

### 0.1 What this report is

An evidence-based re-verification of every claim in `ROADVISION_S5_M1_REPORT.md`, `ROADVISION_S5_M2_REPORT.md` and `ROADVISION_S5_M3_VIDEO_ENGINE_REPORT.md` that can be re-run on this machine today, followed by a precise integration contract for the backend/API/frontend owner.

### 0.2 What this report is **not**

- It is **not** a claim that the RoadVision AI application works end to end.
- It does **not** certify any endpoint, database table, browser flow or video job pipeline, because **none of those layers exist in this repository** (see §3).
- It does **not** restore, repair or reconstruct any file. Every file listed as empty in §3 was empty before this audit and is empty after it.

### 0.3 Read-only declaration

No source file, test file, config file, model, dataset or report was created, modified, deleted or restored during this audit, with the single exception of the report you are reading.

Executing the test suite and the smoke scripts **did** produce runtime artifacts (video/image outputs and logs). These are listed in §9.4 rather than silently discarded.

### 0.4 Ownership boundary

| Tree | Owner | State in this workspace |
| :--- | :--- | :--- |
| `backend/app/services/vision/**`, `backend/tests/**`, `training/**` | Ram | Present, audited |
| `backend/app/main.py`, `backend/app/api/**`, `backend/app/database/**`, `backend/app/utils/**` | Shakib | **0 bytes / absent** |
| `frontend/**` | Shakib | **Scaffold + 7 zero-byte files** |

Per instruction, Shakib's trees were **not** reconstructed, even though a validated pre-crash snapshot exists outside the repository (see §3.4).

---

## 1. Verdict summary

| Area | Verdict | Basis |
| :--- | :--- | :--- |
| Production checkpoint integrity | **PASS** | SHA-256 matches both the expected constant and the evaluated `best.pt` |
| Class contract (4 classes, order) | **PASS** (CV layers only) | JSON, checkpoint, `classes.py` verified; DB/frontend layers unverifiable |
| Image CV engine | **PASS** | 28 unit tests + real GPU/CPU smoke, GPU↔CPU detection parity |
| Recorded-video CV engine | **PASS WITH CONDITIONS** | 18 tests + real GPU run + ffprobe; 3 must-fix defects before wiring |
| Automated test suite | **PASS (59/59)** but **mis-scoped** | No test imports the real application; see §5.2 |
| Image application E2E | **BLOCKED** | `backend/app/main.py` is 0 B; no `app` object; no API/DB/frontend |
| Video application E2E | **BLOCKED** | No `/api/detect/video`, no job slot, no history/cancel/serving endpoints |
| Browser verification | **BLOCKED** | Frontend renders the environment scaffold, not a product UI |
| Documentation accuracy | **CORRECTIONS REQUIRED** | 4 claims do not survive re-verification; see §6 |
| **Overall S5-M4** | **NOT READY FOR DEMO** — CV subsystem is integration-ready subject to §7 | — |

---

## 2. Verified host environment

Commands run from the repository root with the project virtual environment. Verbatim results:

```
> .\.venv\Scripts\python.exe --version
Python 3.11.9

> .\.venv\Scripts\python.exe -c "import torch, cv2, numpy, imageio_ffmpeg; ..."
torch 2.11.0+cu128
cuda_available True
device_count 1
device_name NVIDIA GeForce RTX 5060 Laptop GPU
cv2 5.0.0
numpy 2.4.6
imageio_ffmpeg 0.8.1

> ffmpeg -version
ffmpeg version 9.0-full_build-www.gyan.dev ... --enable-libx264 ...
```

```
ultralytics 8.4.202
Pillow 13.0.0
fastapi 0.162.0
uvicorn 0.54.0
pydantic 2.14.2
pytest 9.2.0
```

All of the above match the pins in `backend/requirements.txt`. **Note:** `AGENTS.md` describes the host as "AMD Radeon 780M (integrated GPU)" with CUDA "PRESENT". The measured reality is a discrete **NVIDIA GeForce RTX 5060 Laptop GPU** with CUDA functional (`torch.cuda.is_available() == True`). The audit used the measured hardware, not the `AGENTS.md` description.

FFmpeg used by the engine (resolved through `imageio_ffmpeg`, not PATH):

```
C:\Users\ramsa\Desktop\roadvision ai\.venv\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v9.0.2.exe
```

---

## 3. Repository state — why application E2E is blocked

### 3.1 Backend application layer

| Path | Size | Consequence |
| :--- | ---: | :--- |
| `backend/app/main.py` | 0 B | No FastAPI `app`; no lifespan; no router mounting |
| `backend/app/api/__init__.py` | 0 B | No router aggregation |
| `backend/app/api/detect.py` | 0 B | No `POST /api/detect/image` |
| `backend/app/api/health.py` | 0 B | No `GET /api/health` |
| `backend/app/api/model.py` | 0 B | No `GET /api/model/status` |
| `backend/app/api/results.py` | 0 B | No `GET /api/results/{name}` |
| `backend/app/database/__init__.py` | 0 B | No `db_insert_inspection` / `db_finish_inspection` |
| `backend/app/database/db.py` | 0 B | No DB access layer |
| `backend/app/database/schema.sql` | 0 B | No schema |
| `backend/app/utils/__init__.py` | 0 B | — |
| `backend/app/utils/files.py` | 0 B | No `save_upload`, `new_output_name`, `sanitize_filename` |
| `backend/tests/test_production_app.py` | 0 B | The only test that imported `app.main` is gone |

Direct evidence that the entrypoint is non-functional:

```
> $env:PYTHONPATH="...\backend"; python -c "import app.main as m; print(..., hasattr(m,'app'))"
imported app.main OK, file size bytes= 0
has app attr: False
EXITCODE=0
```

`uvicorn app.main:app` therefore fails with `AttributeError: module 'app.main' has no attribute 'app'`.

Grep over `backend/app` for the video/history/dashboard/camera routes required by TDD v1.1 Table 6 (`detect/video`, `history`, `dashboard`, `camera`): **no matches**. The pre-crash application was image-only; the video API was never implemented.

### 3.2 Frontend

`frontend/src/App.tsx` is the 2026-11-05 environment scaffold. Its own comment and body state:

> "Environment scaffold only. No product features are implemented yet"
> "Application pages are intentionally not implemented at this stage."

Seven source files are 0 B: `components/DetectionResults.tsx`, `components/Header.tsx`, `components/ImageUpload.tsx`, `services/api.ts`, `types/classes.ts`, `types/detection.ts`. `frontend/dist/` contains historical build output (236,800 B JS) that does not correspond to the current source.

### 3.3 Git

- Branch `master`, single commit `0f977c7`.
- All application, CV, frontend and training code is **untracked** (`?? backend/app/`, `?? backend/tests/`, `?? frontend/`, `?? training/`).
- No remote, no stash.
- Consequence: `git status` **cannot** support any "no files were modified" claim about Shakib's trees, because those trees were never tracked. The S5-M3 report's line "Verified via `git status` that no files under `backend/app/api/`, `backend/app/database/`, or `frontend/` were modified" is therefore vacuous, not false.

### 3.4 Historical artifacts — evidence only, not functionality

| Artifact | Meaning |
| :--- | :--- |
| `data/roadvision.db` (16,384 B, WAL) | 2 completed **image** inspections from 2026-11-07; **0 video rows** |
| `frontend/dist/**` | Build from a previous session |
| `C:\Users\ramsa\AppData\Local\Temp\opencode\recovered\` | Pre-crash source snapshot recovered from the Antigravity conversation DB |
| `C:\Users\ramsa\AppData\Local\Temp\opencode\fe_shadow\` | Shadow frontend build proving snapshot fidelity |

DB contents, verbatim:

```
id=1 created=2026-11-07T17:55:09.718Z image test.jpg            models_used=None     det=2  status=completed
id=2 created=2026-11-07T17:57:36.423Z image pavement_test.jpg   models_used=YOLO26m  det=0  processing_ms=51  output_name=20261107_232736_214facb8.jpg  status=completed
```

These rows are historical evidence that an image pipeline once ran. They are **not** evidence that the application runs now.

**Caveat on the recovered snapshot:** the extracted files for `services/vision/types.py`, `services/vision/errors.py` and `tests/test_production_app.py` contain **duplicated trailing blocks** (an extraction artifact — e.g. `class VideoMetadata` appears twice). The current in-repo `types.py` / `errors.py` are the authoritative versions: both compile to bytecode **identical** to the pre-crash `__pycache__` `.pyc` files (§4.1). The snapshot must never be restored verbatim.

---

## 4. CV subsystem — verified

### 4.1 Source integrity of the CV package

Every CV module in `backend/app/services/vision/` was compiled in-memory and compared against its pre-crash `__pycache__` object (co_code, co_consts, co_names):

| Module | Bytecode vs pre-crash `.pyc` |
| :--- | :--- |
| `types.py`, `errors.py`, `config.py`, `classes.py`, `annotate.py` | **MATCH** |
| `image_engine.py`, `model_manager.py`, `service.py`, `video_engine.py`, `__init__.py` | **MATCH** |
| `backend/app/config.py` | **DIFF** — one import line missing (§7, D-01) |

The CV subsystem is therefore the same code that was tested in S5-M1..M3, with one integration break in the application-level config bridge.

### 4.2 Model promotion and provenance

```
models/weights/yolo26m.pt                      44,031,321 B
SHA-256  1BC41287DBDBC5EC5793D5D8F14CBA770E9E71E9C9E0CC0188B7146DA592D233   (PASS)

runs/train/yolo26m_s4_t5_main_50ep/weights/best.pt
SHA-256  1BC41287DBDBC5EC5793D5D8F14CBA770E9E71E9C9E0CC0188B7146DA592D233   (PASS)
```

The promoted checkpoint is bit-identical to the evaluated training artifact. `MODEL_YOLO26M_EXPECTED_SHA256` in `backend/app/services/vision/config.py:42` matches. Expected-hash verification is enforced at load time (`model_manager.py:153-160`).

`models/weights/yolo26n_pretrained.pt` (5,544,453 B) is COCO-pretrained (80 classes) and is correctly **not** registered in `MODEL_CHECKSUMS`; `YOLO26N_FALLBACK_ENABLED = False` (`config.py:49`), so AC-10 fallback is deliberately out of scope until transfer learning is done.

Production metrics (`runs/s4_t6_test_summary.json`, held-out test split):

| Metric | Value |
| :--- | ---: |
| Precision | 0.6696 |
| Recall | 0.5637 |
| mAP@50 | 0.6191 |
| mAP@50-95 | 0.3197 |
| Test images / instances | 2,349 / 5,424 |
| Inference speed | 14.01 ms |

These reproduce the figures quoted in the earlier milestone reports and are traceable to an on-disk artifact.

### 4.3 Automated test suite

```
> $env:PYTHONPATH="...\backend"; ..\.venv\Scripts\python.exe -m pytest -q
59 passed, 1 warning in 7.92s
EXITCODE=0
```

| File | Tests | Kind |
| :--- | ---: | :--- |
| `test_api_image_integration.py` | 11 | **Contract-shape tests against a reference FastAPI app built inside the test file** |
| `test_app_startup.py` | 2 | Lifespan harness built inside the test file |
| `test_video_engine.py` | 18 | Real OpenCV + real FFmpeg, **mocked model** |
| `test_vision_annotate.py` | 4 | Unit |
| `test_vision_config_classes.py` | 5 | Unit |
| `test_vision_image_engine.py` | 7 | Unit |
| `test_vision_model_manager.py` | 6 | Unit |
| `test_vision_service_mocked.py` | 2 | Unit |
| `test_vision_types_errors.py` | 4 | Unit |
| `test_production_app.py` | 0 | **Empty file → contributes no tests** |
| **Total** | **59** | |

---

## 5. What "59/59 passing" does and does not prove

### 5.1 It proves

- The four error hierarchies and their HTTP status codes are internally consistent.
- The annotator does not mutate its input and clamps boxes to image bounds.
- The image validator rejects empty, oversize, wrong-format and corrupt payloads.
- The model manager enforces SHA-256, class order, append-only C-01 tracking, and raises when unloaded.
- The video engine handles real MP4/AVI files and produces a real H.264 output; cancellation deletes partial output; FFmpeg failure and inference exceptions propagate and clean up.

### 5.2 It does **not** prove application integration

`test_api_image_integration.py:52-166` defines `create_integration_app()` — a **fresh FastAPI application constructed inside the test module** — and exercises that. `test_app_startup.py` builds its own `FastAPI(lifespan=...)`. **No test imports `app.main`, `app.api.*`, `app.database.*` or `frontend/`.**

Therefore:

- "41 automated tests" in S5-M2 and "59/59" in S5-M3 are accurate as **test counts** and misleading as **integration evidence**.
- The S5-M2 heading "End-to-End Verification" describes an end-to-end **of a reference app written for the test**, not of RoadVision AI.
- The only test that ever touched the real entrypoint, `test_production_app.py`, is now 0 B.

This distinction is the single most important finding of S5-M4.

---

## 6. Claim reconciliation

| # | Claim (source) | Re-verified result | Verdict |
| :--- | :--- | :--- | :--- |
| C-1 | Checkpoint SHA-256 verified (M1, M3) | Recomputed; matches expected and `best.pt` | **CONFIRMED** |
| C-2 | 28 CV unit tests passed (M1) | 28 non-video tests pass today | **CONFIRMED** |
| C-3 | GPU 49.68 ms forward pass (M1) | Re-run: **32.83 ms** engine forward pass, 73.92 ms full pipeline | **CONFIRMED (timing varies)** |
| C-4 | GPU and CPU detection counts identical (M1) | Re-run: 2 == 2, same classes/confidence | **CONFIRMED** |
| C-5 | 41 automated tests passed (M2) | 28 + 11 + 2 = 41 collect today | **CONFIRMED as counts** |
| C-6 | "End-to-End" image workflow verified (M2) | Executed only against an in-test reference app | **MIS-SCOPED — correction required** |
| C-7 | 18 video engine tests + 41 = 59/59 (M3) | 18 + 41 = 59, all pass, exit 0 | **CONFIRMED** |
| C-8 | 49.87 end-to-end FPS, 58.96 inference FPS, 0.84 s (M3) | Re-run: **34.58 / 38.34 FPS, 1.20 s wall clock**. Also internally inconsistent: `40 / 0.84 s = 47.6`, not 49.87 | **NOT REPRODUCED — correction required** |
| C-9 | H.264, yuv420p, faststart, 40 frames (M3) | ffprobe: h264 High, yuv420p, 640×512, 10/1, nb_frames 40, duration 4.0 s, `moov` at byte 32 before `mdat` at 1015 | **CONFIRMED** |
| C-10 | Cancellation leaves no partial output (M3) | Re-run: status `cancelled`, output absent | **CONFIRMED (weak test — event pre-set before start; see D-13)** |
| C-11 | C-04 cross-layer consistency PASS — DB + frontend (M1/M3) | `verify_classes.py` prints PASSED for a **0-byte** `schema.sql` and a **0-byte** `classes.ts` | **FALSE PASS — defect D-11** |
| C-12 | "Git status proves Shakib's files unmodified" (M3) | Those paths are untracked; git status cannot express this | **UNSUPPORTABLE — correction required** |

---

## 7. Defect register (Ram-owned CV code)

Severity: **S1** = blocks integration · **S2** = must fix before demo · **S3** = should fix · **S4** = hygiene.
**None of these fixes have been applied.** Each is proposed only.

### D-01 — S1 — `MAX_CONFIDENCE` missing from the application config bridge

`backend/app/config.py:17-47` re-exports 28 names but omits `MAX_CONFIDENCE`. `backend/app/api/detect.py` (per the recovered contract and per S5-M2 §3 blueprint) does `from app.config import MAX_CONFIDENCE`, which raises `ImportError` at import time — the whole application fails to start even after `main.py` is restored.

Bytecode comparison confirms the current file is the only CV-adjacent module that differs from its pre-crash state (19 bytes: the missing import line).

**Proposed fix (1 line, Ram-owned bridge):** add `    MAX_CONFIDENCE,` between `MIN_CONFIDENCE,` and `MIN_LIVE_FPS,` in the `app.services.vision.config` import block.

### D-02 — S1 — Video validation accepts files that violate TDD §10.2

`video_engine.py:156` — `fps = float(cap.get(cv2.CAP_PROP_FPS)) or 25.0`
`video_engine.py:175` — `calc_frames = max(1, reported_frames)`

TDD v1.1 §10.2: *"videos must open with fps and frame count above zero"*. The current code substitutes 25 fps and 1 frame instead of rejecting, so a structurally invalid container is accepted and then processed.

Reproduced with a fake capture reporting `FPS=0`, `FRAME_COUNT=0`:

```
ACCEPTED zero-fps/zero-frame video ->
{'filename': 'fake.mp4', 'width': 320, 'height': 240, 'fps': 25.0,
 'total_frames': 1, 'duration_s': 0.04, 'size_bytes': 100}
```

**Proposed fix:** if `fps <= 0` or `reported_frames <= 0`, raise `VideoDecodeError`; keep the 25 fps assumption only as a *writer* fallback, per TDD §8 ("25 fps is assumed if the file reports none").

### D-03 — S2 — Missing video file raises the wrong exception type

`video_engine.py:134` raises `FileNotFoundError`, which is not a `VisionServiceError`, so the shared TDD §10.3 error handler cannot map it and the API would return an unmapped 500.

```
type: FileNotFoundError  |  is VisionServiceError: False
```

**Proposed fix:** raise `VideoValidationError("Video file not found", code="video_not_found", status_code=400)`, or document that the API must catch `FileNotFoundError` explicitly.

### D-04 — S2 — Out-of-range `conf` is silently clamped instead of rejected

`video_engine.py:254` and `model_manager.py:302`: `max(MIN_CONFIDENCE, min(conf, MAX_CONFIDENCE))`.

```
conf=5.0 -> returned conf_threshold: 0.9  status: completed
```

TDD §10: detection routes take a `conf` parameter *within the allowed range*. For images, `api/detect.py` rejects out-of-range values before the engine sees them; the video route does not exist yet, so the only guard would be this silent clamp — and the response then reports a threshold the client never asked for.

**Decision required (not a unilateral fix):** either (a) keep clamping and make the video route validate strictly at the boundary (recommended, matches the image route), or (b) have the engine raise `VideoValidationError(..., 422)`. Option (a) keeps the engine tolerant for programmatic callers.

### D-05 — S2 — Tests write into the production output directory

`test_video_engine.py:292` and `:417` call `process_video()` **without** `output_path`, so the engine's default (`video_engine.py:58, 226-229`) writes to `data/outputs/`. Evidence in `data/outputs/`:

```
20261107_233904_stats_annotated.mp4        1810 B
20261107_233904_callback_test_annotated.mp4 1677 B
20261107_233954_stats_annotated.mp4        1810 B
20261107_233954_callback_test_annotated.mp4 1677 B
20261107_234009_stats_annotated.mp4        1810 B
20261107_234009_callback_test_annotated.mp4 1677 B
20261108_001641_stats_annotated.mp4        1810 B   <- created by this audit's pytest run
20261108_001642_callback_test_annotated.mp4 1677 B  <- created by this audit's pytest run
```

These names match `SAFE_NAME = ^[A-Za-z0-9_-]{8,64}\.(jpg|png|mp4)$`, so they would be **servable** through `/api/results/{name}` alongside real user outputs.

**Proposed fix:** pass `output_path=tmp_path / "..."` at both call sites (2-line change, test-only).

### D-06 — S2 — Default output name is not contract-safe

`video_engine.py:226-229` builds `{timestamp}_{input_stem}_annotated.mp4` from the **raw on-disk filename stem**. An upload whose stem contains spaces, Cyrillic, CJK or `..` yields a name that fails `SAFE_NAME` and can exceed 64 characters. TDD §10.2 requires managed names generated by `new_output_name()`.

**Proposal:** make `output_path` effectively mandatory (raise `ValueError` if `None`), or sanitize and clamp the stem. The API must always pass `OUTPUT_DIR / new_output_name("mp4")` (also stated in the handoff, §8.3).

### D-07 — S3 — `JobTimeoutError` can be exceeded by the encoder wait

`video_engine.py:335` — `proc.wait(timeout=60)` runs **after** the deadline check and can add 60 s past a 600 s job budget. TDD §10.1 describes a hard job time limit.

**Proposal:** `proc.wait(timeout=max(1.0, deadline - time.monotonic()))`, then treat `subprocess.TimeoutExpired` as `JobTimeoutError`.

### D-08 — S3 — FFmpeg stderr is piped but never drained during the job

`video_engine.py:117` — `stderr=subprocess.PIPE`, read only on non-zero exit (`:337`). Stderr is capped at `-loglevel error` so the risk is low, but a chatty decoder can fill the OS pipe buffer and deadlock the encoder. TDD §8's own reference skeleton uses `stderr=subprocess.DEVNULL`.

**Proposal:** drain stderr in a daemon thread into a bounded deque (keeps diagnostics), or set `DEVNULL` and log a generic message.

### D-09 — S3 — No frame cap while reading (TDD §8 deviation)

TDD §8: *"a frame cap is also enforced while reading because container metadata can be wrong."* `process_video` loops until EOF or timeout only. If metadata under-reports frames, progress exceeds 100 %; if a container reports a valid duration but contains far more frames, there is no structural stop besides the 600 s watchdog.

**Proposal:** cap at `MAX_VIDEO_DURATION_S * metadata.fps + margin` frames and log a warning when the cap is hit.

### D-10 — S3 — `JobCancelledError` is dead code

`errors.py:195` defines it (HTTP 409), `video_engine.py:44` imports it, `__init__.py` exports it — nothing ever raises it. Cancellation returns a `VideoInspectionResult(status="cancelled")` instead.

**Proposal:** either delete the class and its import/export, or document explicitly that cancellation is a **return value, not an exception**, so the API worker knows it must inspect `result.status` *and* catch exceptions (§8.4).

### D-11 — S2 — C-04 verifier returns false PASS for empty files

`training/verify_classes.py:107-122` returns `True` when **any** candidate DB file exists; `:125-139` does the same for the frontend. It never inspects file contents. Actual run:

```
[4] Checking Database Layer...
  Found database files: ['schema.sql']. Verifying constants...
[5] Checking Frontend Layer...
  Found frontend files: ['classes.ts']. Verifying constants...
  - database_layer : PASSED
  - frontend_layer : PASSED
```

Both files are **0 bytes**. The S5-M1 report correctly recorded these layers as "PENDING (no mock claims)"; the truncation event created empty placeholders, which flipped the verifier to PASS. AC-08 is currently **falsely satisfied**.

**Proposal:** require non-empty files, and parse them (regex for `D00|D10|D20|D40` in order for the frontend; verify the `CHECK`/`class_summary` constants for SQL). Keep returning `None` (honest pending) for missing **or empty** inputs.

### D-12 — S3 — `log` used before definition in `model_manager.py`

`model_manager.py:55` calls `log.warning(...)` inside the `except` of the Ultralytics import block, but `log` is not bound until line 62. If `from ultralytics import YOLO, settings` or `settings.update(...)` ever raises, the module import dies with `NameError` instead of degrading to `YOLO = None`.

**Proposal:** move `log = logging.getLogger(...)` above the `try` block.

### D-13 — S4 — Smoke-test cancellation is trivial

`training/smoke_gpu_video.py:192` sets `cancel_event` **before** calling `detect_video`, so it exercises only the "cancelled before processing started" branch (`video_engine.py:233-252`). Mid-stream cancellation is covered only by the mocked unit test. The report's "Cancellation and cleanup verified" is true but narrower than it reads.

**Proposal:** set the event from the progress callback after N frames (the dead `cancel_after_frames` helper at `:186-188` already shows the intent).

### D-14 — S4 — `nms_mode` status string is hardcoded

`model_manager.py:362` returns `nms_mode="end-to-end (nms=False)"` as a literal. `NMS_ARGS = {}` (`config.py:71`) is per TDD §3.3 default, but the status string is documentation, not a measurement.

**Proposal:** label it as the configured mode, e.g. `"end2end (configured)"`, or derive it from `NMS_ARGS`.

---

## 8. Handoff to the application owner (separate repository)

This section is the deliverable Shakib needs. It assumes Ram's CV service as-is and the TDD v1.1 contracts. Nothing here was implemented in this repository.

### 8.1 CV service surface (stable)

```python
from app.services.vision import get_vision_service, VideoInspectionResult, VisionInspectionResult

service = get_vision_service()          # process-wide singleton
service.initialize(device=None)         # -> bool; idempotent enough to call at startup

# Image (synchronous)
insp: VisionInspectionResult = service.detect_image(
    image_input=raw_bytes, conf=conf, filename=display_name,
    annotate=True, output_path=OUTPUT_DIR / new_output_name("jpg"),
)

# Video (blocking; call from a worker thread)
result: VideoInspectionResult = service.detect_video(
    video_input=src_path, conf=conf,
    output_path=OUTPUT_DIR / new_output_name("mp4"),      # MUST be explicit
    cancel_event=slot.cancel,                             # threading.Event
    progress_callback=lambda done, total, hits, counts: db_progress(iid, done, total, hits, counts),
    timeout_s=600.0,
)
```

`result.to_dict()` keys (verbatim from `types.py`): `input_filename, output_video_path, status, total_frames, frames_processed, frames_with_detections, total_detections, class_summary, processing_duration_s, processing_fps, model_inference_duration_s, model_inference_fps, models_used, device, conf_threshold, error_message, metadata{filename,width,height,fps,total_frames,duration_s,size_bytes}`.

### 8.2 Endpoints required by TDD v1.1 Table 6 — none exist

| Method | Endpoint | Success | Errors | Status here |
| :--- | :--- | :--- | :--- | :--- |
| GET | `/api/health` | 200 | — | **absent** (0 B) |
| GET | `/api/model/status` | 200 | — | **absent** (0 B) |
| POST | `/api/detect/image` | 200 | 400,413,415,422,503,500 | **absent** (0 B) |
| POST | `/api/detect/video` | **202 + inspection_id** | 400,409,413,415,422,503 | **never implemented** |
| POST | `/api/history/{id}/cancel` | 200 | 404,409 | **never implemented** |
| POST | `/api/camera/start` | 200 + inspection_id | 409,503 | **never implemented** |
| GET | `/api/camera/stream` | 200 stream | 409 | **never implemented** |
| POST | `/api/camera/stop` | 200 | 409 | **never implemented** |
| GET | `/api/history` | 200 | 422 | **never implemented** |
| GET | `/api/history/{id}` | 200 (also job polling) | 404,422 | **never implemented** |
| DELETE | `/api/history/{id}` | 204 | 404,409 | **never implemented** |
| GET | `/api/dashboard` | 200 | — | **never implemented** |
| GET | `/api/results/{name}` | 200 | 400,404 | **absent** (0 B) |

### 8.3 Video job contract (normative)

**`POST /api/detect/video`** — `multipart/form-data`: `file` (required), `conf` (form float, default 0.25, allowed 0.10–0.90).

1. Reject `Content-Length` over 200 MB (413) before reading the body.
2. Stream to a temp file in ≤1 MB chunks; abort and delete at >200 MB (413).
3. Validate: extension ∈ {`.mp4`, `.avi`} (415); decodable, `fps > 0`, `frame_count > 0` (415); duration ≤60 s and ≤1920×1080 (422).
4. Validate `conf` range **at the route** (422 `invalid_parameters`) — do not rely on the engine's clamp (D-04).
5. `iid = db_insert_inspection(input_type="video", filename=display, conf_threshold=conf, status="queued", nms_mode="end2end")`.
6. Acquire the single global `JobSlot`; on failure: mark the record `failed` / `"busy"`, delete the temp file, return **409** `{"error":{"code":"busy", ...}}`.
7. Start a daemon thread; return **202** `{"inspection_id": iid, "status": "queued"}`.

**Worker thread** — must do all of the following:

```
out_name = new_output_name("mp4")                 # ^[A-Za-z0-9_-]{8,64}\.mp4$
db_mark(iid, "processing", frames_total=<meta frames>)
try:
    res = service.detect_video(src, conf=conf, output_path=OUTPUT_DIR / out_name,
                               cancel_event=slot.cancel, progress_callback=cb, timeout_s=600)
    if res.status == "cancelled":
        db_finish(iid, "cancelled", "Job cancelled by request.", ...)
    else:
        db_finish(iid, "completed", None, frames..., output_name=out_name,
                  models_used=",".join(res.models_used), processing_ms=int(res.processing_duration_s*1000))
except VisionServiceError as e:       # includes JobTimeoutError(504), FFmpegExecutionError(500)
    db_finish(iid, "failed", e.message[:300], ...)
except Exception as e:
    db_finish(iid, "failed", str(e)[:300], ...)
finally:
    src.unlink(missing_ok=True)       # originals are not retained (PRD FR-09)
    slot.release()
```

Hard rules for this layer:

- **Pass `output_path` explicitly.** The engine's default writes into `data/outputs/` with an unsanitized stem (D-06) and would bypass the managed-name contract.
- **Never expose `result.output_video_path`.** Return `output_url = f"/api/results/{out_name}"`; the DB stores `output_name` only (TDD §11).
- **Treat cancellation as a status, not an exception** (D-10), and treat `VisionServiceError` as a status too — `process_video` **re-raises** on failure but **returns** on cancel.
- `progress_callback` is already throttled to ≈1 call/second by the engine (`video_engine.py:317-328`) — do not add a second throttle that loses the final update.
- `result.total_frames` comes from container metadata and may be `1` for odd containers (D-02). Clamp UI progress to 100 % and prefer `frames_processed` for display.

**`GET /api/history/{id}`** — returns TDD §10.3 `InspectionOut`. For video, `output_url` is non-null only when `status == "completed"`. Polled by the frontend at ~1 Hz while `status ∈ {queued, processing}`.

**`POST /api/history/{id}/cancel`** — 404 unknown id; 409 if that id is not the active slot owner; otherwise set `slot.cancel`, return 200 `{"inspection_id": id, "status": "cancelling"}`. The worker writes the terminal `cancelled` row.

**`GET /api/results/{name}`** — `SAFE_NAME = ^[A-Za-z0-9_-]{8,64}\.(jpg|png|mp4)$`; resolve inside `OUTPUT_DIR`; `FileResponse` with `media_type="video/mp4"` for `.mp4`. Starlette serves `Range` requests, which is what makes in-browser seeking work — verify by seeking to 50 % in the `<video>` element.

**Startup** — `init_db()` must run `UPDATE inspections SET status='failed', error_message='interrupted by restart' WHERE status IN ('queued','processing')` (TDD §11) so a killed job never looks alive.

**Shutdown** — release the slot, set `slot.cancel`, join the worker briefly; the engine deletes partial output on the non-completed path.

### 8.4 Acceptance tests Shakib must run (not run here)

| ID | Test | Expected |
| :--- | :--- | :--- |
| A-01 | `GET /api/health` on a fresh start | 200 `{"status":"ok"}` |
| A-02 | `GET /api/model/status` | `active_model="YOLO26m"`, `is_available=true`, `classes=["D00","D10","D20","D40"]` |
| A-03 | Upload a valid 640×512/40-frame MP4 | 202, `inspection_id`, DB row `queued→processing→completed` |
| A-04 | Poll `GET /api/history/{id}` during the job | `frames_processed` increases, ~1 update/s |
| A-05 | Download `output_url` | 200, `video/mp4`, plays in Chrome/Edge, seekable |
| A-06 | Second upload while A-03 runs | 409 `busy`, no orphan temp file, first job unaffected |
| A-07 | Cancel mid-job | 200; status becomes `cancelled`; **no output file** remains |
| A-08 | `.mkv` upload | 415 `unsupported_video` |
| A-09 | Corrupt `.mp4` | 415 `unsupported_video` |
| A-10 | 61 s video / 200 MB+ video | 422 `video_over_limit` / 413 `video_size_exceeded` |
| A-11 | `conf=0.05` and `conf=0.95` | 422 `invalid_parameters` |
| A-12 | Kill the server mid-job, restart | row flips to `failed`, message `interrupted by restart` |
| A-13 | `GET /api/results/..%2F..%2Fetc%2Fpasswd` | 400 `invalid_name` |
| A-14 | Image upload → annotated image renders → download | AC-02, for real this time |
| A-15 | Two uploads with the same original filename | distinct managed names, no overwrite (AC-15) |

A-03…A-13 are **BLOCKED** in this repository; they are not blocked in principle, only by the missing layer.

---

## 9. Evidence appendix

### 9.1 Video GPU smoke (re-run, real model, real GPU)

```
> $env:PYTHONPATH="...\backend"; .\.venv\Scripts\python.exe training\smoke_gpu_video.py
Checkpoint Path : ...\models\weights\yolo26m.pt
Actual SHA256   : 1BC41287DBDBC5EC5793D5D8F14CBA770E9E71E9C9E0CC0188B7146DA592D233  -> VERIFIED
CUDA Available  : True
Device Name     : NVIDIA GeForce RTX 5060 Laptop GPU
FFmpeg Path     : ...\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v9.0.2.exe
Created sample video: 40 frames @ 10.0 fps, 1156.5 KB
Init Status     : True (2627.0 ms)
Total Elapsed   : 1.20 s
Status          : completed
Frames Processed: 40        Frames With Detections: 40        Total Detections: 70
Class Summary   : {'D00': 50, 'D10': 20, 'D20': 0, 'D40': 0}
Processing FPS  : 34.58     Inference FPS: 38.34
Output Size     : 907.6 KB   H.264 Codec Detected: True
Cancellation Status: cancelled   (no partial file)
ALL S5-M3 VIDEO ENGINE GPU SMOKE TESTS PASSED!
EXITCODE=0
```

### 9.2 Independent ffprobe of the produced video

```
stream: codec_name=h264  profile=High  width=640  height=512  pix_fmt=yuv420p
        r_frame_rate=10/1  avg_frame_rate=10/1  nb_frames=40  duration=4.000000
format: mov,mp4,... duration=4.000000 size=929397 bit_rate=1858794

top-level atoms: [('ftyp',0,32), ('moov',32,975), ('free',1007,8), ('mdat',1015,928382)]
```

`moov` precedes `mdat` → **faststart confirmed**. `yuv420p` → browser-decodable. Frame count and rate preserved.

### 9.3 Image GPU + CPU smoke (re-run)

```
GPU Init OK : True (2603.1 ms)     CPU Init OK: True (585.4 ms)
GPU total latency: 73.92 ms (engine forward pass 32.83 ms)
CPU total latency: 227.76 ms (engine forward pass 221.78 ms)
GPU detections: 2  {'D00': 1, 'D10': 1, 'D20': 0, 'D40': 0}
  D00 0.6045 box [132.0,178.0,166.2,512.0]
  D10 0.5918 box [0.0,265.0,209.3,295.7]
CPU detections: 2  (MATCH)
GPU speedup: 3.08x
EXITCODE=0
```

### 9.4 Artifacts created by this audit (not source changes)

| Path | Cause |
| :--- | :--- |
| `runs/smoke_test_video/smoke_input.mp4` | Video smoke input (regenerated) |
| `runs/smoke_test_video/smoke_output_h264.mp4` | Video smoke output |
| `runs/smoke_test/smoke_annotated_gpu.jpg` | Image smoke output |
| `runs/smoke_test/smoke_annotated_cpu.jpg` | Image smoke output |
| `data/outputs/20261108_001641_stats_annotated.mp4` | pytest (`test_correct_frame_and_detection_statistics`) — see D-05 |
| `data/outputs/20261108_001642_callback_test_annotated.mp4` | pytest (`test_progress_callback`) — see D-05 |
| `%TEMP%\s5m4_*` scripts/logs | Audit tooling, outside the repository |

No file under `backend/`, `frontend/`, `training/`, `models/`, `dataset/` or `docs/` was modified.

---

## 10. TDD / PRD traceability (CV-verifiable rows only)

| Requirement | Source | Status | Evidence |
| :--- | :--- | :--- | :--- |
| FR-01 image upload & detection (engine side) | PRD §4.1 | **CV PASS / APP BLOCKED** | 7 image-engine tests + smoke; no route |
| FR-02 recorded video (engine side) | PRD §4.2 | **CV PASS / APP BLOCKED** | 18 tests + GPU run; no job/route |
| FR-04 four-class mapping | PRD §4.4 | **CV PASS** | JSON + checkpoint + `classes.py` |
| FR-06 configurable threshold 0.10–0.90 | PRD §4.6 | **CV PASS** (`MAX_CONFIDENCE=0.90`) | D-01 breaks the app-level import; D-04 clamp |
| FR-09 unique output names, temp cleanup | PRD §4.9 | **CV PARTIAL** | Engine deletes partials; default naming unsafe (D-06); D-05 pollutes |
| FR-10 job/cancel/timeout behaviour | PRD §4.10 | **CV PARTIAL** | Cancel + timeout implemented; no job slot/API (D-07, D-10) |
| TDD §8 fps/frame-count validation | TDD §8 | **FAIL** | D-02 |
| TDD §8 frame cap while reading | TDD §8 | **MISSING** | D-09 |
| TDD §8 H.264 / yuv420p / faststart / pad | TDD §8 | **PASS** | ffprobe + atom order |
| TDD §8 cancel → delete partial | TDD §8 | **PASS** | smoke + unit test 16 |
| TDD §10.1 one job at a time | TDD §10.1 | **NOT IMPLEMENTED** | No `JobSlot` in repo |
| TDD §10.2 limits 200 MB / 60 s / 1920×1080 / 10 min | TDD §10.2 | **PASS** | `config.py:104-107`, enforced in validator |
| TDD §10.3 single error shape | TDD §10.3 | **CV PASS / APP N/A** | `errors.py` `status_code`/`code`/`message`; handler absent |
| TDD §11 append-only `models_used` (C-01) | TDD §11 | **PASS** | `test_model_manager_c01_append_only_tracking` |
| AC-02 image E2E | PRD AC-02 | **BLOCKED** | no route, no UI |
| AC-04 video E2E | PRD AC-04 | **BLOCKED** | no route, no UI |
| AC-05 video failure handling (engine) | PRD AC-05 | **CV PASS** | unit tests 6,7,8,9,16,17,18 |
| AC-08 cross-layer consistency | PRD AC-08 | **FALSE PASS** | D-11 |
| AC-09 primary model active at startup | PRD AC-09 | **CV PASS / APP BLOCKED** | startup smoke; no `main.py` |
| AC-10 YOLO26n fallback | PRD AC-10 | **OUT OF SCOPE** | `YOLO26N_FALLBACK_ENABLED=False` |
| AC-15 no overwrite / temp cleanup | PRD AC-15 | **CV PARTIAL** | D-05, D-06 |

---

## 11. Recommended next actions (in order)

**Step 1 — decide, do not code yet (owner: Ram + Shakib).**
Confirm the three S1/S2 contract decisions: D-01 (config export), D-02 (reject fps/frame-count 0), D-04 (strict conf at route vs clamp in engine). D-04 is a shared decision; the other two are unambiguous TDD conformance.

**Step 2 — apply the approved Ram-owned fixes.**
Batch of 4 low-risk edits, each independently testable: D-01 (1 line), D-02 (~6 lines), D-05 (2 test call sites), D-12 (move 1 line). Re-run `pytest` and the video smoke after the batch; expect 59/59 and 40 frames again, plus a new rejection test for D-02.

**Step 3 — fix the AC-08 verifier (D-11).**
Until this is fixed, no C-04 claim should be made in any report or demo. This is a truthfulness blocker, not a code-quality one.

**Step 4 — Shakib implements `main.py`, `api/*`, `database/*`, `utils/files.py`, `frontend/*` in his repository** against §8 and TDD §10–§11. Ram's CV service needs no further change to support it beyond Step 2.

**Step 5 — Shakib runs A-01…A-15** and records actual outputs. Only then may AC-02 / AC-04 / AC-05 / AC-09 / AC-15 be marked recorded.

**Step 6 — re-run this audit** (same commands, §9) against the integrated repository, and correct the S5-M2 and S5-M3 claims listed in §6.

---

## 12. Residual risks

| Risk | Impact | Mitigation |
| :--- | :--- | :--- |
| Video FPS figures are timing-dependent (34.58 today vs 49.87 reported) | Demo claims look inflated | Quote a range or re-measure on the demo machine, same script |
| GPU is a discrete RTX 5060, while `AGENTS.md` describes an integrated Radeon | Documentation drift, wrong thermal/CPU assumptions | Correct `AGENTS.md` or document the delta |
| S5-M2/S5-M3 reports overstate "E2E" | Reviewer/demo credibility | Corrections listed in §6; append an erratum rather than rewriting history |
| Empty placeholder files satisfy existence-based checks | False certification (AC-08 today; possibly others tomorrow) | D-11 + content-based verification everywhere |
| `data/outputs` accumulates test files | Managed-output directory is not trustworthy | D-05, then clean the directory deliberately (both owners aware) |
| Single global model singleton + one inference lock | Image requests during a video job block on a frame boundary — by design (TDD §10.1) but must be demonstrated | Include in demo script |

---

**End of report. No fixes applied. Awaiting review before any Ram-owned change.**
