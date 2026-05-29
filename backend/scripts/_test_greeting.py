"""Test greeting detection + normal questions."""
import sys, io, urllib.request, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

API = "http://localhost:8080/api/chat"
KEY = "changeme-enterprise-wiki-2025"

TESTS = [
    # Greetings
    "สวัสดี",
    "สวัสดีครับ",
    "หวัดดี",
    "Hello",
    "hi!",
    "Good morning",
    # Normal questions (should NOT trigger greeting)
    "ผู้ถือหุ้นรายใหญ่ของเทเวศประกันภัยคือใคร",
    "วิธีเคลมประกันรถยนต์",
]

for q in TESTS:
    body = json.dumps({"question": q, "company_code": "DEVES"}).encode("utf-8")
    req = urllib.request.Request(API, data=body,
        headers={"Content-Type": "application/json", "X-API-Key": KEY})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    mode = data.get("mode")
    answer = data.get("answer", "")[:120]
    print(f'Q: "{q}"')
    print(f"   mode={mode}")
    print(f"   answer: {answer}")
    print()
