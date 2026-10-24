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
- **Timestamp (UTC)**: `2026-10-24T22:25:00Z`
- **Timestamp (Local IST)**: `2026-10-25T03:55:00+05:30`
- **Current Step**: `PHASE_7_COMPLETED`
- **Phase 7 O2 Redesign (Offline, Post-Hoc Round 4, Exploratory)**: Completed.
  - Pre-registered in `analysis_plan.md` Section 13 and `results/phase_7/variants_ledger.json`.
  - Part A Diagnostics: Computed across 4 arms ($E_0'\text{-k200}$, $E_0'\text{-TECH-k200}$, $E_{1a}$, $E_1\text{-MIXED}$) at $B \in \{500, 1000\}$; saved in `results/phase_7/assets/table_diagnostics_o2.csv`.
  - Part B Variants: Built $E_{1h}$ (150-token cap, sentence-boundary split, header repeated, 100% ID coverage) and $E_{1h}\text{-MIXED}$.
  - Part C Contrasts (Family P7, Holm $M=4$): Evaluated vs $E_0'\text{-TECH-k200}$ on `cti-ate` and `CTI-ATTACK` (paired bootstrap $N=10,000$, seed 42, exact sign test). Results: P7_01 (Neutral, $p=0.5014$), P7_02 (Neutral, $p=0.6162$), P7_03 (Neutral under Holm, $p=0.0334$), P7_04 (Significant Deficit, $p=0.0106$).
  - Full 4-budget scaling table ($B \in \{500, 1000, 2000, 4000\}$) with binding flags generated and saved in `results/phase_7/assets/table_o2_4budget_scaling.csv`.
  - Report finalized in `reviews/REVIEW_PHASE_7.md`. Original O2 negative result preserved as-is.
- **Phase 6C Generation Status**:
  - Pre-declared in `analysis_plan.md` Section 12 and `results/phase_6c/variants_ledger.json`.
  - Queued for live execution when the 24-hour rolling Gemini API rate-limit quota resets.
- **Active Errors / Blockers**: None. All Phase 7 offline benchmarks completed with code 0.

---

## Completed Milestones
1. `STEP 1 — OFFLINE FIXES`: Complete. Artifacts in `results/phase_5b/`.
2. `STEP 1b — PRE-DECLARED EXTENSIONS`: Complete. Pre-registered in `analysis_plan.md` Section 11 and `results/phase_6/variants_ledger.json`. Artifacts in `results/phase_6/`.
3. `PHASE 6B — FIX ROUND (OFFLINE)`: Complete. Rebuilt claims table, leakage audit, detector audit (D0 vs D1), common-budget & k=200 ladders, Family P6 M=2 correction. Artifacts in `results/phase_6b/`.
4. `PHASE 7 — O2 REDESIGN (OFFLINE, POST-HOC ROUND 4, EXPLORATORY)`: Complete. Diagnostics, $E_{1h}$ & $E_{1h}\text{-div}$ implementations, Family P7 contrasts, 4-budget scaling table, and `reviews/REVIEW_PHASE_7.md` report.
5. `REPORTING & REVIEWS`: All review markdown documents updated.
6. `FREEZE & MANIFEST`: Phase 0–6 frozen results strictly preserved. Ready for push to `main`.

