# ROADVISION AI — S4-T2 REPORT
## Decision Ratification and RDD2022 Dataset Acquisition

**Date:** 5 November 2026
**Owner:** Ram (AI/CV workstream)
**Task:** S4-T2 — ratify the four Stage-4 decisions, acquire and verify RDD2022, build `training/inspect_dataset.py`
**Authority:** TDD v1.1 §4.1–§4.3, §3.4; PRD v1.1 §5.2, §5.3, AC-18; `AGENTS.md` §6
**Status:** **ALL GATES PASSED** — decisions ratified, preflight passed, archive downloaded and verified, extraction complete, inspection complete

---

## 1. Scope compliance

| Restriction | Compliance |
| :--- | :--- |
| Only Ram-owned files created or modified | Yes — `training/inspect_dataset.py` (new), `docs/project/OPEN_QUESTIONS.md` (modified), `.gitignore` (modified), this report (new), plus dataset/report artefacts under `data/` |
| Do not modify Shakib-owned API / DB / frontend | Yes — no file under `backend/` or `frontend/` was touched. Those paths carry modification timestamps of 00:20–00:22, before this task began (01:03) |
| Do not install, update or remove dependencies | Yes — no `pip` command was issued. Used only `opencv-python 5.0.0`, `numpy 2.4.6` and the standard library, all already present |
| Do not download pretrained YOLO weights | Yes — verified: 0 `*.pt`/`*.pth`/`*.onnx`/`*.engine` files outside `.venv` |
| Do not start training | Yes — nothing was trained or converted |
| Do not create backend scaffolding | Yes — no backend file created |
| Do not commit or push | Yes — `git status` shows the working tree only; no commit was made |
| Do not modify other projects' settings | Yes — `%APPDATA%\Ultralytics\settings.json` was not opened for writing and not changed |
| Keep dataset files in the approved project data directories | Yes — everything landed under `data\raw\` and `data\reports\` |
| Do not convert annotations or split the dataset | Yes — inspection is strictly read-only; no YOLO label or split file exists |

---

## 2. Part A — Decisions ratified

All four items were recorded in [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md). That file keeps its
existing structure: the individual entries were updated in place (Q-02, A-01, A-03, §8 sign-off)
and one new section, **§5.2 "Stage 4.1 ratified decisions"**, holds the combined table, the chosen
paths and the AC-18 verification method. Nothing was renumbered.

| ID | Ratified decision | Implemented in this task? |
| :--- | :--- | :--- |
| **N-02** | End-to-end NMS-free inference is selected with **`nms=False`**. The deprecated `end2end=` keyword is **never** used in new code. Default `predict()` arguments select the one-to-many branch **with external NMS**. | No — documentation only (backend/model manager is out of scope) |
| **N-09** | Each model instance uses **one inference mode for its entire lifetime**; modes are never switched on the same object. The model manager must build a fresh instance per mode and assert the head at load. | No — documentation only |
| **N-08** | Ultralytics configuration is **project-local**: `YOLO_CONFIG_DIR` is set to `C:\Users\ramsa\Desktop\roadvision ai\.ultralytics` **before** importing Ultralytics; every dataset/weights/runs path passed to Ultralytics is absolute and project-owned; no other project's configuration is modified. | Partially — the paths are documented and `.ultralytics/` is git-ignored; the training/serving processes that set the variable are not written yet |
| **AC-18 policy** | Serving environment sets `YOLO_OFFLINE=1` and disables settings synchronization in the project-local settings file; effective settings are read back and recorded. **An environment variable alone is explicitly not accepted as proof of complete network isolation.** | No — policy ratified; the OS-level socket proof remains outstanding (see §7) |

**Chosen paths (N-08), as recorded in §5.2 of `OPEN_QUESTIONS.md`:**

| Purpose | Absolute path |
| :--- | :--- |
| Ultralytics config dir (`YOLO_CONFIG_DIR`) | `C:\Users\ramsa\Desktop\roadvision ai\.ultralytics` |
| Raw dataset (immutable) | `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022` |
| Preserved archives | `C:\Users\ramsa\Desktop\roadvision ai\data\raw\_archives` |
| Source metadata | `C:\Users\ramsa\Desktop\roadvision ai\data\raw\_meta` |
| Converted labels (later) | `C:\Users\ramsa\Desktop\roadvision ai\data\annotations` |
| Frozen YOLO split (later) | `C:\Users\ramsa\Desktop\roadvision ai\dataset` |
| Model weights | `C:\Users\ramsa\Desktop\roadvision ai\models\weights` |
| Training/validation runs | `C:\Users\ramsa\Desktop\roadvision ai\models\runs` |

**AC-18 verification method recorded (5 steps, all executable):** set `YOLO_CONFIG_DIR` before the
first `import ultralytics` → confirm `ultralytics.utils.SETTINGS_FILE` resolves under it → confirm
`SETTINGS["sync"] is False` → confirm `env_bool("YOLO_OFFLINE") is True` → log all four values.
Step 6 (proving no socket is opened) is **not claimed** anywhere and remains an OS-level test.

The raw evidence for N-02 and N-09 (42 assertions, 0 failures; `end2end` deprecation message;
`backend.end2end` staying `True` across a later default-argument call) is in
[`ROADVISION_S4_T1_REPORT.md`](ROADVISION_S4_T1_REPORT.md) §5.1 and is not re-derived here.

---

## 3. Part B — Acquisition preflight (all checks passed)

### 3.1 Source and version

| Item | Evidence |
| :--- | :--- |
| Official source | DOI `10.6084/m9.figshare.21431547.v1` → `HTTP 202` → `https://figshare.com/articles/dataset/RDD2022_-_The_multi-national_Road_Damage_Dataset_released_through_CRDDC_2022/21431547/1` |
| Listing read from | `https://api.figshare.com/v2/articles/21431547` (the same article's machine-readable listing) |
| Title | *RDD2022 — The multi-national Road Damage Dataset released through CRDDC'2022* |
| Version | `version: 1`; `published_date: 2022-10-29T10:53:29Z`; `modified_date: 2023-05-30T10:01:26Z` |
| Type / licence | `dataset`; **CC BY 4.0** |
| Authors | 20 listed, incl. Deeksha Arya, Hiroya Maeda, Yoshihide Sekimoto, … |
| Research paper | DOI `10.1002/gdj3.260` → *Geoscience Data Journal*, Wiley, published **2024-06-26**, type `journal-article` |

### 3.2 Published file listing and integrity information

Four files are published. All four sizes and MD5 values were taken from the listing, and the three
small files were downloaded in advance to confirm that the served bytes match the listing.

| File | Bytes | Published MD5 | Download-verified |
| :--- | ---: | :--- | :--- |
| `RDD2022_released_through_CRDDC2022.zip` | 13,264,172,619 | `b62bd51d2ffcfaa76c60f234f0cc2bb3` | §4 |
| `File_List_CRDDC_RDD2022.txt` | 3,250,534 | `08993a6e2bca4a841c2f37b526e52d96` | **MD5 match** |
| `Directory_Structure_CRDDC_RDD2022.txt` | 1,161 | `96dadd450b1122b9c798fac54207ea04` | **MD5 match** |
| `label_map.pbtxt` | 127 | `1c2f8cabf4217798538989ebe203db2e` | **MD5 match** |

### 3.3 Size, free space and the 3× rule

| Check | Value | Verdict |
| :--- | :--- | :--- |
| Exact download size | 13,264,172,619 bytes = **12.353 GiB** | established from the listing |
| Free space on `C:` before download | 457,575,120,896 bytes = **426.15 GiB** (first reading); 456,295,600,128 bytes = 424.96 GiB (reading used for the margin) | sufficient |
| Required 3× margin | 39,792,517,857 bytes = **37.06 GiB** | — |
| Achieved margin | 456,295,600,128 / 39,792,517,857 = **11.47×** | **PASS** |
| Sustained throughput probe (50 MiB range request) | 52,428,800 bytes in 6.74 s = **7.42 MB/s** | transfer feasible |

### 3.4 Destination short-path check (Windows-safe)

| Measure | Value |
| :--- | ---: |
| Repository root length | 36 characters (`C:\Users\ramsa\Desktop\roadvision ai`) |
| Longest internal relative path (`RDD2022\China_MotorBike\train\annotations\xmls\China_MotorBike_000001.xml`) | 73 characters |
| Worst-case absolute path (`<repo>\data\raw\` + relative) | **119 characters** |
| `MAX_PATH` headroom | **141 characters** |

The destination chosen is the repository's own `data\raw\` tree rather than a root-level
`C:\rv`, because `AGENTS.md` and the task both require dataset files to stay in the approved
project data directories, and 119 characters leaves ample headroom. The repository directory
contains a space, so any future generated `data.yaml` must quote its `path:` value.

**Preflight verdict: PASS — all five required facts (source, size, integrity information,
free space, short safe paths) were established, so the download was allowed to proceed.**

---

## 4. Part C — Download and integrity verification

### 4.1 Download

| Item | Value |
| :--- | :--- |
| Command | `curl.exe -L --fail --retry 5 --retry-all-errors -C - --write-out … https://ndownloader.figshare.com/files/38030910 -o data\raw\_archives\RDD2022_released_through_CRDDC2022.zip` |
| HTTP result | `http=200` |
| Bytes received | **13,264,172,619** (exactly the published size) |
| Elapsed | `1094.507630` s |
| Mean throughput | `12,118,849` B/s (≈ 11.6 MiB/s) |
| File timestamp | 2026-11-05 01:20:23 local = `2026-11-04T19:50:23Z` |
| Location | `data\raw\_archives\RDD2022_released_through_CRDDC2022.zip` |

### 4.2 Hashes and archive test

| Check | Result |
| :--- | :--- |
| Size vs published | **match** (13,264,172,619) |
| MD5 | `b62bd51d2ffcfaa76c60f234f0cc2bb3` — **matches the published MD5** |
| SHA-256 | `5d230a2941e8f2ac5fbca1a0faddee393314368dd17f9304effc11ec532845b6` |
| `zipfile.testzip()` | **None** (no bad member) — 9.0 s |
| Entries | 7, all `.zip`, stored (compression ratio 1.00) |
| Longest member name | 27 characters (`RDD2022/China_MotorBike.zip`) |
| Duplicate member names | 0 |

### 4.3 Two-stage extraction

The published container is **not** a flat directory tree: it holds one nested ZIP per country, so
extraction had to be done in two stages. This was discovered from `testzip()`/`infolist()` before
any extraction, not assumed.

**Stage 1** — outer container → `data\raw\_archives\RDD2022\` (15.3 s), yielding 7 archives:

| Archive | Bytes | SHA-256 |
| :--- | ---: | :--- |
| `China_Drone.zip` | 160,193,541 | `b7cc335a7704b98e0927e8cee6b94adbd2d97c81c33ef57068d08b3da119f15b` |
| `China_MotorBike.zip` | 192,030,116 | `2acdc8b8527c9b36cce4ba97dfdd5be9090be32f588c31b769a08c1a41c0c274` |
| `Czech.zip` | 257,117,218 | `94c65a4e6cfed187b193ba967f0a2b16bd4287dfe313d0962f3711afce75bf1d` |
| `India.zip` | 526,709,145 | `28eab0aa85638855e1907e63b175be2305a0accd018c54603037d3fb8cab963a` |
| `Japan.zip` | 1,072,598,857 | `76efe7acb4642da283891611670dac7e8866a1b1dd145b8a1540fd440b1328f7` |
| `Norway.zip` | 10,611,186,814 | `58f75bb91a90c866f716a40705b2b27b171869c715458cc70b3786e8be80b0b9` |
| `United_States.zip` | 444,335,958 | `597e8bcf1ffbe80d6c8295fbf99ebab5651c9e4efe961f9d38a9ed4ad10b957e` |

**Stage 2** — each nested archive CRC-checked with `zipfile.testzip()` and then extracted into
`data\raw\RDD2022\` (166.3 s total). **7/7 archives passed CRC; `failures: []`.**

| Archive | Entries | JPG | XML | CRC s | Extract s |
| :--- | ---: | ---: | ---: | ---: | ---: |
| China_Drone | 4,806 | 2,401 | 2,401 | 0.7 | 3.4 |
| China_MotorBike | 4,460 | 2,477 | 1,977 | 0.9 | 3.8 |
| Czech | 6,373 | 3,538 | 2,829 | 0.6 | 5.0 |
| India | 17,377 | 9,665 | 7,706 | 2.2 | 14.1 |
| Japan | 23,645 | 13,133 | 10,506 | 2.7 | 19.2 |
| Norway | 18,368 | 10,201 | 8,161 | 42.0 | 60.1 |
| United_States | 10,816 | 6,005 | 4,805 | 2.0 | 9.3 |
| **Total** | **85,845** | **47,420** | **38,385** | | **166.3** |

The 85,845 ZIP entries are 85,805 files plus 40 directory entries; the file totals are the ones
reconciled against the published listing in §4.4.

### 4.4 Post-extraction verification

| Check | Result |
| :--- | :--- |
| Published `File_List_CRDDC_RDD2022.txt` file lines | 47,420 `.jpg` + 38,385 `.xml` = **85,805** |
| Actual files on disk under `data\raw\RDD2022` | 47,420 `.jpg` + 38,385 `.xml` = **85,805** |
| Agreement | **exact, per extension** |
| Directory count | 47 = 7 country roots + China_Drone's 4 sub-folders + 6 countries × 6 sub-folders, matching the published `Directory_Structure` exactly (China_Drone has **no** `test` split) |
| Extraction failures | none |
| Metadata preserved | `data\raw\_meta\` holds all three source files with MD5s matching the listing |
| Archive preserved | `RDD2022_released_through_CRDDC2022.zip` still present at full size |
| Post-extraction re-hash (**after** all extraction) | size exact, MD5 `b62bd51d…2bb3`, SHA-256 `5d230a…845b6` — **unchanged, HASH CHECK: PASS** |
| Free space after extraction | 400.44 GiB immediately after; 387.71 GiB at report time |

**Integrity verdict: PASS — download size, published MD5, SHA-256, container CRC, all seven
nested CRCs, and the file-level reconciliation against the published listing all agree. Nothing
was skipped.**

---

## 5. Part D — Dataset inspection

### 5.1 Deliverable

`training/inspect_dataset.py` (new, Ram-owned), standard library + `cv2` + `numpy` only. It is
read-only: it never modifies, converts or splits anything.

```
.\.venv\Scripts\python.exe training\inspect_dataset.py `
    --raw data\raw\RDD2022 --out data\reports\dataset_inspection
```

It writes `data/reports/dataset_inspection.json` (machine-readable) and
`data/reports/dataset_inspection.md` (human-readable). Options: `--hamming` (default 3),
`--max-bucket` (default 500), `--skip-near-duplicates`. Both runs were syntax-checked with
`py_compile` (exit 0) and a single-country smoke test was run before the full pass.

Runtime of the full pass: annotation stage 231.3 s, image stage 1,120.1 s, near-duplicate stage
0.4 s, **total 1,357.5 s**, 0 crashes, 0 exceptions.

### 5.2 Totals

| Metric | Value |
| :--- | ---: |
| Images | **47,420** |
| Annotations parsed / found | **38,385 / 38,385** (0 malformed) |
| Objects | **65,712** |
| Images with an annotation | 38,385 |
| Images without an annotation | **9,035** (all in the official `test` splits) |
| Annotations without an image | **0** |
| Unreadable / corrupt images | **0** |
| XML `size` missing / unparsable / mismatching the real image | **0 / 0 / 0** |
| XML files with zero `<object>` | 11,724 |
| Objects without a class name | 0 |
| Image bytes / XML bytes / total | 13,807,757,095 / 24,718,784 / 13,832,475,879 (12.88 GiB) |

### 5.3 Per country and split

| Country | Split | Images | Annotations | Objects |
| :--- | :--- | ---: | ---: | ---: |
| China_Drone | train | 2,401 | 2,401 | 3,840 |
| China_MotorBike | train | 1,977 | 1,977 | 4,927 |
| China_MotorBike | test | 500 | 0 | 0 |
| Czech | train | 2,829 | 2,829 | 1,745 |
| Czech | test | 709 | 0 | 0 |
| India | train | 7,706 | 7,706 | 8,203 |
| India | test | 1,959 | 0 | 0 |
| Japan | train | 10,506 | 10,506 | 24,754 |
| Japan | test | 2,627 | 0 | 0 |
| Norway | train | 8,161 | 8,161 | 11,229 |
| Norway | test | 2,040 | 0 | 0 |
| United_States | train | 4,805 | 4,805 | 11,014 |
| United_States | test | 1,200 | 0 | 0 |

Only the seven official `train` folders carry annotations; the seven official `test` folders are
unlabelled (9,035 images), exactly as the published `Directory_Structure` implies.

### 5.4 Class distribution

| Code | Objects | Images | Countries | In TDD §4.3 scope |
| :--- | ---: | ---: | :--- | :--- |
| **D00** | **26,016** | 13,548 | all 7 | yes (ID 0) |
| **D10** | **11,830** | 7,709 | all 7 | yes (ID 1) |
| **D20** | **10,617** | 8,412 | all 7 | yes (ID 2) |
| **D40** | **6,544** | 3,674 | all 7 | yes (ID 3) |
| D44 | 5,057 | 4,079 | India, Japan | **no** |
| D50 | 3,581 | 2,638 | India, Japan | **no** |
| Repair | 1,046 | 803 | China_Drone, China_MotorBike | **no** |
| D43 | 793 | 753 | India, Japan | **no** |
| D01 | 179 | 118 | India | **no** |
| D11 | 45 | 36 | India | **no** |
| Block crack | 3 | 3 | China_Drone | **no** |
| D0w0 | 1 | 1 | India | **no** |

In-scope total **55,007** objects; out-of-scope total **10,705** (16.3% of all objects).

### 5.5 Image properties and XML structure

| Property | Value |
| :--- | :--- |
| Extensions | `{'.jpg': 47420}` — a single format, no PNG/BMP/TIFF |
| Width | min 512, median 640, mean 1,322.6, max 4,040 |
| Height | min 512, median 640, mean 932.0, max 2,044 |
| Most common sizes | 600×600 (16,268), 720×720 (9,665), 640×640 (6,005), 4040×2035 (5,400), 512×512 (4,878), 3643×2041 (3,655) |
| XML root tag | `annotation` in 38,385/38,385 files |
| XML child tags (first sample) | `folder`, `filename`, `size`, `segmented`, `object` |

This is plain Pascal VOC, so the converter in TDD §4.3 applies without special cases. Note that
image sizes vary per country, which is why the converter must read each image for its true
dimensions rather than trusting the XML.

### 5.6 Duplicates

| Check | Result |
| :--- | ---: |
| Exact duplicate groups (SHA-256) | **2** (2 extra copies) |
| Near-duplicate groups (dHash 64-bit, Hamming ≤ 3) | 635 |
| Images inside near-duplicate groups | 2,395 |
| Near-duplicate pair edges | 7,673 |
| Largest near-duplicate group | 358 |
| Duplicate file names | **0** |

The two exact duplicate pairs, with paths:

1. `United_States\test\images\United_States_005833.jpg` is **byte-identical** to
   `United_States\train\images\United_States_003260.jpg` — the only exact duplicate that crosses
   the official train/test boundary.
2. `United_States\train\images\United_States_001623.jpg` is byte-identical to
   `United_States\train\images\United_States_003917.jpg` (same split; harmless but must not end up
   on both sides of the internal split).

### 5.7 Independent cross-check

Because "11,724 XML files with zero objects" is a surprising number, it was re-measured with a
completely separate implementation (raw text scan of `<object>` occurrences, no parser, no
`inspect_dataset.py` code path):

| Measure | Inspection tool | Independent scan |
| :--- | ---: | ---: |
| XML files | 38,385 | 38,385 |
| XMLs containing ≥ 1 `<object>` | 26,661 | 26,661 |
| XMLs with no `<object>` | 11,724 | 11,724 |
| Total `<object>` tags | 65,712 | 65,712 |

**The two implementations agree exactly.** Empty annotations are a genuine property of RDD2022
(e.g. Czech 1,757/2,829 and Norway 5,247/8,161 annotated images describe "no damage"), not a
parsing defect.

### 5.8 Supplementary measurement — what survives the TDD §4.3 mapping

A one-off, annotation-only count (no images read, nothing converted, nothing written) applied the
TDD's fixed mapping `{D00, D10, D20, D40}` to every XML to size the exclusion effect:

| Country | XMLs | Objects | In scope | Out of scope | Empty XML | Only out-of-scope | Empty after mapping |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| China_Drone | 2,401 | 3,840 | 3,068 | 772 | 5 | 477 | 482 |
| China_MotorBike | 1,977 | 4,927 | 4,650 | 277 | 0 | 43 | 43 |
| Czech | 2,829 | 1,745 | 1,745 | 0 | 1,757 | 0 | 1,757 |
| India | 7,706 | 8,203 | 6,831 | 1,372 | 3,921 | 562 | 4,483 |
| Japan | 10,506 | 24,754 | 16,470 | 8,284 | 794 | 1,812 | 2,606 |
| Norway | 8,161 | 11,229 | 11,229 | 0 | 5,247 | 0 | 5,247 |
| United_States | 4,805 | 11,014 | 11,014 | 0 | 0 | 0 | 0 |
| **Total** | **38,385** | **65,712** | **55,007** | **10,705** | **11,724** | **2,894** | **14,618** |

**23,767 annotated images will carry at least one in-scope box; 14,618 will be empty after the
fixed mapping.** Combined with the 9,035 unlabelled test images, the dataset's usable labelled
volume is materially below the headline "47,420 images" and must be recorded as such in the split
and training reports (PRD §5.2, Table 7).

---

## 6. Gates

| # | Gate | Evidence | Result |
| :--- | :--- | :--- | :--- |
| A1 | Four decisions ratified in the project decision document | `OPEN_QUESTIONS.md` Q-02, §5.2, §8 | **PASS** |
| A2 | Chosen paths documented and project-owned | §5.2 path table | **PASS** |
| A3 | AC-18 verification method documented; isolation not over-claimed | §5.2 method, 5 steps, step 6 excluded | **PASS** |
| B1 | Official source, version and listing verified | §3.1 | **PASS** |
| B2 | Exact size and published integrity information established | §3.2–§3.3 | **PASS** |
| B3 | Free space ≥ 3× download size | 11.47× | **PASS** |
| B4 | Windows-safe short destination | worst path 119 chars, 141 headroom | **PASS** |
| C1 | Download completed at the exact published size | 13,264,172,619 bytes, HTTP 200 | **PASS** |
| C2 | Published MD5 matched | `b62bd51d…2bb3` | **PASS** |
| C3 | SHA-256 recorded | `5d230a29…845b6` | **PASS** |
| C4 | Container `zipfile.testzip()` clean | `None` | **PASS** |
| C5 | All 7 nested archives CRC-clean and extracted | 7/7, `failures: []` | **PASS** |
| C6 | Extracted file set matches the published listing | 47,420 JPG + 38,385 XML = 85,805 | **PASS** |
| C7 | Original archive preserved and re-verified after extraction | MD5/SHA-256 unchanged | **PASS** |
| D1 | `training/inspect_dataset.py` created and runnable | `py_compile` 0, full run 0 | **PASS** |
| D2 | Machine-readable + human-readable reports produced | `dataset_inspection.json`, `.md` | **PASS** |
| D3 | No conversion, no split, no training | no label/split/weight file exists | **PASS** |

---

## 7. Failed checks and unresolved issues

No gate failed. The following items are **open observations that the next stages must handle**;
none of them invalidates this task's result.

1. **Near-duplicate counts are a lower bound.** Three 16-bit dHash buckets exceeded the 500-image
   cap and were skipped (2,077 images, `near_skipped_buckets: 3`). Those images were never
   compared pairwise, so the reported 635 groups / 2,395 images is a floor, not a total. Rationale
   for the cap: a degenerate bucket (e.g. many near-uniform, low-contrast images sharing a hash
   prefix) would otherwise force a quadratic blow-up. The definitive leakage proof belongs to the
   split stage (TDD §4.5 / PRD §5.3), where the final, much smaller split can be checked
   exhaustively.
2. **Eight class codes sit outside the TDD's four.** `D01`, `D0w0`, `D11`, `D43`, `D44`, `D50`
   (India, Japan), plus `Repair` and `Block crack` (China). That is **10,705 objects (16.3%)**.
   TDD §4.3 says codes outside the four are excluded and counted, so the converter must count them
   by reason — and **no document authorises aliasing** `D01`→`D00` etc. This needs a team decision
   before conversion if those objects are wanted.
3. **14,618 annotated images become empty after the fixed mapping** (11,724 genuinely empty XMLs
   + 2,894 with only out-of-scope codes). Whether these are used as background examples is exactly
   **Q-03**, still open. It materially changes the training volume.
4. **One exact duplicate crosses the official train/test boundary**
   (`United_States_005833.jpg` ↔ `United_States_003260.jpg`). The official test split is unlabelled
   and per PRD §5.2 is excluded from quantitative evaluation, but this pair must not silently
   become internal train/test leakage later.
5. **AC-18 OS-level network proof is still outstanding.** The ratified policy is a library-level
   control plus a verification procedure; no firewall rule or connection trace has been run.
   Until then the project must not claim complete network isolation.
6. **The official test split is unlabelled** (9,035 images). It cannot be used for metrics; the
   internal evaluation split must come from the labelled `train` folders.
7. **Repository path contains a space**, so any generated Ultralytics `data.yaml` must quote its
   `path:` value. This is recorded, not yet exercised.
8. **Still-open decisions unchanged by this task:** Q-01, Q-03 … Q-11, C-01 … C-04, G-01 … G-06,
   A-02, A-04, A-05, A-07, A-09 (see `OPEN_QUESTIONS.md`).

---

## 8. Files created or modified

| Path | Change |
| :--- | :--- |
| `docs/project/OPEN_QUESTIONS.md` | **Modified** — Q-02 ratified; A-01/A-03 marked verified; new §5.2 (N-02, N-08, N-09, AC-18 policy, chosen paths, verification method); §8 sign-off row; "still open" list updated |
| `.gitignore` | **Modified** — added `.ultralytics/` |
| `training/inspect_dataset.py` | **New** — dataset inspection tool (read-only) |
| `docs/project/ROADVISION_S4_T2_REPORT.md` | **New** — this report |
| `data/raw/_archives/RDD2022_released_through_CRDDC2022.zip` | **New** — preserved original archive (12.35 GiB) |
| `data/raw/_archives/RDD2022/*.zip` | **New** — 7 nested country archives (12.35 GiB total) |
| `data/raw/RDD2022/<Country>/{train,test}/…` | **New** — extracted dataset, 85,805 files, 12.88 GiB |
| `data/raw/_meta/{File_List,Directory_Structure,label_map}` | **New** — source metadata, MD5-verified |
| `data/reports/dataset_inspection.json` | **New** — machine-readable inspection summary |
| `data/reports/dataset_inspection.md` | **New** — human-readable inspection report |

Not committed, not pushed. Dataset artefacts are ignored by `.gitignore` (`data/raw/*`, `*.zip`,
`*.jpg`); `data/reports/` is currently untracked and its tracking policy is a team choice.

---

## 9. Exact next recommended task

**S4-T3 — Annotation conversion and frozen split (TDD §4.3–§4.5), gated on two decisions.**

Concretely:

1. Close **Q-03** (are the 14,618 empty-after-mapping images background examples?) and **Q-04**
   (split ratio and perceptual-hash threshold), because both change the split definition.
2. Create `training/convert_annotations.py` implementing TDD §4.3 exactly: read each XML, map
   `{D00, D10, D20, D40}` → IDs 0–3 from a single `classes.json`, read each image for true size,
   clip with the 2 px tolerance and count clipped boxes, exclude and count by reason (non-numeric,
   zero-area, out-of-image beyond tolerance, unsupported code), write labels to
   `data\annotations\`, and emit a conversion report that reconciles against this inspection's
   55,007 in-scope objects.
3. Only then freeze the split into `dataset\` with a recorded seed, stratification, and an
   exhaustive duplicate/leakage check that also resolves open item §7.1 and the cross-split
   duplicate in §7.4.

Do **not** start training in the same task.

---

## 10. Result

Decisions ratified, preflight fully established (11.47× free-space margin, 119-character worst
path), archive downloaded at the exact published size with a matching MD5, SHA-256 recorded, all
container and nested CRCs clean, 85,805 extracted files reconciled exactly against the published
listing, archive preserved and re-verified, and a read-only inspection tool run over all 47,420
images producing both machine- and human-readable reports. No gate failed, and nothing was
converted, split, trained or committed.

**S4-T2 COMPLETE**
