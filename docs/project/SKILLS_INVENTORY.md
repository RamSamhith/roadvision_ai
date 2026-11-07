# RoadVision AI — Agent Skills & Tooling Inventory

**Audited:** 2026-11-05 (Stage 2)
**Scope:** every agent skill, plugin, MCP server and marketplace entry reachable from this
machine, assessed against the actual RoadVision stack (TDD v1.1 §14 p18; PRD v1.1 §6 p10).

This document answers one question: **for each thing this project must build, is there
verified guidance on disk, or does the implementer have to rely on general knowledge?**

---

## 1. What the project actually needs

Derived from TDD v1.1 Table 11 (p18) and PRD v1.1 §6 (p10), not from preference:

| Capability | Required by | Concrete work |
| :--- | :--- | :--- |
| Python env + pinned deps | TDD §14 p18 | `.venv`, `pip freeze`, cu128 wheel selection |
| Dataset engineering | TDD §4 p7–9; PRD §5 p9 | RDD2022 conversion, dHash dedup, disjoint splits |
| YOLO26 training | TDD §5 p9–10 | Ultralytics training, staged smoke tests, gate script |
| Inference + fallback | TDD §3, §6 p5–6, p11 | model manager, class check, F1–F5 |
| OpenCV video pipeline | TDD §8 p11–12 | decode, annotate, H.264 re-encode via FFmpeg |
| Webcam capture (Windows) | TDD §9 p13 | DirectShow, MJPEG, watchdog |
| FastAPI backend + SQLite | TDD §10–11 p14–16 | routes, job slot, stdlib `sqlite3` |
| React/TS/Vite/Tailwind UI | TDD §12 p17 | 4 pages, video overlay, progress polling |
| Verification | TDD §16 p20 | pytest, GPU gate, failure injection, manual checklist |

---

## 2. Installed and directly applicable

### 2.1 Antigravity skills — `C:\Users\ramsa\.gemini\config\skills\`

| Skill | Applies to | Why it matters here | Verdict |
| :--- | :--- | :--- | :--- |
| `managing-python-dependencies` | Env setup | Enforces `.venv` isolation, detects the dependency manager, prevents global installs | **USE** — cited by `AGENTS.md` §3 |
| `ml-best-practices` | Dataset + training | Split-before-transform, leakage prevention, class imbalance, mAP/precision/recall reporting | **USE** — cited by `AGENTS.md` §4 |
| `notebook-guidance` | Exploration only | Notebook hygiene if any EDA is done | OPTIONAL — the project is script-based |
| `data-autocleaning` | Dataset prep | General cleaning heuristics | REVIEW — only if RDD2022 needs it; `ml-best-practices` governs splits |
| `schema-mapping` | Data interop | Mapping external schemas | LOW — annotation conversion is a fixed 4-class mapping |
| `accidental-data-loss-prevention` | All shell work | Guards against destructive commands | **USE** — cheap safety net |
| `skill-repair` | Tooling | Repairs broken skills | ON DEMAND |

