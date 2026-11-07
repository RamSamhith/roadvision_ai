# ROADVISION AI — S4-T1 REPORT
## Day-1 GPU Gate and YOLO26 Compatibility Probe

**Date:** 5 November 2026
**Owner:** Ram (AI/CV workstream)
**Task:** S4-T1 — create and run `training/verify_gpu.py`
**Authority:** TDD v1.1 §14 ("Installation order and gate"); `ROADVISION_STAGE_3_1_INSPECTION.md` §12
**Status:** **GATE PASSED** — 42 assertions passed, 0 failed
**Implementation:** `training/verify_gpu.py` (new file, Ram-owned)

---

## 1. Scope compliance

| Restriction | Compliance |
| :--- | :--- |
| Only create/modify Ram-owned files | Yes — only `training/verify_gpu.py` (new) and this report (new) |
| Create `training/` if absent | Yes — directory did not exist; created implicitly with the script |
| Do not modify Shakib's API / DB / frontend / orchestration | Yes — no file under `backend/` or `frontend/` was touched |
| Do not install, upgrade or remove dependencies | Yes — no pip command was issued; `.venv` unchanged |
| Do not download datasets or model weights | Yes — verified programmatically (0 `*.pt` files before and after) |
| Do not start training | Yes — no `train()` anywhere |
| Do not commit or push | Yes — nothing staged or committed |

**Commands executed (the only two that mutate anything):**

```powershell
.\.venv\Scripts\python.exe -m py_compile training\verify_gpu.py
.\.venv\Scripts\python.exe training\verify_gpu.py
```

---

## 2. What the script verifies

| # | Required check | Where it is implemented |
| :-: | :--- | :--- |
| 1 | Python / PyTorch / torchvision / CUDA / driver versions | `report_versions()` — includes `nvidia-smi --query-gpu=name,driver_version,memory.total,compute_cap` |
| 2 | CUDA availability and GPU identification | `check_cuda_device()` — asserts availability and device count, prints name and SM count |
| 3 | RTX 5060 capability and `sm_120` support | `check_cuda_device()` — asserts the installed arch list contains kernels for the detected capability, and explicitly requires `sm_120` when capability is `(12, 0)` |
| 4 | Real CUDA matmul with finite validation | `check_matmul_and_memory()` — 2048×2048 on `cuda`, `torch.isfinite(...).all()`, `synchronize()` |
| 5 | VRAM allocated / reserved / total | `check_matmul_and_memory()` — asserts `0 <= allocated <= reserved <= total` |
| 6 | Integer `0` vs string `"0"` | `check_device_selection()` resolves both with `select_device` and asserts `cuda:0`; probe C additionally predicts with `device="0"` |
| 7 | Build YOLO26n from YAML without weights | `build_yaml_model()` — `YOLO("yolo26n.yaml")`; `ckpt_path is None`; zero `*.pt` files created |
| 8 | Predict with `nms=False` and with defaults | probes A and B, each on a **fresh** model instance |
| 9 | Warnings, errors, result types, box shapes | `UltralyticsWarningSink` + `warnings.catch_warnings` + `describe_result()`; every probe records `Results`/`Boxes` types, `(N, 6)` data shape, `(N, 4)` xyxy shape, dtype, device, `orig_shape`, per-stage timings |
| 10 | `YOLO_OFFLINE` and Ultralytics settings sync | `report_offline_state()` — reports env var, `env_bool`, `sync`, and the settings file path |

**Fail-fast contract:** every required condition goes through `Gate.require()`, which raises
`GateFailure` and terminates with exit code 1. `GATE PASSED` is printed only on the final line,
after the failure count is confirmed to be zero. Unexpected exceptions exit with code 2.

---

## 3. Verbatim execution output

Command:

```powershell
cd "C:\Users\ramsa\Desktop\roadvision ai"
.\.venv\Scripts\python.exe training\verify_gpu.py
```

Exit code: **0**

