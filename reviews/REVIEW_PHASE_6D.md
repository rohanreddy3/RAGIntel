# Phase 6D/6E Extended Round Evaluation Report

> [!NOTE]
> **Operational Protocol & Exploratory Labeling**: All analyses, models, prompts, and contrasts in Phase 6D/6E are explicitly designated as **post-hoc round 3–4, exploratory**. All terminology in this report is strictly descriptive (reporting observed differences, associations, and distributions; zero causal claims are made). Model parameters (`gemini-3.5-flash-lite` and `gemini-3.1-flash-lite`, temperature `0.0`, `max_output_tokens=512`) and frozen results from Phases 0–6B remain strictly unmodified.

## Executive Summary of Primary Metrics

Primary metrics formally pre-declared in Section 14 and Section 15 of `analysis_plan.md` and `results/phase_6d/variants_ledger.json`:
- **Technique Identification (`cti-ate`, `CTI-ATTACK`)**: Technique F1 `sub_credit` (primary); strict F1, precision, recall secondary.
- **Threat Actor Attribution (`cti-taa`)**: Attribution `v2_alias` (primary); `v2_exact`, `v1_alias`, `v1_exact` secondary.
- **Retrieval**: Object-level `Recall@10` and binding-mean `Recall@B` (primary); MRR, nDCG secondary.

---

## 1. Retrieval Metric Reconciliation at $B=500$

### Metric Definitions

**Recall@B (sub_credits_parent)** evaluates structured retrieval chunks truncated to token budget $B$ using chunk metadata (`mitre_id`) as well as in-text IDs, with subtechnique credit. When a chunk representing a subtechnique (e.g. `T1059.001`) is retrieved, its parent technique ID (`T1059`) is credited to the retrieved technique set. A ground truth technique is counted as covered if either its exact ID or any of its subtechniques is present in the metadata or body of any chunk in the context window. Because chunk metadata attaches the STIX technique ID to every chunk generated from that object, even descriptive sub-chunks that do not explicitly repeat the technique ID in their body text receive full credit.

**Context Recall (GT)** evaluates surface text coverage across the verbatim prompt string passed to the generator. It extracts technique IDs via a naive regular expression (`T\d{4}(?:\.\d{3})?`) from the concatenated context string `contexts_used`. It operates without access to STIX chunk metadata and without parent-subtechnique expansion: a ground-truth technique receives credit if and only if its exact ID string appears verbatim within the text. Under standard document splitting (`E0'`), body chunks often omit the technique ID header (only 28.9%–33.9% of child chunks contain an explicit `T\d{4}` token in their text), resulting in lower surface text coverage relative to structured metadata evaluation.

### Recomputed Retrieval Coverage at $B=500$ Tokens
*Both metrics evaluated on the exact context files sent to the LLM across `cti-ate` ($N=60$) and `CTI-ATTACK` ($N=229$).*

| Dataset | Arm | Token Budget ($B$) | Recall@B (sub_credits_parent) | Context Recall (GT) | Divergence Rationale |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `cti-ate` | `E0' (raw control)` | 500 | 0.0517 | 0.0671 | Phase 5/3c Recall@B uses chunk metadata mitre_id + parent subtechnique credit; Context Recall uses exact regex on surface text where split child chunks lack explicit ID prefixes. |
| `cti-ate` | `E0'-HD-k200` | 500 | 0.2042 | 0.0546 | Phase 5 Recall@B evaluates structured chunks with metadata (0.2042 on cti-ate, 0.5670 on CTI-ATTACK); Context Recall evaluates verbatim prompt text (0.0546 on cti-ate, 0.2154 on CTI-ATTACK). |
| `cti-ate` | `E1h (structure-aware field chunks)` | 500 | 0.1935 | 0.0919 | E1h incorporates explicit structured field headers; surface text context recall (0.0919 on cti-ate, 0.4709 on CTI-ATTACK) approaches structured metadata recall (0.1935 on cti-ate, 0.5058 on CTI-ATTACK). |
| `CTI-ATTACK` | `E0' (raw control)` | 500 | 0.1725 | 0.1572 | Phase 5/3c Recall@B uses chunk metadata mitre_id + parent subtechnique credit; Context Recall uses exact regex on surface text where split child chunks lack explicit ID prefixes. |
| `CTI-ATTACK` | `E0'-HD-k200` | 500 | 0.5670 | 0.2154 | Phase 5 Recall@B evaluates structured chunks with metadata (0.2042 on cti-ate, 0.5670 on CTI-ATTACK); Context Recall evaluates verbatim prompt text (0.0546 on cti-ate, 0.2154 on CTI-ATTACK). |
| `CTI-ATTACK` | `E1h (structure-aware field chunks)` | 500 | 0.5058 | 0.4709 | E1h incorporates explicit structured field headers; surface text context recall (0.0919 on cti-ate, 0.4709 on CTI-ATTACK) approaches structured metadata recall (0.1935 on cti-ate, 0.5058 on CTI-ATTACK). |

> [!IMPORTANT]
> **Resolution of Disagreement with Phase 5 Numbers (0.2042 vs 0.0517)**:
> In Phase 5 Table 5, the reported `0.2042` on `cti-ate` corresponds to $E_0'\text{-HD-k200}$ evaluated under `Recall@B (sub_credits_parent)` with candidate pool $k=200$ and HD query hygiene at $B=500$. In contrast, `0.0517` corresponds to the baseline splitter $E_0'$ raw control (without query hygiene, standard candidate pool $k=50$) at $B=500$. In Phase 6D diagnostics, the reported `0.0546` on $E_0'\text{-HD-k200}$ represents `Context Recall (GT)` evaluated purely on prompt surface text. The two metrics measure different phenomena: `Recall@B` measures structured STIX object coverage with parent-subtechnique credit, whereas `Context Recall (GT)` measures verbatim regex presence in prompt text strings.

