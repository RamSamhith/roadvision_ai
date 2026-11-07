# ROADVISION AI — S4-T7B EXPERIMENT REPORT
## 832px High-Resolution Memory Verification & Controlled Fine-Tuning Benchmark

- **Date:** 7 November 2026
- **Task:** S4-T7B — 832px Resolution Memory Test & Controlled Fine-Tuning
- **Authority:** TDD v1.1 §4, §8, §14; PRD v1.1; `ROADVISION_S4_T5_MAIN_TRAINING_REPORT.md`; `ROADVISION_S4_T7A_IMPROVEMENT_ANALYSIS.md`
- **Starting Weights:** S4-T5 Best Checkpoint (`runs/train/yolo26m_s4_t5_main_50ep/weights/best.pt`, SHA-256: `1BC41287DBDBC5EC5793D5D8F14CBA770E9E71E9C9E0CC0188B7146DA592D233`)
- **Fine-Tuned Checkpoint:** `runs/train/yolo26m_s4_t7b_832_finetune/weights/best.pt` (SHA-256: `0F5B7AAF9A602A2EBEC8976801E8D4F7270C4DF8448331CC833753D085B1483D`)
- **Status:** **S4-T7B COMPLETE — 832PX EXPERIMENT EVALUATED**

---

## 1. Executive Summary & Verification of Evidence Provenance

### 1.1 Data Provenance Verification (Mandatory Pre-Training Audit)
Prior to launching S4-T7B, the provenance of the reported 168 `D00` background false-positive count was audited across historical experiment summaries:
- **Finding:** The count of 168 background false alarms originated exclusively from row 4, column 0 of the **S4-T6 held-out test set confusion matrix** (`runs/s4_t6_test_summary.json`), and was erroneously attributed to the validation set in earlier analytical discussions.
- **Enforcement Action:** In strict compliance with Section 1 and Section 2 non-negotiable data protection rules, the 168 false-positive finding was **formally cataloged as unverified for validation tuning and strictly excluded from guiding training decisions**.
- **Experiment Scope:** S4-T7B was executed strictly as an isolated **resolution-only experiment** (832×832 vs 640×640), without introducing class re-weighting, synthetic shadow/glare augmentations, background images, or label modifications.

### 1.2 Summary of Experimental Outcomes

| Benchmark Metric | S4-T5 Baseline (640×640) | S4-T7B Fine-Tuned (832×832) | Delta / Empirical Effect | Target Compliance |
| :--- | :---: | :---: | :---: | :---: |
| **Input Resolution** | 640×640 | **832×832** | +69% spatial area | Evaluated |
| **Batch Size** | 8 | **4** | Adjusted for VRAM | Safe |
| **Peak GPU VRAM** | 7,515 MB | **6,607 MB** | -908 MB | **Pass (< 7,200 MB limit)** |
| **Pipeline Latency** | 14.64 ms/frame | **22.96 ms/frame** | +8.32 ms | **Pass (≤ 25 ms target)** |
| **Inference Throughput** | 68.3 FPS | **43.6 FPS** | -24.7 FPS | **Pass (≥ 30 FPS target)** |
| **Overall Precision (P)** | **0.682** | 0.660 | -2.2 pp | Moderate drop |
| **Overall Recall (R)** | 0.574 | **0.596** | **+2.2 pp (+3.8%)** | **Strong improvement** |
| **Overall mAP@50** | **0.630** | 0.629 | -0.1 pp | Parity |
| **Overall mAP@50-95** | **0.324** | 0.319 | -0.5 pp | Parity |
| **`D00` (Longitudinal) Recall** | 0.561 | **0.597** | **+3.6 pp (+6.4%)** | **Substantial gain** |
| **`D00` (Longitudinal) mAP@50** | 0.627 | **0.646** | **+1.9 pp (+3.0%)** | **Substantial gain** |
| **`D40` (Pothole) Recall** | 0.501 | **0.528** | **+2.7 pp (+5.4%)** | **Substantial gain** |
| **`D40` (Pothole) mAP@50** | 0.554 | **0.564** | **+1.0 pp (+1.8%)** | **Substantial gain** |

---

