# Overnight Unattended Run — Status

### Reasonable Reading & Execution Plan
- **Mode**: Overnight unattended run (thread cap 4, one heavy process at a time, no deletion, zero secrets printed/committed).
- **Scope**:
  - Step 1 offline fixes: Complete. Exact sign test p-values added, P3_03/P3_11 classified as bootstrap-significant/exact-test borderline, C10 rewritten with k200 pool, primary O2 tables updated with k200 controls, CTI-ATTACK entity detector share reconciled (3.49%), C4/C5/C7 relabeled as measured under raw queries, cti-taa evaluated on full and mappable subsets, query splitting asserted.
  - Step 1b pre-declared extensions: Complete. Pre-registered in `analysis_plan.md` Section 11 and `results/phase_6/variants_ledger.json`. Vrel-T and E-comb evaluated on `cti-ate`, `CTI-ATTACK`, and `cti-taa`. Family P6 contrasts computed. Improvement ladder synthesis table generated.
  - Phase 6B fix round (offline): Complete.
    1. Claims table rebuilt from Phase 4B/5 matrix (C1–C10 original meanings restored; unbacked claims removed; C11–C14 added; all numbers asserted against JSON/CSV).
    2. Leakage audit completed (cti-ate 94.81% GT technique STIX uses share, 60.35% oracle top-5 recall; CTI-ATTACK 0% software; cti-taa 28.95% software-group association; relabeled "KB-lookup upper bound; not evidence of generalization to unseen reports").
    3. Ladder recomputed on common budgets {500, 1000} binding for every stage and on all 4 budgets with k=200 for every stage including raw-k200.
    4. Detectors formalized as D0 (unfiltered) and D1 (V1h strict); entity share and matches/query recomputed for raw and body-only across all 3 datasets; C3 domain statistic fixed to 396/397 (99.75%).
    5. Family P6 deduplicated to M=2 (P6_01 and P6_02 only); P6_03/P6_04 removed; P3_04 original decision preserved.
    6. Step 3 generation parameters preserved unchanged.
- **Integrity**: Frozen Phase 0–5 results and `analysis_plan.md` sections 1–10 remain strictly unmodified. Artifacts stored in `results/phase_6b/`.

---