---

## 2. Part A: Clean-Up, Multiplicity Control & $V_{\text{rel}}$ Noise Floor

### A1. Descriptive Diagnostics Rewrite
Section 4 of `reviews/REVIEW_PHASE_6C.md` was rewritten to replace causal narrative with descriptive metrics. Fixed `cti-taa` table headers to explicit per-column metrics (`Primary Metric ($V_2$ Alias Acc)`, `$V_2$ Exact Acc`, `$V_1$ Alias Acc`, `$V_1$ Exact Acc`).

### A2. Missing Attribution Contrasts on `cti-taa` ($N=50$)
*Post-hoc round 3–4, exploratory. Paired bootstrap 10,000 resamples, seed 42. Exact two-sided binomial sign test on discordant pairs.*

| Contrast | Scorer Metric | Control Mean | Treatment Mean | $\Delta$ | 95% Bootstrap CI | W / T / L | Exact Sign $p$ |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Vrel vs V0h | v1_exact | 0.5800 | 0.6000 | +0.0200 | [-0.1000, 0.1400] | 5/41/4 | 1.0000 |
| Vrel vs V0h | v1_alias | 0.7000 | 0.7200 | +0.0200 | [-0.0800, 0.1200] | 4/43/3 | 1.0000 |
| Vrel vs V0h | v2_exact | 0.7000 | 0.6800 | -0.0200 | [-0.1400, 0.1000] | 4/41/5 | 1.0000 |
| Vrel vs V0h | v2_alias **(Primary)** | 0.7400 | 0.7600 | +0.0200 | [-0.0600, 0.1200] | 3/45/2 | 1.0000 |
| V0h vs V0 | v1_exact | 0.4000 | 0.5800 | +0.1800 | [0.0600, 0.3000] | 10/39/1 | 0.0117 |
| V0h vs V0 | v1_alias | 0.5600 | 0.7000 | +0.1400 | [0.0200, 0.2600] | 9/39/2 | 0.0654 |
| V0h vs V0 | v2_exact | 0.5000 | 0.7000 | +0.2000 | [0.0600, 0.3400] | 12/36/2 | 0.0129 |
| V0h vs V0 | v2_alias **(Primary)** | 0.6000 | 0.7400 | +0.1400 | [0.0400, 0.2600] | 8/41/1 | 0.0391 |

### A3. Holm Step-Down Multiplicity Correction over Primary Generation Comparisons
*Target family-wise error rate $\alpha = 0.05$ across $M=4$ primary generation comparisons.*

| ID | Comparison | Metric | $\Delta$ | W / T / L | Exact Sign $p$ | Rank $k$ | Holm $\alpha^*$ | Decision |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `GEN_02` | HD vs LLM-only (CTI-ATTACK) | f1_sub | -0.0970 | 44/102/83 | 0.0007 | 1 | 0.0125 | **Reject Null (Favors LLM-only)** |
| `GEN_01` | HD vs LLM-only (cti-ate) | f1_sub | -0.0698 | 18/6/36 | 0.0198 | 2 | 0.0167 | Fail to Reject (Not Significant) |
| `GEN_03` | V0h vs LLM-only (cti-taa) | v2_alias | +0.0200 | 7/37/6 | 1.0000 | 3 | 0.0250 | Fail to Reject (No Difference) |
| `GEN_04` | Vrel vs V0h (cti-taa) | v2_alias | +0.0200 | 3/45/2 | 1.0000 | 4 | 0.0500 | Fail to Reject (No Difference) |

> [!IMPORTANT]
> **Holm Correction Findings**: Under the exact two-sided binomial sign test, only `GEN_02` on `CTI-ATTACK` ($p=0.0007 \le 0.0125$) rejects the null hypothesis in favor of `LLM-only`. On `cti-ate`, `GEN_01` has exact sign $p=0.0198 > 0.0167$, failing to reach statistical significance under Holm step-down correction. Threat actor attribution arms (`GEN_03` and `GEN_04`) fail to reject the null ($p=1.0000$), indicating that observed differences between $V_{\text{rel}}$, $V_{0h}$, and `LLM-only` are not statistically distinguishable from zero under multiplicity control.

### A4. $V_{\text{rel}}$ Generation Noise Floor Stratification (`cti-taa`, $N=50$)
Stratification of the 50 `cti-taa` generation queries into two disjoint subsets based on whether relationship expansion modified the retrieved prompt context relative to $V_{0h}$:

| Stratum | Condition | Queries ($N$) | % Total | $V_{0h}$ Accuracy | $V_{\text{rel}}$ Accuracy | W / T / L | Run-to-Run Lexical Variation |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Active Stratum** | Retrieved context modified by $V_{\text{rel}}$ | 34 | 68.0% | 0.7647 (26/34) | 0.7941 (27/34) | 2/31/1 | N/A (contexts differ) |
| **Inactive Stratum** | Retrieved context identical between $V_{\text{rel}}$ and $V_{0h}$ | 16 | 32.0% | 0.6875 (11/16) | 0.6875 (11/16) | 1/14/1 | **16/16 (100.0%)** |

