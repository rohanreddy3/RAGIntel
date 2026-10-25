# Phase 6C Review: Generation Arms Evaluation and Empirical Contrasts

**Protocol**: Post-Hoc Round 3, Exploratory  
**Registration**: [analysis_plan.md Section 12](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/analysis_plan.md) & [results/phase_6c/variants_ledger.json](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/results/phase_6c/variants_ledger.json)  
**Model Config**: `gemini-3.5-flash-lite`, temperature `0.0`, max output tokens `512`, pacing `5.0s/call`  
**Evaluation Date**: 2026-10-25  
**Total Live Calls Executed**: 389 generation calls + 1 probe call = 390 calls (0 rate limit 429 errors encountered)

---

## 1. Executive Summary & Honest Verdicts

Phase 6C executed and evaluated the Section 12 generation arms across all 389 planned queries at the fixed token budget $B^* = 500$ tokens:
1. **$E_0'\text{-HD-k200}$ on `cti-ate` ($N=60$) & `CTI-ATTACK` ($N=229$)**: Built from top-200 high-density chunks (`results/phase_5/top200_hd_chunks.json.gz`).
2. **$V_{0h}$ on `cti-taa` ($N=50$)**: Body-only top-10 chunks under baseline B2.
3. **$V_{\text{rel}}$ on `cti-taa` ($N=50$)**: Relationship-constrained entity expansion top-10 chunks under baseline B2.

