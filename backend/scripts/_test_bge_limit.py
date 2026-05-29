"""Find exact character limit for bge-m3 with real mixed Thai/English content."""
import sys, io, urllib.request, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.db.supabase_client import supabase

res = supabase.table("wiki_pages").select("title,content_markdown").eq("company_code","DEVES").execute()
pages = {r["title"]: r["content_markdown"] for r in res.data}

shareholder_cm = pages.get("Deves (About Us - Shareholder)", "")

print(f"Full content length: {len(shareholder_cm)}")
print()

for length in [80, 100, 120, 140, 160, 180, 200, 220, 240, 260]:
    text = shareholder_cm[:length]
    body = json.dumps({"model": "bge-m3", "prompt": text}).encode("utf-8")
    req = urllib.request.Request("http://llm-server:11434/api/embeddings", data=body,
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        dim = len(data.get("embedding", []))
        thai_count = sum(1 for c in text if 0x0E00 <= ord(c) <= 0x0E7F)
        print(f"  {length:3d} chars ({thai_count} thai): OK")
    except:
        thai_count = sum(1 for c in text if 0x0E00 <= ord(c) <= 0x0E7F)
        print(f"  {length:3d} chars ({thai_count} thai): FAIL")
