# RoadVision AI

RoadVision AI is an intelligent road condition analysis and hazard detection system utilizing state-of-the-art Computer Vision (YOLO), deep learning, and a modern web application stack to monitor road surface anomalies, traffic conditions, and safety metrics.

---

## Project Status

- **Phase**: Foundation & Environment Setup
- **Source of Truth**: Technical Design Document (TDD v1.1), Product Requirements Document (PRD v1.1), and Project Proposal.
- **Application Implementation**: Awaiting document ingestion and specifications. No features or model training commenced yet.

---

## System Requirements & Verified Environment

| Component | Verified Local Specification | Status |
| :--- | :--- | :--- |
| **Operating System** | Windows 11 (AMD64) | Verified |
| **CPU / APU** | AMD Ryzen Processor / AMD Radeon 780M Graphics | Verified |
| **NVIDIA CUDA** | Not available (Inference configured for CPU / DirectML) | Verified |
| **Python** | Python 3.11.9 | Verified (`C:\Users\ramsa\AppData\Local\Programs\Python\Python311\python.exe`) |
| **Node.js / npm** | Node.js v24.19.0 / npm 11.16.0 | Verified |
| **FFmpeg** | FFmpeg 9.0 (Full Build with AV1, H.264, H.265 support) | Verified |
| **Git** | Git 2.53.0 | Verified |
| **Disk Space** | C: Drive (443.5 GB free) | Verified |

---

## Repository Structure

```
roadvision ai/
├── AGENTS.md                  # Operational directives and rules of engagement for coding agents
├── README.md                  # Project overview and system specification
├── CHANGELOG.md               # Versioning and modification history
├── .gitignore                 # Git ignore rules for Python, Node, data, and model weights
├── backend/                   # FastAPI backend service
│   ├── app/
│   │   ├── api/               # API routers and endpoints
│   │   ├── core/              # Configuration, logging, security
│   │   ├── models/            # Pydantic schemas and database models
│   │   ├── services/          # Vision pipelines, inference engines, video processors
│   │   └── utils/             # Helper utilities and validators
│   ├── tests/                 # Backend unit and integration test suite
│   └── requirements.txt       # Python dependency manifest
├── frontend/                  # React + TypeScript + Vite + Tailwind CSS dashboard
├── data/                      # Dataset repository (git-ignored)
│   ├── raw/                   # Unprocessed video and image feeds
│   ├── processed/             # Preprocessed frames and crops
│   └── annotations/           # Annotation files (YOLO / COCO format)
├── models/                    # Model storage (git-ignored)
│   ├── weights/               # Trained and pre-trained model weights (.pt, .onnx)
│   └── configs/               # Model configuration YAML files
└── docs/                      # Documentation
    ├── project/               # Project governance and skills inventory
    ├── architecture/          # Architecture diagrams and system design
    └── setup/                 # Environment setup and onboarding guides
```

---

## Setup & Getting Started

Refer to [ENVIRONMENT_SETUP.md](file:///C:/Users/ramsa/Desktop/roadvision%20ai/docs/setup/ENVIRONMENT_SETUP.md) for full setup instructions.
