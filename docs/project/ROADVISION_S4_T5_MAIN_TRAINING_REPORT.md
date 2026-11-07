# ROADVISION AI — S4-T5 MAIN TRAINING REPORT
## YOLO26m 50 Cumulative Epochs Training Execution & Assessment

- **Date:** 7 November 2026
- **Task:** S4-T5 — Main YOLO26m Training Run (50 Cumulative Epochs)
- **Authority:** TDD v1.1 §8, §14; PRD v1.1; `ROADVISION_S4_T4_BASELINE_REPORT.md`
- **Model Architecture:** YOLO26m (`ultralytics.models.yolo.detect.DetectionModel`, 20.35M params, 68.1 GFLOPs fused)
- **Starting Weights:** S4-T4 Stage B Checkpoint (`runs/train/yolo26m_s4_t4_pilot/weights/last.pt`, SHA-256: `35a6b0c6198f3c7e7b8c2ec1736b043977dc819f7e719114f0896faef0736c4b`)
- **Status:** **S4-T5 MAIN TRAINING COMPLETE — 50 CUMULATIVE EPOCHS REACHED**

---

## 1. Executive Summary

| Parameter | S4-T4 Pilot Baseline | S4-T5 Main Training | Delta / Outcome |
| :--- | :--- | :--- | :--- |
| **Cumulative Epochs** | 12 (2 Stage A + 10 Stage B) | **50 Cumulative** (12 Pilot + 38 Additional) | **+38 Epochs (Target Reached)** |
| **Execution Duration** | 1h 35m 31s (Stage B) | **6h 33m 50s (23,630.46 s)** | **Complete overnight execution** |
| **Batch Size & Image Size** | Batch 8, 640×640 | **Batch 8, 640×640** | **Preserved verified pilot config** |
| **Peak GPU VRAM** | 7,017 MB (86.1% capacity) | **7,515 MB (92.2% capacity)** | **636 MB safety headroom maintained** |
| **Average GPU Utilization** | 87.0% | **86.3%** | **Sustained compute saturation** |
| **Peak GPU Temperature** | 89.0°C | **80.0°C (Average: 71.0°C)** | **Optimal thermal management** |
| **Validation Precision (P)** | 0.589 | **0.682** | **+9.3 percentage points (+15.8%)** |
| **Validation Recall (R)** | 0.517 | **0.574** | **+5.7 percentage points (+11.0%)** |
| **Validation mAP@50** | 0.536 | **0.630** | **+9.4 percentage points (+17.5%)** |
| **Validation mAP@50-95** | 0.262 | **0.324** | **+6.2 percentage points (+23.7%)** |
| **Primary Model Checkpoint** | `runs/train/yolo26m_s4_t4_pilot/weights/best.pt` | `runs/train/yolo26m_s4_t5_main_50ep/weights/best.pt` | **44.0 MB (SHA: `1BC4128...`)** |
| **Final State Checkpoint** | `runs/train/yolo26m_s4_t4_pilot/weights/last.pt` | `runs/train/yolo26m_s4_t5_main_50ep/weights/last.pt` | **44.0 MB (SHA: `3EC4798...`)** |

---

## 2. Checkpoint Continuation Protocol

### 2.1 Inspection of Starting Checkpoint
Prior to training, `runs/train/yolo26m_s4_t4_pilot/weights/last.pt` was inspected via PyTorch inspection scripts:
- **Recorded Epoch:** `epoch: -1`
- **Optimizer / Scaler State:** `optimizer: None` (Ultralytics strips optimizer and scheduler states upon successful run completion to minimize footprint).
- **Weights Integrity:** Model structure intact with 20,352,536 parameters across 130 fused layers, correctly mapped to 4 RoadVision classes (`{0: 'D00', 1: 'D10', 2: 'D20', 3: 'D40'}`).