## Current Status Snapshot
- **Timestamp (UTC)**: `2026-10-25T10:45:00Z`
- **Timestamp (Local IST)**: `2026-10-25T16:15:00+05:30`
- **Current Step**: `PHASE_6D_IN_PROGRESS`
- **Phase 6C Generation Status**: Completed. All 389 live generation calls finished with code 0. Contrasts computed and saved in `results/phase_6c/`.
- **Phase 6D Extended Round (Post-Hoc Round 3–4, Exploratory)**:
  - Pre-registered in `analysis_plan.md` Section 14 (SHA256: `117E541B157001676F963D3B73C81504CBCE7328FE43A635C5F12EEDE30A3BA6`) and `results/phase_6d/variants_ledger.json`.
  - Part A (Clean-up & Multiplicity): Complete. Fixed cti-taa table labels, replaced Section 4 of REVIEW_PHASE_6C.md with descriptive diagnostics, computed missing cti-taa contrasts (Vrel vs V0h, V0h vs V0 across all 4 scorers with bootstrap and exact sign p in `missing_taa_contrasts.csv`), and computed Holm step-down correction over 4 primary generation comparisons in `holm_primary_generation.csv`.
  - Part C (Diagnostics): Complete. Descriptive diagnostics for E0'(raw), E0'-HD-k200, E1h, LLM-only on cti-ate/CTI-ATTACK in `diagnostics_generation.json`. Spearman rank correlation: CTI-ATTACK $\rho = +0.5565$ ($p < 0.0001$), cti-ate $\rho = +0.2415$ ($p = 0.0630$). Mobile domain filter compliance verified (100% compliant, 0 leaks in `mobile_domain_filter_check.json`).
  - Part G (Case Studies): Complete. Deterministic case studies on cti-taa (first 5 Vrel wins, first 3 losses by row_idx) with detected software, top-3 voted groups, ground-truth context presence, model response, and verbatim query span assertions passed in `case_studies_cti_taa.md`.
  - Part F (Second Generator Replication): Complete. Evaluated 200 live calls on `models/gemini-3.1-flash-lite` across `cti-taa` (LLM-only, V0, V0h, Vrel). Relative ranking is $V_{\text{rel}} (0.7200) > V_{0h} (0.7000) > \text{LLM-only} (0.6600) \ge V_0 (0.6600)$. Exact relative ranking matches primary model (`True`) in `second_generator_ranking_comparison.json`.
  - Part B (API Generation Priority Arms): In progress (607 live calls completed).
    - Priority D1 (`E0_prime_HD_k200_b2000` at $B=2000$ tokens): **100% Complete** (60 cti-ate + 229 CTI-ATTACK = 289 calls). Evaluated with 10k paired bootstrap and exact sign test: on CTI-ATTACK, $B=2000$ significantly increases technique F1 by +0.0599 ($p=0.0008$, W/T/L 60/141/28) over $B=500$ (0.3593 vs 0.2994), closing the gap with LLM-only (0.3593 vs 0.3964, $p=0.3232$, no longer statistically significantly worse). On cti-ate, $B=2000$ reaches 0.4432 vs 0.3936 ($p=0.0704$), virtually matching LLM-only (0.4634, $p=1.0000$).
    - Priority D2a (Hybrid prompt at $B=500$ tokens): **100% Complete** (60 cti-ate + 50 V0h + 50 Vrel = 160 calls). On cti-ate, hybrid prompt achieves 0.3957 vs 0.3936 standard prompt ($p=0.1934$). On cti-taa, hybrid prompt yields 0.7400 attribution for both Vrel and V0h.
    - Priority D3 (O2 end-to-end `E1h_mixed_HD_b500`): **60 cti-ate calls Complete** (F1 0.3515 vs 0.3936 HD, $p=0.1189$; vs 0.4634 LLM-only, $p=0.0003$). CTI-ATTACK has 98 calls complete (131 remaining).
    - Runner is safely sleeping on quota backoff and will resume remaining D3 (131 calls), D2b (229 calls), and D4 (60 calls) upon quota replenishment.
    - Metrics saved in `results/phase_6d/generation_contrasts.csv` and `generation_arm_means.json`.
  - Part E (Secondary KB Replication): **Complete**. Evaluated V0, V0h, V1, Vrel on `E0-STIX-ENT` under B2 (`MiniLM-Truncated-256`) and B3 (`MiniLM-MaxSim-Windows`) across all 3 datasets (339 queries). Key findings: (1) on `cti-taa`, relationship expansion ($V_{\text{rel}}$) provides significant recall gains over hygiene alone ($V_{0h}$) under B2 ($\Delta = +0.1800$, $p=0.0117$) and under B3 ($\Delta = +0.0800$); (2) on `cti-ate`, $V_{\text{rel}}$ substantially outperforms both $V_1$ and $V_{0h}$ under B2 ($\Delta = +0.1510$, $p < 0.0001$) and B3 ($\Delta = +0.1476$, $p < 0.0001$); (3) on `CTI-ATTACK`, hygiene ($V_{0h}$) yields a massive +44.9 percentage point recall gain over $V_0$ under both B2 and B3 (0.6303 vs 0.1812, $p < 0.0001$). Saved in `results/phase_6d/secondary_kb_contrasts.csv` and `secondary_kb_evaluations.json`.
  - Part D (B1 Retriever Robustness): **Complete**. Evaluated dense long-context embeddings (`nomic-ai/nomic-embed-text-v1.5`, 8192 context) without document or query chunking across 2,088 raw STIX docs and all 3 datasets. Key findings: (1) on `cti-taa`, relationship expansion ($V_{\text{rel}}$) strictly maintains or improves recall over hygiene alone (0.3400 vs 0.2200, $\Delta = +0.1200$, $p=0.0312$, W/T/L = **6/44/0**; and $\Delta = +0.2000$ over $V_0$, $p=0.0020$, W/T/L = **10/40/0**); (2) on `cti-ate`, HD preprocessing more than doubles technique recall (0.1809 vs 0.0874, $\Delta = +0.0935$, $p=0.0002$); (3) on `CTI-ATTACK`, HD preprocessing yields a massive +35.4 percentage point gain (0.5662 vs 0.2118, $\Delta = +0.3544$, $p < 0.0001$, W/T/L = **90/137/2**). Both headline effects hold under long-context dense embeddings without chunking. Saved in `results/phase_6d/b1_robustness_contrasts.csv` and `b1_robustness_metrics.json`.
  - Part H (Report & Reproducibility): Unified report updated in `reviews/REVIEW_PHASE_6D.md`. Freeze manifest updated to 146 bit-exact files (historic hashes strictly preserved).
- **Active Errors / Blockers**: None. Background runner safely waiting on quota backoff for remaining generation calls.


---

## Completed Milestones
1. `STEP 1 — OFFLINE FIXES`: Complete. Artifacts in `results/phase_5b/`.
2. `STEP 1b — PRE-DECLARED EXTENSIONS`: Complete. Pre-registered in `analysis_plan.md` Section 11 and `results/phase_6/variants_ledger.json`. Artifacts in `results/phase_6/`.
3. `PHASE 6B — FIX ROUND (OFFLINE)`: Complete. Rebuilt claims table, leakage audit, detector audit (D0 vs D1), common-budget & k=200 ladders, Family P6 M=2 correction. Artifacts in `results/phase_6b/`.
4. `PHASE 7 — O2 REDESIGN (OFFLINE, POST-HOC ROUND 4, EXPLORATORY)`: Complete. Diagnostics, $E_{1h}$ & $E_{1h}\text{-div}$ implementations, Family P7 contrasts, 4-budget scaling table, and `reviews/REVIEW_PHASE_7.md` report.
5. `REPORTING & REVIEWS`: All review markdown documents updated.
6. `FREEZE & MANIFEST`: Phase 0–6 frozen results strictly preserved. Ready for push to `main`.