```text
RoadVision AI - Day-1 GPU gate and YOLO26 compatibility probe
TDD v1.1 Section 14 / Stage S4-T1
Random untrained weights only: no accuracy or performance claim is made.
[INFO] pt_files_present_before: <none>

==============================================================================
1. Versions
==============================================================================
[INFO] python: 3.11.9
[INFO] python_executable: C:\Users\ramsa\Desktop\roadvision ai\.venv\Scripts\python.exe
[INFO] platform: Windows-10-10.0.26300-SP0
[INFO] torch: 2.11.0+cu128
[INFO] torchvision: 0.26.0+cu128
[INFO] torch.version.cuda: 12.8
[INFO] torch.cuda.is_available: True
[INFO] nvidia-smi: NVIDIA GeForce RTX 5060 Laptop GPU, 591.84, 8151 MiB, 12.0
[INFO] opencv: 5.0.0
[PASS] torch is a CUDA build  (torch.version.cuda='12.8')
[PASS] torch is not a CPU-only build  (2.11.0+cu128)

==============================================================================
2-3. CUDA availability, GPU identity, compute capability, kernels
==============================================================================
[PASS] CUDA is available
[PASS] at least one CUDA device  (count=1)
[INFO] gpu_name: NVIDIA GeForce RTX 5060 Laptop GPU
[INFO] compute_capability: (12, 0)
[INFO] total_memory_bytes: 8546484224
[INFO] total_memory_GiB: 7.96
[INFO] total_memory_GB_decimal: 8.55
[INFO] multiprocessor_count: 26
[INFO] arch_list: ['sm_75', 'sm_80', 'sm_86', 'sm_90', 'sm_100', 'sm_120']
[INFO] required_kernel_arch: sm_120 (or compute_120)
[PASS] torch build contains kernels for this GPU  (sm_120 in arch_list=True, compute_120 in arch_list=False)
[PASS] sm_120 kernels present for the RTX 5060  (arch_list=['sm_75', 'sm_80', 'sm_86', 'sm_90', 'sm_100', 'sm_120'])

==============================================================================
4-5. Real CUDA matrix multiplication and VRAM accounting
==============================================================================
[PASS] matmul output shape  (shape=(2048, 2048))
[PASS] matmul result is finite
[PASS] matmul output element count  (numel=4194304 expected=4194304)
[INFO] matmul_sample: y[0,0]=-9.544709
[INFO] memory_allocated_bytes: 42074112
[INFO] memory_reserved_bytes: 94371840
[INFO] memory_peak_allocated_bytes: 71434240
[INFO] memory_allocated_MiB: 40.1
[INFO] memory_reserved_MiB: 90.0
[INFO] memory_peak_allocated_MiB: 68.1
[INFO] memory_total_MiB: 8150.6
[PASS] reserved >= allocated
[PASS] reserved does not exceed total VRAM
[PASS] peak allocation recorded

==============================================================================
6. Device selection: integer 0 vs string "0"
==============================================================================
[INFO] select_device(0): cuda:0 type=cuda index=0
[INFO] select_device("0"): cuda:0 type=cuda index=0
[PASS] integer device 0 resolves to cuda:0  (cuda:0)
[PASS] string device "0" resolves to cuda:0  (cuda:0)
[PASS] integer 0 and string "0" resolve to the same device  (cuda:0 == cuda:0)

==============================================================================
7-8. YOLO26 built from YAML, end-to-end vs external-NMS probes
==============================================================================
NOTE: yolo26n.yaml produces a randomly initialised network. The blank 640x640 image below is a synthetic compatibility input, not a test image, and the timings are not benchmarks.

-- probe A_nms_False --
[INFO] model_yaml: yolo26n.yaml
[INFO] head_class: Detect
[INFO] head_nc: 80
[INFO] head_has_one2one_branch: True
[INFO] head_end2end_before_any_predict: False
[INFO] model_ckpt_path: None
[INFO] parameter_count: 2572280
[PASS] probe A_nms_False returned a one-element list  (type=list len=1)
[INFO] A_nms_False.result_type: Results
[INFO] A_nms_False.boxes_type: Boxes
[INFO] A_nms_False.num_boxes: 0
[INFO] A_nms_False.boxes_data_shape: (0, 6)
[INFO] A_nms_False.boxes_xyxy_shape: (0, 4)
[INFO] A_nms_False.boxes_dtype: torch.float32
[INFO] A_nms_False.boxes_device: cuda:0
[INFO] A_nms_False.orig_shape: (640, 640)
[INFO] A_nms_False.speed_ms: {'preprocess': 26.01630000026489, 'inference': 17.93920000000071, 'postprocess': 0.9060000002136803}
[PASS] probe A_nms_False produced a 2-D boxes tensor  ((0, 6))
[PASS] probe A_nms_False boxes have 6 columns (x1,y1,x2,y2,conf,cls)  ((0, 6))
[PASS] probe A_nms_False preserved the original image shape  (orig_shape=(640, 640) input=(640, 640))
[INFO] A_nms_False.backend_end2end: True
[PASS] probe A_nms_False selected the expected head  (end2end=True expected=True)

-- probe B_default --
[PASS] probe B_default returned a one-element list  (type=list len=1)
[INFO] B_default.result_type: Results
[INFO] B_default.boxes_type: Boxes
[INFO] B_default.num_boxes: 0
[INFO] B_default.boxes_data_shape: (0, 6)
[INFO] B_default.boxes_xyxy_shape: (0, 4)
[INFO] B_default.boxes_dtype: torch.float32
[INFO] B_default.boxes_device: cuda:0
[INFO] B_default.orig_shape: (640, 640)
[INFO] B_default.speed_ms: {'preprocess': 5.957600000328966, 'inference': 17.750499999237945, 'postprocess': 1.444200000150886}
[PASS] probe B_default produced a 2-D boxes tensor  ((0, 6))
[PASS] probe B_default boxes have 6 columns (x1,y1,x2,y2,conf,cls)  ((0, 6))
[PASS] probe B_default preserved the original image shape  (orig_shape=(640, 640) input=(640, 640))
[INFO] B_default.backend_end2end: False
[PASS] probe B_default selected the expected head  (end2end=False expected=False)

-- probe C_device_string --
[PASS] probe C_device_string returned a one-element list  (type=list len=1)
[INFO] C_device_string.result_type: Results
[INFO] C_device_string.boxes_type: Boxes
[INFO] C_device_string.num_boxes: 0
[INFO] C_device_string.boxes_data_shape: (0, 6)
[INFO] C_device_string.boxes_xyxy_shape: (0, 4)
[INFO] C_device_string.boxes_dtype: torch.float32
[INFO] C_device_string.boxes_device: cuda:0
[INFO] C_device_string.orig_shape: (640, 640)
[INFO] C_device_string.speed_ms: {'preprocess': 1.5698999995947815, 'inference': 11.8772000005265, 'postprocess': 0.5852000003869762}
[PASS] probe C_device_string produced a 2-D boxes tensor  ((0, 6))
[PASS] probe C_device_string boxes have 6 columns (x1,y1,x2,y2,conf,cls)  ((0, 6))
[PASS] probe C_device_string preserved the original image shape  (orig_shape=(640, 640) input=(640, 640))
[INFO] C_device_string.backend_end2end: False
[PASS] probe C_device_string selected the expected head  (end2end=False expected=False)

-- probe D_deprecated_end2end_False --
WARNING 'end2end=False' is deprecated and will be removed in the future. Use 'nms=None' instead.
[PASS] probe D_deprecated_end2end_False returned a one-element list  (type=list len=1)
[INFO] D_deprecated_end2end_False.result_type: Results
[INFO] D_deprecated_end2end_False.boxes_type: Boxes
[INFO] D_deprecated_end2end_False.num_boxes: 0
[INFO] D_deprecated_end2end_False.boxes_data_shape: (0, 6)
[INFO] D_deprecated_end2end_False.boxes_xyxy_shape: (0, 4)
[INFO] D_deprecated_end2end_False.boxes_dtype: torch.float32
[INFO] D_deprecated_end2end_False.boxes_device: cuda:0
[INFO] D_deprecated_end2end_False.orig_shape: (640, 640)
[INFO] D_deprecated_end2end_False.speed_ms: {'preprocess': 1.514800000222749, 'inference': 13.710299999729614, 'postprocess': 0.5919000004723785}
[PASS] probe D_deprecated_end2end_False produced a 2-D boxes tensor  ((0, 6))
[PASS] probe D_deprecated_end2end_False boxes have 6 columns (x1,y1,x2,y2,conf,cls)  ((0, 6))
[PASS] probe D_deprecated_end2end_False preserved the original image shape  (orig_shape=(640, 640) input=(640, 640))
[INFO] D_deprecated_end2end_False.backend_end2end: False
[PASS] probe D_deprecated_end2end_False selected the expected head  (end2end=False expected=False)
[WARN] D_deprecated_end2end_False ultralytics log: WARNING: WARNING 'end2end=False' is deprecated and will be removed in the future. Use 'nms=None' instead.

-- probe E_low_conf_evidence --
[PASS] probe E_low_conf_evidence returned a one-element list  (type=list len=1)
[INFO] E_low_conf_evidence.result_type: Results
[INFO] E_low_conf_evidence.boxes_type: Boxes
[INFO] E_low_conf_evidence.num_boxes: 300
[INFO] E_low_conf_evidence.boxes_data_shape: (300, 6)
[INFO] E_low_conf_evidence.boxes_xyxy_shape: (300, 4)
[INFO] E_low_conf_evidence.boxes_dtype: torch.float32
[INFO] E_low_conf_evidence.boxes_device: cuda:0
[INFO] E_low_conf_evidence.orig_shape: (640, 640)
[INFO] E_low_conf_evidence.speed_ms: {'preprocess': 1.4633999999205116, 'inference': 18.688500000280328, 'postprocess': 14.791200000217941}
[PASS] probe E_low_conf_evidence produced a 2-D boxes tensor  ((300, 6))
[PASS] probe E_low_conf_evidence boxes have 6 columns (x1,y1,x2,y2,conf,cls)  ((300, 6))
[PASS] probe E_low_conf_evidence preserved the original image shape  (orig_shape=(640, 640) input=(640, 640))
[INFO] E_low_conf_evidence.backend_end2end: True
[PASS] probe E_low_conf_evidence selected the expected head  (end2end=True expected=True)
[PASS] low-threshold probe produced populated boxes  (num_boxes=300)

==============================================================================
9b. Diagnostic: NMS-mode persistence on a re-used model instance
==============================================================================
Not a required assertion. Records whether the head mode is sticky.
[INFO] end2end_after_nms_False_call: True
[INFO] end2end_after_following_default_call: True
[WARN] the end-to-end head is STICKY on a re-used model instance: a later default-argument predict() did not revert to external NMS. Use a fresh model instance per mode (see R-02).

==============================================================================
9c. Diagnostic: untrained weights are input-independent
==============================================================================
Not a required assertion. Confirms the random weights carry no signal.
[INFO] blank.num_boxes: 300
[INFO] noise.num_boxes: 300
[INFO] blank.max_confidence: 0.00015623
[INFO] noise.max_confidence: 0.00015623
[WARN] blank and noise images produced identical box counts and confidences. This is expected from random initialisation and proves the forward pass carries no detection signal: no accuracy, recall or precision may be inferred from it.

==============================================================================
No-download verification
==============================================================================
[INFO] pt_files_present_after: <none>
[PASS] no model weights were downloaded or created  (before=0 after=0)

==============================================================================
10. Offline / analytics state
==============================================================================
[INFO] env YOLO_OFFLINE: <unset>
[INFO] env_bool(YOLO_OFFLINE): False
[INFO] settings.sync: True
[INFO] settings.datasets_dir: C:\Users\ramsa\Desktop\LiveFaceProject\datasets
[INFO] settings.weights_dir: weights
[INFO] settings.runs_dir: runs
[INFO] settings_file: C:\Users\ramsa\AppData\Roaming\Ultralytics\settings.json
[WARN] Ultralytics settings sync is enabled (settings['sync']=True). This is the user-level setting shared by every project on this machine. AC-18 requires no external calls during inference, so the serving process must set YOLO_OFFLINE=1 and disable sync (or set YOLO_CONFIG_DIR to a project-local config) before claiming AC-18. No global setting was modified by this gate.
[INFO] offline_note: YOLO_OFFLINE is not set for this gate run; the gate performs no network I/O because it never resolves a remote weight path

==============================================================================
Gate summary
==============================================================================
assertions passed : 42
assertions failed : 0
informational     : 100
warnings          : 4

GATE PASSED
Reminder: this gate proves environment and API compatibility only. It does not establish detection accuracy, and the printed timings are not benchmarks.
```

