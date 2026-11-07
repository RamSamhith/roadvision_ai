# RoadVision AI — Requirements Traceability Matrix

**Prepared:** 2026-11-05 (Stage 2: document analysis and environment preparation)
**Sources:** TDD v1.1, PRD v1.1, Project Proposal — see `docs/source/DOCUMENT_REGISTER.md`
**Authority order:** TDD v1.1 → PRD v1.1 → Project Proposal

---

## 0. How to read this matrix

- **Requirement ID** — official identifiers (`FR-xx`, `AC-xx`, `F1`–`F6`) are used exactly
  as the documents define them. Where a document states a requirement without assigning an
  ID, a traceability label is used: `TDD-nn`, `PRD-nn`, `PROP-nn`. **These labels are
  bookkeeping added by this matrix, not requirement IDs invented by the source documents.**
- **Status vocabulary** (fixed for this project):
  - `COMPLETED` — implemented *and* verified by an executed command or observable result.
  - `PARTIALLY COMPLETED` — some work exists; the requirement is not yet satisfiable.
  - `NOT STARTED` — no implementation exists.
  - `BLOCKED` — cannot start until a decision, dataset, or external input is available.
- **Nothing in this project has been functionally implemented yet.** This stage deliberately
  stopped at environment preparation. Model training, dataset acquisition and feature
  implementation were explicitly out of scope.

**Repository state at the time of this audit**

| Area | Actual state |
| :--- | :--- |
| `backend/` | `requirements.txt` only. No `app/`, no `tests/`, no application code. |
| `frontend/` | Vite + React 19 + TypeScript + Tailwind v4 scaffold; one placeholder shell page. No product pages. |
| `training/` | Does not exist. |
| `models/` | `configs/` and `weights/` with `.gitkeep` only. No checkpoints. |
| `data/` | `raw/`, `processed/`, `annotations/` with `.gitkeep` only. No dataset. |
| `docs/` | `source/`, `reference/`, `project/`, `setup/`. No `architecture/`. |

---

## 1. Product objectives and scope

| Requirement ID | Requirement | Source document | Section / page | Implementation area | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| PROP-01 | Detect four road-damage categories | Proposal | §3 Objectives, p3 | Model + backend + frontend | NOT STARTED |
| PROP-02 | Support image, recorded-video and live-webcam input | Proposal | §3, §6, p3 / p6 | Backend input modules, frontend pages | NOT STARTED |
| PROP-03 | Display bounding boxes, class labels and confidence scores | Proposal | §3, §7, p3 / p6 | Backend annotation, frontend result view | NOT STARTED |
| PROP-04 | Generate class-wise detection summaries | Proposal | §3, §7, p3 / p6 | Backend aggregation, frontend summary | NOT STARTED |
| PROP-05 | Store inspection history locally | Proposal | §3, p3 | SQLite + history API/page | NOT STARTED |
| PROP-06 | Evaluate detection performance using labelled test data | Proposal | §3, §5.4, p3 / p5 | `training/evaluate.py` | NOT STARTED |
| PROP-07 | Provide a lightweight fallback model | Proposal | §3, §5.2, p3 / p5 | Model manager + weights | NOT STARTED |
| PROP-08 | Operate without paid cloud services | Proposal | §1, §3, p3 | Whole system (local-only) | PARTIALLY COMPLETED — no cloud dependency exists in the prepared stack (verified: all installed packages local; no cloud SDKs) |
| PROP-09 | Locally running web application (React + FastAPI + SQLite) | Proposal | §12, p10 | Full stack | PARTIALLY COMPLETED — stack installed and building; no features |
| PROP-10 | Position as preliminary assistive screening tool, not engineering-grade assessment | Proposal | §1, §12.1, p3 / p10 | README + UI copy | PARTIALLY COMPLETED — documented in README; no UI copy yet |
| PROP-11 | Seven-day academic development schedule, two-person team | Proposal | §10, p9 | Process | NOT STARTED (delivery tracking is a project-management activity) |
| PRD-01 | Product goals: four categories, three input modes, clear results, simple dashboard, local history, no paid cloud, usable without primary model | PRD | §2, p3 | Whole system | NOT STARTED |
| PRD-02 | Target users: students, academic evaluators, preliminary visual inspectors | PRD | §3, p3 | UX decisions | NOT STARTED |
| PRD-03 | Caution: webcam inputs differ from RDD2022 (domain shift); live mode is a functional demo only | PRD | §3, p4 | UI copy + report | NOT STARTED |