The remaining `skills\` entries (`bigquery-*`, `dbt-bigquery`, `gcp-*`, `dataform-bigquery`,
`cloud-databases-onboarding`, `discovering-gcp-data-assets`, `building-data-apps`,
`enforcing-resource-attribution`) are **Google Cloud data-platform skills**. They are not
applicable: PRD §6 p10 and TDD §15 p19 forbid cloud processing, and no GCP service is used.

### 2.2 Antigravity plugins — `C:\Users\ramsa\.gemini\config\plugins\`

| Plugin | Skills inside | Applies to | Verdict |
| :--- | :--- | :--- | :--- |
| `modern-web-guidance-plugin` | `modern-web-guidance`, `chrome-extensions` | React/Vite/Tailwind patterns, a11y, performance | **USE** — cited by `AGENTS.md` §5. The `search` CLI is the documented way to query it |
| `chrome-devtools-plugin` | `chrome-devtools`, `a11y-debugging`, `cookie-debugging`, `debug-optimize-lcp`, `memory-leak-debugging`, `troubleshooting` | Verifying the dashboard, finding console errors, checking LCP on the video page | **USE** — the only on-disk browser-verification guidance |
| `science` | ~50 domain skills + `uv` | Only `uv` is generic enough to matter | `uv` NOT USED — the project is committed to `pip` + `.venv` (see `AGENTS.md` §3) |
| `gemini-api` | Gemini API usage | Explicitly out of scope (no external API calls during inference, PRD §6 p10) | DO NOT USE |
| `google_maps_platform`, `firebase`, `flutter`, `android-cli-plugin`, `data-agent-kit-plugin`, `google-antigravity-sdk`, `googlecloudtools.datacloud_telemetry` | — | Not part of the stack | DO NOT USE |

### 2.3 Agent skills — `C:\Users\ramsa\.agents\skills\`

| Skill | Applies to | Verdict |
| :--- | :--- | :--- |
| `clean-code` | Backend/frontend structure | **USE** — keep modules small, matching TDD §13 p18 |
| `lint-and-validate` | After every change | **USE** — pairs with the no-unverified-claims rule in `AGENTS.md` §6 |
| `systematic-debugging` | Any bug | **USE** — required before proposing fixes |
| `web-design-guidelines` | UI review | **USE** — accessibility/UX audit of the dashboard |
| `frontend-design` | UI construction | **USE** — visual quality of the four pages |
| `vercel-react-best-practices` | React performance | **USE** — polling, memoisation, avoiding re-render storms on video |
| `vercel-composition-patterns` | Component APIs | USE when the component tree grows past simple pages |
| `vercel-react-view-transitions` | Page transitions | OPTIONAL — polish only, not required by any AC |
| `tailwind-4-docs` | Tailwind v4 utilities/config | **PARTIALLY USABLE** — see §2.4 |
| `docx` | Word deliverables | ON DEMAND — only if the academic report must be `.docx` |
| `workspace-memory` | Recalling prior decisions | ON DEMAND — this repo keeps decisions in `docs/`, not in `.memory` |
| `find-skills`, `skill-creator`, `system-connector` | Tooling | ON DEMAND |
| `developing-with-streamlit`, `astro`, `deploy-to-vercel`, `vercel-cli-with-tokens`, `vercel-optimize`, `vercel-react-native-skills`, `desktop-commander-guide` | — | **NOT APPLICABLE** — wrong stack or wrong platform (no Streamlit, no Astro, no deployment target, no React Native) |
| `backend-dev-guidelines` | — | **DO NOT LOAD** — see §2.5 |
| `docs` | — | Unclassified wrapper; no ML/CV content |

### 2.4 `tailwind-4-docs` — partially usable

The skill expects a generated documentation snapshot under `references/docs/` plus a
`docs-index.tsx`. **That snapshot is not present.** What exists is:

| File | Size | State |
| :--- | :--- | :--- |
| `references/docs-source.txt` | 270 B | Placeholder, not a snapshot |
| `references/engineering-playbook.md` | 9.6 KB | Usable prose on v4 workflow |
| `references/gotchas.md` | 1.7 KB | Usable: v3→v4 migration pitfalls |

**Consequence:** the playbook and gotchas are trustworthy; any claim that requires the official
v4 reference must instead come from the installed package or from Context7. The project uses
Tailwind **4.3.4** with `@tailwindcss/vite` (see `DEPENDENCY_MATRIX.md`), which is a v4-only
setup, so v3 answers from model memory are actively wrong here.

### 2.5 `backend-dev-guidelines` — explicitly rejected

| Property | Value |
| :--- | :--- |
| Declared scope | Node.js, Express, TypeScript, microservices, Prisma |
| Metadata | `source: community`, `risk: critical` |
| Relevance to RoadVision | **None** — the backend is Python/FastAPI with stdlib `sqlite3` (TDD §11 p16) |

Loading it would inject Express/Prisma architecture rules into a FastAPI codebase. It is
recorded here so that a future agent does not mistake it for a backend skill that applies.

---

## 3. Marketplace scan — the real finding

The two configured marketplaces were enumerated from their cached catalogs:

| Marketplace | Plugins | ML / CV / FastAPI / OpenCV / CUDA / FFmpeg skill found |
| :--- | :-: | :--- |
| `antigravity-plugins-official` | 18 | **None** |
| `antigravity-plugins-partners` | 51 | **None** |

Official catalog: `android-cli-plugin`, `chrome-devtools-plugin`, `data-agent-kit-plugin`,
`firebase`, `flutter`, `gcalendar`, `gdocs`, `gdrive`, `gemini-api`, `google_maps_platform`,
`google-antigravity-sdk`, `google-cloud-developer`, `google-developer-knowledge`, `gsheets`,
`gslides`, `looker`, `modern-web-guidance-plugin`, `science`.

Partner catalog: `atlassian-twg-cli`, `auth0`, `base44`, `browse`, `canva`, `coderabbit`,
`context7`, `crowdstrike`, `databricks`, `datadog`, `dropbox`, `dynatrace`,
`endor-labs-agent-kit`, `figma`, `harness-antigravity`, `intercom`, `keenable`,
`keenable-select`, `leapwork-play`, `linear`, `mobbin`, `monday`, `mongodb-atlas`, `netlify`,
`notion`, `pandadoc`, `parallel`, `ping-identity-pingone`, `postman`, `qodo`, `railway`,
`semrush`, `sentinelone-purple-mcp`, `sentry`, `soc`, `stripe`, `supabase`, `superpowers`,
`trello`, `unity`, `vercel-plugin`, `virustotal`, `wispr-flow`, `wix`, `wordpress`, `zapier`,
`zoho-bigin`, `zohobooks-antigravity`, `zoho-crm-plugin`, `zoho-desk-antigravity`,
`zoho-projects`.

**Conclusion:** there is no installable skill for PyTorch, Ultralytics/YOLO, OpenCV video,
FastAPI, SQLite or FFmpeg on either marketplace. No third-party skill was installed. The
previous draft of this file claimed a keyword scan had been performed across
`python/pytorch/fastapi/react/cuda/yolo/sqlite`; the catalog above is the actual evidence and it
contains no such entries.

---

## 4. Documented gaps and how they will be covered

| Gap | Risk it creates | Mitigation |
| :--- | :--- | :--- |
| No Ultralytics YOLO26 guidance | Wrong `predict()` kwargs, wrong export/validation flags, silent CPU fallback | Context7 (`/ultralytics/ultralytics`) + the installed package source + the gate script in TDD §14 p18 |
| No PyTorch/CUDA troubleshooting skill | OOM and driver errors diagnosed by guesswork | `training/verify_gpu.py` first; Context7 for PyTorch; `systematic-debugging` for method |
| No OpenCV video/camera skill | Codec and DirectShow surprises | Empirically verified round-trips (see `ENVIRONMENT_SETUP.md`); test with a real clip and the laptop camera before wiring the UI |
| No FastAPI skill | Route/async misuse, blocking calls in `async def` | TDD §10 p14–15 already mandates `def` handlers for blocking work; Context7 for FastAPI |
| No SQLite skill | Schema drift vs TDD §11 | Schema is written out in TDD §11 p16 and must be copied verbatim |
| No FFmpeg skill | Broken H.264 output | `imageio-ffmpeg` binary verified present; `libx264` verified present in system FFmpeg 9.0 |

**Policy:** when a gap has to be filled, the answer must come from (a) the ratified documents,
(b) the installed package, or (c) Context7 — not from unverified memory, and not from a
community skill with an unrelated stack.

---

## 5. MCP servers available to this session

| Server | Useful for | Limitation |
| :--- | :--- | :--- |
| `context7` | Live docs for PyTorch, Ultralytics, FastAPI, React, Vite, Tailwind | Must resolve a library ID first |
| `playwright` | Driving the dashboard end-to-end | Requires the dev servers to be running |
| `chrome-devtools` | Console/network inspection, a11y, LCP, memory leaks | Same; best for diagnosing, not for CI |
| `fetch` | Pulling a specific doc page or the RDD2022 landing page | Text only |
| `sequential-thinking` | Structuring a hard debugging session | Not project knowledge |
| `agentmemory` | Cross-session recall + audit of memory operations | Only useful if the team records decisions there |
| `github` | Issues/PRs if the repo is pushed | Docker + token configured |
| `filesystem` | — | **Scoped to `C:\projects\INTELLIGENT QUEUE AND CROWD MANAGMENT`; it cannot read this repository.** Do not rely on it. |

---

## 6. Invocation map by phase

| Phase | Skills / servers | Gate before moving on |
| :--- | :--- | :--- |
| Env + deps (done) | `managing-python-dependencies`, `accidental-data-loss-prevention` | `verify_gpu.py` prints `GATE PASSED`; `pip freeze` recorded |
| Dataset | `ml-best-practices`, `data-autocleaning` (only if needed), `accidental-data-loss-prevention` | Split-disjointness script passes; per-class counts recorded |
| Training | `ml-best-practices`, `systematic-debugging`, Context7 | Staged smoke test per TDD §5.2 p10; mAP/precision/recall on the frozen test set |
| Backend | `clean-code`, `lint-and-validate`, `systematic-debugging`, Context7 | pytest suite + failure-injection list from TDD §16.1 p20 |
| Frontend | `frontend-design`, `web-design-guidelines`, `vercel-react-best-practices`, `modern-web-guidance`, `tailwind-4-docs` (playbook only) | `npm run build` clean; keyboard nav + contrast checked |
| Verification | `verification-before-completion`, `chrome-devtools` / `playwright`, `requesting-code-review` | AC-01…AC-19 checklist with recorded evidence |
| Report | `writing-guidelines`, `docx` (if required), `verification-before-completion` | No unmeasured number in the report |

---

## 7. Summary verdict

- **Covered well:** Python dependency hygiene, ML methodology, web/React/Tailwind guidance,
  browser verification, code quality and verification discipline.
- **Covered partially:** Tailwind v4 reference material (playbook and gotchas only).
- **Not covered at all:** PyTorch/CUDA operations, Ultralytics YOLO26 specifics, OpenCV video and
  DirectShow camera work, FastAPI patterns, SQLite schema practice, FFmpeg H.264 encoding.
- **Rejected:** `backend-dev-guidelines` (Express/Prisma), all GCP data skills, and all
  cloud/API plugins that contradict the local-only NFR.

The uncovered areas are the highest-risk parts of the build. They will be handled with the
ratified documents + Context7 + empirical tests, and each unproven behaviour is already tracked
as an assumption in [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md) §6.
