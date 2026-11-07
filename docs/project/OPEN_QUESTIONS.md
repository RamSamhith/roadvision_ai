# RoadVision AI — Conflicts, Open Questions and Recorded Decisions

**Prepared:** 2026-11-05 (Stage 2 — document analysis and environment preparation)
**Sources:** TDD v1.1, PRD v1.1, Project Proposal — identities and SHA-256 in
[`docs/source/DOCUMENT_REGISTER.md`](../source/DOCUMENT_REGISTER.md)
**Authority order:** TDD v1.1 → PRD v1.1 → Project Proposal

---

## 0. Why this file exists

`AGENTS.md` §1 forbids inventing requirements and forbids resolving document conflicts
silently. This file is the single place where every disagreement, ambiguity, gap and
environment-driven deviation is written down, with its source citation, its impact and the
decision that is still owed by the team.

Nothing in this file has been resolved by the agent on the team's behalf unless it is listed
in §3 as a **recorded Stage-2 decision** — and even those are marked *pending ratification*
and can be reversed without re-doing the environment work only where stated.

**Vocabulary used below**

| Term | Meaning |
| :--- | :--- |
| **Conflict (C-xx)** | Two statements in the ratified documents that cannot both be implemented as written. |
| **Question (Q-xx)** | A value or choice the documents explicitly defer to the team ("recommended", "to be approved", "optional"). |
| **Decision (D-xx)** | A choice made during Stage 2 to make the environment installable, with rationale and reversibility. |
| **Assumption (A-xx)** | A design detail taken from document skeleton code that has not been executed and must be proven at implementation time. |
| **Gap (G-xx)** | Behaviour needed for a usable product that no document specifies at all. |

---

## 1. Summary

| ID | Type | Subject | Source | Blocks | Needs decision by |
| :--- | :--- | :--- | :--- | :--- | :--- |
| C-01 | Conflict | Fallback wipes the primary model from `models_used` | TDD §3.3 p5–6 vs PRD §4.8 Table 6 p7 | AC-10, FR-05, FR-08 | Before model-manager work |
| C-02 | Conflict | Webcam stream-closed session recorded as `completed` | TDD §9 p13 vs PRD §4.10 p8 | AC-07, FR-03 | Before camera module work |
| C-03 | Conflict | Free-disk-space check missing from TDD upload/validation | PRD §4.9 p7 vs TDD §10.2 p14–15 | FR-09, AC-05 | Before video module work |
| C-04 | Conflict | AC-08 cross-layer class check absent from TDD test plan | PRD §4.4 p5 / AC-08 p12 vs TDD §16.1 p20 | FR-04, AC-08 | Before first test suite |
| Q-01 | Question | Operating limits (sizes, durations, FPS, concurrency) | PRD §4.11 p8–9; TDD §10.2 p14 | FR-01/02/03, AC-03/05 | Before feature build |
| Q-02 | Question | End-to-end (NMS-free) vs NMS mode | TDD §3.4 p6, App. B p22 | FR-06, evaluation | Before training |
| Q-03 | Question | Use annotation-free images as background examples | TDD §4.6 p9, App. B p22 | Training quality | Before training |
| Q-04 | Question | Perceptual-hash distance and split ratio | TDD §4.4 p8, App. B p22 | AC-16 | Before splitting |
| Q-05 | Question | Minimum live FPS and watchdog interval | PRD §4.11 p9; TDD §9 p13, App. B p22 | F5, AC-06 | Before camera work |
| Q-06 | Question | Image-list files vs copied folders | TDD §4.5 p9, App. B p22 | Dataset build | Before dataset build |
| Q-07 | Question | Optional features: manual selector, FP16, ONNX, ByteTrack | TDD App. B p22 | Scope | Before feature build |
| Q-08 | Question | Dataset size claims ("47,420 images") | TDD App. C p22; PRD §5.1 p9 | Report accuracy | Before acquisition |
| Q-09 | Question | Upload retention after processing | PRD §4.9 p7 | FR-09, disk growth | Before video work |
| Q-10 | Question | Training subset size and sampling seed | PRD §5.1 p9; TDD §4.6 p9 | Training, schedule | Before training |
| Q-11 | Question | Backend binding and demo access | PRD §6 p10 (NFR) | AC-18 | Before demo |
| G-01 | Gap | "Recent inspection history" length on dashboard | PRD §4.7 p7 | FR-07 | Before dashboard |
| G-02 | Gap | Log file location, format, rotation | TDD §15 p19 | NFR maintainability | Before backend work |
| G-03 | Gap | Delete semantics: record vs output files | PRD §4.8 p7, §4.9 p7 | FR-08, AC-14 | Before history work |
| G-04 | Gap | Database/output/config absolute locations | TDD §13 p18 | All persistence | Before backend work |
| G-05 | Gap | Frontend test strategy (no framework named) | TDD §16.1 p20 | Quality | Before frontend work |

---

## 2. Conflicts (cannot both be implemented as written)

### C-01 — The fallback path discards the primary model from `models_used`

**PRD v1.1 §4.8, Table 6, p7** requires the stored field:

> "Model used | YOLO26m or YOLO26n (**for a mid-session switch, both are recorded**) [REV]"

**PRD v1.1 §4.5, p6** (F5) and **§4.3, p5** repeat that both models must be recorded when a
switch occurs. **TDD v1.1 §3.3, p5–6** agrees in prose:

> "Every fallback is logged with its reason and stored in the inspection's `models_used` field."