## 2. Functional requirements (PRD §4)

| Requirement ID | Requirement | Source document | Section / page | Implementation area | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| FR-01 | Image upload: accept JPG/JPEG/PNG, validate content and size, display, detect, show boxes/labels/confidence/class counts, view and download annotated image | PRD | §4.1, p4 | `backend/app/api` image route; `frontend` image page | NOT STARTED |
| FR-01a | Validation must confirm the file actually decodes as an image, not only its extension | PRD | §4.1, p4 | `backend/app/utils/files.py::validate_image` | NOT STARTED |
| FR-02 | Recorded-video upload: MP4/AVI, validate, background job, progress, cancel, H.264 browser-playable output, preview + download, class summary, frames processed and frames with detections | PRD | §4.2, p4–5 | `backend/app/api/video.py`, FFmpeg writer, video page | NOT STARTED |
| FR-02a | Output must be re-encoded to a browser-playable format (MP4/H.264); OpenCV's default MP4 writer may not play in browsers | PRD | §4.2, p4–5 | `open_h264_writer` (TDD §8) | NOT STARTED (FFmpeg with libx264 verified available) |
| FR-03 | Live webcam: capture via chosen path, annotated live feed, classes + confidence, start/stop, active model + measured FPS, camera error handling, one session at a time, auto-stop at limit, one aggregated record | PRD | §4.3, p5 | `backend/app/services/camera.py`, MJPEG route, live page | NOT STARTED |
| FR-03a | **Camera path decision must be recorded before FR-03 development**; recommended = backend capture with OpenCV DirectShow streamed as MJPEG | PRD | §4.3, p5 | Architecture decision record | **COMPLETED (decision recorded)** — TDD v1.1 §9 already fixes Option B (backend capture, DirectShow, MJPEG); see `OPEN_QUESTIONS.md` D-10 |
| FR-04 | Four detection classes with fixed indices 0=D00, 1=D10, 2=D20, 3=D40, identical in model, backend, database and frontend | PRD | §4.4, p5 | `backend/app/classes.json` + model `names` + DB constants + frontend labels | NOT STARTED |
| FR-04a | Class order is the single source of truth, defined once and verified by an automated consistency check (AC-08) | PRD | §4.4, p5 | `classes.json` + pytest check | NOT STARTED |
| FR-04b | Annotations with any other RDD2022 code are excluded from training and the exclusions counted | PRD | §4.4, p5 | `training/convert_annotations.py` | NOT STARTED |
| FR-05 | Model selection: YOLO26m primary, trained/tested YOLO26n fallback, never silent, active model displayed, fallback notice + reason, logged, model stored per inspection | PRD | §4.5, p5–6 | `backend/app/services/model_manager.py` | NOT STARTED |
| F1 | Fallback trigger: YOLO26m checkpoint missing/corrupt/fails to load → start on YOLO26n, log, notify | PRD / TDD | PRD §4.5 p6; TDD §3.3 p5 | Model manager | NOT STARTED |
| F2 | Fallback trigger: YOLO26m warm-up inference or class check fails → start on YOLO26n, log, notify | PRD / TDD | PRD §4.5 p6; TDD §3.3 p5 | Model manager | NOT STARTED |
| F3 | Fallback trigger: image inference runtime failure → retry once on YOLO26m, then switch and process on YOLO26n | PRD / TDD | PRD §4.5 p6; TDD §3.3 p6 | Model manager | NOT STARTED |
| F4 | Fallback trigger: video job failure → restart once from the beginning on YOLO26n; one model per output video; mark failed if YOLO26n also fails | PRD / TDD | PRD §4.5 p6; TDD §3.3 p6 | Video worker | NOT STARTED |
| F5 | Fallback trigger: live FPS below minimum (recommended 5) for 10 s → switch session to YOLO26n with notice, record both models | PRD / TDD | PRD §4.5 p6; TDD §3.3 p6 | Camera service | NOT STARTED |
| F6 | Optional manual model selection | PRD / TDD | PRD §4.5 p6; TDD §3.3 p6 | Frontend control | NOT STARTED (optional) |
| FR-05a | A COCO-only YOLO26n checkpoint is not a valid fallback; fallback counts as operational only after training + 3-mode smoke test + recorded metrics | PRD / TDD / Proposal | PRD §4.5 p6; TDD §3.2 p5; Proposal §5.2 p5 | Weights + evaluation | NOT STARTED |
| FR-06 | Detection results per inspection: annotated output, category, confidence, total detections, class-wise counts, status, model used, threshold used | PRD | §4.6, p6–7 | API schema + frontend | NOT STARTED |
| FR-06a | Confidence threshold configurable, default 0.25, range 0.10–0.90, chosen on validation set, documented; NMS IoU threshold documented; scores not described as guaranteed probabilities | PRD | §4.6, p7 | Config + UI + report | NOT STARTED |
| FR-07 | Dashboard: total sessions, total detections, class-wise counts, recent history, active model + fallback notice, access to all modes, empty state, totals computed from SQLite | PRD | §4.7, p7 | `/api/dashboard` + dashboard page | NOT STARTED |
| FR-08 | Inspection history in SQLite with the 12 stored fields of Table 6; no large blobs in DB; view, delete record + outputs | PRD | §4.8, p7 | DB schema (TDD §11) + history API/page | NOT STARTED |
| FR-09 | Output management: dedicated output dir, unique generated filenames, never use client filename as a path, graceful missing-file handling, temp cleanup, original-upload retention policy, free-space check (≥2× input size before video job) | PRD | §4.9, p7–8 | `utils/files.py`, startup cleanup | NOT STARTED |
| FR-10 | Error handling and job management for every failure class (bad upload, inference, video, timeout, cancel, camera, busy, no model, DB write); all errors logged with timestamp and cause; no stack traces to users | PRD | §4.10, p8 | `errors.py`, logging config | NOT STARTED |
| PRD-04 | Operating limits (recommended): image ≤20 MB / ≤8192 px; video MP4/AVI ≤200 MB, ≤60 s, ≤1920×1080; job limit 10 min; webcam ≤10 min; min live FPS 5; 1 concurrent job | PRD | §4.11, p8–9 | `backend/app/config.py` | NOT STARTED (values approved? see `OPEN_QUESTIONS.md` Q-01) |

