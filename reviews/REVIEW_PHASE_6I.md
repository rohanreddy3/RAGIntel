# Phase 6I Review: Source-of-Truth Rebuild, Multiplicity Corrections, and Final Freeze

**Date**: 2026-10-30  
**Status**: Certified & Verified Offline (Zero API Calls)  
**Execution**: Lead Engineer Source-of-Truth Audit & Repository Freeze  
**Branch**: `main` | **Tag**: `v1.0-final`

---

## Executive Summary

Phase 6I constitutes the final source-of-truth rebuild, rigorous cross-check verification, and freeze of the RAGIntel project. Operating under strict protocol—relying solely on per-query raw result files and canonical CSV/JSON artifacts under `results/` and `.cache/api_runner/`—every metric, confidence interval, discordant pair count (W/T/L), and $p$-value was recomputed programmatically via a single master script (`scripts/build_results_master.py`). Zero hand-typed values exist in any report, table, caption, or figure.

A companion verification script (`scripts/verify_master.py`) re-reads each canonical source and performs independent assertions across every claim cell, calculating exact two-sided binomial sign test $p$-values via `scipy.stats.binomtest` for all discordant pairs. All 48 programmatic checks **PASSED** with zero discrepancies.

---

## 1. Automated Cross-Check Verification Output (`scripts/verify_master.py`)

Below is the verbatim raw console output of `scripts/verify_master.py`:

```
======================================================================
Phase 6I Cross-Check: 48 PASS, 0 FAIL
======================================================================
  [PASS] [OK] C1.cti-ate.wtl: expected=8/36/16, actual=8/36/16
  [PASS] [OK] C1.CTI-ATTACK.wtl: expected=117/104/8, actual=117/104/8
  [PASS] [OK] C2.B3.cti-ate.wtl: expected=6/32/22, actual=6/32/22
  [PASS] [OK] C2.B3.cti-ate.ci_lo: expected=-0.1033, actual=-0.1033
  [PASS] [OK] C2.B3.cti-ate.ci_hi: expected=0.0293, actual=0.0293
  [PASS] [OK] C2.B3.cti-ate.binomtest_p: expected=0.0037, actual=0.0037191659212112427
  [PASS] [OK] C2.CTI-ATTACK.B2.wtl: expected=117/104/8, actual=117/104/8
  [PASS] [OK] C2.CTI-ATTACK.B2.binomtest_p: expected=0.0, actual=5.928488920821206e-26
  [PASS] [OK] C3.CTI-ATTACK.wtl: expected=90/137/2, actual=90/137/2
  [PASS] [OK] C3.CTI-ATTACK.binomtest_p: expected=0.0, actual=1.7282743364816433e-24
  [PASS] [OK] C4.cti-ate.ci_lo: expected=-0.1356, actual=-0.1356
  [PASS] [OK] C4.cti-ate.ci_hi: expected=-0.0386, actual=-0.0386
  [PASS] [OK] C4.CTI-ATTACK.ci_lo: expected=0.0069, actual=0.0069
  [PASS] [OK] C4.CTI-ATTACK.ci_hi: expected=0.1027, actual=0.1027
  [PASS] [OK] C4.cti-ate.binomtest_p: expected=0.0127, actual=0.012660335802414213
  [PASS] [OK] C5.GEN_01.binomtest_calc: expected=0.01983, actual=0.01983432672806828
  [PASS] [OK] C5.GEN_01.p_raw: expected=0.01983, actual=0.01983
  [PASS] [OK] C5.GEN_01.holm_threshold: expected=0.01667, actual=0.01667
  [PASS] [OK] C5.GEN_01.reject: expected=False, actual=False
  [PASS] [OK] C5.GEN_02.binomtest_calc: expected=0.00068, actual=0.0006846086250425259
  [PASS] [OK] C5.GEN_02.p_raw: expected=0.00068, actual=0.00068
  [PASS] [OK] C5.GEN_02.reject: expected=True, actual=True
  [PASS] [OK] Holm.sorted_by_p: expected=True, actual=True
  [PASS] [OK] C6.delta_ret: expected=0.2, actual=0.2
  [PASS] [OK] C6.wtl_ret: expected=8/32/0, actual=8/32/0
  [PASS] [OK] C6.binomtest_p: expected=0.0078125, actual=0.0078125
  [PASS] [OK] C7.leaked_count: expected=10, actual=10
  [PASS] [OK] C7.clean_count: expected=40, actual=40
  [PASS] [OK] C8.no_p_value: expected=N/A (counts only; no valid binomial null), actual=N/A (counts only; no valid binomial null)
  [PASS] [OK] C9.cti-ate.delta: expected=0.1496, actual=0.1496
  [PASS] [OK] C9.CTI-ATTACK.delta: expected=0.3516, actual=0.3516
  [PASS] [OK] C9.no_p_value: expected=N/A (deterministic scoring discrepancy; no valid test), actual=N/A (deterministic scoring discrepancy; no valid test)
  [PASS] [OK] C10.cti-ate.p_sign: expected=0.0704, actual=0.0704
  [PASS] [OK] C10.cti-ate.wtl: expected=33/8/19, actual=33/8/19
  [PASS] [OK] C10.cti-ate.binomtest_calc: expected=0.0704, actual=0.07039422106706228
  [PASS] [OK] C10.CTI-ATTACK.wtl: expected=60/141/28, actual=60/141/28
  [PASS] [OK] C10.CTI-ATTACK.binomtest_calc: expected=0.0008, actual=0.000846496085616675
  [PASS] [OK] C10.D4.cti-ate.delta: expected=0.0354, actual=0.0354
  [PASS] [OK] C10.D4.cti-ate.p_sign: expected=0.6778, actual=0.6778
  [PASS] [OK] C10.D4.cti-ate.binomtest_calc: expected=0.6778, actual=0.6778086391424605
  [PASS] [OK] arm_means.LLM_ate.f1_sub: expected=0.4634, actual=0.4634
  [PASS] [OK] arm_means.LLM_att.f1_sub: expected=0.3964, actual=0.3964
  [PASS] [OK] arm_means.HD_ate.f1_sub: expected=0.3936, actual=0.3936
  [PASS] [OK] arm_means.HD_att.f1_sub: expected=0.2994, actual=0.2994
  [PASS] [OK] arm_means.LLM_taa.v2_alias: expected=0.72, actual=0.72
  [PASS] [OK] arm_means.LLM_taa.v1_alias: expected=0.68, actual=0.68
  [PASS] [OK] headline.sec_gen.LLM.full50: expected=0.66, actual=0.66
  [PASS] [OK] headline.sec_gen.LLM.clean40: expected=0.575, actual=0.575

All 48 checks PASSED.
```

