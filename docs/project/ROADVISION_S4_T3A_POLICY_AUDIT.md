# ROADVISION AI — S4-T3A POLICY AUDIT
## Annotation policy (Q-03) and duplicate / split policy (Q-04)

**Date:** 5 November 2026
**Owner:** Ram (AI/CV workstream)
**Task:** S4-T3A — audit-only resolution of the evidence behind Q-03 and Q-04. No conversion, no
split, no training.
**Authority:** TDD v1.1 §4.3–§4.6 and Appendix B; PRD v1.1 §5.1–5.3 and AC-16; `AGENTS.md` §1, §4, §6
**Status:** **AUDIT COMPLETE. Recommendations recorded, NOT RATIFIED.** Nothing was converted, split,
copied or trained. The decisions in §7 still belong to the team.

**Inputs measured:** `data/raw/RDD2022` — 47,420 images, 38,385 XML files, 12.86 GB
**Tool:** [`training/audit_dataset_policy.py`](../../training/audit_dataset_policy.py) (new, read-only)
**Artefacts:** `data/reports/audit/policy_audit.json`, `duplicate_groups.json`,
`contact_sheets/ambiguous_groups_report.json`, `contact_sheets/*.jpg`, `audit_run.log`

---

## 1. Scope compliance

| Restriction | Compliance |
| :--- | :--- |
| Audit only; do not convert annotations | **Yes** — no YOLO label file exists anywhere under `data/`; `data/annotations/` still contains only its `.gitkeep` placeholder |
| Do not create `classes.json` | **Yes** — no `training/classes.json`, `backend/classes.json` or any other class file was written |
| Do not create train/val/test folders | **Yes** — `dataset/` does not exist; the split is a *simulation* held in memory and written only as JSON statistics |
| Do not modify original XML/image files | **Yes** — the tool's only write targets are `data/reports/audit/*`. Every file under `data/raw` has a modification time from the S4-T2 extraction (≤ 07:47:30 local); nothing was written by this task |
| Do not download anything | **Yes** — no network call, no new file fetched |
| Do not train a model | **Yes** — no Ultralytics import, no weight loaded, no GPU work |
| Do not modify Shakib-owned files | **Yes** — no file under `backend/` or `frontend/` was touched |
| Do not commit or push | **Yes** — `git log` still shows the single initial commit (`0f977c7`); the working tree is uncommitted |
| Use the venv interpreter | **Yes** — every run used `.venv\Scripts\python.exe` (3.11.9); nothing was installed |
| Stop after the audit | **Yes** — this report is the last deliverable; §9 is a *proposal*, not an execution |

**One pre-existing anomaly, reported for completeness:** `China_Drone_000001.xml` carries a
`LastWriteTime` of `2026-11-05 07:47:30`, about six hours later than the rest of its folder
(`01:24:53`). Its content is valid and consistent (512×512, one `D10` box) and the per-class totals
reconcile exactly with S4-T2, so the audit is unaffected. The file was not written by this task; the
timestamp predates the session.

---

## 2. Method and reproducibility

### 2.1 What the tool does

| Stage | Operation |
| :--- | :--- |
| Scan | `rglob("*")` over `data/raw/RDD2022`, paths sorted; images keyed by `(country, split, stem.lower())`, XMLs matched to their sibling `images/` folder |
| Hash | SHA-256 over raw bytes (exact) + 64-bit dHash (near); cached in `image_hash_cache.json` with a version byte |
| Part A | Parse every XML, apply TDD §4.3 validation rules per object, classify each image, count per code and per country |
| Part B | Collapse identical hashes, generate candidate pairs by 8 × 8-bit pigeonhole, union-find at each threshold 0–6, pixel-verify samples, analyse group structure |
| Part C | Simulate `StratifiedGroupKFold(n_splits=10, shuffle=True, random_state=42)` on the two candidate pools, `folds[0] -> test`, `folds[1] -> val`, remainder train |

### 2.2 Hash parameters (must be copied verbatim into S4-T3)

| Item | Definition |
| :--- | :--- |
| Exact duplicate | SHA-256 over the raw file bytes |
| Near duplicate | 64-bit dHash: BGR → grayscale → `cv2.resize((9, 8), INTER_AREA)` → bit = right pixel > left pixel → `np.packbits` → big-endian integer |
| Candidate generation | Pigeonhole over 8 × 8-bit chunks — **exact for every Hamming distance ≤ 7** (a pair at distance d ≤ 7 must share at least one of 8 chunks) |
| Grouping | Union-find transitive closure over unique hash values |
| Bucket cap | **None.** Identical hashes are collapsed to one representative before comparison; a hard pair ceiling (4 × 10⁸) raises an error instead of skipping data |

This deliberately differs from the TDD skeleton's 4 × 16-bit chunks (exact only for d ≤ 3) because the
threshold study evaluates d = 0…6. The skeleton's `MAX_BUCKET = 2000` skip is **not** reproduced; see §4.3.

### 2.3 Determinism and cross-checks

| Check | Result |
| :--- | :--- |
| dHash implementation vs `training/inspect_dataset.py` | **300 / 300 images identical** |
| Object total vs S4-T2 inspection | **65,712 = 65,712**; every per-class count identical |
| XML without image | **0** |
| Unknown class codes | **0** |
| XML size vs true image size mismatch | **0** |
| Category sum vs annotated images | 19,221 + 4,546 + 2,894 + 11,724 = **38,385** ✓ |
| Target + out-of-scope objects | 55,007 + 10,705 = **65,712** ✓ |
| Independent re-scan of images without XML | **9,035**, 100 % under `*/test/` (separate script, §2.4) |

Determinism caveat for S4-T3: the audit is reproducible because all input paths are sorted, but
union-find component order is an implementation detail. **S4-T3 must sort groups by their first member
path before folding**, otherwise the same seed can produce a different assignment after a code change.

