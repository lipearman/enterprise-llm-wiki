#!/bin/bash
export XDG_RUNTIME_DIR=/run
C=enterprise-llm-wiki-backend-1
podman exec "$C" python -c "
import httpx
from app.db.supabase_client import supabase
p={x['name']:x for x in supabase.table('ai_providers').select('*').execute().data}['openrouter']
r=httpx.get(p['base_url'].rstrip('/')+'/models', headers={'Authorization':'Bearer '+p['api_key']}, timeout=20).json()['data']
free=[m['id'] for m in r if m['id'].endswith(':free') or str(m.get('pricing',{}).get('prompt'))in('0','0.0')]
print('FREE total:', len(free))
# strong instruct/chat families good at Thai + structured output
for kw in ['llama-3.3','llama-3.1','deepseek','qwen','gemma','mistral','gpt-oss','glm','nemotron']:
    hits=[f for f in free if kw in f.lower()]
    if hits: print(f'  {kw:10}:', hits[:4])
"
