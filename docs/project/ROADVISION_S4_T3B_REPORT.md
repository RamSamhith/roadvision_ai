# ROADVISION AI — S4-T3B DATASET PREPARATION REPORT
## Pascal VOC → YOLO conversion, Q-03 filtering, duplicate-aware 80/10/10 split

**Date:** 6 November 2026
**Owner:** Ram (AI/CV workstream)
**Task:** S4-T3B — build the reproducible dataset from `data/raw/RDD2022` and verify it end to end.
**Authority:** TDD v1.1 §4.3–4.6 and Appendix B; PRD v1.1 §5.1–5.3 and AC-16; `AGENTS.md` §1, §4, §6
**Status:** **COMPLETE.** Dataset generated and verified: **PASS** (8/8 checks, 0 failures).

**What changed:** new code under `training/`, a generated `dataset/` tree (~4.78 GB, 47,550 files),
and evidence reports under `dataset/reports/`. No raw dataset file was modified. No model was
trained. Nothing was committed or pushed.

---

## 1. Scope compliance

| Restriction | Compliance |
| :--- | :--- |
| Work only in Ram's CV/data area | **Yes** — only `training/`, `dataset/`, `docs/project/` changed |
| Do not modify Shakib's backend/API/frontend | **Yes** — no `backend/` or `frontend/` file touched |
| Do not modify original dataset files | **Yes** — all source hashes and the raw mtime ceiling unchanged (§8) |
| Do not convert in place | **Yes** — labels are written only under `dataset/labels/` |
| Do not download model weights / train | **Yes** — no Ultralytics import, no weight, no GPU run |
| Do not change dependencies | **Yes** — only the existing venv was used (Python 3.11.9) |
| Do not commit or push | **Yes** — the work remains uncommitted (single commit `0f977c7`) |
| Use the venv interpreter | **Yes** — every run used `.venv\Scripts\python.exe` |

---

## 2. Deliverables

### Code (`training/`)

| File | Role |
| :--- | :--- |
| `classes.json` | Four-class contract: `0=D00`, `1=D10`, `2=D20`, `3=D40`; records out-of-scope codes observed in RDD2022 |
| `convert_annotations.py` | Canonical VOC parser, validation rules, YOLO label writer, CLI (`--check-classes`) |
| `split_dataset.py` | Deterministic group-aware split (`StratifiedGroupKFold`, seed 42) |
| `prepare_dataset.py` | Full pipeline: parse → filter → split → copy → manifests → reports; `--dry-run`, `--reports-only`, `--copy-mode` |
| `verify_dataset.py` | Consolidated verifier; `--repro-dir` compares a complete second run |

### Generated dataset (`dataset/`)

```
dataset/
  images/{train,val,test}/        23,767 images
  labels/{train,val,test}/        23,767 YOLO label files
  data.yaml                       nc=4, class names, three split paths
  manifests/
    split_manifest.csv            authoritative 23,767-row manifest
    split_manifest.json           manifest hashes and split stats
    {train,val,test}.txt          per-split image lists
  reports/
    conversion_summary.json       parse counts, class totals, audit reconciliation
    class_distribution.json       split shares and per-class deviation
    exclusion_report.json         all 23,653 excluded images with reasons
    object_exclusions.json        all 10,706 excluded objects with reasons
    duplicate_leakage.json        zero-crossing evidence
    policy_decision.json          Q-03/Q-04 decisions and V2 status
    source_integrity.json         XML tree digest and raw mtime ceiling
    per_image_index.json          per-source annotation summary
    dataset_report.json           consolidated dataset record
    verification.json             authoritative PASS/FAIL result
```

Regeneration:

```powershell
.\.venv\Scripts\python.exe training\prepare_dataset.py --force
.\.venv\Scripts\python.exe training\verify_dataset.py --dataset dataset
```

---

## 3. Conversion and filtering (Q-03)

