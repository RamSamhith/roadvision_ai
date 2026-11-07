# ROADVISION AI — RAM CV TRACK — DEFECT REPAIR BATCH 1 REPORT

**Batch:** CV Defect Repair 1
**Date:** 2026-11-08
**Repository:** `C:\Users\ramsa\Desktop\roadvision ai`
**Branch:** `master`
**HEAD:** `0f977c7` (no commits created)
**Author of work:** Ram CV track
**Source audit:** [`docs/project/ROADVISION_S5_M4_INTEGRATION_REPORT.md`](./ROADVISION_S5_M4_INTEGRATION_REPORT.md) §7 defect register

---

## 0. Verdict

| Item | Result |
|---|---|
| D-01 `MAX_CONFIDENCE` missing from config bridge | **FIXED** (1 line, verified by import + test) |
| D-02 invalid fps / frame count accepted | **FIXED** (validation + 8 regression cases) |
| D-05 tests write into production `data/outputs` | **FIXED** (2 call sites + autouse guard) |
| D-12 `log` used before definition | **FIXED** (ordering + real induced-import-failure test) |
| D-04 silent confidence clamping | **PARTIALLY ADDRESSED / STRICT REJECTION PENDING** — clamping is unchanged for compatibility, now logs a warning; decision documented in §5 |
| Regression suite | **72 passed, 1 warning, exit 0** |
| Baseline suite (before edits) | **59 passed, 1 warning, exit 0** |
| Image GPU + CPU smoke | **PASS** (identical detections, 3.45× GPU speedup) |
| Video GPU + H.264 + cancellation smoke | **PASS** (40 frames, 70 detections, H.264 High / yuv420p) |
| Writes to `data/outputs` during tests | **NONE** (11 pre-existing files byte-identical before/after) |
| Full FastAPI application integration | **NOT VERIFIED — application layer is 0 bytes** (see §10) |

No commit, push, file deletion, dataset change, weight change or training-result change was made.

---

## 1. Scope, ownership and pre-change safety

### 1.1 Files changed (all Ram-owned)

| File | Layer / owner | Change | Size before → after |
|---|---|---|---|
| `backend/app/config.py` | Ram — application config bridge | D-01: re-export `MAX_CONFIDENCE` | 1 155 B → 1 175 B |
| `backend/app/services/vision/video_engine.py` | Ram — CV service | D-02 metadata validation; D-04 clamp warning; docstrings | 14 414 B → 15 959 B |
| `backend/app/services/vision/model_manager.py` | Ram — CV service | D-12 logger ordering; D-04 clamp warning; docstrings | 13 813 B → 14 543 B |
| `backend/tests/test_video_engine.py` | Ram — CV tests | D-02 tests, D-04 test, D-05 call sites + guard fixture | 16 089 B → 22 067 B |
| `backend/tests/test_vision_model_manager.py` | Ram — CV tests | D-12 static + behavioural tests | not captured* → 5 608 B |
| `backend/tests/test_vision_config_classes.py` | Ram — CV tests | D-01 bridge test | not captured* → 3 170 B |

\* Pre-change sizes for these two test files were not captured individually in Phase 1 (only their post-change hashes are recorded here); the new hash values are authoritative for the resulting state.

### 1.2 Files explicitly **not** touched

- `backend/app/main.py` — **0 bytes**
- `backend/app/api/{health,detect,model,results}.py`, `backend/app/api/__init__.py` — **all 0 bytes**
- `backend/app/database/{db.py,schema.sql,__init__.py}` — **all 0 bytes**
- `backend/app/utils/{files.py,__init__.py}` — **all 0 bytes**
- `frontend/**` — scaffold only, untouched
- `dataset/**`, `models/weights/**`, training results, locked test set — untouched
- `docs/project/ROADVISION_S5_M4_INTEGRATION_REPORT.md` — **hash unchanged** (`581A0DFA…58E2`)

