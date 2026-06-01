# Deploy to Railway

Runs the whole stack on Railway — **no code changes vs. local**. Scheduler,
worker, SSE streaming and in-memory caches all work because Railway services are
long-lived containers (not serverless).

## Architecture on Railway

```
                ┌─────────────────────────────────────────┐
  Browser ───►  │ frontend (Next.js)   Root: frontend/     │
                │   NEXT_PUBLIC_API_BASE_URL = public API   │
                └───────────────┬──────────────────────────┘
                                │ HTTPS (CORS)
                ┌───────────────▼──────────────────────────┐
                │ backend  (FastAPI)   Root: backend/       │
                │   railway.web.toml · healthcheck /api/health
                └───────────────┬──────────────────────────┘
                ┌───────────────▼──────────────────────────┐
                │ worker   (same image, no HTTP)            │
                │   railway.worker.toml · python -m app.jobs.worker
                └───────────────────────────────────────────┘

  Supabase (external, already cloud) ◄── backend + worker
```

3 Railway services from **one GitHub repo**. Supabase stays where it is.

> **Cloud-only:** the local `llm-server` (Ollama / typhoon fallback) is **not**
> deployed — embeddings use Gemini and chat uses the cloud provider chain
> (groq → sambanova → nvidia → cerebras → gemini), all stored in the DB. Set
> `ANSWER_LLM_USE_LOCAL=false` so nothing tries to reach `llm-server`.

## Files added for Railway

| File | Purpose |
|---|---|
| `backend/Dockerfile` | API image, binds `$PORT` (Railway) / 8080 (local) |
| `frontend/Dockerfile` | Next standalone, binds `$PORT`, bakes `NEXT_PUBLIC_*` at build |
| `backend/app/jobs/worker.py` | Clean worker entrypoint (`python -m app.jobs.worker`) |
| `backend/railway.web.toml` | API service config (healthcheck `/api/health`) |
| `backend/railway.worker.toml` | Worker service config (start cmd, no healthcheck) |
| `frontend/railway.toml` | Frontend service config |

## Step-by-step

### 1. Create the project
1. railway.app → **New Project → Deploy from GitHub repo** → pick this repo.
2. This creates the first service. You'll configure 3 services total.

### 2. Backend (API) service
- Settings → **Root Directory**: `backend`
- Settings → **Config-as-code path**: `backend/railway.web.toml`
- Variables: add the backend env vars (see table below)
- Deploy → wait for healthcheck `/api/health` to pass
- Settings → **Networking → Generate Domain** → note the public URL
  (e.g. `https://api-xxxx.up.railway.app`)

### 3. Worker service
- **New → GitHub Repo** (same repo) → or **New → Empty Service** then connect repo
- Settings → **Root Directory**: `backend`
- Settings → **Config-as-code path**: `backend/railway.worker.toml`
- Variables: **same** as backend (copy them, or use a shared variable group)
- No domain needed (it has no HTTP server)

### 4. Frontend service
- **New → GitHub Repo** (same repo)
- Settings → **Root Directory**: `frontend`
- Variables:
  - `NEXT_PUBLIC_API_BASE_URL` = the backend public URL from step 2
  - `NEXT_PUBLIC_COMPANY_CODE` = `DEVES`
  - ⚠️ Set these **before the first build** — they're inlined into the client
    bundle at build time. Change later = **redeploy required**.
- Settings → **Networking → Generate Domain** → this is your app URL.

### 5. Wire up CORS (backend)
On the **backend** service set:
```
ALLOW_ORIGINS=https://<your-frontend>.up.railway.app
```
Then redeploy the backend. (Leaving `*` works but is flagged insecure.)

## Environment variables

### Backend + Worker (identical set)
Provider API keys live in the DB (`ai_providers`), so the backend only needs
Supabase creds to load them. Minimum required:

| Variable | Value / note |
|---|---|
| `SUPABASE_URL` | your Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | 🔒 service-role key |
| `SUPABASE_SCHEMA` | `public` |
| `API_KEY` | 🔒 strong secret (login key) |
| `API_KEY_ENABLED` | `true` |
| `DEFAULT_COMPANY_CODE` | `DEVES` |
| `APP_ENV` | `production` |
| `ANSWER_LLM_USE_LOCAL` | `false`  ← cloud-only, skips `llm-server` |
| `ALLOW_ORIGINS` | frontend URL (after step 4) |
| `ENABLE_SCHEDULER` | `true` |
| `ENABLE_LLM_RERANK` | `true` |
| `ENABLE_AGENTIC_ANSWER` | `true` |
| `ENABLE_QUERY_PLANNER` | `true` |
| retrieval/feature flags | copy remaining non-secret flags from `.env` |

> Don't set `APP_PORT` — Railway injects `$PORT` and the Dockerfile honours it.
> The legacy `OLLAMA_*` / `LOCAL_LLM_*` vars can be omitted (unused in cloud mode).

### Frontend
| Variable | Value |
|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | backend public URL |
| `NEXT_PUBLIC_COMPANY_CODE` | `DEVES` |

## Verify after deploy
1. `GET https://<backend>/api/health` → `200`
2. Open the frontend URL → log in with `API_KEY`
3. Ask a chat question → expect a streamed answer (~11–18s)
4. Worker logs show `Worker started — polling job_runs every 10s`

## Notes / gotchas
- **Secrets:** set keys only as Railway service variables — never commit `.env`
  (it's gitignored). Rotate any key that was ever pasted in plaintext.
- **One replica each** (`numReplicas = 1`) — APScheduler is process-local;
  scaling the API to >1 would double-run scheduled jobs.
- **Build minutes:** the frontend rebuilds whenever `NEXT_PUBLIC_*` changes
  (build-time inlining). Backend/worker share an image but build separately.
- **Cost:** 3 always-on services use Railway usage credits; the worker is tiny.
  To trim cost you can fold the worker into the API and rely on the in-process
  scheduler only — but keeping it separate matches the local compose topology.