### 2.2 Continuation Method Selection
Because `last.pt` from the pilot was a completed run artifact without an active optimizer state dictionary, **Method 2** was executed:
1. Initialized a new training run from `runs/train/yolo26m_s4_t4_pilot/weights/last.pt`.
2. Configured the run for **exactly 38 additional epochs**, guaranteeing that cumulative epochs equal exactly **12 + 38 = 50 cumulative epochs**.
3. Preserved all previous Stage A and Stage B checkpoints, directories, and telemetry logs untouched.
4. Set periodic checkpointing (`save_period=5`) to safeguard training progress against power or system interruptions.

---

## 3. Training Configuration & Hyperparameters

The training configuration strictly adopted the empirical settings verified during S4-T4 without arbitrary modification:

| Hyperparameter | Value | Rationale & Authority |
| :--- | :--- | :--- |
| **Architecture** | YOLO26m | TDD v1.1 §8; PRD v1.1 |
| **Input Resolution** | 640×640 (`imgsz=640`) | Preserves multi-scale feature pyramids and 8.4 ms real-time inference |
| **Batch Size** | 8 | Optimal saturation of 8 GB VRAM with 636 MB safety margin |
| **Epochs** | 38 additional (50 cumulative) | Bridges 12-epoch pilot to 50-epoch target |
| **Optimizer** | AdamW (auto-selected) | `momentum=0.937`, `weight_decay=0.0005` |
| **Initial Learning Rate (`lr0`)** | 0.01 (warmup bias `0.1` for 3 epochs) | Standard Ultralytics decay schedule |
| **Loss Weights** | `box=7.5`, `cls=0.5`, `dfl=1.5` | Detection loss formulation |
| **Augmentation** | `mosaic=1.0`, `close_mosaic=10`, `hsv_h=0.015`, `hsv_s=0.7`, `hsv_v=0.4`, `fliplr=0.5` | Standard spatial and photometric augmentations; mosaic disabled for final 10 epochs |
| **Precision** | AMP (FP16 / Tensor Cores) | RTX 5060 Blackwell tensor saturation |
| **Hardware Device** | CUDA Device 0 | NVIDIA GeForce RTX 5060 Laptop GPU (8,151 MiB) |
| **Dataloader Workers** | 2 | Zero I/O bottleneck on local NVMe SSD; no CPU thread thrashing |
| **Working Directory** | `dataset/` | Resolves `data.yaml` relative paths without modifying manifests |
| **Checkpoints Saved** | `best.pt`, `last.pt`, `epoch0.pt`, `epoch5.pt`, `epoch10.pt`, `epoch15.pt`, `epoch20.pt`, `epoch25.pt`, `epoch30.pt`, `epoch35.pt` | Periodic resilience checkpoints every 5 epochs |

---

## 4. Hardware Telemetry & Runtime Metrics

Continuous telemetry was recorded every 2.0 seconds via `HardwareMonitor` querying `nvidia-smi` into `runs/train/s4_t5_hw_monitor.csv` (11,500 total telemetry samples recorded).

| Telemetry Metric | Measured Value | Operational Assessment |
| :--- | :--- | :--- |
| **Total Wall Clock Time** | 23,630.46 s (6.56 hours) | Within estimated ~6.0 hour projection (~618 s / epoch average) |
| **Peak GPU VRAM Usage** | 7,515.0 MB (92.2% of 8,151 MB) | 636 MB of unfragmented headroom; zero OOM faults |
| **Average GPU VRAM Usage** | 6,978.3 MB | Consistent working allocation throughout all epochs |
| **Peak GPU Temperature** | 80.0°C | Well below thermal throttling thresholds (90°C) |
| **Average GPU Temperature** | 71.0°C | Dual-fan cooling on ROG Zephyrus G14 maintained thermal stability |
| **Average GPU Utilization** | 86.3% | Compute saturated with minimal dataloader wait times |
| **Peak GPU Utilization** | 100.0% | Achieved during forward-backward tensor contractions |

---

## 5. Training Loss & Metric Progression (38 Additional Epochs)

