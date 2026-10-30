# Independent Adversarial Audit Report: RAGIntel Repository

**Auditor Role**: Independent, Adversarial Cybersecurity Thesis & Peer Reviewer  
**Date of Audit**: October 30, 2026  
**Repository State**: Git tag `v1.0-final3` (commit `394943b`), clean working tree  
**Audit Scope**: Comprehensive examination across 8 dimensions (Number Verification, Statistical Methodology, Benchmark Leakage & Validity, Source Code Integrity, Cross-Document Consistency, Frozen Manifest Hashes, Claims vs. Evidence, Priority Remediation).  
**Execution Guardrails**: Strictly offline, zero API invocations, zero edits to frozen artifacts (`results/phase_0` .. `results/phase_6b`).

---

## Executive Summary & Verdict

### Final Verdict: **NOT READY**

While the project exhibits commendable engineering rigor in establishing automated verification pipelines (`verify_master.py`), freezing SHA-256 asset manifests, and resolving historical phantom control bugs, **the repository cannot be approved for thesis defense or publication in its present state**. 

Most critically:
1. **Publication LaTeX Tables Desynchronized**: The LaTeX tables intended for inclusion in the thesis document (`results_for_report/tables/T3_main_results.tex` and `T4_statistical_tests.tex`) still present discredited numbers, erroneous discordant pair counts (W/T/L), invalid statistical tests (pseudo-binomial tests against an arbitrary 50% null; p-values for deterministic scoring gaps), and conflicting Holm multiplicity family structures where non-significant results are marked significant.
2. **Contradictory Prompt Instructions in CTI-ATTACK**: The generation prompt explicitly instructs the LLM: *"Ensure the final line contains only the IDs for the main techniques, separated by commas, excluding any subtechnique IDs."* However, 47.8% of the unique ground truth technique targets in `CTI-ATTACK` are subtechniques (`Txxxx.yyy`), and the scoring metric only credits subtechnique predictions matching parent targets, with zero credit for parent predictions matching subtechnique targets. The benchmark structurally penalizes the model for obeying prompt instructions.
3. **Hardcoded Cells Breaching Rebuild Protocol**: Claim C1's confidence intervals, W/T/L, and p-values are hardcoded in `scripts/build_results_master.py` because no per-query ladder scores file exists in `results/phase_6b/assets/`, violating the Phase 6 source-of-truth rule.
4. **Summary Discrepancies**: Claim C9 in `claims_master.csv` and `RESULTS_MASTER.md` displays stale delta figures (`+0.1556 / +0.3475`) in its prose summary while reporting `+0.1496 / +0.3516` in its data columns.

---

## Complete Audit Findings by Severity

### Summary Table of Findings