**Applied policy: A (documented fallback).** The requested policy is C, but Policy C is gated on the
**V2 visual-inspection sign-off**, which does not exist and could not be closed: the literal V2 sample
is impossible for `China_Drone`, which has only **5** empty XMLs. The V2 gate was **not performed and
is not claimed as ratified**. Policy A was applied as the documented fallback and the reason is
recorded in `policy_decision.json`, `conversion_summary.json` and `dataset_report.json`.

Policy C remains implemented as an option and requires an explicit, complete sign-off file:

```powershell
.\.venv\Scripts\python.exe training\prepare_dataset.py --policy C --v2-signoff <v2_gate.json> --force
```

### Measured corpus

| Item | Count |
| :--- | ---: |
| Images in `data/raw/RDD2022` | 47,420 |
| Pascal VOC XML files | 38,385 |
| Annotated objects (all classes) | 65,712 |
| Images without XML (all official `*/test/`) | 9,035 |
| Policy A pool (≥1 retained target box) | **23,767** |
| Policy C pool (A + verified-empty), not used | 35,119 |

### Retained target objects

| Class | ID | Objects | Images |
| :--- | ---: | ---: | ---: |
| D00 | 0 | 26,016 | 13,548 |
| D10 | 1 | 11,830 | 7,709 |
| D20 | 2 | 10,616 | 8,412 |
| D40 | 3 | 6,544 | 3,674 |
| **Total** | | **55,006** | **23,767** |

### Exclusions (nothing is silently dropped)

| Reason | Images |
| :--- | ---: |
| No annotation, official test (`no_annotation_official_test`) | 9,035 |
| Empty XML, excluded by Policy A (`empty_annotation_excluded_policy_a`) | 11,724 |
| Out-of-scope classes only (`out_of_scope_only`) | 2,894 |
| **Total excluded** | **23,653** |

| Object exclusion | Count |
| :--- | ---: |
| Out-of-scope class (never relabelled) | 10,705 |
| Degenerate target box (< 1 px) | 1 |
| **Total excluded objects** | **10,706** |

- **Background treatment:** Policy A includes **no** background-only images. Policy C would include
  11,352 verified-empty images with empty label files.
- Target object reconciliation: 55,007 target objects → 55,006 retained → 1 degenerate excluded.
- 0 missing object names, 0 unknown class codes, 0 clipped boxes, 0 XML/image size mismatches.
- 372 empty XMLs were flagged by duplicate evidence; under Policy A they remain excluded and are
  named individually in `exclusion_report.json`.

---

## 4. Split (Q-04)

| Parameter | Value |
| :--- | :--- |
| Duplicate evidence | `data/reports/audit/duplicate_groups.json` (S4-T3A, 64-bit dHash, Hamming ≤ 3) |
| Grouping | Union-find transitive closure over image hashes; **no bucket cap**; groups never broken |
| Splitter | `StratifiedGroupKFold(n_splits=10, shuffle=True, random_state=42)` |
| Fold assignment | `folds[0]=test`, `folds[1]=val`, `folds[2–9]=train` |
| Stratification label | Rarest retained class present in the group |
| Exact duplicates | SHA-256 over raw bytes; also constrained to one split |

| Split | Images | Share | Groups | Objects |
| :--- | ---: | ---: | ---: | ---: |
| train | 19,017 | 80.01% | 18,372 | 44,005 |
| val | 2,401 | 10.10% | 2,297 | 5,577 |
| test | 2,349 | 9.88% | 2,297 | 5,424 |
| **Total** | **23,767** | **100%** | **22,966** | **55,006** |

Per-class maximum absolute deviation from the global share is **1.03 pp** (D20 in val). The split
reproduces the S4-T3A audit simulation exactly (pool, groups, per-split images, objects and class
counts all reconcile; verified in `dataset_report.json` → `reconciliation`).

---

## 5. Verification evidence

Command: `training/verify_dataset.py --dataset dataset --repro-dir dataset_repro`

