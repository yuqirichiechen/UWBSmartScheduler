# PISAN-Suggest.md

*Produced by Claude.AI on 2026-05-29*

> Automated instructor-facing feedback. Intended as a starting point for
> discussion, not a final grade. All citations are repo-relative.

## Project Overview

UWBSmartScheduler is a natural-language course scheduling assistant for
UW Bothell (UWB, part of the UW system) CSS undergraduates. A student
types something like "CSS core requirements, only Tue/Thu, max 14 credits,
include CSS 342" and the system returns a conflict-free, prerequisite-aware
weekly schedule with specific section picks. Stack: FastAPI + BeautifulSoup
scraper of `washington.edu/students/timeschd`, optional OpenAI
embeddings/Pinecone vector store, deterministic `ScheduleBuilder` as the
primary recommender, and a React 18 SPA, all deployed as a single Vercel
project (`api/index.py` serverless function + `frontend/build` static).

## Evaluation Against Assignment Specification

Evaluation based only on what is visible in the GitHub repository.

### UW Community Impact (10 pts)

The target audience is squarely UW Bothell CSS students, and the pain
point is real: hand-cross-referencing MyPlan, the Time Schedule, and
degree requirements every quarter, especially for students with
work/transport constraints (`PROPOSAL.md:7-9`). Scope is appropriately
narrowed to the CSS major core
(`backend/app/rag/schedule_builder.py:26-29` defines `CSS_CORE`;
`backend/app/scraper/uw_scheduler_scraper.py:33-36` mirrors it). The
scraper reads the live UW Time Schedule and falls back to a committed
cache of 30 real CSS courses
(`backend/data/cache/courses_bothell_css.json` — verified, 30 entries
CSS 112 → CSS 490). Prerequisite inference (`backend/app/utils/prerequisites.py`,
called from `backend/main.py:74-83`) is a real value-add over MyPlan.
Ceiling on this score: only CSS Bothell is wired end-to-end, so
non-CSS UWB students and Seattle/Tacoma students currently get nothing,
despite `DELIVERABLES.md` claiming "Multi-campus support". Score
estimate: **8/10**.

### AI Integration (15 pts)

AI is architecturally embedded (not a chat sidecar), but the deployed
behavior is more modest than the proposal implies. The honest read is in
`ARCHITECTURE.md:100-110` and `TODO.md:56-58`: the deterministic
`ScheduleBuilder` is the primary path and the source of truth for which
sections are picked; the LLM, when enabled, only overwrites the
human-readable summary string (`backend/main.py:228-238`). The RAG
pipeline (`backend/app/rag/rag_pipeline.py`, JSON-mode `gpt-4`,
temperature 0.3, system prompt at lines 88-101) is real and well-written,
the embedding service uses `text-embedding-3-small`
(`backend/main.py:99-103`), and a Pinecone v3+/v2 dual-API vector store
exists (`backend/app/embedding/vector_store.py:40-76`). However: on
serverless (which is how the project is deployed) embedding upsert is
skipped entirely on cold start (`backend/main.py:105`), so semantic
search has no vectors to hit and `_retrieve_courses` falls through to
regex constraint filtering (`backend/main.py:394-432`). The constraint
parser itself (`backend/app/rag/constraint_parser.py`) is impressive
rule-based NLP, not ML. Net: meaningfully embedded, architecturally
correct, but in the deployed configuration the AI path is essentially
optional polish on top of deterministic code. Score estimate: **10/15**.

### Technical Execution (25 pts)

Strengths: clean separation `models / scraper / embedding / rag / utils`
under `backend/app/`; typed FastAPI request/response models
(`backend/main.py:144-157`); deterministic fallback so the demo works
without any API key; dual `/api/health` + `/health` mounts to survive
Vercel's `/api/*` rewrite (`backend/main.py:160-171`); thoughtful
serverless guard via `SMARTSCHED_SERVERLESS` (`api/index.py:15`,
honored in `backend/app/scraper/uw_scheduler_scraper.py:71-79`);
`ConflictChecker` does pairwise meeting overlap correctly
(`backend/app/rag/conflict_checker.py:27-37`); `ScheduleBuilder._pick_section`
scores candidates rather than picking the first hit
(`backend/app/rag/schedule_builder.py:166-182`); evaluation harness
exists with 10 reference queries (`backend/eval/eval_queries.json`,
`backend/eval/run_eval.py`).

