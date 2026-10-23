import json
import re
import sys
sys.path.insert(0, ".")
from pathlib import Path
from typing import Dict, Any, List

import pandas as pd
from transformers import AutoTokenizer

from src.data_loader import load_benchmark_dataset, load_stix_bundle
from src.retrieval_eval import normalize_group_name

def main():
    print("Loading STIX Knowledge Base...")
    kb = load_stix_bundle()
    group_alias_map = kb.get_group_alias_map()
    
    print("Loading CTI-TAA dataset...")
    dinfo = load_benchmark_dataset("cti-taa")
    df = dinfo.df
    
    print("Loading B2 (truncated) and B3 (MaxSim) completed results...")
    df_b2 = pd.read_csv("results/phase_1/retrieval_cti_taa_before_truncated.csv")
    df_b3 = pd.read_csv("results/phase_1/retrieval_cti_taa_after_longquery.csv")
    
    print("Loading tokenizer for all-MiniLM-L6-v2...")
    tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
    
    records = []
    
    print("\nRunning CTI-TAA Diagnostic...")
    for idx, row in df.iterrows():
        query = str(row["query"])
        gt_str = str(row.get("ground_truth", ""))
        
        # 1. Check whether any alias of GT appears in first 256 tokens
        tokens = tokenizer.tokenize(query)
        first_256_tokens = tokens[:256]
        first_256_text = tokenizer.convert_tokens_to_string(first_256_tokens).lower()
        
        raw_gt_norm = normalize_group_name(gt_str)
        all_gt_aliases = {raw_gt_norm}
        for gid, gdata in group_alias_map.items():
            canonical_norm = normalize_group_name(gdata.get("canonical_name", ""))
            alias_norms = {normalize_group_name(a) for a in gdata.get("aliases", [])}
            if raw_gt_norm == canonical_norm or raw_gt_norm in alias_norms or any(a in raw_gt_norm for a in alias_norms if len(a) > 3):
                all_gt_aliases.add(canonical_norm)
                all_gt_aliases.update(alias_norms)
                
        alias_in_256 = False
        matching_aliases_found = []
        norm_first_256 = normalize_group_name(first_256_text)
        for alias in all_gt_aliases:
            if len(alias) >= 3 and alias in norm_first_256:
                alias_in_256 = True
                matching_aliases_found.append(alias)
                
        # 2. Extract ranks from MRR in completed B2 and B3 results
        mrr_b2 = float(df_b2.loc[idx, "MRR"])
        rec10_b2 = float(df_b2.loc[idx, "Recall@10"])
        rank_b2 = round(1.0 / mrr_b2) if mrr_b2 > 0 else 0  # 0 indicates not in top 10
        
        mrr_b3 = float(df_b3.loc[idx, "MRR"])
        rec10_b3 = float(df_b3.loc[idx, "Recall@10"])
        rank_b3 = round(1.0 / mrr_b3) if mrr_b3 > 0 else 0
        
        records.append({
            "query_idx": idx,
            "ground_truth": gt_str,
            "alias_in_first_256": alias_in_256,
            "matching_aliases": matching_aliases_found,
            "rank_B2": rank_b2,
            "rank_B3": rank_b3,
            "Recall@10_B2": rec10_b2,
            "Recall@10_B3": rec10_b3,
            "MRR_B2": mrr_b2,
            "MRR_B3": mrr_b3,
        })
        print(f"Query {idx:2d} | GT: {gt_str[:15]:15s} | in_256: {str(alias_in_256):5s} | Rank B2: {rank_b2:2d} (R@10: {rec10_b2}) | Rank B3: {rank_b3:2d} (R@10: {rec10_b3})")
        
    diag_df = pd.DataFrame(records)
    out_csv = Path("results/phase_1/cti_taa_diagnostic.csv")
    diag_df.to_csv(out_csv, index=False)
    print(f"\nSaved diagnostic CSV to {out_csv}")
    
    # 3. Compute splits
    split_true = diag_df[diag_df["alias_in_first_256"] == True]
    split_false = diag_df[diag_df["alias_in_first_256"] == False]
    
    print("\n" + "=" * 65)
    print("CTI-TAA DIAGNOSTIC SUMMARY (DESCRIPTIVE ONLY)")
    print("=" * 65)
    print(f"Total Queries: {len(diag_df)}")
    print(f"Queries with Alias in First 256 Tokens: {len(split_true)} ({len(split_true)/len(diag_df)*100:.1f}%)")
    print(f"Queries WITHOUT Alias in First 256 Tokens: {len(split_false)} ({len(split_false)/len(diag_df)*100:.1f}%)")
    
    print("\n--- Split: Alias Present in First 256 Tokens (N = {}) ---".format(len(split_true)))
    print(f"Recall@10 (B2: Truncated) : {split_true['Recall@10_B2'].mean():.4f}")
    print(f"Recall@10 (B3: MaxSim)    : {split_true['Recall@10_B3'].mean():.4f}")
    print(f"MRR (B2: Truncated)       : {split_true['MRR_B2'].mean():.4f}")
    print(f"MRR (B3: MaxSim)          : {split_true['MRR_B3'].mean():.4f}")
    hits_b2_true = (split_true['Recall@10_B2'] > 0).sum()
    hits_b3_true = (split_true['Recall@10_B3'] > 0).sum()
    print(f"Top-10 Hits: B2 = {hits_b2_true}/{len(split_true)} | B3 = {hits_b3_true}/{len(split_true)}")
    
    print("\n--- Split: Alias NOT Present in First 256 Tokens (N = {}) ---".format(len(split_false)))
    print(f"Recall@10 (B2: Truncated) : {split_false['Recall@10_B2'].mean():.4f}")
    print(f"Recall@10 (B3: MaxSim)    : {split_false['Recall@10_B3'].mean():.4f}")
    print(f"MRR (B2: Truncated)       : {split_false['MRR_B2'].mean():.4f}")
    print(f"MRR (B3: MaxSim)          : {split_false['MRR_B3'].mean():.4f}")
    hits_b2_false = (split_false['Recall@10_B2'] > 0).sum()
    hits_b3_false = (split_false['Recall@10_B3'] > 0).sum()
    print(f"Top-10 Hits: B2 = {hits_b2_false}/{len(split_false)} | B3 = {hits_b3_false}/{len(split_false)}")
    
    summary_data = {
        "total_queries": len(diag_df),
        "split_alias_in_256": {
            "count": len(split_true),
            "percentage": round(len(split_true)/len(diag_df)*100, 1),
            "recall10_B2_truncated": round(float(split_true['Recall@10_B2'].mean()), 4),
            "recall10_B3_maxsim": round(float(split_true['Recall@10_B3'].mean()), 4),
            "mrr_B2_truncated": round(float(split_true['MRR_B2'].mean()), 4),
            "mrr_B3_maxsim": round(float(split_true['MRR_B3'].mean()), 4),
            "hits_top10_B2": int(hits_b2_true),
            "hits_top10_B3": int(hits_b3_true),
        },
        "split_no_alias_in_256": {
            "count": len(split_false),
            "percentage": round(len(split_false)/len(diag_df)*100, 1),
            "recall10_B2_truncated": round(float(split_false['Recall@10_B2'].mean()), 4) if len(split_false) > 0 else 0.0,
            "recall10_B3_maxsim": round(float(split_false['Recall@10_B3'].mean()), 4) if len(split_false) > 0 else 0.0,
            "mrr_B2_truncated": round(float(split_false['MRR_B2'].mean()), 4) if len(split_false) > 0 else 0.0,
            "mrr_B3_maxsim": round(float(split_false['MRR_B3'].mean()), 4) if len(split_false) > 0 else 0.0,
            "hits_top10_B2": int(hits_b2_false),
            "hits_top10_B3": int(hits_b3_false),
        }
    }
    
    with open("results/phase_1/cti_taa_diagnostic_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

if __name__ == "__main__":
    main()