The following table records the epoch-by-epoch loss and validation progression across the 38-epoch run (representing cumulative epochs 13 through 50):

| S4-T5 Epoch | Cumul. Epoch | Step Time (s) | Train Box Loss | Train Cls Loss | Val Box Loss | Val Cls Loss | Precision | Recall | mAP@50 | mAP@50-95 |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | 13 | 649.2 | 1.8942 | 2.2735 | 1.7867 | 1.9272 | 0.5438 | 0.4431 | 0.4551 | 0.2140 |
| 2 | 14 | 587.7 | 1.8947 | 2.2480 | 1.8321 | 2.0555 | 0.5013 | 0.4125 | 0.4036 | 0.1792 |
| 3 | 15 | 577.9 | 1.9222 | 2.3184 | 1.8850 | 2.1345 | 0.4609 | 0.4235 | 0.3897 | 0.1749 |
| 4 | 16 | 575.2 | 1.9686 | 2.3845 | 1.8685 | 2.0889 | 0.5170 | 0.4122 | 0.4175 | 0.1855 |
| 5 | 17 | 576.8 | 1.9394 | 2.3324 | 1.7947 | 2.0106 | 0.5073 | 0.4418 | 0.4274 | 0.1962 |
| 6 | 18 | 612.9 | 1.9244 | 2.2779 | 1.7873 | 1.9141 | 0.5016 | 0.4798 | 0.4545 | 0.2154 |
| 7 | 19 | 663.8 | 1.9145 | 2.2395 | 1.7904 | 1.9187 | 0.5408 | 0.4750 | 0.4743 | 0.2221 |
| 8 | 20 | 972.2 | 1.8992 | 2.1959 | 1.7853 | 1.8575 | 0.5651 | 0.4755 | 0.4845 | 0.2312 |
| 9 | 21 | 831.3 | 1.8870 | 2.1767 | 1.7817 | 1.8475 | 0.5554 | 0.4766 | 0.4868 | 0.2277 |
| 10 | 22 | 637.1 | 1.8817 | 2.1263 | 1.7641 | 1.8227 | 0.5683 | 0.4803 | 0.5021 | 0.2376 |
| 11 | 23 | 595.6 | 1.8648 | 2.1002 | 1.7621 | 1.8012 | 0.5945 | 0.4983 | 0.5247 | 0.2519 |
| 12 | 24 | 575.3 | 1.8643 | 2.0916 | 1.7377 | 1.7721 | 0.5856 | 0.4950 | 0.5161 | 0.2515 |
| 13 | 25 | 583.1 | 1.8512 | 2.0636 | 1.7522 | 1.6843 | 0.6027 | 0.5097 | 0.5375 | 0.2617 |
| 14 | 26 | 579.6 | 1.8436 | 2.0164 | 1.7231 | 1.6906 | 0.5974 | 0.4996 | 0.5407 | 0.2651 |
| 15 | 27 | 586.4 | 1.8359 | 2.0033 | 1.7220 | 1.6633 | 0.6085 | 0.5181 | 0.5512 | 0.2702 |
| 16 | 28 | 586.1 | 1.8191 | 1.9931 | 1.7074 | 1.6420 | 0.6104 | 0.5297 | 0.5594 | 0.2755 |
| 17 | 29 | 591.7 | 1.8139 | 1.9487 | 1.7067 | 1.6241 | 0.6152 | 0.5445 | 0.5705 | 0.2805 |
| 18 | 30 | 608.1 | 1.7991 | 1.9201 | 1.6947 | 1.5992 | 0.6175 | 0.5307 | 0.5723 | 0.2872 |
| 19 | 31 | 607.8 | 1.7978 | 1.9016 | 1.6850 | 1.5823 | 0.6420 | 0.5352 | 0.5846 | 0.2957 |
| 20 | 32 | 606.9 | 1.7845 | 1.8633 | 1.6890 | 1.5519 | 0.6544 | 0.5364 | 0.5878 | 0.2947 |
| 21 | 33 | 607.8 | 1.7765 | 1.8452 | 1.6714 | 1.5459 | 0.6574 | 0.5321 | 0.5879 | 0.2986 |
| 22 | 34 | 608.2 | 1.7698 | 1.8247 | 1.6801 | 1.5223 | 0.6585 | 0.5427 | 0.5989 | 0.3057 |
| 23 | 35 | 607.6 | 1.7527 | 1.8081 | 1.6763 | 1.5152 | 0.6650 | 0.5497 | 0.6015 | 0.3033 |
| 24 | 36 | 608.9 | 1.7418 | 1.7722 | 1.6675 | 1.5058 | 0.6524 | 0.5587 | 0.6068 | 0.3065 |
| 25 | 37 | 608.6 | 1.7377 | 1.7659 | 1.6590 | 1.5019 | 0.6617 | 0.5639 | 0.6117 | 0.3112 |
| 26 | 38 | 608.1 | 1.7331 | 1.7495 | 1.6661 | 1.4924 | 0.6537 | 0.5652 | 0.6107 | 0.3128 |
| 27 | 39 | 607.8 | 1.7219 | 1.7177 | 1.6588 | 1.4731 | 0.6665 | 0.5630 | 0.6181 | 0.3154 |
| 28 | 40 | 607.8 | 1.7158 | 1.7031 | 1.6543 | 1.4654 | 0.6628 | 0.5679 | 0.6171 | 0.3174 |
| 29 | 41* | 614.4 | 1.6776 | 1.5178 | 1.6582 | 1.4593 | 0.6632 | 0.5735 | 0.6224 | 0.3187 |
| 30 | 42 | 604.2 | 1.6650 | 1.4703 | 1.6603 | 1.4463 | 0.6800 | 0.5720 | 0.6267 | 0.3210 |
| 31 | 43 | 604.8 | 1.6441 | 1.4465 | 1.6628 | 1.4318 | 0.6884 | 0.5700 | 0.6267 | 0.3218 |
| 32 | 44 | 604.6 | 1.6390 | 1.4162 | 1.6601 | 1.4434 | 0.6944 | 0.5602 | 0.6267 | 0.3219 |
| 33 | 45 | 604.1 | 1.6247 | 1.3893 | 1.6651 | 1.4377 | 0.6853 | 0.5740 | 0.6293 | 0.3239 |
| 34 | 46 | 604.5 | 1.6066 | 1.3516 | 1.6697 | 1.4239 | 0.6813 | 0.5731 | 0.6288 | 0.3243 |
| 35 | 47 | 604.8 | 1.5944 | 1.3275 | 1.6689 | 1.4324 | 0.6822 | 0.5711 | 0.6281 | 0.3230 |
| 36 | 48 | 604.6 | 1.5796 | 1.3112 | 1.6687 | 1.4335 | 0.6805 | 0.5725 | 0.6287 | 0.3231 |
| 37 | 49 | 604.2 | 1.5676 | 1.2927 | 1.6716 | 1.4316 | 0.6918 | 0.5695 | 0.6295 | 0.3224 |
| 38 | 50 | 604.5 | 1.5572 | 1.2699 | 1.6766 | 1.4286 | 0.6842 | 0.5710 | 0.6286 | 0.3225 |