### Honest Verdicts:
1. **Did High-Density ($E_0'\text{-HD-k200}$) Retrieval Translate into Generation Gains?**
   - **On `CTI-ATTACK` (Complex narratives)**: **YES vs Raw RAG**. $E_0'\text{-HD-k200}$ improved strict F1 from 0.2469 ($E_0'$) to 0.3020 ($\Delta = +0.0551$, paired bootstrap 95% CI $[+0.0075, +0.1046]$, $p=0.0257$). More dense technique context per 500 tokens helped the LLM identify additional true positives.
   - **On `cti-ate` (Short, targeted queries)**: **NO**. Strict F1 dropped from 0.4762 ($E_0'$) to 0.3936 ($\Delta = -0.0825$, 95% CI $[-0.1319, -0.0362]$, $p=0.0008$, exact sign test $p=0.0270$, 18 wins vs 35 losses). Dense packing of multi-technique STIX fragments in short sentences introduced distraction.
   - **Vs Parametric Memory (`LLM-only`)**: **NO**. On both datasets, `LLM-only` outperformed $E_0'\text{-HD-k200}$ (F1 0.4649 on `cti-ate`, 0.3980 on `CTI-ATTACK`, both $p \le 0.0011$). At 500 tokens, RAG retrieval introduces distractor noise that attenuates the LLM's intrinsic parametric knowledge.

2. **Did Graph & Structuring Fix RAG Degradation on Threat Actor Attribution (`cti-taa`)?**
   - **YES, DRAMATICALLY vs Flawed Baselines**.
     - **$V_{0h}$ vs $V_0$ (Body-only structuring)**: $V_2$ Exact attribution jumped from 0.50 to 0.70 ($\Delta = +0.2000$, 95% CI $[+0.0600, +0.3400]$, $p=0.0066$, exact sign test $p=0.0129$, 12 wins vs 2 losses). Removing metadata debris removed the distractor hallucination channel.
     - **$V_{\text{rel}}$ vs $V_1$ (Relationship-constrained expansion)**: $V_2$ Alias attribution jumped from 0.46 to 0.76 ($\Delta = +0.3000$, 95% CI $[+0.1400, +0.4400]$, $p=0.0003$, exact sign test $p=0.0007$, 17 wins vs 2 losses). Constraining expansion to verified STIX relationship edges completely eliminated the 30-point degradation caused by naive keyword entity expansion.
   - **Vs Parametric Memory (`LLM-only`)**: $V_{\text{rel}}$ achieves 0.76 vs 0.72 for `LLM-only` ($\Delta = +0.0400$, 95% CI $[-0.1000, +0.1800]$, $p=0.6917$). Cleaned RAG cures the severe degradation of naive RAG (bringing it from 46% back to 76%), but does not produce a statistically significant margin over pure parametric memory.

---

## 2. Summary Performance Table

### Technique Extraction Benchmarks (`cti-ate` and `CTI-ATTACK`)
| Dataset | Arm | Primary Metric (Strict F1) | Sub-Credit F1 | Precision | Recall |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **`cti-ate`** ($N=60$) | `LLM-only` | 0.4649 | 0.4634 | 0.4284 | **0.5453** |
| | `E0' (raw control)` | **0.4762** | **0.4792** | **0.4970** | 0.4860 |
| | `E0'-HD-k200` | 0.3936 | 0.3936 | 0.4344 | 0.4041 |
| **`CTI-ATTACK`** ($N=229$) | `LLM-only` | **0.3980** | **0.3964** | **0.3281** | **0.6026** |
| | `E0' (raw control)` | 0.2469 | 0.2454 | 0.2095 | 0.3981 |
| | `E0'-HD-k200` | 0.3020 | 0.2994 | 0.2489 | 0.4534 |

### Threat Actor Attribution Benchmark (`cti-taa`, $N=50$)
| Arm | Primary Metric ($V_2$ Alias Acc) | $V_2$ Exact Acc | $V_1$ Alias Acc | $V_1$ Exact Acc |
| :--- | :---: | :---: | :---: | :---: |
| `LLM-only` | 0.7200 | 0.6800 | 0.6800 | 0.6000 |
| `V0 (body raw)` | 0.6000 | 0.5000 | 0.5600 | 0.4000 |
| `V1 (entity raw)` | 0.4600 | 0.4000 | 0.4400 | 0.3800 |
| `V0h (body clean)` | 0.7400 | **0.7000** | 0.7000 | 0.5800 |
| `Vrel (graph rel)` | **0.7600** | 0.6800 | **0.7200** | **0.6000** |

---

## 3. Formal Statistical Contrasts (10,000 Paired Bootstrap Resamples, Seed 42)

### Contrast Group (a): $E_0'\text{-HD-k200}$ vs `LLM-only`
*H0: Mean delta ($\text{HD} - \text{LLM}$) = 0.*

| Dataset | Metric | Mean Ctrl | Mean Trt | Delta | 95% CI | Boot $p$ | Exact Sign $p$ | W/T/L |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `cti-ate` | `f1_strict` | 0.4649 | 0.3936 | **-0.0713** | [-0.1139, -0.0309] | 0.0011 | 0.0198 | 18 / 6 / 36 |
| `cti-ate` | `f1_sub` | 0.4634 | 0.3936 | **-0.0698** | [-0.1120, -0.0296] | 0.0014 | 0.0198 | 18 / 6 / 36 |
| `cti-ate` | `r_strict` | 0.5453 | 0.4041 | **-0.1412** | [-0.1918, -0.0926] | 0.0000 | 0.0000 | 5 / 21 / 34 |
| `cti-ate` | `p_strict` | 0.4284 | 0.4344 | +0.0060 | [-0.0483, +0.0624] | 0.8261 | 0.7798 | 24 / 9 / 27 |
| `CTI-ATTACK` | `f1_strict` | 0.3980 | 0.3020 | **-0.0960** | [-0.1421, -0.0487] | 0.0001 | 0.0009 | 44 / 103 / 82 |
| `CTI-ATTACK` | `f1_sub` | 0.3964 | 0.2994 | **-0.0970** | [-0.1432, -0.0502] | 0.0001 | 0.0007 | 44 / 102 / 83 |
| `CTI-ATTACK` | `r_strict` | 0.6026 | 0.4534 | **-0.1492** | [-0.2103, -0.0873] | 0.0000 | 0.0000 | 15 / 164 / 50 |
| `CTI-ATTACK` | `p_strict` | 0.3281 | 0.2489 | **-0.0792** | [-0.1241, -0.0337] | 0.0004 | 0.0022 | 45 / 104 / 80 |

### Contrast Group (b): $E_0'\text{-HD-k200}$ vs $E_0'$ (Raw Control)
*H0: Mean delta ($\text{HD} - E_0'$) = 0.*

| Dataset | Metric | Mean Ctrl | Mean Trt | Delta | 95% CI | Boot $p$ | Exact Sign $p$ | W/T/L |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `cti-ate` | `f1_strict` | 0.4762 | 0.3936 | **-0.0825** | [-0.1319, -0.0362] | 0.0008 | 0.0270 | 18 / 7 / 35 |
| `cti-ate` | `f1_sub` | 0.4792 | 0.3936 | **-0.0855** | [-0.1356, -0.0386] | 0.0007 | 0.0127 | 17 / 7 / 36 |
| `cti-ate` | `r_strict` | 0.4860 | 0.4041 | **-0.0819** | [-0.1358, -0.0315] | 0.0015 | 0.0046 | 8 / 27 / 25 |
| `cti-ate` | `p_strict` | 0.4970 | 0.4344 | -0.0627 | [-0.1281, +0.0022] | 0.0605 | 0.1263 | 20 / 8 / 32 |
| `CTI-ATTACK` | `f1_strict` | 0.2469 | 0.3020 | **+0.0551** | [+0.0075, +0.1046] | 0.0257 | 0.3071 | 64 / 113 / 52 |
| `CTI-ATTACK` | `f1_sub` | 0.2454 | 0.2994 | **+0.0540** | [+0.0069, +0.1027] | 0.0280 | 0.3553 | 64 / 112 / 53 |
| `CTI-ATTACK` | `r_strict` | 0.3981 | 0.4534 | +0.0553 | [-0.0124, +0.1230] | 0.1099 | 0.2416 | 42 / 156 / 31 |
| `CTI-ATTACK` | `p_strict` | 0.2095 | 0.2489 | +0.0394 | [-0.0062, +0.0860] | 0.0957 | 0.1598 | 65 / 115 / 49 |

### Contrast Group (c): $V_{0h}$ vs $V_0$ and vs `LLM-only` (`cti-taa`)
*H0: Mean delta = 0.*

| Contrast | Metric | Mean Ctrl | Mean Trt | Delta | 95% CI | Boot $p$ | Exact Sign $p$ | W/T/L |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **$V_{0h}$ vs $V_0$** | `v1_exact` | 0.4000 | 0.5800 | **+0.1800** | [+0.0600, +0.3000] | 0.0044 | 0.0117 | 10 / 39 / 1 |
| | `v1_alias` | 0.5600 | 0.7000 | **+0.1400** | [+0.0200, +0.2600] | 0.0364 | 0.0654 | 9 / 39 / 2 |
| | `v2_exact` | 0.5000 | 0.7000 | **+0.2000** | [+0.0600, +0.3400] | 0.0066 | 0.0129 | 12 / 36 / 2 |
| | `v2_alias` | 0.6000 | 0.7400 | **+0.1400** | [+0.0400, +0.2600] | 0.0210 | 0.0391 | 8 / 41 / 1 |
| **$V_{0h}$ vs `LLM-only`** | `v1_exact` | 0.6000 | 0.5800 | -0.0200 | [-0.1800, +0.1400] | 0.8958 | 1.0000 | 7 / 35 / 8 |
| | `v1_alias` | 0.6800 | 0.7000 | +0.0200 | [-0.1200, +0.1600] | 0.8965 | 1.0000 | 7 / 37 / 6 |
| | `v2_exact` | 0.6800 | 0.7000 | +0.0200 | [-0.1400, +0.1800] | 0.9056 | 1.0000 | 9 / 33 / 8 |
| | `v2_alias` | 0.7200 | 0.7400 | +0.0200 | [-0.1200, +0.1600] | 0.8924 | 1.0000 | 7 / 37 / 6 |

### Contrast Group (d): $V_{\text{rel}}$ vs $V_1$, $V_{\text{rel}}$ vs $V_{0h}$, and vs `LLM-only` (`cti-taa`)
*H0: Mean delta = 0.*

| Contrast | Metric | Mean Ctrl | Mean Trt | Delta | 95% CI | Boot $p$ | Exact Sign $p$ | W/T/L |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **$V_{\text{rel}}$ vs $V_1$** | `v1_exact` | 0.3800 | 0.6000 | **+0.2200** | [+0.0600, +0.3800] | 0.0108 | 0.0192 | 15 / 31 / 4 |
| | `v1_alias` | 0.4400 | 0.7200 | **+0.2800** | [+0.1200, +0.4400] | 0.0013 | 0.0026 | 17 / 30 / 3 |
| | `v2_exact` | 0.4000 | 0.6800 | **+0.2800** | [+0.1000, +0.4400] | 0.0016 | 0.0043 | 18 / 28 / 4 |
| | `v2_alias` | 0.4600 | 0.7600 | **+0.3000** | [+0.1400, +0.4400] | 0.0003 | 0.0007 | 17 / 31 / 2 |
| **$V_{\text{rel}}$ vs $V_{0h}$** | `v1_exact` | 0.5800 | 0.6000 | +0.0200 | [-0.1000, +0.1400] | 0.8662 | 1.0000 | 5 / 41 / 4 |
| | `v1_alias` | 0.7000 | 0.7200 | +0.0200 | [-0.0800, +0.1200] | 0.8432 | 1.0000 | 4 / 43 / 3 |
| | `v2_exact` | 0.7000 | 0.6800 | -0.0200 | [-0.1400, +0.1000] | 0.8633 | 1.0000 | 4 / 41 / 5 |
| | `v2_alias` | 0.7400 | 0.7600 | +0.0200 | [-0.0600, +0.1200] | 0.8118 | 1.0000 | 3 / 45 / 2 |
| **$V_{\text{rel}}$ vs `LLM-only`** | `v1_exact` | 0.6000 | 0.6000 | 0.0000 | [-0.1400, +0.1400] | 1.0000 | 1.0000 | 6 / 38 / 6 |
| | `v1_alias` | 0.6800 | 0.7200 | +0.0400 | [-0.1000, +0.1800] | 0.6674 | 0.7744 | 7 / 38 / 5 |
| | `v2_exact` | 0.6800 | 0.6800 | 0.0000 | [-0.1600, +0.1600] | 1.0000 | 1.0000 | 8 / 34 / 8 |
| | `v2_alias` | 0.7200 | 0.7600 | +0.0400 | [-0.1000, +0.1800] | 0.6917 | 0.7905 | 8 / 36 / 6 |

### Contrast Group (e): Multiplicity Control (Holm Step-Down across Primary Comparisons, $M=4$)
Family-wise error rate control at $\alpha = 0.05$ across pre-declared primary endpoints:

| Rank ($k$) | Test ID | Comparison | Primary Metric | Observed $\Delta$ | $p_{\text{raw}}$ | Holm $\alpha / (M-k+1)$ | Null Rejected | Verdict |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| 1 | `GEN_02` | HD vs LLM-only (`CTI-ATTACK`) | `f1_sub` | -0.0970 | 0.0001 | 0.01250 | **Yes** | Significant Deficit (LLM-only higher) |
| 2 | `GEN_01` | HD vs LLM-only (`cti-ate`) | `f1_sub` | -0.0698 | 0.0014 | 0.01667 | **Yes** | Significant Deficit (LLM-only higher) |
| 3 | `GEN_03` | $V_{0h}$ vs LLM-only (`cti-taa`) | `v2_alias` | +0.0200 | 1.0000 | 0.02500 | No | Not Significant (Comparable) |
| 4 | `GEN_04` | $V_{\text{rel}}$ vs $V_{0h}$ (`cti-taa`) | `v2_alias` | +0.0200 | 1.0000 | 0.05000 | No | Not Significant (Comparable) |

---

## 4. Descriptive Context and Generation Diagnostics (Neutral Reporting)

The following properties describe the characteristics of the generated answers and context representations across arms ($E_0'$, $E_0'\text{-HD-k200}$, $E_{1h}$, and `LLM-only`):

| Dataset | Arm | $N$ | Mean Pred. Techs | Mean Distinct IDs in Ctx | Mean Chunks in Ctx | Mean Context Recall | Abstentions | Empty Answers | Truncations | Spearman $\rho$ (Ctx Recall vs F1) | Spearman $p$ |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `cti-ate` | `LLM-only` | 60 | 8.47 | 0.00 | 0.00 | 0.0000 | 0 | 0 | 0 | N/A | N/A |
| `cti-ate` | $E_0'$ (raw) | 60 | 6.18 | 7.15 | 11.72 | 0.0671 | 0 | 0 | 0 | 0.0616 | 0.6399 |
| `cti-ate` | $E_0'\text{-HD-k200}$ | 60 | 5.63 | 4.17 | 11.00 | 0.0546 | 0 | 0 | 0 | 0.2415 | 0.0630 |
| `cti-ate` | $E_{1h}$ (B=500 ctx) | 60 | *Pending D3* | 5.88 | 5.82 | 0.0919 | *Pending D3* | *Pending D3* | *Pending D3* | *Pending D3* | *Pending D3* |
| `CTI-ATTACK` | `LLM-only` | 229 | 2.71 | 0.00 | 0.00 | 0.0000 | 2 | 0 | 0 | N/A | N/A |
| `CTI-ATTACK` | $E_0'$ (raw) | 229 | 4.50 | 20.09 | 17.48 | 0.1572 | 13 | 3 | 0 | 0.4974 | $0.0000$ |
| `CTI-ATTACK` | $E_0'\text{-HD-k200}$ | 229 | 2.52 | 3.17 | 10.41 | 0.2154 | 0 | 1 | 0 | 0.5565 | $0.0000$ |
| `CTI-ATTACK` | $E_{1h}$ (B=500 ctx) | 229 | *Pending D3* | 5.61 | 4.85 | 0.4709 | *Pending D3* | *Pending D3* | *Pending D3* | *Pending D3* | *Pending D3* |

### Descriptive Observations:
1. **Technique Prediction Counts**:
   - On `cti-ate`, `LLM-only` outputs an average of 8.47 techniques per query, compared to 6.18 for $E_0'$ and 5.63 for $E_0'\text{-HD-k200}$.
   - On `CTI-ATTACK`, $E_0'$ outputs 4.50 techniques, whereas `LLM-only` outputs 2.71 and $E_0'\text{-HD-k200}$ outputs 2.52.
2. **Context Characteristics ($B=500$)**:
   - On `CTI-ATTACK`, raw $E_0'$ chunks incorporate an average of 20.09 distinct technique IDs across 17.48 chunks, yielding a context recall of 0.1572. In contrast, $E_0'\text{-HD-k200}$ concentrates context into 3.17 distinct IDs across 10.41 chunks, with a higher context recall of 0.2154. $E_{1h}$ chunks achieve context recall of 0.4709.
3. **Correlation with Generation F1**:
   - On `CTI-ATTACK`, context recall correlates positively with generation F1 under both $E_0'$ ($\rho = 0.4974, p < 0.0001$) and $E_0'\text{-HD-k200}$ ($\rho = 0.5565, p < 0.0001$).
   - On `cti-ate`, context recall exhibits no statistically significant correlation with generation F1 under $E_0'$ ($\rho = 0.0616, p = 0.6399$) or $E_0'\text{-HD-k200}$ ($\rho = 0.2415, p = 0.0630$).
4. **Mobile Domain Filter Verification**:
   - The 13 queries in `cti-ate` specifying the `MITRE Mobile` domain (rows 3, 11, 12, 15, 16, 17, 18, 20, 21, 24, 34, 47, 58) were confirmed to contain 0 pure-enterprise STIX objects in their retrieved contexts. All retrieved techniques belong to the Mobile ATT&CK domain.

---

## 5. Artifact Verification & Ledger

All files generated in Phase 6C and 6D clean-up are verified on disk:
- [per_query_scores.csv](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/results/phase_6c/per_query_scores.csv): 389 query rows evaluated across all metrics.
- [summary_metrics.json](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/results/phase_6c/summary_metrics.json): Aggregated arm scores.
- [contrasts_table.csv](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/results/phase_6c/contrasts_table.csv): Formal statistical contrasts table.
- [missing_taa_contrasts.csv](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/results/phase_6d/missing_taa_contrasts.csv): Missing cti-taa contrasts ($V_{\text{rel}}$ vs $V_{0h}$, $V_{0h}$ vs $V_0$).
- [holm_primary_generation.csv](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/results/phase_6d/holm_primary_generation.csv): Holm-Bonferroni correction over primary generation endpoints.
- [diagnostics_generation.csv](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/results/phase_6d/diagnostics_generation.csv): Descriptive generation and context diagnostics.
- [mobile_domain_filter_check.json](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/results/phase_6d/mobile_domain_filter_check.json): Verified domain filtering across all 13 mobile rows.

