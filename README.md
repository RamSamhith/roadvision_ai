# RoadVision AI

A locally hosted road-condition screening system: four road-damage classes detected with
YOLO26, served by a FastAPI backend and a React dashboard. Images, recorded videos and a live
webcam are all processed on the project laptop — **no cloud service is used at any point**.

> **This is a preliminary, assistive screening tool.** It is an academic B.Tech CSE (AI & ML)
> mini project and is **not** an engineering-grade road assessment instrument. Results must not
> be used for structural or safety decisions.

---

## Project status

| Item | State |
| :--- | :--- |
| Stage | **Stage 2 complete** — documents ratified, environment installed and verified |
| Application code | **Not started** — `backend/app/`, `backend/tests/`, `training/` and the product pages do not exist |
| Dataset | **Not downloaded** — `data/` holds `.gitkeep` only |
| Model weights | **Not downloaded or trained** — `models/weights/` holds `.gitkeep` only |
| Documents | Project Proposal, PRD v1.1 and TDD v1.1 ingested and registered |

Nothing below claims a working feature. The environment is installed and proven; the product is not.

---

## Source of truth

1. **TDD v1.1** — architecture, schemas, API contracts, model parameters, pipelines.
2. **PRD v1.1** — features, behaviour, acceptance criteria, operating limits.
3. **Project Proposal** — objectives, scope, academic context.

| Document | Reference copy | Identity |
| :--- | :--- | :--- |
| Project Proposal (no version stated) | [`docs/reference/PROJECT_PROPOSAL.md`](docs/reference/PROJECT_PROPOSAL.md) | `docs/source/DOC-20261102-WA0017.pdf` |
| PRD v1.1 | [`docs/reference/PRD_v1.1.md`](docs/reference/PRD_v1.1.md) | `docs/source/DOC-20261102-WA0018.pdf` |
| TDD v1.1 | [`docs/reference/TDD_v1.1.md`](docs/reference/TDD_v1.1.md) | `docs/source/DOC-20261103-WA0001.pdf` |

Original PDFs are unmodified; SHA-256 and metadata are recorded in
[`docs/source/DOCUMENT_REGISTER.md`](docs/source/DOCUMENT_REGISTER.md).

Governance records:

- [`docs/project/REQUIREMENTS_TRACEABILITY.md`](docs/project/REQUIREMENTS_TRACEABILITY.md) — every
  FR/AC mapped to a source section and an implementation status.
- [`docs/project/OPEN_QUESTIONS.md`](docs/project/OPEN_QUESTIONS.md) — conflicts, questions the
  documents defer to the team, recorded deviations and unproven assumptions.
- [`docs/project/DEPENDENCY_MATRIX.md`](docs/project/DEPENDENCY_MATRIX.md) — pinned versions and
  why this combination is compatible.
- [`docs/project/SKILLS_INVENTORY.md`](docs/project/SKILLS_INVENTORY.md) — what agent guidance
  exists, what is missing, what was rejected.

---

## Verified environment

Measured on the project laptop on 2026-11-05:

| Component | Verified value |
| :--- | :--- |
| OS | Windows 11, 64-bit |
| CPU | AMD Ryzen 9 270 (8C / 16T) |
| GPU | **NVIDIA GeForce RTX 5060 Laptop GPU**, 8151 MiB, compute capability **(12, 0)** |
| GPU driver | 591.84 |
| CUDA Toolkit | **Not installed — not required** (the PyTorch wheel bundles its runtime) |
| PyTorch | **2.11.0+cu128** (CUDA 12.8); `sm_120` present; real GPU matmul verified |
| Python | 3.11.9 |
| Node.js / npm | 24.19.0 / 11.16.0 |
| FFmpeg | 9.0-full_build with `libx264` |
| Git | 2.53.0 |
| Free disk (C:) | 426.06 GB |

