# RoadVision — Installation Guide

This guide covers installing and running RoadVision locally on **Windows**, **Linux**, and **macOS**.

---

## 1. Prerequisites

RoadVision requires the following system tools:
- **Python**: 3.10 to 3.12 (Tested on 3.11.9)
- **Node.js**: v18.0.0 or later (v20+ LTS recommended; tested on v24.19.0) & npm (v9+)
- **FFmpeg**: Full build with H.264 support (libx264 or h264_nvenc) in system `PATH`
- **Git**: Installed and configured

---

## 2. Operating System Setup

### Windows (PowerShell)

1. **Verify Prerequisites**:
   ```powershell
   python --version
   node --version
   ffmpeg -version
   ```

2. **Clone and Create Virtual Environment**:
   ```powershell
   git clone https://github.com/RamSamhith/roadvision_ai.git
   cd roadvision_ai
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. **Install Backend Dependencies**:
   - **For NVIDIA GPU (CUDA)**:
     ```powershell
     pip install --upgrade pip setuptools wheel
     pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
     pip install -r backend/requirements.txt
     ```
   - **For CPU-Only**:
     ```powershell
     pip install --upgrade pip setuptools wheel
     pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
     pip install -r backend/requirements.txt
     ```

4. **Install Frontend Dependencies**:
   ```powershell
   cd frontend
   npm ci
   cd ..
   ```

---

### Linux (Ubuntu / Debian)

1. **Install System Dependencies & FFmpeg**:
   ```bash
   sudo apt update
   sudo apt install -y python3-pip python3-venv ffmpeg libgl1 libglib2.0-0 nodejs npm
   ```

2. **Clone and Create Virtual Environment**:
   ```bash
   git clone https://github.com/RamSamhith/roadvision_ai.git
   cd roadvision_ai
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install Backend Dependencies**:
   - **For NVIDIA GPU (CUDA 12)**:
     ```bash
     pip install --upgrade pip setuptools wheel
     pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
     pip install -r backend/requirements.txt
     ```
   - **For CPU-Only**:
     ```bash
     pip install --upgrade pip setuptools wheel
     pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
     pip install -r backend/requirements.txt
     ```

4. **Install Frontend Dependencies**:
   ```bash
   cd frontend
   npm ci
   cd ..
   ```

---

### macOS (Apple Silicon / Intel)

1. **Install System Dependencies via Homebrew**:
   ```bash
   brew install ffmpeg node python@3.11
   ```

2. **Clone and Virtual Environment**:
   ```bash
   git clone https://github.com/RamSamhith/roadvision_ai.git
   cd roadvision_ai
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install Python & Frontend Dependencies**:
   ```bash
   pip install --upgrade pip setuptools wheel
   pip install -r backend/requirements.txt
   cd frontend && npm ci && cd ..
   ```

---

## 3. Production Weights Setup

The production model is **YOLO26m** trained on road-damage classes (`D00`, `D10`, `D20`, `D40`).

- File path: `models/weights/yolo26m.pt`
- Expected SHA-256 Digest: `1BC41287DBDBC5EC5793D5D8F14CBA770E9E71E9C9E0CC0188B7146DA592D233`

To verify model integrity:
```powershell
# Windows PowerShell
Get-FileHash -Path models\weights\yolo26m.pt -Algorithm SHA256
```
```bash
# Linux / macOS
sha256sum models/weights/yolo26m.pt
```

---

## 4. Running the Application

### Option A: Separate Terminal Windows (Recommended for Development)

**Terminal 1 (Backend API)**:
```bash
# Windows
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --app-dir backend

# Linux / macOS
source .venv/bin/activate
PYTHONPATH=backend uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 (Frontend Client)**:
```bash
cd frontend
npm run dev
```

Open `http://localhost:5173` in your browser.

---

### Option B: Docker Compose (CPU Inference)

```bash
docker compose up --build
```
The backend API is exposed at `http://localhost:8000`.