| ID | Severity | Category | Target File | Target Cell / Line | Summary |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **CRIT-01** | CRITICAL | Publication Tables | `results_for_report/tables/T3_main_results.tex`, `T4_statistical_tests.tex` | Tables T3 & T4 | Discredited numbers, invalid tests, and wrong Holm families in LaTeX tables |
| **CRIT-02** | CRITICAL | Validity / Prompting | `results/phase_6c/per_query_scores.csv`, `src/retrieval_eval.py` | Query prompt & Scorer | Prompt instructs model to exclude subtechniques, but 47.8% of GT targets are subtechniques |
| **CRIT-03** | CRITICAL | Source-of-Truth | `scripts/build_results_master.py` | Lines 161–166, 302, 317 | Hardcoded C1 CI/WTL/p and C7 Fisher strings violate zero-hand-typed protocol |
| **MAJ-01** | MAJOR | Consistency | `results_for_report/data/claims_master.csv`, `reviews/RESULTS_MASTER.md` | Row C9 | Internal contradiction: summary says `+0.1556/+0.3475`, columns say `+0.1496/+0.3516` |
| **MAJ-02** | MAJOR | Code / Test Harness | `pytest.ini` | Line 2 | Missing `pythonpath = .` causes direct `pytest` invocation to fail with 4 import errors |
| **MAJ-03** | MAJOR | Data Integrity | `data/README.md` | Lines 1–11 | Upstream `enterprise-attack.json` SHA-256 and STIX version contradict on-disk bundle |
| **MAJ-04** | MAJOR | Consistency | `report/figures/F1_hygiene_effect.csv` | Lines 4–9 | Figures directory contains stale CIs (`[-0.0768, -0.0051]` vs `[-0.1033, +0.0293]`) |
| **MAJ-05** | MAJOR | Validity / Controls | `results_for_report/data/claims_master.csv`, `analysis_plan.md` | Row C4 | Confounded control: Treatment ($k=200$) vs Control ($k=\text{all}$) confounds pool size with hygiene |
| **MAJ-06** | MAJOR | Statistics / Baselines | `results_for_report/data/claims_master.csv`, `secondary_kb_contrasts.csv` | Row C2 | Asymmetric baseline selection (B3 on `cti-ate`, B2 on `CTI-ATTACK`) maximizes perceived divergence |
| **MAJ-07** | MAJOR | Methodology | `analysis_plan.md` | Section 18.4 (line 746) | Retrospective generation family ($M=4$) mislabeled as "Pre-Registered" after data was observed |
| **MIN-01** | MINOR | Documentation | `README.md` | Lines 11, 18–28 | Stale status ("Experiments in progress") and cp1252 corrupted tree diagram |
| **MIN-02** | MINOR | Data Formatting | `claims_master.csv`, `RESULTS_MASTER.md` | Row C5 | Non-ASCII encoding artifact: `(Holm *=0.01667)` |
| **MIN-03** | MINOR | Code / Determinism | `src/entity_resolver.py` | Lines 62, 272 | Shared class instance RNG induces query execution order dependency for Variant V3 |
| **MIN-04** | MINOR | Code / Robustness | `src/cache.py` | Line 39 | Bare `except Exception: pass` silently masks corrupted JSON cache records |
| **MIN-05** | MINOR | Consistency | `report/dataset_stats.md` | Line 33 | Contradictory KB version description: claims "v14.1" instead of 2026-07-31 rolling master |
| **MIN-06** | MINOR | Manifest Integrity | `results/freeze_manifest.json` | Manifest Header | 10 files under `results/` (Phase 7 and Phase 6B cache) untracked in freeze manifest |
| **MIN-07** | MINOR | Validity | `results/phase_4b/detector_labels.csv` | `annotator` column | Detector precision evaluated by single unverified annotator without recall measurement |
| **MIN-08** | MINOR | Generalization | `analysis_plan.md`, `data/datasets/` | Dataset specs | Absence of held-out test splits creates test-set tuning and overfitting risks |

---

## Detailed Findings & Evidence

### 1. CRITICAL FINDINGS

#### [CRIT-01] Discredited Numbers, Invalid Tests, and Mismatched Multiplicity Families in Publication-Ready LaTeX Tables
- **Files**: `results_for_report/tables/T3_main_results.tex`, `results_for_report/tables/T4_statistical_tests.tex`
- **Cell / Line**: Table T3 (lines 6–15) and Table T4 (lines 5–8)
- **Evidence**:
  While Phase 6I, 6J, and 6K updated the Markdown tables (`T3_main_results.md`, `T4_statistical_tests.md`), the corresponding `.tex` files intended for thesis typesetting were completely neglected. Inspecting `T3_main_results.tex` reveals:
  - **Claim C2**: Reports W/T/L as `1/53/6 (ate B3) / 128/91/10 (att B2)` and CI as `[-0.0768, -0.0051]`. The verified master values from `secondary_kb_contrasts.csv` are W/T/L `6/32/22 / 117/104/8` and CI `[-0.1033, +0.0293]`.
  - **Claim C3**: Reports `CTI-ATTACK` W/T/L as `139/72/18` instead of `90/137/2`.
  - **Claim C7**: Reports invalid pooled test `<0.001 (Fisher exact on leaked vs clean)` instead of the per-arm exact values (`0.0445, 0.0366, 0.0463, 0.0920`).
  - **Claim C8**: Reports `<0.0001 (Binomial test against null 50%)`, an invalid test against an arbitrary 50% null explicitly ordered removed in Phase 6I.
  - **Claim C9**: Reports `<0.0001 / <0.0001` for deterministic scoring divergence, explicitly ordered deleted.
  - **Claim C10**: Reports obsolete p-values `0.0031` and `<0.0001` instead of `0.0704` and `0.0008`.
  - **Table T4 (`T4_statistical_tests.tex`)**: Defines Primary Generation ($M=4$) family with `GEN_03` and `GEN_04` as HD vs E0' (Raw), claiming `GEN_04` is significant under Holm (`p=0.012660 <= 0.050000`). This directly contradicts `T4_statistical_tests.md` and `analysis_plan.md` Section 19/20 where `GEN_03` and `GEN_04` are `cti-taa` controls ($p=1.0$), and HD vs E0' is segregated into post-hoc exploratory hygiene ($M=2$).