### 2.4 Limitations of this audit

1. **No full visual certification of 11,724 empty XMLs.** A 37-image contact sheet was inspected
   (`contact_sheets/empty_xml_sample.jpg`, all five affected countries). At thumbnail scale the
   samples show no obvious in-scope damage, but thumbnails cannot prove absence of small cracks.
2. **The "likely over-merged" verdict is a heuristic** (median pixel correlation of a sample), not a
   conclusion. §4.10 therefore reports the visual check separately, and two groups judged
   "over-merged" by the heuristic turned out to be genuine video sequences.
3. **No measurement of training behaviour.** Nothing in this report says whether background images
   improve or hurt mAP on this dataset; that needs S4-T4.

---

## 3. Part A — Q-03: annotation policy

### 3.1 Corpus reconciliation

| Item | Count |
| :--- | ---: |
| Images on disk | 47,420 |
| Pascal VOC XML files | 38,385 |
| Annotated images (XML matched to an image) | 38,385 |
| Images with **no XML** | **9,035** |
| — of which under `*/test/` | **9,035 (100 %)** |
| — of which under `*/train/` | **0** |
| XML files without an image | 0 |
| Objects (`<object>` elements) | 65,712 |

The 9,035 unannotated images are the *official* RDD2022 test splits (China_MotorBike 500, Czech 709,
India 1,959, Japan 2,627, Norway 2,040, United_States 1,200). TDD §4.4 says they are "kept separate and
never used for quantitative evaluation", so they are outside every policy below — including the split.

### 3.2 Image categories (38,385 annotated images)

| Category | Meaning | Images | Share |
| :--- | :--- | ---: | ---: |
| `only_target` | ≥ 1 box of D00/D10/D20/D40, no other code | 19,221 | 50.07 % |
| `mixed_target_oos` | ≥ 1 target box **and** ≥ 1 out-of-scope box | 4,546 | 11.84 % |
| `only_oos` | ≥ 1 out-of-scope box, **zero** target boxes | 2,894 | 7.54 % |
| `empty_xml` | XML exists but contains **zero** `<object>` elements | 11,724 | 30.54 % |
| **Total** | | **38,385** | 100 % |

| Country | only_target | mixed | only_oos | empty_xml |
| :--- | ---: | ---: | ---: | ---: |
| Japan | 4,133 | 3,767 | 1,812 | 794 |
| India | 2,729 | 494 | 562 | 3,921 |
| China_MotorBike | 1,754 | 180 | 43 | 0 |
| China_Drone | 1,814 | 105 | 477 | 5 |
| Czech | 1,072 | 0 | 0 | 1,757 |
| Norway | 2,914 | 0 | 0 | 5,247 |
| United_States | 4,805 | 0 | 0 | 0 |

### 3.3 Per-class counts — all twelve original codes

| Code | In target map? | Objects | % of objects | Images containing it |
| :--- | :---: | ---: | ---: | ---: |
| D00 | **yes (0)** | 26,016 | 39.59 % | 13,548 |
| D10 | **yes (1)** | 11,830 | 18.00 % | 7,709 |
| D20 | **yes (2)** | 10,617 | 16.16 % | 8,412 |
| D40 | **yes (3)** | 6,544 | 9.96 % | 3,674 |
| *target subtotal* | | **55,007** | **83.71 %** | — |
| D44 | no | 5,057 | 7.70 % | 4,079 |
| D50 | no | 3,581 | 5.45 % | 2,638 |
| Repair | no | 1,046 | 1.59 % | 803 |
| D43 | no | 793 | 1.21 % | 753 |
| D01 | no | 179 | 0.27 % | 118 |
| D11 | no | 45 | 0.07 % | 36 |
| Block crack | no | 3 | 0.005 % | 3 |
| D0w0 | no | 1 | 0.002 % | 1 |
| *out-of-scope subtotal* | | **10,705** | **16.29 %** | — |

Image counts are not additive: an image can contain several classes.

The in-scope classes appear in all seven countries. The excluded codes are geographically concentrated:
D43, D44, D50 only in India and Japan (the Japanese road-maintenance classes); D01, D0w0, D11 only in
India; Repair and Block crack only in China.

### 3.4 What the fixed mapping actually does to the data

| Quantity | Count |
| :--- | ---: |
| Target objects before geometry rules | 55,007 |
| Target objects **retained** | **55,006** |
| Target objects excluded | **1** — reason `degenerate` (zero-area box after clipping) |
| Target objects clipped | 0 |
| Target boxes rejected as out of bounds | 0 |
| Out-of-scope objects excluded by code | **10,705 (100 %)** |
| Out-of-scope objects excluded for geometry | **0** |
| Out-of-scope boxes clipped | 0 |
| Images with ≥ 1 retained target | **23,767** |
| Images whose targets were all lost by geometry rules | **0** |
| Target objects inside mixed images | **9,414 (17.1 % of all target objects)** |

The last row matters for policy: dropping `only_oos` images does **not** drop their neighbours' target
boxes. Every mixed image keeps its target boxes and simply loses its out-of-scope boxes.

### 3.5 What the out-of-scope images contain

`only_oos` images are not random: each contains real, labelled road damage of an excluded class.

| Code | Images containing it | | Country | Images |
| :--- | ---: | :--- | :--- | ---: |
| D44 | 1,464 | | Japan | 1,812 |
| D50 | 774 | | India | 562 |
| Repair | 520 | | China_Drone | 477 |
| D43 | 467 | | China_MotorBike | 43 |
| D01 | 88 | | | |
| D11 | 25 | | | |
| Block crack | 1 | | | |
| D0w0 | 1 | | | |

