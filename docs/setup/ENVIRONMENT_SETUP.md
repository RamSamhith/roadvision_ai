# RoadVision AI — Environment Setup & Verification

**Prepared:** 2026-11-05 (Stage 2)
**Applies to:** Windows 11 on the project laptop (ASUS ROG Zephyrus G14, RTX 5060 Laptop GPU)
**Companion documents:** [`DEPENDENCY_MATRIX.md`](../project/DEPENDENCY_MATRIX.md) for version
rationale, [`OPEN_QUESTIONS.md`](../project/OPEN_QUESTIONS.md) for unresolved decisions.

> **Status of this guide.** Everything in §2–§6 was executed on this machine and the observed
> output is quoted. Anything that has **not** been run is explicitly marked *(not yet run)*.
> Do not treat a green box below as proof of a feature that does not exist yet — no application
> code, dataset or trained model is present at this stage.

---

## 1. Verified host

| Component | Verified value | How it was read |
| :--- | :--- | :--- |
| Operating system | Windows 11, 64-bit (AMD64) | `[System.Environment]::OSVersion` |
| CPU | AMD Ryzen 9 270 (8 cores / 16 threads) | `Get-CimInstance Win32_Processor` |
| GPU | **NVIDIA GeForce RTX 5060 Laptop GPU**, 8151 MiB, compute capability **(12, 0)** | `nvidia-smi --query-gpu=name,memory.total,driver_version,compute_cap --format=csv` |
| GPU driver | 591.84 (supports CUDA 13.1; backwards compatible with the 12.8 runtime in the wheel) | same command |
| CUDA Toolkit | **not installed — and not required** | `nvcc` absent; the PyTorch wheel carries its own runtime (TDD v1.1 §14 p18 permits this) |
| Integrated GPU | AMD Radeon 780M (unused by this project) | `Get-CimInstance Win32_VideoController` |
| RAM | 16 GB installed (≈15.3 GB usable) | `Get-CimInstance Win32_ComputerSystem` |
| Python | **3.11.9** (MSC v.1938, 64-bit) | `.venv\Scripts\python.exe -c "import sys; print(sys.version)"` |
| Node.js / npm | **24.19.0** / **11.16.0** | `node --version`, `npm --version` |
| FFmpeg | **9.0-full_build**, built with `--enable-libx264 --enable-libx265` | `ffmpeg -version` |
| Git | 2.53.0 | `git --version` |

**Correction to earlier documentation.** A previous version of this file, of `README.md` and of
`AGENTS.md` §2 stated that this machine has *no* NVIDIA GPU and that inference would run on
CPU/DirectML. That was wrong: `nvidia-smi` reports an RTX 5060 Laptop GPU with 8151 MiB, and
PyTorch runs real CUDA kernels on it. The three files have been corrected in this stage.

---

## 2. Prerequisites

Install once, then verify:

```powershell
python --version          # must print 3.11.x
node --version            # must print v24.x
npm --version
ffmpeg -version           # only the first line is needed
git --version
nvidia-smi                # must show the RTX 5060 and a driver version
```

If `nvidia-smi` is not found, the driver is missing — stop and install the NVIDIA driver before
continuing. A missing `nvcc` is **not** a problem; the CUDA toolkit is deliberately not installed.

---

## 3. Backend setup

### 3.1 Create or reuse the virtual environment