- **One-Line Fix**: Extend `scripts/build_results_master.py` to regenerate all `.tex` tables programmatically alongside `.md` tables to ensure absolute synchronization.

#### [CRIT-02] Prompt-Evaluation Metric Contradiction Penalizes Model for Obeying Instructions in CTI-ATTACK
- **Files**: `results/phase_6c/per_query_scores.csv` (column `query`), `src/retrieval_eval.py` (lines 69–77), `scripts/compute_phase6c_metrics.py` (lines 53–62)
- **Cell / Line**: Column `query` in `per_query_scores.csv` across all rows; `compute_technique_f1()` in `compute_phase6c_metrics.py`
- **Evidence**:
  The system prompt delivered to the generation model across all `CTI-ATTACK` and `cti-ate` queries explicitly commands:
  > *"Extract all MITRE Enterprise attack patterns from the following text and map them to their corresponding MITRE technique IDs. Provide reasoning for each identification. Ensure the final line contains only the IDs for the main techniques, separated by commas, excluding any subtechnique IDs."*
  
  However, in `CTI-ATTACK`:
  - 55 of 115 unique ground truth technique targets (47.8%) are subtechniques (`Txxxx.yyy`).
  - 324 of 687 evaluations (47.2%) possess ground truth sets containing subtechniques.
  - The evaluation function `compute_technique_f1` computes `r_sub = tp_sub / len(gt_techs)`. It expands predicted subtechniques to parents (`credited_pred.add(t.split(".")[0])`), but **does not expand parent predictions to subtechnique ground truths**.
  
  Consequently, when the model obeys the prompt and outputs `T1059` instead of `T1059.001`, `tp_sub` receives 0 credit. The generator is penalized for following the prompt's explicit negative constraint, creating an artificial performance ceiling below 0.55 recall on nearly half the dataset.
- **One-Line Fix**: Update the generation prompt to permit subtechnique IDs, or adjust `compute_technique_f1` to evaluate bidirectional hierarchical credit where parent predictions satisfy subtechnique ground truth.

#### [CRIT-03] Hardcoded Numbers in `build_results_master.py` Violate Zero-Hand-Typed Source-of-Truth Protocol
- **File**: `scripts/build_results_master.py`
- **Cell / Line**: Lines 103–111, 161–166, 302, 317
- **Evidence**:
  Phase 6 Rule 2 explicitly dictates: *"NEVER type a number by hand into a report, table, caption or figure. Every number must be loaded by key in code (scripts/build_results_master.py) and written out by that code."*
  However, in `scripts/build_results_master.py`:
  ```python
  # Lines 161-166
  "ci_ate": fmt_ci(0.0382, 0.1315),
  "ci_att": fmt_ci(0.2520, 0.3500),
  "wtl_ate": "29/21/10",
  "wtl_att": "175/27/27",
  "p_ate": fmt_p(0.0034),
  "p_att": fmt_p(0.0000),
  ```
  These values are hand-typed literals. The source CSV `results/phase_6b/assets/table_ladder_common_budgets.csv` contains only aggregate Mean Recall@B, not per-query rows or bootstrap replicates. No per-query scores file exists in `results/phase_6b/assets/`, preventing independent verification of these bootstrap statistics. Furthermore, lines 302 and 317 hardcode the Fisher exact string (`"LLM-only=0.0445, V0=0.0366, V0h=0.0463, Vrel=0.0920"`) rather than computing it from partition arrays.
