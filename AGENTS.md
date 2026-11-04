# RoadVision AI - Agent Guidelines & Operating Rules

This document governs the engineering standards, decision hierarchy, and execution protocols for all AI agents and developers working on the RoadVision AI repository.

---

## 1. Document Hierarchy & Source of Truth

When making architectural, technical, or design decisions, adhere strictly to the following authority ranking:
1. **Technical Design Document (TDD v1.1)**: Primary technical authority for system architecture, schemas, API contracts, model parameters, and processing pipelines.
2. **Product Requirements Document (PRD v1.1)**: Authority for user stories, functional scope, acceptance criteria, and UX workflows.
3. **Project Proposal**: Reference for high-level project vision, problem context, and roadmap milestones.

> [!IMPORTANT]
> **No Hallucinated Requirements**: Never invent missing requirements, APIs, data formats, or architectural choices. If a technical requirement is not specified in TDD v1.1 or PRD v1.1, explicitly flag the gap and seek confirmation before proceeding.

---

## 2. Hardware Environment & Execution Constraints

The verified host development environment consists of:
- **CPU**: AMD Ryzen processor (Windows 11)
- **GPU**: AMD Radeon 780M Graphics (Integrated GPU)
- **NVIDIA GPU / CUDA**: **NOT PRESENT**. `nvidia-smi` and `nvcc` are unavailable.
- **Python**: 3.11.9
- **Node.js**: v24.19.0 / npm 11.16.0
- **FFmpeg**: v9.0-full_build (Installed and active in system PATH)

### Hardware Execution Directives
- **Device Placement**: Do **NOT** hardcode `device='cuda'` or `torch.cuda.is_available()` assumptions into training or inference scripts. Always use dynamic device resolution:
  ```python
  import torch
  device = "cuda" if torch.cuda.is_available() else "cpu"
  ```
- **Local Execution**: On this machine, PyTorch and Ultralytics YOLO run on **CPU** by default. Ensure test batches and verification runs use lightweight configurations (small image sizes, small batch sizes) to prevent thermal throttling or excessive CPU contention.

---

## 3. Python & Dependency Management Directives

Adhere strictly to the [`managing-python-dependencies`](file:///C:/Users/ramsa/.gemini/config/skills/managing-python-dependencies/SKILL.md) skill:
1. **Never Global**: **NEVER** run `pip install` globally. All Python libraries must be installed inside an isolated virtual environment (`.venv`).
2. **Explicit Paths**: Always execute commands using the virtual environment interpreter:
   - Windows PowerShell: `.venv\Scripts\python.exe` and `.venv\Scripts\pip.exe`
3. **Manifest Integrity**: Keep `backend/requirements.txt` strictly pinned and updated using pip freeze / exported locks.
4. **No Premature Massive Downloads**: Do not download full datasets or pre-trained multi-gigabyte models without explicit confirmation.

---

## 4. Machine Learning & Computer Vision Governance

Adhere strictly to the [`ml-best-practices`](file:///C:/Users/ramsa/.gemini/config/skills/ml-best-practices/SKILL.md) skill:
- **Data Integrity**: Never fit scalers, imputers, or transforms across data splits; always split before processing to prevent data leakage.
- **Split Validation**: Maintain strict separation between training, validation, and test subsets.
- **Metrics Standard**: Report full evaluation matrices including mAP@50, mAP@50-95, precision, recall, and inference latency per frame.
- **Traceability**: Log all training runs, hyperparameter choices, and model weights under `models/configs` and `models/weights`.

---

## 5. Frontend & UI Engineering Directives

Adhere strictly to the [`modern-web-guidance`](file:///C:/Users/ramsa/.gemini/config/plugins/modern-web-guidance-plugin/skills/modern-web-guidance/SKILL.md) skill:
- **Stack**: React 18+, TypeScript, Vite, Tailwind CSS.
- **Standards**: Execute `npx -y modern-web-guidance@latest search "<query>"` before implementing UI patterns (dialogs, video canvases, responsive data tables).
- **Accessibility & UX**: Ensure keyboard navigation, ARIA semantics, and contrast compliance.
- **Performance**: Optimize canvas re-renders and bounding box overlays on video playback using requestAnimationFrame and offscreen buffers.

---

## 6. Truthful Reporting & Verification Protocol

- **Verification First**: Never report a task, service, installation, or test as "complete" or "successful" unless it has been explicitly executed and verified via terminal output.
- **Transparent Logging**: Report every completed action, skipped action, warning, and error truthfully.