*\*Note: Mosaic augmentation disabled for the final 10 epochs (epochs 29–38 / cumulative 41–50) per standard Ultralytics close-mosaic schedule.*

---

## 6. Final Validation & Per-Class Performance Breakdown

Final validation was conducted on the preserved validation split (2,401 images, 5,577 ground-truth damage instances) using the optimal checkpoint `best.pt`:

### 6.1 Per-Class Metrics Comparison

| Class ID | Damage Class | S4-T4 Precision | S4-T5 Precision | S4-T4 Recall | S4-T5 Recall | S4-T4 mAP@50 | S4-T5 mAP@50 | S4-T4 mAP50-95 | S4-T5 mAP50-95 |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **All** | **Overall** | **0.589** | **0.682** *(+9.3 pp)* | **0.517** | **0.574** *(+5.7 pp)* | **0.536** | **0.630** *(+9.4 pp)* | **0.262** | **0.324** *(+6.2 pp)* |
| 0 | `D00` (Longitudinal Crack) | 0.592 | **0.684** *(+9.2 pp)* | 0.542 | **0.561** *(+1.9 pp)* | 0.550 | **0.627** *(+7.7 pp)* | 0.287 | **0.348** *(+6.1 pp)* |
| 1 | `D10` (Transverse Crack) | 0.568 | **0.656** *(+8.8 pp)* | 0.532 | **0.585** *(+5.3 pp)* | 0.522 | **0.607** *(+8.5 pp)* | 0.243 | **0.305** *(+6.2 pp)* |
| 2 | `D20` (Alligator Crack) | 0.659 | **0.738** *(+7.9 pp)* | 0.578 | **0.649** *(+7.1 pp)* | 0.634 | **0.733** *(+9.9 pp)* | 0.329 | **0.401** *(+7.2 pp)* |
| 3 | `D40` (Pothole) | 0.537 | **0.649** *(+11.2 pp)* | 0.417 | **0.501** *(+8.4 pp)* | 0.438 | **0.554** *(+11.6 pp)*| 0.188 | **0.243** *(+5.5 pp)* |