The environment already exists at `.venv\`. To recreate it from scratch:

```powershell
cd "C:\Users\ramsa\Desktop\roadvision ai"
python -m venv .venv
```

**Never install into the global Python interpreter** (`AGENTS.md` §3). Use the explicit
interpreter path instead of relying on activation:

```powershell
# Preferred: explicit paths, no activation needed, immune to execution-policy issues
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip --version
```

Activation also works if you prefer it:

```powershell
.\.venv\Scripts\Activate.ps1        # PowerShell; run `Set-ExecutionPolicy -Scope Process RemoteSigned` once if blocked
.\.venv\Scripts\activate.bat        # Command Prompt
```

### 3.2 Install dependencies

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

**Why the flags in `requirements.txt` matter.** The file starts with:

```
--extra-index-url https://download.pytorch.org/whl/cu128
```

Without that index, `pip install torch` on Windows can resolve to a **CPU-only** wheel, which
cannot execute on this GPU at all (TDD v1.1 §14 p18 warns about exactly this). The pins are
`torch==2.11.0+cu128` and `torchvision==0.26.0+cu128`; the `+cu128` suffix is only available from
that index.

A dry run confirms the manifest is satisfiable without changing anything:

```powershell
.\.venv\Scripts\python.exe -m pip install --dry-run --no-deps -r backend\requirements.txt
```

Observed on this machine: every requirement reported *"Requirement already satisfied"*.

### 3.3 GPU / PyTorch gate (must pass before any training)

This is the check TDD v1.1 §14 p18 requires on Day 1 and again before the demonstration. Run it
as a single command; it must print `True`, the device name, capability `(12, 0)`, the `sm_120`
kernel and a finite matmul result.

```powershell
.\.venv\Scripts\python.exe -c "import torch,numpy as np; print('torch',torch.__version__,'| cuda build',torch.version.cuda); assert torch.cuda.is_available(),'CUDA unavailable'; cc=torch.cuda.get_device_capability(0); arch=torch.cuda.get_arch_list(); print(torch.cuda.get_device_name(0),'capability',cc); print('arch list has sm_120:', 'sm_120' in arch); assert 'sm_120' in arch; x=torch.randn(2048,2048,device='cuda'); y=x@x; torch.cuda.synchronize(); print('matmul finite:',bool(torch.isfinite(y).all())); print('VRAM GiB:',round(torch.cuda.get_device_properties(0).total_memory/1024**3,2))"
```

**Observed output on this machine:**

```
torch 2.11.0+cu128 | cuda build 12.8
NVIDIA GeForce RTX 5060 Laptop GPU capability (12, 0)
arch list has sm_120: True
matmul finite: True
VRAM GiB: 7.96
```

The gate also checks that Ultralytics will not silently fall back to CPU. A forward pass on a
blank image proves the integration without downloading weights:

```powershell
.\.venv\Scripts\python.exe -c "import numpy as np; from ultralytics import YOLO; m=YOLO('yolo26n.yaml'); r=m.predict(np.zeros((640,640,3),np.uint8),device=0,imgsz=640,verbose=False); print('gpu detections:',len(r[0].boxes))"
```

Observed: one detection tensor returned, **≈20.4 ms per forward pass**.

> **This is a smoke test, not a benchmark.** It used a blank image and a randomly initialised
> architecture. It says nothing about accuracy or real throughput. Never quote it as "FPS" in
> the report.

The CPU fallback path was exercised the same way with `device='cpu'` and also succeeded.

### 3.4 FFmpeg for H.264 output

PRD FR-02 requires a browser-playable MP4, which OpenCV's default writer does not guarantee
(TDD §8 p11–12). Two FFmpeg sources exist here:

1. **System FFmpeg 9.0** in `PATH` — verified to include `libx264`, `libx265` and `aac`.
2. **`imageio-ffmpeg` 0.8.1** — a bundled binary used by the code path in TDD §8.

```powershell
ffmpeg -hide_banner -encoders | Select-String "libx264"
.\.venv\Scripts\python.exe -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"
```

### 3.5 OpenCV round-trip check

```powershell
.\.venv\Scripts\python.exe -c "import numpy as np, cv2; img=(np.random.rand(64,64,3)*255).astype('uint8'); ok,buf=cv2.imencode('.jpg',img); back=cv2.imdecode(buf,cv2.IMREAD_COLOR); print('opencv',cv2.__version__,'| encode-decode ok:', ok and back.shape==img.shape)"
```

Observed: `opencv 5.0.0.93 | encode-decode ok: True`. A `mp4v` `VideoWriter` write was also
verified. **Real decode of a user video and DirectShow camera capture are not yet tested**
(assumption A-07 in `OPEN_QUESTIONS.md`).

### 3.6 API smoke check

Once `backend/app/main.py` exists *(not yet written)*, the API is started from the repository root
with `backend/` added to the import path:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

*(This run convention is provisional: it is consistent with the `backend/app/…` layout in TDD
v1.1 §13 p18, but the TDD does not fix a start command. Confirm it when `main.py` is created.)*

At this stage only an app-shaped health route was exercised in-process with
`starlette.testclient`: `GET /api/health` → **200**.

> A deprecation warning appears:
> `Using httpx with starlette.testclient is deprecated; install httpx2 instead`.
> The test still passes. Decide whether to move to httpx2 when the real test suite is written.

---

## 4. Frontend setup

The scaffold already exists in `frontend/` and `npm run build` succeeds.

### 4.1 Recreate from scratch (reference only)

```powershell
cd "C:\Users\ramsa\Desktop\roadvision ai"
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install react-router-dom
npm install -D tailwindcss @tailwindcss/vite
```

These commands reflect **Tailwind 4**, which is a Vite plugin, not the PostCSS + `tailwind.config.js`
flow of v3. Do not run `npx tailwindcss init -p` — it is a v3 command and is not part of this
setup (TDD §12 p17 asks for the current Tailwind-for-Vite guidance).

### 4.2 Components already wired

| File | Purpose |
| :--- | :--- |
| `frontend/vite.config.ts` | Registers `@vitejs/plugin-react` and `@tailwindcss/vite`; proxies `/api` → `http://127.0.0.1:8000` |
| `frontend/src/index.css` | `@import "tailwindcss";` — the v4 entry point |
| `frontend/src/App.tsx` | Minimal shell (no product pages yet) |
| `frontend/.nvmrc` | `24`, per TDD Table 11 p18 |

### 4.3 Build and run

```powershell
cd "C:\Users\ramsa\Desktop\roadvision ai\frontend"
npm run build        # tsc -b && vite build
npm run dev          # http://localhost:5173, /api proxied to the backend
npm run lint         # oxlint
```