These are Shakib-owned per the audit and per TDD v1.1 §10. None were modified or reconstructed.

### 1.3 Pre-existing user work preserved

`git status` at baseline and after the batch is identical for tracked files. Seven tracked files already had user edits before this batch; they were not touched:

```
 M .gitignore
 M AGENTS.md
 M CHANGELOG.md
 M README.md
 M backend/requirements.txt
 M docs/project/SKILLS_INVENTORY.md
 M docs/setup/ENVIRONMENT_SETUP.md
```

All `backend/app/`, `backend/tests/`, `docs/project/*.md`, `docs/reference/`, `training/` content remains untracked exactly as it was (the whole CV track is pre-commit).

### 1.4 File hashes

SHA-256, uppercase:

| File | Before | After |
|---|---|---|
| `backend/app/config.py` | `2A3D1F23EDA9A88CEA75EF2D70BFC9F8062A0E342EB878A5E3D6894DFED2CD33` | `CC10737B7BF7B85FF6DD945269E05E3B6C21283A3EC312CF328B6BA9476D5164` |
| `backend/app/services/vision/video_engine.py` | `976CEBB99FD714460D3C11FAA14299CCB80A84F20EF7257F15E625A8E6C03205` | `FDC1F966FAA004BF9039999E58625D1F3D82306F47C1DF7C988EE84AD1006484` |
| `backend/app/services/vision/model_manager.py` | `867F0B317ACB772F1163B0CBAA7785327B1020BBC0064B8A4D733370537DEB2C` | `9BBF9113EE5EB2597CF70BB76E129CBA5D0451CC600BDB0678F949167B684EDF` |
| `backend/tests/test_video_engine.py` | `BB27443AA775D515CD8DCF253EFFB7714B0CB21616F396DED752DACDE625D2F0` | `F32B01F37B8209E1C5702062094F72C59C5BFE3F35926800A97D180835E56331` |
| `backend/tests/test_vision_model_manager.py` | — | `0AEA0B2D12DCECAA4A0E015CEF524A1FD2D08F7B2DBF98542A06079495E10DE9` |
| `backend/tests/test_vision_config_classes.py` | — | `8A602CAEF2660F996E25272B2F3E4A5FC126B1398D54E5989400B9DC380EC539` |
| `docs/project/ROADVISION_S5_M4_INTEGRATION_REPORT.md` | `581A0DFAC3C416BE45DB694CBB62488A5E4367F506B56D24DAC29796F7D558E2` | `581A0DFAC3C416BE45DB694CBB62488A5E4367F506B56D24DAC29796F7D558E2` (unchanged) |

### 1.5 Baseline test result

```
cd backend
$env:PYTHONPATH="C:\Users\ramsa\Desktop\roadvision ai\backend"
..\.venv\Scripts\python.exe -m pytest -q
```
→ `59 passed, 1 warning in 6.58s`, exit code 0.

The single warning is pre-existing and external: `StarletteDeprecationWarning` about `httpx`/`httpx2` from `fastapi/testclient.py`.

---

## 2. D-01 — `MAX_CONFIDENCE` missing from the config bridge

**Severity:** S1 (application would fail to import).
**File:** `backend/app/config.py` (Ram-owned bridge).

### Before

The `from app.services.vision.config import (...)` block re-exported `MIN_CONFIDENCE` and `MIN_LIVE_FPS` but omitted `MAX_CONFIDENCE`. `backend/app/api/detect.py` is contracted to do `from app.config import MAX_CONFIDENCE`, so restoring `detect.py` first would have produced `ImportError` at startup.

### After

```python
    MAX_WEBCAM_SESSION_SECONDS,
    MIN_CONFIDENCE,
    MAX_CONFIDENCE,
    MIN_LIVE_FPS,
```

Placed exactly where the recovered original had it (after `MIN_CONFIDENCE`, before `MIN_LIVE_FPS`). No other configuration value changed.

### Verification