---

## 2. Comprehensive Discrepancy & Reconciliation Ledger

In accordance with Phase 6I Rule 7 (*"Report every discrepancy you find as: file, old value, new value, source file. Do not hide a discrepancy"*), the following discrepancies across prior phase documentation were audited, traced to canonical source artifacts, and permanently rectified:

| Identifier | File Affected | Stale / Discrepant Value | Certified True Value | Canonical Source Artifact | Resolution Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **C2 (ate B3 W/T/L)** | `RESULTS_MASTER.md` | `1/53/6` | **`6/32/22`** | `results/phase_6d/secondary_kb_contrasts.json` | Prior reporting conflated B2 tie counts with B3. Correct discordant pairs: 6 wins, 22 losses ($N=28$). |
| **C2 (ate B3 CI)** | `RESULTS_MASTER.md` | `[-0.0768, -0.0051]` | **`[-0.1033, +0.0293]`** | `results/phase_6d/secondary_kb_contrasts.json` | 95% bootstrap CI on B3 Enterprise STIX subtechnique recall crosses zero; exact sign test $p=0.0037$. |
| **C2 (att B2 W/T/L)** | `RESULTS_MASTER.md` | `128/91/10` | **`117/104/8`** | `results/phase_6d/secondary_kb_contrasts.json` | Rectified to exact query counts under E0-STIX-ENT B2 query hygiene on CTI-ATTACK ($N=229$). |
| **C3 (att B1 W/T/L)** | `RESULTS_MASTER.md` | `139/72/18` | **`90/137/2`** | `results/phase_6d/b1_robustness_contrasts.csv` | Prior table transcribed unchunked baseline row without deduplication. Verified from frozen B1 contrasts CSV. |
| **C4 (att CI)** | `RESULTS_MASTER.md` | `[-0.0570, +0.1659]` | **`[+0.0069, +0.1027]`** | `results/phase_6c/contrasts_table.json` | Prior report transcribed uncorrected bootstrap interval. Paired bootstrap CI on live Live F1 reflects verified bounds. |
| **C5 (GEN_01 p & decision)** | `REVIEW_PHASE_6D.md` A3, `RESULTS_MASTER.md` | `p=0.0014`, Reject Null | **`p=0.01983`**, Fail to Reject Null | `results/phase_6d/holm_primary_generation.json` | Historical `0.0014` was a bootstrap $p$-value. Exact sign test on 54 discordant pairs yields $0.01983 > 0.01667$. |
| **C7 (Leakage Fisher p)** | `RESULTS_MASTER.md` | `<0.001` (pooled) | **Exact per-arm** ($p=0.0465, 0.0850, 0.1687$) | `results/phase_6d/gt_alias_leakage_audit.json` | Removed invalid pooled test. Computed exact two-sided Fisher test between leaked-10 and clean-40 per arm. |
| **C8 (Detector Precision p)**| `RESULTS_MASTER.md` | `<0.0001` | **N/A (Counts only)** | `results/phase_6d/phase6g_corrections.json` | Deleted pseudo-hypothesis binomial test against arbitrary 50% null; reported counts ($62/66 = 93.9\%$). |
| **C9 (Metadata Credit p)** | `RESULTS_MASTER.md` | `<0.0001` | **N/A (Difference only)** | `results/phase_6d/metadata_credit_audit.json` | Deleted pseudo $p$-value for deterministic scoring divergence; reported discrepancy $+0.1496$ and $+0.3516$. |
| **C10 (ate D1 W/T/L & p)** | `RESULTS_MASTER.md` | `31/18/11`, $p=0.0031$ | **`33/8/19`**, $p=0.0704$ | `results/phase_6d/generation_contrasts.json` | Stale draft table had incorrect query pairing. Correct sign test $p=0.0704$ on 52 discordant pairs. |
| **C10 (att D1 W/T/L & p)** | `RESULTS_MASTER.md` | `121/70/38`, $p<0.0001$| **`60/141/28`**, $p=0.0008$ | `results/phase_6d/generation_contrasts.json` | Live generation contrast D1 vs P6C HD on CTI-ATTACK re-asserted from canonical contrasts JSON. |
| **C10 (ate D4 vs HD)** | `RESULTS_MASTER.md` | Missing / untracked | **`+0.0354`**, $p=0.6778$ | `results/phase_6d/generation_contrasts.json` | Verified D4 Hybrid ($B=2000$) technique F1 on `cti-ate`: 0.4290 vs 0.3936, W/T/L 28/8/24, sign $p=0.6778$. |
| **Headline LLM-only Acc** | `RESULTS_MASTER.md`, `REVIEW_PHASE_6G.md` | `0.6800` | **`0.7200`** | `results/phase_6d/phase6g_corrections.json` | 0.6800 was $v_1\text{-alias}$ accuracy; primary benchmark metric is $v_2\text{-alias}$ (0.7200 on Full-50). |
| **Headline 2nd-Gen V0** | `RESULTS_MASTER.md` | Omitted / inconsistent | **Full: `0.6600`**, Clean: **`0.5750`** | `results/phase_6d/phase6g_corrections.json` | Reconciled secondary generator `gemini-3.1-flash-lite` V0 attribution accuracy from Part F logs. |
| **SysUpdate STIX ID** | `REVIEW_PHASE_6D.md` Case 26 | `S0434` | **`S0663`** | `data/mitre/enterprise-attack.json` | S0434 was a transcription error. Exact external_id in upstream STIX bundle is S0663. |
| **S9000-Series Examples** | `REVIEW_PHASE_6G.md` Sec 7.2 | `S9001 XWorm`, `S9008 Cobalt Strike` | **`S9001 SystemBC`**, **`S9008 Shai-Hulud`** | `results/phase_6d/kb_integrity_audit.csv` | Replaced incorrect malware names with exact upstream names from the STIX bundle audit CSV. |
| **Stale Quota Reporting** | `REVIEW_PHASE_6D.md` Sec 10 | "Nominal 500 daily quota" | **Removed / Replaced** | Live execution logs | Deleted stale nominal 500 quota rows; retained verified operational accounting logs. |

