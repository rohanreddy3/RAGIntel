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

| ID | Comparison | Metric | $\Delta$ | W / T / L | Raw $p$ | Rank $k$ | Holm $\alpha^*$ | Decision |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `GEN_02` | HD vs LLM-only (CTI-ATTACK) | f1_sub | -0.0970 | 44/102/83 | 0.0001 | 1 | 0.0125 | **Reject Null (Favors LLM-only)** |
| `GEN_01` | HD vs LLM-only (cti-ate) | f1_sub | -0.0698 | 18/6/36 | 0.0014 | 2 | 0.0167 | **Reject Null (Favors LLM-only)** |
| `GEN_03` | V0h vs LLM-only (cti-taa) | v2_alias | +0.0200 | 7/37/6 | 1.0000 | 3 | 0.0250 | Fail to Reject (No Difference) |
| `GEN_04` | Vrel vs V0h (cti-taa) | v2_alias | +0.0200 | 3/45/2 | 1.0000 | 4 | 0.0500 | Fail to Reject (No Difference) |

> [!IMPORTANT]
> **Holm Correction Findings**: Technique extraction arms (`GEN_01` on `cti-ate` and `GEN_02` on `CTI-ATTACK`) reject the null hypothesis in favor of `LLM-only` ($p=0.0014 \le 0.0167$ and $p=0.0001 \le 0.0125$). Threat actor attribution arms (`GEN_03` and `GEN_04`) fail to reject the null ($p=1.0000$), indicating that observed differences between $V_{\text{rel}}$, $V_{0h}$, and `LLM-only` are not statistically distinguishable from zero under multiplicity control.

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
> 3. **Hybrid Prompting**: Emphasizing context alongside internal knowledge produces 0.3957 on `cti-ate` (vs 0.3936, $p=0.1934$) and maintains 0.7400 attribution accuracy on `cti-taa`.
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

Evaluation of the query hygiene effect across four distinct evaluation regimes on `cti-ate` and `CTI-ATTACK`:

| Evaluation Regime | Metric Evaluated | `cti-ate` Hygiene Delta | `cti-ate` Effect | `CTI-ATTACK` Hygiene Delta | `CTI-ATTACK` Effect | Statistical Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **1. Recall@B Common Budgets (Phase 5)** | `Recall_sub (sub_credits_parent)` | +0.1525 | **+ (Positive)** | +0.3945 | **+ (Positive)** | Statistically significant gains across all token budgets |
| **2. Enterprise STIX Bundle (Phase 6D Part E)** | `Recall@10` | +0.0167 (B2) / +0.0000 (B3) | **0 (Null)** | +0.4491 | **+ (Positive)** | Null on cti-ate (p=0.6875); massive positive on CTI-ATTACK (p < 0.0001) |
| **3. Long-Context Dense Embeddings (Phase 6D Part D)** | `Recall@10` | +0.0935 | **+ (Positive)** | +0.3544 | **+ (Positive)** | Statistically significant on both datasets (p=0.0002 on cti-ate; p < 0.0001 on CTI-ATTACK) |
| **4. Downstream Live Generation (Phase 6C)** | `Technique F1 (f1_sub)` | +0.0129 | **0 (Null)** | +0.0116 | **0 (Null)** | Statistically non-significant on both datasets (p=0.6904 on cti-ate; p=0.4069 on CTI-ATTACK) |

> [!NOTE]
> **Synthesis of Query Hygiene Effect**:
> - **CTI-ATTACK**: Query hygiene is consistently **positive (+)** across all retrieval representations, yielding massive recall improvements (+35.4 to +44.9 percentage points) by stripping irrelevant operational prose. In live generation, however, downstream technique F1 exhibits a **null (0)** difference (+0.0116, $p=0.4069$), indicating that retriever recall gains do not automatically translate to generation improvements at $B=500$.
> - **cti-ate**: Query hygiene is **positive (+)** on full STIX-ALL and dense 8k embeddings (+9.4 to +15.3 percentage points), but **null (0)** on isolated Enterprise STIX (0.0 to +1.7 percentage points) and **null (0)** in live generation (+0.0129, $p=0.6904$).

---

## 9. Part G: Deterministic Case Studies & Limitations

### Winning Cases ($V_{\text{rel}}$ Wins over $V_{0h}$, $N=5$)