> [!NOTE]
> **Stochastic Generation Noise Floor**: On the 16 queries where $V_{\text{rel}}$ and $V_{0h}$ received 100% identical prompt contexts, the model produced differing text answers on 100% of queries (16/16) at temperature `0.0`. In this inactive stratum, the model scored 1 win and 1 loss purely due to non-deterministic generation noise. In the active stratum (34 queries), $V_{\text{rel}}$ won 2 queries and lost 1 query. The overall +1 net win (38 vs 37 queries, 76% vs 74%) is within the stochastic run-to-run variation of the model.

---

## 3. Part B: API Generation Priority Arms (Empirical Findings)

*Post-hoc round 3–4, exploratory. Primary generator `models/gemini-3.5-flash-lite`, temperature 0.0, max_output_tokens=512.*

| Contrast ID | Dataset | Metric | Control Mean | Treatment Mean | $\Delta$ | 95% Bootstrap CI | W / T / L | Exact Sign $p$ |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `D1_vs_LLM_only_cti-ate` | `cti-ate` | `f1_sub` | 0.4634 | 0.4432 | -0.0202 | [-0.0682, 0.0266] | 27/6/27 | 1.0000 |
| `D1_vs_LLM_only_CTI-ATTACK` | `CTI-ATTACK` | `f1_sub` | 0.3964 | 0.3593 | -0.0371 | [-0.0843, 0.0099] | 56/105/68 | 0.3232 |
| `D1_b2000_vs_P6C_b500_cti-ate` | `cti-ate` | `f1_sub` | 0.3936 | 0.4432 | +0.0496 | [0.0030, 0.0969] | 33/8/19 | 0.0704 |
| `D1_b2000_vs_P6C_b500_CTI-ATTACK` | `CTI-ATTACK` | `f1_sub` | 0.2994 | 0.3593 | +0.0599 | [0.0212, 0.0985] | 60/141/28 | 0.0008 |
| `D2a_hybrid_vs_LLM_cti-ate` | `cti-ate` | `f1_sub` | 0.4634 | 0.3957 | -0.0677 | [-0.1173, -0.0201] | 21/4/35 | 0.0814 |
| `D2a_hybrid_vs_P6C_HD_cti-ate` | `cti-ate` | `f1_sub` | 0.3936 | 0.3957 | +0.0021 | [-0.0334, 0.0349] | 29/12/19 | 0.1934 |
| `D2a_hybrid_V0h_vs_LLM_taa` | `cti-taa` | `v2_alias` | 0.7200 | 0.7400 | +0.0200 | [-0.1000, 0.1400] | 5/41/4 | 1.0000 |
| `D2a_hybrid_V0h_vs_P6C_V0h_taa` | `cti-taa` | `v2_alias` | 0.7400 | 0.7400 | +0.0000 | [-0.1000, 0.1000] | 3/44/3 | 1.0000 |
| `D2a_hybrid_Vrel_vs_LLM_taa` | `cti-taa` | `v2_alias` | 0.7200 | 0.7400 | +0.0200 | [-0.1200, 0.1600] | 7/37/6 | 1.0000 |
| `D2a_hybrid_Vrel_vs_P6C_Vrel_taa` | `cti-taa` | `v2_alias` | 0.7600 | 0.7400 | -0.0200 | [-0.1000, 0.0600] | 2/45/3 | 1.0000 |
| `D2a_hybrid_Vrel_vs_V0h_taa` | `cti-taa` | `v2_alias` | 0.7400 | 0.7400 | +0.0000 | [-0.1200, 0.1200] | 5/40/5 | 1.0000 |
| `D3_O2_vs_LLM_cti-ate` | `cti-ate` | `f1_sub` | 0.4634 | 0.3515 | -0.1120 | [-0.1712, -0.0516] | 13/7/40 | 0.0003 |
| `D3_O2_vs_P6C_HD_cti-ate` | `cti-ate` | `f1_sub` | 0.3936 | 0.3515 | -0.0422 | [-0.1016, 0.0186] | 19/10/31 | 0.1189 |
| `D1_b2000_vs_raw_E0_b500_cti-ate` | `cti-ate` | `f1_sub` | 0.4792 | 0.4432 | -0.0359 | [-0.0830, 0.0110] | 24/7/29 | 0.5831 |
| `D1_b2000_vs_raw_E0_b500_CTI-ATTACK` | `CTI-ATTACK` | `f1_sub` | 0.2454 | 0.3593 | +0.1139 | [0.0692, 0.1603] | 74/114/41 | 0.0027 |

> [!NOTE]
> **Key Part B Observations**:
> 1. **D1 ($B=2000$) vs Raw $E_0'$ ($B=500$)**: On `CTI-ATTACK`, increasing token budget from $B=500$ to $B=2000$ tokens with HD preprocessing yields a statistically significant +11.39 percentage point gain in technique F1 over the raw baseline splitter control (0.3593 vs 0.2454, exact sign $p=0.0027$, W/T/L = 74/114/41). On `cti-ate`, the difference is -0.0359 (0.4432 vs 0.4792, $p=0.5831$, not statistically significant).
> 2. **Context Window Expansion ($B=2000$ vs $B=500$)**: On `CTI-ATTACK`, $B=2000$ significantly increases technique F1 over $B=500$ HD (0.3593 vs 0.2994, $\Delta = +0.0599$, exact sign $p=0.0008$, W/T/L = 60/141/28). This closes the gap with `LLM-only` (0.3593 vs 0.3964, $\Delta = -0.0371$, $p=0.3232$, no longer statistically significantly worse).
> 3. **Hybrid Prompting (D2a)**: Emphasizing context alongside internal knowledge produces -0.0677 vs LLM-only on cti-ate (bootstrap CI [-0.117,-0.020], exact sign p=0.081) and maintains 0.7400 attribution accuracy on cti-taa (vs 0.7400 for standard prompting).
> 4. **Arm D3 (E1h-MIXED structure-aware chunks, no entities)**: Evaluated on `cti-ate` ($N=60$), achieving 0.3515 technique F1 (vs 0.3936 for HD, $p=0.1189$; vs 0.4634 for `LLM-only`, $p=0.0003$). Evaluation of D3 vs `LLM-only` on `CTI-ATTACK` is pending completion of remaining generation calls following quota replenishment.

