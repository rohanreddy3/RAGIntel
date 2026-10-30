# REVIEW_PHASE_6L: Final Consistency Rebuild, Adversarial Audit Remediation, and Certified Freeze

**Date**: October 30, 2026  
**Phase**: Phase 6L (Final Consistency Synchronization & Certified Freeze)  
**Execution Guardrails**: Strictly offline, zero API invocations, zero edits to historical frozen results (`results/phase_0` through `results/phase_6b`).  
**Certification Verdict**: **100% PASS** (97/97 verification checks passed; 52/52 pytest tests passed).  
**Release Tag**: `v1.0-final4`  

---

## 1. Executive Summary

Phase 6L addresses and resolves all findings identified in the comprehensive independent adversarial audit (`reviews/FINAL_AUDIT.md`). In accordance with the project's strict scientific integrity and source-of-truth invariants:
1. **Full LaTeX Table Rebuild**: All publication-ready LaTeX tables (`T1_datasets.tex` through `T6_benchmark_defects.tex`) are now compiled programmatically by `scripts/build_results_master.py` from the exact same underlying data structures as the Markdown and CSV tables. Every single numerical token in the Markdown tables has been machine-verified to match its LaTeX counterpart.
2. **Elimination of Literal Hand-Typed Values**:
   - Claim C1's confidence intervals, W/T/L discordant pairs, and p-values are formally designated and labeled across all summaries as *"from Phase 6B run; per-query data not archived; not re-derivable"* while retaining verified point estimates ($\Delta = +0.0849$ on `cti-ate`, $+0.3010$ on `CTI-ATTACK`) from `results/phase_6b/assets/table_ladder_common_budgets.csv`.
   - Claim C7's Fisher exact p-values are computed dynamically in code via `scipy.stats.fisher_exact` (`0.0445, 0.0366, 0.0463, 0.0920`).
   - Claim C9's prose summary is formatted dynamically from `results/phase_6d/metadata_credit_audit.json` (`+0.1496 ate / +0.3516 att`), eliminating the stale historical relic (`+0.1556 / +0.3475`).
3. **Dual Baseline Reporting for Claim C2**:
   - Both Baseline B3 and Baseline B2 are reported for `cti-ate`: B3 yields $\Delta = -0.0410$ ($p=0.0037$, significant negative), while B2 yields $\Delta = -0.0082$ ($p=0.1516$, null).
   - The hygiene effect on `cti-ate` is explicitly documented as baseline-dependent.
4. **Architectural Confound Disclosures**:
   - Claim C4 explicitly discloses candidate pool truncation ($k=200$ vs $k=\text{all}$) as an experimental confound alongside query hygiene.
5. **Bidirectional Parent/Subtechnique Credit Sensitivity Analysis (CRIT-02)**:
   - Evaluated saved generation outputs offline under full bidirectional hierarchical credit across `CTI-ATTACK` and `cti-ate` (`results/phase_6l/bidirectional_sensitivity.csv` and `.json`).
   - Proved that model rankings on `CTI-ATTACK` are **100% invariant** under bidirectional credit: LLM-only (0.5834) > D1 (0.5249) > HD (0.4566) > E0' (0.3960).
   - Headline metric `f1_sub` retained for pre-registered comparability; prompt limitation fully disclosed.
6. **Multiplicity Family Transparency**:
   - Section 18.4 of `analysis_plan.md` renamed to `"Post-Hoc Confirmatory Generation Family (M=4)"` and explicitly documented as formulated after viewing Phase 6C results.
   - All uses of "pre-registered" removed for dates after 2026-10-19.
7. **Freeze Manifest & Certified Release**:
   - Manifest updated to `v1.0-final4` (169 files tracked with dual raw and LF-normalized SHA-256 hashes).
   - Documented in `analysis_plan.md` Section 21 that `results/phase_7/` is exploratory and excluded from the frozen manifest.

---

## 2. Audit Remediation Mapping Table

Mapping each finding from `reviews/FINAL_AUDIT.md` to its certified resolution:

