import sys
from pathlib import Path
import pandas as pd
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.retrieval_eval import compute_paired_bootstrap_ci

df = pd.read_csv('results/phase_4/per_query_cti_taa_attribution.csv')
for metric in ['v2_alias', 'v1_alias']:
    p_llm = df[df['arm'] == 'LLM-only'].sort_values('row_idx')[metric].values
    p_v0 = df[df['arm'] == 'cti-taa_B2_V0'].sort_values('row_idx')[metric].values
    p_v1 = df[df['arm'] == 'cti-taa_B2_V1'].sort_values('row_idx')[metric].values
    
    print(f'=== Metric: {metric} ===')
    print(f'LLM-only mean: {np.mean(p_llm):.4f}')
    print(f'V0 mean: {np.mean(p_v0):.4f}')
    print(f'V1 mean: {np.mean(p_v1):.4f}')
    
    # V0 vs LLM-only
    ci_v0_llm = compute_paired_bootstrap_ci(p_llm, p_v0, n_resamples=10000, seed=42)
    diff_v0_llm = p_v0 - p_llm
    w_0 = int(np.sum(diff_v0_llm > 0))
    l_0 = int(np.sum(diff_v0_llm < 0))
    t_0 = int(np.sum(diff_v0_llm == 0))
    print(f'V0 vs LLM-only: delta={ci_v0_llm["mean_delta"]:.4f}, CI=[{ci_v0_llm["ci_lower"]:.4f}, {ci_v0_llm["ci_upper"]:.4f}], p={ci_v0_llm["p_value"]:.4f}, W/T/L={w_0}/{t_0}/{l_0}')

    # V1 vs V0
    ci_v1_v0 = compute_paired_bootstrap_ci(p_v0, p_v1, n_resamples=10000, seed=42)
    diff_v1_v0 = p_v1 - p_v0
    w_1 = int(np.sum(diff_v1_v0 > 0))
    l_1 = int(np.sum(diff_v1_v0 < 0))
    t_1 = int(np.sum(diff_v1_v0 == 0))
    print(f'V1 vs V0: delta={ci_v1_v0["mean_delta"]:.4f}, CI=[{ci_v1_v0["ci_lower"]:.4f}, {ci_v1_v0["ci_upper"]:.4f}], p={ci_v1_v0["p_value"]:.4f}, W/T/L={w_1}/{t_1}/{l_1}')

    # V1 vs LLM-only
    ci_v1_llm = compute_paired_bootstrap_ci(p_llm, p_v1, n_resamples=10000, seed=42)
    diff_v1_llm = p_v1 - p_llm
    w_2 = int(np.sum(diff_v1_llm > 0))
    l_2 = int(np.sum(diff_v1_llm < 0))
    t_2 = int(np.sum(diff_v1_llm == 0))
    print(f'V1 vs LLM-only: delta={ci_v1_llm["mean_delta"]:.4f}, CI=[{ci_v1_llm["ci_lower"]:.4f}, {ci_v1_llm["ci_upper"]:.4f}], p={ci_v1_llm["p_value"]:.4f}, W/T/L={w_2}/{t_2}/{l_2}')
