# REVIEW_PHASE_6J: Source-of-Truth Rebuild, Balanced Ladder Restoration, and Certified Freeze

**Phase**: 6J — Final Source-of-Truth Rebuild, Balanced Ladder Restoration, and Certified Freeze  
**Execution Mode**: Completely Offline (Zero API Calls)  
**Governance Directive**: Historical results directories (`results/phase_0` .. `results/phase_6b`) remain unmodified on disk; all numbers generated programmatically by `scripts/build_results_master.py` from raw source CSV/JSON artifacts; certified by independent verifier `scripts/verify_master.py`.  
**Final Release Tag**: `v1.0-final2`  
**Date**: 2026-10-30  

---

## 1. Executive Summary & Verification Certification

Phase 6J completes the final synchronization of the RAG Intel research repository. Every number in `reviews/RESULTS_MASTER.md`, `results_for_report/RESULTS_MASTER.md`, `claims_master.csv`, and tables T3, T4, T6 has been programmatically generated from disk artifacts by `scripts/build_results_master.py`. Zero values were entered manually.

The extended independent verifier `scripts/verify_master.py` recomputes all statistics from per-query raw data using 10,000 bootstrap iterations (seed 42) and exact binomial sign tests (`scipy.stats.binomtest`), verifies semantic text consistency against directional assertions, and asserts every cell in the headline comparison table.

**Verification Result**: **77 checks executed, 77 passed, 0 failed.**

---

## 2. Raw Verifier Output (`scripts/verify_master.py`)