**Verdict: PASS — 8/8 checks passed, 0 failures.**

| # | Check | Result | Key evidence |
| ---: | :--- | :--- | :--- |
| 1 | Classes / `data.yaml` | PASS | `nc=4`, names `[D00,D10,D20,D40]`, three split paths |
| 2 | Image/label correspondence | PASS | 23,767 images, 23,767 labels, one-to-one, no orphans |
| 3 | YOLO format and boxes | PASS | 55,006 lines, 0 invalid class IDs, 0 box violations, 0 empty labels |
| 4 | Conversion and exclusions | PASS | Independent XML re-scan matches every audit count; all 23,653 exclusions have valid reasons |
| 5 | Duplicate leakage | PASS | 22,966 split groups, 0 group crossings, 0 exact-hash crossings, 0 near-group violations |
| 6 | Manifest reconciliation | PASS | CSV ↔ JSON ↔ split lists ↔ reports agree on images, objects and classes |
| 7 | Determinism | PASS | In-memory re-run identical; full second run identical (labels + images + reports) |
| 8 | Original-data integrity | PASS | 38,385 XMLs re-hashed; 245/245 sampled source images unchanged; no raw file newer than pipeline start |

### Determinism

- Manifest SHA-256: `7cf34087b2efee5ff5988d600f79ece891cc66acf0e7589a02b6dc2dab1b569e` (identical in both runs).
- A second complete pipeline run was built into `dataset_repro/` using hardlinks and compared:
  - 23,767 label files identical.
  - 23,767 image names and sizes identical.
  - `split_manifest.csv`, `split_manifest.json`, `data.yaml`, per-split lists and comparable reports identical.
- The temporary `dataset_repro/` comparison tree was removed after the evidence was captured; it is
  not a deliverable. `dataset/reports/verification.json` retains the full-run result.

### Original data integrity

- XML tree digest: `535c930d18013a06b89c358ebdbf149325c5bede719aef892bffb2a0e554e89e`
  over 38,385 files (24,718,784 bytes).
- Raw tree mtime ceiling unchanged at `2026-11-05T02:17:30Z`; no raw file is newer than the pipeline start.
- Source images are covered by the pre-existing S4-T3A hash cache; the verifier re-hashed a
  deterministic 245-image country-stratified sample (134 of them also present in the dataset, and all
  dataset copies matched their source hash).

---

## 6. Limitations and honest caveats

1. **Policy C is not active.** The V2 visual-inspection gate is **not closed**; Policy A was applied
   as fallback. Any downstream result must be described as using Policy A, not Policy C. The 11,352
   verified-empty candidate images are not in the dataset.
2. **Policy A pool is official-train only.** All 9,035 unlabelled images are official `*/test/`
   images, so no official test image enters the pool. This is intentional (TDD §4.4) but means the
   dataset does not exploit unlabelled test imagery.
3. **80/10/10 is approximate.** Groups are never broken to force exact percentages; actual shares are
   80.01 / 10.10 / 9.88.
4. **Background images are absent.** Policy A cannot measure or tune the false-positive rate against
   background-only imagery; that evidence only exists under Policy C.
5. **Verification is a sample for image bytes.** XMLs are hashed exhaustively; image content is
   checked against the cached hashes for a 245-image sample (plus image sizes for all 23,767 files).
6. **`dataset/` is git-ignored.** The binary dataset is not tracked; the reproducible code, manifests
   and reports are the source of truth.
7. **No training has been run.** No mAP, precision, recall or latency numbers exist yet, and none are
   claimed here.

---

## 7. Next step

**S4-T3C — final dataset gate.** Confirm:
- the dataset record and `data.yaml` are accepted;
- the Policy A fallback is acceptable for the first training cycle, or a V2 sign-off is produced so
  Policy C can be regenerated;
- split disjointness and exclusion evidence (already machine-verified) are accepted as the gate
  evidence.

After that gate, **S4-T4 (training)** can start against `dataset/data.yaml`.
