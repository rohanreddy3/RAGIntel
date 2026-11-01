# Results Guide: Map of Empirical Claims to Source Artifacts

This document maps every empirical claim ($C_1$ through $C_{10}$) reported in Table T3, `claims_master.csv`, and `RESULTS_MASTER.md` to its exact raw source files under `results/`, along with the underlying statistical properties, metrics, and scripts.

---

## Claims to Source File Mapping

### Claim C1: Balanced Ladder Retrieval Query Hygiene
- **Summary**: Balanced retrieval query hygiene improves Mean Recall@B across balanced budgets {500, 1000} with fixed pool $k=50$.
- **Metric**: `Mean Recall@B` across budgets $\{500, 1000\}$.
- **Datasets**: `cti-ate` ($N=60$) & `CTI-ATTACK` ($N=229$).
- **Control**: Raw ($E_0'$ raw, $k=50$). Mean: `0.1601` (ate), `0.3064` (att).
- **Treatment**: Hygiene ($E_0'$ body-only, $k=50$). Mean: `0.2450` (ate), `0.6074` (att).
- **Delta**: $\Delta = +0.0849$ (`cti-ate`), $\Delta = +0.3010$ (`CTI-ATTACK`).
- **Statistical Inferences**: CI, W/T/L, and $p$-values are labeled as *"from Phase 6B run; per-query data not archived; not re-derivable"*. Canonical point estimates are preserved.
- **Source Artifact**: `results/phase_6b/assets/table_ladder_common_budgets.csv`
- **Generating / Auditing Script**: `scripts/build_results_master.py`
- **Status Label**: **Robust**

---

### Claim C2: Enterprise STIX Baseline-Dependent Hygiene
- **Summary**: On Enterprise STIX (`E0-STIX-ENT`), the query hygiene effect is baseline-dependent on `cti-ate` and positive on `CTI-ATTACK`.
- **Metric**: `Subtech_Recall@10`.
- **Datasets**: `cti-ate` ($N=60$) under B3 and B2; `CTI-ATTACK` ($N=229$) under B2.
- **Control**: $E_0\text{-STIX-ENT}$ Raw ($V_0$). Means: `0.1221` (cti-ate B3), `0.0895` (cti-ate B2), `0.1812` (CTI-ATTACK B2).
- **Treatment**: $E_0\text{-STIX-ENT}$ Hygiene ($V_{0h}$). Means: `0.0811` (cti-ate B3), `0.0813` (cti-ate B2), `0.6303` (CTI-ATTACK B2).
- **Deltas**:
  - `cti-ate` B3: $\Delta = -0.0410$, 95% CI `[-0.1033, +0.0293]`, W/T/L `6/32/22`, exact sign $p = 0.0037$ (significant negative).
  - `cti-ate` B2: $\Delta = -0.0082$, 95% CI `[-0.0636, +0.0561]`, W/T/L `8/36/16`, exact sign $p = 0.1516$ (null).
  - `CTI-ATTACK` B2: $\Delta = +0.4491$, 95% CI `[+0.3785, +0.5168]`, W/T/L `117/104/8`, exact sign $p < 0.0001$ (massive positive).
- **Source Artifact**: `results/phase_6d/secondary_kb_contrasts.csv`
- **Generating / Auditing Script**: `scripts/run_phase6d_secondary_kb.py`
- **Status Label**: **Mixed**

---

### Claim C3: B1 Dense Long-Context Embedding Hygiene
- **Summary**: Long-context dense embeddings (Nomic v1.5) without chunking benefit substantially from query hygiene.
- **Metric**: `Recall@10` (`Subtech_Recall@10`).
- **Datasets**: `cti-ate` ($N=60$) & `CTI-ATTACK` ($N=229$).
- **Control**: B1 Raw Unchunked. Means: `0.1208` (ate), `0.1652` (att).
- **Treatment**: B1 Hygiene Unchunked. Means: `0.2144` (ate), `0.5196` (att).
- **Deltas**: $\Delta = +0.0935$ (`cti-ate`), $\Delta = +0.3544$ (`CTI-ATTACK`).
- **Confidence Intervals**: 95% CI `[+0.0484, +0.1463]` (ate), `[+0.2933, +0.4156]` (att).
- **Discordant Pairs (W/T/L)**: `24/32/4` (ate), `90/137/2` (att).
- **Exact Sign Tests**: $p = 0.0002$ (ate), $p < 0.0001$ (att).
- **Source Artifact**: `results/phase_6d/b1_robustness_contrasts.csv`
- **Generating / Auditing Script**: `scripts/run_phase6d_b1_robustness.py`
- **Status Label**: **Robust**

---

### Claim C4: Downstream Live Generation Hygiene (HD vs E0')
- **Summary**: Downstream generation hygiene (HD vs $E_0'$) hurts `cti-ate` (negative, significant) and is mixed on `CTI-ATTACK` (positive mean, CI excludes 0, sign test $p=0.355$). Confound note: control is $k=\text{all}$, treatment is $k=200$, so hygiene is confounded with candidate pool truncation.
- **Metric**: Technique F1 (`f1_sub`).
- **Datasets**: `cti-ate` ($N=60$) & `CTI-ATTACK` ($N=229$).
- **Control**: True Raw $E_0'$ ($B=500, k=\text{all}$). Means: `0.4792` (ate), `0.2454` (att).
- **Treatment**: HD ($B=500, k=200$). Means: `0.3936` (ate), `0.2994` (att).
- **Deltas**: $\Delta = -0.0855$ (ate), $\Delta = +0.0540$ (att).
- **Confidence Intervals**: 95% CI `[-0.1356, -0.0386]` (ate), `[+0.0069, +0.1027]` (att).
- **Discordant Pairs (W/T/L)**: `17/7/36` (ate), `64/112/53` (att).
- **Exact Sign Tests**: $p = 0.0127$ (ate, significant negative), $p = 0.3553$ (att, tie).
- **Source Artifacts**: `results/phase_6d/phase6g_corrections.json` + `results/phase_6c/contrasts_table.json`
- **Generating / Auditing Script**: `scripts/compute_phase6c_metrics.py`
- **Status Label**: **Mixed**

---

### Claim C5: Primary Generation Family (HD vs LLM-Only)
- **Summary**: Under pre-declared Holm correction ($M=4$), HD is significantly worse than zero-shot LLM-only on `CTI-ATTACK` ($p=0.0007 \le 0.0125$), and does not beat LLM-only on `cti-ate` ($p=0.0198 > 0.0167$).
- **Metric**: Technique F1 (`f1_sub`).
- **Comparisons**:
  - `GEN_02` (CTI-ATTACK): HD (`0.2994`) vs LLM-only (`0.3964`), $\Delta = -0.0970$, 95% CI `[-0.1432, -0.0502]`, W/T/L `44/102/83`, raw $p = 0.00068 \le 0.0125$ $\to$ **Statistically Significant Negative**.
  - `GEN_01` (cti-ate): HD (`0.3936`) vs LLM-only (`0.4634`), $\Delta = -0.0698$, 95% CI `[-0.1120, -0.0296]`, W/T/L `18/6/36`, raw $p = 0.01983 > 0.01667$ $\to$ **Not Significant under Holm**.
- **Source Artifacts**: `results/phase_6d/holm_primary_generation.json` + `results/phase_6c/contrasts_table.json`
- **Generating / Auditing Script**: `scripts/compute_phase6c_metrics.py`
- **Status Label**: **Robust (CTI-ATTACK) / Not Sig under Holm (cti-ate)**

---

### Claim C6: cti-taa Clean-40 Attribution & Vrel
- **Summary**: On `cti-taa` Clean-40, STIX relationship expansion ($V_{\text{rel}}$) recovers retrieval recall ($+0.2000, p=0.0078$), but downstream generation differences are null on both primary and secondary generators.
- **Metric**: Retrieval `Recall@10` / Generation `v2_alias`.
- **Dataset**: `cti-taa` Clean-40 ($N=40$).
- **Retrieval**: $V_{0h}$ (`0.1250`) $\to$ $V_{\text{rel}}$ (`0.3250`), $\Delta = +0.2000$, 95% CI `[+0.0750, +0.3250]`, W/T/L `8/32/0`, exact sign $p = 0.0078$.
- **Downstream Generation (Clean-40)**:
  - Primary Generator (`gemini-3.5-flash-lite`): LLM-only = `0.650`, $V_0$ = `0.525`, $V_{0h}$ = `0.675`, $V_{\text{rel}}$ = `0.700` (standard) / `0.675` (hybrid).
  - Secondary Generator (`gemini-3.1-flash-lite`): LLM-only = `0.575`, $V_0$ = `0.575`, $V_{0h}$ = `0.625`, $V_{\text{rel}}$ = `0.650`.
- **Source Artifact**: `results/phase_6d/phase6g_corrections.json (item8)`
- **Generating / Auditing Script**: `scripts/evaluate_missing_taa_contrasts.py`
- **Status Label**: **Exploratory (Retrieval Sig / Generation Null)**

---

### Claim C7: Ground-Truth Alias Leakage in cti-taa
- **Summary**: 20% of `cti-taa` queries (10 of 50) have adversary group aliases embedded directly within the query body text, producing 100% accuracy saturation across generators. Fisher's exact tests are descriptive and uncorrected.
- **Metric**: Query Leakage Share / Attribution Accuracy (`v2_alias`).
- **Dataset**: `cti-taa` ($N=50$: Clean-40 vs Leaked-10).
- **Leaked Subset Accuracy**: 10/10 correct (LLM-only, $V_{0h}$, $V_{\text{rel}}$), 9/10 ($V_0$).
- **Fisher's Exact Tests (Two-Sided, Uncorrected)**:
  - LLM-only: $p = 0.0445$
  - $V_0$: $p = 0.0366$
  - $V_{0h}$: $p = 0.0463$
  - $V_{\text{rel}}$: $p = 0.0920$
- **Source Artifact**: `results/phase_6d/gt_alias_leakage_audit.json`
- **Generating / Auditing Script**: `scripts/audit_row_alignment.py`
- **Status Label**: **Robust Benchmark Defect**

---

### Claim C8: Entity Detector Survival Filtering Precision
- **Summary**: Survival filtering purifies query entity detection precision from 74.0% to 93.9% real entity and 63.0% to 93.9% informative attribution precision.
- **Metric**: Real Entity / Informative Precision (Counts only; single annotator, AI-draft labels, recall unmeasured).
- **Sample**: 89 raw prompt body detections $\to$ 66 surviving matches (62 real & informative).
- **Precision Shifts**:
  - Real Entity Precision: $83.1\% \to 93.9\%$ ($+10.8$ percentage points).
  - Informative Attribution Precision: $70.8\% \to 93.9\%$ ($+23.2$ percentage points).
- **Source Artifact**: `results/phase_6d/phase6g_corrections.json (item6)`
- **Generating / Auditing Script**: `scripts/analyze_detector_precision.py`
- **Status Label**: **Exploratory Precision (Recall unmeasured, single annotator)**

---

### Claim C9: STIX Metadata-Credit Inflation Defect
- **Summary**: Chunk metadata tagging creates an artificial recall advantage over surface text-visible matching (+0.1496 on `cti-ate` / +0.3516 on `CTI-ATTACK`).
- **Metric**: `Recall@B` at $B=500$ tokens.
- **Datasets**: `cti-ate` ($N=60$) & `CTI-ATTACK` ($N=229$).
- **Discrepancy**:
  - `cti-ate`: Metadata-credit = `0.2042`, Text-visible = `0.0546`, Discrepancy Delta = `+0.1496`.
  - `CTI-ATTACK`: Metadata-credit = `0.5670`, Text-visible = `0.2154`, Discrepancy Delta = `+0.3516`.
- **Statistical Inferences**: Deterministic scoring difference between evaluation harnesses; no stochastic test applicable.
- **Source Artifact**: `results/phase_6d/metadata_credit_audit.json`
- **Generating / Auditing Script**: `scripts/audit_budget_binding.py`
- **Status Label**: **Robust Methodological Defect**

---

### Claim C10: Budget Expansion Scaling (B=500 -> B=2000)
- **Summary**: Budget expansion from $B=500$ to $B=2000$ shows statistically significant improvement on `CTI-ATTACK` ($p=0.0008$), but is marginal on `cti-ate` ($p=0.0704$), and the hybrid prompt arm (D4) is null.
- **Metric**: Technique F1 (`f1_sub`).
- **Datasets**: `cti-ate` ($N=60$) & `CTI-ATTACK` ($N=229$).
- **Control**: HD $B=500$ (`0.3936` ate, `0.2994` att).
- **Treatment**: D1 $B=2000$ (`0.4432` ate, `0.3593` att) / D4 Hybrid $B=2000$ (`0.4290` ate, `0.3348` att).
- **Deltas**:
  - D1 on `CTI-ATTACK`: $\Delta = +0.0599$, 95% CI `[+0.0212, +0.0985]`, W/T/L `60/141/28`, exact sign $p = 0.0008$ (significant).
  - D1 on `cti-ate`: $\Delta = +0.0496$, 95% CI `[+0.0030, +0.0969]`, W/T/L `33/8/19`, exact sign $p = 0.0704$ (not significant).
  - D4 on `cti-ate`: $\Delta = +0.0354$, exact sign $p = 0.6778$ (null).
- **Source Artifact**: `results/phase_6d/generation_contrasts.json`
- **Generating / Auditing Script**: `scripts/compute_phase6c_metrics.py`
- **Status Label**: **Exploratory**