```
>>> from app.config import MAX_CONFIDENCE, MIN_CONFIDENCE
>>> MIN_CONFIDENCE, MAX_CONFIDENCE
(0.1, 0.9)
```

Regression test `test_app_config_bridge_exports_confidence_bounds` asserts:
`app.config.MIN_CONFIDENCE == vision.config.MIN_CONFIDENCE == 0.10` and
`app.config.MAX_CONFIDENCE == vision.config.MAX_CONFIDENCE == 0.90`.

---

## 3. D-02 — Video validation accepts zero/invalid fps and frame count

**Severity:** S1 (TDD v1.1 §10.2 violation).
**File:** `backend/app/services/vision/video_engine.py` — `validate_video_file()`.

### Before

```python
width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = float(cap.get(cv2.CAP_PROP_FPS)) or 25.0
reported_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
...
calc_frames = max(1, reported_frames)
duration_s = calc_frames / fps
...
total_frames=calc_frames,
```

Consequences: a stream reporting `fps=0` was silently treated as 25 fps; a stream reporting `frame_count=0` was silently treated as 1 frame. Duration and progress were therefore fabricated, and TDD v1.1 §10.2 — *"videos must open with fps and frame count above zero"* — was not enforced.

### After

```python
width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
raw_fps    = float(cap.get(cv2.CAP_PROP_FPS))
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
...
duration_s = reported_frames / fps
...
total_frames=reported_frames,
```

`math.isfinite` was chosen over a bare `> 0` test so that `NaN` and `+inf` are also rejected (comparisons against `NaN` are always false, which would otherwise let `NaN` through a naive `<= 0` check). `import math` was added.

`VideoDecodeError` maps to HTTP 415 `unsupported_video` in the existing error hierarchy; no error type was added or changed.

### Compatibility implications

- Any container that cannot report both a positive fps and a positive frame count is now rejected with `VideoDecodeError` instead of being processed under fabricated metadata. This is the TDD-required behaviour, and it is a deliberate behaviour change for malformed containers (some streamed/partially-written MP4s report `CAP_PROP_FRAME_COUNT == 0`).
- Valid synthetic and dataset-derived MP4s are unaffected: `test_valid_video_metadata` still asserts `meta.fps == 10.0` and the correct frame count.
- No signature change; callers that already handle `VisionServiceError`/`VideoDecodeError` need no change.

### Regression tests (8 cases)

`backend/tests/test_video_engine.py`:
- `test_zero_fps_rejected`
- `test_zero_frame_count_rejected`
- `test_invalid_fps_rejected[-1.0 | nan | inf]` (parametrized)
- `test_invalid_frame_count_rejected[-5.0 | nan | inf]` (parametrized)

They use `mock_capture_with_metadata(fps, frame_count)` to drive the real `validate_video_file()` path and assert `VideoDecodeError` with `code == "unsupported_video"` and `status_code == 415`.

---

## 4. D-05 — Tests write into the production output directory

**Severity:** S2.
**Files:** `backend/tests/test_video_engine.py` (test-only change).

### Before

`process_video()` falls back to `DEFAULT_OUTPUT_DIR` (`data/outputs/`) when `output_path` is omitted. Two tests omitted it, so every suite run wrote servable artifacts into the production managed-output directory.

### After

1. Both call sites now pass an isolated target:
   - `test_correct_frame_and_detection_statistics` → `output_path=tmp_path / "stats_out.mp4"`
   - `test_progress_callback` → `output_path=tmp_path / "callback_out.mp4"`
2. An autouse guard fixture was added:

```python
@pytest.fixture(autouse=True)
def guard_production_output_dir():
    """D-05 guard: no test in this module may write into ``data/outputs``."""
    before = set(DEFAULT_OUTPUT_DIR.glob("*")) if DEFAULT_OUTPUT_DIR.is_dir() else set()
    yield
    after = set(DEFAULT_OUTPUT_DIR.glob("*")) if DEFAULT_OUTPUT_DIR.is_dir() else set()
    leaked = sorted(p.name for p in after - before)
    assert not leaked, f"Tests wrote into the production output directory: {leaked}"
```

