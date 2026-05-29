"""Debug specific failing pages to understand bge-m3 crash pattern."""
import sys, io, urllib.request, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.db.supabase_client import supabase

MAX_THAI = 150


def safe_truncate(text: str) -> str:
    thai_seen = 0
    for i, ch in enumerate(text):
        if 0x0E00 <= ord(ch) <= 0x0E7F:
            thai_seen += 1
            if thai_seen > MAX_THAI:
                return text[:i]
    return text


def embed_sync(text: str):
    body = json.dumps({"model": "bge-m3", "prompt": text}).encode("utf-8")
    req = urllib.request.Request(
        "http://llm-server:11434/api/embeddings",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        return len(data.get("embedding", [])), None
    except Exception as e:
        return 0, str(e)


# Check specific failing pages
failing_titles = [
    "Deves (About Us - Company Profile)",
    "Deves (Contact Us)",
    "Deves (Products - Motor Insurance)",
]

res = supabase.table("wiki_pages").select("title,content_markdown").eq("company_code","DEVES").execute()
pages = {r["title"]: r["content_markdown"] for r in res.data}

for title in failing_titles:
    cm = pages.get(title, "")
    truncated = safe_truncate(cm)
    thai_count = sum(1 for c in truncated if 0x0E00 <= ord(c) <= 0x0E7F)
    total_len = len(truncated)
    print(f"\n=== {title} ===")
    print(f"Truncated to {total_len} chars, {thai_count} Thai chars")
    print(f"Content: {repr(truncated[:200])}")

    # Try embedding
    dim, err = embed_sync(truncated)
    if err:
        print(f"Result: FAIL - {err}")
        # Try with even shorter text
        for shorter in [100, 80, 60, 50, 40, 30]:
            truncated2 = safe_truncate(cm[:200])[:shorter]
            thai2 = sum(1 for c in truncated2 if 0x0E00 <= ord(c) <= 0x0E7F)
            dim2, err2 = embed_sync(truncated2)
            print(f"  Shorter ({shorter} chars, {thai2} thai): {'OK' if not err2 else 'FAIL'}")
            if not err2:
                print(f"    Text: {repr(truncated2)}")
                break
    else:
        print(f"Result: OK dim={dim}")