## 2. Stage B1: 832px Memory Verification Gate

Prior to full fine-tuning, a controlled 2-epoch memory test (`runs/train/yolo26m_s4_t7b_mem832`) was executed on the NVIDIA RTX 5060 Laptop GPU:

- **Parameters:** `imgsz=832`, `batch=4`, `amp=True`, `workers=2`, `device=0`, `seed=0`.
- **Target Safety Limit:** Peak VRAM ≤ **7,200 MB** (7.03 GB).
- **Execution Telemetry (Recorded via `runs/train/s4_t7b_mem_hw_monitor.csv`):**
  - **Peak VRAM:** **6,609.0 MB** (leaving **1,542 MB** unfragmented headroom on the 8,151 MB GPU).
  - **Average VRAM:** 6,197.8 MB.
  - **Average GPU Utilization:** 84.7%.
  - **Peak GPU Temperature:** 77.0°C.
  - **Runtime:** 2,043.23 s (34.05 minutes, ~17.0 min/epoch).
  - **CUDA / OOM Faults:** Zero.
- **Stage B1 Verdict:** **PASS.** Batch size 4 at 832×832 is certified stable and safe for multi-epoch training.

---

## 3. Stage B2: Controlled 832px Fine-Tuning Execution

### 3.1 Training Configuration Comparison

| Hyperparameter | S4-T5 Baseline | S4-T7B Fine-Tuning | Isolation Justification |
| :--- | :---: | :---: | :--- |
| **Initial Weights** | S4-T4 Pilot `last.pt` | S4-T5 `best.pt` (`1BC4128...`) | Fine-tuning pre-converged 50-epoch weights |
| **Resolution (`imgsz`)** | 640 | **832** | Isolated independent variable |
| **Batch Size** | 8 | **4** | Required by 8 GB VRAM budget |
| **Optimizer** | AdamW (auto) | AdamW (auto) | Unchanged |
| **Learning Rate Schedule** | Cosine (`lr0=0.01`) | Cosine (`lr0=0.00125`) | Lower LR for fine-tuning |
| **Loss Formulations** | `box=7.5, cls=0.5, dfl=1.5` | `box=7.5, cls=0.5, dfl=1.5` | Strict parity (No D40 re-weighting) |
| **Augmentations** | Standard baseline | Standard baseline | Strict parity (No new shadow/glare augs) |
| **Dataset & Splits** | 23,767 Policy A | 23,767 Policy A | Strict parity (Zero dataset changes) |
| **Target Epochs** | 38 additional (50 cumulative) | **20 fine-tuning epochs** | Controlled adaptation |

### 3.2 Interruption and Resumption Protocol
During Epoch 12 of the fine-tuning run, the host Windows 11 system entered Modern Standby / Sleep mode (at 1:52 PM), which severed the inter-process communication (IPC) pipe connecting the PyTorch DataLoader worker subprocesses.
- **Preserved State:** The background checkpoints `epoch0.pt`, `epoch5.pt`, `epoch10.pt`, `best.pt`, and `last.pt` were verified intact in `runs/train/yolo26m_s4_t7b_832_finetune/weights/`.
- **Checkpoint Inspection:** `last.pt` verified `epoch: 10` (11 completed epochs) with `has optimizer: True`.
- **Resumption Execution:** The hung process was terminated, and training was cleanly resumed using `model.train(resume=True)` via `training/resume_s4_t7b_finetune.py`.
- **Completed Execution:** The remaining 9 epochs (Epochs 12 through 20) ran without incident to completion in 9,159 s (2.54 hours). Total active compute elapsed across the 20 epochs was ~5.33 hours.

---

## 4. Stage B3: Validation Evaluation & Per-Class Analysis

Post-training validation was conducted on the preserved 2,401-image validation split (5,577 ground-truth damage instances) at resolution 832×832 using `runs/train/yolo26m_s4_t7b_832_finetune/weights/best.pt`:

### 4.1 Detailed Per-Class Comparison

