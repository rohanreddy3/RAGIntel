import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import numpy as np
import pandas as pd
from scipy.stats import binomtest
from src.data_loader import load_benchmark_dataset, load_stix_all_bundles
from scripts.run_o1_phase5_benchmark import build_stix_indices
from scripts.compute_phase6c_metrics import score_group_match

# 1. Clean indices
with open('results/phase_6d/gt_alias_leakage_audit.json') as f:
    d = json.load(f)
leaked = set(d['leaked_row_indices'])
clean_indices = [i for i in range(50) if i not in leaked]
assert len(clean_indices) == 40

# 2. Retrieval scores
with open('results/phase_2/p1_eval_checkpoint.json') as f:
    p2 = json.load(f)
with open('results/phase_5/o1_phase5_benchmark_results.json') as f:
    p5 = json.load(f)

v0_ret_50 = [float(x['Recall@10']) for x in p2['E0-STIX-ALL_B2_V0_cti-taa']]
v0h_ret_50 = p5['per_query_archive']['V0h']['B2']['object_level']['Recall@10']
vrel_ret_50 = p5['per_query_archive']['Vrel']['B2']['object_level']['Recall@10']

v0_ret_40 = [v0_ret_50[i] for i in clean_indices]
v0h_ret_40 = [v0h_ret_50[i] for i in clean_indices]
vrel_ret_40 = [vrel_ret_50[i] for i in clean_indices]

# 3. Generator scores
df_taa = load_benchmark_dataset('cti-taa').df
stix_kb = load_stix_all_bundles()
intrusion_sets, _, _, _ = build_stix_indices(stix_kb)

def get_scores_from_files(cache_dir: Path, filename_pattern: str):
    scores = []
    for idx in range(50):
        fname = filename_pattern.format(idx=idx)
        fpath = cache_dir / fname
        assert fpath.exists(), f"Missing file: {fpath}"
        with open(fpath, 'r', encoding='utf-8') as fp:
            data = json.load(fp)
        ans = data.get('raw_answer', '')
        gt = str(df_taa.iloc[idx]['ground_truth'])
        scores.append(score_group_match(ans, gt, intrusion_sets)['v2_alias'])
    return scores

cache_prim = Path('.cache/api_runner')
cache_sec = Path('.cache/api_runner_second_gen')

prim_llm_scores = get_scores_from_files(cache_prim, 'LLM-only_cti-taa_row_{idx}.json')
prim_v0_scores = get_scores_from_files(cache_prim, 'cti-taa_B2_V0_cti-taa_row_{idx}.json')
prim_v0h_scores = get_scores_from_files(cache_prim, 'V0h_cti-taa_row_{idx}.json')
prim_vrel_scores = get_scores_from_files(cache_prim, 'Vrel_cti-taa_row_{idx}.json')

sec_llm_scores = get_scores_from_files(cache_sec, 'LLM_only_cti-taa_row_{idx}.json')
sec_v0_scores = get_scores_from_files(cache_sec, 'V0_cti-taa_row_{idx}.json')
sec_v0h_scores = get_scores_from_files(cache_sec, 'V0h_cti-taa_row_{idx}.json')
sec_vrel_scores = get_scores_from_files(cache_sec, 'Vrel_cti-taa_row_{idx}.json')

prim_llm_40 = [prim_llm_scores[i] for i in clean_indices]
prim_v0_40 = [prim_v0_scores[i] for i in clean_indices]
prim_v0h_40 = [prim_v0h_scores[i] for i in clean_indices]
prim_vrel_40 = [prim_vrel_scores[i] for i in clean_indices]

sec_llm_40 = [sec_llm_scores[i] for i in clean_indices]
sec_v0_40 = [sec_v0_scores[i] for i in clean_indices]
sec_v0h_40 = [sec_v0h_scores[i] for i in clean_indices]
sec_vrel_40 = [sec_vrel_scores[i] for i in clean_indices]