### 6.2 Key Takeaways per Class
1. **`D40` (Pothole) Underwent Massive Gains:** mAP@50 surged from **0.438 to 0.554 (+11.6 percentage points)**, and recall expanded from **0.417 to 0.501 (+8.4 percentage points)**. Extended training allowed the model to discover discriminative localized features despite fewer instances in the dataset.
2. **`D20` (Alligator Crack) Achieved Exceptional Accuracy:** Reached **0.733 mAP@50** and **0.401 mAP50-95** with **73.8% precision** and **64.9% recall**, demonstrating that complex interconnected cracking patterns are learned with high fidelity by YOLO26m's multi-scale receptive fields.
3. **`D00` & `D10` Stabilized Above 0.60 mAP@50:** Longitudinal cracks reached **0.627 mAP@50** and transverse cracks reached **0.607 mAP@50**, providing balanced detection across orientation variations.

### 6.3 Inference Latency Profile
- **Preprocess:** 1.28 ms
- **Inference:** 12.42 ms (~80.5 FPS)
- **Postprocess (NMS):** 0.94 ms
- **Total Pipeline Latency:** **14.64 ms / frame** (equivalent to ~68.3 FPS on the RTX 5060 Laptop GPU).
- Conforms comfortably with TDD v1.1 §8 real-time dashcam inference specifications (>30 FPS).

---

## 7. Analysis: Is Further Training to 100 Epochs Worthwhile?

Section 7 of the mission mandate requires an empirical determination of whether to proceed to 100 epochs or retain the 50-epoch checkpoint.

### 7.1 Empirical Evidence from S4-T5 Curves
1. **Convergence of Validation Loss:**
   - `val/cls_loss` dropped rapidly from 1.927 (epoch 13) to 1.446 (epoch 42), but then leveled off completely between 1.424 and 1.433 during epochs 43 to 50.
   - `val/box_loss` reached its empirical minimum at **1.654** around epoch 40, and showed slight upward drift to **1.677** by epoch 50.
2. **Metric Plateauing:**
   - Over the final 8 epochs (epochs 43 to 50), mAP@50 remained effectively flat:
     - Epoch 43: 0.6267
     - Epoch 44: 0.6267
     - Epoch 45: 0.6293
     - Epoch 46: 0.6288
     - Epoch 47: 0.6281
     - Epoch 48: 0.6287
     - Epoch 49: 0.6295
     - Epoch 50: 0.6286
   - The best fitness checkpoint was reached at epoch 45 / 49 (`mAP50 = 0.630`, `mAP50-95 = 0.324`).