- **One-Line Fix**: Export the per-query ladder scores to `results/phase_6b/assets/` to allow programmatic bootstrap computation, and compute Fisher exact tests dynamically via `scipy.stats.fisher_exact`.

---

### 2. MAJOR FINDINGS

#### [MAJ-01] Internal Contradiction in Claim C9 Summary vs Data Columns
- **Files**: `results_for_report/data/claims_master.csv` (row C9), `reviews/RESULTS_MASTER.md` (row C9)
- **Cell / Line**: Summary text vs `delta_ate` and `delta_att` columns
- **Evidence**:
  In `claims_master.csv` and `RESULTS_MASTER.md`, Claim C9 summary states:
  > `"Chunk metadata tagging creates artificial recall advantage over text-visible matching (+0.1556 ate / +0.3475 att)"`
  
  Yet in the exact same row, the reported metric deltas are:
  > `delta_ate = +0.1496`, `delta_att = +0.3516`
  
  The numbers in the summary are leftover relics from Phase 6E that contradict the actual data columns derived from `results/phase_6d/metadata_credit_audit.json`.
- **One-Line Fix**: In `scripts/build_results_master.py` line 352, dynamically format the summary string using the loaded JSON keys (`mc_ate_hd['discrepancy_delta']` and `mc_att_hd['discrepancy_delta']`).

#### [MAJ-02] Missing `pythonpath = .` in `pytest.ini` Prevents Direct Test Execution
- **File**: `pytest.ini`
- **Cell / Line**: Line 2
- **Evidence**:
  Executing standard `pytest` or `pytest -q` from the root directory fails immediately with 4 collection errors:
  `ModuleNotFoundError: No module named 'src'` in `test_attribution_scorer_spec.py`, `test_chunking.py`, `test_config.py`, and `test_data_loader.py`. Only invoking via `python -m pytest` succeeds because `pytest.ini` fails to define `pythonpath = .`.
- **One-Line Fix**: Add `pythonpath = .` beneath `[pytest]` in `pytest.ini`.

#### [MAJ-03] Knowledge Base Bundle Checksum and Version Mismatch in `data/README.md`
- **Files**: `data/README.md` lines 1–11, `data/mitre/enterprise-attack.json`, `analysis_plan.md` line 769
- **Cell / Line**: Table row 1 in `data/README.md`
- **Evidence**:
  `data/README.md` instructs users to verify `enterprise-attack.json` against SHA-256 `f7eaf37fe53b50404084fe1fe67237278f7317e61c11ad550295722d13ede259` (size: 47,953,963 bytes).
  However, the actual bundle used by the repository on disk has SHA-256 `66f3fe3f07ef1a2de0bd2fe4b3e8a9ea06c1d0bb2c46171bdbb57c7f7b666524` and size 49,253,343 bytes (the July 31, 2026 rolling master containing the S9000-series objects documented in `analysis_plan.md` Section 18.6). Any third party downloading the bundle according to `data/README.md` will fail checksum verification.
- **One-Line Fix**: Update `data/README.md` with the verified July 31, 2026 hash and size, and update the heading from STIX 2.0 to STIX 2.1.

#### [MAJ-04] Stale Confidence Intervals in Publication Figures Directory (`report/figures/`)
- **Files**: `report/figures/F1_hygiene_effect.csv`, `results_for_report/figures/F1_hygiene_effect.csv`
- **Cell / Line**: Rows 3–8 in `report/figures/F1_hygiene_effect.csv`
- **Evidence**:
  While `results_for_report/figures/` was rebuilt during Phase 6J, the publication directory `report/figures/` was left un-synchronized:
  - Enterprise STIX `cti-ate` CI is recorded as `[-0.0768, -0.0051]` instead of `[-0.1033, +0.0293]`.
  - Enterprise STIX `CTI-ATTACK` CI is recorded as `[0.3850, 0.5132]` instead of `[+0.3785, +0.5168]`.
  - Downstream Generation `cti-ate` CI is recorded as `[-0.1555, -0.0163]` instead of `[-0.1356, -0.0386]`.
  - Downstream Generation `CTI-ATTACK` CI is recorded as `[-0.0570, +0.1659]` instead of `[+0.0069, +0.1027]`.
