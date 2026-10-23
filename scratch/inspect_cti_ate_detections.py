import json
from pathlib import Path

p = Path("results/phase_4/detected_examples_audit.json")
with open(p, "r", encoding="utf-8") as f:
    data = json.load(f)

ate = data["examples"]["cti-ate"]
print(f"Total cti-ate queries: {len(ate)}")
detected_counts = [len(r["detected_entities"]) for r in ate]
queries_with_ge1 = sum(1 for c in detected_counts if c >= 1)
print(f"Queries with >=1 entity: {queries_with_ge1} / {len(ate)} ({queries_with_ge1/len(ate)*100:.2f}%)")
print(f"Query without entity: {[r['row_idx'] for r in ate if len(r['detected_entities']) == 0]}")

print("\nFirst 10 rows inspection:")
for r in ate[:10]:
    names = [(e["canonical_name"], e["matched_alias"], e["span"]) for e in r["detected_entities"]]
    print(f"Row {r['row_idx']:2d}: {r['num_detected']} entities -> {names}")
    print(f"  preview: {r['query_preview'][:100]}")
