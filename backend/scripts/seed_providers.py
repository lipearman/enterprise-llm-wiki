#!/usr/bin/env python
"""
Seed AI providers + a sample answer_llm failover chain.

Run AFTER creating the tables (sql/010_ai_providers.sql).
Provide the API keys via environment variables (never hard-code secrets here):

    SEED_CEREBRAS_KEY=...  SEED_SAMBANOVA_KEY=...  SEED_OPENROUTER_KEY=... \
    SEED_NVIDIA_KEY=...     SEED_OLLAMA_KEY=... \
    python -m scripts.seed_providers

Idempotent: upserts providers by name. Any provider whose key env var is unset
is skipped. Manage everything else from the /providers page afterwards.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.db.supabase_client import supabase  # noqa: E402

PROVIDERS = [
    {"name": "cerebras",   "base_url": "https://api.cerebras.ai/v1",          "env": "SEED_CEREBRAS_KEY"},
    {"name": "sambanova",  "base_url": "https://api.sambanova.ai/v1",         "env": "SEED_SAMBANOVA_KEY"},
    {"name": "openrouter", "base_url": "https://openrouter.ai/api/v1",        "env": "SEED_OPENROUTER_KEY"},
    {"name": "nvidia",     "base_url": "https://integrate.api.nvidia.com/v1", "env": "SEED_NVIDIA_KEY"},
    {"name": "ollama",     "base_url": "https://ollama.com/v1",               "env": "SEED_OLLAMA_KEY"},
]

# answer_llm failover chain: cerebras → sambanova → openrouter (fast OpenAI-compat)
ANSWER_CHAIN = [
    ("cerebras",   "gpt-oss-120b",             10),
    ("sambanova",  "gpt-oss-120b",             20),
    ("openrouter", "openai/gpt-oss-120b:free", 30),
]


def main() -> None:
    ids: dict[str, str] = {}
    for p in PROVIDERS:
        key = os.environ.get(p["env"])
        if not key:
            print(f"  skip {p['name']} (env {p['env']} not set)")
            continue
        row = {"name": p["name"], "base_url": p["base_url"], "api_key": key}
        existing = supabase.table("ai_providers").select("id").eq("name", p["name"]).execute().data
        if existing:
            supabase.table("ai_providers").update(row).eq("id", existing[0]["id"]).execute()
            ids[p["name"]] = existing[0]["id"]
            print(f"  updated provider: {p['name']}")
        else:
            res = supabase.table("ai_providers").insert({**row, "protocol": "openai", "is_active": True}).execute()
            ids[p["name"]] = res.data[0]["id"]
            print(f"  created provider: {p['name']}")

    # answer_llm chain — clear existing then insert (only providers that were seeded)
    supabase.table("ai_role_assignments").delete().eq("role", "answer_llm").execute()
    for name, model, prio in ANSWER_CHAIN:
        if name not in ids:
            continue
        supabase.table("ai_role_assignments").insert({
            "role": "answer_llm", "provider_id": ids[name], "model": model,
            "priority": prio, "is_active": True,
        }).execute()
        print(f"  answer_llm[{prio}] = {name} / {model}")

    print("\nDone. Manage everything else from the /providers page.")


if __name__ == "__main__":
    main()