- **One-Line Fix**: Copy all updated CSV, PNG, and SVG artifacts from `results_for_report/figures/` into `report/figures/`.

#### [MAJ-05] Confounded Control Comparison in Live Generation Hygiene (Claim C4)
- **Files**: `results_for_report/data/claims_master.csv` (row C4), `analysis_plan.md` Section 18.2
- **Cell / Line**: Control vs Treatment specification for C4
- **Evidence**:
  Claim C4 compares Treatment `E0'-HD-k200` ($B=500, k=200$) against Control `True Raw E0'` ($B=500, k=\text{all}$).
  This comparison simultaneously introduces two experimental changes: (1) query hygiene and domain routing, and (2) candidate chunk pool truncation ($k=200$ vs unfiltered $k=\text{all}$).
  Because the control does not isolate pool size ($k=200$ without hygiene), the observed performance drop on `cti-ate` ($\Delta = -0.0855$) cannot be strictly causally attributed to hygiene alone; pool truncation may contribute to the loss of relevant chunks.
- **One-Line Fix**: Document in Claim C4 and the thesis methodology that candidate pool truncation ($k=200$ vs $k=\text{all}$) is a confounding factor alongside query hygiene.

#### [MAJ-06] Asymmetric Baseline Selection in Claim C2 Cherry-Picks Maximum Divergence
- **Files**: `results_for_report/data/claims_master.csv` (row C2), `results/phase_6d/secondary_kb_contrasts.csv`
- **Cell / Line**: Baseline selection across datasets
- **Evidence**:
  In Claim C2, the author evaluates Enterprise STIX hygiene by selecting Baseline B3 (MaxSim sliding windows) on `cti-ate`, but Baseline B2 (Truncated 256) on `CTI-ATTACK`.
  Checking `secondary_kb_contrasts.csv` reveals that under Baseline B2 on `cti-ate`, query hygiene is statistically indistinguishable from zero ($\Delta = -0.0082, p = 0.1516$). Only under B3 does `cti-ate` show a statistically significant decrease ($\Delta = -0.0410, p = 0.0037$).
  Conversely, on `CTI-ATTACK`, where queries average 62 tokens (well below the 256 truncation boundary), B2 and B3 are mathematically identical ($\Delta = +0.4491, p < 0.0001$). Selecting B3 for one dataset and B2 for the other creates an artificial appearance of dramatic opposition that does not exist under a uniform B2 baseline.
- **One-Line Fix**: Disclose in the main results table that the negative hygiene effect on `cti-ate` is baseline-dependent and null under B2 ($p=0.1516$).

#### [MAJ-07] Retrospective Generation Family ($M=4$) Mislabeled as "Pre-Registered"
- **File**: `analysis_plan.md`
- **Cell / Line**: Section 18.4 (line 746)
- **Evidence**:
  Section 18.4 (dated 2026-10-26 in Phase 6H) heads its discussion: `"1. Pre-Registered Family Definitions: GEN_01 and GEN_02 are pre-registered as HD vs LLM-only (technique f1_sub)..."`.
  However, Phase 6C generation metrics were executed and analyzed on 2026-10-25 (`compute_phase6c_metrics.py`). The true pre-registered analysis plan from 2026-10-19 (Sections 1–3) only pre-registered Phase 2 retrieval tests on `cti-taa`. Defining an $M=4$ family after observing Phase 6C results and calling it "pre-registered" risks accusations of retroactive p-hacking from committee members.
- **One-Line Fix**: Rename Section 18.4 to "Post-Hoc Confirmatory Generation Family ($M=4$)" and explicitly document that this multiplicity family was constructed retrospectively following Phase 6C.

---

### 3. MINOR FINDINGS

