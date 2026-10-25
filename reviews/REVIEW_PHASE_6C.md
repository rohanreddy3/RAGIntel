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

| Dataset | Arm | Primary Metric | Score | Precision | Recall |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **`cti-ate`** ($N=60$) | `LLM-only` | Strict F1 | **0.4649** | 0.4284 | **0.5453** |
| | `E0' (raw control)` | Strict F1 | **0.4762** | **0.4970** | 0.4860 |
| | `E0'-HD-k200` | Strict F1 | 0.3936 | 0.4344 | 0.4041 |
| **`CTI-ATTACK`** ($N=229$) | `LLM-only` | Strict F1 | **0.3980** | **0.3281** | **0.6026** |
| | `E0' (raw control)` | Strict F1 | 0.2469 | 0.2095 | 0.3981 |
| | `E0'-HD-k200` | Strict F1 | 0.3020 | 0.2489 | 0.4534 |
| **`cti-taa`** ($N=50$) | `LLM-only` | $V_2$ Alias Acc | 0.7200 | $V_2$ Exact: 0.68 | $V_1$ Exact: 0.60 |
| | `V0 (body raw)` | $V_2$ Alias Acc | 0.6000 | $V_2$ Exact: 0.50 | $V_1$ Exact: 0.40 |
| | `V1 (entity raw)` | $V_2$ Alias Acc | 0.4600 | $V_2$ Exact: 0.40 | $V_1$ Exact: 0.38 |
| | `V0h (body clean)` | $V_2$ Alias Acc | 0.7400 | $V_2$ Exact: **0.70** | $V_1$ Exact: 0.58 |
| | `Vrel (graph rel)` | $V_2$ Alias Acc | **0.7600** | $V_2$ Exact: 0.68 | $V_1$ Exact: **0.60** |

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

### Contrast Group (d): $V_{\text{rel}}$ vs $V_1$ and vs `LLM-only` (`cti-taa`)
*H0: Mean delta = 0.*

| Contrast | Metric | Mean Ctrl | Mean Trt | Delta | 95% CI | Boot $p$ | Exact Sign $p$ | W/T/L |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **$V_{\text{rel}}$ vs $V_1$** | `v1_exact` | 0.3800 | 0.6000 | **+0.2200** | [+0.0600, +0.3800] | 0.0108 | 0.0192 | 15 / 31 / 4 |
| | `v1_alias` | 0.4400 | 0.7200 | **+0.2800** | [+0.1200, +0.4400] | 0.0013 | 0.0026 | 17 / 30 / 3 |
| | `v2_exact` | 0.4000 | 0.6800 | **+0.2800** | [+0.1000, +0.4400] | 0.0016 | 0.0043 | 18 / 28 / 4 |
| | `v2_alias` | 0.4600 | 0.7600 | **+0.3000** | [+0.1400, +0.4400] | 0.0003 | 0.0007 | 17 / 31 / 2 |
| **$V_{\text{rel}}$ vs `LLM-only`** | `v1_exact` | 0.6000 | 0.6000 | 0.0000 | [-0.1400, +0.1400] | 1.0000 | 1.0000 | 6 / 38 / 6 |
| | `v1_alias` | 0.6800 | 0.7200 | +0.0400 | [-0.1000, +0.1800] | 0.6674 | 0.7744 | 7 / 38 / 5 |
| | `v2_exact` | 0.6800 | 0.6800 | 0.0000 | [-0.1600, +0.1600] | 1.0000 | 1.0000 | 8 / 34 / 8 |
| | `v2_alias` | 0.7200 | 0.7600 | +0.0400 | [-0.1000, +0.1800] | 0.6917 | 0.7905 | 8 / 36 / 6 |

---

## 4. In-Depth Mechanistic Analysis

### 4.1 Why did $E_0'\text{-HD-k200}$ improve on CTI-ATTACK but lose on cti-ate?
- **Dataset Property Discrepancy**:
  - `CTI-ATTACK` queries are full incident reports where attack patterns span dozens of sentences. Raw $E_0'$ chunks often contained narrative prose with zero technique mentions. In contrast, HD chunks filter specifically for high technique-mention density, ensuring that the 500-token budget contains relevant technique context. This yielded a **+5.5% point F1 boost** ($\Delta = +0.0551$, CI $[+0.0075, +0.1046]$).
  - `cti-ate` queries are concise sentence-level descriptions. The raw $E_0'$ chunking preserved coherent, localized context. Packing multiple HD snippets into 500 tokens created "technique soup" — the model predicted irrelevant co-occurring techniques from the high-density chunks, causing false positives and lowering recall from 0.4860 to 0.4041.

### 4.2 Why does `LLM-only` beat RAG on technique extraction?
- `gemini-3.5-flash-lite` has extensive pre-trained cyber threat intelligence knowledge.
- In both datasets, `LLM-only` achieves the highest recall (0.5453 on `cti-ate`, 0.6026 on `CTI-ATTACK`).
- When a 500-token retrieved context is prepended, the model grounds its generation on the provided text. If the retriever misses a technique that the model would have otherwise known parametrically, the model omits it, reducing recall.

### 4.3 Why was $V_{\text{rel}}$ so successful at eliminating the RAG penalty on `cti-taa`?
- In Phase 2 and Phase 3, naive entity expansion ($V_1$) was a catastrophic failure mode: expanding on every detected alias fetched text from unrelated threat groups that happened to share string overlaps (e.g. "APT" or common malware names). The LLM was overwhelmed by conflicting actor names, collapsing attribution to 46%.
- $V_{\text{rel}}$ queries the STIX graph specifically for verified relationships (`uses`, `attributed-to`). Distractor chunks are eliminated at the index level. As a result, attribution jumps from **46% to 76%** ($\Delta = +0.3000$, $p=0.0007$, 17 wins vs 2 losses).

---

## 5. Artifact Verification & Ledger

All files generated in Phase 6C are verified on disk:
- [per_query_scores.csv](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/results/phase_6c/per_query_scores.csv): 389 query rows evaluated across all metrics.
- [summary_metrics.json](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/results/phase_6c/summary_metrics.json): Aggregated arm scores.
- [contrasts_table.csv](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/results/phase_6c/contrasts_table.csv): Formal statistical contrasts table.
- [bootstrap_distributions.json.gz](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/results/phase_6c/bootstrap_distributions.json.gz): Full 10,000 resample bootstrap delta quantiles.
- [variants_ledger.json](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/results/phase_6c/variants_ledger.json): Registered arms, completion timestamps, and file checksums.