Concerns: (1) **No CI/CD** — there is no `.github/workflows/` directory
at all; nothing is preventing a broken `main`. (2) **Documentation
sprawl** — fifteen-plus markdown files at root and `backend/`
(`README.md`, `ARCHITECTURE.md`, `docs/ARCHITECTURE.md`, `DEPLOY.md`,
`DELIVERABLES.md`, `SETUP.md`, `TODO.md`, `SCRAPER_START_HERE.md`,
`SCRAPER_IMPLEMENTATION_SUMMARY.md`, `FILES_OVERVIEW.txt`,
`backend/BACKEND.md`, `backend/SCRAPER_INTEGRATION.md`,
`backend/app/scraper/README.md`, `backend/app/scraper/SCRAPER_GUIDE.md`),
much of it overlapping and visibly LLM-generated
(`DELIVERABLES.md:201` boasts "4000+ lines of production-ready code");
`README.md:260` still has a stray `# SmartScheduler` line at EOF.
(3) **Test coverage is thin** — `frontend/src/App.test.js` exists but
appears to be the only frontend test, and there is no `pytest`
configuration or visible suite under `backend/`
beyond `backend/test_system.py` and `backend/app/scraper/test_scraper.py`.
(4) **Frontend only has one section per course on the calendar** —
`backend/main.py:548-558` keeps only `course.sections[0]` for validation
even though the builder picked a specific section; that is correct
because the builder trims to one section, but the path is fragile if
the contract ever changes. (5) `CORSMiddleware` allows `*` with
`allow_credentials=True` (`backend/main.py:27-33`) — browsers will
refuse credentialed requests in that combination. Score estimate:
**18/25**.

### Project Web Presence (15 pts)

The React SPA itself is the project landing experience: hero copy,
example query chips (`frontend/src/components/QueryInput.js:21-26`),
schedule cards, weekly calendar (`frontend/src/components/ScheduleCalendar.js`),
catalog view, and a 4-quarter year-planner with localStorage persistence
(`frontend/src/components/YearPlanner.js:1-50`). Dark theme is
consistent. Missing for "Project Web Presence" specifically: there is
**no live URL** anywhere in `README.md`, `PROPOSAL.md`, or the GitHub
About box — `DEPLOY.md` is generic deploy *instructions* with a
`<project>.vercel.app` placeholder, never a real URL. There is no
project landing page distinct from the app itself (no "why this exists"
for a non-technical visitor, no screenshots in README, no demo gif, no
contact). A community-impact statement is also absent — `PROPOSAL.md`
hints at it but the public-facing repo never frames the problem for an
outsider. Score estimate: **7/15**.

### Milestones & Planning (20 pts)

`git log --oneline --all` shows **13 commits total** on a single `main`
branch, no PRs, no tags, no branches. Timeline: scaffold/scraper burst
on 2026-05-19 (Kevin Vo, 5 commits), one massive rewrite commit on
2026-05-24 (Yousuf Al-Bassyiouni, 1 commit, the commit message lists 11
distinct improvements — visibly a squash of many sessions), then a
frontend/deploy polish burst by Richie Chen on 2026-05-26 (5 commits).
That is essentially three sittings spread over a single week, which is
much less iterative than a 10-week milestone roadmap. Commit hygiene is
weak: "course schduler added" (typo), "deployemnt fix", "first commit",
"Front end ui changes" — these are not milestone labels. Module
ownership in `README.md:149-162` does not match the visible commit
record: Richie is listed as Backend / Data Pipeline lead but his commits
are frontend; the scraper rewrite is in Yousuf's commit. No issues or
project board are visible. Score estimate: **10/20**.

### Peer Review (15 pts) — Not evaluable from repository alone

Nothing in the repo evidences peer review of another team's project.
Defer to instructor records.

**Subtotal excluding Peer Review: ~53 / 85**

## Suggested Improvements & New Features

### UI / UX