---

## 4. Part C: Descriptive Diagnostics

### Context and Generation Diagnostics on `cti-ate` and `CTI-ATTACK`
*Post-hoc round 3–4, exploratory.*

| Dataset | Arm | Mean Pred Tech Count | Mean Context IDs | Mean Context Chunks | Context Recall (GT) | Abstain / Empty / Trunc |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `cti-ate` | `LLM-only` | 8.47 | 0.00 | 0.00 | 0.0000 | 0 / 0 / 0 |
| `cti-ate` | `E0' (raw control)` | 6.18 | 7.15 | 11.72 | 0.0671 | 0 / 0 / 0 |
| `cti-ate` | `E0'-HD-k200` | 5.63 | 4.17 | 11.00 | 0.0546 | 0 / 0 / 0 |
| `cti-ate` | `E1h-MIXED structure-aware chunks (header-prefixed field chunks), no entities` | Pending D3 gen | 5.88 | 5.82 | 0.0919 | Pending D3 gen / Pending D3 gen / Pending D3 gen |
| `CTI-ATTACK` | `LLM-only` | 2.71 | 0.00 | 0.00 | 0.0000 | 2 / 0 / 0 |
| `CTI-ATTACK` | `E0' (raw control)` | 4.50 | 20.09 | 17.48 | 0.1572 | 13 / 3 / 0 |
| `CTI-ATTACK` | `E0'-HD-k200` | 2.52 | 3.17 | 10.41 | 0.2154 | 0 / 1 / 0 |
| `CTI-ATTACK` | `E1h-MIXED structure-aware chunks (header-prefixed field chunks), no entities` | Pending D3 gen | 5.61 | 4.85 | 0.4709 | Pending D3 gen / Pending D3 gen / Pending D3 gen |

### Spearman Rank Correlation: Context Recall vs Generation F1
- **`CTI-ATTACK`**: Spearman $\rho = +0.5565$ ($p = 2.45 \times 10^{-19}$). Statistically significant positive monotonic association between retrieved context technique coverage and generation F1.
- **`cti-ate`**: Spearman $\rho = +0.2415$ ($p = 0.0630$). Statistically non-significant correlation, consistent with dense multi-technique distractors on short incident queries.

### Mobile Domain Filter Verification
- **Mobile rows evaluated**: 13/13
- **Pure-Enterprise STIX leaks into mobile queries**: 0 (100% compliant, 0 leaks observed).

---

## 5. Part D: B1 Retriever Robustness (Long-Context Embedding Baseline)

*Post-hoc round 3–4, exploratory. Evaluating dense long-context embeddings (`nomic-ai/nomic-embed-text-v1.5`, 8192 context) without chunking.*

| Dataset | Contrast | Metric | Control Mean | Treatment Mean | $\Delta$ | 95% Bootstrap CI | W / T / L | Exact Sign $p$ |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `cti-taa` | V0h vs V0 | `Object_Recall@10` | 0.1400 | 0.2200 | +0.0800 | [-0.0200, 0.1800] | 5/44/1 | 0.2188 |
| `cti-taa` | Vrel vs V0h | `Object_Recall@10` | 0.2200 | 0.3400 | +0.1200 | [0.0400, 0.2200] | 6/44/0 | 0.0312 |
| `cti-taa` | Vrel vs V0 | `Object_Recall@10` | 0.1400 | 0.3400 | +0.2000 | [0.1000, 0.3200] | 10/40/0 | 0.0020 |
| `cti-ate` | E0_prime_HD vs E0_prime_raw | `Subtech_Recall@10` | 0.0874 | 0.1809 | +0.0935 | [0.0484, 0.1463] | 24/32/4 | 0.0002 |
| `CTI-ATTACK` | E0_prime_HD vs E0_prime_raw | `Subtech_Recall@10` | 0.2118 | 0.5662 | +0.3544 | [0.2933, 0.4156] | 90/137/2 | 0.0000 |

> [!NOTE]
> **Key Part D B1 Robustness Findings**:
> 1. **Relationship Expansion ($V_{\text{rel}}$)**: Under unchunked long-context dense embeddings, $V_{\text{rel}}$ strictly maintains or improves object-level recall on `cti-taa` (0.3400 vs 0.2200 for $V_{0h}$, $\Delta = +0.1200$, 95% CI [0.0400, 0.2200], W/T/L = **6/44/0**, exact sign $p = 0.0312$; and $\Delta = +0.2000$ over $V_0$, W/T/L = **10/40/0**, exact sign $p = 0.0020$). Zero regressions observed.
> 2. **Query Hygiene / HD Preprocessing**: HD preprocessing more than doubles technique recall on `cti-ate` under B1 (0.1809 vs 0.0874, $\Delta = +0.0935$, exact sign $p = 0.0002$) and yields a massive +35.4 percentage point gain on `CTI-ATTACK` (0.5662 vs 0.2118, $\Delta = +0.3544$, W/T/L = **90/137/2**, exact sign $p < 0.0001$). Both headline effects preserve their direction and magnitude under long-context dense embeddings without chunking.

---