The guard fails the offending test immediately if any new file appears. It is intentionally non-destructive: it never deletes existing artifacts.

### Evidence

All `process_video()` call sites in `backend/tests/` now pass `output_path` (verified by grep; 9/9).

A byte-level snapshot of `data/outputs/` was taken before the final full suite and again after it:

```
before: 11 files
after:  11 files
added: []
removed: []
changed: []
data/outputs unchanged: True
```

The 11 pre-existing artifacts (including `20261107_*` and `20261108_*` files created by earlier audit runs) were left in place, as instructed.

---

## 5. D-04 — Out-of-range `conf`: decision and current behaviour

**Severity:** S2.
**Status:** **Strict rejection NOT implemented. Clamping retained; now logged. Decision documented.**

### 5.1 What the contract says

- TDD v1.1 §6: confidence threshold is configurable per request, recommended default 0.25, **range 0.10 to 0.90**.
- TDD v1.1 §10: detection *routes* take a `conf` parameter within the allowed range. Boundary validation is the route's job; the image route (Shakib-owned) is contracted to reject out-of-range values before the engine sees them.
- The engine docstrings historically documented clamping as the engine-side behaviour (`process_video` arg range, `model_manager.predict` "clamped between MIN_CONFIDENCE and MAX_CONFIDENCE"). No test asserted rejection.

### 5.2 Why strict rejection was not implemented in this batch

1. **No documented engine-level rejection contract exists.** The only documented clamping site is the engine; the only documented rejection site is the API boundary. Adding rejection in the engine would change a documented programmatic contract without a TDD amendment.
2. **The video route does not exist yet.** `backend/app/api/*.py` are 0 bytes. Implementing rejection in the engine would pre-empt an API-layer decision that belongs to Shakib per TDD §10, and would risk double validation with a different status code.
3. **Return-value compatibility.** `VisionService.detect_video()` / `VideoEngine.process_video()` currently always complete for any numeric `conf`. Raising inside them would be a breaking change for programmatic callers (scripts, smoke tests, future workers) that rely on the clamp.
4. **The user instruction was conditional:** implement only if the CV service contract clearly supports it; otherwise leave pending with a recommendation. It does not.

### 5.3 What was implemented instead (non-silent clamping)

Both clamp sites now log a warning and keep the documented clamp:

```python
# video_engine.process_video() and model_manager.predict()
requested_conf = float(conf)
clamped_conf = max(MIN_CONFIDENCE, min(requested_conf, MAX_CONFIDENCE))
if clamped_conf != requested_conf:
    log.warning(
        "Requested confidence %.3f is outside [%.2f, %.2f]; using %.2f.",
        requested_conf, MIN_CONFIDENCE, MAX_CONFIDENCE, clamped_conf,
    )
```

Docstrings updated to state that values outside the range are clamped **and logged**, with strict rejection enforced at the API boundary (TDD v1.1 §10). Return values and status codes are unchanged.

Regression test `test_out_of_range_confidence_clamped_and_logged[5.0-0.9 | 0.01-0.1]` asserts:
- `result.conf_threshold` is the clamped bound,
- the model receives the clamped value (`mock.predict.call_args.kwargs["conf"]`),
- a warning record is emitted.

### 5.4 Compatibility implications of the two options (for the route owner)

| Option | Behaviour change | Compatibility impact |
|---|---|---|
| (a) Keep engine clamp + warn; reject at API boundary *(current)* | None in the engine; route returns 400/422 for out-of-range | Programmatic callers keep working; matches the image-route pattern |
| (b) Engine raises `VideoValidationError(..., 422)` | `conf=5.0` stops completing and starts raising | Breaking for any direct caller; route must not pre-validate or status codes diverge |