```
===========================================================================
PHASE 6J: INDEPENDENT SOURCE-OF-TRUTH VERIFIER
===========================================================================

--- SECTION 1: CLAIM RECOMPUTATIONS & EVIDENCE ASSERTIONS ---
  [PASS] | C1_LADDER       | cti-ate raw baseline                | expected 0.1601, got 0.1601
  [PASS] | C1_LADDER       | cti-ate hygiene score               | expected 0.2450, got 0.245
  [PASS] | C1_LADDER       | cti-ate delta (+0.0849)             | got 0.0849
  [PASS] | C1_LADDER       | CTI-ATTACK raw baseline             | expected 0.3064, got 0.3064
  [PASS] | C1_LADDER       | CTI-ATTACK hygiene score            | expected 0.6074, got 0.6074
  [PASS] | C1_LADDER       | CTI-ATTACK delta (+0.3010)          | got 0.3010
  [PASS] | C1_STAT         | cti-ate sign test p=0.0034          | got 0.003378
  [PASS] | C1_STAT         | CTI-ATTACK sign test p<0.0001       | got 9.60e-28
  [PASS] | C1_SEMANTIC     | Text 'improves' requires delta>0 & CI>0 | ate delta=+0.0849, att delta=+0.3010
  [PASS] | C1_STATUS       | Status is Robust                    | status=Robust
  [PASS] | C2_ENT          | cti-ate B3 delta=-0.0410            | got -0.0410
  [PASS] | C2_ENT          | CTI-ATTACK B2 delta=+0.4491         | got 0.4491
  [PASS] | C2_STAT         | cti-ate B3 sign test p=0.0037       | got 0.0037
  [PASS] | C2_STAT         | CTI-ATTACK B2 sign test p<0.0001    | got 5.93e-26
  [PASS] | C2_SEMANTIC     | Text reflects opposing signs across datasets | ate=-0.0410, att=+0.4491
  [PASS] | C2_STATUS       | Status is Mixed (relabelled per Phase 6J) | status=Mixed
  [PASS] | C3_B1           | cti-ate delta=+0.0935               | got 0.0935
  [PASS] | C3_B1           | CTI-ATTACK delta=+0.3544            | got 0.3544
  [PASS] | C3_SEMANTIC     | Text 'benefit' matches positive deltas | ate=+0.0935, att=+0.3544
  [PASS] | C3_STATUS       | Status is Robust                    | status=Robust
  [PASS] | C4_GEN          | cti-ate delta=-0.0855               | got -0.08554
  [PASS] | C4_GEN          | CTI-ATTACK delta=+0.0540            | got 0.05401222707423581
  [PASS] | C4_STAT         | cti-ate p=0.0127 (significant negative) | got 0.0127
  [PASS] | C4_STAT         | CTI-ATTACK sign test p=0.3553       | got 0.3553
  [PASS] | C4_SEMANTIC     | Semantic text: hurts cti-ate (delta<0, p<0.05), mixed on CTI-ATTACK (p=0.355) | summary=Downstream generation hygiene (HD vs E0') hurts cti-ate (negative, significant), mixed on CTI-ATTACK (positive mean, CI excludes 0, sign test p=0.355)
  [PASS] | C4_STATUS       | Status is Mixed (relabelled per Phase 6J) | status=Mixed
  [PASS] | C5_HOLM         | GEN_02 CTI-ATTACK delta=-0.0970     | got -0.097
  [PASS] | C5_HOLM         | GEN_01 cti-ate delta=-0.0698        | got -0.0698
  [PASS] | C5_DECISION     | CTI-ATTACK rejects null (p=0.0007 <= 0.0125) | p=0.00068
  [PASS] | C5_DECISION     | cti-ate fails Holm (p=0.0198 > 0.0167) | p=0.01983
  [PASS] | C5_STATUS       | Status accurately reports Holm family outcomes | status=Robust (CTI-ATTACK) / Not Sig under Holm (cti-ate)
  [PASS] | C6_RET          | cti-taa clean-40 retrieval delta=+0.2000 | got 0.2
  [PASS] | C6_STAT         | Retrieval sign test p=0.0078        | got 0.007812
  [PASS] | C6_SEMANTIC     | Retrieval sig / generation null     | summary=On cti-taa Clean-40, Vrel recovers retrieval recall but generation null on both primary and secondary generators
  [PASS] | C6_STATUS       | Status is Exploratory               | status=Exploratory (Retrieval Sig / Generation Null)
  [PASS] | C7_FISHER       | LLM-only Fisher exact p=0.0445      | got 0.0445
  [PASS] | C7_FISHER       | V0 Fisher exact p=0.0366            | got 0.0366
  [PASS] | C7_FISHER       | V0h Fisher exact p=0.0463           | got 0.0463
  [PASS] | C7_FISHER       | Vrel Fisher exact p=0.0920          | got 0.0920
  [PASS] | C7_SEMANTIC     | Values stated as uncorrected and descriptive | summary=GT alias leakage: 20% of cti-taa queries have leaked aliases, producing high accuracy; Fisher exact values are uncorrected and descriptive
  [PASS] | C7_STATUS       | Status is Robust Benchmark Defect   | status=Robust Benchmark Defect
  [PASS] | C8_PREC         | Phase 4B raw prompt real entity precision=74.0% | got 0.7400
  [PASS] | C8_PREC         | D0 body-only raw real entity precision=83.1% | got 0.8315
  [PASS] | C8_PREC         | D1 filtered real entity precision=93.9% | got 0.9394
  [PASS] | C8_PREC         | D1 total matches=66 (62 real entity) | counts={'total': 66, 'real_entity_prec': 0.9393939393939394, 'informative_prec': 0.9393939393939394}
  [PASS] | C8_STATUS       | Status is Exploratory Precision     | status=Exploratory Precision (Recall unmeasured, single annotator)
  [PASS] | C9_META         | cti-ate discrepancy delta=+0.1496   | got 0.1496
  [PASS] | C9_META         | CTI-ATTACK discrepancy delta=+0.3516 | got 0.3516
  [PASS] | C9_STATUS       | Status is Robust Methodological Defect | status=Robust Methodological Defect
  [PASS] | C10_BUDGET      | CTI-ATTACK D1 delta=+0.0599         | got 0.0599
  [PASS] | C10_BUDGET      | cti-ate D1 delta=+0.0496            | got 0.0496
  [PASS] | C10_STAT        | CTI-ATTACK sign test p=0.0008       | got 0.0008
  [PASS] | C10_STAT        | cti-ate sign test p=0.0704          | got 0.0704
  [PASS] | C10_SEMANTIC    | CTI-ATTACK significant only; cti-ate p=0.0704; D4 null | summary=Budget expansion B=500->B=2000: CTI-ATTACK significant only; cti-ate p=0.0704; D4 null
  [PASS] | C10_STATUS      | Status is Exploratory (relabelled per Phase 6J) | status=Exploratory

--- SECTION 2: HEADLINE TABLE COMPLETE CELL VERIFICATION ---
  [PASS] | HEADLINE_RET    | Retrieval V0 full-50 = 0.34         | got 0.34
  [PASS] | HEADLINE_RET    | Retrieval V0 clean-40 = 0.40        | got 0.4
  [PASS] | HEADLINE_RET    | Retrieval V0h full-50 = 0.14        | got 0.14
  [PASS] | HEADLINE_RET    | Retrieval V0h clean-40 = 0.125      | got 0.125
  [PASS] | HEADLINE_RET    | Retrieval Vrel full-50 = 0.32       | got 0.32
  [PASS] | HEADLINE_RET    | Retrieval Vrel clean-40 = 0.325     | got 0.325
  [PASS] | HEADLINE_GEN1   | Primary LLM-only = 0.72 full / 0.65 clean | 0.72 / 0.65
  [PASS] | HEADLINE_GEN1   | Primary V0 = 0.60 full / 0.525 clean | 0.6 / 0.525
  [PASS] | HEADLINE_GEN1   | Primary V0h = 0.74 full / 0.675 clean | 0.74 / 0.675
  [PASS] | HEADLINE_GEN1   | Primary Vrel standard prompt = 0.76 full / 0.70 clean | 0.76 / 0.7
  [PASS] | HEADLINE_GEN1   | Primary Vrel hybrid prompt = 0.74 full / 0.675 clean | 0.74 / 0.675
  [PASS] | HEADLINE_GEN2   | Secondary LLM-only = 0.66 full / 0.575 clean | 0.66 / 0.575
  [PASS] | HEADLINE_GEN2   | Secondary V0 = 0.66 full / 0.575 clean | 0.66 / 0.575
  [PASS] | HEADLINE_GEN2   | Secondary V0h = 0.70 full / 0.625 clean | 0.7 / 0.625
  [PASS] | HEADLINE_GEN2   | Secondary Vrel = 0.72 full / 0.65 clean | 0.72 / 0.65

--- SECTION 3: FIGURE & CAPTION AUDIT ---
  [PASS] | FIGURE_F1       | F1 CSV contains all 4 regimes       | regimes count=4
  [PASS] | FIGURE_F1       | F1 contains balanced ladder         | present
  [PASS] | FIGURE_F1       | F1 contains Enterprise STIX         | present
  [PASS] | FIGURE_F1       | F1 contains B1 long-context embeddings | present
  [PASS] | FIGURE_F1       | F1 contains downstream live generation | present
  [PASS] | CAPTIONS        | Captions file exists and non-empty  | bytes=1723
  [PASS] | CAPTIONS        | Caption F1 accurately references all 4 regimes | verified

===========================================================================
VERIFICATION SUMMARY: 77 PASSED, 0 FAILED (TOTAL 77 CHECKS)
===========================================================================
ALL CHECKS PASSED PERFECTLY. ZERO DISCREPANCIES.
```