---

## 3. Pre-Registered Primary Family & Exploratory Multiplicity Control

### Primary Generation Family ($M=4$, Pre-Declared)
*Target family-wise error rate $\alpha = 0.05$. Sourced from `results/phase_6d/holm_primary_generation.json`. Ranks strictly sorted by ascending exact sign test $p$-values.*

| Rank ($k$) | Test ID | Comparison | Metric | Treatment Mean | Control Mean | $\Delta$ | W / T / L | Exact Sign $p$ | Holm Threshold $\alpha^*$ | Holm Verdict |
| :---: | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **1** | `GEN_02` | HD vs LLM-only (`CTI-ATTACK`) | `f1_sub` | 0.2994 | 0.3964 | -0.0970 | 44/102/83 | **0.00068** | 0.01250 ($0.05/4$) | **Reject Null (Favors LLM-only)** |
| **2** | `GEN_01` | HD vs LLM-only (`cti-ate`) | `f1_sub` | 0.3936 | 0.4634 | -0.0698 | 18/6/36 | **0.01983** | 0.01667 ($0.05/3$) | **Fail to Reject Null (Not Significant)** |
| **3** | `GEN_03` | $V_{0h}$ vs LLM-only (`cti-taa`) | `v2_alias` | 0.7400 | 0.7200 | +0.0200 | 7/37/6 | **1.00000** | 0.02500 ($0.05/2$) | Fail to Reject Null (No Difference) |
| **4** | `GEN_04` | $V_{\text{rel}}$ vs $V_{0h}$ (`cti-taa`) | `v2_alias` | 0.7600 | 0.7400 | +0.0200 | 3/45/2 | **1.00000** | 0.05000 ($0.05/1$) | Fail to Reject Null (No Difference) |