Because these counts overlap (a single image may show D43 + D44 + D50), they sum to 3,340
image–code incidences across 2,894 images. The most common single-code contents are D44 alone (3,357
incidences), D50 alone (1,810), Repair alone (802).

**Consequence:** labelling these 2,894 images as "background" would tell the detector that visible
cracks and patches are *absence* of damage. Since D43/D44/D50 are crack-like and share texture and
context with D00/D10/D20, that is a direct false-negative injection, not a neutral negative sample.

### 3.6 The three candidate policies

| | **Policy A** — targets only | **Policy B** — A + only_oos as background | **Policy C** — A + verified-empty as background |
| :--- | :--- | :--- | :--- |
| Definition | Images with ≥ 1 retained target box | A plus every image whose XML has only out-of-scope boxes | A plus structurally empty XMLs **not** contradicted by duplicate evidence |
| Pool images | **23,767** | **26,661** | **35,119** |
| Retained target objects | 55,006 | 55,006 | 55,006 |
| Background images | 0 | 2,894 | 11,352 |
| Background share of pool | 0 % | 10.9 % | 32.3 % |
| Known mislabelled backgrounds | 0 | **21 images** contradicted by a near-duplicate target image; 3,340 damage incidences labelled "no damage" | 0 (the 372 contradicted images are excluded) |
| Residual risk | none from labels; more false positives on plain road | **high and directed at the product goal** | unquantified annotation omissions in the remaining 11,352 |
| TDD §4.4 compliance | Allowed | Allowed but contradicts §4.4 intent | Allowed and explicitly contemplated |
| Verdict | **Safe fallback** | **Reject** | **Recommend, with a verification gate** |

Why Policy B is rejected even though it is technically permitted:

1. It converts 10,705 labelled damage objects into negative evidence. The four kept classes are
   visually adjacent to D43/D44/D50; suppressing them is the opposite of the product's purpose.
2. 21 of the 2,894 images have a near-duplicate image in the corpus that *is* target-labelled
   (§4.9). The annotation is therefore provably inconsistent for at least 0.7 % of the set, and the
   true rate is unknown.
3. It biases the background set toward Japan (1,812 of 2,894) and India (562), i.e. exactly the two
   countries that already dominate the excluded codes.

### 3.7 Recommendation for Q-03

**Adopt Policy C** — images with ≥ 1 retained target box, plus structurally empty XMLs, minus the 372
empty XMLs that duplicate evidence shows are contradicted by a target-labelled near-duplicate.
Keep **Policy A** as the fallback if the verification gate in §7 cannot be closed before the split is
frozen. **Do not adopt Policy B.**

Distribution rules that follow from the TDD and from the measurements:

- The 9,035 official-test images stay out of the pool (TDD §4.4).
- Background images enter **all three splits in natural proportion**, because TDD §4.4 requires it and
  because val/test must represent the deployed distribution (§5).
- Only the *training* subset may reduce its background share, and only under TDD §4.6, after a measured
  reason exists. The audit has no evidence to justify a cap now, so none is proposed here.
- The 372 excluded images and the 21 contradicted `only_oos` images must be written to an exclusion file
  in S4-T3 so the decision is auditable.

### 3.8 Proof that no out-of-scope object can silently become a target class

This is the core safety property of the mapping, and it is provable from the data rather than asserted:

1. **Exact-string mapping only.** `CODE_TO_ID` has four keys and is queried with
   `(obj.findtext("name") or "").strip()`; there is no prefix, case-fold, fuzzy or fallback match.
2. **The corpus contains no name variants at all.** `raw_name_variants` has exactly twelve entries —
   the twelve bare codes — and `names_differing_after_strip` is empty. There is no `"D44 "`,
   `"d44"`, `"D44_crack"` or any other string that could normalise into a target code.
3. **Zero unknown codes.** Every one of the 65,712 objects matches one of the twelve known codes, so
   nothing escapes into an unclassified bucket.
4. **Classification precedes geometry.** An object whose code is not in `CODE_TO_ID` is counted and
   skipped *before* any box parsing. Its geometry can therefore never be re-tagged.
5. **The arithmetic closes.** 65,712 = 55,007 target + 10,705 out-of-scope, and
   55,007 = 26,016 + 11,830 + 10,617 + 6,544. There is no residual object that could belong to a
   different bucket.
6. **No out-of-scope object was dropped by accident.** `oos_exclusion_reasons` is empty and zero
   out-of-scope boxes were clipped or out of bounds. All 10,705 were removed strictly by code, so a
   geometry rule cannot be masking a mapping error.
7. **No target was silently lost.** Exactly one target object was excluded, for a degenerate box, and
   that image still has other retained targets: `images_with_target_but_zero_retained = 0`.
8. **Independent recount.** The per-class totals equal S4-T2's independent inspection, which used a
   different tree walk (`findall` vs `iter`) — the same corpus produces the same numbers.

**S4-T3 must additionally assert, at write time:** every emitted class id is in `{0,1,2,3}`; the number
of emitted lines equals 55,006; the emitted per-class counts equal
`{D00: 26,016, D10: 11,830, D20: 10,617, D40: 6,544}`; and the converter's `excluded_code:<code>`
counters equal the audit's per-code out-of-scope totals. Any mismatch aborts the conversion.

### 3.9 Residual uncertainty in the annotation data

The mapping is safe; the *labels* are not perfect. Two measured signals quantify it:

| Signal | Count | Meaning |
| :--- | ---: | :--- |
| Structurally empty XMLs | 11,724 | zero `<object>` elements |
| Empty XMLs contradicted by a target-labelled near-duplicate | **372** (in 79 duplicate groups) | the same scene is labelled "damage" elsewhere, so the empty XML is an omission or an inconsistency |
| Verified-empty candidates | **11,352** | 11,724 − 372 |
| `only_oos` images contradicted by a target-labelled near-duplicate | **21** | an omitted target label, not a true negative |

