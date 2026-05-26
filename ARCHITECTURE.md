# SmartScheduler — Architecture

Current as of the post-rewrite codebase (real UW Bothell scraper + deterministic
`ScheduleBuilder` as the primary recommendation path).

## Components

```
┌──────────────────────────────┐
│  React SPA  (frontend/)       │
│  - QueryInput                 │
│  - CompletedCourses           │
│  - ScheduleCalendar           │
│  - ScheduleOutput             │
└──────────────┬───────────────┘
               │ HTTP (axios)
               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  FastAPI server  (backend/main.py)                                       │
│                                                                          │
│   POST /api/schedule                                                     │
│      ConstraintParser ─► VectorStore* ─► PrerequisiteGraph               │
│                                          │                               │
│                                          ▼                               │
│                                  ScheduleBuilder  (deterministic)        │
│                                          │                               │
│                                          ▼                               │
│                                  ConflictChecker  (validation)           │
│                                          │                               │
│                                          ▼                               │
│                              { is_valid, issues, recommended_courses }   │
│                                                                          │
│   *VectorStore / RAGPipeline are present but optional — they only run    │
│    when OPENAI_API_KEY (and optionally PINECONE_API_KEY) are configured. │
│    Without keys the system uses the in-memory mock vector store plus     │
│    constraint-only filtering, then the deterministic builder.            │
└──────────────────────────────────────────────────────────────────────────┘
               │
               │ live HTTP (BeautifulSoup)
               ▼
┌──────────────────────────────┐
│  UWScheduleScraper            │
│  http://www.washington.edu/   │
│  students/timeschd/pub/B/...  │
│                               │
│  cache → live → sample        │
│  SHA-256 cache hash           │
│  schema validation            │
└──────────────────────────────┘
```

## Request flow (POST /api/schedule)

1. **Parse**. `ConstraintParser.parse_query()` extracts a structured constraint dict from plain English. Day-name scanning is longest-match-first to avoid `tue` shadowing `tuesday`; preferred / avoid scopes are bounded to the clause after a trigger word and flip on `but` / `except`.
2. **Retrieve**. `_retrieve_courses()` does a semantic search via the vector store when one is available, otherwise constraint-based filtering. Required courses (mentioned by code in the query) are always merged in.
3. **Infer prerequisites**. `PrerequisiteGraph.infer_completed()` does a transitive closure so that completing `CSS 343` also implies `CSS 342, 211, 161, 143` (etc.).
4. **Build schedule**. `ScheduleBuilder.build()` picks one section per course such that:
   - all hard constraints hold (avoid_days, no_online, max_credits),
   - prerequisites are satisfied,
   - the new section has no time-overlap with already-selected sections.
5. **Validate**. `ConflictChecker.validate_schedule_constraints()` runs a final pass and surfaces any residual `issues` to the UI.
6. **Optional RAG augmentation**. If a RAG pipeline is configured (OpenAI key present), its recommendation *message* overrides the builder's summary, but the builder remains the source of truth for which sections are selected.

## Data shapes

### Course (in cache and `/api/courses`)
```json
{
  "code": "CSS 342",
  "title": "Data Structures, Algorithms, and Discrete Mathematics II",
  "credit_hours": 5,
  "department": "CSS",
  "prerequisites": ["CSS 211", "CSS 201"],
  "sections": [
    {
      "section_number": "A",
      "section_id": "12345",
      "instructor": "Dr. Smith",
      "meeting_times": [
        { "days": ["T","Th"], "start_time": "14:00", "end_time": "15:50", "location": "UWB 105" }
      ],
      "credits": 5
    }
  ]
}
```

### `/api/schedule` response
```json
{
  "query": "…",
  "recommendations": "human-readable summary",
  "constraints": { "max_credits": 14, "avoid_days": ["F"], "...": "…" },
  "recommended_courses": [ /* same Course shape, sections trimmed to picked one */ ],
  "is_valid": true,
  "issues": []
}
```

## Why a deterministic builder?

The proposal mandates section-level conflict-free output and prerequisite
enforcement. Those are graph and combinatorial problems, not language problems
— so they belong in deterministic code, not behind a non-deterministic LLM
call. The builder also means the demo works without an OpenAI key, which is
important for grading and replication.

The RAG path is kept in `backend/app/rag/rag_pipeline.py` because the proposal
calls for it explicitly, and because once a key is present it can add a richer
natural-language explanation on top of the deterministic plan.

## Evaluation

`backend/eval/run_eval.py` runs all four proposal success criteria:

| # | Criterion                                | Last reported |
|---|------------------------------------------|---------------|
| 1 | 10 queries → zero conflicts              | 10/10         |
| 2 | Prerequisite enforcement                 | 0 violations  |
| 3 | Scraper determinism (3 runs)             | identical hash |
| 4 | NL parsing accuracy ≥ 80%                | 10/10         |

Run with:
```bash
cd backend && source venv/bin/activate
python -m eval.run_eval
```

## Out of scope (per proposal)
- Multi-major planning
- Real-time MyPlan integration
- User accounts / persistence
