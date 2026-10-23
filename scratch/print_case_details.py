import json
import sys
from pathlib import Path

with open("results/phase_2/o1_benchmark_results.json", "r", encoding="utf-8") as f:
    d = json.load(f)

cases = d.get("query_case_inspections_b3_v1_vs_v0", {})
print("Cases keys:", list(cases.keys()))

for k in ["top_5_helped", "top_5_hurt"]:
    print(f"\n=== {k} ===")
    items = cases.get(k, [])
    for it in items:
        idx = it.get("query_idx")
        gt = it.get("ground_truth")
        v0_r = it.get("v0_recall10")
        v1_r = it.get("v1_recall10")
        delta = it.get("delta_recall10")
        print(f"Row {idx} | GT: {gt} | V0: {v0_r} -> V1: {v1_r} (Delta: {delta})")
        print(f"  V0 top-10 IDs: {it.get('v0_retrieved_ids', [])}")
        print(f"  V1 top-10 IDs: {it.get('v1_retrieved_ids', [])}")
        print(f"  V1 Prefix: {it.get('v1_prefix')}")