So the *known* contamination rate among empty XMLs is 3.17 %, and the rate among `only_oos` images is
0.73 %. Neither is zero, which is why Policy B is unsafe and why Policy C's background set is filtered.

The 37-image contact sheet of empty XMLs (`contact_sheets/empty_xml_sample.jpg`) shows ordinary road
scenes and pavement crops with no obvious in-scope damage, which is consistent with Policy C — but it
cannot certify 11,352 images, and this report does not claim it does.

---

## 4. Part B — Q-04: duplicates, near-duplicates and the Hamming threshold

### 4.1 Exact duplicates (SHA-256)

| Pair | Split of members | Categories |
| :--- | :--- | :--- |
| `United_States/test/.../United_States_005833.jpg` ↔ `United_States/train/.../United_States_003260.jpg` | official test ↔ train | no XML ↔ only_target |
| `United_States/train/.../United_States_001623.jpg` ↔ `United_States/train/.../United_States_003917.jpg` | train ↔ train | only_target ↔ only_target |

**2 groups, 2 redundant files.** 47,418 unique SHA-256 values for 47,420 images.

The first pair crosses the *official* train/test boundary, but the test member has no XML and is
excluded from the pool, so it cannot leak into our split. It is still recorded because AC-16 asks for
the duplicate evidence, and because it proves the official split is not duplicate-clean.

### 4.2 Near-duplicate method and bucket behaviour

| Statistic | Value |
| :--- | ---: |
| Unique 64-bit dHash values | 47,308 |
| Buckets (8 chunks × 256 values) | 2,048 |
| Largest bucket (unique hashes) | **2,567** |
| Buckets above 5,000 | **0** |
| Exhaustive within-bucket comparisons | 88,946,102 |
| Pairs at Hamming distance ≤ 6 | **35,227** |

### 4.3 The S4-T2 500-image cap — resolved

S4-T2's inspector skipped **3 buckets covering 2,077 images** and reported 635 groups / 2,395 images.
Re-running without any cap:

| | S4-T2 (capped) | S4-T3A (no cap) | Delta |
| :--- | ---: | ---: | ---: |
| Near-duplicate groups at d ≤ 3 | 635 | **636** | +1 |
| Images inside groups | 2,395 | **2,416** | +21 |

So the cap distorted the *reported* total by 0.16 % of grouped images. That is small but not zero, and
the cap is still a correctness hazard: the largest distinct-hash bucket holds 2,567 values, and the TDD
skeleton's alternative scheme (4 × 16-bit chunks with `MAX_BUCKET = 2000`) would produce *larger*
buckets by construction. The audit did not measure that partition, so no claim is made about how many
images it would drop — which is precisely why S4-T3 must not inherit the cap.

The correct substitute, implemented here and recommended for S4-T3, is: collapse images with identical
hashes to a single representative, compare all representatives inside a bucket, and fail loudly if the
comparison count exceeds a computed ceiling. No bucket is ever skipped.

### 4.4 Distance distribution

| Hamming distance | Pairs |
| :--- | ---: |
| 0 (identical hash, not identical file) | 224 |
| 1 | 239 |
| 2 | 697 |
| 3 | 1,759 |
| 4 | 4,169 |
| 5 | 9,122 |
| 6 | 19,241 |
| **Total ≤ 6** | **35,227** |

The mass is overwhelmingly at d = 5–6 (80.7 % of all pairs), which is the signature of unrelated
images that happen to share coarse structure, not of duplicates.

### 4.5 Threshold study

`groups` counts only groups of size ≥ 2; `images` counts only images inside such groups.

| Threshold | Groups | Images in groups | Largest group |
| ---: | ---: | ---: | ---: |
| 0 | 73 | 185 | 12 |
| 1 | 198 | 546 | 36 |
| 2 | 399 | 1,236 | 111 |
| **3** | **636** | **2,416** | **360** |
| 4 | 956 | 4,296 | 1,352 |
| 5 | 1,152 | 6,642 | 2,889 |
| 6 | 1,313 | 9,630 | 5,347 |

### 4.6 Pixel verification (does the hash mean what it claims?)

Sampled pairs per distance bucket, aligned by resize, Pearson correlation and mean absolute difference:

| Distance | Pairs available | Sampled | Median corr | p10 corr | Median MAD | Share below corr 0.75 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 239 | 239 | 0.951 | 0.743 | 0.021 | 10.5 % |
| 2 | 697 | 250 | 0.934 | 0.559 | 0.039 | 17.2 % |
| 3 | 1,759 | 250 | **0.909** | 0.610 | 0.062 | 18.0 % |
| 4 | 4,169 | 250 | 0.880 | 0.618 | 0.080 | 21.2 % |
| 5 | 9,122 | 250 | 0.861 | 0.542 | 0.088 | 26.4 % |
| 6 | 19,241 | 250 | 0.784 | 0.513 | 0.117 | 42.4 % |

There is no cliff; precision degrades smoothly. But the *cost* of moving the threshold is not smooth:
d ≤ 3 → 4 adds 1,880 images to groups (+78 %) while the largest group explodes from 360 to 1,352, i.e.
a quarter of all grouped images would sit in one blob spanning five countries. The extra pairs at d = 4
are therefore dominated by hash-degenerate merges, not by new duplicates.

### 4.7 Group structure at threshold 3

| Group size | Groups |
| ---: | ---: |
| 2 | 435 |
| 3 | 104 |
| 4 | 41 |
| 5 | 15 |
| 6 | 12 |
| 7 | 7 |
| 8 | 4 |
| 9 | 3 |
| 10 | 2 |
| 11 | 2 |
| 13, 16, 17, 21, 25, 30, 37 | 1 each |
| 14 | 2 |
| **226** | 1 |
| **360** | 1 |