**Observed build output:** CSS **8.92 kB**, JS **220.57 kB**, exit code 0.

---

## 5. Running the whole stack (target layout)

Two terminals, both from the repository root:

```powershell
# Terminal 1 — backend (once backend/app/main.py exists); run from the repository root
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000

# Terminal 2 — frontend
cd frontend
npm run dev
```

`127.0.0.1` binding is a requirement, not a default: PRD §6 p10 and AC-18 forbid exposing the
service on the network unless the team documents a reason.

---

## 6. Verification checklist for this stage

Executed and observed on 2026-11-05:

- [x] `nvidia-smi` reports RTX 5060 Laptop GPU, 8151 MiB, driver 591.84, compute cap 12.0.
- [x] `torch 2.11.0+cu128`, CUDA build 12.8, `cuda.is_available() == True`.
- [x] `sm_120` present in `torch.cuda.get_arch_list()`; real matmul on device 0 is finite.
- [x] CPU fallback path executes a YOLO forward pass on `device='cpu'`.
- [x] `yolo26n.yaml` builds and runs on GPU (smoke test only; no weights downloaded).
- [x] `pip install --dry-run --no-deps -r backend\requirements.txt` resolves with no changes.
- [x] OpenCV 5.0.0.93 encode/decode round-trip; `mp4v` `VideoWriter` write.
- [x] FFmpeg 9.0 present with `libx264`; `imageio-ffmpeg` binary path resolves.
- [x] `GET /api/health` → 200 via `TestClient`.
- [x] `npm run build` succeeds (CSS 8.92 kB, JS 220.57 kB).
- [x] `.venv` isolated; no global installs were performed.
- [x] Original PDFs untouched; SHA-256 recorded in `docs/source/DOCUMENT_REGISTER.md`.

Not executed, by design (do not mark as done):

- [ ] `training/verify_gpu.py` as a committed script — TDD §14 p18 requires it; the equivalent
      checks were run inline above. **NOT STARTED**
- [ ] Real video decode, H.264 re-encode, browser playback/seeking — **NOT TESTED**
- [ ] DirectShow camera open on this laptop — **NOT TESTED**
- [ ] YOLO26m download, training, or evaluation — **NOT STARTED** (no dataset; no weights)
- [ ] Any application feature (routes, pages, SQLite schema) — **NOT STARTED**

---

## 7. Troubleshooting

| Symptom | Cause | Fix |
| :--- | :--- | :--- |
| `torch.cuda.is_available()` is `False` | A CPU-only wheel was installed, or the driver is too old | Reinstall with `-r backend\requirements.txt` (which carries the cu128 index). Check `torch.version.cuda` is not `None`. A plain `pip install torch` is the usual culprit |
| `AssertionError: This torch build has no kernels for sm_120` | Wrong wheel (CUDA < 12.8) | Same fix; verify `'sm_120' in torch.cuda.get_arch_list()` |
| `nvcc: command not found` | CUDA toolkit not installed | **Expected and harmless.** The wheel ships its own runtime; do not install the toolkit (TDD §14 p18) |
| Ultralytics silently runs on CPU | `device` not passed, or CUDA unavailable | Always pass `device=`; print the resolved device once at start-up |
| `FileNotFoundError` when importing `app.*` | Running uvicorn from the wrong directory | Run from the repository root and pass `--app-dir backend` (or `cd backend` first), so that `app` is importable |
| `ffmpeg` not found in `PATH` | FFmpeg not installed | `imageio-ffmpeg` provides a binary; the code path in TDD §8 uses it directly |
| Output MP4 will not play or seek in the browser | OpenCV wrote a non-browser codec | Re-encode to H.264 with the `imageio-ffmpeg` binary (TDD §8), then test seeking (assumption A-05) |
| `StarletteDeprecationWarning: ... install httpx2 instead` | New Starlette deprecating httpx for `TestClient` | Harmless today; decide on httpx2 when writing the test suite (A-08) |
| Windows "path too long" during dataset work | Deep RDD2022 extraction tree | Extract to a short root (TDD §4.1 p7) |
| `npm run build` type errors after adding a page | `tsc -b` is strict about unused/undocumented types | Fix the type; do not disable strict mode to make the build pass |

---

## 8. What this environment does *not* contain yet

| Area | State |
| :--- | :--- |
| `backend/app/` (routes, services, config, DB) | does not exist |
| `backend/tests/` | does not exist |
| `training/` (gate script, conversion, training, evaluation) | does not exist |
| `frontend/src/{pages,services,types}` | do not exist; only a placeholder shell |
| `models/weights/` | `.gitkeep` only — no YOLO26m or YOLO26n checkpoint |
| `data/raw/`, `data/processed/`, `data/annotations/` | `.gitkeep` only — no RDD2022 data |
| SQLite database | does not exist |

The stack is installed and verifiably functional. The application is not built.
