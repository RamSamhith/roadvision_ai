# RoadVision AI - Environment Setup & Installation Guide

This guide describes how to configure and verify the local development environment for RoadVision AI.

---

## 1. Verified Host Specifications

The environment has been audited on the host machine:
- **Operating System**: Windows 11 (64-bit)
- **CPU**: AMD Ryzen Processor (x86_64)
- **GPU**: AMD Radeon 780M Graphics (Integrated)
- **NVIDIA GPU / CUDA**: **None**. Systems without an NVIDIA GPU must run PyTorch inference via CPU or DirectML.
- **Python**: 3.11.9 (Verified at `C:\Users\ramsa\AppData\Local\Programs\Python\Python311\python.exe`)
- **Node.js**: v24.19.0 (npm v11.16.0)
- **FFmpeg**: v9.0-full_build (Global in PATH)
- **Git**: 2.53.0

---

## 2. Backend Environment Setup

A dedicated Python virtual environment has been initialized at `.venv/`.

### Activating the Virtual Environment
- **PowerShell**:
  ```powershell
  .\.venv\Scripts\Activate.ps1
  ```
- **Command Prompt (cmd)**:
  ```cmd
  .\.venv\Scripts\activate.bat
  ```

### Installing Backend Dependencies
Once requirements are aligned with TDD v1.1 specifications, install dependencies using the virtual environment's pip:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\pip.exe install -r backend\requirements.txt
```

> [!NOTE]
> Since this machine utilizes an AMD Radeon 780M APU, standard PyTorch wheels will automatically run on **CPU**. If GPU acceleration on AMD under Windows is desired in subsequent phases, `torch-directml` can be explored after validating baseline functionality.

### Verifying Backend Installation
Run the following verification command:
```powershell
.\.venv\Scripts\python.exe -c "import torch, fastapi, cv2; print('PyTorch:', torch.__version__, '| CUDA available:', torch.cuda.is_available(), '| OpenCV:', cv2.__version__)"
```

---

## 3. Frontend Environment Setup

The frontend will be scaffolded in `frontend/` using Vite, React 18+, TypeScript, and Tailwind CSS.

### Initialization Command (Pending TDD confirmation)
```powershell
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
npm install lucide-react clsx tailwind-merge axios
```

### Running Frontend Development Server
```powershell
npm run dev
```

---

## 4. Verification Checklist

Before commencing application development or model inference:
- [x] Workspace inspected and verified clean.
- [x] Initial project directory hierarchy established.
- [x] System hardware and software audited (Python 3.11.9, Node.js 24, Git, FFmpeg 9.0, AMD Radeon 780M).
- [x] `.venv` initialized and verified (`python --version` outputs 3.11.9).
- [x] `backend/requirements.txt` prepared.
- [x] AGENTS.md, README.md, CHANGELOG.md, SKILLS_INVENTORY.md documented.
- [ ] Receive and inspect official RoadVision documents: Project Proposal, PRD v1.1, and TDD v1.1.
- [ ] Align database schema and model versions with TDD v1.1.
- [ ] Run full dependency install after document alignment.
