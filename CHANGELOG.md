# Changelog

All notable changes to the RoadVision AI project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.0-stage2] - 2026-11-05

**Stage 2: document ingestion, environment installation and independent verification.**
No product feature, dataset download or model training was started.

### Added
- **Document register**: `docs/source/DOCUMENT_REGISTER.md` — SHA-256, PDF metadata, page counts,
  extraction status and the binding authority order.
- **Reference copies**: `docs/reference/PROJECT_PROPOSAL.md`, `docs/reference/PRD_v1.1.md`,
  `docs/reference/TDD_v1.1.md` — full text, tables and code listings extracted from the PDFs.
  The original PDFs under `docs/source/` are unmodified.
- **Governance records**:
  - `docs/project/REQUIREMENTS_TRACEABILITY.md` — 96 rows mapping FR/AC/F1–F6 and the
    un-numbered document requirements to source sections and implementation status.
  - `docs/project/OPEN_QUESTIONS.md` — 4 document conflicts (C-01…C-04), 11 team decisions
    (Q-01…Q-11), 10 recorded deviations (D-01…D-10), 9 unproven assumptions (A-01…A-09) and
    6 gaps (G-01…G-06).
  - `docs/project/DEPENDENCY_MATRIX.md` — pinned versions, compatibility chains, exclusions.
- **Frontend scaffold**: Vite 8 + React 19 + TypeScript 7 + Tailwind CSS 4 via `@tailwindcss/vite`,
  `react-router-dom` 7, `/api` proxy to `127.0.0.1:8000`, `frontend/.nvmrc` (`24`).
- **`.gitignore`** entries for runtime outputs (`data/outputs/`, `data/tmp/`, `logs/`), dataset
  extraction (`dataset/`, `runs/`, `training/runs/`) and UI-asset exceptions.

### Changed
- **`backend/requirements.txt` rewritten and pinned** (`==` for every direct dependency) with
  `--extra-index-url https://download.pytorch.org/whl/cu128`.
  - Added: `torch==2.11.0+cu128`, `torchvision==0.26.0+cu128`, `opencv-python==5.0.0.93`,
    `numpy==2.4.6`, `imageio-ffmpeg==0.8.1`, `scikit-learn==1.9.1`, `pillow==13.0.0`,
    `httpx==0.28.1`, `pytest-cov==7.1.0`.
  - Removed: `sqlalchemy`, `aiosqlite` (TDD §11 uses stdlib `sqlite3`), `ffmpeg-python`
    (TDD §8 uses `imageio-ffmpeg`), `aiofiles`, `pytest-asyncio`, and the `numpy<2` cap
    (incompatible with torch 2.11 / OpenCV 5).
- **`README.md`, `AGENTS.md` §2, `docs/setup/ENVIRONMENT_SETUP.md`** corrected: the machine has an
  NVIDIA RTX 5060 Laptop GPU and CUDA works. The previous "no NVIDIA GPU / CPU-only" claims were
  wrong.
- **`docs/project/SKILLS_INVENTORY.md`** replaced with a verified audit of the skills and plugins
  actually present on disk, including the two marketplace catalogs (18 official + 51 partner
  plugins) and the finding that none covers PyTorch, Ultralytics, OpenCV, FastAPI or FFmpeg.

### Verified (executed, output observed)
- Hardware: RTX 5060 Laptop GPU 8151 MiB, driver 591.84, compute capability (12, 0); Ryzen 9 270;
  15.3 GB usable RAM; 426.06 GB free on C:.
- `torch 2.11.0+cu128`, `torch.version.cuda == "12.8"`, `torch.cuda.is_available() == True`,
  `'sm_120'` present in `torch.cuda.get_arch_list()`, real 2048×2048 matmul finite on device 0.
- VRAM visible to PyTorch: 7.96 GiB.
- CPU fallback path: YOLO forward pass succeeded on `device='cpu'`.
- YOLO26n architecture: `YOLO('yolo26n.yaml')` built and ran on GPU (~20.4 ms per forward pass on
  a blank 640 px image — **smoke test only, not a benchmark**). No weights were downloaded.
- OpenCV 5.0.0.93 encode/decode round-trip; `mp4v` `VideoWriter` write.
- FFmpeg 9.0 with `libx264`; `imageio-ffmpeg` binary path resolves.
- FastAPI `TestClient`: `GET /api/health` → 200 (with a Starlette/httpx deprecation warning).
- `npm run build`: TypeScript project build + Vite production bundle, CSS 8.92 kB, JS 220.57 kB.
- `pip install --dry-run --no-deps -r backend/requirements.txt`: all requirements satisfied.

### Corrections to earlier records
- The `0.1.0-init` entry below states "confirmed absence of NVIDIA GPU/CUDA". That verification was
  wrong. It is retained as history and superseded by the measurements above.
- The `0.1.0-init` free-space figure (443.58 GB) is stale; the value measured in this stage is
  426.06 GB.

### Not done (deliberately)
- No application code (`backend/app/`, `backend/tests/`, `training/`), no product pages, no SQLite
  database.
- No dataset download, no weight download, no training, no evaluation, no inference benchmark.

---

## [0.1.0-init] - 2026-11-04

### Added
- **Project Structure**: Established modular directory layout for `backend/`, `frontend/`, `data/`, `models/`, and `docs/`.
- **Governance**: Added `AGENTS.md` specifying document hierarchy (TDD v1.1 > PRD v1.1 > Proposal), hardware execution constraints, and coding rules.
- **Documentation**:
  - `README.md`: System overview, hardware specifications, and project layout.
  - `docs/project/SKILLS_INVENTORY.md`: Catalog of active skills (`managing-python-dependencies`, `ml-best-practices`, `modern-web-guidance`, etc.) and marketplace safety evaluation.
  - `docs/setup/ENVIRONMENT_SETUP.md`: Step-by-step verified environment setup guide.
- **Dependency Manifests**: Initialized `backend/requirements.txt` with compatible baseline specifications for Python 3.11 and CPU inference.
- **Configuration**: Added `.gitignore` configured for Python environments, Node modules, large video datasets, and model weight binaries.

### Verified
- **Software**: Git 2.53.0, Python 3.11.9, Node.js v24.19.0, npm 11.16.0, FFmpeg 9.0.
- **Hardware**: Verified AMD Radeon 780M Graphics / AMD CPU architecture; confirmed absence of NVIDIA GPU/CUDA (`nvidia-smi` / `nvcc` absent); set PyTorch default target to CPU inference.
- **Disk Space**: 443.58 GB available on primary storage (C:).