## 3. Non-functional requirements (PRD §6)

| Requirement ID | Requirement | Source document | Section / page | Implementation area | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| NFR-PERF | Honest measured performance; visible video progress; usable live inference with FPS displayed | PRD | §6, p10 | Backend + frontend | NOT STARTED (no metrics claimed) |
| NFR-REL | Understandable upload errors; FR-05 model rules; camera failures must not crash; recovery without restart | PRD | §6, p10 | Backend | NOT STARTED |
| NFR-USE | Clear navigation, readable labels, consistent layout, loading/empty/error states | PRD | §6, p10 | Frontend | NOT STARTED |
| NFR-PRIV | Local processing only; no uploads to paid/external services; local records; backend bound to 127.0.0.1; no external API calls during inference (AC-18) | PRD | §6, p10 | Whole system | NOT STARTED (design intent recorded; no server exists yet) |
| NFR-PLAT | Windows 11, RTX 5060; React/TS/Vite/Tailwind; Python/FastAPI/OpenCV/PyTorch; CUDA build must support this GPU; must also run on CPU with documented lower speed | PRD | §6, p10 | Environment | **COMPLETED for the environment** — CUDA PyTorch verified on `cuda:0` (sm_120); CPU path verified; see `docs/setup/ENVIRONMENT_SETUP.md` |
| NFR-MAINT | Setup/run steps, versions, limits, thresholds documented; local log file; configuration in one place | PRD | §6, p10 | README, config module, logging | PARTIALLY COMPLETED — versions and setup documented; config module and logging do not exist yet |

## 4. Dataset and model engineering