| Audit ID | Severity | Category | Status | Action Taken, Location & Evidence |
| :--- | :---: | :--- | :---: | :--- |
| **CRIT-01** | CRITICAL | Publication Tables | **FIXED** | Extended `scripts/build_results_master.py` with `render_latex_table()` and `write_table_artifacts()` to generate `T1` through `T6` `.tex` files programmatically from the exact same data dicts as `.md` and `.csv`. Verified 100% numerical match in Section 4 of `scripts/verify_master.py`. |
| **CRIT-02** | CRITICAL | Prompting / Validity | **DISCLOSED & EVALUATED** | Implemented `scripts/compute_phase6l_bidirectional_sensitivity.py` to evaluate saved outputs with bidirectional parent-subtechnique credit. Archived in `results/phase_6l/bidirectional_sensitivity.csv` and `.json`. Proved relative rankings on `CTI-ATTACK` are 100% invariant: LLM-only (0.5834) > D1 (0.5249) > HD (0.4566) > E0' (0.3960). Preserved headline metric `f1_sub` for comparability; limitation disclosed in Section 21 of `analysis_plan.md`. |
| **CRIT-03** | CRITICAL | Source-of-Truth Protocol | **FIXED** | For C1, replaced hardcoded CI/WTL/p literals with explicit label `"from Phase 6B run; per-query data not archived; not re-derivable"` across `RESULTS_MASTER.md`, `claims_master.csv`, and Table T3. For C7, computed Fisher exact tests dynamically via `scipy.stats.fisher_exact`. |
| **MAJ-01** | MAJOR | Internal Consistency | **FIXED** | In `scripts/build_results_master.py` line 348–353, dynamically formatted Claim C9 summary using `mc_ate_hd['discrepancy_delta']` (`+0.1496`) and `mc_att_hd['discrepancy_delta']` (`+0.3516`), eliminating the stale `+0.1556 / +0.3475` strings. |
| **MAJ-02** | MAJOR | Test Harness | **FIXED** | Added `pythonpath = .` to `pytest.ini`. Standard `pytest -q` now executes cleanly from repository root (52/52 passed). |
| **MAJ-03** | MAJOR | KB Checksums | **FIXED** | Updated `data/README.md` with verified SHA-256 (`66f3fe3f07ef...`), size (49,253,343 bytes), and STIX specification 2.1 matching `data/mitre/enterprise-attack.json` on disk. |
| **MAJ-04** | MAJOR | Figure Artifacts | **FIXED** | Synchronized all figure CSVs, PNGs, SVGs, and caption text files from `results_for_report/figures/` into `report/figures/`. |
| **MAJ-05** | MAJOR | Confounded Controls | **DISCLOSED** | Added explicit confound note to Claim C4 summary: `(confound note: control is k=all, treatment is k=200, so hygiene is confounded with pool size)` and documented in `analysis_plan.md` Section 21. |
| **MAJ-06** | MAJOR | Baseline Selection | **FIXED / DISCLOSED** | In Claim C2, reported both Baseline B3 ($\Delta = -0.0410, p=0.0037$) and Baseline B2 ($\Delta = -0.0082, p=0.1516$) for `cti-ate`, and explicitly labeled the effect as baseline-dependent. |
| **MAJ-07** | MAJOR | Multiplicity Labeling | **FIXED** | Renamed `analysis_plan.md` Section 18.4 to `"Post-Hoc Confirmatory Generation Family (M=4)"` and noted it was formulated retrospectively after Phase 6C results were observed. Removed "pre-registered" for all post-2026-10-19 sections. |
| **MIN-01** | MINOR | Documentation | **FIXED** | Updated `README.md` project status to "Release v1.0 Frozen" and re-encoded directory tree using clean UTF-8 box characters. |
| **MIN-02** | MINOR | Encoding Artifacts | **FIXED** | Replaced unicode `α*` with ASCII `alpha*` across `build_results_master.py`, `claims_master.csv`, and `FINAL_AUDIT.md`. |
| **MIN-03** | MINOR | Resolver PRNG State | **NOT CHANGED** | Historic frozen code in `src/entity_resolver.py`. Deterministic when queries run in canonical index order. Documented as a code design limitation. |
| **MIN-04** | MINOR | Cache Exception Handler | **NOT CHANGED** | Historic frozen code in `src/cache.py`. All Phase 6 caches verified uncorrupted. Documented in technical limitations. |
| **MIN-05** | MINOR | Dataset Metadata | **FIXED** | Updated `report/dataset_stats.md` line 33 to "MITRE ATT&CK STIX 2.1 rolling master snapshot (2026-07-31)". |
| **MIN-06** | MINOR | Untracked Files | **DISCLOSED** | Documented in `analysis_plan.md` Section 21 that `results/phase_7/` contains exploratory post-v1.0 evaluation artifacts and is excluded from the frozen manifest. |
| **MIN-07** | MINOR | Detector Precision Sample | **DISCLOSED** | Maintained explicit status label in Claim C8: `"Exploratory Precision (Recall unmeasured, single annotator)"`. |
| **MIN-08** | MINOR | Lack of Test Splits | **DISCLOSED** | Documented in `analysis_plan.md` Section 21 and thesis limitations that small dataset sizes precluded held-out splits. |