---

## 4. Result summary

| Metric | Value |
| :--- | :--- |
| Required assertions passed | **42** |
| Required assertions failed | **0** |
| Informational lines | 100 |
| Warnings recorded | 4 (all expected / explained below) |
| Exit code | 0 |

### 4.1 Environment confirmed by this run

| Item | Observed |
| :--- | :--- |
| Python | 3.11.9 (`.venv` interpreter) |
| PyTorch | 2.11.0+cu128 |
| torchvision | 0.26.0+cu128 |
| CUDA runtime bundled with torch | 12.8 |
| `torch.cuda.is_available()` | `True` |
| GPU | NVIDIA GeForce RTX 5060 Laptop GPU |
| Driver | 591.84 |
| `nvidia-smi` memory / capability | 8151 MiB, compute capability 12.0 |
| Torch device capability | `(12, 0)` |
| `torch.cuda.get_arch_list()` | `['sm_75', 'sm_80', 'sm_86', 'sm_90', 'sm_100', 'sm_120']` |
| `sm_120` present | **Yes** |
| VRAM visible to torch | 8 546 484 224 bytes = **7.96 GiB** (8150.6 MiB) |
| Streaming multiprocessors | 26 |
| OpenCV | 5.0.0 |
| Matmul | 2048×2048, shape OK, all finite, `synchronize()` OK |
| Device selection | `select_device(0) == select_device("0") == cuda:0` |