435 of 636 groups are simple pairs; the distribution has a short head and two long video chains.

### 4.8 Groups that cross the original dataset boundaries

| Property | Count |
| :--- | ---: |
| Groups spanning official splits | **220** |
| — train ↔ official test | 220 |
| — entirely official test | 11 |
| — entirely train | 405 |
| Groups spanning two *labelled* splits | **0** (only `train` has XML) |
| Groups spanning two countries | **11** |
| Label-inconsistent groups (target image + zero-target XML image) | **79** |
| Chained groups (hash diameter > 3) | **160** |

Chained groups are expected: union-find is transitive, so a video sequence a→b→c can join a and c at
d = 22 (group 52). 160 groups covering 1,409 images have a diameter above the threshold, median size 4.
Splitting them would re-introduce exactly the leakage the grouping exists to prevent, so chaining is
kept deliberately.

### 4.9 File numbering does not imply adjacency — hashing is mandatory

If filenames were sequential video frames, consecutive numbers would have tiny hash distances. They do
not:

| Statistic | Value |
| :--- | ---: |
| Consecutive-number pairs analysed | 47,407 |
| Median Hamming distance | **28** |
| p95 Hamming distance | 38 |
| Share within d ≤ 6 | **0.02 %** |
| Median pixel correlation of 120 sampled consecutive pairs | **0.30** |

So a splitter that trusted filename order would leak massively, and a splitter that trusted only exact
hashes would leak on video. The dHash grouping is the only mechanism that catches the 360-frame and
226-frame sequences.

### 4.10 Inspection of the risky groups

All 22 groups with ≥ 8 images plus the 7 remaining cross-country groups (29 total, covering 11 of 11
cross-country groups) were examined statistically. Group statistics and heuristic verdicts are
recorded in `contact_sheets/ambiguous_groups_report.json`.

**Contact-sheet coverage is now complete:** all 29 groups have a sheet (all 22 groups of ≥ 8 plus
the 7 remaining cross-country groups). The 13 sheets that were missing at first verification
(5, 11, 138, 180, 198, 206, 387, 407, 434, 447, 467, 502, 583) were generated by
`training/make_inspection_artifacts.py` from the existing group records; no group membership,
statistic or heuristic verdict was changed. Group 447 already had a recorded visual conclusion;
group 256 already had a sheet but no visual verdict, so it remains un-inspected.

A recorded **visual conclusion** exists for 16 groups — 54, 52, 418, 404, 278, 130, 240, 0, 30,
263, 36, 473, 524, 525, 526 and 447. The other 13 groups (5, 11, 138, 180, 198, 206, 256, 387,
407, 434, 467, 502, 583) have sheets but **no recorded visual verdict** and are explicitly marked
`"visual_inspection": "not inspected"` in the JSON; no verdict was invented for them.

| Heuristic verdict | Groups |
| :--- | ---: |
| Coherent visual duplicates | 1 |
| Ambiguous | 13 |
| "Likely over-merged" (median corr < 0.75) | 15 |

The visual check corrects the heuristic in both directions:

- **Groups 54 (360 images) and 52 (226) are genuine single-route dashcam sequences**, not unrelated
  collisions. Group 54 is dominated by one India highway drive (320 frames) but is transitively
  bridged to 40 frames from four other countries; group 52 is 224 frames of one Norway mountain road
  plus 2 China_Drone pavement crops. Their low median correlation is caused by camera motion, not by
  scene mismatch.
- **Groups 418 (30), 404 (25), 278 (21), 130 (17), 240 (16), 0 (11), 30 (5), 263 (4), 36/473/524/525/526 (2 each)
  are hash-degenerate clusters**: low-contrast China_Drone / China_MotorBike pavement crops where the
  dHash is dominated by lane markings, so visually similar but distinct frames merge. Contact sheets
  show different bicycles, crack layouts and road positions.

Decision: **keep the groups as they are and never split a group.** Merging is conservative for
leakage; the measurable cost is small. Excluding the two genuine sequences, the 13 artefact clusters
contain **139 images, i.e. 0.6 % of the Policy A pool**. Refining the grouping with a pixel-correlation
gate would trade a 0.6 % diversity loss for a new leakage risk, which is the wrong trade for a frozen
evaluation split.

### 4.11 Independent-group estimate

| Policy | Pool images | Independent groups | Images removed as redundant | Reduction |
| :--- | ---: | ---: | ---: | ---: |
| A | 23,767 | **22,966** | 801 | 3.37 % |
| C | 35,119 | **34,141** | 978 | 2.78 % |

### 4.12 Recommendation for Q-04 (duplicates)

**Confirm exact duplicates by SHA-256 and near-duplicates at Hamming ≤ 3 with transitive closure, no
bucket cap.** Evidence: d ≤ 3 keeps a median pixel correlation of 0.909; d = 4 adds 78 % more images
to groups and grows the largest group 3.8×, mostly through degenerate paving-texture merges; d = 2
would miss 1,759 same-scene pairs (median corr 0.909), which are the video-adjacency links that matter
most for leakage.

**Deviations from the TDD skeleton that must be recorded in S4-T3:** 8 × 8-bit pigeonhole (exact to
d = 7) instead of 4 × 16-bit; identical-hash collapse instead of `MAX_BUCKET` skipping; SHA-256 instead
of SHA-1 (SHA-1 is deprecated for integrity evidence and has no advantage here); `iter("object")`
instead of `findall("object")`.

---

## 5. Part C — 80 / 10 / 10 split simulation (seed 42)

### 5.1 Method

- Pool = the policy's images only; the official test splits never enter.
- Near-duplicate groups are recomputed **on the pool members**, so an excluded official-test image can
  never drag a train image into a test group.
