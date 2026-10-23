import json
from pathlib import Path

p_3b = Path("results/phase_3/top50_ranked_chunks.json")
p_3c = Path("results/phase_3/top50_phase3c_chunks.json")

with open(p_3b, "r", encoding="utf-8") as f:
    c_3b = json.load(f)

with open(p_3c, "r", encoding="utf-8") as f:
    c_3c = json.load(f)

queries_3b = c_3b.get("cti-ate", {}).get("B3", {}).get("E1a", [])
queries_3c = c_3c.get("cti-ate", {}).get("B3", {}).get("E1a", [])

print(f"3B cti-ate B3 E1a: {len(queries_3b)} queries")
print(f"3C cti-ate B3 E1a: {len(queries_3c)} queries")

if len(queries_3b) > 0 and len(queries_3c) > 0:
    for idx in range(min(5, len(queries_3b))):
        q_3b = queries_3b[idx]
        q_3c = queries_3c[idx]
        top_3b = [c.get("mitre_id", c.get("chunk_id", "")) for c in q_3b["top50"][:5]]
        top_3c = [c.get("mitre_id", c.get("chunk_id", "")) for c in q_3c["top50"][:5]]
        print(f"Row {idx}:")
        print(f"  3B top5: {top_3b}")
        print(f"  3C top5: {top_3c}")
        # check chunk texts or scores
        print(f"  3B first chunk id: {q_3b['top50'][0].get('chunk_id')} | score: {q_3b['top50'][0].get('score')}")
        print(f"  3C first chunk id: {q_3c['top50'][0].get('chunk_id')} | score: {q_3c['top50'][0].get('score')}")
