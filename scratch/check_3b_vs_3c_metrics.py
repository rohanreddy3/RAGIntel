import json
from pathlib import Path

# 1. Load Phase 3B benchmark results
p_3b_res = Path("results/phase_3/o2_benchmark_results.json")
if p_3b_res.is_file():
    with open(p_3b_res, "r", encoding="utf-8") as f:
        d_3b = json.load(f)
    print("Phase 3B benchmark results loaded.")
    # Check evaluations / results structure
    if "evaluations" in d_3b:
        print("3B evaluations keys:", list(d_3b["evaluations"].keys()))
    if "results" in d_3b:
        print("3B results keys:", list(d_3b["results"].keys()))
        b3_e1a_3b = d_3b["results"].get("cti-ate", {}).get("B3", {}).get("E1a", {})
        print("3B cti-ate B3 E1a keys:", list(b3_e1a_3b.keys()))
        for k in b3_e1a_3b:
            if isinstance(b3_e1a_3b[k], dict) and "summary" in b3_e1a_3b[k]:
                print(f"  3B budget {k}: Recall_sub={b3_e1a_3b[k]['summary'].get('Recall_sub_credits_parent')} MRR={b3_e1a_3b[k]['summary'].get('MRR')}")
            else:
                print(f"  3B key {k}: {b3_e1a_3b[k]}")

# 2. Load Phase 3C benchmark results
p_3c_res = Path("results/phase_3/o2_phase3c_benchmark_results.json")
if p_3c_res.is_file():
    with open(p_3c_res, "r", encoding="utf-8") as f:
        d_3c = json.load(f)
    print("\nPhase 3C benchmark results loaded.")
    b3_e1a_3c = d_3c["results"]["text_and_metadata"].get("cti-ate", {}).get("B3", {}).get("E1a", {})
    print("3C cti-ate B3 E1a keys:", list(b3_e1a_3c.keys()))
    for k in b3_e1a_3c:
        if isinstance(b3_e1a_3c[k], dict) and "summary" in b3_e1a_3c[k]:
            print(f"  3C budget {k}: Recall_sub={b3_e1a_3c[k]['summary'].get('Recall_sub_credits_parent')} MRR={b3_e1a_3c[k]['summary'].get('MRR')}")

# Also check top-50 untruncated metrics in 3B
print("\nChecking top-level metrics in 3B:")
for k, v in d_3b.items():
    if isinstance(v, dict):
        print(f"  key {k}: subkeys={list(v.keys())[:5]}")