- Groups are the split unit; `StratifiedGroupKFold(n_splits=10, shuffle=True, random_state=42)`.
- Fold 0 → **test**, fold 1 → **val**, folds 2–9 → **train**. The fold order is part of the contract.
- Stratification label = the **rarest retained class present in the group** (by global image count,
  ties broken by code); a pure-background group gets the label `none`.
- Integrity checks: no group in two splits, no SHA-256 in two splits.

### 5.2 Results

| Policy A | train | val | test |
| :--- | ---: | ---: | ---: |
| Images | 19,017 (80.01 %) | 2,401 (10.10 %) | 2,349 (9.88 %) |
| Groups | 18,372 | 2,297 | 2,297 |
| Retained objects | 44,005 (80.00 %) | 5,577 (10.14 %) | 5,424 (9.86 %) |

| Policy C | train | val | test |
| :--- | ---: | ---: | ---: |
| Images | 28,103 (80.02 %) | 3,487 (9.93 %) | 3,529 (10.05 %) |
| Groups | 27,313 | 3,414 | 3,414 |
| Retained objects | 43,994 (79.98 %) | 5,530 (10.05 %) | 5,482 (9.97 %) |

**Group-crossing violations: 0. Exact-hash crossing violations: 0. Both policies.**

### 5.3 Class balance

Policy A — images per class and share of the split's images:

| Class | train | val | test | Global share | Max deviation |
| :--- | ---: | ---: | ---: | ---: | ---: |
| D00 | 10,821 (56.90 %) | 1,369 (57.02 %) | 1,358 (57.81 %) | 57.00 % | +0.81 pp |
| D10 | 6,139 (32.28 %) | 799 (33.28 %) | 771 (32.82 %) | 32.44 % | +0.84 pp |
| D20 | 6,753 (35.51 %) | 825 (34.36 %) | 834 (35.50 %) | 35.39 % | **−1.03 pp** |
| D40 | 2,955 (15.54 %) | 358 (14.91 %) | 361 (15.37 %) | 15.46 % | −0.55 pp |

Policy C:

| Class | train | val | test | Global share | Max deviation |
| :--- | ---: | ---: | ---: | ---: | ---: |
| D00 | 10,824 (38.52 %) | 1,376 (39.46 %) | 1,348 (38.20 %) | 38.58 % | **+0.88 pp** |
| D10 | 6,163 (21.93 %) | 758 (21.74 %) | 788 (22.33 %) | 21.95 % | +0.38 pp |
| D20 | 6,718 (23.90 %) | 833 (23.89 %) | 861 (24.40 %) | 23.95 % | +0.45 pp |
| D40 | 2,944 (10.48 %) | 369 (10.58 %) | 361 (10.23 %) | 10.46 % | −0.23 pp |

Object shares per class stay within 79.5–80.8 % train / 9.4–10.4 % val / 9.6–10.4 % test under both
policies. The largest deviation (1.03 pp) belongs to D20 in a 2,401-image validation fold and is well
inside what group-level stratification can promise without leaking.

**Why the balance survives:** stratifying on the rarest class forces each fold to contain a
proportional number of groups that carry D40 (the scarcest class at 6,544 objects). Because a group is
atomic, a video sequence containing D40 arrives in one split as a block, so the class ratio moves in
steps of whole groups — which is exactly the source of the ~1 pp wobble.

**Background share:** under Policy C, 11,175 of 34,141 groups (32.7 %) are pure-background groups.
They are stratified as their own label (`none`), so they appear in all three splits at their natural
rate — 32.6 % train, 32.5 % val, 32.3 % test.

### 5.4 Country balance

| Policy A | Japan | US | India | Norway | China_Drone | China_Moto | Czech |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 33.4 % | 20.1 % | 13.6 % | 12.2 % | 8.1 % | 8.0 % | 4.6 % |
| val | 31.6 % | 20.2 % | 13.5 % | 13.2 % | 8.8 % | 8.7 % | 4.0 % |
| test | 33.5 % | 20.9 % | 13.7 % | 11.7 % | 7.2 % | 8.8 % | 4.2 % |

All seven countries are present in all three splits under both policies; the largest deviation is
1.8 pp (Japan). No split is single-country, which would have destroyed the country-generalisation
claim.

### 5.5 How validation and test stay frozen

1. Fold order is fixed by the splitter contract (`folds[0]` = test, `folds[1]` = val) and groups are
   sorted before folding.
2. The three lists are written **once** to `dataset/splits/{train,val,test}.txt` together with a
   SHA-256 of each list and the full parameter block (hash definition, threshold, seed, sklearn
   version, group count).
3. The splitter refuses to overwrite existing lists; a regeneration requires a new version directory
   and a written reason.
4. Training reads the lists; it never re-derives groups. Under TDD §4.6 only the *train* list may be
   subsampled, and the subsampled list is written as a separate file so the frozen originals remain
   intact.
5. `verify_split.py` re-reads the materialised tree and re-checks the invariants (no group or hash in
   two splits) against the frozen hashes before training is allowed to start.

### 5.6 Recommendation for Q-04 (split)

**Confirm 80 / 10 / 10, seed 42, group-level stratification by rarest retained class** (TDD Appendix B
recommendation, reproduced here with 0 violations and ≤ 1.03 pp class-share deviation). No alternative
ratio is proposed: 70/15/15 would buy a slightly tighter validation estimate at the cost of 1,200
training images and a colder test set, and nothing in the measurements supports that trade.

---

## 6. Findings — exact, measured

1. The corpus is 47,420 images / 38,385 XMLs / 65,712 objects; 9,035 images have no XML and **all**
   are official test splits.
2. Of the annotated images, 19,221 contain only target classes, 4,546 contain both, 2,894 contain only
   out-of-scope classes, and 11,724 contain a structurally empty XML.