| Requirement ID | Requirement | Source document | Section / page | Implementation area | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| TDD-01 | Complete RDD2022 acquisition target; originals preserved; conversion writes to separate directories | TDD | §4.1, p7 | `training/`, `data/` | NOT STARTED (explicitly out of scope for this stage) |
| TDD-02 | Verify each downloaded file size/MD5 against the figshare listing; `zipfile.testzip()`; short extraction path; free-space check; record file counts | TDD | §4.1, p7 | `training/` acquisition script | NOT STARTED |
| TDD-03 | `inspect_dataset.py`: folders, image/annotation counts, missing annotations, class distribution overall and per country, duplicates, unreadable files, dimensions, summary | TDD | §4.2, p7 | `training/inspect_dataset.py` | NOT STARTED |
| TDD-04 | `convert_annotations.py`: Pascal VOC XML → YOLO normalised format, fixed class mapping, conversion report | TDD / PRD / Proposal | TDD §4.3 p7–8; PRD §5.2 p9; Proposal §4.3 p4 | `training/convert_annotations.py` | NOT STARTED |
| TDD-05 | Conversion validation rules: true image size, size-mismatch logging, swapped min/max correction, tolerance clipping with count, exclusion of out-of-bounds/non-numeric/zero-area/unsupported classes, per-reason counts | TDD | §4.3, p8 | Converter + unit tests | NOT STARTED |
| TDD-06 | Group-aware split: hash exact-duplicate check, dHash near-duplicate grouping with recorded threshold, stratified by rarest class, recorded seed, ~80/10/10, frozen split lists | TDD / PRD | TDD §4.4 p8–9; PRD §5.3 p9–10 | `training/split_dataset.py` | NOT STARTED |
| TDD-07 | Split disjointness verification (no group/hash in two splits), result stored in dataset record | TDD / PRD | TDD §4.4 p9; PRD §5.3 p10 | `assert_disjoint` + report | NOT STARTED |
| TDD-08 | YOLO dataset layout `images|labels/{train,val,test}` + generated `data.yaml` with absolute path and class names D00/D10/D20/D40 | TDD | §4.5, p9 | `training/` | NOT STARTED |
| TDD-09 | Training subset strategy: freeze val/test first, subsample only train, keep all rare-class images, size via measured formula | TDD / PRD | TDD §4.6 p9; PRD §5.1 p9 | `training/` | NOT STARTED |
| TDD-10 | Staged smoke test: Stage 0 GPU gate, Stage 1 data smoke (~200 images, 1 epoch YOLO26n), Stage 2 memory ladder (640 px; batch 16/8/4), Stage 3 pilot, Stage 4 main run with resume | TDD | §5.2, p10–11 | `training/smoke_train.py`, `training/train.py` | NOT STARTED |
| TDD-11 | YOLO26m go/no-go at Day 3 (fit at batch ≥4 and enough images for rare classes) | TDD / Proposal | TDD §5.2 p11; Proposal §10 p9 | Training decision | NOT STARTED |
| TDD-12 | Training hygiene: pretrained weights, per-epoch checkpoints, resume, logs, recorded Ultralytics/PyTorch/driver versions, never tune on test, app stopped, plugged in / high performance, Windows `__main__` guard, few workers | TDD | §5.1, p10 | Training scripts | NOT STARTED |
| TDD-13 | Evaluate once on frozen test split with `conf=0.001`, per-class mAP, precision/recall at documented operating threshold | TDD / PRD / Proposal | TDD §16 p20; PRD §11 p13–14; Proposal §5.4 p5 | `training/evaluate.py` | NOT STARTED |
| PROP-12 | Train YOLO26n first as a pilot; YOLO26m as main detector | Proposal / TDD | Proposal §5 p5; TDD §5 p9–10 | Training order | NOT STARTED |

## 5. Backend API, database and frontend

