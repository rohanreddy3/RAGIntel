import json
from pathlib import Path

path = Path("results/phase_3/o2_benchmark_results.json")
with open(path, "r", encoding="utf-8") as f:
    d = json.load(f)

print("=== KEYS ===")
print(list(d.keys()))

print("\n=== ITEM 1.5 TESTS ===")
print(json.dumps(d.get("tests_item_1_5"), indent=2))

print("\n=== FAMILY P2 HYPOTHESIS CONTRASTS ===")
print(f"{'Hypothesis':<30} | {'Delta Rec':<10} | {'95% CI':<22} | {'p-val':<8} | {'Holm Crit':<10} | {'Holm Sig'}")
print("-" * 95)
for c in d.get("family_p2_contrasts", []):
    crit = f"{c.get('holm_critical_value', 'N/A')}"
    sig = str(c.get("significant_holm", "N/A"))
    ci_str = f"[{c['ci_recall'][0]:+.4f}, {c['ci_recall'][1]:+.4f}]"
    print(f"{c['hypothesis_id']:<30} | {c['delta_recall']:<+10.4f} | {ci_str:<22} | {c['raw_p_value']:<8.4f} | {crit:<10} | {sig}")

print("\n=== CELL SUMMARY (B* = 500) ===")
cells = d.get("cells", {})
print(f"{'Cell Key':<35} | {'Arm':<10} | {'Rec_Strict':<10} | {'Rec_SubCredit':<14} | {'MRR':<8} | {'Tokens':<8} | {'DistinctTech'}")
print("-" * 105)
for k, v in cells.items():
    if isinstance(v, dict) and "mean_Recall_strict" in v:
        print(f"{k:<35} | {v.get('arm',''):<10} | {v.get('mean_Recall_strict',0):<10.4f} | {v.get('mean_Recall_sub_credits_parent',0):<14.4f} | {v.get('mean_MRR',0):<8.4f} | {v.get('mean_tokens_used',0):<8.1f} | {v.get('mean_distinct_techniques',0)}")
    elif k == "cti-taa_no_regression_guard":
        print("\n=== NO REGRESSION GUARD (cti-taa) ===")
        print(json.dumps(v, indent=2))
