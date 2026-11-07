# ROADVISION AI — STAGE 3.1
## AI/CV Architecture and Repository Inspection (Ram's scope)

**Prepared:** 5 November 2026
**Author role:** AI/CV workstream (Ram)
**Stage:** 3.1 — inspection and decision proposal only. **No implementation.**
**Repository:** `C:\Users\ramsa\Desktop\roadvision ai`
**Git state observed:** one commit `0f977c7` on `master`; all Stage 2 work is still uncommitted.

> **What this document is.** An evidence-based inspection of the repository and the installed
> environment, a mapping of the TDD/PRD onto Ram's responsibilities, a proposed module
> architecture and interface contract, and a recommendation for every open decision.
>
> **What this document is not.** It does not approve any decision, does not implement any
> module, does not contain measured model metrics, and does not claim any dataset or model
> download. Every recommendation below requires Ram's explicit sign-off, and the items that
> touch the backend/DB require Shakib's agreement.

---

## 1. Existing repository structure

### 1.1 Document filenames actually found (the prompt's names differ)

The prompt names documents without paths. The repository uses different locations and, for
some, different names. The mapping was established by reading the actual content, not by
trusting the names:

| Referenced in prompt | Actual file in this workspace | Identity confirmed by | Used |
| :--- | :--- | :--- | :--- |
| `PROJECT_PROPOSAL.md` | `docs/reference/PROJECT_PROPOSAL.md` | PDF metadata: *RoadVision – Intelligent Road Monitoring System: Project Proposal*; source PDF `docs/source/DOC-20261102-WA0017.pdf` | Yes |
| `PRD_v1.1.md` | `docs/reference/PRD_v1.1.md` | PDF metadata: *RoadVision - Product Requirements Document v1.1*; source `DOC-20261102-WA0018.pdf` | Yes |
| `TDD_v1.1.md` | `docs/reference/TDD_v1.1.md` | PDF metadata: *RoadVision - Technical Design Document v1.1*; source `DOC-20261103-WA0001.pdf` | Yes |
| `OPEN_QUESTIONS.md` | `docs/project/OPEN_QUESTIONS.md` | Contains C-01…C-04, Q-01…Q-11, D-01…D-10, A-01…A-09, G-01…G-06 | Yes |
| `REQUIREMENTS_TRACEABILITY.md` | `docs/project/REQUIREMENTS_TRACEABILITY.md` | 96 requirement rows, status vocabulary | Yes |
| `DEPENDENCY_MATRIX.md` | `docs/project/DEPENDENCY_MATRIX.md` | Pinned versions + compatibility chains | Yes |
| `ENVIRONMENT_SETUP.md` | `docs/setup/ENVIRONMENT_SETUP.md` | Verified host + commands | Yes |
| Project Handoff and Implementation Roadmap | **`C:\Users\ramsa\Downloads\RoadVision_Project_Handoff_and_Implementation_Roadmap.docx`** | Content: title *Project Handoff & Implementation Roadmap*, workspace path, Ram/Shakib ownership, Stages 1–8 | Yes |

**Location note.** The handoff document is **outside** the repository. It was found by content
search and has **not** been copied, renamed or moved into the project. If it is to become part
of the repo's governance trail, that is a separate, explicit decision.

**Rejected look-alike.** `C:\Users\ramsa\Downloads\Handoff.pdf` is a 7-page document titled
*VISIONQUEUE — Project Handoff & Execution Summary*. It belongs to a different project and was
**not** used.

**Unmodified originals.** The three PDFs under `docs/source/` keep their WhatsApp names and
their Stage 2 SHA-256 values; nothing in this stage touched them.

### 1.2 Directory tree (files, actual state)

```
roadvision ai/
├── AGENTS.md                          operating rules (corrected in Stage 2)
├── README.md                          project overview (corrected in Stage 2)
├── CHANGELOG.md                       Stage 2 entry present
├── .gitignore                         extended in Stage 2
├── backend/
│   ├── requirements.txt               pinned Python stack (Stage 2)
│   ├── app/
│   │   ├── api/                       EMPTY directory (Shakib's area)
│   │   ├── core/                      EMPTY directory (not in TDD §13)
│   │   ├── models/                    EMPTY directory (not in TDD §13; name collides with model weights)
│   │   ├── services/                  EMPTY directory (shared boundary — see §9)
│   │   └── utils/                     EMPTY directory (Shakib's area)
│   └── tests/                         EMPTY directory
├── frontend/
│   ├── .nvmrc                         "24"
│   ├── package.json / package-lock.json
│   ├── vite.config.ts                 React + Tailwind v4 plugins, /api proxy → 127.0.0.1:8000
│   ├── src/{App.tsx, main.tsx, index.css}
│   ├── src/assets/                    EMPTY directory
│   └── dist/                          previous production build output (committed? see risk R-11)
├── data/
│   ├── raw/.gitkeep
│   ├── processed/.gitkeep
│   └── annotations/.gitkeep           no dataset, no images
├── models/
│   ├── configs/.gitkeep               no training configs yet
│   └── weights/.gitkeep               no checkpoints
├── docs/
│   ├── source/                        3 original PDFs + DOCUMENT_REGISTER.md
│   ├── reference/                     PROJECT_PROPOSAL.md, PRD_v1.1.md, TDD_v1.1.md
│   ├── project/                       OPEN_QUESTIONS, TRACEABILITY, DEPENDENCY_MATRIX, SKILLS_INVENTORY
│   └── setup/                         ENVIRONMENT_SETUP.md
└── (absent) training/                 no scripts at all
```

**Structural observations that matter to Ram:**

| Observation | Consequence |
| :--- | :--- |
| `training/` does not exist | All nine TDD §13 training/eval scripts are missing |
| `backend/app/services/` exists but is empty | The agreed place for the inference core; Ram's package can be added here without touching Shakib's routes |
| `backend/app/{core,models}` exist but are **not** in TDD §13 | Structure already deviates from TDD §13 (`database/` is missing). Ram must not "fix" this; it is Shakib's layout decision |
| `backend/app/models/` shares the name with `models/` (weights) | Import-path ambiguity risk; recommend Ram's code never uses `app.models` |
| `frontend/dist/` is present | Build artifact; its committed/ignored status is a Shakib concern, noted in R-11 |
| No `.env`, no config module, no `classes.json` | `classes.json` is required by TDD Table 3 and does not exist yet |

### 1.3 Ownership boundary used in this report

Taken verbatim from the handoff §6 and the user instruction:

| Workstream | Owner | In scope of this report |
| :--- | :--- | :---: |
| Dataset acquisition, conversion, validation, dedup, splitting | **Ram** | Yes |
| YOLO26m / YOLO26n training, fine-tuning, evaluation | **Ram** | Yes |
| CV inference core for image / video / webcam, model loading, GPU management, fallback | **Ram** | Yes |
| AI/CV tests and documentation; Python inference interface to Shakib | **Ram** | Yes |
| React frontend, dashboard, FastAPI routes, SQLite, video/webcam job orchestration | **Shakib** | **No — read-only inspection only** |

No file owned by Shakib was opened for modification, and no route, DB or frontend file will be
proposed for Ram to edit.

---

## 2. Verified environment status

### 2.1 What was re-checked in this stage

Read-only only. **Nothing was installed, upgraded, removed or downloaded.** The `.venv` was not
modified.

| Item | Observed value | Evidence |
| :--- | :--- | :--- |
| Python | 3.11.9 | interpreter of `.venv` |
| torch | 2.11.0+cu128 | `importlib.metadata` |
| torchvision | 0.26.0+cu128 | `importlib.metadata` |
| ultralytics | 8.4.202 | `importlib.metadata` |
| opencv-python | 5.0.0.93 | `importlib.metadata` |
| numpy | 2.4.6 | `importlib.metadata` |
| scikit-learn | 1.9.1 | `importlib.metadata` |
| fastapi | 0.162.0 | `importlib.metadata` |
| imageio-ffmpeg | 0.8.1 | `importlib.metadata` |
| pytest | 9.2.0 | `importlib.metadata` |
| CUDA available | `True` | `torch.cuda.is_available()` |
| torch CUDA runtime | 12.8 | `torch.version.cuda` |
| GPU capability | `(12, 0)` | `torch.cuda.get_device_capability(0)` |
| `sm_120` kernels | present | `'sm_120' in torch.cuda.get_arch_list()` |