---

## 3. Bidirectional Parent/Subtechnique Sensitivity Analysis (CRIT-02)

To evaluate the impact of the prompt-metric instruction mismatch (where the prompt instructed models to output main techniques excluding subtechniques while 47.8% of `CTI-ATTACK` ground truth targets are subtechniques), `scripts/compute_phase6l_bidirectional_sensitivity.py` re-scored all saved model generation outputs under full bidirectional hierarchical credit:

### Summary Table (`results/phase_6l/bidirectional_sensitivity.csv`)

| Dataset | Arm | Queries | Headline Metric (`f1_sub`) | Bidirectional F1 | Bidirectional Precision | Bidirectional Recall | Rank Shift |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **CTI-ATTACK** | LLM-only | 229 | 0.3964 | **0.5834** | 0.6385 | 0.5888 | Rank 1 $\to$ Rank 1 (Invariant) |
| **CTI-ATTACK** | D1 ($B=2000$) | 229 | 0.3593 | **0.5249** | 0.5735 | 0.5284 | Rank 2 $\to$ Rank 2 (Invariant) |
| **CTI-ATTACK** | HD ($B=500$) | 229 | 0.2994 | **0.4566** | 0.5186 | 0.4497 | Rank 3 $\to$ Rank 3 (Invariant) |
| **CTI-ATTACK** | E0' (Raw, $B=500$) | 229 | 0.2454 | **0.3960** | 0.4704 | 0.3804 | Rank 4 $\to$ Rank 4 (Invariant) |
| **cti-ate** | LLM-only | 60 | 0.4634 | **0.5494** | 0.5983 | 0.5518 | Rank 2 $\to$ Rank 1 (+1) |
| **cti-ate** | E0' (Raw, $B=500$) | 60 | 0.4792 | **0.5313** | 0.5543 | 0.5606 | Rank 1 $\to$ Rank 2 (-1) |
| **cti-ate** | D1 ($B=2000$) | 60 | 0.4432 | **0.5144** | 0.5721 | 0.5134 | Rank 3 $\to$ Rank 3 (Invariant) |
| **cti-ate** | HD ($B=500$) | 60 | 0.3936 | **0.4554** | 0.5199 | 0.4429 | Rank 4 $\to$ Rank 4 (Invariant) |