> [!IMPORTANT]
> **Key Methodological Finding**: Under multiplicity-controlled exact sign testing, **`GEN_01` does not achieve statistical significance** ($p=0.01983 > 0.01667$). The historical claim of significance ($p=0.0014$) was rooted in paired bootstrap resampling. Only `GEN_02` on `CTI-ATTACK` demonstrates a statistically significant performance deficit relative to zero-shot `LLM-only`. Threat actor attribution differences (`GEN_03` and `GEN_04`) are statistically indistinguishable from zero under multiplicity control.

### Post-Hoc Exploratory Hygiene Family ($M=2$, HD vs True Raw $E_0'$)
*Target family-wise error rate $\alpha = 0.05$. Sourced from live generation live contrasts.*

| Rank ($k$) | Test ID | Comparison | Metric | Treatment Mean | Control Mean | $\Delta$ | W / T / L | Exact Sign $p$ | Holm Threshold $\alpha^*$ | Verdict |
| :---: | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **1** | `HYG_01` | HD vs $E_0'$ (`cti-ate`) | `f1_sub` | 0.3936 | 0.4792 | -0.0855 | 17/7/36 | **0.01266** | 0.02500 ($0.05/2$) | **Statistically Significant Negative** |
| **2** | `HYG_02` | HD vs $E_0'$ (`CTI-ATTACK`) | `f1_sub` | 0.2994 | 0.2454 | +0.0540 | 64/112/53 | **0.3553** | 0.05000 ($0.05/1$) | **Not Significant (Robust Null)** |

---

## 4. Headline Threat Actor Attribution Comparison Table (`cti-taa`)

Regenerated programmatically from `results/phase_6d/phase6g_corrections.json` (Item 8). Every row explicitly designates the metric evaluated and data source:

| Section (Evaluation Metric) | Model / Arm Configuration | Full-50 Queries | Clean-40 Primary Benchmark | Data Provenance Source |
| :--- | :--- | :---: | :---: | :--- |
| **Retrieval Recall@10** | $V_0$ (Raw prompt text) | 0.3400 (17/50) | 0.4000 (16/40) | `phase6g_corrections.json` (item8) |
| **Retrieval Recall@10** | $V_{0h}$ (Hygienic body-only) | 0.1400 (7/50) | 0.1250 (5/40) | `phase6g_corrections.json` (item8) |
| **Retrieval Recall@10** | $V_{\text{rel}}$ (STIX relationship expansion) | 0.3200 (16/50) | 0.3250 (13/40) | `phase6g_corrections.json` (item8) |
| **Primary Generator (`v2_alias`)** | `LLM-only` Baseline | **0.7200** (36/50) | **0.6500** (26/40) | `phase6g_corrections.json` (item8) |
| **Primary Generator (`v2_alias`)** | $V_0$ (Raw prompt text) | 0.6000 (30/50) | 0.5250 (21/40) | `phase6g_corrections.json` (item8) |
| **Primary Generator (`v2_alias`)** | $V_{0h}$ (Hygienic body-only) | 0.7400 (37/50) | 0.6750 (27/40) | `phase6g_corrections.json` (item8) |
| **Primary Generator (`v2_alias`)** | $V_{\text{rel}}$ (STIX relationship expansion) | 0.7600 (38/50) | 0.7000 (28/40) | `phase6g_corrections.json` (item8) |
| **Secondary Generator (`v2_alias`)** | `LLM-only` Baseline | 0.6600 (33/50) | 0.5750 (23/40) | `phase6g_corrections.json` (item8) |
| **Secondary Generator (`v2_alias`)** | $V_0$ (Raw prompt text) | 0.6600 (33/50) | 0.5750 (23/40) | `phase6g_corrections.json` (item8) |
| **Secondary Generator (`v2_alias`)** | $V_{0h}$ (Hygienic body-only) | 0.7000 (35/50) | 0.6250 (25/40) | `phase6g_corrections.json` (item8) |
| **Secondary Generator (`v2_alias`)** | $V_{\text{rel}}$ (STIX relationship expansion) | 0.7200 (36/50) | 0.6500 (26/40) | `phase6g_corrections.json` (item8) |

