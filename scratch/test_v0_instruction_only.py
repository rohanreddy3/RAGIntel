import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import numpy as np
from src.data_loader import load_benchmark_dataset, load_stix_all_bundles
from src.retriever import HybridSTIXRetriever
from src.retrieval_eval import compute_retrieval_metrics_taa_alias_aware
from scripts.run_query_hygiene_audit import split_query

with open('results/phase_6d/gt_alias_leakage_audit.json') as f:
    d = json.load(f)
leaked = set(d['leaked_row_indices'])
clean_indices = [i for i in range(50) if i not in leaked]

stix_kb = load_stix_all_bundles()
group_alias_map = stix_kb.get_group_alias_map()
retriever = HybridSTIXRetriever(stix_kb=stix_kb, cache_dir=".cache/retriever_index_all")

ds_taa = load_benchmark_dataset("cti-taa")
df_taa = ds_taa.df

recalls = []
for idx, row in df_taa.iterrows():
    raw_q = str(row["query"])
    gt = str(row.get("ground_truth", ""))
    instruction, body, marker = split_query(raw_q)
    
    docs = retriever.retrieve(instruction, top_k=10, enable_query_chunking=False)
    metrics = compute_retrieval_metrics_taa_alias_aware(
        docs, gt, k_values=[1, 3, 5, 10], group_alias_map=group_alias_map
    )
    recalls.append(metrics["Recall@10"])

recalls_50 = np.array(recalls)
recalls_40 = recalls_50[clean_indices]

print(f"V0-instruction-only Full-50 Object_Recall@10:  {np.mean(recalls_50):.4f} ({np.sum(recalls_50)}/{len(recalls_50)})")
print(f"V0-instruction-only Clean-40 Object_Recall@10: {np.mean(recalls_40):.4f} ({np.sum(recalls_40)}/{len(recalls_40)})")
