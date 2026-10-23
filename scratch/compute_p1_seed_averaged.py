import json
import numpy as np
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.retrieval_eval import compute_paired_bootstrap_ci

# 1. Load P1 checkpoint
with open(REPO_ROOT / "results" / "phase_2" / "p1_eval_checkpoint.json", "r", encoding="utf-8") as f:
    ckpt = json.load(f)

# V0, V1 arrays
b2_v0_rec = np.array([r["Recall@10"] for r in ckpt["E0-STIX-ALL_B2_V0_cti-taa"]], dtype=float)
b2_v0_mrr = np.array([r["MRR"] for r in ckpt["E0-STIX-ALL_B2_V0_cti-taa"]], dtype=float)
b2_v1_rec = np.array([r["Recall@10"] for r in ckpt["E0-STIX-ALL_B2_V1_cti-taa"]], dtype=float)
b2_v1_mrr = np.array([r["MRR"] for r in ckpt["E0-STIX-ALL_B2_V1_cti-taa"]], dtype=float)

b3_v0_rec = np.array([r["Recall@10"] for r in ckpt["E0-STIX-ALL_B3_V0_cti-taa"]], dtype=float)
b3_v0_mrr = np.array([r["MRR"] for r in ckpt["E0-STIX-ALL_B3_V0_cti-taa"]], dtype=float)
b3_v1_rec = np.array([r["Recall@10"] for r in ckpt["E0-STIX-ALL_B3_V1_cti-taa"]], dtype=float)
b3_v1_mrr = np.array([r["MRR"] for r in ckpt["E0-STIX-ALL_B3_V1_cti-taa"]], dtype=float)

# Seed 42 V3 arrays
b2_v3_s42_rec = np.array([r["Recall@10"] for r in ckpt["E0-STIX-ALL_B2_V3_cti-taa"]], dtype=float)
b2_v3_s42_mrr = np.array([r["MRR"] for r in ckpt["E0-STIX-ALL_B2_V3_cti-taa"]], dtype=float)
b3_v3_s42_rec = np.array([r["Recall@10"] for r in ckpt["E0-STIX-ALL_B3_V3_cti-taa"]], dtype=float)
b3_v3_s42_mrr = np.array([r["MRR"] for r in ckpt["E0-STIX-ALL_B3_V3_cti-taa"]], dtype=float)

# 2. Load B3 seeds 42-44
with open(REPO_ROOT / "results" / "phase_2" / "v3_seeds_b3_results.json", "r", encoding="utf-8") as f:
    v3_b3 = json.load(f)

# Average per-query across seeds 42, 43, 44 for B3
b3_per_query_rec = []
b3_per_query_mrr = []
for i in range(50):
    rec_vals = [v3_b3["seeds"][str(s)]["per_query"][i]["Recall@10"] for s in [42, 43, 44]]
    mrr_vals = [v3_b3["seeds"][str(s)]["per_query"][i]["MRR"] for s in [42, 43, 44]]
    b3_per_query_rec.append(np.mean(rec_vals))
    b3_per_query_mrr.append(np.mean(mrr_vals))

b3_v3_avg_rec = np.array(b3_per_query_rec, dtype=float)
b3_v3_avg_mrr = np.array(b3_per_query_mrr, dtype=float)

print(f"B3 V3 seed-avg: Recall@10 mean = {np.mean(b3_v3_avg_rec):.4f}, MRR mean = {np.mean(b3_v3_avg_mrr):.4f}")

# 3. For B2 V3: check if per-query files exist or construct from per_seed
# In v3_seeds_b2_results.json, seed-averaged mean is 0.2520, MRR is 0.0650
# Let's check if there are per-query files or if we can run B2 seeds 42-46
print("Testing B3 V1 vs V3 seed-avg:")
ci_b3_rec = compute_paired_bootstrap_ci(b3_v3_avg_rec, b3_v1_rec, n_resamples=10000, seed=42)
print("  Recall@10:", ci_b3_rec)
ci_b3_mrr = compute_paired_bootstrap_ci(b3_v3_avg_mrr, b3_v1_mrr, n_resamples=10000, seed=42)
print("  MRR:", ci_b3_mrr)

# Sensitivity with seed 42 only on B3:
ci_b3_s42_rec = compute_paired_bootstrap_ci(b3_v3_s42_rec, b3_v1_rec, n_resamples=10000, seed=42)
ci_b3_s42_mrr = compute_paired_bootstrap_ci(b3_v3_s42_mrr, b3_v1_mrr, n_resamples=10000, seed=42)
print("\nSensitivity B3 Seed 42 only:")
print("  Recall@10:", ci_b3_s42_rec)
print("  MRR:", ci_b3_s42_mrr)
