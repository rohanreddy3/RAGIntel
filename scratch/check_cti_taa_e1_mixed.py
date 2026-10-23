import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.data_loader import load_benchmark_dataset, load_stix_all_bundles
from src.retrieval_eval import compute_retrieval_metrics_taa_alias_aware

p_3c = REPO_ROOT / "results" / "phase_3" / "top50_phase3c_chunks.json"
with open(p_3c, "r", encoding="utf-8") as f:
    c_3c = json.load(f)

stix_kb = load_stix_all_bundles()
group_alias_map = stix_kb.get_group_alias_map()
ds_taa = load_benchmark_dataset("cti-taa")
df_taa = ds_taa.df

e0_queries = c_3c["cti-taa"]["B2"]["E0_prime"]
e1_mixed_queries = c_3c["cti-taa"]["B2"]["E1_mixed"]

print(f"Loaded {len(e0_queries)} E0_prime queries and {len(e1_mixed_queries)} E1_mixed queries.")

e0_recalls = []
e1_recalls = []
displaced_cases = []

for idx, row in df_taa.iterrows():
    gt = str(row["ground_truth"])
    e0_top50 = e0_queries[idx]["top50"][:10]
    e1_top50 = e1_mixed_queries[idx]["top50"][:10]

    # Convert top-10 chunks into mock docs for evaluation
    docs_e0 = [{"content": c.get("content", ""), "metadata": c.get("metadata", {})} for c in e0_top50]
    docs_e1 = [{"content": c.get("content", ""), "metadata": c.get("metadata", {})} for c in e1_top50]

    m_e0 = compute_retrieval_metrics_taa_alias_aware(docs_e0, gt, group_alias_map=group_alias_map, k_values=[10])
    m_e1 = compute_retrieval_metrics_taa_alias_aware(docs_e1, gt, group_alias_map=group_alias_map, k_values=[10])

    r_e0 = m_e0["Recall@10"]
    r_e1 = m_e1["Recall@10"]
    e0_recalls.append(r_e0)
    e1_recalls.append(r_e1)

    if r_e0 > r_e1:
        # Ground truth was in E0 top 10 but displaced in E1 top 10
        # Find which threat group / object displaced it
        e0_groups = [c.get("metadata", {}).get("name") for c in e0_top50 if c.get("metadata", {}).get("type") == "intrusion-set"]
        e1_techs = [c.get("metadata", {}).get("name") for c in e1_top50 if c.get("metadata", {}).get("type") == "attack-pattern"]
        displaced_cases.append({
            "row_idx": int(idx),
            "ground_truth": gt,
            "e0_recall": r_e0,
            "e1_recall": r_e1,
            "e0_top_groups": e0_groups,
            "e1_top_techs": e1_techs[:5],
            "e1_top10_all": [f"{c.get('metadata', {}).get('type')}: {c.get('metadata', {}).get('name')}" for c in e1_top50],
        })

print(f"\nE0_prime Recall@10 mean: {sum(e0_recalls)/len(e0_recalls):.4f}")
print(f"E1_mixed Recall@10 mean: {sum(e1_recalls)/len(e1_recalls):.4f}")
delta = sum(e1_recalls)/len(e1_recalls) - sum(e0_recalls)/len(e0_recalls)
print(f"Delta (E1_mixed - E0_prime): {delta:+.4f}")
print(f"\nNumber of queries where E0 succeeded but E1_mixed failed: {len(displaced_cases)}")

print("\n--- 5 DISPLACED CASES ---")
for case in displaced_cases[:5]:
    print(f"\nQuery Row {case['row_idx']} (Ground Truth: {case['ground_truth']}):")
    print(f"  E0 Recall@10: {case['e0_recall']} | E1_mixed Recall@10: {case['e1_recall']}")
    print(f"  E0 top groups: {case['e0_top_groups']}")
    print(f"  E1 top items in top-10: {case['e1_top10_all'][:6]}")