### 4.2 YOLO26 probe evidence (random weights, 640×640 blank image)

| Probe | Arguments | Backend `end2end` | Boxes | `boxes.data` | `boxes.xyxy` |
| :--- | :--- | :--- | :-: | :--- | :--- |
| A | `nms=False` | **True** | 0 | `(0, 6)` | `(0, 4)` |
| B | default (no `nms`) | **False** | 0 | `(0, 6)` | `(0, 4)` |
| C | `device="0"`, default | **False** | 0 | `(0, 6)` | `(0, 4)` |
| D | `end2end=False` (deprecated) | **False** | 0 | `(0, 6)` | `(0, 4)` |
| E | `nms=False, conf=0.0` | **True** | 300 | `(300, 6)` | `(300, 4)` |

Model from YAML: `head_class=Detect`, `nc=80`, one-to-one branch present,
`end2end` before any predict = `False`, `ckpt_path=None`, parameters = 2 572 280
(matches the packaged `nms()`-scale comment of 2,572,280 in `yolo26.yaml`).

---

## 5. Findings that change or confirm earlier decisions

### 5.1 N-02 is now confirmed empirically (not just from source reading)

S4-T1 was designed to settle the `end2end` vs `nms` question raised in Stage 3.1.
The probe produced the definitive result:

```
WARNING 'end2end=False' is deprecated and will be removed in the future. Use 'nms=None' instead.
```

| Question | Answer from this run |
| :--- | :--- |
| Does `end2end=` still work? | Yes, but it emits a deprecation warning and is translated onto `nms` |
| What does `end2end=False` map to? | `nms=None` → **external NMS** (the traditional path) → `backend.end2end = False` |
| What actually enables the NMS-free head? | **`nms=False`** → `backend.end2end = True` |
| Does default `predict()` use end-to-end on YOLO26? | **No** — the YAML only *builds* the one-to-one branch; it does not select it. `backend.end2end = False` |
| Is the box tensor layout identical in both modes? | Yes — `(N, 6)` = `x1, y1, x2, y2, conf, cls`, and `xyxy` is `(N, 4)` |

**Consequence for Q-02.** Recommending end-to-end for both models remains valid, but the
implementation must call `nms=False`. The TDD's literal `NMS_ARGS = {"end2end": False, "iou": 0.7}`
selects *external NMS*, i.e. the opposite of what the TDD intends when it names end-to-end as the
default. This is a documented deviation, not an interpretation.

### 5.2 N-09 (new): the head mode is sticky on a re-used model instance

Diagnostic 9b: after one `predict(nms=False)` call, a subsequent `predict()` **with default
arguments on the same model object stayed end-to-end**:

```
end2end_after_nms_False_call: True
end2end_after_following_default_call: True
```

Cause (confirmed in source): `predict` re-runs `setup_model(fuse=True)`; `Detect.fuse()` deletes
the one-to-many branch (`cv2 = None`), and `AutoBackend` only overrides the head when `end2end` is
not `None`. A default call passes `None`, so the already-fused head cannot go back.

**Rule adopted for RoadVision:** build a **fresh model instance per mode**. Never switch
`nms` on a live model object. This also constrains the fallback design — YOLO26m and YOLO26n must
be loaded with the same mode at construction, not switched in place.

### 5.3 N-08 (new): Ultralytics settings are user-global, not project-local

```
settings.sync          : True
settings.datasets_dir  : C:\Users\ramsa\Desktop\LiveFaceProject\datasets
settings.weights_dir   : weights          (relative)
settings.runs_dir      : runs             (relative)
settings_file          : C:\Users\ramsa\AppData\Roaming\Ultralytics\settings.json
```

This is a shared, machine-wide file that already points at **a different project's dataset
directory**. Nothing was modified by this gate, but two risks follow:

1. A relative `weights`/`runs` setting resolves against the *current working directory*, so a
   careless `YOLO("yolo26n.pt")` or `save=True` could write outside `models/`.
2. `datasets_dir` pointing at another project makes `data=` resolution ambiguous.

**Recommendation (requires approval before Stage 4):**

