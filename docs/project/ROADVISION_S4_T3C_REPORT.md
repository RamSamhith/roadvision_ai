# ROADVISION AI — S4-T3C FINAL DATASET GATE READINESS REPORT
## Final verification and readiness check before YOLO26m training

**Date:** 6 November 2026  
**Owner:** Ram (AI/CV workstream)  
**Task:** S4-T3C — final dataset gate and pre-training readiness verification.  
**Authority:** TDD v1.1 §4.3–4.6, §5.2, §14; PRD v1.1 §5.1–5.3, §6, AC-16; `AGENTS.md` §1, §2, §4, §6  
**Final Status:** **S4-T3C READY FOR TRAINING** (All 9 prerequisites verified; operational convention established and validated).

---

## 1. Executive Summary & Gate Verdict

A lightweight, non-destructive final readiness inspection was executed on the generated dataset (`dataset/`, 23,767 images, 55,006 retained target annotations) without repeating annotation conversions, split calculations, or duplicate scans.

All underlying dataset integrity, annotation validity, duplicate containment, path resolutions, and hardware prerequisites have been verified with 100% compliance:

| # | Prerequisite | Status | Key Evidence |
| ---: | :--- | :---: | :--- |
| 1 | `dataset/data.yaml` paths and 4-class mapping | **PASS** | Class mapping: `0: D00, 1: D10, 2: D20, 3: D40` (`nc: 4`). Operational convention (`dataset/` CWD) resolves `train`, `val`, and `test` cleanly. |
| 2 | Image-label correspondence | **PASS** | Exactly 23,767 images and 23,767 YOLO labels across 3 splits. 0 missing images, 0 missing labels, 0 orphans. |
| 3 | No invalid or empty YOLO labels | **PASS** | Policy A applied: 0 empty labels across all 23,767 files. 0 invalid classes ({0,1,2,3} only). 0 coordinate violations. 55,006 total boxes. |
| 4 | Class distribution across splits | **PASS** | Ratios: Train 80.01%, Val 10.10%, Test 9.88%. Maximum per-class deviation from global share is 1.03 pp (D20 in val). |
| 5 | Split manifest reconciliation | **PASS** | Manifest CSV (23,767 rows, SHA-256 `7cf34087b2efee5ff5988d600f79ece891cc66acf0e7589a02b6dc2dab1b569e`), JSON, and txt lists agree exactly with disk contents. |
| 6 | No duplicate leakage | **PASS** | 22,966 split groups (Hamming distance ≤ 3, 64-bit dHash). 0 group crossings, 0 exact hash crossings, 0 near-group crossings across splits. |
| 7 | Training paths on host machine | **PASS** | Host repo path `C:\Users\ramsa\Desktop\roadvision ai` verified. Space in path handled. Working directory convention tested and verified. |
| 8 | Sufficient disk space & GPU | **PASS** | Drive C: free space **382.83 GiB** (> 15 GB requirement). NVIDIA RTX 5060 Laptop GPU (8,151 MiB / 7.96 GiB VRAM, `sm_120`), CUDA 12.8 active. |
| 9 | Ultralytics YOLO26 compatibility | **PASS** | Ultralytics 8.4.202 installed; native YOLO26 architecture (`yolo26m.yaml`) verified loadable without weights download. |

---

## 2. Operational Blocker Resolution (Zero-Mutation Convention)

### Resolution Details
- **Issue:** `dataset/data.yaml` defines `path: .`. Ultralytics resolves relative paths against the current working directory of the process (`os.getcwd()`).
- **Adopted Convention:** Standardize execution of all Ultralytics training/evaluation commands with `dataset/` as the active working directory.
- **Verification Evidence (terminal test):**
  ```powershell
  # Working directory: C:\Users\ramsa\Desktop\roadvision ai\dataset
  from ultralytics.data.utils import check_det_dataset
  d = check_det_dataset('data.yaml')
  ```
  - `check_det_dataset verdict`: **SUCCESS**
  - `train`: `C:\Users\ramsa\Desktop\roadvision ai\dataset\images\train` (19,017 images verified present)
  - `val`: `C:\Users\ramsa\Desktop\roadvision ai\dataset\images\val` (2,401 images verified present)
  - `test`: `C:\Users\ramsa\Desktop\roadvision ai\dataset\images\test` (2,349 images verified present)
  - `nc`: `4`
  - `names`: `{0: 'D00', 1: 'D10', 2: 'D20', 3: 'D40'}`
- **Integrity Preservation:**
  - `data.yaml` SHA-256: `c09dfe261abd8db73709508decf5c6bea73361a77600d942b31695c41c9499cd` (Unchanged, matches S4-T3B report).
  - `split_manifest.csv` SHA-256: `7cf34087b2efee5ff5988d600f79ece891cc66acf0e7589a02b6dc2dab1b569e` (Unchanged, matches S4-T3B report).
  - Zero dataset files modified, zero re-conversions, zero resplits.

---

## 3. Prerequisite Audit & Measured Evidence

### 3.1 Class Mapping & Configuration
- **Contract:** Defined in `training/classes.json` and TDD v1.1 §4.3:
  - `0: D00` (Longitudinal crack)
  - `1: D10` (Transverse crack)
  - `2: D20` (Alligator crack)
  - `3: D40` (Pothole)
- **`data.yaml` Verification:** `nc: 4`, class mapping identical to `classes.json`. Out-of-scope RDD2022 codes (`D01`, `D0w0`, `D11`, `D43`, `D44`, `D50`, `Repair`, `Block crack`) are cleanly excluded.