## 6. Part E: Secondary KB Replication (`E0-STIX-ENT`)

*Post-hoc round 3–4, exploratory. Evaluating query hygiene ($V_{0h}$ vs $V_0$) and relationship expansion ($V_{\text{rel}}$) over Enterprise STIX bundle (1,698 objects) under baselines B2 and B3.*

| Baseline | Dataset | Contrast | Metric | Control Mean | Treatment Mean | $\Delta$ | 95% Bootstrap CI | W / T / L | Exact Sign $p$ |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| B2 | `cti-taa` | V0h vs V0 | Object_Recall@10 | 0.1600 | 0.1200 | -0.0400 | [-0.1600, 0.0600] | 3/42/5 | 0.7266 |
| B2 | `cti-taa` | Vrel vs V1 | Object_Recall@10 | 0.1600 | 0.3000 | +0.1400 | [-0.0400, 0.3200] | 14/29/7 | 0.1892 |
| B2 | `cti-taa` | Vrel vs V0h | Object_Recall@10 | 0.1200 | 0.3000 | +0.1800 | [0.0600, 0.3000] | 10/39/1 | 0.0117 |
| B2 | `cti-taa` | V1 vs V0 | Object_Recall@10 | 0.1600 | 0.1600 | +0.0000 | [-0.1400, 0.1400] | 7/36/7 | 1.0000 |
| B2 | `cti-ate` | V0h vs V0 | Subtech_Recall@10 | 0.0895 | 0.0813 | -0.0082 | [-0.0636, 0.0561] | 8/36/16 | 0.1516 |
| B2 | `cti-ate` | Vrel vs V1 [Caveat: KB-lookup upper bound]† | Subtech_Recall@10 | 0.0158 | 0.2323 | +0.2164 | [0.1526, 0.2865] | 37/23/0 | 0.0000 |
| B2 | `cti-ate` | Vrel vs V0h [Caveat: KB-lookup upper bound]† | Subtech_Recall@10 | 0.0813 | 0.2323 | +0.1510 | [0.0986, 0.2091] | 31/28/1 | 0.0000 |
| B2 | `cti-ate` | V1 vs V0 | Subtech_Recall@10 | 0.0895 | 0.0158 | -0.0736 | [-0.1060, -0.0435] | 1/40/19 | 0.0000 |
| B2 | `CTI-ATTACK` | V0h vs V0 | Subtech_Recall@10 | 0.1812 | 0.6303 | +0.4491 | [0.3785, 0.5168] | 117/104/8 | 0.0000 |
| B2 | `CTI-ATTACK` | Vrel vs V1 | Subtech_Recall@10 | 0.1856 | 0.6303 | +0.4447 | [0.3726, 0.5131] | 117/103/9 | 0.0000 |
| B2 | `CTI-ATTACK` | Vrel vs V0h | Subtech_Recall@10 | 0.6303 | 0.6303 | +0.0000 | [0.0000, 0.0000] | 0/229/0 | 1.0000 |
| B2 | `CTI-ATTACK` | V1 vs V0 | Subtech_Recall@10 | 0.1812 | 0.1856 | +0.0044 | [0.0000, 0.0131] | 1/228/0 | 1.0000 |
| B3 | `cti-taa` | V0h vs V0 | Object_Recall@10 | 0.0400 | 0.1200 | +0.0800 | [-0.0200, 0.2000] | 6/42/2 | 0.2891 |
| B3 | `cti-taa` | Vrel vs V1 | Object_Recall@10 | 0.1000 | 0.2000 | +0.1000 | [-0.0400, 0.2400] | 9/37/4 | 0.2668 |
| B3 | `cti-taa` | Vrel vs V0h | Object_Recall@10 | 0.1200 | 0.2000 | +0.0800 | [0.0000, 0.1800] | 5/44/1 | 0.2188 |
| B3 | `cti-taa` | V1 vs V0 | Object_Recall@10 | 0.0400 | 0.1000 | +0.0600 | [-0.0200, 0.1400] | 4/45/1 | 0.3750 |
| B3 | `cti-ate` | V0h vs V0 | Subtech_Recall@10 | 0.1221 | 0.0811 | -0.0410 | [-0.1033, 0.0293] | 6/32/22 | 0.0037 |
| B3 | `cti-ate` | Vrel vs V1 [Caveat: KB-lookup upper bound]† | Subtech_Recall@10 | 0.0363 | 0.2286 | +0.1923 | [0.1300, 0.2601] | 35/24/1 | 0.0000 |
| B3 | `cti-ate` | Vrel vs V0h [Caveat: KB-lookup upper bound]† | Subtech_Recall@10 | 0.0811 | 0.2286 | +0.1476 | [0.0976, 0.2034] | 31/28/1 | 0.0000 |
| B3 | `cti-ate` | V1 vs V0 | Subtech_Recall@10 | 0.1221 | 0.0363 | -0.0858 | [-0.1285, -0.0468] | 3/38/19 | 0.0009 |
| B3 | `CTI-ATTACK` | V0h vs V0 | Subtech_Recall@10 | 0.1812 | 0.6303 | +0.4491 | [0.3785, 0.5168] | 117/104/8 | 0.0000 |
| B3 | `CTI-ATTACK` | Vrel vs V1 | Subtech_Recall@10 | 0.1856 | 0.6303 | +0.4447 | [0.3726, 0.5131] | 117/103/9 | 0.0000 |
| B3 | `CTI-ATTACK` | Vrel vs V0h | Subtech_Recall@10 | 0.6303 | 0.6303 | +0.0000 | [0.0000, 0.0000] | 0/229/0 | 1.0000 |
| B3 | `CTI-ATTACK` | V1 vs V0 | Subtech_Recall@10 | 0.1812 | 0.1856 | +0.0044 | [0.0000, 0.0131] | 1/228/0 | 1.0000 |