> [!NOTE]
> **Provenance & Scorer Clarifications**:
> 1. In `LLM-only` on the primary model, **0.7200 is $v_2\text{-alias}$ accuracy** on Full-50 (36/50 correct). The historical citation of 0.6800 corresponds to $v_1\text{-alias}$ (34/50 correct). Both values are verified in `results/phase_6d/generation_arm_means.json`.
> 2. On the secondary generator (`gemini-3.1-flash-lite`), raw $V_0$ achieves 0.6600 on Full-50 (33/50) and 0.5750 on Clean-40 (23/40), exactly matching the `LLM-only` baseline on that model.

---

## 5. Descriptive Project Findings & Epistemic Distinctions

In adherence to Phase 6I Rule 6 (*"rewrite the 'Key Project Findings' descriptively; no 'choking', no mechanism claims; label hypotheses as hypotheses"*), all project conclusions are strictly framed in descriptive, empirical terms:

1. **Retrieval Gains Do Not Translate Proportionally to Live Generation**: While query hygiene consistently yields large retrieval recall gains on `CTI-ATTACK` (up to $+0.4491$ on `E0-STIX-ENT` B2), downstream live generation technique F1 at $B=500$ shows a null effect on `CTI-ATTACK` ($+0.0540$, $p=0.3553$) and a statistically significant negative effect on `cti-ate` ($-0.0855$, $p=0.0127$).
2. **Parametric Zero-Shot Performance Exceeds Constrained $B=500$ RAG**: On both technique extraction benchmarks, zero-shot `LLM-only` obtains higher technique F1 than standard $B=500$ RAG (`cti-ate`: 0.4634 vs 0.3936; `CTI-ATTACK`: 0.3964 vs 0.2994). This empirical finding is consistent with the hypothesis that severely constrained context budgets limit the generator's access to complete semantic descriptions, but causal mechanisms are not definitively established.
3. **Context Window Expansion ($B=2000$) Partially Narrows the Deficit**: Expanding token budget to $B=2000$ (Arm D1) improves technique F1 to 0.4432 on `cti-ate` and 0.3593 on `CTI-ATTACK`, representing a statistically significant gain over $B=500$ HD on `CTI-ATTACK` ($p=0.0008$), while the gain on `cti-ate` is non-significant by sign test ($p=0.0704$).
4. **Attribution Benchmark Disclosures & Artifacts**:
   - `cti-taa` contains 20% ground-truth alias leakage in report text bodies.
   - On the clean 40-query subset, STIX relationship expansion ($V_{\text{rel}}$) recovers retrieval recall ($+0.2000$, $p=0.0078$) over hygienic baseline ($V_{0h}$), but generation accuracy differences remain non-significant on both models.
   - Standard `Recall@B` incorporates structured metadata credit (`mitre_id` and parent expansion); surface text-visible values are systematically lower ($0.0546$ vs $0.2042$ on `cti-ate`; $0.2154$ vs $0.5670$ on `CTI-ATTACK`).
5. **Knowledge Base Integrity**: The STIX knowledge base is an unversioned rolling master snapshot (spec 2.1, schema 3.3.0, modified timestamp `2026-07-31T14:48:40.000Z`). The 62 S9000-series objects (53 malware, 9 tools) are verified authentic upstream MITRE draft objects directly present in the source STIX bundle (`results/phase_6d/kb_integrity_audit.csv`), not synthetic artifacts.

---

## 6. Repository Integrity & Manifest Verification

All writing assets in `results_for_report/` have been regenerated and verified against master:
- **Tables**: `T1_datasets`, `T2_arms`, `T3_main_results`, `T4_statistical_tests`, `T5_detector_precision`, `T6_benchmark_defects` (all with `.md` and `.csv`).
- **Figures**: `F1_hygiene_effect`, `F2_cti_taa_clean40`, `F3_leakage`, `F4_metadata_credit`, `F5_rag_vs_llm_only` (all with `.png`, `.svg`, `.csv`, and `.caption.txt`).
- **Data & Captions**: `claims_master.csv`, `captions.md`, and `RESULTS_MASTER.md`.
- **Test Suite**: 100% of offline unit tests pass cleanly (`pytest` 46/46 passed in 17.38s).
- **Git State**: Certified commit created, tagged `v1.0-final`, and pushed to `main`.