def bootstrap_ci(ctrl, trt, n_boot=10000, seed=42):
    rng = np.random.default_rng(seed)
    diffs = np.array(trt) - np.array(ctrl)
    n = len(diffs)
    boot_means = [np.mean(rng.choice(diffs, size=n, replace=True)) for _ in range(n_boot)]
    return float(np.percentile(boot_means, 2.5)), float(np.percentile(boot_means, 97.5))

def exact_sign_p(ctrl, trt):
    diffs = np.array(trt) - np.array(ctrl)
    w = int(np.sum(diffs > 1e-6))
    l = int(np.sum(diffs < -1e-6))
    t = int(np.sum(np.abs(diffs) <= 1e-6))
    n = w + l
    if n == 0:
        p = 1.0
    else:
        p = float(binomtest(min(w, l), n, p=0.5, alternative='two-sided').pvalue)
    return w, t, l, p

def run_contrasts(arm_dict, metric_name):
    # Contrats:
    # 1. V0h vs V0 (ctrl: V0, trt: V0h)
    # 2. Vrel vs V0h (ctrl: V0h, trt: Vrel)
    # 3. V0h vs LLM-only (ctrl: LLM, trt: V0h)
    # 4. Vrel vs LLM-only (ctrl: LLM, trt: Vrel)
    # 5. V0 vs LLM-only (ctrl: LLM, trt: V0)
    contrasts = [
        ('V0h vs V0', 'V0', 'V0h'),
        ('Vrel vs V0h', 'V0h', 'Vrel'),
        ('V0h vs LLM-only', 'LLM-only', 'V0h') if 'LLM-only' in arm_dict else None,
        ('Vrel vs LLM-only', 'LLM-only', 'Vrel') if 'LLM-only' in arm_dict else None,
        ('V0 vs LLM-only', 'LLM-only', 'V0') if 'LLM-only' in arm_dict else None,
    ]
    contrasts = [c for c in contrasts if c is not None]
    rows = []
    for c_name, c_ctrl, c_trt in contrasts:
        ctrl = arm_dict[c_ctrl]
        trt = arm_dict[c_trt]
        c_mean = float(np.mean(ctrl))
        t_mean = float(np.mean(trt))
        delta = t_mean - c_mean
        w, t, l, p = exact_sign_p(ctrl, trt)
        ci_l, ci_u = bootstrap_ci(ctrl, trt)
        rows.append({
            'contrast': c_name,
            'control': c_ctrl,
            'treatment': c_trt,
            'ctrl_mean': c_mean,
            'trt_mean': t_mean,
            'delta': delta,
            'ci_lower': ci_l,
            'ci_upper': ci_u,
            'wtl': f"{w}/{t}/{l}",
            'p_raw': p,
        })
    # Apply Holm if M=5
    if len(rows) == 5:
        # Sort by p_raw ascending
        sorted_indices = sorted(range(5), key=lambda i: rows[i]['p_raw'])
        alpha = 0.05
        for rank, idx in enumerate(sorted_indices, start=1):
            m_factor = 5 - rank + 1
            holm_thresh = alpha / m_factor
            rows[idx]['holm_rank'] = rank
            rows[idx]['holm_thresh'] = holm_thresh
            rows[idx]['holm_sig'] = rows[idx]['p_raw'] <= holm_thresh
    return rows

print("--- 1. Retrieval (Clean-40) ---")
ret_dict = {'V0': v0_ret_40, 'V0h': v0h_ret_40, 'Vrel': vrel_ret_40}
for r in run_contrasts(ret_dict, 'Object_Recall@10'):
    print(r)

print("\n--- 2. Primary Generator (Clean-40) ---")
prim_dict = {'LLM-only': prim_llm_40, 'V0': prim_v0_40, 'V0h': prim_v0h_40, 'Vrel': prim_vrel_40}
prim_rows = run_contrasts(prim_dict, 'v2_alias')
for r in prim_rows:
    print(r)

print("\n--- 3. Secondary Generator (Clean-40) ---")
sec_dict = {'LLM-only': sec_llm_40, 'V0': sec_v0_40, 'V0h': sec_v0h_40, 'Vrel': sec_vrel_40}
sec_rows = run_contrasts(sec_dict, 'v2_alias')
for r in sec_rows:
    print(r)