These match Stage 2's `DEPENDENCY_MATRIX.md` and `ENVIRONMENT_SETUP.md`. **No drift was found.**

### 2.2 What was deliberately not re-verified

Per the no-repeat rule, the following Stage 2 results are accepted as reported and were **not**
re-executed: the CUDA matmul gate, the YOLO26n yaml forward pass, the FastAPI health route, the
OpenCV round-trip, the FFmpeg `libx264` check and `npm run build`. They are documented in
`docs/setup/ENVIRONMENT_SETUP.md` §6.

### 2.3 One environment fact that changes the TDD's model code

This is the most important discovery of Stage 3.1, obtained by **reading the installed
Ultralytics source**, not by running a model:

| Finding | Evidence in `ultralytics 8.4.202` |
| :--- | :--- |
| `end2end` is a **deprecated** predict/val/train keyword that is translated onto `nms` | `ultralytics/cfg/__init__.py` L604–610: `custom["nms"] = False if end2end else ...` + `deprecation_warn("end2end=…", "nms=…")` |
| `nms` semantics | `ultralytics/cfg/default.yaml` L61: `None: external NMS (default); True: embed NMS on export; False: NMS-free head if available` |
| The end-to-end switch is applied to the model head | `engine/predictor.py` L475: `end2end=self.args.nms is False`; `nn/backends/pytorch.py` L57–58: override applied only when not `None` |
| YOLO26 is architecturally dual-head (one-to-many + one-to-one) | `cfg/models/26/yolo26.yaml` L9 `end2end: True`; `nn/modules/head.py` L155–167, L195–204 |
| With end-to-end on, NMS is skipped | `utils/nms.py` L71: `if prediction.shape[-1] == 6 or end2end:` |
| Offline mode exists | `utils/__init__.py` L1128: `if env_bool("YOLO_OFFLINE")`; `SETTINGS["sync"]` default `True` (sends analytics only if `sentry_sdk` is installed) |

**Consequence.** The TDD's `NMS_ARGS = {}` (end-to-end) / `{"end2end": False, "iou": 0.7}`
(traditional) cannot be copied literally:

- `NMS_ARGS = {"end2end": False, "iou": 0.7}` would emit a deprecation warning and map to
  `nms=None` → **external NMS**, which is what the TDD calls the traditional path. The *intent*
  survives, the *mechanism* is legacy.