3. **Training Loss Trajectory:**
   - `train/cls_loss` continued to descend (1.470 → 1.270), while `val/cls_loss` ceased declining. This divergence indicates that additional epochs will initiate mild overfitting rather than generalization gains.
4. **Diminishing Returns:**
   - Training for an additional 50 epochs would require another ~8.0 hours of heavy GPU computation with an estimated expected gain of <0.5 to 1.0 mAP percentage points, accompanied by an increased risk of over-fitting on high-frequency road textures.

### 7.2 Formal Recommendation
> [!IMPORTANT]
> **Recommendation: 50 EPOCHS SUFFICIENT.**
> 
> The evidence firmly demonstrates that the model has reached its convergence plateau on the RDD2022 4-class dataset under the current resolution (640×640) and augmentations. Retaining `runs/train/yolo26m_s4_t5_main_50ep/weights/best.pt` is the optimal engineering decision. Additional training to 100 epochs is not recommended as it will yield negligible returns while increasing overfitting risk.

---

## 8. Artifacts & Checkpoints Inventory

All artifacts have been created and preserved in project-local, versioned directories:

- **Run Directory:** `runs/train/yolo26m_s4_t5_main_50ep/`
- **Model Checkpoints:**
  - Best Checkpoint: `runs/train/yolo26m_s4_t5_main_50ep/weights/best.pt` (44.0 MB, SHA-256: `1BC41287DBDBC5EC5793D5D8F14CBA770E9E71E9C9E0CC0188B7146DA592D233`)
  - Last Checkpoint: `runs/train/yolo26m_s4_t5_main_50ep/weights/last.pt` (44.0 MB, SHA-256: `3EC4798AE0F43DEE8A4D9AC75C31603E721FFB50D44207E9572B07FD7C087244`)
  - Periodic Checkpoints: `epoch0.pt`, `epoch5.pt`, `epoch10.pt`, `epoch15.pt`, `epoch20.pt`, `epoch25.pt`, `epoch30.pt`, `epoch35.pt`
- **Plots & Visualizations:**
  - `BoxF1_curve.png`, `BoxP_curve.png`, `BoxPR_curve.png`, `BoxR_curve.png`
  - `confusion_matrix.png`, `confusion_matrix_normalized.png`
  - `results.png`
- **Machine-Readable Metadata:**
  - Comprehensive Training & Val Summary: `runs/s4_t5_summary.json`
  - Epoch-by-Epoch CSV Logs: `runs/train/yolo26m_s4_t5_main_50ep/results.csv`
  - High-Resolution Hardware Telemetry: `runs/train/s4_t5_hw_monitor.csv`
  - Training Execution Script: `training/run_s4_t5_main.py`
- **Preserved Prior Runs:**
  - S4-T4 Memory Test: `runs/train/yolo26m_s4_t4_memory/` (Preserved)
  - S4-T4 Training Pilot: `runs/train/yolo26m_s4_t4_pilot/` (Preserved)

---

## 9. Verification & Completion Status

- [x] **50 cumulative training epochs** reached (12 pilot + 38 additional).
- [x] Best (`best.pt`) and last (`last.pt`) checkpoints verified, checksummed, and preserved.
- [x] Comprehensive validation performed on the 2,401-image validation split (zero test set leakage).
- [x] Overall and per-class metrics recorded and compared against S4-T4 baseline.
- [x] Hardware telemetry logged continuously with zero OOM errors or thermal throttling.
- [x] Analysis of convergence curves completed with a clear recommendation regarding 100 epochs.
- [x] S4-T5 report written to `docs/project/ROADVISION_S4_T5_MAIN_TRAINING_REPORT.md`.
- [x] Zero project files, raw datasets, manifests, backend, API, or frontend files modified or damaged.

**Final Status:** **`S4-T5 MAIN TRAINING COMPLETE — 50 EPOCHS`**