### Key Scientific Takeaway
On `CTI-ATTACK`, **the model ranking is 100% robust and invariant**: zero-shot LLM-only remains substantially superior to all RAG configurations, and budget expansion ($B=2000$) outperforms constrained RAG ($B=500$). On `cti-ate`, bidirectional scoring elevates LLM-only to Rank 1 over raw RAG ($E_0'$). The core thesis finding—that zero-shot parametric recall exceeds tight-budget RAG—is strengthened under bidirectional scoring.

---

## 4. Full Verifier Suite Output (`scripts/verify_master.py`)

```
===========================================================================
PHASE 6L: INDEPENDENT SOURCE-OF-TRUTH VERIFIER
===========================================================================

--- SECTION 1: CLAIM RECOMPUTATIONS & EVIDENCE ASSERTIONS ---
  [PASS] | C1_LADDER       | cti-ate raw baseline                | expected 0.1601, got 0.1601
  [PASS] | C1_LADDER       | cti-ate hygiene score               | expected 0.2450, got 0.245
  [PASS] | C1_LADDER       | cti-ate delta (+0.0849)             | got 0.0849
  [PASS] | C1_LADDER       | CTI-ATTACK raw baseline             | expected 0.3064, got 0.3064
  [PASS] | C1_LADDER       | CTI-ATTACK hygiene score            | expected 0.6074, got 0.6074
  [PASS] | C1_LADDER       | CTI-ATTACK delta (+0.3010)          | got 0.3010
  [PASS] | C1_LABEL        | CI/WTL/p labeled unarchived         | ci_ate=from Phase 6B run; per-query data not archived; not re-derivable
  [PASS] | C1_SEMANTIC     | Text 'improves' matches positive deltas | ate delta=+0.0849, att delta=+0.3010
  [PASS] | C1_STATUS       | Status is Robust                    | status=Robust
  [PASS] | C2_ENT          | cti-ate B3 baseline control mean (0.1221) | got 0.1221
  [PASS] | C2_ENT          | cti-ate B3 treatment mean (0.0811)  | got 0.0811
  [PASS] | C2_ENT          | cti-ate B3 delta=-0.0410            | got -0.041
  [PASS] | C2_ENT          | cti-ate B2 baseline control mean (0.0895) | got 0.0895
  [PASS] | C2_ENT          | cti-ate B2 treatment mean (0.0813)  | got 0.0813
  [PASS] | C2_ENT          | cti-ate B2 delta=-0.0082            | got -0.0082
  [PASS] | C2_ENT          | CTI-ATTACK B2 baseline control mean (0.1812) | got 0.1812
  [PASS] | C2_ENT          | CTI-ATTACK B2 treatment mean (0.6303) | got 0.6303
  [PASS] | C2_ENT          | CTI-ATTACK B2 delta=+0.4491         | got 0.4491
  [PASS] | C2_STAT         | cti-ate B3 sign test p=0.0037       | got 0.0037
  [PASS] | C2_STAT         | cti-ate B2 sign test p=0.1516       | got 0.1516
  [PASS] | C2_STAT         | CTI-ATTACK B2 sign test p<0.0001    | got 0.00e+00
  [PASS] | C2_SEMANTIC     | Text states baseline-dependent and cites both B2 and B3 | summary=Enterprise STIX (E0-STIX-ENT): query hygiene effect is baseline-dependent on cti-ate (B3: 0.1221 -> 0.0811, delta -0.0410, p=0.0037; B2: 0.0895 -> 0.0813, delta -0.0082, p=0.1516) and positive under B2 on CTI-ATTACK (0.1812 -> 0.6303, delta +0.4491, p<0.0001)
  [PASS] | C2_STATUS       | Status is Mixed                     | status=Mixed
  [PASS] | C3_B1           | cti-ate delta=+0.0935               | got 0.0935
  [PASS] | C3_B1           | CTI-ATTACK delta=+0.3544            | got 0.3544
  [PASS] | C3_SEMANTIC     | Text 'benefit' matches positive deltas | ate=+0.0935, att=+0.3544
  [PASS] | C3_STATUS       | Status is Robust                    | status=Robust
  [PASS] | C4_GEN          | cti-ate delta=-0.0855               | got -0.08554
  [PASS] | C4_GEN          | CTI-ATTACK delta=+0.0540            | got 0.05401222707423581
  [PASS] | C4_STAT         | cti-ate p=0.0127 (significant negative) | got 0.0127
  [PASS] | C4_STAT         | CTI-ATTACK sign test p=0.3553       | got 0.3553
  [PASS] | C4_SEMANTIC     | Semantic text: hurts cti-ate, mixed on CTI-ATTACK, contains confound note | summary=Downstream generation hygiene (HD vs E0') hurts cti-ate (negative, significant), mixed on CTI-ATTACK (positive mean, CI excludes 0, sign test p=0.355) (confound note: control is k=all, treatment is k=200, so hygiene is confounded with pool size)
  [PASS] | C4_STATUS       | Status is Mixed                     | status=Mixed
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
  [PASS] | C9_DYNAMIC      | Summary text built dynamically with +0.1496 and +0.3516 | summary=Chunk metadata tagging creates artificial recall advantage over text-visible matching (+0.1496 ate / +0.3516 att)
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
  [PASS] | CAPTIONS        | Captions file exists and non-empty  | bytes=2209
  [PASS] | CAPTIONS        | Caption F1 accurately references all 4 regimes | verified

--- SECTION 4: LATEX VS MARKDOWN TABLE CELL VERIFICATION ---
  [PASS] | TEX_EXISTS      | T1_datasets.tex exists and non-empty | size=1468
  [PASS] | TEX_NUM_MATCH   | T1_datasets numbers in md match tex (31 numbers checked) | 100% matched
  [PASS] | TEX_EXISTS      | T2_arms.tex exists and non-empty    | size=1984
  [PASS] | TEX_NUM_MATCH   | T2_arms numbers in md match tex (26 numbers checked) | 100% matched
  [PASS] | TEX_EXISTS      | T3_main_results.tex exists and non-empty | size=3695
  [PASS] | TEX_NUM_MATCH   | T3_main_results numbers in md match tex (138 numbers checked) | 100% matched
  [PASS] | TEX_EXISTS      | T4_statistical_tests.tex exists and non-empty | size=969
  [PASS] | TEX_NUM_MATCH   | T4_statistical_tests numbers in md match tex (48 numbers checked) | 100% matched
  [PASS] | TEX_EXISTS      | T5_detector_precision.tex exists and non-empty | size=1486
  [PASS] | TEX_NUM_MATCH   | T5_detector_precision numbers in md match tex (77 numbers checked) | 100% matched
  [PASS] | TEX_EXISTS      | T6_benchmark_defects.tex exists and non-empty | size=713
  [PASS] | TEX_NUM_MATCH   | T6_benchmark_defects numbers in md match tex (10 numbers checked) | 100% matched

===========================================================================
VERIFICATION SUMMARY: 97 PASSED, 0 FAILED (TOTAL 97 CHECKS)
===========================================================================
ALL CHECKS PASSED PERFECTLY. ZERO DISCREPANCIES.
```

---

## 5. Full Pytest Suite Output

```
....................................................                     [100%]
============================== warnings summary ===============================
src\ragas_patch.py:15
  C:\Users\Akshitha Reddy\OneDrive\Desktop\RAG Intel\src\ragas_patch.py:15: DeprecationWarning: `langchain-community` is being sunset and is no longer actively maintained. See https://github.com/langchain-ai/langchain-community/issues/674 for details and migration guidance toward standalone integration packages.
    import langchain_community.chat_models.vertexai

tests/test_retrieval_determinism.py::test_b3_retrieval_determinism
  C:\Users\Akshitha Reddy\OneDrive\Desktop\RAG Intel\src\retriever.py:51: LangChainDeprecationWarning: The class `HuggingFaceEmbeddings` was deprecated in LangChain 0.2.2 and will be removed in 1.0. An updated version of the class exists in the `langchain-huggingface package and should be used instead. To use it run `pip install -U `langchain-huggingface` and import as `from `langchain_huggingface import HuggingFaceEmbeddings``.
    self.embeddings = HuggingFaceEmbeddings(model_name=self.embedding_model_name)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
52 passed, 2 warnings in 134.92s (0:02:14)
```

---

## 6. Freeze Manifest & Git Tag

- **Manifest Updated**: `results/freeze_manifest.json` updated with `freeze_version: "v1.0-final4"`, 169 tracked files, and SHA-256 signatures for new `results/phase_6l/` sensitivity artifacts and updated `analysis_plan.md`.
- **Git Tag**: Tagged as `v1.0-final4`.