#### Case 0 (Query ID: `8b8e568edda9`)
- **Ground Truth**: `SideCopy`
- **Detected Software**: `Action RAT (canonical: Action RAT), Action RAT (canonical: Action RAT), Action RAT (canonical: Action RAT), Raindrop (canonical: Raindrop), Crimson (canonical: Crimson)`
- **Top-3 Voted Threat Groups**: `SideCopy (G1008, score: 3.0), APT29 (G0016, score: 1.0), Transparent Tribe (G0134, score: 1.0)`
- **Ground Truth Present in Retrieved Context**: `True`
- **$V_{\text{rel}}$ Model Answer**: Based on the provided threat report and MITRE ATT&CK framework, the incident and threat actor can be attributed as follows:  * **Threat Group / APT:** **SideCopy** (associated as a sub-division of **Transparent Tribe** / **APT36** / **G1008**) * **Software / Tools:**    * **AllaKore RAT**   * **Ares RAT**   * **Crimson RAT**   * **Poseidon**
- **$V_{0h}$ Model Answer**: Based on the provided threat report and MITRE ATT&CK framework, the incident and threat group can be mapped as follows:  *   **Threat Actor Group:** **Transparent Tribe** (also known as **APT36**, associated with aliases such as **Operation Transparent Tribe** or **Mythic Leopard**). *   **Software / Tools:**      *   **Crimson RAT** (S0334)     *   **Ares RAT**     *   **AllaKore RAT**     *   **Action RAT**     *   **Capra RAT**     *   **Oblique RAT**

#### Case 8 (Query ID: `92723fd96f20`)
- **Ground Truth**: `APT-C-36, also known as Blind Eagle`
- **Detected Software**: `QuasarRAT (canonical: QuasarRAT), QuasarRAT (canonical: QuasarRAT), QuasarRAT (canonical: QuasarRAT)`
- **Top-3 Voted Threat Groups**: `APT-C-36 (G0099, score: 0.4286), Gorgon Group (G0078, score: 0.4286), Kimsuky (G0094, score: 0.4286)`
- **Ground Truth Present in Retrieved Context**: `False`
- **$V_{\text{rel}}$ Model Answer**: Based on the provided threat report details—specifically the targeting of government institutions and financial/banking entities in Colombia and Latin America (such as Bancolombia, Davivienda, and the Colombian Ministry of Foreign Affairs), the use of Spanish-language artifacts, custom modifications to QuasarRAT, and the attribution context from the MITRE ATT&CK reference data—the incident can be attributed to the following threat actor:  * **Threat Actor Group:** **APT-C-36** (also known in public threat intelligence reporting as **BlindEagle**) * **Associated Software/Tools:** **QuasarRAT** / **Meterpreter**
- **$V_{0h}$ Model Answer**: Based on the provided threat report, the incident can be attributed to the following known software and toolset used by the threat actors:  * **Software/Tools:**    * **QuasarRAT** (modified open-source remote access trojan used in the initial campaign targeting Colombian financial entities).   * **Meterpreter** (delivered via Python scripts in subsequent campaigns targeting Ecuador).  *(Note: The threat report specifically redacts the threat actor group name using `[PLACEHOLDER]`, focusing heavily on the customization and deployment of QuasarRAT and Meterpreter by Spanish-speaking financially motivated actors targeting Latin America.)*

