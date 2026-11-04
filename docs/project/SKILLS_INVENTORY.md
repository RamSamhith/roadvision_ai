# RoadVision AI - Agent Skills Inventory & Ecosystem Evaluation

This document cataloges the agent skills, developer tooling, and specialized workflow guidance discovered and evaluated for the RoadVision AI project.

---

## 1. Discovery Scope & Tech Stack Requirements

The RoadVision AI project requires specialized engineering capabilities across the following domains:
- **Core ML & CV**: Python 3.11+, PyTorch, Ultralytics YOLO, OpenCV, CUDA/Hardware acceleration.
- **Backend & Data**: FastAPI, SQLite (or configured database), Uvicorn, Pydantic, FFmpeg video processing.
- **Frontend & Web**: React 18+, TypeScript, Vite, Tailwind CSS, Canvas / Video overlay rendering.
- **Quality & Workflow**: Git version control, unit/integration testing (pytest, vitest), documentation, and ML lifecycle governance.

---

## 2. Installed & Active Agent Skills

| Skill / Tooling | Source | Classification | Primary Scope & Relevance to RoadVision |
| :--- | :--- | :--- | :--- |
| **`managing-python-dependencies`** | Google / Official | Core Python & Environment | Enforces virtual environment isolation (`.venv`), detects dependency managers, prevents global package contamination, and ensures reproducible Python environments. |
| **`ml-best-practices`** | Google / Official | ML & Computer Vision | Mandatory workflow rules for data integrity, chronological/stratified dataset splitting, leak prevention, class imbalance handling, metrics evaluation (mAP, precision, recall), and model comparison. |
| **`modern-web-guidance`** | Google / Official | Frontend & UI/UX | Authoritative web engineering guidelines for modern React, Vite, TypeScript, Tailwind CSS, responsive layouts, accessibility (WCAG), and performance optimization. |
| **`chrome-devtools` / `a11y-debugging`** | Official Plugin | Web Testing & Verification | Browser automation, UI layout inspection, console/network error tracing, and accessibility auditing for the frontend dashboard. |
| **`uv`** | Official / Ecosystem | Package Management | Fast, deterministic Python package resolution and virtual environment creation. |
| **`context7`** | MCP Tooling | Documentation Oracle | Real-time source documentation retrieval for frameworks without relying on outdated model memory (FastAPI, PyTorch, Ultralytics, etc.). |

---

## 3. Marketplace Discovery & Safety Audit

A systematic scan of the Antigravity Agent Marketplace was performed across all relevant keywords (`python`, `pytorch`, `fastapi`, `react`, `git`, `testing`, `vision`, `ffmpeg`, `tailwind`, `cuda`, `yolo`, `sqlite`):

- **Available Catalog Matches**:
  - `CodeRabbit` (antigravity-plugins-partners/plugin/coderabbit): External AI PR code review tool (optional for CI/CD, skipped for local development).
  - `Context7` (antigravity-plugins-partners/plugin/context7): Installed/Available for grounded documentation lookup.
  - `Modern Web Guidance` (antigravity-plugins-official/plugin/modern-web-guidance-plugin): Already installed and active.
- **Evaluation Decision**:
  - No external unverified third-party skills were installed.
  - Relying exclusively on trusted, verified official Google and core partner skills ensures environment stability and avoids supply-chain vulnerabilities or duplicate conflicting agents.

---

## 4. Phase-by-Phase Skill Invocation Matrix

| Project Phase | Primary Skills Applied | Verification Criteria |
| :--- | :--- | :--- |
| **Phase 1: Foundation & Setup** | `managing-python-dependencies` | `.venv` created, dependencies isolated, requirements pinned. |
| **Phase 2: ML & CV Pipeline** | `ml-best-practices`, `context7` | Clean train/val splits, dataset YAML verification, metrics tracking (mAP50, mAP50-95). |
| **Phase 3: Backend API & Video Processing** | `managing-python-dependencies`, `context7` | FastAPI async streaming, FFmpeg frame extraction, SQLite schemas validated. |
| **Phase 4: Frontend Dashboard** | `modern-web-guidance`, `chrome-devtools` | Responsive video playback, bounding box rendering, accessible controls. |
| **Phase 5: Integration & Testing** | `chrome-devtools`, `ml-best-practices` | End-to-end inference verification, test coverage for API and UI. |