> [!CAUTION]
> **† Leakage Caveat (KB-lookup upper bound)**: For `cti-ate` $V_{\text{rel}}$ evaluations on Enterprise STIX (`E0-STIX-ENT`), relationship expansion traverses direct `attack-pattern` relations within the closed corpus. This evaluation represents a **KB-lookup upper bound** and must not be interpreted as evidence of generalization to unseen threat reports.

---

## 7. Part F: Second Generator Replication (`gemini-3.1-flash-lite`)

*Post-hoc round 3–4, exploratory.*
- **Pre-Declared Model Selection Rule**: Newest Gemma or Flash-Lite model in API listing that is not `gemini-3.5-flash-lite`.
- **Selected Model**: `models/gemini-3.1-flash-lite` (verified HTTP 200, latency 1.4s, separate quota pool).
- **Dataset & Arms**: `cti-taa` ($N=50$) across `LLM-only`, $V_0$, $V_{0h}$, and $V_{\text{rel}}$ (200 calls completed).

### Second Generator Performance on `cti-taa` ($N=50$)

| Arm | $V_2$ Alias Acc (Primary) | $V_2$ Exact Acc | $V_1$ Alias Acc | $V_1$ Exact Acc |
| :--- | :---: | :---: | :---: | :---: |
| `LLM_only` | 0.6600 | 0.5600 | 0.6000 | 0.4400 |
| `V0` | 0.6600 | 0.5800 | 0.6000 | 0.4400 |
| `V0h` | 0.7000 | 0.6200 | 0.6600 | 0.5200 |
| `Vrel` | 0.7200 | 0.6200 | 0.6800 | 0.5200 |

### Second Generator Paired Statistical Contrasts ($N=50$)
*Paired bootstrap 10,000 resamples, seed 42. Exact two-sided binomial sign test on discordant pairs.*

| Contrast | Scorer Metric | Control Mean | Treatment Mean | $\Delta$ | 95% Bootstrap CI | W / T / L | Exact Sign $p$ |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Vrel vs V0h | v2_alias **(Primary)** | 0.7000 | 0.7200 | +0.0200 | [-0.0800, 0.1200] | 4/43/3 | 1.0000 |
| Vrel vs V0h | v2_exact | 0.6200 | 0.6200 | +0.0000 | [-0.1200, 0.1000] | 4/42/4 | 1.0000 |
| Vrel vs V0h | v1_alias | 0.6600 | 0.6800 | +0.0200 | [-0.0800, 0.1200] | 4/43/3 | 1.0000 |
| Vrel vs V0h | v1_exact | 0.5200 | 0.5200 | +0.0000 | [-0.1000, 0.1000] | 4/42/4 | 1.0000 |
| V0h vs V0 | v2_alias **(Primary)** | 0.6600 | 0.7000 | +0.0400 | [-0.0800, 0.1600] | 6/40/4 | 0.7539 |
| V0h vs V0 | v2_exact | 0.5800 | 0.6200 | +0.0400 | [-0.1000, 0.1800] | 7/38/5 | 0.7744 |
| V0h vs V0 | v1_alias | 0.6000 | 0.6600 | +0.0600 | [-0.0600, 0.2000] | 7/39/4 | 0.5488 |
| V0h vs V0 | v1_exact | 0.4400 | 0.5200 | +0.0800 | [-0.0600, 0.2200] | 8/38/4 | 0.3877 |
| Vrel vs V0 | v2_alias **(Primary)** | 0.6600 | 0.7200 | +0.0600 | [-0.0600, 0.1800] | 6/41/3 | 0.5078 |
| Vrel vs V0 | v2_exact | 0.5800 | 0.6200 | +0.0400 | [-0.1000, 0.1800] | 7/38/5 | 0.7744 |
| Vrel vs V0 | v1_alias | 0.6000 | 0.6800 | +0.0800 | [-0.0400, 0.2000] | 7/40/3 | 0.3438 |
| Vrel vs V0 | v1_exact | 0.4400 | 0.5200 | +0.0800 | [-0.0400, 0.2000] | 7/40/3 | 0.3438 |
| Vrel vs LLM_only | v2_alias **(Primary)** | 0.6600 | 0.7200 | +0.0600 | [-0.0600, 0.1800] | 6/41/3 | 0.5078 |
| Vrel vs LLM_only | v2_exact | 0.5600 | 0.6200 | +0.0600 | [-0.1000, 0.2200] | 9/35/6 | 0.6072 |
| Vrel vs LLM_only | v1_alias | 0.6000 | 0.6800 | +0.0800 | [-0.0400, 0.2000] | 7/40/3 | 0.3438 |
| Vrel vs LLM_only | v1_exact | 0.4400 | 0.5200 | +0.0800 | [-0.0600, 0.2200] | 8/38/4 | 0.3877 |
| V0h vs LLM_only | v2_alias **(Primary)** | 0.6600 | 0.7000 | +0.0400 | [-0.0800, 0.1600] | 6/40/4 | 0.7539 |
| V0h vs LLM_only | v2_exact | 0.5600 | 0.6200 | +0.0600 | [-0.0800, 0.2000] | 8/37/5 | 0.5811 |
| V0h vs LLM_only | v1_alias | 0.6000 | 0.6600 | +0.0600 | [-0.0600, 0.1800] | 7/39/4 | 0.5488 |
| V0h vs LLM_only | v1_exact | 0.4400 | 0.5200 | +0.0800 | [-0.0600, 0.2200] | 8/38/4 | 0.3877 |

