"""Verify bge-m3 with real wiki page content."""
import sys, io, urllib.request, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.db.supabase_client import supabase

# Get the shareholder page
res = supabase.table("wiki_pages").select("title,content_markdown").eq("company_code","DEVES").execute()
pages = {r["title"]: r["content_markdown"] for r in res.data}

shareholder_page = pages.get("Deves (About Us - Shareholder)", "")
print(f"Shareholder page length: {len(shareholder_page)} chars")
print(f"First 380 chars:\n{shareholder_page[:380]}")
print()

# Test embedding with bge-m3
for label, text in [
    ("Shareholder page (380 chars)", shareholder_page[:380]),
    ("Claims question", "วิธีเคลมประกันรถยนต์"),
    ("Branch question", "สาขาของเทเวศประกันภัยมีที่ไหนบ้าง"),
    ("Shareholder question", "ผู้ถือหุ้นรายใหญ่ของเทเวศประกันภัยคือใคร"),
]:
    body = json.dumps({"model": "bge-m3", "prompt": text}).encode("utf-8")
    req = urllib.request.Request(
        "http://llm-server:11434/api/embeddings",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        emb = data.get("embedding", [])
        print(f"{label}: OK dim={len(emb)} first3={[round(x,3) for x in emb[:3]]}")
    except Exception as e:
        print(f"{label}: FAIL {e}")
