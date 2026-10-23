import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data_loader import load_stix_all_bundles, load_benchmark_dataset
from src.entity_resolver import CyberEntityResolver

kb = load_stix_all_bundles()
resolver = CyberEntityResolver(stix_kb=kb, random_seed=42)
ds_taa = load_benchmark_dataset("cti-taa").df

print("=" * 80)
print("ITEM 2.4: RECONCILE CASE STUDIES (ROW 21 & ROW 24)")
print("=" * 80)

# Check stored results from phase 2
with open("results/phase_2/o1_benchmark_results.json", "r", encoding="utf-8") as f:
    p2_res = json.load(f)

for row_idx in [21, 24]:
    row = ds_taa.iloc[row_idx]
    q = str(row["query"])
    gt = str(row.get("ground_truth", ""))
    
    print(f"\n--- CTI-TAA Row {row_idx} ---")
    print(f"Ground Truth: {gt}")
    print(f"Query text (first 250 chars):\n{q[:250]}...")
    
    detected = resolver.detect_entities(q)
    print(f"Detected entities ({len(detected)}):")
    for d in detected:
        print(f"  '{d.matched_text}' -> {d.entity.canonical_name} ({d.entity.mitre_id})")
        
    v1_q, _ = resolver.expand_query(q, variant="V1")
    prefix = v1_q[:len(v1_q) - len(q)].strip()
    print(f"V1 Prefix: '{prefix}'")

# Check what query_case_inspections_b3_v1_vs_v0 has stored
if "query_case_inspections_b3_v1_vs_v0" in p2_res:
    cases = p2_res["query_case_inspections_b3_v1_vs_v0"]
    print("\nStored case studies in o1_benchmark_results.json:")
    for c in cases:
        print(f"Stored case index: {c.get('index')}, GT: {c.get('ground_truth')}")
        print(f"  V0 Recall: {c.get('v0_recall')}, V1 Recall: {c.get('v1_recall')}")
        print(f"  V0 top-10 IDs: {c.get('v0_retrieved_top10')}")
        print(f"  V1 top-10 IDs: {c.get('v1_retrieved_top10')}")