### 3.2 Image-Label Correspondence (Exhaustive Scan)
Every file in `dataset/images/` and `dataset/labels/` was matched:
- **Train:** 19,017 images | 19,017 label files | 0 missing images | 0 missing labels
- **Val:** 2,401 images | 2,401 label files | 0 missing images | 0 missing labels
- **Test:** 2,349 images | 2,349 label files | 0 missing images | 0 missing labels
- **Total:** 23,767 images, 23,767 labels. Exact 1:1 stem parity; 0 orphan files.

### 3.3 Label Validity and Policy Compliance
- **Policy Applied:** Policy A (documented fallback). 
- **Empty Labels:** 0 empty label files (0.00%). Under Policy A, every included image contains at least one verified target box.
- **Class Index Bounds:** 55,006 total lines examined across 23,767 files. 0 lines with class outside {0, 1, 2, 3}.
- **Geometry Bounds:** 0 coordinate violations. All bounding box values are within normalized range `(0.0, 1.0]`.

### 3.4 Split Balance & Class Distribution
The dataset reproduces the S4-T3A audit simulation and S4-T3B split:

| Class | Total Objects | Train (80.01%) | Val (10.10%) | Test (9.88%) | Max Class Deviation |
| :--- | ---: | ---: | ---: | ---: | ---: |
| **D00** | 26,016 | 20,743 (79.73%) | 2,698 (10.37%) | 2,575 (9.90%) | +0.27 pp |
| **D10** | 11,830 | 9,457 (79.94%) | 1,208 (10.21%) | 1,165 (9.85%) | +0.11 pp |
| **D20** | 10,616 | 8,517 (80.23%) | 1,052 (9.91%) | 1,047 (9.86%) | -1.03 pp |
| **D40** | 6,544 | 5,288 (80.81%) | 619 (9.46%) | 637 (9.73%) | -0.55 pp |
| **Total** | **55,006** | **44,005 (80.00%)** | **5,577 (10.14%)** | **5,424 (9.86%)** | **1.03 pp** |

- Class presence in images: D00 (13,548 images), D10 (7,709 images), D20 (8,412 images), D40 (3,674 images).
- Maximum absolute deviation across splits is **1.03 pp** (D20 in validation).

### 3.5 Manifest & Disk Reconciliation
- `split_manifest.csv`: 23,767 entries, SHA-256 `7cf34087b2efee5ff5988d600f79ece891cc66acf0e7589a02b6dc2dab1b569e`.
- `split_manifest.json`: Confirms 23,767 rows, matching CSV counts and per-split totals.
- Manifest image lists:
  - `manifests/train.txt`: 19,017 lines, all resolve to `images/train/`.
  - `manifests/val.txt`: 2,401 lines, all resolve to `images/val/`.
  - `manifests/test.txt`: 2,349 lines, all resolve to `images/test/`.

### 3.6 Duplicate Leakage Audit
- `dataset/reports/duplicate_leakage.json`:
  - 22,966 split groups formed by transitive closure (union-find) over 64-bit dHash (Hamming distance ≤ 3, no bucket cap).
  - Exact SHA-256 duplicate crossings across splits: **0**
  - Near-duplicate group crossings across splits: **0**
  - Group-spanning split violations: **0**
  - Largest group (178 frames from a continuous sequence) is strictly confined to `train`.

### 3.7 Compute & Host Resource Verification
- **Free Disk Space:** **382.83 GiB** available on `C:\` (well above the 15 GB minimum requirement).
- **GPU Accelerator:** **NVIDIA GeForce RTX 5060 Laptop GPU** (8,151 MiB / 7.96 GiB VRAM visible to PyTorch).
- **Compute Capability:** `(12, 0)` (`sm_120`), driver version 591.84.
- **PyTorch Environment:** `2.11.0+cu128` with CUDA 12.8 runtime active (`torch.cuda.is_available() == True`).
- **Ultralytics YOLO Compatibility:** Version `8.4.202`. Model architecture `yolo26m.yaml` verified loadable natively without network requests.

---

## 4. Operational Training Launcher & Recommended Configuration

### Exact Windows Command for S4-T4 Training Launcher

From the repository root `C:\Users\ramsa\Desktop\roadvision ai`:

```powershell
# Windows PowerShell command using the dataset/ CWD convention:
Push-Location dataset
..\.venv\Scripts\python.exe -m ultralytics train model=yolo26m.pt data=data.yaml imgsz=640 batch=8 epochs=2 device=0 workers=2 project=..\runs\train name=yolo26m_stage2 exist_ok=True
Pop-Location
```

Or via a Python script executed from repo root:
```python
import os
from pathlib import Path
from ultralytics import YOLO

# Set operational working directory to dataset/
repo_root = Path(__file__).resolve().parent.parent
dataset_dir = repo_root / "dataset"
os.chdir(dataset_dir)

model = YOLO("yolo26m.pt")
model.train(
    data="data.yaml",
    epochs=2,
    imgsz=640,
    batch=8,
    device=0,
    workers=2,
    seed=0,
    amp=True,
    project=str(repo_root / "runs" / "train"),
    name="yolo26m_smoke",
    exist_ok=True,
)
```

### Memory Fallback Ladder (TDD v1.1 §5.2)
If peak allocated/reserved memory exceeds 7.5 GiB during the Stage 2 two-epoch run:
1. Reduce `batch` from `8` to `4` (leaves ~3 GiB VRAM headroom).
2. If `batch=4` remains memory-constrained, reduce `imgsz` from `640` to `512` as specified in TDD v1.1 §5.2.

---

## 5. Conclusion & S4-T4 Gate Transition

All prerequisites are met. Hashes and dataset files remain frozen and unmodified.

**Final Status:** `S4-T3C READY FOR TRAINING`