and the SQLite schema in **TDD v1.1 §11, p16** documents the intended value:

> `models_used TEXT, -- e.g. 'YOLO26m' or 'YOLO26m,YOLO26n'`

**The conflict.** The skeleton implementation in **TDD §3.3, p6** does this:

```python
def startup(self, start_from="YOLO26m"):
    for name in self.ORDER[self.ORDER.index(start_from):]:
        try:
            self.model, self.active = self._load(name), name
            self.models_used = [name]          # <-- list is REPLACED
...
def switch_to_fallback(self, reason):
    if self.active != "YOLO26m":
        return False
    self.errors["YOLO26m"] = reason
    self.startup(start_from="YOLO26n")         # <-- reaches the line above
```

`switch_to_fallback()` calls `startup()`, which assigns `self.models_used = [name]`. After a
F3/F5 switch the list is therefore `["YOLO26n"]`, and the YOLO26m attempt is lost — exactly the
information PRD Table 6 says must be preserved.

**Impact.** AC-10 ("the history stores the model used") can pass while the PRD requirement is
still violated, because the acceptance criterion does not check for *both* names. Any evaluation
or report that counts "inspections that used the fallback" would under-report.

**Options for the team**

1. Change `startup()` to append instead of replace when it is called from a fallback, and keep
   `models_used` append-only per inspection. *(Recommended: smallest change, matches the schema
   comment.)*
2. Keep `startup()` as-is and have `switch_to_fallback()` record the previous model before
   calling it.
3. Accept the TDD code as authoritative and amend PRD Table 6. *(Not recommended: it loses audit
   information the PRD explicitly asked for.)*

**Status:** UNRESOLVED — needs team approval. The traceability matrix lists FR-05/AC-10 as
NOT STARTED, so no code needs to be rewritten yet.

---

### C-02 — A webcam session closed by the watchdog is saved as `completed`

**PRD v1.1 §4.10, p8** (failure table) requires:

> "Camera unavailable, in use, or disconnected mid-session | Clear message; session ends;
> aggregated results so far are saved with a **failed or interrupted** note; the application
> keeps running"

**PRD v1.1 §4.3, p5** and **AC-07, p12** repeat that camera failures must be reported without
crashing.

**TDD v1.1 §9, p13** Table 5 lists "no stream consumer for the watchdog interval (recommended
10 s)" as a session-end condition, and the skeleton does:

```python
def _loop(self, cap, iid, conf):
    status, err, started = "completed", None, time.monotonic()
    try:
        while not self._stop.is_set():
            if time.monotonic() - started > MAX_SESSION_S: break
            if time.monotonic() - self._last_client > WATCHDOG_S:
                err = "stream closed"; break        # <-- status NOT changed
```

**The conflict.** The watchdog branch sets `err` but leaves `status = "completed"`, so
`db_finish_webcam(iid, "completed", "stream closed")` writes a *successful* record with an error
string. The PRD requires failed or interrupted. (The TDD's own status vocabulary in §11 p16 and
PRD Table 6 has no `interrupted` value — only `queued, processing, completed, failed, cancelled` —
so "interrupted note" must be expressed as `failed` plus an explanatory error, or as
`cancelled`.)

**Impact.** AC-07 passes on the visible behaviour (no crash, message shown) while the stored
record falsely reports success, contaminating dashboard statistics.

**Options for the team**

1. Set `status = "failed"` (or `"cancelled"` if the user closed the tab) with
   `err = "stream closed after watchdog timeout"`. *(Recommended: uses existing vocabulary.)*
2. Add `interrupted` to the status CHECK constraint in TDD §11 and to PRD Table 6. *(Cleaner
   semantics, but changes the ratified schema and every status filter.)*

**Status:** UNRESOLVED — needs team approval before the camera module is implemented.

---

### C-03 — The free-disk-space precondition is only in the PRD

**PRD v1.1 §4.9, p7:**

> "Check that free disk space is at least **twice the input file size** before starting a video
> job; otherwise reject with a clear message."

**PRD v1.1 §4.10, p8** lists "disk full" as a video-job failure that must delete partial output.

**TDD v1.1 §10.2, p14–15** specifies upload limits, streaming, Pillow/OpenCV validation and the
result-name sanitiser, but contains **no free-space check**; `validate_video()` ends at duration
and resolution checks. A repository-wide search of the TDD for "free disk", "disk space" or
"disk full" finds only §4.1 p7, which concerns dataset extraction, not uploads.

**The conflict.** The TDD is the primary technical authority and its validation list is
presented as the complete set of preconditions. Implementing it literally omits a PRD
requirement; AC-05 ("corrupt file and user cancellation … leave no partial output or temp files")
does not test the precondition either, so the omission would go unnoticed by acceptance testing.

**Impact.** On a laptop with a nearly full disk, a 200 MB upload can start, fail mid-way, and
leave a partial output — the exact failure mode the PRD wanted prevented.