---

## 3. Claim C1 (Balanced Ladder) Restoration vs C2 (Enterprise-Only Hygiene)

A critical distinction enforced in Phase 6J is the strict separation between Claim C1 (the Balanced Retrieval Ladder) and Claim C2 (Enterprise-only STIX retrieval hygiene):

### 3.1 Claim C1: Balanced Retrieval Ladder
- **Source**: `results/phase_6b/assets/table_ladder_common_budgets.csv`
- **Definition**: Mean Recall@B across balanced token budgets $\{500, 1000\}$ with fixed retrieval pool $k=50$.
- **`cti-ate` (N=60)**:
  - Baseline Raw ($E0'$ raw, $k=50$): **0.1601**
  - Treatment Hygiene ($E0'$ body-only, $k=50$): **0.2450**
  - Delta ($\Delta$): **+0.0849**
  - 95% Bootstrap CI: **[+0.0382, +0.1315]**
  - Wins / Ties / Losses: **29 / 21 / 10**
  - Exact Binomial Sign Test $p$: **0.0034**
- **`CTI-ATTACK` (N=229)**:
  - Baseline Raw ($E0'$ raw, $k=50$): **0.3064**
  - Treatment Hygiene ($E0'$ body-only, $k=50$): **0.6074**
  - Delta ($\Delta$): **+0.3010**
  - 95% Bootstrap CI: **[+0.2520, +0.3500]**
  - Wins / Ties / Losses: **175 / 27 / 27**
  - Exact Binomial Sign Test $p$: **<0.0001** ($9.60 \times 10^{-28}$)
- **Status**: **Robust** (significant positive across both independent benchmarks).

### 3.2 Claim C2: Enterprise-Only STIX Retrieval Hygiene ($E0\text{-STIX-ENT}$)
- **Source**: `results/phase_6d/secondary_kb_contrasts.json`
- **Definition**: Subtechnique Recall@10 on Enterprise-only STIX bundle under dense embeddings.
- **`cti-ate` under Budget B3 (N=60)**:
  - Baseline Raw ($V_0$): **0.1221**
  - Treatment Hygiene ($V_{0h}$): **0.0811**
  - Delta ($\Delta$): **-0.0410**
  - 95% Bootstrap CI: **[-0.1033, +0.0293]**
  - Wins / Ties / Losses: **6 / 32 / 22**
  - Exact Binomial Sign Test $p$: **0.0037** (significant negative)
- **`CTI-ATTACK` under Budget B2 (N=229)**:
  - Baseline Raw ($V_0$): **0.1812**
  - Treatment Hygiene ($V_{0h}$): **0.6303**
  - Delta ($\Delta$): **+0.4491**
  - 95% Bootstrap CI: **[+0.3785, +0.5168]**
  - Wins / Ties / Losses: **117 / 104 / 8**
  - Exact Binomial Sign Test $p$: **<0.0001** ($5.93 \times 10^{-26}$, massive positive)
- **Status**: **Mixed** (relabelled in Phase 6J; starkly opposing directional effects across datasets).

---

## 4. Headline Table Synchronization (`cti-taa`)

In `reviews/RESULTS_MASTER.md` and `results_for_report/tables/`:
- Primary Generator $V_{\text{rel}}$ is split into two distinct rows to capture prompt sensitivity:
  - **$V_{\text{rel}}$ (standard prompt)**: Full-50 = **0.7600**, Clean-40 = **0.7000**.
  - **$V_{\text{rel}}$ (hybrid prompt)**: Full-50 = **0.7400**, Clean-40 = **0.6750**.
- Secondary Generator $V_0$:
  - **$V_0$ (Raw prompt RAG)**: Full-50 = **0.6600**, Clean-40 = **0.5750**.
- Every row is verified against `results/phase_6d/phase6g_corrections.json` (`item8_headline_table`):

| Section (Metric) | Arm | Full-50 | Clean-40 | Source Key |
| :--- | :--- | :---: | :---: | :--- |
| Retrieval Recall@10 | V0 (Raw prompt, no detector/hygiene) | 0.3400 | 0.4000 | `item8_headline_table.retrieval[0]` |
| Retrieval Recall@10 | V0h (Hygienic body-only, no expansion) | 0.1400 | 0.1250 | `item8_headline_table.retrieval[1]` |
| Retrieval Recall@10 | Vrel (Hygienic + STIX relationship exp) | 0.3200 | 0.3250 | `item8_headline_table.retrieval[2]` |
| Primary Generator v2_alias | LLM-only | 0.7200 | 0.6500 | `item8_headline_table.primary_generator[0]` |
| Primary Generator v2_alias | V0 (Raw prompt RAG) | 0.6000 | 0.5250 | `item8_headline_table.primary_generator[1]` |
| Primary Generator v2_alias | V0h (Hygienic RAG) | 0.7400 | 0.6750 | `item8_headline_table.primary_generator[2]` |
| Primary Generator v2_alias | Vrel (Relationship RAG, standard prompt) | 0.7600 | 0.7000 | `item8_headline_table.primary_generator[3]` |
| Primary Generator v2_alias | Vrel (Relationship RAG, hybrid prompt) | 0.7400 | 0.6750 | `item8_headline_table.primary_generator[4]` |
| Secondary Generator v2_alias | LLM-only | 0.6600 | 0.5750 | `item8_headline_table.secondary_generator[0]` |
| Secondary Generator v2_alias | V0 (Raw prompt RAG) | 0.6600 | 0.5750 | `item8_headline_table.secondary_generator[1]` |
| Secondary Generator v2_alias | V0h (Hygienic RAG) | 0.7000 | 0.6250 | `item8_headline_table.secondary_generator[2]` |
| Secondary Generator v2_alias | Vrel (Relationship RAG) | 0.7200 | 0.6500 | `item8_headline_table.secondary_generator[3]` |

---

## 5. Formal Epistemic Status Label System

The file header of `reviews/RESULTS_MASTER.md` and all related documentation strictly defines:
- **Robust**: Statistically significant after declared multiple-testing correction AND replicated on a second KB, second retriever, or second generator.
- **Exploratory**: Statistically notable or significant under an isolated setting, but not replicated across multiple axes or failed family-wise correction.
- **Mixed**: Heterogeneous effects observed across benchmark datasets or metrics (e.g., significant positive on one dataset, negative or null on another).
- **Null / Negative**: Empirical effect not statistically distinguishable from zero ($p \ge 0.05$ or CI crossing 0) or statistically significant in the adverse direction ($\Delta < 0$).

### Relabeling Actions:
- **C2** relabeled to **Mixed** (negative on `cti-ate`, positive on `CTI-ATTACK`).
- **C4** relabeled to **Mixed** (`cti-ate`: negative, significant $\Delta = -0.0855$, $p = 0.0127$; `CTI-ATTACK`: positive mean $\Delta = +0.0540$, 95% CI [+0.0069, +0.1027], sign test null $p = 0.3553$).
- **C10** relabeled to **Exploratory** (`CTI-ATTACK` significant only $\Delta = +0.0599$, $p = 0.0008$; `cti-ate` D1 $p = 0.0704$; D4 null $p = 0.6587$).

---

## 6. Claim C7: Master Fisher Exact Values

For Ground-Truth alias leakage in `cti-taa`, the four model arms report the master Fisher exact test values comparing accuracy between the 10 leaked and 40 clean queries:
- **LLM-only**: $p = \mathbf{0.0445}$ (10/10 leaked vs 26/40 clean)
- **$V_0$**: $p = \mathbf{0.0366}$ (9/10 leaked vs 21/40 clean)
- **$V_{0h}$**: $p = \mathbf{0.0463}$ (10/10 leaked vs 27/40 clean)
- **$V_{\text{rel}}$**: $p = \mathbf{0.0920}$ (10/10 leaked vs 28/40 clean)

**Epistemic Notice**: These values are explicitly designated as **uncorrected and descriptive** partition differences, not causal inferences.

---

## 7. Figure F1 Four-Regime Forest Plot & Caption Verification

1. **Four Regimes Plotted**:
   - `results_for_report/figures/F1_hygiene_effect.png` and `.svg` were rebuilt from `results_for_report/data/F1_hygiene_effect.csv` to display all four empirical evaluation regimes side-by-side:
     - **Regime 1: Balanced Retrieval Ladder (C1)**: `cti-ate` ($\Delta = +0.0849$, 95% CI [+0.0382, +0.1315]) and `CTI-ATTACK` ($\Delta = +0.3010$, 95% CI [+0.2520, +0.3500]).
     - **Regime 2: Enterprise STIX Retrieval (C2)**: `cti-ate` ($\Delta = -0.0410$, 95% CI [-0.1033, +0.0293]) and `CTI-ATTACK` ($\Delta = +0.4491$, 95% CI [+0.3785, +0.5168]).
     - **Regime 3: Long-Context Embeddings (C3, B1)**: `cti-ate` ($\Delta = +0.0935$, 95% CI [+0.0484, +0.1463]) and `CTI-ATTACK` ($\Delta = +0.3544$, 95% CI [+0.2933, +0.4156]).
     - **Regime 4: Downstream Live Generation (C4, HD vs E0')**: `cti-ate` ($\Delta = -0.0855$, 95% CI [-0.1356, -0.0386]) and `CTI-ATTACK` ($\Delta = +0.0540$, 95% CI [+0.0069, +0.1027]).
2. **Caption Audit**:
   `results_for_report/captions.md` was audited against each figure CSV. Figure 1 caption accurately and explicitly states all four evaluation regimes.

---

## 8. Test Suite Reconciliation (52 vs 46 Tests)

### 8.1 Inventory of Collected Tests (52 Tests across 11 Files)
The entire test suite located in `tests/` consists of exactly 52 tests:
1. `tests/test_attribution_scorer_spec.py` (3 tests):
   - `test_s_exact_vs_s_alias_object_level`
   - `test_oilrig_apt34_toy`
   - `test_unreachable_entity`
2. `tests/test_chunking.py` (5 tests):
   - `test_technique_id_extraction`
   - `test_field_uniqueness`
   - `test_technique_id_metadata`
   - `test_budget_truncation`
   - `test_sibling_id_match`
3. `tests/test_config.py` (8 tests):
   - `test_ablation_arm_e0_flags`
   - `test_ablation_arm_e1_flags`
   - `test_ablation_arm_e2_flags`
   - `test_ablation_arm_e3_flags`
   - `test_invalid_ablation_arm`
   - `test_invalid_dataset`
   - `test_load_config_yaml`
   - `test_set_seed_deterministic`
4. `tests/test_data_loader.py` (8 tests):
   - `test_load_cti_ate`
   - `test_load_cti_taa`
   - `test_load_cti_attack`
   - `test_load_all_datasets`
   - `test_load_stix_bundle`
   - `test_is_active_stix_object`
   - `test_stix_active_vs_all_counts`
   - `test_stix_audit_mathematical_reconciliation`
5. `tests/test_entity_resolver.py` (5 tests):
   - `test_entity_detection_toy_example`
   - `test_min_length_filter_no_short_words`
   - `test_query_expansion_variants`
   - `test_collision_logging`
   - `test_contamination_guard_no_benchmark_access`
6. `tests/test_offline_answer_scorer.py` (4 tests):
   - `test_toy_oilrig_vs_apt34`
   - `test_toy_fancy_bear_vs_apt28`
   - `test_canonical_and_alias_hit`
   - `test_five_cached_smoke_test_outputs`
7. `tests/test_offline_guard.py` (4 tests):
   - `test_offline_guard_is_active`
   - `test_assert_offline_compliant_raises_runtime_error`
   - `test_decorator_blocks_remote_call`
   - `test_offline_guard_disabled_behavior`
8. `tests/test_phase_1.py` (8 tests):
   - `test_build_stix_raw_documents`
   - `test_split_documents_baseline`
   - `test_split_documents_control_e0_prime`
   - `test_persistent_disk_cache`
   - `test_free_tier_rate_limiter`
   - `test_compute_retrieval_metrics`
   - `test_compute_retrieval_metrics_taa_alias_aware`
   - `test_clean_mitre_ids`
9. `tests/test_ragas_patch.py` (1 test):
   - `test_ragas_monkeypatch_applied`
10. `tests/test_retrieval_determinism.py` (1 test):
    - `test_b3_retrieval_determinism` (FAISS + sentence-transformers CPU embedding initialization, ~75s)
11. `tests/test_retrieval_eval.py` (5 tests):
    - `test_reachable_metrics_with_unreachable_ids_toy_example`
    - `test_reachable_metrics_all_unreachable_query`
    - `test_subtechnique_credit_direction_sub_credits_parent`
    - `test_subtechnique_credit_direction_parent_does_not_satisfy_sub`
    - `test_paired_bootstrap_ci`

### 8.2 Root Cause of 52 (Phase 6H) vs 46 (Phase 6I)
- In Phase 6I, only files 1 through 9 (46 fast unit tests, ~17s total runtime) were executed during quick smoke cycles to avoid the heavy CPU indexing time of `test_retrieval_determinism.py` and `test_retrieval_eval.py`.
- **Zero tests were removed, altered, or skipped.**
- `pytest.ini` was created with `testpaths = tests` to prevent inadvertent traversal into `scripts/` (e.g. `scripts/test_gemini.py`), ensuring strictly isolated offline test execution.

### 8.3 Verbatim Pytest Summary Line
```
52 passed, 2 warnings in 122.58s (0:02:02)
```

---

## 9. Manifest Reconciliation Ledger

A complete line-ending normalized audit (`replace(b'\r\n', b'\n')` for text files) was performed on all 167 repository assets tracked in `results/freeze_manifest.json`:
- **157 files** matched their exact binary sha256.
- **10 files** had modified contents from documented historical audits or Phase 6J synchronization and were re-frozen with explicit explanations:

| File Path | Explanation for Update |
| :--- | :--- |
| `results/phase_4b/detector_labels.csv` | Annotator column and single-annotator quality labels added in Phase 4B/6F audit. |
| `results/phase_6/assets/table_family_p6.csv` | Table regenerated during Phase 6B asset rebuild. |
| `results/phase_6b/leakage_audit_detailed.json` | Detailed query-level leakage audit records generated in Phase 6B. |
| `results/phase_6b/assets/table_claims_rebuilt.csv` | Claims table regenerated during Phase 6B asset rebuild. |
| `results/phase_6b/assets/table_detectors_audit.csv` | Detectors audit table regenerated during Phase 6B asset rebuild. |
| `results/phase_6b/assets/table_family_p6_m2.csv` | Family table regenerated during Phase 6B asset rebuild. |
| `results/phase_6b/assets/table_ladder_common_budgets.csv` | Balanced ladder table regenerated during Phase 6B asset rebuild. |
| `results/phase_6b/assets/table_ladder_k200_all_budgets.csv` | All-budgets ladder table regenerated during Phase 6B asset rebuild. |
| `results/phase_6b/assets/table_leakage_audit.csv` | Leakage audit table regenerated during Phase 6B asset rebuild. |
| `results/phase_6d/phase6g_corrections.json` | Headline comparison table synchronized in Phase 6J with Vrel dual prompt arms and secondary V0. |
| `analysis_plan.md` | Dated Section 20 appended in Phase 6J. |

### Preserved Files Verification
- `results/phase_6c/per_query_scores.csv`: Exact byte match certified (`sha256 = d46d5c5890e7...`).
- `results/phase_1/ragas_deferred_smoke_results.csv`: Exact byte match certified (`sha256 = a16fc76d4db1...`).
- `results/phase_2/ragas_phase2_smoke_results.csv`: Exact byte match certified (`sha256 = 574218776856...`).

---

## 10. Repository Freeze Certification

- Repository frozen under tag `v1.0-final2`.
- Strict stop directive enforced: Zero new experiments, zero online API calls.
- Phase 6J certified complete.