**Recommendation:** keep (a). When the video route is authored (TDD §10), validate `conf ∈ [0.10, 0.90]` at the boundary exactly as the image route does, and return an explicit `VideoValidationError`/400–422. If a future requirement demands rejection at the service layer, add an explicit `strict_conf: bool = False` flag and amend the TDD — do not change the default silently.

**Residual nuance (pre-existing, not introduced):** the immediate-cancellation return path (`video_engine.py`, before processing starts) reports `conf_threshold=conf` unclamped. No inference occurs on that path, so no threshold was applied; it is recorded here so the route owner is not surprised by the raw value in a cancelled response.

---

## 6. D-12 — `log` used before definition in `model_manager.py`

**Severity:** S3 (module import dies with `NameError` on any Ultralytics import/settings failure, defeating the `YOLO = None` fallback).
**File:** `backend/app/services/vision/model_manager.py`.

### Before

```python
try:
    from ultralytics import YOLO, settings
    settings.update({"sync": False})
except Exception as _e:
    log.warning(...)          # NameError: log is not bound yet
    try:
        from ultralytics import YOLO
    except Exception as _e2:
        YOLO = None
        log.error(...)        # NameError

log = logging.getLogger("roadvision.vision.model_manager")
```

### After

```python
# D-12: bind the module logger before the guarded Ultralytics import. ...
log = logging.getLogger("roadvision.vision.model_manager")

try:
    from ultralytics import YOLO, settings
    settings.update({"sync": False})
except Exception as _e:
    log.warning("Ultralytics import / settings update warning: %s", _e)
    try:
        from ultralytics import YOLO
    except Exception as _e2:
        YOLO = None
        log.error("Failed to import YOLO from ultralytics: %s", _e2)
```

### Verification (static + behavioural)

1. `test_logger_bound_before_ultralytics_import` — asserts the logger assignment precedes `from ultralytics import YOLO, settings` in the module source and that `model_manager.log.name` is correct.
2. `test_ultralytics_import_failure_degrades_gracefully` — the real proof. It creates a stub `ultralytics` package that raises `ImportError`, prepends it to `PYTHONPATH`, and imports the module in a subprocess. Result:

```
Ultralytics import / settings update warning: simulated ultralytics import failure
Failed to import YOLO from ultralytics: simulated ultralytics import failure
YOLO: None
log name: roadvision.vision.model_manager
exit 0
```

Before the fix this subprocess would have exited non-zero with `NameError: name 'log' is not defined`; the test asserts exit 0, `YOLO_IS_NONE=True`, and the logged warning on stderr.

---

## 7. Test evidence

### 7.1 Targeted runs

```
cd backend
$env:PYTHONPATH="C:\Users\ramsa\Desktop\roadvision ai\backend"
..\.venv\Scripts\python.exe -m pytest tests/test_video_engine.py tests/test_vision_model_manager.py tests/test_vision_config_classes.py -q
```
→ **42 passed in 6.03s**, exit 0.

New-defect-only selection:

```
..\.venv\Scripts\python.exe -m pytest tests/test_video_engine.py tests/test_vision_model_manager.py \
  tests/test_vision_config_classes.py -v \
  -k "zero_fps or zero_frame_count or invalid_fps or invalid_frame_count or clamped_and_logged or logger_bound or bridge_exports or degrades_gracefully"
```
→ **13 passed, 29 deselected in 5.19s**, exit 0 (D-02 ×8, D-04 ×2, D-12 ×2, D-01 ×1).

### 7.2 Full CV suite (final)

```
cd backend
$env:PYTHONPATH="C:\Users\ramsa\Desktop\roadvision ai\backend"
..\.venv\Scripts\python.exe -m pytest -q
```
→ **72 passed, 1 warning in 9.00s**, exit 0.

Delta: **59 → 72 (+13)** — 8 D-02 cases, 2 D-04 cases, 2 D-12 tests (ordering + induced failure), 1 D-01 test.

