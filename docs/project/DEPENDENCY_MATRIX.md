# RoadVision AI — Dependency & Compatibility Matrix

**Prepared:** 2026-11-05 (Stage 2)
**Verification method:** every version below was read from the installed environment
(`.venv\Scripts\python.exe -m pip list --format=freeze`, `npm ls --depth=0`, `node --version`,
`ffmpeg -version`, `nvidia-smi`), not from documentation or memory. The rationale column cites
the ratified document that requires the dependency.

**Authority order:** TDD v1.1 → PRD v1.1 → Project Proposal.

---

## 1. Host facts that constrain every choice

| Fact | Measured value | Consequence |
| :--- | :--- | :--- |
| GPU | NVIDIA GeForce RTX 5060 Laptop GPU | Meets TDD Table 10 p18 |
| Compute capability | **(12, 0)** → `sm_120` (Blackwell) | **Requires CUDA 12.8+ wheels.** Pre-12.8 builds have no kernels for this GPU |
| VRAM | 8151 MiB total / **7.96 GiB** visible to PyTorch | Caps batch size; TDD Appendix C p22 lists VRAM as unverified until measured |
| Driver | 591.84 (reports CUDA 13.1 compatibility) | Newer than the 12.8 runtime shipped in the wheel — forward compatible |
| OS | Windows 11, AMD64 | TDD Table 11 p18 |
| Python | 3.11.9 | TDD Table 11 p18 requires 3.11 |
| Node.js | 24.19.0 (npm 11.16.0) | TDD Table 11 p18 requires 24.x, pinned in `.nvmrc` |
| FFmpeg (system) | 9.0-full_build, `--enable-libx264`, `--enable-libx265` | Satisfies TDD §8 p11–12 H.264 output requirement |
| CUDA Toolkit | **Not installed** | Not needed: the cu128 wheel ships its own runtime. TDD §14 p18 allows this |

---

## 2. Python runtime stack (backend)

### 2.1 Deep learning and vision

| Package | Installed | Constraint / source | Why exactly this |
| :--- | :--- | :--- | :--- |
| `torch` | **2.11.0+cu128** | TDD Table 11 p18: "PyTorch CUDA build for CUDA 12.8 or newer (supports compute capability 12.0)" | `torch.version.cuda == "12.8"`; `"sm_120" in torch.cuda.get_arch_list()` verified `True`; real matmul on device 0 produced finite output. The `+cu128` local version is mandatory — a plain `pip install torch` on Windows can resolve to a CPU-only build (TDD §14 p18 warns exactly this) |
| `torchvision` | **0.26.0+cu128** | Must match the torch build | 0.26.0 is the torchvision release paired with torch 2.11; mismatched pairs fail at import |
| `ultralytics` | **8.4.202** | TDD Table 11 p18 | Provides `YOLO`, `predict`, training and validation. Verified: `YOLO("yolo26n.yaml")` builds and runs a forward pass on GPU and CPU, so the YOLO26 architecture exists in this release |
| `opencv-python` | **5.0.0.93** | TDD Table 11 p18 ("OpenCV") | Decode/annotate/encode. **Deviation D-06:** not `opencv-python-headless`, because Ultralytics declares `opencv-python` and installing both variants puts two `cv2` packages in one environment |
| `numpy` | **2.4.6** | Not pinned by any document | Required: torch 2.11 and OpenCV 5 are built against NumPy 2.x. **Deviation D-05:** the old `numpy<2.0.0` cap in the previous manifest made the stack uninstallable |
| `pillow` | **13.0.0** | TDD §10.2 p14 (Pillow-based image validation) | `Image.verify()` plus `MAX_IMAGE_PIXELS` decompression-bomb guard |
| `scikit-learn` | **1.9.1** | TDD Table 11 p18 | Evaluation utilities (precision/recall helpers) |
| `imageio-ffmpeg` | **0.8.1** | TDD §2 p4, §8 p11–12 (`get_ffmpeg_exe()`) | Supplies the FFmpeg executable used for H.264 re-encode. **Deviation D-03:** replaces `ffmpeg-python`, which no document uses |
| `onnxruntime` | **1.31.1** | Pulled in by `ultralytics` | Present transitively; ONNX export remains optional/out of core scope (TDD App. B p22) |

### 2.2 Web layer

| Package | Installed | Constraint / source | Why exactly this |
| :--- | :--- | :--- | :--- |
| `fastapi` | **0.162.0** | TDD §10 p14–15; Table 11 p18 | Routes, request validation, `StreamingResponse` for MJPEG |
| `starlette` | **1.10.0** | Transitive via FastAPI | `FileResponse` for `/api/results/{name}` (TDD §10.2 p15) |
| `uvicorn` | **0.54.0** | TDD Table 11 p18 | ASGI server; `[standard]` extras pull `httptools`, `watchfiles`, `websockets` |
| `pydantic` | **2.14.2** | TDD §10.3 p15 (schemas) | Response/request models |
| `pydantic-settings` | **2.16.2** | Not required by TDD; installed for config loading | Optional convenience — not imported by any locked code yet |
| `python-multipart` | **0.0.33** | Required by FastAPI for `UploadFile` | Without it, multipart upload routes fail at import time |