- To get true end-to-end (the TDD's preferred mode), the supported switch is **`nms=False`**,
  not `end2end=True`.
- The model must receive the same `nms` value in **train, val and predict**, otherwise training
  validation and application inference can use different head branches.

This is recorded as **N-02** in §10.4 and must be confirmed by a one-image runtime probe before
training (see §12).

---

## 3. Existing versus missing AI/CV components

**Verdict: zero of Ram's AI/CV components exist.** The repository contains an installed
environment and a frontend shell, not a CV pipeline.

| # | Component (TDD/PRD ref) | Required by | State | Evidence |
| :-: | :--- | :--- | :--- | :--- |
| 1 | Dataset acquisition + integrity | TDD §4.1 p7 | **MISSING** | `data/` only `.gitkeep` |
| 2 | `inspect_dataset.py` | TDD §4.2 p7 | **MISSING** | no `training/` |
| 3 | `convert_annotations.py` (VOC→YOLO) | TDD §4.3 p7–8 | **MISSING** | no `training/` |
| 4 | Dedup + group-aware split | TDD §4.4 p8–9 | **MISSING** | no `training/` |
| 5 | `data.yaml` generator | TDD §4.5 p9 | **MISSING** | no `dataset/` |
| 6 | Training subset policy | TDD §4.6 p9 | **MISSING** | no code |
| 7 | `verify_gpu.py` gate | TDD §14 p18 | **MISSING** | only inline commands in the setup doc |
| 8 | `smoke_train.py` | TDD §5.2 p10 | **MISSING** | no `training/` |
| 9 | `train.py` (m and n) | TDD §5 p9–10 | **MISSING** | no `training/` |
| 10 | `evaluate.py` | TDD §16 p20 | **MISSING** | no `training/` |
| 11 | Trained weights (m, n) | TDD §3.1–3.2 p5 | **MISSING** | `models/weights/` only `.gitkeep` |
| 12 | `classes.json` (single source of truth) | TDD Table 3 p7; PRD AC-08 | **MISSING** | not in `backend/app/` |
| 13 | Model manager (load, class check, warm-up, F1–F5) | TDD §3.3 p5–6 | **MISSING** | `backend/app/services/` empty |
| 14 | Shared inference result schema | TDD §6 p11 | **MISSING** | `schemas.py` absent |
| 15 | Image inference engine | TDD §7 p11 | **MISSING** | — |
| 16 | Video inference engine + H.264 writer | TDD §8 p11–12 | **MISSING** | — |
| 17 | Webcam capture engine (DirectShow/MJPEG) | TDD §9 p13 | **MISSING** | — |
| 18 | Annotator (boxes/labels/conf) | TDD §7–9 | **MISSING** | — |
| 19 | Class-consistency checker across five layers | PRD AC-08 p12 | **MISSING** | — |
| 20 | AI/CV unit tests | TDD §16.1 p20 | **MISSING** | `backend/tests/` empty |
| 21 | Vision settings/config | TDD §13 p18 | **MISSING** | no `config.py` |
| 22 | Dataset record (PRD Table 7) | PRD §5.3 p9 | **MISSING** | no record |
| — | FastAPI routes / SQLite / job slot / frontend pages | Shakib | **MISSING (not Ram's)** | only empty dirs + shell |

### 3.1 Requirements that belong to Ram

| Requirement | Source | Ram's deliverable |
| :--- | :--- | :--- |
| FR-04 + AC-08 class order and automated consistency | PRD §4.4 p5, AC-08 p12 | `classes.json`, `vision/classes.py`, `training/verify_classes.py` |
| FR-05 + F1–F5 model selection and fallback | PRD §4.5 p5–6; TDD §3.3 p5–6 | `model_manager.py`, `models_used` tracking |
| FR-06 detection payload (boxes, conf, class counts, model) | PRD §4.6 p6–7; TDD §6 p11 | `types.py::to_result` equivalent |
| FR-02 video core (frames, annotation, H.264 stream) | PRD §4.2 p4–5; TDD §8 p11–12 | `video_engine.py`, `media.py` |
| FR-03 webcam core (capture, FPS, annotated frames) | PRD §4.3 p5; TDD §9 p13 | `webcam_engine.py` |
| Dataset completeness, splits, leakage (AC-16) | PRD §5.3 p9–10; TDD §4 | `training/` scripts + dataset record |
| Evaluation metrics (AC-17) | PRD §11 p13; TDD §16 p20 | `training/evaluate.py` + JSON reports |
| GPU gate and honest performance measurement | TDD §14 p18, §16 p20 | `training/verify_gpu.py`, benchmark scripts |
| AI/CV test suite | TDD §16.1 p20 | `backend/tests/vision/` |

---

## 4. Ram's complete implementation architecture

### 4.1 Pipeline (offline side)

```
RDD2022 archive (figshare DOI)
   │  acquire: size/MD5 vs listing, zipfile.testzip(), short-path extraction
   ▼
IMMUTABLE RAW  C:\rv\data\raw\            (never modified)
   │  inspect_dataset.py → counts, per-country, class distribution,
   │                        missing annotations, unreadable, dimensions, exact dups
   ▼
CONVERTED      C:\rv\data\converted\      (images untouched; labels written separately)
   │  convert_annotations.py: VOC XML → YOLO normalised; D00/D10/D20/D40 only;
   │  clip tolerance, exclusion counters, conversion report
   ▼
GROUPED        exact-hash + dHash(Hamming ≤ 3) union-find groups
   │  split_dataset.py: StratifiedGroupKFold(10) → 80/10/10, seed recorded
   ▼
FROZEN SPLITS  dataset/{images,labels}/{train,val,test} + data.yaml + split lists
   │  assert_disjoint(): no hash and no group crosses a split
   ▼
TRAINING       verify_gpu.py → smoke_train.py → train.py (n pilot, m main)
   │  checkpoint + confidence selection on VALIDATION only
   ▼
FROZEN MODELS  models/weights/yolo26n.pt, models/weights/yolo26m.pt
   │  evaluate.py: ONE pass on the test split
   ▼
EVIDENCE       models/eval/*.json, models/runs/**, docs reports
```

### 4.2 Serving pipeline (Ram's core inside Shakib's app)

```
Shakib: FastAPI route / job worker / camera route
            │  (owns HTTP, DB, job slot, progress, cancel, output naming)
            ▼
   VisionService  ──────────────────────────────── RAM-OWNED
     ├── startup():  load m → class check → warm-up → else n → else unavailable
     ├── predict_image(bgr, conf)      → DetectionResult + annotated frame   [F3]
     ├── predict_frame(bgr, conf)      → DetectionResult                     [F3]
     ├── render(bgr, result)           → annotated BGR
     ├── open_video(src, out, conf, on_progress, cancel) → VideoSession      [F4 support]
     ├── open_camera(index, conf)      → CameraSession                       [F5]
     ├── status()                      → ModelStatus (for /api/model/status)
     └── models_used                   → append-only provenance for the DB
            │
            ▼
   model_manager (single lock, one model active, CUDA → CPU fallback)
            │
            ▼
   YOLO26m.pt / YOLO26n.pt  on RTX 5060 (device 0), CPU only as last resort
```

### 4.3 Non-negotiable design rules

1. **One forward pass at a time.** A single process-wide `threading.Lock` serialises all
   inference (TDD §3.3). Consequence: Shakib must not call `VisionService` from `async def`
   without a thread hop — see §9.
2. **No silent fallback.** Every switch is logged with a reason and appended to `models_used`
   (PRD FR-05; fixes C-01).
3. **Classification of failure.** Low confidence or zero detections are **results**, never
   failures (TDD §3.3 p6).
4. **Raw data is immutable.** Conversion always writes to a new directory (TDD §4.1 p7).
5. **Splits are frozen before training** and never regenerated (PRD §5.3 p9).
6. **Test set is touched once**, after all selection is complete (PRD §11 p13).
7. **No external calls during inference.** Enforce `YOLO_OFFLINE=1` and `settings sync=False`
   for the serving process (AC-18).
8. **Measure, never assume.** Every number in a report comes from a recorded run.

---

## 5. Proposed Python module and directory structure

### 5.1 Directory layout (Ram-owned files in bold)

```
roadvision ai/
├── backend/
│   ├── app/
│   │   ├── services/
│   │   │   └── vision/                     ← RAM (new package)
│   │   │       ├── __init__.py             public surface (the only import Shakib uses)
│   │   │       ├── config.py               VisionSettings: paths, imgsz, nms mode, device, conf defaults
│   │   │       ├── classes.py              load/validate classes.json; index↔code↔label
│   │   │       ├── device.py               resolve_device(), gpu_report(), empty_cache_if_needed()
│   │   │       ├── types.py                Detection, DetectionResult, ModelStatus, outcomes, summaries
│   │   │       ├── errors.py               VisionError hierarchy (no FastAPI imports)
│   │   │       ├── model_manager.py        load/class-check/warm-up, lock, F1–F3, F5 switch, models_used
│   │   │       ├── annotate.py             draw boxes/labels, colour map, JPEG encode
│   │   │       ├── image_engine.py         validate→infer→render→outcome
│   │   │       ├── video_engine.py         frame iteration, progress, cancel, F4-friendly summary
│   │   │       ├── webcam_engine.py        DirectShow capture thread, rolling FPS, latest JPEG
│   │   │       ├── media.py                H.264 writer (imageio-ffmpeg), fps/frame metadata
│   │   │       ├── summary.py              class-count aggregation, frames_processed / with_detections
│   │   │       └── service.py              VisionService facade
│   │   ├── classes.json                    ← RAM authors content; Shakib reads it (shared)
│   │   ├── api/ …                          Shakib (not touched)
│   │   ├── core/ …                         Shakib (not touched)
│   │   ├── models/ …                       Shakib (name collision; Ram avoids `app.models`)
│   │   └── utils/ …                        Shakib (not touched)
│   └── tests/
│       └── vision/                         ← RAM (new)
│           ├── test_classes.py
│           ├── test_model_manager.py
│           ├── test_result_schema.py
│           ├── test_image_engine.py
│           ├── test_video_engine.py
│           ├── test_webcam_logic.py        fake capture, no hardware
│           └── test_cleanup.py
├── training/                                ← RAM (new, all files)
│   ├── verify_gpu.py                        Day-1 gate + nms-mode probe
│   ├── inspect_dataset.py
│   ├── convert_annotations.py
│   ├── split_dataset.py
│   ├── verify_classes.py                    five-layer class consistency (AC-08)
│   ├── smoke_train.py
│   ├── train.py
│   ├── evaluate.py
│   ├── dataset_report.py                    PRD Table 7 record generation
│   └── configs/
│       ├── train_yolo26n.yaml
│       └── train_yolo26m.yaml
├── models/
│   ├── configs/                             frozen training configs + resolved args
│   ├── weights/                             yolo26m.pt, yolo26n.pt (best checkpoints)
│   ├── runs/                                Ultralytics train/val outputs (git-ignored)
│   └── eval/                                evaluate.py JSON + plots
└── data/
    └── reports/                             dataset reports/manifests (small, committable)
```

**Dataset bytes themselves stay outside the repo** at `C:\rv\data\…` (short path, TDD §4.1 p7,
Windows MAX_PATH). Only small JSON/Markdown reports land in `data/reports/`.

### 5.2 Module responsibilities and import rules

| Module | Responsibility | Must NOT do |
| :--- | :--- | :--- |
| `config.py` | Single place for vision constants; reads env overrides | Import FastAPI/SQLite |
| `classes.py` | Validate `classes.json` = `["D00","D10","D20","D40"]`, indices 0–3 | Hard-code a second list |
| `device.py` | `cuda if available else cpu`; report name/VRAM/capability | Assume CUDA |
| `model_manager.py` | Loading, class check, warm-up, lock, fallback, `models_used` | Know about HTTP/DB/inspections |
| `annotate.py` | Draw boxes + `D00 0.87` labels; BGR/JPEG | Download fonts from the internet |
| `image_engine.py` | One image → result + annotated array | Write files or DB rows |
| `video_engine.py` | Decode → infer → write H.264 → summary; honour cancel | Own job slot, status polling or DB |
| `webcam_engine.py` | Capture thread, FPS, latest annotated JPEG | Own routes or MJPEG response |
| `media.py` | Even-padding, `libx264`, `+faststart`, fps metadata | Decide the output filename (Shakib does) |
| `summary.py` | Aggregate counts, frames processed/with detections | Persist anything |
| `service.py` | Facade + lifecycle + status | Import Shakib's modules |

**Dependency rule:** `backend/app/services/vision/**` imports only stdlib + numpy + cv2 +
torch + ultralytics. Shakib's layer imports `vision`; `vision` never imports Shakib's layer.
This keeps the boundary testable and prevents circular ownership.

### 5.3 Public surface (what Shakib may import)

```python
# backend/app/services/vision/__init__.py
from .service import VisionService
from .types import (
    Detection, DetectionResult, ModelStatus,
    ImageOutcome, FrameOutcome, VideoSummary, CameraSummary, VideoProgress,
)
from .errors import (
    VisionError, ModelUnavailable, InferenceError,
    VideoDecodeError, VideoEncodeError, CameraUnavailable,
)

__all__ = [
    "VisionService",
    "Detection", "DetectionResult", "ModelStatus",
    "ImageOutcome", "FrameOutcome", "VideoSummary", "CameraSummary", "VideoProgress",
    "VisionError", "ModelUnavailable", "InferenceError",
    "VideoDecodeError", "VideoEncodeError", "CameraUnavailable",
]
```

---

## 6. Dataset engineering plan

### 6.1 Acquisition (Stage 4, Task 1–2)

| Step | Action | Gate |
| :--- | :--- | :--- |
| A1 | Confirm source: `https://doi.org/10.6084/m9.figshare.21431547.v1` (TDD Table 2 p7) and its licence/usage terms | Recorded in the dataset record |
| A2 | Check free space for archive + extracted + converted copies (TDD §4.1 p7) | ≥ 3× archive size free |
| A3 | Download the archive(s); compare **size and MD5** against the figshare file listing | Every file matches |
| A4 | `zipfile.testzip()` on each archive | No corrupt member |
| A5 | Extract to `C:\rv\data\raw\` (short path) | Extraction succeeds; path length OK |
| A6 | Record file counts before/after; compute SHA-256 of each archive | Manifest written |
| A7 | Never modify the raw tree | Read-only by convention |

**No figure is quoted for image count.** The "47,420 images" number is not in any ratified
document and was not verified (Q-08). Counts come from `inspect_dataset.py` output.

### 6.2 Inspection (`inspect_dataset.py`)

Outputs a JSON + Markdown report containing:

- per-country/source folder: images, XML files, images without XML, XML without image;
- class distribution overall and per country (raw codes before filtering);
- codes outside `D00/D10/D20/D40` (counted, not remapped);
- unreadable images and malformed XML (with paths);
- image dimension histogram (to reason about 640 vs 960 training size);
- exact duplicate counts by SHA-256;
- labelled vs unlabelled pools (official test images separated).

Acceptance: the report is reproducible from the raw tree and every count is traceable.

### 6.3 Conversion (`convert_annotations.py`)

Implements TDD §4.3 p7–8 exactly:

- fixed map `{D00:0, D10:1, D20:2, D40:3}` loaded from `classes.json`;
- true image size read with OpenCV; XML size mismatch **logged, not trusted**;
- swapped `xmin/xmax`, `ymin/ymax` corrected;
- boxes within `TOL_PX = 2.0` outside the image are clipped and counted;
- larger overruns, non-numeric, zero-area, unsupported class → excluded and counted **by reason**;
- one `.txt` per image, `class cx cy w h` normalised to 6 decimals;
- conversion report (JSON + Markdown) with every counter;
- unit test compares the formula to hand-computed boxes;
- visual spot-check of ≥ 20 converted images across classes and countries.

### 6.4 Deduplication and grouping

- exact duplicates: SHA-256 of file bytes;
- near duplicates: 64-bit dHash (`resize 9×8`, horizontal gradient), union-find with
  Hamming ≤ 3 and pigeonhole bucketing (TDD §4.4 p8);
- `MAX_BUCKET = 2000` guard against pathological buckets (blank images), skipped buckets logged;
- **before freezing**, inspect the group-size distribution. If unrelated road images merge,
  lower Hamming to 2 and record the change (Q-04).

### 6.5 Splitting (`split_dataset.py`)

- `StratifiedGroupKFold(n_splits=10, shuffle=True, random_state=SEED)` → fold 0 = test,
  fold 1 = val, rest = train (≈80/10/10);
- stratify by the **rarest class present in each image**;
- freeze `train.txt`, `val.txt`, `test.txt` + `split_manifest.json` (seed, ratio, thresholds,
  per-class counts per split, source file hashes);
- `assert_disjoint()` fails the build if any group or hash spans two splits;
- generate `data.yaml` with an **absolute** path (TDD §4.5 p9);
- background policy (Q-03) applied here and recorded.

### 6.6 Dataset record (PRD Table 7)

`dataset_report.py` fills every row: downloaded, usable annotations, exclusions by reason,
split counts, class distribution per split, subset size + method, seed + split-file location,
leakage-check result. No row may remain "to be recorded" at the end of Stage 4.

### 6.7 Commands (target)

```powershell
.\.venv\Scripts\python.exe training\inspect_dataset.py --raw C:\rv\data\raw --out data\reports\inspect
.\.venv\Scripts\python.exe training\convert_annotations.py --raw C:\rv\data\raw --out C:\rv\data\converted --report data\reports\convert
.\.venv\Scripts\python.exe training\split_dataset.py --converted C:\rv\data\converted --out C:\rv\data\dataset --seed 42 --ratio 0.8 0.1 0.1
.\.venv\Scripts\python.exe training\verify_classes.py --data C:\rv\data\dataset\data.yaml
```

All scripts must be idempotent or refuse to overwrite a frozen split unless `--force` is given.

---

## 7. YOLO26m / YOLO26n training plan

### 7.1 Order of work (TDD §5 p9–10, §5.2 p10)

| Stage | Work | Gate |
| :-: | :--- | :--- |
| 0 | `verify_gpu.py` + NMS-mode probe | prints `GATE PASSED` |
| 1 | Data smoke test: ~200 converted images, **YOLO26n**, 1 epoch | training batch plots show correct boxes/classes |
| 2 | Memory ladder for **YOLO26m**: 2 epochs @640, batch 16 → 8 → 4 | peak VRAM recorded; largest stable batch chosen |
| 3 | Pilot: ~10 % of the intended train subset, few epochs | seconds/image/epoch `t` measured; metric trend sane |
| 4 | Main run YOLO26m (+ YOLO26n if not already final), checkpoints every epoch, resume enabled | completes within budget |
| 5 | Checkpoint + confidence selection on **validation** | no test-set use |
| 6 | Single **test** evaluation of both | AC-17 numbers |

### 7.2 Settings chosen by measurement (not fixed here)

| Setting | Starting point (explicitly **not** a recommendation of a final value) | How it is fixed |
| :--- | :--- | :--- |
| `imgsz` | 640 | Stage 2 memory ladder; raise to 960/1280 only if thin-crack recall demands and VRAM allows |
| `batch` | 16 → 8 → 4 ladder | largest stable value from Stage 2 |
| `epochs` | derived from the time budget | `N = (B×3600)/(t×E)` (TDD §5.2 p10) |
| `workers` | 2 | Windows + 16 GB RAM constraint (TDD §5.1 p10) |
| `cache` | False | 16 GB RAM |
| `amp` | True (default) | verify no NaN; disable if unstable |
| `seed` | 42 | recorded; deterministic where feasible |
| `patience` | 20 (proposal) | early stop on val fitness; recorded |
| `device` | 0 (int) | A-03; never a hard-coded string |
| `nms` | `False` for end-to-end (Q-02) | recorded in every run config |

### 7.3 Artifacts and provenance

- `models/weights/yolo26m.pt`, `models/weights/yolo26n.pt` (best checkpoints, copied from runs);
- `models/configs/train_yolo26{m,n}.yaml` (resolved args, versions, git hash);
- `models/runs/<model>_<timestamp>/` (Ultralytics outputs, `results.csv`, plots);
- `models/eval/<model>_test.json` (evaluate.py output);
- a run log line per run: torch/ultralytics/CUDA/driver versions, dataset manifest hash,
  seed, peak VRAM, wall time.

### 7.4 Operating threshold and reporting

- Sweep `conf` from 0.10 to 0.90 **on validation**, choose the operating threshold, record it.
- Report **both** Ultralytics' summary P/R (its own best-F1 point) **and** P/R at the chosen
  operating threshold; label which is which (TDD §16 p20 warns they differ).
- Report mAP@0.5 and mAP@0.5:0.95 overall **and per class** (PRD §11 p13); per-class results are
  mandatory because RDD2022 is imbalanced.
- `iou` is only meaningful in NMS mode; if end-to-end is used, record `iou_threshold = null`
  and say so.

### 7.5 Guardrails

- `if __name__ == "__main__":` in every script (Windows spawn).
- Application stopped during training; laptop plugged in; temperature watched (TDD §5.1 p10).
- No test-set inspection, no test-set-driven tuning.
- No claim of accuracy from unlabelled data.
- If YOLO26m cannot meet the memory/rare-class gate, reduce image size → batch → subset, and
  only as a last resort change the primary model — recorded as a PRD deviation (TDD §5.2 p10).

---

## 8. Inference engine design

### 8.1 Public API (the contract Ram hands to Shakib)

```python
class VisionService:
    def __init__(self, settings: VisionSettings | None = None) -> None: ...

    # lifecycle
    def startup(self) -> ModelStatus: ...      # idempotent; F1/F2
    def shutdown(self) -> None: ...            # release models/GPU
    def status(self) -> ModelStatus: ...       # safe to call any time

    # single image / single frame
    def predict_image(self, bgr: np.ndarray, conf: float) -> ImageOutcome: ...   # F3 applied
    def predict_frame(self, bgr: np.ndarray, conf: float) -> FrameOutcome: ...   # no file I/O
    def render(self, bgr: np.ndarray, outcome: FrameOutcome) -> np.ndarray: ...  # annotated BGR

    # streams
    def open_video(
        self, src: Path, out_path: Path, conf: float,
        on_progress: Callable[[VideoProgress], None] | None = None,
        cancel: threading.Event | None = None,
    ) -> VideoSession: ...
    def open_camera(self, index: int, conf: float) -> CameraSession: ...

    # fallback control (F4 is orchestrated by Shakib)
    def force_fallback(self, reason: str) -> bool: ...

    @property
    def models_used(self) -> tuple[str, ...]: ...   # e.g. ("YOLO26m", "YOLO26n")
```

### 8.2 Data contracts (exactly TDD §6 p11)

```python
@dataclass(frozen=True)
class Detection:
    class_id: int              # 0..3
    class_name: str            # "D00" | "D10" | "D20" | "D40"
    confidence: float          # 0..1, rounded to 4 dp
    box: tuple[float, float, float, float]   # x1, y1, x2, y2 in ORIGINAL image pixels

@dataclass(frozen=True)
class DetectionResult:
    model: str
    total_detections: int
    class_counts: dict[str, int]   # always all four keys, zeros included
    detections: list[Detection]

    def as_dict(self) -> dict: ... # exact JSON keys: model, total_detections, class_counts, detections

@dataclass(frozen=True)
class ModelStatus:
    active_model: str | None
    available: bool
    fallback_active: bool
    fallback_reason: str | None
    models_used: tuple[str, ...]
    device: str                # "cuda:0" | "cpu"
    nms_mode: str              # "end2end" | "nms"
    iou_threshold: float | None
    imgsz: int
```

Stream outcomes:

```python
@dataclass
class ImageOutcome:
    result: DetectionResult
    annotated_bgr: np.ndarray      # same H×W as input
    width: int
    height: int

@dataclass
class FrameOutcome:
    result: DetectionResult
    # annotated frame is produced by render() to keep this cheap

@dataclass
class VideoProgress:
    frames_processed: int
    frames_total: int | None
    frames_with_detections: int
    class_counts: dict[str, int]
    fps: float

@dataclass
class VideoSummary:
    status: str                    # "completed" | "failed" | "cancelled"
    error: str | None
    frames_processed: int
    frames_total: int | None
    frames_with_detections: int
    class_counts: dict[str, int]
    models_used: tuple[str, ...]
    model: str | None              # exactly ONE model per output video
    output_written: bool

@dataclass
class CameraSummary:
    status: str                    # "completed" | "failed" | "cancelled"
    error: str | None
    frames_processed: int
    frames_with_detections: int
    class_counts: dict[str, int]
    models_used: tuple[str, ...]
    average_fps: float
```

### 8.3 Fallback state machine

| State | Entered by | Behaviour |
| :--- | :--- | :--- |
| `PRIMARY` | YOLO26m loads + class check + warm-up OK | normal |
| `FALLBACK` | F1/F2 at startup, or F3/F5 at runtime | YOLO26n active; `fallback_active=True`; reason string kept |
| `UNAVAILABLE` | both models failed | `predict_*` raises `ModelUnavailable`; Shakib returns 503 |

Transitions:

| Trigger | Where implemented | Effect |
| :--- | :--- | :--- |
| F1 missing/corrupt YOLO26m | `model_manager.startup()` | log, try n, append `YOLO26n` |
| F2 warm-up/class-check failure | `model_manager.startup()` | same |
| F3 image runtime error (incl. OOM) | `predict_image` | retry once on m → `force_fallback` → retry on n |
| F4 video job error | **Shakib's worker** | Ram returns failed `VideoSummary`; Shakib calls `force_fallback` and restarts once from the beginning on n |
| F5 sustained low live FPS | `CameraSession` | rolling FPS below `MIN_LIVE_FPS` for `F5_DWELL_S` → switch once, notice flag |
| F6 manual selection | optional | not implemented unless Q-07 says yes |

`models_used` is **append-only** and never reset (this is the C-01 fix). Ram exposes the tuple;
Shakib stores it as `"YOLO26m,YOLO26n"`.

### 8.4 Threading and resource rules

- one `threading.Lock` around every `model.predict`;
- `torch.inference_mode()` for inference;
- `torch.cuda.empty_cache()` only after an OOM retry, never per frame;
- video: release `VideoCapture` and kill FFmpeg in `finally`; delete partial output on
  failure/cancel (Shakib decides the path, Ram guarantees cleanup of its handles);
- webcam: capture thread is daemon; `stop()` sets an event and joins with timeout; release
  camera in `finally`; publish only the latest JPEG (no unbounded queue);
- never hold a reference to caller frames after returning.

### 8.5 Error taxonomy (mapped by Shakib, not imported by Ram)

| Exception | `code` | Suggested HTTP (Shakib decides) |
| :--- | :--- | :--- |
| `ModelUnavailable` | `model_unavailable` | 503 |
| `InferenceError` | `inference_failed` | 500 |
| `VideoDecodeError` | `video_decode_failed` | 415/422 |
| `VideoEncodeError` | `video_encode_failed` | 500 |
| `CameraUnavailable` | `camera_unavailable` | 503 |
| `VisionError` (base) | `vision_error` | 500 |

### 8.6 Confidence and mode handling

- `conf` is validated by Shakib at the API boundary (0.10–0.90) and **re-clamped** in Ram's
  engine as defence in depth;
- `nms_mode` is a single process-wide setting (`"end2end"` recommended) applied identically to
  both models, training validation and inference (TDD §3.4 p6);
- `iou_threshold` only in `"nms"` mode;
- the value actually used is returned in `ModelStatus` so Shakib can store it per inspection.

### 8.7 Offline enforcement (AC-18)

For the serving process:

```powershell
$env:YOLO_OFFLINE = "1"
```

plus a one-time `settings.update({"sync": False})` in the app's environment (or the equivalent
CLI setting) so Ultralytics does not attempt analytics/update traffic. Verify empirically with
a network monitor during one image inference before claiming AC-18.

### 8.8 Performance measurement (definitions fixed now, values later)

| Measure | Method |
| :--- | :--- |
| Image inference time | ≥ 20 runs after warm-up; report median and mean; model-only and end-to-end separately |
| Video FPS | frames processed ÷ wall-clock, for a stated clip (resolution, length, fps) |
| Live FPS | rolling average over a stated session; report per model |
| VRAM | `torch.cuda.max_memory_allocated()` / `max_memory_reserved()` |
| CPU fallback | same measurements on `device="cpu"`, clearly labelled |

---

## 9. Shakib integration interface requirements

### 9.1 Contract items

| ID | Contract | Ram provides | Shakib provides | Agreement needed |
| :-- | :--- | :--- | :--- | :--- |
| I-01 | Package boundary | `backend/app/services/vision/**` public API | imports only from `vision` | Directory + import path |
| I-02 | Lifecycle | `VisionService.startup()` / `shutdown()`, idempotent | call in FastAPI lifespan; call `status()` for health | Startup order with `init_db` |
| I-03 | Readiness | `status().available` | 503 when `False`; never call predict when unavailable | Error shape |
| I-04 | Result payload | `DetectionResult.as_dict()` exact TDD §6 keys | embed unchanged in API/DB JSON | Field names/types |
| I-05 | Threading | all calls are **blocking** | call from `def` handlers or `run_in_threadpool`/worker threads; never `await` directly | Concurrency rule |
| I-06 | Inference lock | serialises forwards | one image at a time; video/webcam share the lock per frame | Timeout/queue behaviour |
| I-07 | Error mapping | exception classes + `code` | map to the single API error shape | codes ↔ HTTP |
| I-08 | Image flow | `predict_image` → `ImageOutcome` | validate upload, create inspection, save annotated output, delete temp | who encodes/saves |
| I-09 | Video flow | `open_video(src, out_path, conf, on_progress, cancel)` | validate, job slot, inspection, progress throttling, cancel, output naming, F4 restart | `out_path` ownership |
| I-10 | Video F4 restart | failed `VideoSummary` + `force_fallback` | keep `src` until terminal status; restart once on n | **must not delete upload before restart** (N-04) |
| I-11 | Webcam flow | `open_camera` + `latest_jpeg()` + `fps` | start/stop routes, job slot, MJPEG response, session record | who encodes JPEG (proposed: Ram) |
| I-12 | Model provenance | `models_used` tuple | store as comma-joined string in `models_used` | max length/format |
| I-13 | Settings | `status().nms_mode`, `iou_threshold`, `imgsz`, `device` | store `nms_mode`/`iou_threshold` per inspection | DB columns already exist |
| I-14 | Class list | `classes.json` + `classes.py` | backend constants/DB + frontend labels derive from it | single source of truth |
| I-15 | Output naming | Ram writes to the path it is given | generate unique name, resolve under output dir | path traversal safety |
| I-16 | Shutdown | `shutdown()` releases CUDA/camera | call on app shutdown | ordering |
| I-17 | Test doubles | fake session classes for API tests | use them instead of real GPU/camera | test strategy |

### 9.2 Image sequence

```
Shakib route (def)
  ├─ stream upload → temp file; Pillow/OpenCV validate; limits; inspection row (processing)
  ├─ image = cv2.imread(temp)                      # Shakib's validation already decoded it
  ├─ outcome = vision.predict_image(image, conf)   # Ram: F3 inside
  ├─ out_name = new_output_name("jpg")             # Shakib owns naming (FR-09)
  ├─ cv2.imwrite(OUTPUT_DIR/out_name, outcome.annotated_bgr)
  ├─ update inspection: counts, models_used, conf, nms_mode, output, status=completed
  └─ return DetectionResult + output URL
```

Ram does **not** create the inspection, write the DB, or name the output.

### 9.3 Video sequence (and F4)

```
Shakib worker
  ├─ validate + save upload (src) ; inspection queued ; acquire job slot
  ├─ session = vision.open_video(src, out_path, conf, on_progress, slot.cancel)
  ├─ summary = session.run()          # blocking; Ram writes H.264, reports progress
  ├─ if summary.status == "failed" and fallback not yet used:
  │      vision.force_fallback(summary.error)
  │      summary = vision.open_video(src, out_path2, conf, ...).run()   # restart from beginning
  ├─ finally: delete src ONLY after the final attempt; delete partial output if not completed
  └─ persist status, counts, models_used, frames_processed/with_detections, output name
```

The TDD §8 skeleton deletes `src` in `finally`, which would make the F4 restart impossible.
That is recorded as **N-04**; Shakib must retain the upload until the terminal outcome.

### 9.4 Webcam sequence

```
Shakib route
  ├─ acquire slot ; create inspection(processing) ; session = vision.open_camera(index, conf)
  ├─ session.start()                  # Ram: DirectShow thread, F5 inside
  ├─ GET /api/camera/stream → StreamingResponse of session.latest_jpeg()
  ├─ POST /api/camera/stop → summary = session.stop() ; persist aggregated record
  └─ finally: release slot; camera always released by Ram
```

F5 switching happens inside `CameraSession`; Shakib reads `vision.status()` for the notice.

### 9.5 Non-negotiable interface statements

1. Ram will not import FastAPI, SQLite or `app.config` from Shakib's layer.
2. Shakib will not call `model.predict` directly, load YOLO, or manage CUDA.
3. `DetectionResult` keys are frozen by TDD §6; changes require both owners.
4. `models_used` is append-only; a reset is a defect (C-01).
5. One model per output video (TDD §3.3 F4).
6. `conf` and `nms_mode` stored with every inspection (PRD Table 6; TDD §11).
7. All vision calls are blocking; the event loop must not be blocked.

---

## 10. Unresolved decisions and recommended resolutions

**No decision below is approved.** "Recommended" means Ram's technical recommendation; the
approval column says who must sign it off. Items that change the DB/API also need Shakib.

### 10.1 Team questions Q-01 … Q-11

| ID | Question | Recommended resolution | Evidence / reasoning | Approve |
| :-- | :--- | :--- | :--- | :--- |
| **Q-01** | Operating limits | **Adopt the documented values as provisional, configurable defaults** — image 20 MB / 8192 px; video 200 MB / 60 s / 1920×1080 / 10 min; webcam 10 min; min live FPS 5; 1 job. Do **not** mark as ratified until measured on real clips. | PRD §4.11 p8–9 explicitly says recommended and re-check after throughput measurement. No video has been processed yet. | Ram + Shakib |
| **Q-02** | End-to-end vs NMS | **End-to-end for both models, as the initial default**, implemented via `nms=False` (not the deprecated `end2end=`). Keep it switchable by one constant; record `nms_mode` in every inspection and evaluation. Revert to `nms=None` only if the probe or metrics show a problem. | TDD §3.4 p6 recommends default end-to-end; `yolo26.yaml` L9 `end2end: True`; API semantics in §2.3. **Subject to the runtime probe (A-01).** | Ram |
| **Q-03** | Annotation-free images as background | **Yes, but bounded**: use only images with zero kept-class boxes after conversion; include them in all splits in natural proportion; cap a recorded maximum; report the count. | AC-02 requires a "no damage" image to behave correctly; background examples reduce false positives. No document fixes a ratio, so it must be recorded. | Ram |
| **Q-04** | dHash threshold + split ratio | **Hamming ≤ 3, 64-bit; 80/10/10; seed 42.** Inspect the group-size histogram before freezing; if unrelated images merge, drop to 2 and record the change. | TDD §4.4 p8 skeleton + PRD §5.3 p9. Threshold is explicitly "small" and must be recorded, not assumed. | Ram |
| **Q-05** | Min live FPS + watchdog | **5 FPS, 10 s dwell, 10 s watchdog as provisional constants.** F5 counts only *sustained* degradation over a rolling window, never a single slow frame. | PRD §4.11 p9; TDD §3.3 F5 p5, §9 p13. No live session has been measured. | Ram + Shakib |
| **Q-06** | Image lists vs copied folders | **Copied folders.** Revisit only under disk pressure. | TDD Appendix C p22 lists txt-list support as unverified (A-04); 426 GB free; copied folders are the lower-risk default. | Ram |
| **Q-07** | Optional features | **Defer F6, FP16, ONNX, ByteTrack.** Consider FP16/`quantize=16` only after VRAM/latency measurements; keep ONNX/ByteTrack out of core scope. | TDD Appendix B p22 marks them optional/out of core scope. `half` is also deprecated in 8.4.202 in favour of `quantize`. | Ram |
| **Q-08** | Dataset size claims | **Quote no total until measured.** Fill PRD Table 7 from `inspect_dataset.py`; record archive hashes and per-country counts. | TDD Appendix C p22 lists size/class distribution as unverified. | Ram |
| **Q-09** | Upload retention | **Delete uploads after terminal processing** (success or final failure), with a single config flag. Raw dataset is never treated as an upload. | PRD §4.9 p7 recommended; privacy/disk. | Shakib (Ram consumes) |
| **Q-10** | Training subset size + seed | **Decide only after inspection**: freeze val/test on the full labelled pool, subsample train only, keep every rare-class image, size via `N = (B×3600)/(t×E)`. Record seed 42 unless a reason to change. | PRD §5.1 p9; TDD §4.6 p9, §5.2 p10. Cannot be decided before counts exist. | Ram |
| **Q-11** | Backend binding | **127.0.0.1 only**, per NFR. Any demo-time exception must be documented before opening the port. | PRD §6 p10, AC-18 p12. | Shakib |

### 10.2 Document conflicts C-01 … C-04

| ID | Recommendation | Where the fix lives | Approve |
| :-- | :--- | :--- | :--- |
| **C-01** | **Follow the PRD.** Keep `models_used` append-only: `switch_to_fallback()` must record the previous model before adding the new one, so a switch yields `("YOLO26m","YOLO26n")`. Never re-initialise the list in `startup()`. | Ram (`model_manager.py`) + Shakib (DB string) | Ram + Shakib |
| **C-02** | **Do not add a new status value.** On watchdog `stream closed`, set `status="failed"` with `error="stream closed (no consumer)"`; on explicit stop, `status="cancelled"`. Keep the PRD/TDD enum unchanged. | Ram (session outcome) + Shakib (persist) | Ram + Shakib |
| **C-03** | **Implement the precondition** in the upload/job path: `shutil.disk_usage(OUTPUT_DIR).free >= 2 × input_size`, reject with a clear message before starting. | **Shakib** (upload validation); Ram does not own this | Shakib |
| **C-04** | **Implement an automated five-layer check**: model names (both checkpoints), `classes.json`, backend constants/DB, dataset `data.yaml`, frontend label map. Ram writes `training/verify_classes.py`; Shakib exposes a stable frontend labels source. | Ram + Shakib | Ram + Shakib |

### 10.3 Stage 2 deviations D-01 … D-10

| ID | Recommendation | Reason |
| :-- | :--- | :--- |
| **D-01** | **Accept** `models/weights/`; standardise filenames to `yolo26m.pt` / `yolo26n.pt` (no per-model subfolders). | TDD §13 p18 says `weights/{yolo26m,yolo26n}/`; the repo convention is `models/weights/`. Record and update all references. |
| **D-02** | **Accept** stdlib `sqlite3` (no ORM). | TDD §11 p16 uses raw SQL; Ram's layer does not touch the DB at all. |
| **D-03** | **Accept** `imageio-ffmpeg` + `subprocess`. | TDD §8 p11–12 calls that binary. |
| **D-04** | **Accept** no `aiofiles`. | TDD §10.2 p14 uses blocking chunked I/O in `def` handlers. |
| **D-05** | **Accept** NumPy 2.x. | Verified imports work with torch 2.11 / OpenCV 5. |
| **D-06** | **Accept** `opencv-python`. | Matches Ultralytics' declared dependency; avoids duplicate `cv2`. |
| **D-07** | **Accept** torch 2.11.0+cu128. | Verified `sm_120` at runtime. |
| **D-08** | **Accept for now** (Shakib's call), verify build remains reproducible. | Outside Ram's boundary. |
| **D-09** | **Accept**: PyMuPDF is not a runtime dependency. | It is absent from `requirements.txt`; nothing to remove. |
| **D-10** | **Accept** backend capture (DirectShow → MJPEG). | TDD §9 p13 explicitly decides Option B. Ram implements the capture core. |

### 10.4 New items discovered in Stage 3.1 (not in the Stage 2 numbering)

| ID | Type | Finding | Recommendation | Approve |
| :-- | :--- | :--- | :--- | :--- |
| **N-01** | Decision | `config.py` would mix Ram's vision settings with Shakib's app settings | Put vision constants in `backend/app/services/vision/config.py`; Shakib's `config.py` may import `CLASS_CODES`/`MODEL_PATHS` from it so there is still one effective source | Ram + Shakib |
| **N-02** | Deviation | TDD's `NMS_ARGS` uses the deprecated `end2end`/`iou` form; 8.4.202 uses `nms` | Represent the mode as `VISION_NMS_MODE="end2end" | "nms"` and pass `nms=False` or nothing; never pass `end2end=` in new code | Ram |
| **N-03** | Deviation | TDD writes runs to `runs/`, `runs_smoke/`, `eval/`; AGENTS §4 wants provenance under `models/` | Use `models/runs/` and `models/eval/`; keep `.gitignore` covering them | Ram |
| **N-04** | Gap | F4 requires a restart from the beginning, but TDD §8 deletes the upload in `finally` | Keep the upload until the terminal outcome; restart once on YOLO26n before cleanup | Ram + Shakib |
| **N-05** | Decision | Windows path length + repo size | Dataset bytes live at `C:\rv\data\{raw,converted,dataset}`; only small reports go in `data/reports/` | Ram |
| **N-06** | Decision | AC-18 requires no external calls during inference | Serving process sets `YOLO_OFFLINE=1` and disables Ultralytics settings sync; verify with a network monitor | Shakib + Ram |
| **N-07** | Decision | Annotation rendering source | Start with `res.plot()` (TDD §9 p13); if colours/labels are unsuitable, replace with `annotate.py` using `res.boxes` only. Verify BGR order (A-02). | Ram |

### 10.5 Assumptions A-01 … A-09 (verification plan)

| ID | Assumption | Status in this stage | Verification | When |
| :-- | :--- | :--- | :--- | :--- |
| **A-01** | `NMS_ARGS`/`end2end` accepted by Ultralytics | **Source-read, not executed.** `end2end` is deprecated→`nms`; `nms=False` is the supported end-to-end switch | One image with `nms=False` vs default; compare detection counts, warnings, and `models_used`/`nms_mode` | Stage 4 Task 1 (probe) |
| **A-02** | `res.plot()` returns BGR ndarray | Unverified | Encode to JPEG, inspect colour order, shape equals input | First image engine test |
| **A-03** | `device=DEVICE` string selects GPU | Partially verified in Stage 2 (`device=0` int worked) | Print resolved device in `status()`; assert `cuda:0` when available | `device.py` unit test |
| **A-04** | Ultralytics accepts `.txt` image lists | Unverified | Only if Q-06 changes; 4-image list + 1-epoch smoke | Deferred |
| **A-05** | Served MP4 seeks in browser | Unverified | Chrome seek test on a real output | First video integration |
| **A-06** | YOLO26 available in installed build | **Verified (Stage 2 smoke)** | — | Done |
| **A-07** | OpenCV 5 behaves like 4.x for capture/encode | Partially verified (encode/decode, mp4v writer) | Real clip decode + DirectShow open | First video/webcam test |
| **A-08** | `starlette.testclient` + httpx 0.28.1 | Verified with deprecation warning | Decide httpx2 at test-suite time | Shakib's test setup |
| **A-09** | YOLO26m fits 8 GB VRAM | Unverified | `verify_gpu.py`, then memory ladder batch 16/8/4 | Training Stage 2 |

---

## 11. Risks and technical compatibility concerns

| ID | Risk | Severity | Evidence | Mitigation |
| :-- | :--- | :-- | :--- | :--- |
| **R-01** | End-to-end/NMS API mismatch between TDD code and installed Ultralytics | **High** | `end2end` deprecated; `nms` semantics inverted vs TDD | N-02; probe in Stage 4 Task 1; single constant used by train/val/predict |
| **R-02** | Training and inference use different head branches | **High** | `nms` is applied per call, not stored in the checkpoint | Persist `nms` in every run config; assert in evaluation; store `nms_mode` per inspection |
| **R-03** | F4 restart impossible if the upload is deleted early | **High** | TDD §8 `src.unlink()` in `finally` | N-04: retain until terminal outcome |
| **R-04** | YOLO26m may not fit 8 GB at a usable batch | **High** | 7.96 GiB visible; no measurement yet | Memory ladder; reduce imgsz/batch/subset; last resort change primary model (recorded) |
| **R-05** | Thin cracks vanish at 640 px, hurting D00/D10 recall | **Medium–High** | RDD2022 crack geometry; TDD §5.2 p10 warns explicitly | Compare 640 vs 960 on validation; report per-class mAP, not only overall |
| **R-06** | Class imbalance hides a weak class | **High** | PRD §11 p13 requires per-class reporting | Per-class P/R/mAP; keep all rare-class images in the training subset |
| **R-07** | RDD2022 test-set annotation availability is unknown | **Medium** | TDD assumes unlabelled official test images are excluded | Inspection step decides; we build our own frozen test split from the labelled pool |
| **R-08** | dHash over-merges unrelated road images | **Medium** | TDD §4.4 warns; threshold is a guess | Inspect group-size distribution before freezing; fall back to Hamming 2 |
| **R-09** | DirectShow camera open fails or wrong index | **Medium** | A-07 untested | Enumerate indices 0–3 at startup probe; clear `camera_unavailable` |
| **R-10** | OpenCV 5.0 API differences vs TDD's 4.x assumptions | **Medium** | Major-version bump | Pin 5.0.0.93; empirical tests for each cv2 call used |
| **R-11** | Stage 2 work is uncommitted; `frontend/dist/` present | **Medium** | `git status` shows all Stage 2 files untracked/modified | Commit before Stage 4 (separate, explicit action; not done here) |
| **R-12** | Ultralytics may make external calls during inference | **Medium** | `settings["sync"]` defaults True; `YOLO_OFFLINE` exists | N-06; network-monitor verification for AC-18 |
| **R-13** | Windows MAX_PATH during dataset conversion | **Medium** | TDD §4.1 p7 | Short root `C:\rv\...`; no deep nesting |
| **R-14** | Ultralytics AGPL-3.0 implications for distributing weights | **Low–Medium** | TDD §18 p21 | Academic use; document licence in the report; no redistribution without review |
| **R-15** | Duplicate/ambiguous module names (`app.models`, `app.core`) cause import confusion | **Low–Medium** | Empty dirs not in TDD §13 | Ram never imports `app.models`; use `app.services.vision` only |
| **R-16** | Ultralytics may auto-install optional packages at runtime | **Low** | Observed package layout includes optional backends | No tracking/ByteTrack; pin environment; fail loudly rather than auto-install |

---

## 12. Exact next implementation task

> **Task S4-T1 — Create and run the Day-1 GPU gate with an NMS-mode compatibility probe.**
> This is the only task to start after this report is approved. It closes A-01/A-03, confirms
> Q-02's mechanism, and satisfies TDD §14 p18 before any dataset work.

### Deliverable

`training/verify_gpu.py` (new file, Ram-owned), implementing:

1. Python / torch / torchvision / CUDA runtime / driver printout.
2. `torch.cuda.is_available()` assertion.
3. Capability check: `(12, 0)` and `sm_120` (or `compute_120`) in `torch.cuda.get_arch_list()`.
4. Real matmul on `cuda`, `torch.isfinite(...).all()`, `torch.cuda.synchronize()`.
5. VRAM total, allocated/reserved after the matmul.
6. `device` resolution check (`int 0` vs string) — prints the resolved device.
7. **NMS-mode probe** (no training, one blank/known image):
   - run `predict(..., nms=False)` → end-to-end branch;
   - run `predict(...)` with default args → external-NMS branch;
   - print detection counts, timing, and whether a deprecation warning appeared;
   - assert the call does not crash and returns a `Results` object with `.boxes`.
8. `YOLO_OFFLINE` notice and `settings["sync"]` value printout.
9. Final line `GATE PASSED` only if all assertions pass; non-zero exit otherwise.

### Model source for the probe

Two allowed modes, chosen explicitly:

- `--yaml` (default for this task): `YOLO("yolo26n.yaml")` — **no download**, random weights.
  Proves API acceptance and shapes only.
- `--weights`: `YOLO("yolo26n.pt")` — requires an approved weight download; proves real
  end-to-end behaviour. **Do not run without explicit approval.**

### Commands

```powershell
cd "C:\Users\ramsa\Desktop\roadvision ai"
.\.venv\Scripts\python.exe training\verify_gpu.py --yaml
```

### Definition of done

- Script exists, is runnable, and prints `GATE PASSED` with `--yaml`.
- Output is pasted verbatim into the Stage 4 report (no paraphrasing).
- `nms_mode` semantics are recorded: which keyword was used, what warning appeared, and what
  the team will standardise on (N-02/Q-02).
- If the probe fails, **stop**: do not start dataset acquisition until the mode is resolved,
  because training configuration depends on it.

### Explicitly out of scope for S4-T1

- No dataset download, no weight download (unless `--weights` is approved), no training.
- No changes to `backend/`, `frontend/`, routes, DB or Shakib's modules.
- No commits or pushes.

---

## Appendix A — Evidence log (read-only commands executed)

| Command (abridged) | Observed |
| :--- | :--- |
| `Get-ChildItem -Recurse -File` (excluding `.venv`, `node_modules`, `.git`) | File tree in §1.2; `training/` absent; `data/`, `models/` only `.gitkeep` |
| Directory enumeration of `backend/` | `app/{api,core,models,services,utils}` and `tests/` exist, all empty |
| `importlib.metadata.version(...)` for 9 packages | Values in §2.1 |
| `torch.cuda.is_available()` / `version.cuda` / `get_device_capability(0)` / `get_arch_list()` | `True` / `12.8` / `(12, 0)` / `sm_120` present |
| `git status --short`, `git log --oneline -3` | One commit `0f977c7`; Stage 2 changes uncommitted |
| Read `ultralytics/cfg/__init__.py` L575–624 | `end2end` → `nms` deprecation mapping |
| Read `ultralytics/cfg/default.yaml` L55–61 | `nms` semantics; `iou: 0.7`; `conf` defaults |
| Read `ultralytics/engine/predictor.py` L340–350, L465–476 | `end2end=self.args.nms is False`; head override |
| Read `ultralytics/nn/backends/pytorch.py` L31–77 | overrides `model.end2end` when not `None` |
| Read `ultralytics/nn/modules/head.py` L155–204 | dual-head; branch selected by `_end2end` |
| Read `ultralytics/utils/nms.py` L26–71 | NMS skipped when `end2end` |
| Read `ultralytics/cfg/models/26/yolo26.yaml` L1–52 | `end2end: True`, scales n/m parameters |
| Read `ultralytics/utils/__init__.py` L1122–1128, L1674 | `YOLO_OFFLINE`, `sync` default |
| `pymupdf` first page of `Downloads\Handoff.pdf` | *VISIONQUEUE* — different project, rejected |
| DOCX text extraction of the RoadVision handoff | 275 paragraphs; ownership/roadmap in §1.3 |

No model was loaded, no dataset was touched, no dependency was changed, and no file outside
this report was written.

## Appendix B — Ram requirement → TDD/PRD trace (condensed)

| Ram work item | TDD | PRD |
| :--- | :--- | :--- |
| Acquisition + integrity | §4.1 p7 | §5.1–5.2 p9 |
| Inspection | §4.2 p7 | §5.2 p9 |
| VOC→YOLO conversion | §4.3 p7–8 | §5.2 p9 |
| Dedup + splitting | §4.4 p8–9 | §5.3 p9–10 |
| Dataset YAML + subsets | §4.5–4.6 p9 | §5.1 p9 |
| GPU gate + smoke + training | §5, §5.1–5.2 p9–10, §14 p18 | §6 p10 |
| Evaluation | §16 p20 | §10 AC-17 p12, §11 p13 |
| Class consistency | §3.3 p5 | §4.4 p5, AC-08 p12 |
| Model manager + fallback | §3.1–3.4 p5–6 | §4.5 p5–6 |
| Result payload | §6 p11 | §4.6 p6–7 |
| Image inference | §7 p11 | §4.1 p4 |
| Video inference core | §8 p11–12 | §4.2 p4–5 |
| Webcam capture core | §9 p13 | §4.3 p5 |
| Offline/privacy | §15 p19 | §6 p10, AC-18 p12 |
| Tests | §16.1 p20 | AC-01…AC-19 p12 |

## Appendix C — Recommended module checklist (for Stage 4 planning, not created)

```
[ ] backend/app/classes.json
[ ] backend/app/services/vision/{__init__,config,classes,device,types,errors}.py
[ ] backend/app/services/vision/{model_manager,annotate,image_engine}.py
[ ] backend/app/services/vision/{video_engine,webcam_engine,media,summary,service}.py
[ ] backend/tests/vision/{test_classes,test_model_manager,test_result_schema}.py
[ ] backend/tests/vision/{test_image_engine,test_video_engine,test_webcam_logic,test_cleanup}.py
[ ] training/{verify_gpu,inspect_dataset,convert_annotations,split_dataset}.py
[ ] training/{verify_classes,smoke_train,train,evaluate,dataset_report}.py
[ ] training/configs/{train_yolo26n,train_yolo26m}.yaml
[ ] data/reports/ (dataset + conversion + split reports)
[ ] models/{configs,weights,runs,eval}/ (populated, git-ignored where appropriate)
```

---

**END OF STAGE 3.1 REPORT. Implementation has not started.**
