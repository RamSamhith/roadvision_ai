# RoadVision AI — Source Document Register

**Purpose:** record the identity, provenance and integrity of the three official project
documents so that every later technical decision can be traced back to a specific,
verifiable source file.

**Location of originals:** `docs/source/` — the files keep their original WhatsApp
filenames. They have **not** been renamed, modified or re-saved. All three are
ReportLab-generated PDFs (PDF 1.4).

**Register prepared:** 2026-11-05
**Verification method:** SHA-256 computed with `Get-FileHash -Algorithm SHA256`; title,
author, subject, creator and creation date read from the PDF metadata dictionary with
PyMuPDF; page count and body text extracted page by page.

---

## 1. Register

| # | Original filename | Actual document title (from PDF) | Document role | Version | Pages | SHA-256 |
| :-: | :--- | :--- | :--- | :--- | :-: | :--- |
| 1 | `DOC-20261102-WA0017.pdf` | *RoadVision – Intelligent Road Monitoring System: Project Proposal* | Project Proposal — objectives, scope, academic context | **Not stated in document** (dated November 2026) | 11 | `6748DE0E50718744D93B58407C3D15B6AEBDE3DDC4A1210FA960633DFF1EAC16` |
| 2 | `DOC-20261102-WA0018.pdf` | *RoadVision - Product Requirements Document v1.1* | Product Requirements Document (PRD) — functional/non-functional requirements, acceptance criteria | **1.1** (supersedes 1.0) | 16 | `C359D4EEFCB71AFC92B5A7BAA2D39F553B0F5DE4A61F5CADC24B7316AFC09328` |
| 3 | `DOC-20261103-WA0001.pdf` | *RoadVision - Technical Design Document v1.1* | Technical Design Document (TDD) — architecture, schemas, API, pipelines | **1.1** (supersedes 1.0; aligned with PRD v1.1) | 22 | `97055376E4B02EA5D1930A389EE492134B35277454BE37D7E31327936D7E92D8` |

**Identity verification result:** the filename→document mapping supplied for this stage is
**confirmed correct** for all three files. No document was mis-identified.

> Note on absolute paths: the files are Git-ignored (see `.gitignore` → `data/…` rules do
> not apply; `docs/source/*.pdf` is tracked). PDFs are treated as immutable reference
> material. The three descriptive Markdown copies under `docs/reference/` are derivatives,
> not replacements.

---

## 2. Metadata verification detail

| Field | WA0017 (Proposal) | WA0018 (PRD) | WA0001 (TDD) |
| :--- | :--- | :--- | :--- |
| PDF format | PDF 1.4 | PDF 1.4 | PDF 1.4 |
| Title (metadata) | RoadVision – Intelligent Road Monitoring System: Project Proposal | RoadVision - Product Requirements Document v1.1 | RoadVision - Technical Design Document v1.1 |
| Author (metadata) | Ram and Shakib | RoadVision Team | RoadVision Team |
| Subject (metadata) | B.Tech CSE (AI & ML) Mini Project Proposal | (unspecified) | (unspecified) |
| Producer | ReportLab PDF Library - (opensource) | ReportLab PDF Library - (opensource) | ReportLab PDF Library - (opensource) |
| Creation date (UTC) | 2026-11-02 12:55:26 | 2026-11-02 13:00:10 | 2026-11-02 18:44:52 |
| File size | 38,556 bytes | 64,034 bytes | 86,602 bytes |
| Embedded images | none (vector tables/diagrams only) | none (vector tables/diagrams only) | none (vector tables/diagrams only) |
| Text layer | present, fully extractable | present, fully extractable | present, fully extractable |
| Encryption | none | none | none |

---

## 3. Extraction status

| # | Original file | Markdown reference copy | Extraction status | Notes |
| :-: | :--- | :--- | :--- | :--- |
| 1 | `DOC-20261102-WA0017.pdf` | `docs/reference/PROJECT_PROPOSAL.md` | **COMPLETED** (text, tables, headings, references) | Figure 1 is a vector diagram; its node labels are transcribed in §8.1 of the reference copy. The generated table of contents and page headers/footers are layout artefacts and are omitted. |
| 2 | `DOC-20261102-WA0018.pdf` | `docs/reference/PRD_v1.1.md` | **COMPLETED** (text, tables, headings, appendices) | Tables renumbered by section (PRD numbering preserved: Tables 5–12). Figure 1 is a vector diagram; the flow is transcribed in §8. |
| 3 | `DOC-20261103-WA0001.pdf` | `docs/reference/TDD_v1.1.md` | **COMPLETED** (text, tables, code listings, appendices) | Figures 1 and 2 are vector diagrams; their captions and text-layer labels are recorded in place. All Python/SQL/YAML/TypeScript listings are reproduced verbatim from the PDF text layer. |

**No content was invented, summarised away or re-worded as a requirement.** Where a visual
element could not be represented in Markdown, its presence and its readable text labels are
documented rather than reconstructed.

---

## 4. Authority order (binding for this project)

1. **TDD v1.1** — primary technical authority: architecture, schemas, API contracts, model
   parameters, processing pipelines.
2. **PRD v1.1** — product requirements: features, behaviour, acceptance criteria, limits.
3. **Project Proposal** — objectives, scope, academic context, schedule.

Where two documents disagree, the disagreement is recorded in
[`docs/project/OPEN_QUESTIONS.md`](../project/OPEN_QUESTIONS.md) and is **not** resolved
silently. Actual conflicts found in this review are listed there.

---

## 5. Related records

| Record | Location |
| :--- | :--- |
| Requirement traceability matrix | `docs/project/REQUIREMENTS_TRACEABILITY.md` |
| Conflicts and unresolved questions | `docs/project/OPEN_QUESTIONS.md` |
| Skill coverage audit | `docs/project/SKILLS_INVENTORY.md` |
| Dependency compatibility matrix | `docs/project/DEPENDENCY_MATRIX.md` |
| Environment setup and verification | `docs/setup/ENVIRONMENT_SETUP.md` |