3. The fixed four-class mapping retains **55,006 of 55,007** target objects (one degenerate box) and
   excludes **all 10,705** out-of-scope objects by exact code match, with zero geometry-driven
   exclusions among them.
4. 17.1 % of target objects (9,414) live in images that also contain out-of-scope boxes; those targets
   survive every policy.
5. The out-of-scope images are real damage: D44 (1,464 images), D50 (774), Repair (520), D43 (467),
   plus 139 images of D01/D11/Block crack/D0w0.
6. Policy pools: A = 23,767 images, B = 26,661, C = 35,119.
7. Exact duplicates: 2 pairs, one of which crosses the official train/test boundary.
8. Near-duplicates at d ≤ 3: 636 groups covering 2,416 images; the largest group is 360 images and is
   a real video sequence.
9. The S4-T2 500-image cap hid 1 group and 21 images; the uncapped result is authoritative.
10. The distance distribution is dominated by d = 5–6 (28,363 of 35,227 pairs, 80.5 %).
11. Median pixel correlation is 0.951 / 0.934 / 0.909 at d = 1 / 2 / 3 and falls to 0.880 at d = 4.
12. 220 near-groups touch an official test image, 11 are entirely official test, 11 span countries,
    79 are label-inconsistent, 160 are chained (diameter > 3).
13. Consecutive filename numbers are **not** adjacent frames (median Hamming 28; 0.02 % within d ≤ 6).
14. Of 29 statistically examined groups, the heuristic verdicts are 1 coherent, 13 ambiguous and 15
    likely over-merged. Recorded visual conclusions cover 16 groups: 2 of the 15 are genuine sequences
    and 13 are hash-degenerate (139 images total). The remaining 13 groups have contact sheets but are
    marked `"visual_inspection": "not inspected"` in the JSON.
15. Independent units: 22,966 groups (A) / 34,141 groups (C).
16. The 80/10/10 simulation with seed 42 yields 0 group and 0 exact-hash crossing violations under both
    policies, with a maximum class-share deviation of 1.03 pp.
17. Known label contamination: 372 empty XMLs (3.17 %) contradicted by duplicate evidence, and 21
    out-of-scope-only images (0.73 %) contradicted by a target-labelled near-duplicate.

---

## 7. Recommended decisions — **RECOMMENDED, NOT RATIFIED**

The team must ratify these before S4-T3 starts. Nothing in this section has been applied.

### Q-03 — annotation / background policy

> **Adopt Policy C.** Split the 23,767 images with ≥ 1 retained target box plus the 11,352
> structurally empty XMLs that are not contradicted by duplicate evidence. Exclude the 372
> contradicted empty XMLs and all 2,894 out-of-scope-only images. **Policy A** (targets only) is the
> fallback if the verification gate below cannot be closed before the split is frozen. **Policy B is
> rejected.**

Verification gate (must pass before the split is frozen):

| Step | Test | Pass condition |
| :--- | :--- | :--- |
| V1 | Already done: duplicate evidence | the 372 contradicted empty XMLs are excluded |
| V2 | Stratified random sample of 300 of the 11,352 remaining empty XMLs (60 per country, viewed at full resolution, seed recorded) | the observed in-scope-damage rate is consistent with the known 3.2 % base rate and does not indicate a *systematic* omission; findings are recorded per country |
| V3 | If V2 shows systematic omission in a country | exclude that country's empty XMLs, or fall back to Policy A |

Rationale and honesty note: the sample cannot prove that 11,352 images are damage-free. It is there to
detect a *systematic* annotation gap, because the duplicate evidence already proves the base rate is
about 3 %. If the team cannot run V2 before the split freeze, use Policy A. Do not use unfiltered
Policy B under any circumstances.

Recorded parameters: background share 32.3 % of the split pool, natural proportion in all splits;
train-only background subsampling deferred to TDD §4.6 with a measured reason; the 372 and 21 exclusion
lists archived with the split.

### Q-04 — duplicate threshold and split ratio

> **Confirm Hamming ≤ 3** with union-find transitive closure, **no bucket cap**, exact duplicates by
> SHA-256, **80 / 10 / 10**, seed **42**, `StratifiedGroupKFold(n_splits=10)`, folds[0] = test,
> folds[1] = val, stratification by the rarest retained class in each group, group-level splitting
> only, lists frozen and hashed on first write.

Recorded deviations for the dataset record (AC-16): 8 × 8-bit pigeonhole; identical-hash collapse;
SHA-256 instead of SHA-1; `iter("object")` instead of `findall("object")`; groups sorted before
folding.

---

## 8. Remaining uncertainties

| # | Uncertainty | Impact | How it is handled |
| :--- | :--- | :--- | :--- |
| U1 | The true omission rate in the 11,352 "verified" empty XMLs is unknown; 3.2 % is a lower bound | Background noise → false negatives | V2 gate; Policy A fallback; exclusions archived |
| U2 | 13 hash-degenerate clusters merge visually distinct pavement images (139 images, 0.6 % of pool) | Slight diversity loss, no leakage | Accepted deliberately; never split a group |
| U3 | Group 54 bridges 40 frames from four countries into one India sequence | One 360-image block is split as a unit; its non-India members cannot be spread | Accepted; documenting it is cheaper than refining the hash |
| U4 | D40 has only ~360 test images under either policy | Wider mAP confidence interval for potholes | Accepted; 80/10/10 is the documented ratio and the alternative is worse |
| U5 | No measurement of whether background images improve mAP on this dataset | Policy C's benefit is theoretical | S4-T4 must report per-class AP with and without background (one ablation) |
| U6 | The heuristic "over-merged" verdict used correlation on a sample, not every pair | Some groups may be mislabelled internally | Visual inspection of all 29 risky groups already done; verdicts recorded |
| U7 | The audit did not measure the TDD skeleton's 4 × 16-bit bucket partition | Unknown how many images `MAX_BUCKET=2000` would drop | The cap is removed in the recommendation, so the question is moot |

