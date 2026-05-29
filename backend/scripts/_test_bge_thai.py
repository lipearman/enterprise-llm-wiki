"""Test bge-m3 embeddings for short Thai texts."""
import sys, io, urllib.request, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

texts = [
    "ผู้ถือหุ้นรายใหญ่ของเทเวศประกันภัยคือใคร",
    "วิธีเคลมประกันรถยนต์",
    "สาขาของเทเวศประกันภัยมีที่ไหนบ้าง",
    "who are the shareholders",
]
embeddings = []
for t in texts:
    body = json.dumps({"model": "bge-m3", "prompt": t}).encode("utf-8")
    req = urllib.request.Request(
        "http://llm-server:11434/api/embeddings",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    emb = data.get("embedding", [])
    embeddings.append(emb)
    print(f"text: {t[:40]:40s} first5: {[round(x,4) for x in emb[:5]]}")

print()
for i in range(len(texts)):
    for j in range(i + 1, len(texts)):
        a, b = embeddings[i], embeddings[j]
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x ** 2 for x in a) ** 0.5
        nb = sum(x ** 2 for x in b) ** 0.5
        cos = dot / (na * nb) if na * nb > 0 else 0
        print(f"  cos({i},{j}) = {cos:.6f}  ({texts[i][:30]} vs {texts[j][:30]})")
