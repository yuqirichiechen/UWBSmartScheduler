# SmartScheduler — TODO

Mapping of CSS 382 DYOP proposal → current state.

All items required by the proposal are complete. The RAG slot exists but is
intentionally inert — the deterministic [`ScheduleBuilder`](backend/app/rag/schedule_builder.py)
is the primary recommendation engine so the system works without an OpenAI key.

## Status legend
- [x] Done
- [~] Partial / optional
- [ ] Not yet done

---

## 1. Data pipeline (Richie — scraper / embeddings / vector store)

### Scraper
- [x] Python scraper for UW Bothell Time Schedule — [uw_scheduler_scraper.py](backend/app/scraper/uw_scheduler_scraper.py)
- [x] Live HTML fetch with retry + exponential backoff
- [x] Cache w/ SHA-256 validation
- [x] Fallback chain: cache → live → sample
- [x] Multi-campus, multi-department coverage
- [x] Course schema: `code, title, credit_hours, department, prerequisites, sections[ {section_number, section_id, instructor, meeting_times[…], credits} ]`
- [x] Schema/field-count validation on every load (proposal mitigation) — see `_validate_schema` in the scraper. Drops malformed rows and logs warnings when fields go missing.
- [x] Cache refreshed to 30 real CSS courses (was sample data)

### Embeddings / vector store
- [x] Embedding service (`text-embedding-3-small`) — [embedding_service.py](backend/app/embedding/embedding_service.py)
- [x] Vector store w/ Pinecone backend + in-memory cosine fallback — [vector_store.py](backend/app/embedding/vector_store.py)
- [x] Pinecone client supports both v3+ (`Pinecone(api_key=...)`) and legacy v2 (`pinecone.init(...)`) APIs, query/stats normalize both response shapes
- [x] Upsert at startup, semantic retrieval at query time (`main.py:_retrieve_courses`)

### Prerequisite graph
- [x] `PrerequisiteGraph` w/ transitive closure ([prerequisites.py](backend/app/utils/prerequisites.py))
- [x] Built at startup by sweeping CSS/CSE 100–500 through `scraper._get_prerequisites`
- [x] `infer_completed` expands student input (CSS 343 → also 342, 211, 161…)

---

## 2. Scheduling & RAG (Kevin — pipeline / prompts / conflict checks)

### Constraint parser
- [x] [constraint_parser.py](backend/app/rag/constraint_parser.py) extracts: `max_credits, min_credits, preferred_days, avoid_days, required_courses, time_windows, no_online`
- [x] Day scanner is longest-match-first so `tue` does not shadow `tuesday`
- [x] `avoid_days` is scoped to the clause following a negation trigger; flips back on `but`/`except`
- [x] `preferred_days` skips matches inside a preceding negation window
- [x] `"only Tue/Thu"` promotes the complement (M, W, F) to `avoid_days` so it behaves as a hard constraint

### Schedule builder (NEW, primary path)
- [x] [schedule_builder.py](backend/app/rag/schedule_builder.py) — deterministic, LLM-free
- [x] Honors `required_courses`, `max_credits`, `min_credits`, `avoid_days`, `preferred_days`, `no_online`
- [x] Picks exactly one section per course, checks conflicts against the running set before adding
- [x] Ranks CSS core courses ahead of electives; required courses first

### RAG pipeline (intentionally idle)
- [x] [rag_pipeline.py](backend/app/rag/rag_pipeline.py) is kept in the tree for the proposal's RAG narrative
- [~] Only runs when `OPENAI_API_KEY` is set; can override the human-readable summary on top of the deterministic plan. Builder remains the source of truth for sections.

### Conflict checker
- [x] [conflict_checker.py](backend/app/rag/conflict_checker.py) — pairwise meeting overlap, credit caps, avoided days, prerequisite eligibility

---

## 3. API (FastAPI)

- [x] [main.py](backend/main.py) — startup lifecycle: scraper → prereq graph → embeddings → vector store → (optional) RAG
- [x] Endpoints:
  - `GET  /health`
  - `POST /api/schedule` (deterministic; RAG-optional)
  - `GET  /api/courses`
  - `GET  /api/courses/{course_code}`
  - `POST /api/scrape`
  - `GET  /api/vector-store/stats`
- [x] CORS open for local dev
- [x] Works end-to-end with no API keys

---

## 4. Frontend (Yousuf — UI / UX)

- [x] React SPA — [App.js](frontend/src/App.js)
- [x] Status banner: connecting / connected / offline
- [x] [QueryInput.js](frontend/src/components/QueryInput.js) — textarea + 4 example prompts + tips
- [x] [CompletedCourses.js](frontend/src/components/CompletedCourses.js) — add/remove tags
- [x] [ScheduleOutput.js](frontend/src/components/ScheduleOutput.js) — header w/ credit total + validity badge, issues list, course cards
- [x] [ScheduleCalendar.js](frontend/src/components/ScheduleCalendar.js) — Mon–Fri grid, dynamic visible hours, color-coded blocks, legend
- [x] [api.js](frontend/src/services/api.js) — axios client, env-driven base URL/timeout
- [x] Dark theme styles
- [x] Happy-path test — [App.test.js](frontend/src/App.test.js) (renders header, mocks the API, asserts schedule rendering)
- [x] Production build clean (`react-scripts build` → 66.9 KB JS gz)

---

## 5. Evaluation (proposal success criteria)

| # | Criterion | Status | Latest run |
|---|-----------|--------|-----------|
| 1 | 10 student constraint queries → zero conflicts | [x] | 10/10 |
| 2 | Prerequisite enforcement → no ineligible courses | [x] | 0 violations across 30 courses |
| 3 | Scraper uptime → 3 test runs w/ hash comparison | [x] | 3× identical `c1ad3be7…`, 30 courses each |
| 4 | NL parsing ≥80% constraint extraction accuracy | [x] | 10/10 (100%) |

Harness: [backend/eval/](backend/eval/)
- [eval_queries.json](backend/eval/eval_queries.json)
- [run_eval.py](backend/eval/run_eval.py)
```bash
cd backend && source venv/bin/activate
python -m eval.run_eval
```

---

## 6. Docs

- [x] [ARCHITECTURE.md](ARCHITECTURE.md) — current data flow + request lifecycle
- [x] [PROPOSAL.md](PROPOSAL.md), [README.md](README.md), [SETUP.md](SETUP.md)
- [x] Stale `IMPLEMENTATION_STATUS.md` removed
- [~] `SCRAPER_*.md` and `BACKEND.md` predate the rewrite; keep as historical reference

---

## How to run

```bash
# Backend
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python main.py            # http://localhost:8000

# Eval
python -m eval.run_eval

# Frontend
cd ../frontend
# Deps live at the repo root via npm workspaces
../node_modules/.bin/react-scripts start   # http://localhost:3000
../node_modules/.bin/react-scripts test --watchAll=false
../node_modules/.bin/react-scripts build
```

## Out of scope (per proposal)
- Multi-major planning
- Real-time MyPlan integration
- User account persistence