| Requirement ID | Requirement | Source document | Section / page | Implementation area | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| TDD-14 | Modular client–server, all components local, **one backend process, one Uvicorn worker**, bound to 127.0.0.1 | TDD | §2, p4 | `backend/app/main.py` | NOT STARTED |
| TDD-15 | Development via Vite proxy `/api → 127.0.0.1:8000`; demonstration via `npm run build` served by FastAPI static files (one port) | TDD / PRD | TDD §2.1 p4; PRD §8 p11 | `frontend/vite.config.ts`, FastAPI StaticFiles | **PARTIALLY COMPLETED** — proxy configured and build verified; FastAPI static serving not implemented |
| TDD-16 | Heavy handlers are plain `def` (thread pool); event loop stays free; all forward passes through one lock | TDD | §2.1 p5, §10.1 p14 | API + services | NOT STARTED |
| TDD-17 | Endpoints: health, model status, detect/image, detect/video, cancel, camera start/stream/stop, history list/get/delete, dashboard, results/{name} with the documented status codes | TDD | §10, p14 | `backend/app/api/` | NOT STARTED |
| TDD-18 | One job slot for video + webcam (409 busy); image requests serialised by the inference lock; video returns 202; progress ≤1 update/s; cancel sets event; startup converts leftover queued/processing to failed "interrupted by restart" | TDD | §10.1, p14 | `services/job_slot.py`, DB | NOT STARTED |
| TDD-19 | Upload handling: streamed save, 413 above limit, Content-Length pre-check, sanitised display name, generated storage names, Pillow verify + OpenCV decode, video fps/frame-count checks | TDD | §10.2, p14–15 | `utils/files.py` | NOT STARTED |
| TDD-20 | `GET /api/results/{name}` accepts only pattern-matching managed names resolved inside the output directory; DB/API never expose absolute paths | TDD | §10.2, p15 | `api/results.py` | NOT STARTED |
| TDD-21 | Uniform error shape `{"error":{"code","message"}}` including 422; no stack traces or paths | TDD | §10.3, p15 | `errors.py` | NOT STARTED |
| TDD-22 | Pydantic schemas: `Detection`, `InspectionOut`, `ImageResult`, status Literal, `nms_mode`, frame counters, `output_url` | TDD | §10.3, p15–16 | `backend/app/schemas.py` | NOT STARTED |
| TDD-23 | SQLite in WAL mode, `inspections` table exactly as specified, CHECK constraints, index on created_at, per-operation connections, parameterised SQL, UTC ISO-8601 timestamps, dashboard aggregation in Python | TDD | §11, p16–17 | `backend/app/database/` | NOT STARTED |
| TDD-24 | Frontend pages: Dashboard, Image, Video, Live Camera, History — with the content listed in Table 9 | TDD | §12, p17 | `frontend/src/pages` | NOT STARTED (scaffold only) |
| TDD-25 | Loading/empty/error states everywhere; shared API client + TS types mirroring the Pydantic schemas; polling hook; MJPEG `img`; threshold control within range | TDD | §12, p17–18 | `frontend/src/{services,types}` | NOT STARTED |
| TDD-26 | Video module: validate → queued → job slot → thread → 202; sequential read + frame cap; per-frame detection; ~1 Hz progress; draw + pipe to FFmpeg H.264 yuv420p faststart, even dimensions; cancel/timeout; cleanup; delete original | TDD | §8, p11–12 | Video worker | NOT STARTED |
| TDD-27 | Webcam module: backend capture (Option B), DirectShow, capture thread, latest JPEG + MJPEG, explicit stop, watchdog, session cap, guaranteed release, shutdown hook, aggregated record only | TDD | §9, p13–14 | `services/camera.py` | NOT STARTED |
| TDD-28 | End-to-end (NMS-free) mode chosen once, used for both models and in evaluation; mode + IoU recorded per inspection | TDD | §3.4, p6 | Config + DB | **BLOCKED** — requires team decision (`OPEN_QUESTIONS.md` Q-02) |
| TDD-29 | `classes.json` as single source of truth; model `names` validated at load | TDD / PRD | TDD §3.3 p5, §4.3 p7; PRD §4.4 p5 | `backend/app/classes.json` | NOT STARTED |

## 6. Security, resources and quality

