# Deploying SmartScheduler to Vercel

The repo is laid out for a single Vercel project that serves the React build as
the static frontend and the FastAPI app as a Python serverless function.

```
smartscheduler/
├── api/index.py            ← Vercel Python entry, re-exports the FastAPI `app`
├── backend/                ← unchanged source tree (FastAPI, scraper, builder)
├── frontend/               ← React SPA (CRA)
├── requirements.txt        ← Python deps used by Vercel's build
├── vercel.json             ← build + routing config
└── .vercelignore           ← excludes venvs, caches, eval, examples
```

## One-time setup

1. **Commit and push all the deploy files first** — `vercel.json`, `api/`, root
   `requirements.txt`, root `package.json` (with `vercel-build` script and
   workspace declaration removed), `.vercelignore`. If you import the repo
   before pushing these, Vercel sees the old layout and the deploy will fail.

2. In Vercel: **New Project → Import Git Repository → pick this repo**.

3. Framework Preset: **Other**.

4. **Leave Build Command, Output Directory, and Install Command fields blank
   in the Vercel UI** — `vercel.json` already sets:
   - `buildCommand: npm run vercel-build`
   - `outputDirectory: frontend/build`
   - `installCommand: echo 'install handled by buildCommand'` (no-op so we
     don't trigger an npm install on the root package.json)
   - `functions: api/index.py` with `maxDuration: 30`, `memory: 1024`,
     `includeFiles: backend/**` (so the FastAPI source + cache JSON ship with
     the function — `sys.path` manipulation in `api/index.py` defeats
     Vercel's static-import detection so we declare the dependency
     explicitly).

5. Click **Deploy**.

## Environment variables (all optional)

Add these under **Project → Settings → Environment Variables** if you want to
turn on the LLM augmentation path:

| Name                     | Purpose                                                |
|--------------------------|--------------------------------------------------------|
| `OPENAI_API_KEY`         | Enables the RAG pipeline summary on top of the builder |
| `OPENAI_MODEL`           | Optional override, defaults to `gpt-4`                 |
| `PINECONE_API_KEY`       | Use Pinecone instead of the in-memory vector store     |
| `PINECONE_ENVIRONMENT`   | Pinecone region (only with Pinecone)                   |
| `PINECONE_INDEX_NAME`    | Index name; defaults to `uwbothell-courses`            |

Without any of the above, the deployment still works end-to-end: the
deterministic `ScheduleBuilder` is the sole recommendation engine.

`SMARTSCHED_SERVERLESS=1` is set automatically by `api/index.py` so the
backend skips work that's slow on cold starts (live scraping, embedding
generation).

## Request flow on Vercel

```
Browser  ──►  https://<project>.vercel.app/api/schedule
                       │
                       ▼
        ┌──────────────────────────────────────────┐
        │  vercel.json rewrite: /api/* → /api      │
        │  → invokes api/index.py                  │
        │    ↳ imports backend/main.py:app         │
        │    ↳ FastAPI routes /api/schedule        │
        │    ↳ returns JSON                        │
        └──────────────────────────────────────────┘

Browser  ──►  https://<project>.vercel.app/   ← served from frontend/build
```

The cached course data ships with the deployment at
`backend/data/cache/courses_bothell_css.json` (30 real CSS courses). The
serverless function reads it on cold start; it never reaches out to UW from
inside a function invocation.

## Local sanity check before deploying

```bash
# Frontend
cd frontend
../node_modules/.bin/react-scripts test --watchAll=false   # 2 passing
../node_modules/.bin/react-scripts build                   # clean build

# Backend
cd ../backend
source venv/bin/activate
python -m eval.run_eval                                    # 4/4 criteria pass

# Simulate the Vercel entry from the repo root
cd ..
SMARTSCHED_SERVERLESS=1 backend/venv/bin/python -c \
  "import sys; sys.path.insert(0,'backend'); from api.index import app; print(len(app.routes), 'routes')"
```

## Updating course data after deploy

Vercel's filesystem is read-only inside a function, so re-scraping has to happen
in the repo and be committed:

```bash
cd backend && source venv/bin/activate
python -c "from app.scraper import UWScheduleScraper as S; \
  s=S(cache_dir='data/cache'); c=s.scrape_courses(); s.cache_courses(c,'bothell_css')"
git add backend/data/cache/courses_bothell_css.{json,hash} && git commit -m "refresh course cache"
git push    # triggers a new Vercel deploy with fresh data
```

## What's excluded from the deploy

`.vercelignore` skips the local virtualenv, `node_modules`, build artifacts,
the eval harness, scraper examples / tests, and stale docs. They are not
needed at runtime and would only inflate the upload.

## Cold-start budget

| Step                                        | Time   |
|---------------------------------------------|--------|
| Load cached courses (30) + schema validate  | <50ms  |
| Build prerequisite graph (CSS/CSE 100–500)  | <50ms  |
| Init vector store (mock)                    | <5ms   |
| Total cold start                            | ~150ms |

Comfortably inside the 10s Hobby / 60s Pro timeout. Warm invocations are
~10ms for `/api/schedule` against the deterministic builder.

## Troubleshooting

- **`404: NOT_FOUND` with `DEPLOYMENT_NOT_FOUND`** — the deployment never
  finished or never started. Causes we've seen:
  1. The Vercel project was imported before the deploy files were pushed.
     Push `vercel.json`, `api/`, root `requirements.txt`, the updated root
     `package.json`, and `.vercelignore`, then redeploy.
  2. Root `package.json` declared `"workspaces": ["backend", "frontend"]`
     but `backend/` has no `package.json`, so `npm install` failed before
     `buildCommand` ever ran. Already fixed in this repo.
  3. Vercel's UI override fields for Build Command / Install Command /
     Output Directory took precedence over `vercel.json` and pointed
     somewhere wrong. Open **Project → Settings → Build & Development
     Settings** and confirm all override toggles are OFF.

  Open the **Deployments** tab in the Vercel dashboard — the failed build's
  log has the real error.

- **`502: NO_RESPONSE_FROM_FUNCTION`** — a Python import failed. Check the
  function logs. Common causes: a missing entry in root `requirements.txt`,
  or `includeFiles` not picking up `backend/` (it should — `vercel.json`
  declares `"includeFiles": "backend/**"`).

- **`404` on `/api/*`** — Vercel's rewrites map `/api/(.*)` → `/api/index`.
  If you renamed `api/index.py`, update `vercel.json`.

- **`courses_loaded: 0` in `/api/health`** — the cache JSON didn't make it
  into the deployment. Confirm `backend/data/cache/courses_bothell_css.json`
  is committed to git and isn't covered by `.vercelignore`.

- **Frontend hits `http://localhost:8000` in production** — make sure you
  didn't set `REACT_APP_API_URL` in Vercel's environment variables; the
  client defaults to a relative base URL in `NODE_ENV=production`.

- **Local `npm run build` fails with `Cannot find module ajv/...` on Node 23+**
  — CRA 5.0.1 has known dependency-resolution issues on Node 23+. This does
  not affect Vercel (which runs Node 22). To build locally, use Node 22 via
  `nvm install 22 && nvm use 22`. The `engines.node` field in `package.json`
  pins Vercel to `20.x || 22.x`.