> An earlier version of this README stated that no NVIDIA GPU or CUDA was available. That was
> incorrect and has been corrected. CPU execution is still supported as a fallback and is tested,
> but the RTX 5060 is the primary inference target.

---

## Quick start

Prerequisites: Python 3.11, Node.js 24, FFmpeg, and an up-to-date NVIDIA driver. Full instructions,
including every verification command and its expected output, are in
[`docs/setup/ENVIRONMENT_SETUP.md`](docs/setup/ENVIRONMENT_SETUP.md).

```powershell
# Backend
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe -c "import torch; assert torch.cuda.is_available(); print(torch.__version__)"

# Frontend
cd frontend
npm install
npm run dev
```

Once `backend/app/main.py` exists, run the API from the repository root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

The Vite dev server proxies `/api` to `http://127.0.0.1:8000` (see `frontend/vite.config.ts`).
Binding to `127.0.0.1` is a requirement (PRD v1.1 §6, AC-18), not a convenience.

---

## Intended behaviour (from the ratified documents)

| Area | Requirement |
| :--- | :--- |
| Classes | `0 = D00`, `1 = D10`, `2 = D20`, `3 = D40` — identical in model, backend, database and UI (PRD FR-04) |
| Models | YOLO26m primary; trained YOLO26n fallback; fallback is never silent and is recorded (PRD FR-05, F1–F5) |
| Inputs | Image upload, recorded video, live webcam (PRD FR-01, FR-02, FR-03) |
| Video output | Browser-playable H.264 MP4 (PRD FR-02; TDD §8) |
| Storage | Local SQLite, records only, no large blobs (PRD FR-08; TDD §11) |
| Privacy | Local processing, `127.0.0.1` only, no external calls during inference (PRD §6) |

Operating limits (image 20 MB / 8192 px, video 200 MB / 60 s / 1080p, webcam 10 min, 1 job at a
time) are **recommended values awaiting team approval** — see `OPEN_QUESTIONS.md` Q-01.

---

## Repository layout

```
roadvision ai/
├── AGENTS.md                       # Operating rules for agents and developers
├── backend/
│   └── requirements.txt            # Pinned Python dependencies (cu128 index included)
├── frontend/                       # Vite + React 19 + TypeScript + Tailwind 4 scaffold
│   ├── .nvmrc                      # Node 24
│   └── vite.config.ts              # Tailwind plugin + /api proxy
├── data/                           # Datasets and runtime outputs (git-ignored)
├── models/
│   ├── configs/                    # Training configuration YAML
│   └── weights/                    # Checkpoints (git-ignored)
└── docs/
    ├── source/                     # Original PDFs + DOCUMENT_REGISTER.md
    ├── reference/                  # Markdown extraction of the three documents
    ├── project/                    # Traceability, open questions, dependencies, skills
    └── setup/                      # ENVIRONMENT_SETUP.md
```

`backend/app/`, `backend/tests/`, `training/` and `frontend/src/{pages,services,types}` are
**planned but absent**. `models/configs/` and `data/*` currently contain `.gitkeep` files only.

---

## Known deviations from the TDD

These are recorded, not hidden (details and rationale in `OPEN_QUESTIONS.md` §5):

| ID | Deviation |
| :--- | :--- |
| D-01 | Weights live in `models/weights/` instead of the TDD's root-level `weights/` |
| D-02 | SQLite is accessed through the standard-library `sqlite3` module — no SQLAlchemy |
| D-03 | Video encoding uses `imageio-ffmpeg` + `subprocess` — no `ffmpeg-python` |
| D-06 | `opencv-python`, not `opencv-python-headless` (matches Ultralytics' dependency) |

---

## License / attribution

Dataset: RDD2022 (figshare DOI `10.6084/m9.figshare.21431547.v1`). Ultralytics YOLO is
AGPL-3.0 for open-source use; the licensing implications are noted in TDD v1.1 §18 and must be
re-checked before any distribution of the trained weights.