| Requirement ID | Requirement | Source document | Section / page | Implementation area | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| TDD-30 | Upload caps, content-based type checks, pixel limit, video checks, generated names, no client paths | TDD | §15, p19 | Backend | NOT STARTED |
| TDD-31 | Model load/class/warm-up checks, F1–F6, 503 when unavailable, low confidence never treated as failure | TDD | §15, p19 | Model manager | NOT STARTED |
| TDD-32 | Resource cleanup: capture/encoder/camera handles and temp files at job end and at startup | TDD | §15, p19 | Services | NOT STARTED |
| TDD-33 | Network: 127.0.0.1 only, no external calls, CORS avoided, no auth (single-user prototype) | TDD | §15, p19 | main.py | NOT STARTED |
| TDD-34 | Rotating local log file with timestamps for model loading, fallback activation and job failures | TDD / PRD | TDD §15 p20; PRD §4.10 p8 | Logging config | NOT STARTED |
| TDD-35 | Unit tests (pytest): conversion formula, class mapping, splitter disjointness, filename sanitiser, results-route validation | TDD | §16.1, p20 | `backend/tests/` | NOT STARTED (pytest 9.2.0 installed and runnable) |
| TDD-36 | API tests (TestClient): invalid type, oversize, corrupt image, busy 409, cancel, error shape, paging limits | TDD | §16.1, p20 | `backend/tests/` | NOT STARTED |
| TDD-37 | Failure injection tests: rename YOLO26m, rename both, unplug camera, unsupported video | TDD | §16.1, p20 | Manual/automated tests | NOT STARTED |
| TDD-38 | Day-1 GPU gate script must print `GATE PASSED` before training/development proceeds | TDD | §14, p19 | `training/verify_gpu.py` | **PARTIALLY COMPLETED** — an equivalent gate was executed successfully (see ENVIRONMENT_SETUP §5), but the script itself has not been created in `training/` |
| TDD-39 | Pin all versions after the gate (`pip freeze`, `.nvmrc`, `package-lock`) and record them | TDD | §14, p19 | Manifests | **COMPLETED** — `backend/requirements.txt` pinned to installed versions, `frontend/package-lock.json` present, `.nvmrc` added |

## 7. Acceptance criteria (PRD §10)

Every AC is `NOT STARTED` because no application code exists. This table exists so that
validation results can be recorded in place during implementation.

| # | Criterion (abridged) | FR link | Status |
| :--- | :--- | :--- | :--- |
| AC-01 | App starts locally from documented steps; active model shown | FR-05, NFR | NOT STARTED |
| AC-02 | Image upload + detection for JPG/JPEG/PNG, download works | FR-01, FR-06 | NOT STARTED |
| AC-03 | Invalid images rejected clearly; app stays usable | FR-01, FR-10 | NOT STARTED |
| AC-04 | Video processing with progress and browser-playable output | FR-02 | NOT STARTED |
| AC-05 | Video failures handled, no partial/temp files | FR-02, FR-09, FR-10 | NOT STARTED |
| AC-06 | Webcam start/annotated frames/FPS/stop + session record | FR-03 | NOT STARTED |
| AC-07 | Camera error cases handled without crashing | FR-03, FR-10 | NOT STARTED |
| AC-08 | Four classes consistent across config, models, backend, DB, frontend | FR-04 | NOT STARTED |
| AC-09 | YOLO26m loads at startup and is shown active | FR-05 | NOT STARTED |
| AC-10 | Tested fallback activates with notice, log and DB record | FR-05 | NOT STARTED |
| AC-11 | Neither model available → clear error, no results | FR-05 | NOT STARTED |
| AC-12 | Confidence threshold configurable and stored per inspection | FR-06 | NOT STARTED |
| AC-13 | Dashboard matches SQLite | FR-07 | NOT STARTED |
| AC-14 | All Table 6 fields saved; survives restart; deleted output handled; delete works | FR-08 | NOT STARTED |
| AC-15 | Outputs viewable/downloadable; same filename twice does not overwrite; temp cleanup | FR-09 | NOT STARTED |
| AC-16 | Dataset record complete; splits disjoint; unlabelled test excluded | §5 | IN PROGRESS — S4-T3B generated a 23,767-image Policy A dataset with 0 duplicate leakage and machine-readable evidence under `dataset/reports/`; final S4-T3C gate pending |
| AC-17 | Metrics computed for both models on held-out test set | §11 | NOT STARTED |
| AC-18 | No data leaves the machine; backend on 127.0.0.1 only | NFR Privacy | NOT STARTED |
| AC-19 | Complete workflow demonstrable; incomplete features stated as incomplete | §1.1 | NOT STARTED |

