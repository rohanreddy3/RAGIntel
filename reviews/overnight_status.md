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
- **Timestamp (UTC)**: `2026-10-25T11:15:00Z`
- **Timestamp (Local IST)**: `2026-10-25T16:45:00+05:30`
- **Current Step**: `PHASE_6E_COMPLETED`
- **Phase 6C Generation Status**: Completed. All 389 live generation calls finished with code 0. Contrasts computed and saved in `results/phase_6c/`.
- **Phase 6D Extended Round (Post-Hoc Round 3–4, Exploratory)**: Completed Parts A, C, D, E, F, G, and priority arms D1/D2a (607 calls served).
- **Phase 6E Fix Round & Methodological Reconciliation (Offline)**: **100% Complete**.
  - Pre-registered in `analysis_plan.md` Section 15.
  - **Retrieval Metric Reconciliation**: Recomputed `Recall@B (sub_credits_parent)` and `Context Recall (GT)` on exact context files sent to LLM for $E_0'\text{(raw)}$, $E_0'\text{-HD-k200}$, and $E_{1h}$ across `cti-ate` and `CTI-ATTACK` at $B=500$. Resolved discrepancy between Phase 5 (0.2042) and Phase 6D (0.0546 / 0.0517): structured metadata with parent credit vs surface text regex without metadata. Saved in `results/phase_6d/retrieval_reconciliation_b500.json` and `.csv`.
  - **Vrel Noise Floor Stratification (`cti-taa`)**: Stratified 50 queries into Active stratum ($N=34$, 68%, $V_{0h}=0.7647$, $V_{\text{rel}}=0.7941$, W/T/L = 2/31/1) and Inactive stratum ($N=16$, 32%, $V_{0h}=0.6875$, $V_{\text{rel}}=0.6875$, W/T/L = 1/14/1). Established that 100% of inactive queries (16/16) produced differing model answers at temperature `0.0`, confirming the +1 net win is within the stochastic generation noise floor. Saved in `results/phase_6d/vrel_noise_floor_stratification.json`.
  - **Labels and Wording**: Standardized Arm D3 label to `"E1h-MIXED structure-aware chunks (header-prefixed field chunks), no entities"`. Removed unprincipled summary list. Added formal leakage caveat (`"KB-lookup upper bound; not evidence of generalization to unseen reports"`) to Enterprise STIX (`E0-STIX-ENT`) `cti-ate` $V_{\text{rel}}$ rows.
  - **Missing Contrasts**: Computed paired bootstrap (10,000 resamples, seed 42) and exact sign tests for D1 ($B=2000$) vs raw $E_0'$ ($B=500$) on `cti-ate` ($\Delta = -0.0359$, $p=0.5831$) and `CTI-ATTACK` ($\Delta = +0.1139$, $p=0.0027$, W/T/L 74/114/41, significant increase). Computed paired bootstrap and sign tests for all second generator (`gemini-3.1-flash-lite`) `cti-taa` arms across all 4 scorers. Rephrased ranking alignment as `"same direction; gaps of 1–3 queries"`. Noted D3 vs `LLM-only` on `CTI-ATTACK` as pending quota replenishment.
  - **Unified Query Hygiene Summary Table**: Synthesized hygiene effect across all 4 regimes (Phase 5 common budgets, ENT B2/B3, B1 unchunked dense 8k, live generation F1) with positive ($+$), null ($0$), negative ($-$) classifications. Saved in `results/phase_6d/hygiene_summary_table.json` and `.csv`.
  - **Quota Accounting**: Reconciled call logs into calls per model per UTC day. Clarified that 998 successful primary calls on 2026-10-25 represent calls served across the 07:00 UTC daily quota reset boundary (391 pre-reset + 607 post-reset). Saved in `results/phase_6d/quota_accounting_by_utc_day.json` and `.csv`.
  - **Detector Failure Case Study**: Added Case 26 ("Soldier" matching SysUpdate) descriptive study illustrating entity detector homonym collision across threat actors and geopolitical boundaries.
  - **Freeze Manifest**: Updated to 157 bit-exact files (historic hashes strictly preserved).
- **Background Daemon Status**: `task-12399` (PID 19736) safely sleeping on quota backoff for remaining generation calls (D3 CTI-ATTACK, D2b, D4).

---

## Completed Milestones
1. `STEP 1 — OFFLINE FIXES`: Complete. Artifacts in `results/phase_5b/`.
2. `STEP 1b — PRE-DECLARED EXTENSIONS`: Complete. Pre-registered in `analysis_plan.md` Section 11 and `results/phase_6/variants_ledger.json`. Artifacts in `results/phase_6/`.
3. `PHASE 6B — FIX ROUND (OFFLINE)`: Complete. Rebuilt claims table, leakage audit, detector audit (D0 vs D1), common-budget & k=200 ladders, Family P6 M=2 correction. Artifacts in `results/phase_6b/`.
4. `PHASE 7 — O2 REDESIGN (OFFLINE, POST-HOC ROUND 4, EXPLORATORY)`: Complete. Diagnostics, $E_{1h}$ & $E_{1h}\text{-div}$ implementations, Family P7 contrasts, 4-budget scaling table, and `reviews/REVIEW_PHASE_7.md` report.
5. `PHASE 6D — EXTENDED ROUND EVALUATION`: Complete Parts A, C, D, E, F, G, D1, D2a.
6. `PHASE 6E — FIX ROUND & METHODOLOGICAL RECONCILIATION (OFFLINE)`: Complete. Section 15 pre-registered, retrieval reconciliation, Vrel noise floor stratification, missing contrasts, unified hygiene table, quota accounting, and Case 26 detector failure analysis incorporated into `reviews/REVIEW_PHASE_6D.md`.
7. `FREEZE & MANIFEST`: Manifest updated to 157 bit-exact files; historic hashes strictly preserved. Ready for push to `main`.