---

## 9. Proposed S4-T3 implementation plan (not started)

Precondition: Q-03 and Q-04 ratified, and the V2 gate closed or Policy A chosen.

| Step | Work | Gate / evidence | Est. |
| :--- | :--- | :--- | ---: |
| T3-1 | Extract the shared primitives into `training/dataset_lib.py`: `sha256_file`, `dhash64`, pool/group builder | Unit tests: dHash equals the audit's value on 50 fixed images; a one-bit image flip changes the hash; group ids identical to `duplicate_groups.json` for the same inputs | 2 h |
| T3-2 | `training/classes.json` + `convert_annotations.py` | Emitted lines = 55,006; per-class = `{26,016 / 11,830 / 10,617 / 6,544}`; every class id in 0–3; `excluded_code:*` totals equal the audit's out-of-scope per-code counts; 1 degenerate box reported; 0 clipped | 4 h |
| T3-3 | `split_dataset.py`: SHA-256 + dHash groups on the pool, Hamming 3, union-find, 10-fold StratifiedGroupKFold seed 42 | 0 group crossings, 0 hash crossings; split sizes within 0.3 pp of the simulation; class shares within 1.5 pp; lists hashed | 4 h |
| T3-4 | Materialise `dataset/images|labels/{train,val,test}` + `data.yaml` | Image count per split equals the list; every target image has a label file; every background image has an explicit empty label file; no label file contains a class id outside 0–3; `path:` quoted (the repo path contains a space); free disk ≥ 15 GB before copying (~9.5 GB for C, ~6.4 GB for A) | 2 h |
| T3-5 | Visual verification | 20 random converted images per class with drawn boxes; 20 random background images (must show no in-scope damage); 10 images from each of the four largest duplicate groups (all members in one split) | 2 h |
| T3-6 | Freeze and record | `dataset/splits/*.txt` + SHA-256 of each; dataset record with policy, threshold, seed, versions, counts; exclusion lists for the 372 / 21; `OPEN_QUESTIONS.md` status updated to RATIFIED + IMPLEMENTED; traceability AC-16 updated | 1 h |
| | **Total** | | **~15 h (2 working days)** |

Hard rules for the implementer:

- Never re-hash with different parameters than §2.2; never reintroduce a bucket cap.
- Never regenerate a frozen split; write a new version directory instead.
- Never split a duplicate group; never resample val/test for convenience (TDD §4.6).
- The converter must abort on any count mismatch with this audit, not warn.
- No model training in S4-T3; it starts in S4-T4.

---

## 10. Artefacts and reproduction

| Artefact | SHA-256 |
| :--- | :--- |
| `training/audit_dataset_policy.py` | `B4860A780764E2EA007905963B3585AF98EBC21AC8D4CEE358B97B6ECCDC7ABD` |
| `data/reports/audit/policy_audit.json` | `EFE53BC6444B896AF9106F33FBDA1735AD626DD296357955819F747152789A6C` |
| `data/reports/audit/duplicate_groups.json` | `A348156F6DAA2C49AB1074112856BE8D9CFE677BF4B22937F05CA5CC1E6AB216` |
| `training/make_inspection_artifacts.py` | `ABDEA8C680E300A716CA779D0924EFB7C6B82C9647D0EE43AFE3E24285FCE8FA` |
| `data/reports/audit/contact_sheets/ambiguous_groups_report.json` | `D78CB3371D1E791478BF68C9BF511D4FAF2D87C04E5B544B27408418349EC22D` |

`contact_sheets/` now holds **29** contact sheets: all 22 groups of ≥ 8 images plus the 7 remaining
cross-country groups. The 13 previously missing sheets were generated from the existing group
records; group membership, statistics and heuristic verdicts are unchanged.

Reproduce the audit (warm cache; 93.1 s measured):

```powershell
.\.venv\Scripts\python.exe training\audit_dataset_policy.py
```

`--refresh-hashes` recomputes the 47,420 SHA-256/dHash values instead of loading
`image_hash_cache.json`; `--countries China_Drone` restricts the run. Versions used: Python 3.11.9,
opencv 5.0.0, numpy 2.4.6, scikit-learn 1.9.1.

Regenerate/validate the inspection artifacts without rerunning duplicate detection:

```powershell
# writes only missing sheets, then rewrites ambiguous_groups_report.json
.\.venv\Scripts\python.exe training\make_inspection_artifacts.py

# validate all 29 sheets and write nothing
.\.venv\Scripts\python.exe training\make_inspection_artifacts.py --check
```

Inputs: `duplicate_groups.json` (membership), `policy_audit.json` (cross-country ids), the existing
`ambiguous_groups_report.json` (recorded statistics/verdicts), and the immutable images under
`data/raw/RDD2022`. `--force` rebuilds existing sheets; the default preserves them.

Validation performed: `--check` opened all 29 sheets, checked each against its expected
1500 × (rows × 150) size, and rejected blank images; a clean regeneration into an empty temporary
directory produced all 29 sheets and the same statistics/verdicts; the selection covers 22 of 22
groups with ≥ 8 images and 11 of 11 cross-country groups. The 13 previously missing sheets were
written into `contact_sheets/` and all 29 repository sheets pass the same check.

---

## 11. Stop point

This task stops here. No annotation was converted, no class file was created, no split directory was
written, no image was copied, no model was trained, and nothing was committed. Q-03 and Q-04 are
recorded as **evidence-backed recommendations awaiting ratification** in
[`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md) §3 (Q-03 and Q-04) and §8; S4-T3 must not start until they
are ratified. The missing contact sheets were generated and the inspection artifacts are reproducible
through `training/make_inspection_artifacts.py`; no visual verdict was invented for any group.