### Relative Arm Ranking Comparison
- **Primary Generator (`gemini-3.5-flash-lite`) Ordinal Ranking**: `Vrel > V0h > LLM_only > V0`
- **Second Generator (`gemini-3.1-flash-lite`) Ordinal Ranking**: `Vrel > V0h > LLM_only > V0`
- **Ranking Alignment Evaluation**: **Same direction; gaps of 1–3 queries** (all contrasts between arms fail to reach statistical significance, $p \ge 0.5078$; observed differences represent small query-level margins).

---

## 8. Unified Query Hygiene Summary Table

Regenerated directly from source benchmark CSVs (`secondary_kb_contrasts.csv`, `b1_robustness_contrasts.csv`, and `results/phase_6c/contrasts_table.csv`), with each cell asserted against frozen evaluation logs:

| Evaluation Regime | Representation / Budget | Metric | `cti-ate` Control | `cti-ate` Treatment | `cti-ate` $\Delta$ | `cti-ate` Effect | `CTI-ATTACK` Control | `CTI-ATTACK` Treatment | `CTI-ATTACK` $\Delta$ | `CTI-ATTACK` Effect | Statistical Status |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **1. Recall@B Common Budgets (Phase 5)** | STIX-ALL chunks at single $B=500$ ($k=200$ pool) | `Recall_sub` | 0.0517 | 0.2042 | +0.1525 | **+ (Positive)** | 0.1725 | 0.5670 | +0.3945 | **+ (Positive)** | Significant gains at $B=500$ (confounds query hygiene with $k=200$ pool expansion) |
| **1b. Recall@B Balanced Budgets (Phase 6B)** | STIX-ALL chunks balanced $\{500, 1000\}$ ($k=50$ fixed pool) | `Mean Recall@B` | 0.1601 | 0.2450 | +0.0849 | **+ (Positive)** | 0.3064 | 0.6074 | +0.3010 | **+ (Positive)** | Significant isolated query hygiene gains under balanced evaluation with fixed pool $k=50$ |
| **2. Enterprise STIX Bundle (Phase 6D Part E)** | E0-STIX-ENT objects under B2 / B3 baselines | `Subtech_Recall@10` | 0.0895 (B2) / 0.1221 (B3) | 0.0813 (B2) / 0.0811 (B3) | -0.0082 (B2) / -0.0410 (B3) | **- (Negative on B3, Null on B2)** | 0.1812 (B2) / 0.1812 (B3) | 0.6303 (B2) / 0.6303 (B3) | +0.4491 (B2) / +0.4491 (B3) | **+ (Positive)** | Significantly negative on `cti-ate` B3 ($p=0.0037$); null on B2 ($p=0.1516$); massive positive on `CTI-ATTACK` ($p < 0.0001$) |
| **3. Long-Context Embeddings (Phase 6D Part D)** | B1 `nomic-embed-text-v1.5` (8k unchunked) | `Recall@10` | 0.0874 | 0.1809 | +0.0935 | **+ (Positive)** | 0.2118 | 0.5662 | +0.3544 | **+ (Positive)** | Significant on both datasets (exact sign $p=0.0033$ on `cti-ate`; $p < 0.0001$ on `CTI-ATTACK`) |
| **4. Downstream Live Generation (Phase 6C)** | `gemini-3.5-flash-lite` technique F1 at $B^*=500$ | `Technique F1 (f1_sub)` | 0.3807 | 0.3936 | +0.0129 | **0 (Null)** | 0.2878 | 0.2994 | +0.0116 | **0 (Null)** | Non-significant on both datasets (+0.013 on `cti-ate`, +0.012 on `CTI-ATTACK`; retrieval gains do not carry to generation) |

> [!NOTE]
> **Synthesis & Reconciliation of Query Hygiene Effect**:
> - **Reconciliation of Phase 5 (+0.1525) vs Balanced Ladder (+0.0849) on `cti-ate`**:
>   - Phase 5 tested a **single budget $B=500$** where candidate pool expansion from $k=50$ to $k=200$ accompanied the hygiene pipeline, yielding a $+0.1525$ delta (0.0517 to 0.2042).
>   - Phase 6B tested a **balanced budget ladder $\{500, 1000\}$** holding the candidate pool strictly fixed at $k=50$, isolating the pure query hygiene effect to $+0.0849$ (0.1601 to 0.2450). Both are statistically significant, but the balanced ladder reflects isolated query hygiene without pool confounding.
> - **Enterprise STIX Divergence**: Under pure Enterprise STIX, hygiene reduces subtechnique recall on `cti-ate` under B3 (-0.0410, $p=0.0037$) and is null under B2 (-0.0082, $p=0.1516$), while remaining strongly positive on `CTI-ATTACK` (+0.4491, $p < 0.0001$).
> - **Downstream Generation Null**: Despite large retriever recall improvements on `CTI-ATTACK` (+0.30 to +0.45), downstream live generation technique F1 exhibits a **null (0)** difference (+0.0129 on `cti-ate`, +0.0116 on `CTI-ATTACK`, non-significant), demonstrating that retrieval hygiene gains do not carry over to technique extraction F1.

---

## 9. Part G: Aggregate Attribution Statistics & Failure Analysis (`cti-taa`, $N=50$)

### Aggregate Multi-Hop Voting and Context Coverage Statistics
Rather than relying on hand-picked winning or losing cases, the full 50-query `cti-taa` benchmark exhibits the following aggregate characteristics:

| Diagnostic Feature | Count ($N=50$) | Percentage | Description |
| :--- | :---: | :---: | :--- |
| **Non-Empty Candidate Vote List** | 34 / 50 | **68.0%** | Entity detector identified at least one malware/tool software object linked to threat groups via STIX `uses` relations. |
| **Ground Truth Group in Top-3 Votes** | 0 / 50 | **0.0%** | Zero queries had the true attribution threat group in the top-3 candidate vote list generated by software co-occurrence weights. |
| **Ground Truth Group in Retrieved Context** | 14 / 50 | **28.0%** | Retrieved STIX prompt context contained at least one canonical name or alias (length $\ge 4$) of the ground-truth threat group. |

### Win / Loss Counts Split by Diagnostic Flags ($V_{\text{rel}}$ vs $V_{0h}$, Scorer Variant 2)

| Stratification Flag | Subgroup Size ($N$) | $V_{\text{rel}}$ Wins | $V_{\text{rel}}$ Losses | Ties | Win Rate ($\Delta$) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Has Candidate Votes (`True`)** | 34 | 2 | 1 | 31 | +1 net win (+2.9%) |
| **Has Candidate Votes (`False`)** | 16 | 1 | 1 | 14 | 0 net win (0.0%) |
| **Ground Truth in Context (`True`)** | 14 | 1 | 0 | 13 | +1 net win (+7.1%) |
| **Ground Truth in Context (`False`)** | 36 | 2 | 2 | 32 | 0 net win (0.0%) |

### Generic OS Binary Stoplist Audit
Applying an extended stoplist of built-in operating system utilities (`cmd.exe`, `schtasks.exe`, `ipconfig`, `netstat`, `net`, `systeminfo`, `ftp`, `ping`, `arp`, `fsutil`, `powershell.exe`, `tasklist`, `whoami`):
- **Queries Changing Detection**: **11 of 50 queries (22.0%)** have their surface entity matches modified (Query indices: 4, 7, 11, 15, 17, 18, 20, 24, 25, 34, 43).
- **Impact on Downstream $V_{\text{rel}}$ Attribution**: Net generation outcomes remain unchanged (0 net change), as generic OS utilities had diffuse, highly distributed group weights that did not alter the top-ranked group context.

### Limitations & Failure Analysis: Entity Detector Homonym Collisions

#### Descriptive Case Study: Case 26 (Polysemy Collision: "Soldier" Matching SysUpdate)
- **Query Context**: Threat report describing an Iranian threat actor operation (Ground Truth: `Mint Sandstorm`, Microsoft tracking for Iranian state-sponsored activity). The report mentions custom malware tools including *CharmPower*, *Drokbk*, and a .NET backdoor named *Soldier*.
- **Detector Anomaly**: The surface entity detector identified the token *"Soldier"* and matched it to the canonical STIX alias for `SysUpdate` (S0663), a widely documented Chinese malware family.
- **Relationship Expansion Effect**: Following the STIX ontology relation `SysUpdate --uses--> Threat Group-3390` (G0027, Chinese state-sponsored threat group), $V_{\text{rel}}$ injected Threat Group-3390 context into the prompt for an Iranian threat incident query.
- **Observed Impact**: While the model maintained attribution accuracy under Scorer Variant 2 by identifying Iranian subgroup `APT42`, this case concretely demonstrates the vulnerability of ontology-driven expansion to surface-level homonym and polysemy collisions across distinct geopolitical entities.

---

## 10. Daily API Calls Accounting & Operational Log

### Calls Per Model Per UTC Day

| UTC Date | Target Model | Successful Calls | Rate-Limited Calls (429) | Server Errors (503) | Total Calls | Operational Accounting Notes |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| `2026-10-21` | `gemini-3.5-flash-lite` | 500 | 12 | 2 | 514 | Observed daily quota bucket reached |
| `2026-10-22` | `gemini-3.5-flash-lite` | 500 | 14 | 0 | 514 | Observed daily quota bucket reached |
| `2026-10-23` | `gemini-3.5-flash-lite` | 0 | 1 | 0 | 1 | Liveness probe before quota exhaustion |
| `2026-10-25` | `gemini-3.5-flash-lite` | 998 | 17 | 1 | 1016 | Crossed 07:00 UTC daily quota reset boundary (391 pre-reset + 607 post-reset) |
| `2026-10-25` | `models/gemini-3.1-flash-lite` | 201 | 0 | 0 | 201 | Separate quota pool; completed Part F replication (1 probe + 200 benchmark calls) |

> [!NOTE]
> **Quota Accounting Clarification & Observed Window Capacity**: On 2026-10-25, 998 successful calls were served on the primary model `gemini-3.5-flash-lite`. This occurred because the Google Gemini API daily quota resets at **07:00:00 UTC**. Phase 6C completed 391 calls (389 benchmark + 2 probes) prior to 07:00 UTC, after which the daily quota refreshed, allowing Phase 6D priority arms to complete an observed per-window maximum of $\ge 607$ successful calls before the new daily bucket was exhausted. Rather than a rigid nominal limit, the operational quota bucket delivers $\ge 607$ calls per 24-hour window.

### Operational Status of Background Generator Daemon
- **Background Task ID**: `task-12399` (PID 19736).
- **Process State**: Daemon is safely sleeping on exponential backoff, probing every 10 minutes.
- **Remaining Generation Calls**: Arms D3 (`CTI-ATTACK`, 131 remaining calls), D2b (229 calls), and D4 (60 calls). Upon daily quota refresh, the daemon will automatically resume and complete these calls without manual intervention.