1. **Surface the AI path to the user.** Right now there is no UI
   indication of whether the schedule came from the deterministic
   builder or the LLM-augmented summary. A small badge on
   `ScheduleOutput` ("deterministic build" vs "AI-explained") would make
   the AI integration legible to graders and users.
2. **Add a one-click "Why this section?" affordance** on each card in
   `frontend/src/components/ScheduleOutput.js` that explains why this
   section beat the others (avoid-day match, earlier start, no conflict
   with already-picked). The `_pick_section` scoring
   (`backend/app/rag/schedule_builder.py:166-182`) already has the
   ingredients; just expose them.
3. **Show enrollment status on cards.** The cache JSON has
   `enrolled`/`capacity` fields (verified in
   `backend/data/cache/courses_bothell_css.json`), but the frontend
   never displays "36/48 seats" or a "Closed" warning — a high-value
   UX win for two lines of code.
4. **Empty-state for the calendar view.** Visiting `view === 'calendar'`
   (the `YearPlanner`) with no plan yet shows a sparse grid; add a
   first-run prompt like "Drop a course onto Autumn 2026 to begin."
5. **Accessibility pass.** Header nav buttons in `frontend/src/App.js:60-83`
   use `aria-label="Primary"` but lack `aria-current` to indicate the
   active view, and the dark-on-dark "Connecting/Connected/Offline" pill
   may fail contrast.

### New Features

1. **Multi-major and Seattle/Tacoma support.** The proposal is
   UW Bothell CSS only, but the scraper already claims multi-campus
   (`DELIVERABLES.md:13-23`). Adding CSSE / CES / BIS endpoints —
   even read-only — turns this from a CSS demo into something the
   whole UW Bothell community could use, which directly lifts the
   Community Impact score.
2. **Multi-quarter graduation planner.** `YearPlanner.js` already
   models four quarters with localStorage; extend it so the builder
   can pick across quarters under a "graduate by Spring 2027"
   constraint, using `PrerequisiteGraph` to enforce ordering.
3. **Section "load balance" hints.** Surface professor RateMyProfessor
   or historical median grade if a public dataset is available; even
   "this section has the most open seats" is useful.
4. **Calendar export.** `.ics` download of the picked schedule so
   students can drop it straight into Google/Outlook calendar.
5. **Save and share.** A read-only shareable URL of a built schedule
   (encode the picked section IDs into a query param) — zero-auth, but
   lets students show advisors and peers.

### Code Quality / Technical

1. **Add a CI workflow.** A single `.github/workflows/ci.yml` that runs
   `pytest backend/` and `npm test --prefix frontend -- --watchAll=false`
   on every push would catch regressions and demonstrate engineering
   discipline. Bonus: run `python -m eval.run_eval` so the proposal's
   success criteria are continuously verified.
2. **Tighten CORS.** `backend/main.py:27-33` uses `allow_origins=["*"]`
   together with `allow_credentials=True`; browsers reject that pair.
   Pin to the Vercel deployment origin in production via an env var.
3. **Collapse the documentation pile.** Keep `README.md`, `PROPOSAL.md`,
   `ARCHITECTURE.md`, `DEPLOY.md`, and `TODO.md`; archive the rest
   under `docs/archive/`. Several of the existing docs visibly
   contradict the rewrite (`backend/app/scraper/SCRAPER_GUIDE.md`
   describes a multi-department parallel scraper that the current
   `scrape_courses()` does not exercise).
4. **Actually exercise the RAG path in production.** Either
   pre-compute and ship the embeddings (the 30-course cache is small,
   <50 KB of vectors), or accept the cold-start cost. As-is, the
   embedding upsert is gated off on serverless
   (`backend/main.py:105`), so semantic retrieval is dead code in
   prod and the AI Integration score is artificially low.
5. **Schema-version the cache file.** `courses_bothell_css.json` has
   no `schema_version`, so a future scraper change that adds/removes
   a field will silently corrupt downstream. Add `{"schema": 1,
   "courses": [...]}` and validate in `_validate_schema`.
6. **Add the live deployed URL to `README.md` and the GitHub About
   box.** The single highest-leverage change in this list: graders
   cannot evaluate a deployed project they cannot find.

---

*End of automated feedback. — Pisan (via Claude.AI, model: claude-opus-4-7)*