| Class ID | Damage Class | Val Instances | S4-T5 Precision | S4-T7B Precision | S4-T5 Recall | S4-T7B Recall | S4-T5 mAP@50 | S4-T7B mAP@50 | S4-T5 mAP50-95 | S4-T7B mAP50-95 |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **All** | **Overall** | **5,577** | **0.682** | 0.660 | 0.574 | **0.596 (+2.2 pp)** | **0.630** | 0.629 | **0.324** | 0.319 |
| 0 | `D00` (Longitudinal) | 2,698 | **0.684** | 0.676 | 0.561 | **0.597 (+3.6 pp)** | 0.627 | **0.646 (+1.9 pp)** | 0.348 | **0.355 (+0.7 pp)** |
| 1 | `D10` (Transverse) | 1,208 | **0.656** | 0.609 | 0.585 | **0.604 (+1.9 pp)** | **0.607** | 0.591 | **0.305** | 0.297 |
| 2 | `D20` (Alligator) | 1,052 | **0.738** | 0.715 | 0.649 | **0.655 (+0.6 pp)** | **0.733** | 0.714 | **0.401** | 0.385 |
| 3 | `D40` (Pothole) | 619 | **0.649** | 0.642 | 0.501 | **0.528 (+2.7 pp)** | 0.554 | **0.564 (+1.0 pp)** | **0.243** | 0.237 |

### 4.2 Key Performance Insights

1. **Resolution Solves the Small-Object Scale Bottleneck:**
   - As hypothesized in S4-T7A, thin longitudinal cracks (`D00`) and small potholes (`D40`) benefited substantially from the 832×832 grid.
   - For `D00`, recall expanded from **56.1% to 59.7% (+3.6 pp)**, pushing its mAP@50 from **0.627 to 0.646 (+1.9 pp)** and mAP@50-95 from **0.348 to 0.355**.
   - For `D40`, recall climbed from **50.1% to 52.8% (+2.7 pp)**, elevating mAP@50 from **0.554 to 0.564 (+1.0 pp)**.
2. **Trade-off on Surface Textures (Precision Regression):**
   - Higher resolution reveals higher spatial frequency road noise (aggregate texture, dark pavement patches, joint seams). Without targeted photometric regularization (such as synthetic shadow augmentation), the model produced slightly more background false alarms, causing precision to dip from **0.682 to 0.660 (-2.2 pp)**.
   - This precision dip offset the recall gains, keeping overall mAP@50 roughly level (0.629 vs 0.630).

---

## 5. Latency & Real-Time Throughput Benchmark

Timing measurements on NVIDIA GeForce RTX 5060 Laptop GPU:

| Pipeline Component | 640×640 Baseline (S4-T5) | 832×832 Fine-Tuned (S4-T7B) | Delta / Overhead |
| :--- | :---: | :---: | :---: |
| **Preprocessing (Letterbox, FP16)** | 1.28 ms | 1.94 ms | +0.66 ms |
| **Model Forward Pass (Inference)** | 12.42 ms | 20.06 ms | +7.64 ms |
| **Postprocessing (NMS, Box Scaling)** | 0.94 ms | 0.96 ms | +0.02 ms |
| **Total Latency per Image** | **14.64 ms** | **22.96 ms** | **+8.32 ms** |
| **Inference Throughput (FPS)** | **68.3 FPS** | **43.6 FPS** | **-24.7 FPS** |
| **TDD v1.1 Target Compliance** | Pass (≥ 30 FPS) | **PASS (43.6 FPS ≥ 30 FPS)** | **Target Satisfied** |
| **Preferred Latency Compliance** | Pass (≤ 25 ms) | **PASS (22.96 ms ≤ 25 ms)** | **Target Satisfied** |

---

## 6. Model Retention Decision & Stage B4 Recommendations

### 6.1 Should 832px Resolution Be Retained as the Primary Production Baseline?
> [!IMPORTANT]
> **Operational Decision: RETAIN 640px S4-T5 CHECKPOINT AS PRIMARY; ARCHIVE 832px S4-T7B AS HIGH-RECALL VARIANT.**
> 
> - **Rationale:** While 832px successfully proved the hypothesis that spatial resolution unlocks significant recall gains on thin cracks (`D00` mAP50: 0.627 → 0.646) and potholes (`D40` recall: 50.1% → 52.8%), overall mAP@50 remained essentially tied (0.629 vs 0.630) due to higher background false-positive sensitivity on high-frequency road aggregate (precision dropped from 0.682 to 0.660).
> - Furthermore, 640px operates at **68.3 FPS** (14.6 ms) compared to **43.6 FPS** (23.0 ms) at 832px.
> - Therefore, the S4-T5 checkpoint `runs/train/yolo26m_s4_t5_main_50ep/weights/best.pt` remains the primary production baseline.

