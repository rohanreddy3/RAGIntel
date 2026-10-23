import json
from pathlib import Path

path = Path("results/phase_3/o2_phase3c_benchmark_results.json")
with open(path, "r", encoding="utf-8") as f:
    d = json.load(f)

res = d["results"]["text_and_metadata"]
print("BUDGET SCALING (Recall_sub_credits_parent):")
for ds in ["cti-ate", "CTI-ATTACK"]:
    print(f"\n--- {ds} (B2) ---")
    b2_data = res[ds]["B2"]
    for arm in ["E0_prime", "E0_prime_tech", "E1a", "E1_mixed", "E1b_mixed", "E1c_mixed"]:
        if arm in b2_data:
            vals = [f"B={b}: {b2_data[arm][str(b)]['summary']['Recall_sub_credits_parent']:.4f}" for b in [500, 1000, 2000, 4000]]
            print(f"  {arm:15s} | " + " | ".join(vals))