### 2.3 Testing

| Package | Installed | Constraint / source | Note |
| :--- | :--- | :--- | :--- |
| `pytest` | **9.2.0** | TDD §16.1 p20 | Unit + API tests |
| `pytest-cov` | **7.1.0** | Not required by TDD | Coverage reporting; no target percentage is specified (see `OPEN_QUESTIONS.md` G-05) |
| `httpx` | **0.28.1** | Required by `starlette.testclient` | **Warning observed:** `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead`. `/api/health` still returns 200. Tracked as assumption A-08 |

### 2.4 Explicitly excluded

| Package | Was in the old manifest | Why removed |
| :--- | :--- | :--- |
| `sqlalchemy` | yes | TDD §11 p16 uses `import sqlite3` and raw SQL; an ORM has no consumer. **Deviation D-02** |
| `aiosqlite` | yes | Same reason; the design uses blocking DB calls inside `def` handlers |
| `ffmpeg-python` | yes | TDD §8 p11–12 calls the `imageio-ffmpeg` binary through `subprocess`. **Deviation D-03** |
| `aiofiles` | yes | Uploads are streamed with plain blocking reads in 1 MB chunks (TDD §10.2 p14). **Deviation D-04** |
| `pytest-asyncio` | yes | No `async def` test is required by TDD §16.1 p20; blocking handlers are tested synchronously |
| `torch-directml` | considered | The project targets CUDA on the RTX 5060, not the AMD iGPU. DirectML would add a second, unverified execution path |
| `torch` CPU wheel | considered | A CPU-only wheel cannot run on `sm_120`, violating FR-05/AC-09. The cu128 wheel still runs on CPU when CUDA is unavailable |
| `pymupdf` (and `pymupdf4llm`, `pymupdf_layout`) | installed for Stage 2 only | Used to read/verify the three PDFs. **Deviation D-09: stage tool, not an application dependency** |

---

## 3. Frontend stack

All versions are the resolved values from `frontend/package-lock.json` (`npm ls --depth=0`).

| Package | Resolved | Role | Constraint / source |
| :--- | :--- | :--- | :--- |
| `react` | **19.3.1** | UI runtime | TDD Table 11 p18 ("React"); `AGENTS.md` §5 requires React 18+ |
| `react-dom` | **19.3.1** | Renderer | Must match `react` |
| `react-router-dom` | **7.18.5** | Routes for image / video / live / history / dashboard | PRD §7 p10–11 requires navigation between all four modes |
| `vite` | **8.3.5** | Dev server + build | TDD Table 11 p18 ("Vite") |
| `@vitejs/plugin-react` | **6.2.1** | React fast refresh | Vite 8 compatible |
| `typescript` | **7.0.2** | Type checking | TDD Table 11 p18 ("TypeScript"); `tsc -b` runs before `vite build` |
| `tailwindcss` | **4.3.4** | Utility CSS | TDD Table 11 p18 ("Tailwind CSS") |
| `@tailwindcss/vite` | **4.3.4** | Tailwind v4 Vite integration | TDD §12 p17 says to follow the current Tailwind-for-Vite guide — v4 uses a Vite plugin, not PostCSS |
| `@types/react` | **19.3.0** | Types | Matches React 19 |
| `@types/react-dom` | **19.3.0** | Types | Matches React 19 |
| `@types/node` | **24.19.2** | Types for `vite.config.ts` | Matches Node 24 |
| `oxlint` | **1.91.0** | Lint (`npm run lint`) | Scaffold default; not mandated by any document |

### 3.1 Frontend deviations and reversals from the previous setup

| Item | Old state | Now | Reason |
| :--- | :--- | :--- | :--- |
| Tailwind integration | PostCSS + `tailwind.config.js` + `npx tailwindcss init -p` | `@tailwindcss/vite` + `@import "tailwindcss";` in `src/index.css` | Tailwind 4 removed the v3 init/PostCSS workflow; the v3 commands in the old setup guide do not work |
| HTTP client | `axios` (old install list) | Native `fetch` | TDD §12 p17 uses `fetch`; one less dependency |
| Test runner | none installed | none | TDD §16.1 p20 names only pytest + manual checklist (see `OPEN_QUESTIONS.md` G-05) |
| `lucide-react`, `clsx`, `tailwind-merge` | listed in old setup guide | **not installed** | Not referenced by any ratified document. Add only when a component actually needs them |

---

## 4. Compatibility chains (why this combination holds together)