- RoadVision always passes **absolute paths** for `data`, `project`, `name`, and weights.
- The serving/training process sets `YOLO_CONFIG_DIR` to a project-local config directory (this
  must happen *before* importing ultralytics) and `YOLO_OFFLINE=1`, so AC-18 can be claimed
  honestly and this repo stops depending on machine-wide state.
- No change to the global `settings.json` is proposed.

### 5.4 Untrained weights are provably input-independent

Diagnostic 9c compared a blank image with a deterministic random-noise image at `conf=0.0`:

```
blank.num_boxes: 300
noise.num_boxes: 300
blank.max_confidence: 0.00015623
noise.max_confidence: 0.00015623
```

Identical detections for completely different pixel content is exactly what random
initialisation implies. It is the empirical justification for the "no accuracy claim" statement:
this run proves **plumbing**, not detection.

### 5.5 Minor observation: the platform string says "Windows-10"

`platform.platform()` returns `Windows-10-10.0.26300-SP0`. The OS is genuinely
**Microsoft Windows 11 Home, build 26300**, 64-bit — the kernel major version is still `10.0`,
so Python's string says "10". This is not a downgrade and is recorded so it is not misread later.

---

## 6. Performance numbers — what they mean and what they do not

The log contains `speed_ms` values (for example inference ≈ 11–19 ms). They are **smoke-test
timings of a randomly initialised network on a black image**, measured once with no warm-up
protocol and no repetition. They are **not**:

- a benchmark,
- a production latency figure,
- an FPS result,
- a comparison between YOLO26m and YOLO26n.

The TDD §16 measurement protocol (≥ 20 runs after warm-up, median and mean, model-only and
end-to-end separately) is still outstanding and will be executed only with real trained weights.

---

## 7. Unresolved issues

| # | Issue | Impact | Status |
| :-: | :--- | :--- | :--- |
| 1 | `nms=False` is the correct end-to-end switch, not `end2end=True` | Q-02 mechanism, training configuration | **Resolved technically**; needs team ratification of the deviation (N-02) |
| 2 | Mode is sticky per model instance | Model manager must load one mode per instance | **Mitigated by design rule**; needs implementation in `model_manager.py` |
| 3 | Ultralytics settings are machine-global and point at another project | AC-18 offline claim; path safety | **Open** — `YOLO_CONFIG_DIR` / absolute-path policy needs approval (N-08) |
| 4 | `settings.sync = True` | AC-18 | **Open** — must be disabled for the serving process (N-06) |
| 5 | End-to-end behaviour on real weights is unverified | Training/eval parity | **Blocked on approved weight download** (`--weights` mode of this script exists but was not run) |
| 6 | `quantize=16` vs deprecated `half` | Optional FP16 (Q-07) | **Deferred** until VRAM/latency measurement |
| 7 | OpenCV 5.0 behaviour on real video | Video engine | **Open** — A-07, unchanged by this gate |
| 8 | `StarletteDeprecationWarning` (httpx 0.28.1) | Test suite | **Open** — Shakib's area; unchanged |

Nothing in this list blocks the gate. Items 1–2 require a one-line documentation update to the
TDD deviation log before training configuration is written.

---

## 8. Files created

| Path | Status | Notes |
| :--- | :--- | :--- |
| `training/verify_gpu.py` | **new** | 742 lines; the gate script |
| `docs/project/ROADVISION_S4_T1_REPORT.md` | **new** | this report |
| `training/__pycache__/verify_gpu.cpython-311.pyc` | generated | build artifact, already ignored by `.gitignore` (`__pycache__/`) |

No tracked file was modified. `git status` shows `?? training/` in addition to the Stage 2/3
untracked files; nothing was staged or committed.

---

## 9. Recommended next task (not started)

**S4-T2 — Decide the path-safety/offline policy, then start dataset acquisition.**

Two small decisions should be taken before the dataset work begins, because both affect every
later script:

1. **Ratify N-02** (`nms=False` = end-to-end; `end2end=` is never used in new code).
2. **Ratify N-08** (absolute paths everywhere + `YOLO_CONFIG_DIR` for a project-local config +
   `YOLO_OFFLINE=1` for the serving process).

After that, the next implementation step is TDD §4.1 acquisition (`A1`–`A7` in the Stage 3.1
report §6.1): confirm the figshare listing, check for ≥ 3× archive free space, download, verify
size/MD5, `zipfile.testzip()`, extract to a short path, and record SHA-256 — followed by
`inspect_dataset.py` (TDD §4.2).

**Explicitly not done and not to be started automatically:** dataset download, weight download,
training, `backend/` scaffolding, commits.

---

**END OF S4-T1 REPORT.**