#### [MIN-01] Stale Project Status and Encoding Corruption in `README.md`
- **File**: `README.md`
- **Cell / Line**: Lines 11, 18–28
- **Evidence**: Line 11 states `Experiments in progress, see reviews/api_status.md`, whereas the repository has achieved frozen tag `v1.0-final3`. Furthermore, the directory tree diagram contains corrupted characters (`"o"?"?`) resulting from cp1252/utf-8 transcoding errors.
- **One-Line Fix**: Update project status to "Release v1.0 Frozen" and re-encode directory tree using clean UTF-8 box characters.

#### [MIN-02] Character Encoding Artifact in Multiplicity Threshold Notation
- **Files**: `results_for_report/data/claims_master.csv` (row C5), `reviews/RESULTS_MASTER.md` (row C5)
- **Cell / Line**: Column `p_ate` and `p_att`
- **Evidence**: The string `0.01983 (Holm *=0.01667, Not Sig)` contains an unmapped replacement character `*` instead of `\alpha^*` or `alpha*`.
- **One-Line Fix**: Replace `alpha*` with `alpha*` in `scripts/build_results_master.py` lines 271–272.

#### [MIN-03] Instance-Level PRNG State Induces Execution Order Dependency in `EntityResolver`
- **File**: `src/entity_resolver.py`
- **Cell / Line**: Lines 62, 272
- **Evidence**: `self.rng = random.Random(random_seed)` is instantiated on the `EntityResolver` instance and mutated during each call to `expand_query()` for Variant V3. If queries are evaluated out of order or as a subset, the random entity ablations change.
- **One-Line Fix**: Seed a per-query PRNG instance deterministically (e.g., `rng = random.Random(self.random_seed + query_idx)`).

#### [MIN-04] Bare Exception Handler in `src/cache.py` Silently Swallows Corrupted Cache Records
- **File**: `src/cache.py`
- **Cell / Line**: Line 39
- **Evidence**: `except Exception: pass` catches JSON decoding errors and treats corrupted cache files as cache misses, masking on-disk data truncation.
- **One-Line Fix**: Add a warning logger emitting the filepath whenever a cache read raises `json.JSONDecodeError`.

#### [MIN-05] Discrepant Knowledge Base Provenance Description in `report/dataset_stats.md`
- **File**: `report/dataset_stats.md`
- **Cell / Line**: Line 33
- **Evidence**: Identifies the knowledge base as "MITRE ATT&CK v14.1", whereas `analysis_plan.md` Section 18.6 specifies it as an unversioned rolling master snapshot dated 2026-07-31 containing unreleased draft objects (S9000-series).
- **One-Line Fix**: Align `report/dataset_stats.md` line 33 to state "MITRE ATT&CK STIX 2.1 rolling master snapshot (2026-07-31)".

#### [MIN-06] Untracked Files under `results/` Omitted from `freeze_manifest.json`
- **File**: `results/freeze_manifest.json`
- **Cell / Line**: Manifest `files` object
- **Evidence**: 10 files under `results/` are not tracked in `freeze_manifest.json`: 8 files in `results/phase_7/`, `results/phase_6b/raw_k200_cache.json`, and `freeze_manifest.json` itself.
- **One-Line Fix**: Annotate in `analysis_plan.md` that Phase 7 constitutes exploratory post-v1.0 work excluded from the frozen manifest.

