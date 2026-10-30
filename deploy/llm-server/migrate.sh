#!/usr/bin/env bash
# Initialise roles, run schema migrations, apply grants, reload PostgREST.
# Idempotent-ish: safe to re-run on a fresh DB; most migrations use IF (NOT) EXISTS.
set -euo pipefail
cd "$(dirname "$0")"
set -a; source ./.env; set +a

DB="docker compose exec -T db psql -v ON_ERROR_STOP=1 -U postgres -d postgres"

echo "[1/4] roles"
$DB < db/00_roles.sql
docker compose exec -T db psql -U postgres -d postgres \
  -c "alter role authenticator login password '${POSTGRES_PASSWORD}';"

echo "[2/4] schema migrations (backend/sql/*.sql in order)"
for f in $(ls ../../backend/sql/*.sql | sort); do
  echo "   -> $(basename "$f")"
  $DB < "$f"
done

echo "[3/4] grants"
$DB < db/99_grants.sql

echo "[4/4] restart PostgREST (reload schema cache)"
docker compose restart rest
echo "migrate.sh: done"
