#!/bin/bash
export XDG_RUNTIME_DIR=/run
C=enterprise-llm-wiki-backend-1
podman exec "$C" python -c "
import asyncio, httpx, time, json
from app.db.supabase_client import supabase
p={x['name']:x for x in supabase.table('ai_providers').select('*').execute().data}['openrouter']
BASE=p['base_url']; KEY=p['api_key']

CANDS=[
 'openai/gpt-oss-120b:free',
 'meta-llama/llama-3.3-70b-instruct:free',
 'qwen/qwen3-next-80b-a3b-instruct:free',
 'google/gemma-4-31b-it:free',
 'z-ai/glm-4.5-air:free',
]
THAI='บริษัท เทเวศประกันภัย จำกัด (มหาชน) ก่อตั้ง 17 มกราคม 2490 สำนักงานใหญ่ 1099 ถนนเพชรบุรี กรุงเทพฯ ทุนจดทะเบียน 500 ล้านบาท ประกันรถยนต์ (ชั้น 1,2+,3+,3) ประกันอัคคีภัย ประกันภัยทางทะเล ศูนย์บริการ 1788 ฟรีทั่วประเทศ แจ้งเคลมผ่านแอป สายด่วน ตัวแทน เตรียมกรมธรรม์ ใบขับขี่ ทะเบียนรถ'
FACT=('You extract structured facts. Return valid JSON only.','Extract facts. JSON only {\"summary\":string,\"key_facts\":[string],\"entities\":[{\"name\":string,\"type\":string}]}. Thai stays Thai. Do not invent.\n'+THAI,'json_obj')
WIKI=('You generate accurate enterprise wiki pages from facts only.','Create Thai Markdown wiki. Sections: สรุป, ข้อมูลสำคัญ, ผลิตภัณฑ์, การติดต่อ, ขั้นตอนการเคลม. Do not invent.\n'+THAI,'prose')
QA=('You generate canonical QA. Return JSON only.','Generate 4 FAQ pairs. JSON array only [{\"question\":string,\"answer\":string}]. Thai. Concise.\n'+THAI,'json_arr')
TASKS=[('FACT',FACT),('WIKI',WIKI),('QA',QA)]

async def call(model,sys,user):
    body={'model':model,'messages':[{'role':'system','content':sys},{'role':'user','content':user}],'temperature':0,'max_tokens':2500,'stream':False}
    t=time.time()
    async with httpx.AsyncClient(timeout=90) as c:
        r=await c.post(BASE.rstrip('/')+'/chat/completions', json=body, headers={'Authorization':'Bearer '+KEY})
    dt=time.time()-t
    if r.status_code!=200: return dt,None,f'HTTP{r.status_code}'
    return dt,(r.json().get('choices') or [{}])[0].get('message',{}).get('content') or '',None

def chk(kind,txt):
    if not txt: return 'EMPTY'
    s=txt.strip()
    if '\`\`\`' in s:
        parts=s.split('\`\`\`'); s=parts[1] if len(parts)>=2 else s; s=s.replace('json','',1).strip()
    if kind=='json_obj':
        a,b=s.find('{'),s.rfind('}')
        try: json.loads(s[a:b+1]); return 'JSON-OK'
        except: return 'JSON-BAD'
    if kind=='json_arr':
        a,b=s.find('['),s.rfind(']')
        try: return f'JSON-OK({len(json.loads(s[a:b+1]))})'
        except: return 'JSON-BAD'
    th=any('฀'<=ch<='๿' for ch in s)
    return f'PROSE({len(s)}ch,thai={th})'

async def main():
    for model in CANDS:
        cells=[]
        for tname,(sys,user,kind) in TASKS:
            try:
                dt,txt,err=await call(model,sys,user)
                cells.append(f'{tname}:{err}' if err else f'{tname}:{chk(kind,txt)} {dt:.1f}s')
            except Exception as e: cells.append(f'{tname}:ERR {type(e).__name__}')
            await asyncio.sleep(6)
        print(f'{model:42}|', '  '.join(cells))

asyncio.run(main())
"