#### [MIN-07] Single-Annotator Detector Precision Sample Lacks Recall Measurement
- **Files**: `results/phase_4b/detector_labels.csv`, `reviews/RESULTS_MASTER.md` (row C8)
- **Cell / Line**: Row C8
- **Evidence**: Detector precision (74.0% raw, 93.9% filtered) was derived from a single annotator (`annotator = claude_draft_unverified`) across 100 sample detections. Detector recall was not evaluated, and no inter-annotator agreement score (Cohen's $\kappa$) was computed.
- **One-Line Fix**: Add an explicit caveat in the detector precision section highlighting that the sample is single-annotator and unverified for recall.

#### [MIN-08] Lack of Train/Validation/Test Splits Creates Risk of Test-Set Tuning
- **Files**: `analysis_plan.md`, `data/datasets/`
- **Evidence**: Across all three benchmark datasets (`cti-ate` $N=60$, `CTI-ATTACK` $N=229$, `cti-taa` $N=50$), no held-out validation splits were maintained. Key pipeline parameters—including token budgets $B^*=500$, pool depth $k^*=200$, entity detector survival stoplists, and prompt templates—were optimized and tested on the identical query sets.
- **One-Line Fix**: Note in the thesis limitations section that the small sample size precluded independent test splits, warranting future validation on unseen threat intelligence feeds.

---

## Detailed Audit Dimensions

### 1. Number Audit
- **Recomputation**: All deltas, 95% bootstrap confidence intervals (10,000 resamples, seed 42), win/tie/loss discordant pairs, and exact two-sided binomial sign test p-values were independently verified against source CSV/JSON files.
- **Findings**:
  - Claims C2, C3, C4, C5, C6, C8, and C10 match programmatic source data in JSON/CSV within $\pm 0.0005$.
  - C1 bootstrap confidence intervals and discordant pairs could not be recomputed independently from `table_ladder_common_budgets.csv` due to the lack of per-query records in that directory ([CRIT-03]).
  - C9 exhibits an internal contradiction between summary text (`+0.1556 / +0.3475`) and data columns (`+0.1496 / +0.3516`) ([MAJ-01]).
  - Publication LaTeX table `T3_main_results.tex` contains widespread numeric mismatches ([CRIT-01]).

### 2. Statistics Audit
- **Test Appropriateness**: Binomial sign tests on discordant pairs correctly exclude ties. The previously reported invalid tests (pooled Fisher $<0.001$ for C7, binomial test against 50% null for C8, and p-value for deterministic scoring difference in C9) were correctly excised from Markdown/CSV outputs, but remain active in `T3_main_results.tex` ([CRIT-01]).
- **Multiplicity Control**:
  - The Primary Generation ($M=4$) Holm family in `holm_primary_generation.json` is correctly sorted by ascending raw p-values (`0.00068, 0.01983, 1.0, 1.0`) with proper step-down thresholds (`0.0125, 0.01667, 0.025, 0.05`).
  - However, `T4_statistical_tests.tex` presents an older, conflicting family structure where HD vs E0' is included in the primary family and marked significant ([CRIT-01]).
  - The generation family was formulated retrospectively on October 26 after viewing Phase 6C data from October 25, despite being labeled "Pre-Registered" ([MAJ-07]).

### 3. Leakage & Validity Audit
- **Alias Leakage**: 10 of 50 queries (20.0%) in `cti-taa` leak canonical adversary aliases in the query body. Establishing the Clean-40 subset properly mitigates this, though Clean-40 findings must be recognized as post-hoc.
- **Prompt Validity**: The prompt template in `CTI-ATTACK` instructs models to exclude subtechnique IDs, while nearly half the ground truth comprises subtechniques and the evaluation metric fails to award credit for parent predictions ([CRIT-02]).
- **Confounded Arms**: Claim C4 confounds query hygiene with candidate pool truncation ($k=200$ vs $k=\text{all}$) ([MAJ-05]).

### 4. Code & Test Suite Audit
- **Pytest**: All 52 unit and integration tests passed in offline mode (`52 passed, 2 warnings in 132.96s`). However, running `pytest` directly fails unless `pythonpath = .` is supplied in `pytest.ini` ([MAJ-02]).
- **Determinism**: Isolated PRNG instances (`np.random.default_rng(42)`) are employed across bootstrap and retrieval modules, but `EntityResolver` shares instance state across queries ([MIN-03]).

### 5. Consistency Audit
- **Grep Verification**: Zero occurrences of historical discredited values (`0.2797, 0.2762, 0.2387, 0.7253`) remain in active Markdown or CSV summaries.
- **Cross-Directory Drift**: LaTeX tables in `results_for_report/tables/` and CSVs in `report/figures/` are severely desynchronized from `results_for_report/` ([CRIT-01], [MAJ-04]).

### 6. Frozen Integrity Audit
- **Manifest Verification**: Evaluated all 167 files tracked in `results/freeze_manifest.json`.
- **Result**: Exactly 167 files matched on-disk hashes (157 matched exact raw byte SHA-256; 10 matched LF-normalized SHA-256). Zero files modified without authorization.
- **Untracked Artifacts**: 10 files in `results/` are untracked (Phase 7 and Phase 6B cache) ([MIN-06]).

### 7. Claims vs. Evidence Audit
- **Claim C1**: Supported by aggregate ladder CSV, but lacks per-query bootstrap source artifact ([CRIT-03]).
- **Claim C2**: Supported by CSV, but baseline selection is asymmetric (B3 vs B2) ([MAJ-06]).
- **Claim C3**: Supported by `b1_robustness_contrasts.csv`.
- **Claim C4**: Supported by `generation_contrasts.json`, but contains pool truncation confound ([MAJ-05]).
- **Claim C5**: Supported by JSON, but conflicting in LaTeX table and formulated post-hoc ([CRIT-01], [MAJ-07]).
- **Claim C6**: Supported on Clean-40 subset.
- **Claim C7**: Supported by audit JSON, but hardcoded in builder script ([CRIT-03]).
- **Claim C8**: Supported by single-annotator sample; lacks recall measurement ([MIN-07]).
- **Claim C9**: Supported by audit JSON, but summary prose contradicts data columns ([MAJ-01]).
- **Claim C10**: Supported by `generation_contrasts.json`.

---

## Top 10 Priority Fixes for Defense Readiness

In order of severity and impact on academic credibility:

1. **Synchronize LaTeX Publication Tables (`CRIT-01`)**:
   Modify `scripts/build_results_master.py` to compile and write `T3_main_results.tex`, `T4_statistical_tests.tex`, and `T6_benchmark_defects.tex` directly from source CSV/JSON, eliminating obsolete numbers and invalid tests from the thesis LaTeX source.
2. **Resolve Prompt-Metric Contradiction in CTI-ATTACK (`CRIT-02`)**:
   Align the generation prompt with the scoring harness by either allowing subtechnique IDs in prompt instructions or updating `compute_technique_f1()` to award bidirectional credit when parent technique predictions match subtechnique GT targets.
3. **Eliminate Hardcoded Literals in Builder Script (`CRIT-03`)**:
   Output per-query ladder scores to `results/phase_6b/assets/` to enable dynamic bootstrap CI computation for C1, and compute Fisher exact tests for C7 dynamically in `scripts/build_results_master.py`.
4. **Fix Internal Prose Contradiction in Claim C9 (`MAJ-01`)**:
   Update `scripts/build_results_master.py` line 352 to dynamically format the C9 summary string with `{mc_ate_hd['discrepancy_delta']:.4f}` and `{mc_att_hd['discrepancy_delta']:.4f}`.
5. **Add `pythonpath = .` to `pytest.ini` (`MAJ-02`)**:
   Add `pythonpath = .` to `pytest.ini` so that standard `pytest` runs cleanly without requiring `python -m pytest`.
6. **Correct Upstream Knowledge Base Checksums in `data/README.md` (`MAJ-03`)**:
   Update `data/README.md` with the verified SHA-256 (`66f3fe3f07ef...`) and size (49,253,343 bytes) of `data/mitre/enterprise-attack.json`, and designate the specification as STIX 2.1.
7. **Synchronize Figures Directory (`MAJ-04`)**:
   Copy the reconciled CSVs, PNGs, and SVGs from `results_for_report/figures/` into `report/figures/` to eliminate stale confidence intervals.
8. **Disclose Architectural Confounds in Claim C4 (`MAJ-05`)**:
   Update the discussion of Claim C4 in `analysis_plan.md` and thesis text to acknowledge that candidate pool truncation ($k=200$ vs $k=\text{all}$) is confounded with query hygiene.
9. **Disclose Baseline Asymmetry in Claim C2 (`MAJ-06`)**:
   Report both Baseline B2 and B3 for `cti-ate` in Claim C2, clarifying that query hygiene under B2 on `cti-ate` is statistically null ($p=0.1516$).
10. **Reclassify Generation Multiplicity Family as Post-Hoc (`MAJ-07`)**:
    Change the header of `analysis_plan.md` Section 18.4 from "Pre-Registered" to "Post-Hoc Confirmatory Generation Family ($M=4$)" to preserve academic honesty regarding pre-registration timelines.