The only warning remains the pre-existing FastAPI/Starlette `httpx2` deprecation notice.

### 7.3 No writes to production output directory

Byte snapshot comparison after the final suite (see §4):
`data/outputs unchanged: True | count: 11`.

---

## 8. Hardware verification

Host: Windows 11, Python 3.11.9, torch 2.11.0+cu128, CUDA on **NVIDIA GeForce RTX 5060 Laptop GPU**, ultralytics 8.4.202, FFmpeg 9.0.2 (imageio-ffmpeg bundle), OpenCV 5.0.0.

### 8.1 Image inference — GPU + CPU parity

Command: `.\.venv\Scripts\python.exe training\smoke_gpu_inference.py` → exit 0.

```
Checkpoint SHA-256 : 1BC41287DBDBC5EC5793D5D8F14CBA770E9E71E9C9E0CC0188B7146DA592D233 (verified)
CUDA Available     : True
Device Name        : NVIDIA GeForce RTX 5060 Laptop GPU
Primary Target     : cuda:0

GPU (cuda:0): 62.77 ms total  | engine forward 26.23 ms | 2 detections
CPU         : 216.57 ms total | engine forward 211.08 ms | 2 detections
Class counts match: {'D00': 1, 'D10': 1, 'D20': 0, 'D40': 0}
GPU speedup: 3.45×
```

CPU fallback remains functional and returns identical detections.

### 8.2 Video inference — GPU pipeline, H.264 output, cancellation

Command: `.\.venv\Scripts\python.exe training\smoke_gpu_video.py` → exit 0.

```
Status            : completed
Total Frames      : 40
Frames Processed  : 40
Total Detections  : 70
Class Summary     : {'D00': 50, 'D10': 20, 'D20': 0, 'D40': 0}
Processing FPS    : 39.00
Inference FPS     : 43.68
Total Elapsed     : 1.05 s
Output Size       : 907.6 KB
H.264 Codec       : detected
Cancellation      : status "cancelled"; partial file removed
```

`ffmpeg -i runs/smoke_test_video/smoke_output_h264.mp4`:

```
Duration: 00:00:04.00, bitrate: 1858 kb/s
Stream #0:0: Video: h264 (High) (avc1), yuv420p(progressive), 640x512, 10 fps
```

Container layout (faststart check):

```
size_bytes: 929397
moov_offset: 36   mdat_offset: 1019
faststart: True
```

**Honest limitation:** `smoke_gpu_video.py` sets the cancel event *before* `detect_video()`, so the hardware test exercises only the immediate-cancel branch (audit D-13 / D-10). Mid-stream cancellation and partial-file cleanup are covered by the mocked unit test `test_cancellation_cleans_partial_output`, which sets the event after the first frame and asserts the partial output is deleted. End-to-end mid-stream cancellation on the GPU remains unverified at hardware level.

### 8.3 Performance impact of the changes

- D-02 adds two `float()` reads and two `isfinite`/range checks per *file validation* (once per job). Not measurable in steady state.
- D-04 adds one `float()` conversion and one comparison per *request*. Not measurable.
- D-12 is import-time ordering only; no runtime cost.

Smoke-to-smoke video numbers are within run-to-run variance (audit: 40 frames / 70 detections / 34.58 FPS / 1.20 s; this run: 40 frames / 70 detections / 39.00 FPS / 1.05 s). No throughput claim is made; the faster run is not attributed to these edits.

---

## 9. Change review — no unrelated edits

- Every source edit is confined to the six Ram-owned files listed in §1.1.
- No change was made to `errors.py`, `config.py` values, `annotate.py`, `classes.py`, `types.py`, `service.py`, or any non-CV module.
- `git status --porcelain` after the batch matches the baseline untracked/modified structure; the seven pre-existing tracked modifications are unchanged.
- `git diff --stat` for tracked files still reports only those seven user-modified files (`.gitignore`, `AGENTS.md`, `CHANGELOG.md`, `README.md`, `backend/requirements.txt`, `docs/project/SKILLS_INVENTORY.md`, `docs/setup/ENVIRONMENT_SETUP.md`).
- `docs/project/ROADVISION_S5_M4_INTEGRATION_REPORT.md` hash is byte-identical to baseline; the audit artifact was preserved.
- No commits, pushes, or deletions.