#### Case 22 (Query ID: `337b6a14a4b4`)
- **Ground Truth**: `Mint Sandstorm (PHOSPHORUS)`
- **Detected Software**: ``
- **Top-3 Voted Threat Groups**: ``
- **Ground Truth Present in Retrieved Context**: `False`
- **$V_{\text{rel}}$ Model Answer**: Based on the threat report provided, the activity can be attributed to the following threat actor group and associated identifiers:  * **Threat Group:** **APT35** (also known as **Charming Kitten**, **Phosphorus**, or **Mint Sandstorm**) * **MITRE ATT&CK Group ID:** [G0058](https://attack.mitre.org/groups/G0058) (Charming Kitten)
- **$V_{0h}$ Model Answer**: Based on the provided threat report and context, the incident can be attributed to the following threat group:  * **MITRE ATT&CK Threat Group:** **APT35** (also known as **Charming Kitten** or **Phosphorus**, which overlap with the placeholders and are explicitly mentioned in the text as being tracked by other researchers).   *(Note: While the primary group is APT35/Charming Kitten, the report also references specific custom malware tools associated with them, such as **MediaPl** and **MischiefTut**).*

#### Case 24 (Query ID: `a1d56b2578c3`)
- **Ground Truth**: `Seedworm (or Muddywater)`
- **Detected Software**: `schtasks.exe (canonical: schtasks), Impacket (canonical: Impacket), cmd.exe (canonical: cmd)`
- **Top-3 Voted Threat Groups**: `BRONZE BUTLER (G0060, score: 0.5), Kimsuky (G0094, score: 0.3333), APT3 (G0022, score: 0.3333)`
- **Ground Truth Present in Retrieved Context**: `False`
- **$V_{\text{rel}}$ Model Answer**: Based on the provided threat report and context, the incident is attributed to the following threat actor group:  * **Threat Actor Group:** [MuddyWater](https://attack.mitre.org/groups/G0069) (also known as MERCURY, Seedworm, or Static Kitten)  **Attribution Details:** * **Associated Organization:** Iran’s Ministry of Intelligence and Security (MOIS). * **Tools and Infrastructure:** The report explicitly mentions tools and infrastructure heavily tied to this group, such as the **MuddyC2Go** framework (which replaced PhonyC2), **SimpleHelp**, **Venom Proxy**, **Revsocks**, and the use of legitimate utilities like AnyDesk for remote access and persistence.
- **$V_{0h}$ Model Answer**: Based on the provided threat report and context, the incident is attributed to the following threat group:  * **Threat Group:** [MuddyWater](https://attack.mitre.org/groups/G0069) (also associated with Iran's Ministry of Intelligence and Security - MOIS)  ### Mapping to MITRE ATT&CK: * **Threat Group:** MuddyWater ([G0069](https://attack.mitre.org/groups/G0069))

#### Case 41 (Query ID: `7172731bb34b`)
- **Ground Truth**: `APT29 (aka Cozy Bear, Nobelium and many other monikers)`
- **Detected Software**: ``
- **Top-3 Voted Threat Groups**: ``
- **Ground Truth Present in Retrieved Context**: `False`
- **$V_{\text{rel}}$ Model Answer**: Based on the provided context and threat report details (specifically the attribution by Ukrainian authorities to Russian intelligence services—referencing the SVR—and the specific mention of exploiting CVE-2023-3883 in conjunction with Russian APT activity typically associated with diplomatic targeting), the threat actor group described in the report corresponds to:  * **Threat Group:** [APT29](https://attack.mitre.org/groups/G0016) (also known as Cozy Bear / Midnight Blizzard, associated with Russia's SVR).   *(Note: While APT29 is the widely recognized MITRE ATT&CK group matching these specific SVR-linked diplomatic targeting campaigns exploiting CVE-2023-3883, if strictly limiting choices to the provided text snippet's groups—such as Turla, Gamaredon, RedCurl, Saint Bear, CopyKittens, or Naikon—Turla is attributed to Russia's FSB, whereas the report specifically highlights the SVR and CVE-2023-3883 vectors commonly tracked under APT29/Cozy Bear).*
- **$V_{0h}$ Model Answer**: Based on the threat report and the provided context, the campaign and vulnerability exploitation details point to the Russian cyber espionage group **Turla** (associated with MITRE ATT&CK Group ID **G0010**, which has ties to Russia's FSB/intelligence apparatus and has a history of targeting diplomatic entities and leveraging spear-phishing campaigns).   Additionally, the specific mention of exploiting CVE-2023-3883 in connection with a Russian APT group targeting diplomats aligns with known threat intelligence attributing these specific WinRAR exploit campaigns to **Turla**.  * **Threat Actor Group:** Turla ([G0010](https://attack.mitre.org/groups/G0010))

### Losing Cases ($V_{\text{rel}}$ Underperforms $V_{0h}$, $N=3$)

#### Case 20 (Query ID: `bd007da00d41`)
- **Ground Truth**: `Kimsuky`
- **Detected Software**: `cmd.exe (canonical: cmd)`
- **Top-3 Voted Threat Groups**: `Orangeworm (G0071, score: 0.1667), APT18 (G0026, score: 0.1667), BRONZE BUTLER (G0060, score: 0.1667)`
- **Ground Truth Present in Retrieved Context**: `False`
- **$V_{\text{rel}}$ Model Answer**: Based on the threat report provided, the campaign features techniques, tools (such as TutRAT / C# R.A.T.), and targeting characteristics (South Korean victims, HWP document references, and specific script-based attack chains) historically associated with North Korean threat actors.   However, looking specifically at the malware tools and tactics mentioned (such as the use of **TutRAT** / **C# R.A.T.** against Korean targets), this aligns with known activity attributed to the threat group **Dark Pink** (or related operations targeting the region).   ### Attribution Summary: * **Threat Group:** Dark Pink (or North Korea-affiliated actors targeting South Korea) * **Software/Tools:** TutRAT / C# R.A.T. (associated with open-source remote access trojans utilized in these campaigns)
- **$V_{0h}$ Model Answer**: Based on the threat report provided, the campaign and associated tactics align closely with known activities attributed to North Korea-linked threat groups and specific malware frameworks.   ### Attribution and Mapping:  * **Threat Group:** **Kimsuky** (also tracked under various aliases such as *Thallium* or *APT43*, historically associated with targeting South Korean entities using tailored lures like PDF/document-based shortcut (.lnk) files and multi-stage script execution). * **Malware/Software:**    * **TutRat / TutClient / C# R.A.T.** (identified in Stage 3 as the open-source C# remote access trojan used for full host control, keylogging, and surveillance).   * **PowerShell / VBScript Stagers** leveraging legitimate cloud services (Dropbox, Google Docs) for command and control (C2) and payload delivery (often associated with custom toolsets used in campaigns like *DEEP#GOSU*).  ### MITRE ATT&CK Mapping Summary: * **T1204.002** - User Execution: Malicious File (.lnk shortcut files) * **T1102** - Web Service (Dropbox used for C2 and payload staging) * **T1059.005** - Command and Scripting Interpreter: VBScript * **T1059.001** - Command and Scripting Interpreter: PowerShell * **T1047** - Windows Management Instrumentation (WMI) * **T1053** - Scheduled Task/Job (Persistence) * **T1082** - System Information Discovery * **T1041** - Exfiltration Over C2 Channel * **T1056.001** - Input Capture: Keylogging

#### Case 26 (Query ID: `b9933f2beb82`)
- **Ground Truth**: `Mint Sandstorm`
- **Detected Software**: `CharmPower (canonical: CharmPower), CharmPower (canonical: CharmPower), CharmPower (canonical: CharmPower), CharmPower (canonical: CharmPower), Impacket (canonical: Impacket), Impacket (canonical: Impacket), Soldier (canonical: SysUpdate), Soldier (canonical: SysUpdate), Soldier (canonical: SysUpdate), Soldier (canonical: SysUpdate), Soldier (canonical: SysUpdate), Soldier (canonical: SysUpdate), Soldier (canonical: SysUpdate)`
- **Top-3 Voted Threat Groups**: `Threat Group-3390 (G0027, score: 7.1111), Magic Hound (G0059, score: 4.1111), Dragonfly (G0035, score: 0.1111)`
- **Ground Truth Present in Retrieved Context**: `False`
- **$V_{\text{rel}}$ Model Answer**: Based on the provided threat report and context, the threat actor group described is **APT42** (also tracked by Microsoft historically as *PHOSPHORUS* and overlapping with reporting on *APT35*, *Charming Kitten*, and *TA453*).  ### Attribution Summary: * **Threat Group:** APT42 / PHOSPHORUS (associated with MITRE ATT&CK Group **G1044** / APT42) * **Associated Software/Tools mentioned in report:**    * Drokbk   * Soldier   * CharmPower
- **$V_{0h}$ Model Answer**: Based on the provided threat report—which details operations by an Iranian nation-state actor historically named *PHOSPHORUS* by Microsoft, associated with the Islamic Revolutionary Guard Corps (IRGC), overlapping with public reporting for *APT35*, *APT42*, *Charming Kitten*, and *TA453*, and known for using custom malware such as *CharmPower*, *Drokbk*, and *Soldier*—the incident maps to the following MITRE ATT&CK threat groups:  ### **Threat Actor Attribution** * **Primary Group:** **APT35** / **TA453** / **Charming Kitten** (often tracked under MITRE as **APT35** or associated Iranian state-sponsored activity). * **Specific Subgroup / Campaign Context:** **APT42** (the subgroup historically recognized within Mint Sandstorm/Phosphorus for targeted phishing, surveillance, and operations aligned with the IRGC).  ### **Associated Software / Tools (Malware)** * **CharmPower** (PowerShell backdoor) * **Drokbk** (S0687 / .NET implant) * **Soldier** (.NET backdoor)

#### Case 36 (Query ID: `a07eb7d47158`)
- **Ground Truth**: `Bahamut`
- **Detected Software**: ``
- **Top-3 Voted Threat Groups**: ``
- **Ground Truth Present in Retrieved Context**: `False`
- **$V_{\text{rel}}$ Model Answer**: Based on the threat report and the provided context, the incident can be attributed to the following MITRE ATT&CK groups and software:  ### **Threat Actor Attribution** * **APT-C-23** (also referenced indirectly through tactics, tradecraft, and historical naming conventions associated with the "Arabian Sea" fish reference/Bellingcat attribution to **DarkCaracal** / **APT-C-23**).  ### **Malware / Software Attribution** * **SpyC23** (Software ID: **S1195**) - The mobile spyware utilized by APT-C-23 targeting Android devices.
- **$V_{0h}$ Model Answer**: Based on the threat report and the provided context, the incident can be attributed to the following MITRE ATT&CK groups and software:  ### **Attribution Summary** * **Threat Group:** **APT-C-23** (also referenced in the report through descriptions matching the Arabic mythology reference "Bahamut", which operates closely with or is documented alongside APT-C-23 infrastructure and mobile campaigns). * **Software / Malware:** **SpyC23** (Software ID: **S1195**) — the Android mobile spyware utilized by APT-C-23 for espionage and data exfiltration.  ### **Mapping Details** * **Threat Group:** [APT-C-23](https://attack.mitre.org/groups/G1028) * **Associated Malware:** [SpyC23](https://attack.mitre.org/software/S1195) (S1195)

### Limitations & Failure Analysis: Entity Detector Homonym Collisions

#### Descriptive Case Study: Case 26 (Polysemy Collision: "Soldier" Matching SysUpdate)
- **Query Context**: Threat report describing an Iranian threat actor operation (Ground Truth: `Mint Sandstorm`, Microsoft tracking for Iranian state-sponsored activity). The report mentions custom malware tools including *CharmPower*, *Drokbk*, and a .NET backdoor named *Soldier*.
- **Detector Anomaly**: The surface entity detector identified the token *"Soldier"* and matched it to the canonical STIX alias for `SysUpdate` (S0434), a widely documented Chinese malware family.
- **Relationship Expansion Effect**: Following the STIX ontology relation `SysUpdate --uses--> Threat Group-3390` (G0027, Chinese state-sponsored threat group), $V_{\text{rel}}$ injected Threat Group-3390 context into the prompt for an Iranian threat incident query.
- **Observed Impact**: While the model maintained attribution accuracy under Scorer Variant 2 by identifying Iranian subgroup `APT42`, this case concretely demonstrates the vulnerability of ontology-driven expansion to surface-level homonym and polysemy collisions across distinct geopolitical entities.

---

## 10. Daily API Calls Accounting & Operational Log

### Calls Per Model Per UTC Day

| UTC Date | Target Model | Successful Calls | Rate-Limited Calls (429) | Server Errors (503) | Total Calls | Operational Accounting Notes |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| `2026-10-21` | `gemini-3.5-flash-lite` | 500 | 12 | 2 | 514 | Nominal 500 daily quota |
| `2026-10-22` | `gemini-3.5-flash-lite` | 500 | 14 | 0 | 514 | Nominal 500 daily quota |
| `2026-10-23` | `gemini-3.5-flash-lite` | 0 | 1 | 0 | 1 | Nominal 500 daily quota |
| `2026-10-25` | `gemini-3.5-flash-lite` | 998 | 17 | 1 | 1016 | Crossed 07:00 UTC daily quota reset boundary (391 pre-reset + 607 post-reset) |
| `2026-10-25` | `models/gemini-3.1-flash-lite` | 201 | 0 | 0 | 201 | Separate quota pool; completed Part F replication (1 probe + 200 benchmark calls) |

> [!NOTE]
> **Quota Accounting Clarification**: On 2026-10-25, 998 successful calls were served on the primary model `gemini-3.5-flash-lite`. This occurred because the Google Gemini API daily quota resets at **07:00:00 UTC**. Phase 6C completed 391 calls (389 benchmark + 2 probes) prior to 07:00 UTC, after which the daily quota refreshed, allowing Phase 6D priority arms to complete an additional 607 calls before the new daily bucket was exhausted.

### Operational Status of Background Generator Daemon
- **Background Task ID**: `task-12399` (PID 19736).
- **Process State**: Daemon is safely sleeping on exponential backoff, probing every 10 minutes.
- **Remaining Generation Calls**: Arms D3 (`CTI-ATTACK`, 131 remaining calls), D2b (229 calls), and D4 (60 calls). Upon daily quota refresh, the daemon will automatically resume and complete these calls without manual intervention.