## 8. Repository gap analysis

### 8.1 Missing relative to TDD v1.1 (must be created during implementation)

| Missing item | TDD reference | Notes |
| :--- | :--- | :--- |
| `backend/app/` (`main.py`, `config.py`, `classes.json`, `schemas.py`, `errors.py`, `api/`, `services/`, `database/`, `utils/`) | §13, p18 | Nothing exists yet; not created in this stage by design |
| `backend/tests/` | §13, §16.1 | pytest installed, no tests |
| `training/` (`verify_gpu`, `inspect_dataset`, `convert_annotations`, `split_dataset`, `smoke_train`, `train`, `evaluate`) | §13, p18 | None exist |
| `frontend/src/{components,pages,services,types}` | §13, p18 | Scaffold has `App.tsx` only |
| `docs/architecture/` | Repo structure, README | Referenced in README, absent |
| Runtime data directories (`uploads_tmp`, `outputs`, `db`) | §13, p18 | Not created; absolute locations undecided (`OPEN_QUESTIONS.md` G-04) |

### 8.2 Unnecessary / conflicting in the current repository

| Item | Problem | Resolution in this stage |
| :--- | :--- | :--- |
| `backend/requirements.txt` listing `sqlalchemy` and `aiosqlite` | TDD §11 specifies the stdlib `sqlite3` module with raw parameterised SQL; an ORM is not part of the design | **Removed** — requirements rewritten to the verified stack |
| `backend/requirements.txt` listing `ffmpeg-python` | TDD §8 uses `imageio-ffmpeg` + `subprocess`, not `ffmpeg-python` | **Removed** |
| `backend/requirements.txt` listing `aiofiles` | TDD handlers are plain `def` (sync) and stream with the stdlib; not required | **Removed** |
| `backend/requirements.txt` `numpy>=1.26,<2.0` | Incompatible with the verified OpenCV 5 / torch 2.11 stack (NumPy 2.x required) | **Replaced** with the verified pinned version |
| `README.md` + `AGENTS.md` stating "NVIDIA CUDA: not available" | Factually wrong: RTX 5060 Laptop GPU, driver 591.84, CUDA 12.8+ wheels work | **Corrected** with measured values |
| `models/weights/` vs TDD §13 `weights/{yolo26m,yolo26n}/` | Two competing locations for checkpoints | Kept `models/weights/` (existing convention + AGENTS.md) and recorded as deviation D-01 |
| `.gitignore` did not cover `dataset/`, `runs/`, runtime outputs, logs | Would allow accidental commits of data, weights and runtime files | **Extended** (and UI assets under `frontend/public` / `frontend/src/assets` explicitly re-included) |

### 8.3 Present and justified

| Item | Justification |
| :--- | :--- |
| `docs/source/*.pdf` | Official sources, preserved unmodified |
| `data/{raw,processed,annotations}` | Matches acquisition → conversion → labels workflow; consistent with TDD §4 |
| `models/{configs,weights}` | Checkpoint + hyperparameter traceability required by AGENTS.md §4 |
| `.venv/` | Isolated environment per AGENTS.md §3 |
| `frontend/` Vite scaffold | TDD §12/§13 frontend stack |

---

## 9. Traceability summary

| Source | Requirement rows | Completed | Partially completed | Blocked | Not started |
| :--- | ---: | ---: | ---: | ---: | ---: |
| Project Proposal | 12 | 0 | 3 | 0 | 9 |
| PRD v1.1 (goals + FR + NFR + limits) | 26 | 0 | 1 | 0 | 25 |
| TDD v1.1 (engineering) | 39 | 1 | 3 | 1 | 34 |
| Acceptance criteria | 19 | 0 | 0 | 0 | 19 |
| **Total** | **96** | **1** | **7** | **1** | **87** |

> These counts describe **implementation** status only. Environment preparation for this
> stage is reported separately in `docs/setup/ENVIRONMENT_SETUP.md` and the Stage 2 report.
