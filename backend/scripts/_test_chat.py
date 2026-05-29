"""Test chat endpoint with multiple Thai questions."""
import sys, io, urllib.request, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

API = "http://localhost:8080/api/chat"
KEY = "changeme-enterprise-wiki-2025"

QUESTIONS = [
    "ผู้ถือหุ้นรายใหญ่ของเทเวศประกันภัยคือใคร",
    "โครงสร้างผู้ถือหุ้นของเทเวศประกันภัยเป็นอย่างไร",
    "วิธีเคลมประกันรถยนต์",
    "สาขาของเทเวศประกันภัยมีที่ไหนบ้าง",
]

for q in QUESTIONS:
    body = json.dumps({"question": q, "company_code": "DEVES"}).encode("utf-8")
    req = urllib.request.Request(API, data=body,
        headers={"Content-Type": "application/json", "X-API-Key": KEY})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    mode = data.get("mode")
    answer = data.get("answer", "")[:200]
    sources = data.get("sources", [])
    print(f"Q: {q}")
    print(f"   mode={mode}  cached={data.get('cached')}")
    print(f"   answer: {answer}")
    if sources:
        top = sources[0]
        print(f"   top_src: [{top.get('source_type')}] score={top.get('score',0):.3f} {top.get('title','')[:50]}")
    print()
