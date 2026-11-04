# Changelog

All notable changes to the RoadVision AI project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