**Recommended resolution.** Add `shutil.disk_usage(OUTPUT_DIR).free >= 2 * input_size` to the
video path inside `validate_video()` / the job-start handler, returning
`507`/`insufficient_storage` (or the project's existing 422-style error shape, TDD §10.3 p15).
Record the check in the traceability matrix under FR-09.

**Status:** UNRESOLVED — the check is not implemented anywhere yet, so this is a documentation
gap only.

---

### C-04 — AC-08's automated cross-layer class check is not in the TDD test plan

**PRD v1.1 §4.4, p5 (Mandatory addition):**

> "It must be defined once (for example in the dataset YAML and one shared configuration file)
> and verified by an automated check (AC-08) comparing it with the trained models' class names,
> the backend, the SQLite schema or constants, and the frontend labels."

**PRD v1.1 AC-08, p12:** "Automated check script comparing class lists and order."

**TDD v1.1 §3.3, p5** implements a *runtime* check (`names != CLASS_CODES` → model rejected) and
**§16.1, p20** lists unit tests for "class-code mapping" among others. Neither is the required
five-layer automated comparison: model weights, `classes.json`/config, backend constants, SQLite
schema/constants and frontend labels.

**The conflict.** The TDD test strategy is narrower than the PRD's mandatory addition. A runtime
class check on load protects inference but would not catch a frontend label reordered relative
to the backend, which is the failure AC-08 exists to prevent.

**Recommended resolution.** Add one pytest/script test (`backend/tests/test_class_consistency.py`
or `training/verify_classes.py`) that parses the frontend label map, `classes.json`, the SQLite
constants and both model checkpoints' `names`, and asserts all five equal
`["D00", "D10", "D20", "D40"]`.

**Status:** UNRESOLVED — no class list exists in code yet.

---

## 3. Questions the documents defer to the team

Each of these is explicitly labelled "recommended", "to be approved" or "optional" in the source.
They are **not** answered here; they are collected so that no silent default is adopted.

### Q-01 — Operating limits must be approved before feature work

**PRD v1.1 §4.11, p8–9** and **TDD v1.1 §10.2, p14** give identical recommended values:

| Limit | Recommended | Consequence of changing it |
| :--- | :--- | :--- |
| Image formats | JPG, JPEG, PNG | Changes `validate_image()` accept list (AC-03) |
| Image size | ≤ 20 MB, longest side ≤ 8192 px | Changes 413/422 thresholds and `MAX_IMAGE_PIXELS` |
| Video formats | MP4, AVI | Changes `validate_video()` and FFmpeg demux expectations |
| Video size / duration | ≤ 200 MB, ≤ 60 s | Drives the free-space check (C-03) and demo clip lengths |
| Video resolution | ≤ 1920 × 1080 | Changes rejection logic only; model downscales |
| Video job time limit | 10 min | Drives the watchdog thread and F4 timeout path |
| Webcam session | auto-stop at 10 min | Drives `MAX_SESSION_S` |
| Minimum live FPS | 5 FPS (trigger F5) | See Q-05 |
| Concurrency | 1 video job or webcam session | Drives the single job slot and 409 `busy` |

PRD §4.11 adds: *"the video limits in particular must be re-checked after the first throughput
measurement (Section 11) and adjusted before final acceptance testing."*

**Decision needed:** approve or amend the table. Until then the backend must read these from one
configuration module (TDD §13 `backend/app/config.py`) rather than hard-coding them, so a change
is a config edit. **No measurement exists yet — the Stage-2 environment audit did not process a
video, so none of these numbers is validated.**

---

### Q-02 — End-to-end (NMS-free) mode or the traditional NMS path

**TDD §3.4, p6:** YOLO26 predicts end-to-end without NMS by default; `end2end=False` selects the
traditional path with an IoU threshold. The team chooses **once**, applies it to both models,
application and evaluation, and stores the mode in every inspection (schema column `nms_mode`
with `CHECK (nms_mode IN ('end2end','nms'))`, TDD §11 p16) and every evaluation result.

**TDD Appendix B, p22** recommends the default end-to-end mode.

**Decision needed:** `end2end` or `nms`. If `nms`, also fix the IoU threshold (the skeleton
suggests `{"end2end": False, "iou": 0.7}`, TDD §3.3 p6). Note that the exact Ultralytics keyword
plumbing is itself unverified — see A-01.

**Status: RATIFIED (S4-T2, 5 November 2026) — end-to-end, selected with `nms=False`.**
The S4-T1 probe proved that the TDD's literal keyword is legacy: `end2end=` is deprecated, maps
onto `nms`, and `end2end=False` selects the **external-NMS** branch. The NMS-free branch is
selected by **`nms=False`**, which sets the model head's end-to-end flag to `True`. Default
`predict()` (no `nms` argument) selects the one-to-many branch and therefore runs external NMS.
Consequences: the stored `nms_mode` value is `end2end` when `nms=False` was used; `end2end=` must
never appear in new code; `iou` is meaningful only in `nms` mode. Evidence:
[`ROADVISION_S4_T1_REPORT.md`](ROADVISION_S4_T1_REPORT.md) §5.1. Implementation is still
NOT STARTED; this closes the decision, not the work.

---

### Q-03 — Annotation-free images as background examples

**TDD §4.6, p9** and **Appendix B, p22**: the team may use RDD2022 images that carry no
annotations as background (negative) examples. This affects the class balance and the
false-positive rate, and it changes what `data/processed` must contain.

**Decision needed:** yes/no, and if yes, how many per split, with the ratio recorded.

**Status: IMPLEMENTATION-APPROVED (S4-T3B, 6 November 2026).** The S4-T3B task approved the
recommendation below for implementation; the S4-T3A evidence is unchanged. Because the **V2**
visual-inspection gate could not be closed (no V2 sign-off artifact exists, and the literal
sample is impossible for China_Drone, which has only 5 empty XMLs), the implementation applied
the documented **Policy A fallback**. The applied policy and the reason are recorded in
`dataset/reports/policy_decision.json`, `dataset/reports/conversion_summary.json` and
`dataset/reports/dataset_report.json`. Policy C is implemented as an option and requires an
explicit `--v2-signoff` file. Evidence:
[`ROADVISION_S4_T3A_POLICY_AUDIT.md`](ROADVISION_S4_T3A_POLICY_AUDIT.md) §3.1–3.9 and §7,
backed by `data/reports/audit/policy_audit.json` (`part_a`).

Measured facts behind the recommendation:

- Corpus: 47,420 images, 38,385 XMLs, 65,712 objects. The 9,035 images without XML are
  **all** official `*/test/` images and stay out of every policy pool (TDD §4.4).
- Annotated images: 19,221 `only_target`, 4,546 `mixed_target_oos`, 2,894 `only_oos`, and
  11,724 structurally empty XMLs. The 2,894 `only_oos` images contain 3,340 real damage
  incidences of excluded codes (D44, D50, Repair, D43, D01, D11, Block crack, D0w0).
- Duplicate evidence contradicts **372** empty XMLs (in 79 groups) and **21** `only_oos`
  images, i.e. the same scene is target-labelled elsewhere.
- Policy pools: **A** (targets only) = 23,767 images; **B** (A + `only_oos` as background) =
  26,661; **C** (A + verified-empty) = 35,119.

**Recommended (not ratified): Policy C** — 23,767 images with at least one retained target
box plus **11,352** structurally empty XMLs not contradicted by duplicate evidence. Exclude
the 372 contradicted empty XMLs and all 2,894 `only_oos` images. **Policy A is the fallback**
if the verification gate cannot be closed before the split is frozen. **Policy B is rejected**
because it would label 10,705 real damage objects as negative evidence and is biased toward
Japan and India.

Before the split is frozen, gate **V2** must inspect a stratified sample of 300 of the 11,352
remaining empty XMLs (60 per country, full resolution, seed recorded). If it shows a
*systematic* omission in a country, exclude that country's empty XMLs or fall back to Policy
A. Background images enter all three splits in natural proportion; only the training list may
be subsampled later under TDD §4.6, and only after a measured reason exists. The 372 and 21
exclusion lists must be archived with the split for auditability.

---

### Q-04 — Perceptual-hash distance and split ratio

**TDD §4.4, p8:** exact duplicates are removed by file hash; near-duplicates by a perceptual
difference hash merged within a small Hamming distance. The skeleton uses **Hamming ≤ 3** over
64 bits with pigeonhole bucketing. **Appendix B, p22** recommends a split of **about 80 / 10 / 10**.

**Decision needed:** confirm threshold 3 and 80/10/10, or state alternatives. Both must be
recorded in the dataset record (AC-16) and reproduce the same splits from the same seed.

**Status: IMPLEMENTATION-APPROVED (S4-T3B, 6 November 2026).** The S4-T3B task approved the
values below for implementation; the S4-T3A evidence is unchanged. They are implemented in
`training/split_dataset.py` and the generated split reconciles exactly with the audit simulation:
22,966 groups, **19,017 / 2,401 / 2,349** images, 0 group-crossing and 0 exact-hash violations.
Evidence:
[`ROADVISION_S4_T3A_POLICY_AUDIT.md`](ROADVISION_S4_T3A_POLICY_AUDIT.md) §4.1–4.12, §5.1–5.6,
and §7, backed by `data/reports/audit/policy_audit.json` (`part_b`, `part_c`) and
`data/reports/audit/duplicate_groups.json`.

**Recommended (not ratified):** exact duplicates by **SHA-256**; near-duplicates by **64-bit
dHash at Hamming ≤ 3** with union-find transitive closure, **no bucket cap** (pigeonhole over
8 × 8-bit chunks is exact for d ≤ 7); **80 / 10 / 10**, seed **42**,
`StratifiedGroupKFold(n_splits=10)`, `folds[0]` = test, `folds[1]` = val, stratification by the
rarest retained class in each group, group-level splitting only, lists frozen and hashed on
first write.

Measured support:

- 2 exact-duplicate pairs / 2 redundant files. One pair crosses the official train/test
  boundary, but its test member has no XML and is outside the pool.
- At d ≤ 3: **636 groups / 2,416 images**; median pixel correlation 0.909. At d = 4 the
  grouping grows to 956 groups / 4,296 images and the largest group from 360 to 1,352, mostly
  through hash-degenerate pavement merges. At d = 2, 1,759 same-scene pairs would be missed.
- Cross-original-split groups: 220; cross-country: 11; label-inconsistent: 79; chained
  (diameter > 3): 160.
- The 80/10/10 simulation (seed 42) has **0 group-crossing and 0 exact-hash violations** under
  both policies; maximum class-share deviation is 1.03 pp.
- The 500-image cap used by S4-T2 is removed. The uncapped audit reports 636 groups / 2,416
  images versus S4-T2's 635 / 2,395 (delta +1 group / +21 images).

**Deviations from the TDD skeleton that must be recorded in S4-T3 (AC-16):** 8 × 8-bit
pigeonhole instead of 4 × 16-bit; identical-hash collapse instead of `MAX_BUCKET` skipping;
SHA-256 instead of SHA-1; `iter("object")` instead of `findall("object")`; groups sorted before
folding.

**Inspection artifacts:** contact sheets now exist for all 22 groups with at least 8 images,
plus the 7 remaining cross-country groups (29 total), under
`data/reports/audit/contact_sheets/`. The 13 groups without a recorded visual conclusion are
marked `"visual_inspection": "not inspected"` in `ambiguous_groups_report.json`; no visual
verdict was fabricated for them. The generator is
[`training/make_inspection_artifacts.py`](../../training/make_inspection_artifacts.py).

---

### Q-05 — Minimum live FPS and watchdog interval

**PRD §4.11, p9:** minimum live FPS **5** (recommended).
**TDD §3.3, p5** (F5): switch to YOLO26n when YOLO26m stays below the minimum **for 10 s**.
**TDD §9, p13:** watchdog interval **10 s** without a stream consumer.

These are three separate constants (`MIN_LIVE_FPS`, the F5 dwell time, `WATCHDOG_S`) and the
documents give no measured basis for any of them.

**Decision needed:** approve 5 FPS / 10 s / 10 s, or set values after measuring this laptop.
**Caution:** the Stage-2 smoke test measured **20.4 ms/frame for YOLO26n at 640 px on a blank
image** — that is a forward-pass smoke test, *not* a throughput measurement, and must not be
quoted as FPS in the report.

---

### Q-06 — Image-list files instead of copied folders

**TDD §4.5, p9** describes the YOLO folder layout; **Appendix B, p22** lists "image-list files
instead of copied folders" as optional. **Appendix C, p22** notes that Ultralytics' handling of
`.txt` image lists is **not verified**.

**Decision needed:** only if disk space forces it. Copied folders are the documented default and
the lower-risk option; image lists must be tested before adoption (see A-04).

---

### Q-07 — Optional features: manual selector, FP16, ONNX Runtime, ByteTrack

**TDD Appendix B, p22:** "Optional: image-list files instead of copied folders; manual model
selector; FP16 inference; ONNX Runtime and ByteTrack remain optional and out of the core scope."
**PRD §4.5, p6 / F6:** manual model selection is optional.

**Decision needed:** include F6 in the demo or not; decide FP16 only after measuring VRAM and
throughput on the 8 GB RTX 5060. ONNX Runtime and ByteTrack are explicitly out of core scope —
they should stay out unless the schedule has slack.

---

### Q-08 — Dataset size claims are unverified

**TDD Appendix C, p22** lists "RDD2022 size and class distribution" as **not verified**.
**PRD §5.1, p9** separates acquisition from the training subset and forbids claiming all
downloaded images were used for training.

A figure of **47,420 images** appears in secondary material associated with RDD2022 but is **not
asserted by any of the three ratified documents** and has **not** been verified against the
archive in this stage (no dataset was downloaded, by instruction).

**Decision needed / action:** after acquisition, count images per country and per class from the
actual archives and record the measured numbers. Until then, the report must not state a total.

---

### Q-09 — Are uploaded originals deleted after processing?

**PRD §4.9, p7:** "Uploaded original files are not retained after processing **unless the team
decides otherwise** (recommended, for privacy and disk space); annotated outputs are retained
until the user deletes them."

**Decision needed:** confirm deletion. If originals are kept, the retention location and lifetime
must be documented, and disk usage grows by up to 200 MB per video.

---

### Q-10 — Training subset size and sampling seed

**PRD §5.1, p9** and **TDD §4.6, p9**: the training volume is decided from available hardware
and the 7-day schedule; validation and test sets are *not* reduced; the test set is frozen first.

**Decision needed:** the subset size, the stratification key (class × country), and the random
seed. This cannot be decided before the dataset is counted (Q-08) and before training throughput
is measured on this GPU.

---

### Q-11 — Backend binding and demo access

**PRD §6, p10 (Privacy and security):** "The backend must listen on the local machine only
(127.0.0.1) unless the team documents a reason otherwise." **AC-18, p12** tests the listening
address.

**Decision needed:** confirm 127.0.0.1 for the whole project. If the evaluator needs to reach the
demo from another machine, that reason must be documented in the report before the port is
opened — it is an exception to a stated NFR, not a default.

---

## 4. Gaps — behaviour no document specifies

These are not contradictions; they are simply missing. Each needs a written decision before the
corresponding module is built, otherwise the implementer will invent a default.

| ID | Missing specification | Source of the requirement that exposes the gap | Suggested default (for approval, not applied) |
| :--- | :--- | :--- | :--- |
| G-01 | How many entries "recent inspection history" shows on the dashboard, and whether it pages | PRD §4.7, p7 | 5 most recent, no paging; full list in History |
| G-02 | Log file path, line format, level, rotation and retention | TDD §15, p19 ("All errors must be logged to a local log file with timestamp and cause") | `logs/roadvision.log`, rotating at 5 MB × 3, INFO |
| G-03 | Whether deleting an inspection removes its annotated output and whether a record can be kept after output deletion | PRD §4.8, p7 ("delete an inspection record together with its output files") vs §4.9, p7 ("history entry remains; 'output no longer available'") | Two actions: delete record + outputs; and tolerate missing output without deleting the record |
| G-04 | Absolute locations of the SQLite file, output directory, temp directory and model directory | TDD §13, p18 (`backend/…` tree is a proposal) | `data/roadvision.db`, `data/outputs/`, `data/tmp/`, `models/weights/` |
| G-05 | Frontend test framework and coverage expectations | TDD §16.1, p20 names only pytest, a gate script, failure injection and a manual checklist | No frontend unit-test framework in core scope; manual checklist + one Playwright smoke run if time allows |
| G-06 | HTTP status/error code for a disk-space rejection (C-03) and for a model-unavailable detection call | TDD §10.3, p15 defines the error shape, not this code | `507 insufficient_storage`; `503 model_unavailable` |

---

## 5. Decisions recorded during Stage 2

These were necessary to reach a *verifiable* environment. Each is a deviation or a pin, with its
reason. **All are pending team ratification.** Deviations from the TDD are marked **DEV**;
choices the documents left open are marked **PIN**.

| ID | Type | Decision | Document position | Rationale / evidence |
| :--- | :--- | :--- | :--- | :--- |
| D-01 | **DEV** | Model weights live in `models/weights/`, not `weights/` | TDD §13, p18 proposes `weights/` at the repository root | `models/weights/` already existed in this repository and is already covered by `.gitignore`; moving it would break the established layout for no functional gain. **This must be listed as a deviation in the project report.** |
| D-02 | **DEV** | No SQLAlchemy / aiosqlite; use the standard-library `sqlite3` module | TDD §11, p16 shows `import sqlite3` and raw SQL; PRD §4.8, p7 says "SQLite is used" | The previous `requirements.txt` listed SQLAlchemy and aiosqlite, which no ratified document requires. Adding an ORM would contradict the schema listing and add a dependency with no consumer. |
| D-03 | **DEV** | No `ffmpeg-python`; use `imageio-ffmpeg` + `subprocess` | TDD §2, p4 and §8, p11–12 explicitly call `imageio_ffmpeg.get_ffmpeg_exe()` and build the command line | Follows the TDD exactly; `ffmpeg-python` was an unused leftover. System FFmpeg 9.0 is present, and `imageio-ffmpeg` bundles its own binary if it is not. |
| D-04 | **DEV** | No `aiofiles` | Not referenced anywhere in TDD v1.1 | Large files are streamed in 1 MB chunks with plain blocking I/O inside `def` handlers (TDD §10.2, p14), not `async` file I/O. |
| D-05 | **DEV** | NumPy **2.x** (no `numpy<2` cap) | No document pins NumPy | PyTorch 2.11 and OpenCV 5 both require NumPy ≥ 2; the old `<2.0.0` cap makes the stack uninstallable. Verified installed: numpy 2.4.6. |
| D-06 | **PIN** | `opencv-python` (not `-headless`) | TDD lists "OpenCV" (Table 11, p18) | Ultralytics declares `opencv-python`; installing the headless variant instead produces two `cv2` distributions in one environment. No GUI functions are used, so behaviour is unchanged. |
| D-07 | **PIN** | PyTorch `2.11.0+cu128` / torchvision `0.26.0+cu128` from the official cu128 index | TDD Table 11, p18 requires "CUDA build for CUDA 12.8 or newer (supports compute capability 12.0)" and forbids unofficial builds | The RTX 5060 is Blackwell, compute capability **(12, 0)** = `sm_120`; older CUDA wheels contain no kernels for it. Verified at runtime: `torch.cuda.is_available() == True`, `sm_120` present in `torch.cuda.get_arch_list()`, real matmul on device 0 succeeded. **No CUDA Toolkit was installed** — the wheel ships its own runtime, which TDD §14, p18 permits ("A separate CUDA toolkit is installed only if the chosen setup requires it"). |
| D-08 | **PIN** | Frontend: React 19, TypeScript 7, Vite 8, Tailwind CSS 4 via `@tailwindcss/vite`; `react-router-dom` for routing; native `fetch` instead of axios; no Vitest | TDD Table 11, p18 names React/TypeScript/Vite/Tailwind without versions; TDD §12, p17 uses `fetch`; TDD §16.1, p20 names no JS test runner | Tailwind 4 with the Vite plugin is the current documented Tailwind-for-Vite setup, which is what the TDD asks to follow. `npm run build` verified: TypeScript project build + production bundle succeed. |
| D-09 | **PIN** | PyMuPDF is a *stage-2 tool only*, not an application dependency | Not in TDD Table 11, p18 | It was installed solely to extract and verify the three PDFs. It must **not** appear in the pinned application requirements; keeping it there would add a large unused dependency. |
| D-10 | **PIN** | Webcam capture path = backend capture (Option B), DirectShow, MJPEG | TDD §9, p13 ("Decision (PRD v1.1 FR-03): backend capture (Option B)") | This closes the PRD §4.3 "camera path decision must be recorded before development" item at the architecture level. It still has to be repeated in the project report. **No camera code exists yet, so it is recorded, not implemented.** |

### 5.1 Version pins recorded for the report

Exact versions installed and verified on this machine (see
[`DEPENDENCY_MATRIX.md`](DEPENDENCY_MATRIX.md) for the compatibility reasoning):

| Component | Pinned version |
| :--- | :--- |
| Python | 3.11.9 |
| torch / torchvision | 2.11.0+cu128 / 0.26.0+cu128 |
| ultralytics | 8.4.202 |
| opencv-python | 5.0.0.93 |
| numpy | 2.4.6 |
| fastapi / uvicorn / starlette | 0.162.0 / 0.54.0 / 1.10.0 |
| pydantic | 2.14.2 |
| pillow | 13.0.0 |
| scikit-learn | 1.9.1 |
| imageio-ffmpeg | 0.8.1 |
| pytest | 9.2.0 |
| Node.js / npm | 24.19.0 / 11.16.0 |
| FFmpeg (system) | 9.0-full_build, `libx264` present |

### 5.2 Stage 4.1 ratified decisions (N-02, N-08, N-09, AC-18 policy)

Ratified by Ram on **5 November 2026** (S4-T2, Part A). These are the items discovered in Stage 3.1
and proven in Stage 4.1; they were never part of the Stage 2 D-series. Evidence for every claim:
[`ROADVISION_S4_T1_REPORT.md`](ROADVISION_S4_T1_REPORT.md) §5, backed by the raw gate log in its §3.

| ID | Type | Ratified decision | Why | How it is enforced |
| :--- | :--- | :--- | :--- | :--- |
| **N-02** | **RATIFIED** (deviation) | End-to-end NMS-free inference is selected with **`nms=False`**. The deprecated `end2end=` keyword is never used in new code. Default `predict()` arguments select the one-to-many branch with **external NMS**. | Installed Ultralytics 8.4.202 translates `end2end` onto `nms` and emits `"Use 'nms=None' instead"`; the TDD's literal `{"end2end": False, "iou": 0.7}` would therefore select the *opposite* of the intended default. | One process-wide mode constant; the same value is passed to train, val and predict; `nms_mode` is stored per inspection and per evaluation result. |
| **N-09** | **RATIFIED** (new constraint) | Each model instance keeps **one inference mode for its entire lifetime**. Modes are never switched on the same model object. | `predict()` re-runs `fuse()`, which deletes the unused head; a later call with the opposite mode cannot restore it, so the mode is sticky and silently wrong. Demonstrated: `end2end` stayed `True` after a following default-argument call. | The model manager builds a fresh instance per mode and asserts `backend.end2end` at load; a runtime mode change requires a reload. |
| **N-08** | **RATIFIED** (isolation) | Ultralytics configuration is **project-local**: `YOLO_CONFIG_DIR` is set *before* importing Ultralytics, and every dataset/weights/runs path passed to Ultralytics is **absolute and project-owned**. Another project's global configuration is never modified. | The machine-wide `%APPDATA%\Ultralytics\settings.json` currently points `datasets_dir` at `C:\Users\ramsa\Desktop\LiveFaceProject\datasets`, and `weights_dir`/`runs_dir` are relative (`weights`, `runs`), so they resolve against whatever the current directory happens to be. | Documented paths below; the serving and training processes set `YOLO_CONFIG_DIR` first; no code relies on `datasets_dir`. |
| **AC-18 policy** | **RATIFIED** (policy) | The serving environment sets `YOLO_OFFLINE=1`, and Ultralytics settings **synchronization is disabled** in the project-local settings file. Effective settings are read back and recorded. **An environment variable alone is explicitly not accepted as proof of complete network isolation.** | AC-18 (PRD §6 p10) requires local-only processing with no external calls; the variable is a library-level hint, not an OS-level guarantee. | Effective values recorded at start-up (see below); OS-level verification (process-scoped firewall rule or connection monitoring during one inference) is a separate, still-outstanding check. |

**Chosen paths (N-08).** All are absolute, project-owned, and inside the repository's existing
data/model trees. The repository directory contains a space, so any generated `data.yaml` must
quote its `path:` value.

| Purpose | Absolute path |
| :--- | :--- |
| Ultralytics config dir (`YOLO_CONFIG_DIR`) | `C:\Users\ramsa\Desktop\roadvision ai\.ultralytics` |
| Raw dataset (immutable) | `C:\Users\ramsa\Desktop\roadvision ai\data\raw\RDD2022` |
| Preserved archives | `C:\Users\ramsa\Desktop\roadvision ai\data\raw\_archives` |
| Dataset metadata from the source listing | `C:\Users\ramsa\Desktop\roadvision ai\data\raw\_meta` |
| Converted labels (later stage) | `C:\Users\ramsa\Desktop\roadvision ai\data\annotations` |
| Frozen YOLO split (later stage) | `C:\Users\ramsa\Desktop\roadvision ai\dataset` |
| Model weights | `C:\Users\ramsa\Desktop\roadvision ai\models\weights` |
| Training/validation runs | `C:\Users\ramsa\Desktop\roadvision ai\models\runs` |

**Effective-settings verification method (AC-18).** The check is: (1) set
`YOLO_CONFIG_DIR` to the table above before the first `import ultralytics`; (2) confirm
`ultralytics.utils.SETTINGS_FILE` resolves under that directory; (3) confirm
`SETTINGS["sync"] is False`; (4) confirm `env_bool("YOLO_OFFLINE") is True`; (5) record all four
values in the run log. Step (6), proving no socket is opened, is **not** claimed by this document
and remains an OS-level test. No global `settings.json` is modified by any of this.

**Still open and not covered by these ratifications:** Q-01, Q-03 … Q-11, C-01 … C-04, G-01 … G-06,
A-02, A-04, A-05, A-07, A-09.

---

## 6. Assumptions to prove at implementation time

The TDD states that its listings are *"design proposals: they were syntax-checked but not
executed against RDD2022, YOLO26 or the project GPU, and must be tested during implementation"*
(TDD front matter, p1). The following therefore remain **unproven** even though the environment
installs and runs.

| ID | Assumption | Where it comes from | How to prove it | Current evidence |
| :--- | :--- | :--- | :--- | :--- |
| A-01 | `**NMS_ARGS` accepts `end2end` (and `iou`) as `predict()` keywords in Ultralytics 8.4.202 | TDD §3.3, p6 (`NMS_ARGS = {}` or `{"end2end": False, "iou": 0.7}`), §16 p20 | Run one image with both `NMS_ARGS` values and compare detection counts | **VERIFIED (S4-T1)** — `end2end=False` still executes but is deprecated (`"Use 'nms=None' instead"`) and selects external NMS; `nms=False` selects the NMS-free head (`backend.end2end == True`). Default arguments select external NMS. See N-02. |
| A-02 | `res.plot()` returns a BGR `ndarray` safe to feed directly to `cv2.imencode` | TDD §9, p13 | Encode `res.plot()` to JPEG and check channel order visually | **NOT TESTED** |
| A-03 | `device=DEVICE` with `DEVICE = "0"`-style strings selects the GPU | TDD §3.3, p5–6 (`device=DEVICE`) vs §14, p18 gate script (`device=0`) | Print `torch.cuda.is_available()` and the resolved device during a real detect call | **VERIFIED (S4-T1)** — `select_device(0)` and `select_device("0")` both resolve to `cuda:0`; a prediction driven through `device="0"` ran on `cuda:0`. |
| A-04 | Ultralytics accepts `.txt` image lists as a training source | TDD Appendix C, p22 (explicitly unverified), Appendix B, p22 (optional) | Build a 4-image list and run a 1-epoch smoke train | **NOT TESTED** — relevant only if Q-06 chooses lists |
| A-05 | Served MP4 files seek correctly in the browser | TDD Appendix C, p22 | Open the result route in Chrome and drag the seek bar | **NOT TESTED** |
| A-06 | YOLO26 architecture is available in the installed Ultralytics build | TDD §3.1–3.2, p5 | Build `YOLO("yolo26n.yaml")` and run a forward pass | **VERIFIED (smoke)** — `yolo26n.yaml` built and ran on GPU (≈20.4 ms/frame, blank 640 px image) and on CPU. `yolo26m` weights were **not** downloaded, by instruction. |
| A-07 | OpenCV 5.0 behaves like 4.x for `VideoCapture`, `imencode`, `VideoWriter` and `CAP_DSHOW` | TDD §8–9, p11–13 (written against OpenCV 4-era APIs) | Run the video round-trip and the camera open on the target laptop | **PARTIALLY TESTED** — `imencode`/`imdecode` round-trip and an `mp4v` `VideoWriter` succeeded; `VideoCapture` of a real file and DirectShow camera open are **NOT TESTED** |
| A-08 | `starlette.testclient` + httpx 0.28.1 is acceptable for API tests | TDD §16.1, p20 | Run the test suite | **VERIFIED WITH WARNING** — `TestClient` returns 200 for `/api/health`, but emits `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead`. Decide at test-writing time whether to move to httpx2. |
| A-09 | YOLO26m training fits in 8 GB VRAM at the chosen batch size | TDD §14, p18 (VRAM "to be recorded"), Appendix C, p22 | Run `training/verify_gpu.py`, then a 1-epoch smoke train with `batch=4` and watch peak memory | **NOT TESTED** — no dataset and no training were permitted in this stage. Recorded VRAM: 8151 MiB total, 7.96 GiB visible to PyTorch. |

---

## 7. What is *not* a conflict (checked and cleared)

To avoid re-litigating settled points, these were compared across all three documents and
**agree**:

- Class list and index order: `0=D00, 1=D10, 2=D20, 3=D40` (Proposal §5, PRD §4.4 p5, TDD §1–2).
- Primary/fallback models: YOLO26m / YOLO26n (all three).
- Input modes: image, recorded video, live webcam (all three).
- Target hardware: Windows 11, RTX 5060 Laptop GPU, 16 GB RAM (Proposal §5.3, PRD §6 p10, TDD §14 p18).
- Local-only processing, no paid cloud (Proposal §1/§3, PRD §6 p10, TDD §15 p19).
- Seven-day schedule and two-person team (Proposal §10, TDD §17 p20).
- Out-of-scope items (PRD §9 p11 vs TDD §1 p4): multi-user, authentication, cloud, mobile app,
  engineering-grade measurement, autonomous repair decisions.

---

## 8. Sign-off

| Item | Owner | Decision recorded on | Notes |
| :--- | :--- | :--- | :--- |
| C-01 … C-04 | RoadVision team | *(pending)* | Must be closed before the corresponding module starts |
| Q-01 … Q-11 | RoadVision team | *(pending)* | Q-01 still blocks the first backend commit; **Q-02 ratified 2026-11-05** (see §5.2); **Q-03/Q-04 implementation-approved 2026-11-06 (S4-T3B)** — Q-03 applied Policy A fallback because the V2 gate is not closed; Q-04 implemented Hamming ≤3, 80/10/10, seed 42 (see §3) |
| D-01 … D-10 | RoadVision team (ratify Stage-2 choices) | *(pending)* | D-07 is verified working; the rest are pins, not experiments |
| **N-02, N-08, N-09, AC-18 policy** | **Ram (AI/CV)** | **2026-11-05 (S4-T2)** | Ratified in §5.2. N-02 and N-09 bind the model manager; N-08 and the AC-18 policy bind training and serving start-up. |
| G-01 … G-06 | Implementer, approved by team | *(pending)* | Suggested defaults are proposals only |
| A-01 … A-09 | Implementer | *(pending)* | A-01 and A-03 verified in S4-T1; the rest keep their proof methods above |
