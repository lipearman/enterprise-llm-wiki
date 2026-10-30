# Deploy: API + Database on llm-server (Docker)

Self-hosts the **database** (Postgres + pgvector, Supabase-compatible via PostgREST)
and the **API** (FastAPI backend + worker) on `llm-server`, behind **Caddy** which
maps the backend port to a route path. TLS + the public `ts.net` hostname are
provided by the machine's existing **`tailscale serve`** (it already owns :443 and
routes other apps by path). The app is mounted at the `/ewiki` path. The
**frontend** runs on Vercel.

```
browser (tailnet) ─► https://llm-server.tail923b9a.ts.net/ewiki/...   (tailscale serve, TLS)
                       └─ strips /ewiki ─► 127.0.0.1:18490 (Caddy)
                                            ├─ /api/*  ─► backend:8080   (FastAPI)
                                            └─ :8000   ─► rest:3000      (PostgREST = Supabase /rest/v1, internal)
backend ─► db (postgres+pgvector)   via PostgREST
backend ─► Ollama on Windows host   (100.99.80.84:11434)   embeddings + local LLM
```

> **Access is Tailnet-only.** Browsers must be on the tailnet to reach the API.

## Layout
- `docker-compose.yml` — db, rest (PostgREST), backend, worker, caddy
- `Caddyfile` — `/api/*` → backend + internal `/rest/v1` → PostgREST gateway
- `db/00_roles.sql`, `db/99_grants.sql` — Supabase-compatible roles + grants
- `migrate.sh` — roles → schema migrations (`backend/sql/*.sql`) → grants
- `.env` / `backend.env` — secrets (gitignored)

## How it runs on this host (notes)
- SSH drops into **WSL2**; run remote commands as `bash -lc '…'`.
- Docker Desktop's Windows credential helper fails over SSH, so pulls use a
  credential-free config: `export DOCKER_CONFIG=$HOME/.docker-anon` (contains `{}`).
- Ollama runs on the **Windows host** (`100.99.80.84:11434`), reachable from
  containers over the mirrored WSL network.

## First deploy (on llm-server, via `ssh admin@llm-server`)
```bash
export DOCKER_CONFIG=$HOME/.docker-anon
cd ~/enterprise-llm-wiki/deploy/llm-server

docker compose up -d db          # start Postgres first
./migrate.sh                     # roles + schema + grants
docker compose up -d --build     # rest, backend, worker, caddy

# Publish on the ts.net name via the existing tailscale serve (Windows node):
"/mnt/c/Program Files/Tailscale/tailscale.exe" serve --bg --https=443 \
  --set-path=/ewiki http://127.0.0.1:18490

# Verify (from any tailnet device)
curl https://llm-server.tail923b9a.ts.net/ewiki/api/health
```

## Migrate data from Supabase Cloud
```bash
# SRC = Supabase "Direct connection" / "Connection string" (URI form), e.g.
#   postgres://postgres:PASS@db.<ref>.supabase.co:5432/postgres
pg_dump "$SRC" --data-only --no-owner --no-privileges \
  --disable-triggers -n public > /tmp/data.sql
docker compose exec -T db psql -U postgres -d postgres < /tmp/data.sql
docker compose restart rest
```

## Tighten CORS after the Vercel domain is known
In `backend.env` set `ALLOW_ORIGINS` and `FRONTEND_ORIGIN` to the Vercel URL,
then `docker compose up -d backend worker`.

## Frontend on Vercel (Git Integration — auto deploy)
1. Vercel → **Add New Project** → import `lipearman/enterprise-llm-wiki`.
2. **Root Directory** = `frontend` (Framework auto-detects Next.js).
3. Environment Variables:
   - `NEXT_PUBLIC_API_BASE_URL = https://llm-server.tail923b9a.ts.net/ewiki`
   - `NEXT_PUBLIC_COMPANY_CODE = DEVES`
4. Deploy. Every push to `master` then auto-deploys.
5. Copy the deployed domain into `backend.env` `ALLOW_ORIGINS` and restart backend.

## Operations
- Containers use `restart: unless-stopped`; `tailscale serve --bg` persists across reboots.
- Logs: `docker compose logs -f backend` (or `worker`, `rest`, `caddy`).
- Postgres is on `127.0.0.1:55432` for maintenance (`psql`, `pg_dump`).
