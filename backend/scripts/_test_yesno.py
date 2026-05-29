"""Test yes/no type questions for natural responses."""
import sys, io, urllib.request, json, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

API = "http://localhost:8080/api/chat"
KEY = "changeme-enterprise-wiki-2025"

TESTS = [
    "เทเวศประกันภัยมีบริการประกันภัยรถยนต์ไหม",
    "เทเวศมีสาขาในต่างจังหวัดไหม",
    "สามารถซื้อประกันออนไลน์ได้ไหม",
    "เทเวศประกันภัยจดทะเบียนในตลาดหลักทรัพย์ไหม",
]

for q in TESTS:
    body = json.dumps({"question": q, "company_code": "DEVES", "force_rag": True}).encode("utf-8")
    req = urllib.request.Request(API, data=body,
        headers={"Content-Type": "application/json", "X-API-Key": KEY})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    elapsed = time.time() - t0
    print(f'Q: "{q}"')
    print(f'   mode={data.get("mode")}  ({elapsed:.1f}s)')
    print(f'   answer: {data.get("answer","")[:200]}')
    print()