```
Python 3.11.9
 └── torch 2.11.0+cu128        ← torch.version.cuda 12.8, arch list contains sm_120
      ├── torchvision 0.26.0+cu128
      ├── numpy 2.4.6
      └── ultralytics 8.4.202  ← YOLO26 yaml builds; GPU + CPU forward pass verified
           ├── opencv-python 5.0.0.93   (needs numpy>=2)
           ├── pillow 13.0.0
           ├── matplotlib 3.11.2        (transitive; plotting only)
           ├── polars 2.1.0             (transitive; ultralytics data layer)
           └── onnxruntime 1.31.1       (transitive)

fastapi 0.162.0
 └── starlette 1.10.0
      └── anyio 4.16.0
 pydantic 2.14.2 → pydantic-core 2.50.2
 uvicorn 0.54.0 → httptools 0.9.0 / watchfiles 1.3.0 / websockets 17.4

Node.js 24.19.0
 └── vite 8.3.5
      ├── @vitejs/plugin-react 6.2.1
      └── @tailwindcss/vite 4.3.4 → tailwindcss 4.3.4
 typescript 7.0.2 (tsc -b)
 react 19.3.1 + react-router-dom 7.18.5
```

**Verified end-to-end after install:**
- `torch.cuda.is_available() == True`; device name and capability `(12, 0)`; `sm_120` present.
- Real GPU matmul finite; peak reserved memory 90 MB during the gate.
- YOLO26n forward pass on GPU (`device=0`): **20.4 ms/frame on a blank 640 px image** — a smoke
  test only. It is **not** a throughput measurement and must not be reported as FPS.
- YOLO26n forward pass on CPU succeeded (fallback path exercised).
- FastAPI `TestClient` → `GET /api/health` → **200**.
- OpenCV `imencode`/`imdecode` round-trip and `mp4v` `VideoWriter` write succeeded.
- `npm run build` → TypeScript project build + Vite production bundle succeeded
  (CSS 8.92 kB, JS 220.57 kB).
- `npm run dev` proxy `/api` → `http://127.0.0.1:8000` configured in `vite.config.ts`.

**Not verified** (tracked in `OPEN_QUESTIONS.md` §6): `NMS_ARGS`/`end2end` kwarg acceptance,
`res.plot()` channel order, real video decode, DirectShow camera open, browser MP4 seeking,
YOLO26m training VRAM fit.

---

## 5. Pin policy

| Artifact | Mechanism | State |
| :--- | :--- | :--- |
| Backend | `backend/requirements.txt` with exact `==` pins for direct dependencies | Written; verified with `pip install --dry-run -r` |
| Python itself | Documented as 3.11.9 | Not enforced by a `.python-version` file (deliberate: a single-machine academic project) |
| Frontend | `frontend/package-lock.json` (npm lockfile, `^` ranges in `package.json`) | Committed with the scaffold |
| Node.js | `frontend/.nvmrc` = `24` | Added per TDD Table 11 p18 |
| CUDA build | `+cu128` local version inside `requirements.txt`, with `--extra-index-url https://download.pytorch.org/whl/cu128` | Pinned; without the index line a plain PyPI resolve installs the CPU build |
| FFmpeg | System 9.0-full_build; `imageio-ffmpeg` 0.8.1 supplies a fallback binary | Documented in `ENVIRONMENT_SETUP.md` |

> Re-pinning rule: `pip freeze` output is the authority. If any install changes a transitive
> version, regenerate the freeze file and add a `CHANGELOG.md` entry — do not hand-edit versions
> to make an error message disappear.

---

## 6. Risk register for this dependency set

| Risk | Trigger | Current mitigation |
| :--- | :--- | :--- |
| A plain `pip install torch` replaces the cu128 build with a CPU build | Adding a package that depends on `torch` without the index URL | `requirements.txt` carries `--extra-index-url`; re-run the GPU gate after every dependency change |
| OpenCV **5.0** is a new major version | API removals/renames vs the 4.x code the TDD was written against | Pin `5.0.0.93`; empirically re-verify every `cv2` call at feature build (A-07) |
| Ultralytics pulls a large transitive tree (matplotlib, polars, onnxruntime) | Install size and import time | Accepted; do not add a second vision framework |
| `starlette.testclient` deprecates httpx | Future Starlette/httpx upgrade | Pinned today; decide on httpx2 when the test suite is written (A-08) |
| TypeScript 7 + Vite 8 are very new | Plugin/type incompatibilities | `npm run build` passes today; keep `package-lock.json` committed |
| 8 GB VRAM is the training ceiling | YOLO26m at a large batch size | Measure with `verify_gpu.py`, then smoke-train at `batch=4` before scaling (A-09) |
| Windows path-length limit | Deep dataset trees from RDD2022 archives | TDD §4.1 p7 already requires a short extraction path |