Note: `runs/smoke_test/` and `runs/smoke_test_video/` were rewritten by the mandated hardware smoke commands (annotated JPEG, input/output MP4). These are smoke-test outputs, not the locked test set or training results; the scripts themselves create/overwrite them on every run.

---

## 10. Not verified / blocked / remaining

### 10.1 Application integration (blocked — outside this batch)

The FastAPI application layer is **0 bytes**: `backend/app/main.py`, all of `backend/app/api/*.py`, `backend/app/database/*`, and `backend/app/utils/*`. There is therefore:

- no real `app.main` to start,
- no route to exercise `from app.config import MAX_CONFIDENCE` end-to-end,
- no HTTP path to exercise `conf` boundary validation or the video route,
- no browser/E2E surface to verify.

`backend/tests/test_production_app.py` is also 0 bytes, so no test exercises the real application. Per the ownership rules, none of this was reconstructed. **No claim of full application integration is made.**

### 10.2 Defects still open (from audit §7, not in this batch)

| ID | Sev | Description | Status |
|---|---|---|---|
| D-03 | S2 | Missing video raises `FileNotFoundError` (not a `VisionServiceError` → unmapped 500) | Open |
| D-04 | S2 | Strict confidence rejection | **Pending decision** — clamping now logged; see §5 |
| D-06 | S2 | Default output name derived from raw stem (`SAFE_NAME` violation) | Open |
| D-07 | S3 | `proc.wait(timeout=60)` can exceed the job deadline | Open |
| D-08 | S3 | FFmpeg stderr piped but not drained during the job | Open |
| D-09 | S3 | No frame cap while reading (TDD §8 deviation) | Open |
| D-10 | S3 | `JobCancelledError` is dead code | Open |
| D-11 | S2 | `training/verify_classes.py` false-PASSes 0-byte `schema.sql` / `classes.ts` | Open |
| D-13 | S4 | Video smoke cancellation is trivial (pre-set event) | Open |
| D-14 | S4 | `nms_mode` status string is hardcoded | Open |

### 10.3 Known limitations of this batch's evidence

- D-12's behavioural test uses a stub package in a subprocess; it proves the fixed ordering handles a failing import, but it does not test a real Ultralytics installation failure.
- The D-05 guard detects *new* entries in `data/outputs`; byte-level modification of an existing file is caught by the manual hash snapshot, not by the fixture.
- Mid-stream GPU cancellation is covered only by a mocked unit test (see §8.2).
- Performance figures are single-run measurements on a laptop GPU; they are not a benchmark.

---

## 11. Sign-off checklist

- [x] Phase 1 baseline captured (branch, HEAD, status, diffs, hashes, 59-test run)
- [x] Ownership confirmed before editing; Shakib layer untouched
- [x] D-01 fixed and tested
- [x] D-02 fixed and tested (8 regression cases)
- [x] D-05 fixed and tested; `data/outputs` byte-identical
- [x] D-12 fixed and tested (ordering + induced failure)
- [x] D-04 inspected; strict rejection left pending with documented rationale and compatibility analysis
- [x] Targeted tests: 42 passed
- [x] Full suite: 72 passed, exit 0
- [x] Image GPU + CPU parity verified
- [x] Video GPU pipeline, H.264 output, cancellation cleanup verified
- [x] No commits, pushes, deletions, dataset/weight/training-result changes
- [x] Audit report preserved byte-identically
- [x] Full application integration explicitly **not** claimed

**Batch complete. Awaiting review before any further defect work.**