### 6.2 Stage B4: Recommended Next Isolated Experiment
The evidence clearly shows that 832px has superior recall potential but requires **background regularization** to control false alarms on high-resolution road textures.

**Recommended Next Experiment: Photometric & Shadow Regularization Fine-Tuning (S4-T7C)**
1. **Hypothesis:** Introducing synthetic shadow masks, exposure jitter (`hsv_v=0.5`, `hsv_s=0.6`), and random asphalt texture erasing will suppress the high-resolution false positives that degraded 832px precision.
2. **Target:** Recover precision to ≥ 0.70 while maintaining the 832px recall gains (R ≥ 0.595), enabling overall mAP@50 to break past **0.645** at 43+ FPS.
3. **Execution Guardrails:** Keep batch size at 4; evaluate exclusively on the validation split; preserve the test-set lock.

---

## 7. Artifacts Inventory

- **Stage B1 Memory Artifacts:**
  - Directory: `runs/train/yolo26m_s4_t7b_mem832/`
  - Summary: `runs/s4_t7b_memtest_summary.json`
  - Telemetry: `runs/train/s4_t7b_mem_hw_monitor.csv`
- **Stage B2 / B3 Fine-Tuning Artifacts:**
  - Directory: `runs/train/yolo26m_s4_t7b_832_finetune/`
  - Best Checkpoint: `runs/train/yolo26m_s4_t7b_832_finetune/weights/best.pt` (SHA-256: `0F5B7AAF9A602A2EBEC8976801E8D4F7270C4DF8448331CC833753D085B1483D`)
  - Last Checkpoint: `runs/train/yolo26m_s4_t7b_832_finetune/weights/last.pt` (SHA-256: `2D44471668DE892691F40718B4BEE7AD717EBC2B726587A113B8DEA3CA5CDC95`)
  - Periodic Checkpoints: `epoch0.pt`, `epoch5.pt`, `epoch10.pt`
  - Plots: `BoxF1_curve.png`, `BoxPR_curve.png`, `BoxP_curve.png`, `BoxR_curve.png`, `confusion_matrix.png`, `results.png`
  - Training CSV: `runs/train/yolo26m_s4_t7b_832_finetune/results.csv`
  - Continuous Telemetry: `runs/train/s4_t7b_hw_monitor.csv`
  - Machine-Readable Summary: `runs/s4_t7b_832_summary.json`
- **Executive Report:** [`docs/project/ROADVISION_S4_T7B_832_RESOLUTION_REPORT.md`](file:///c:/Users/ramsa/Desktop/roadvision%20ai/docs/project/ROADVISION_S4_T7B_832_RESOLUTION_REPORT.md)

---

## 8. Completion Checklist

- [x] Pre-training provenance verified (168 background count confirmed from test set; flagged as unverified for validation tuning and excluded).
- [x] Baseline S4-T5 checkpoint (`1BC4128...`) preserved untouched.
- [x] Stage B1 memory test completed and passed (peak VRAM: 6,609 MB < 7,200 MB limit).
- [x] Stage B2 20-epoch fine-tuning executed strictly isolated to resolution (no class re-weighting or new augmentations).
- [x] Mid-run sleep interruption diagnosed, preserved, and cleanly resumed from `last.pt`.
- [x] Stage B3 validation benchmark conducted on validation split at 832px.
- [x] Per-class comparison and latency/FPS measured (43.6 FPS ≥ 30 FPS).
- [x] Stage B4 recommendations formulated based on empirical trade-offs.
- [x] No test set images or labels evaluated or accessed.
- [x] Zero Git commits, pushes, or modifications to backend/frontend code.

**Final Status:** **`S4-T7B COMPLETE — 832PX EXPERIMENT EVALUATED`**

