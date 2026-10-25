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
- **Timestamp (UTC)**: `2026-10-25T05:32:00Z`
- **Timestamp (Local IST)**: `2026-10-25T11:02:00+05:30`
- **Current Step**: `PHASE_6D_IN_PROGRESS`
- **Phase 6C Generation Status**: Completed. All 389 live generation calls finished with code 0. Contrasts computed and saved in `results/phase_6c/`.
- **Phase 6D Extended Round (Post-Hoc Round 3–4, Exploratory)**:
  - Pre-registered in `analysis_plan.md` Section 14 (SHA256: `117E541B157001676F963D3B73C81504CBCE7328FE43A635C5F12EEDE30A3BA6`) and `results/phase_6d/variants_ledger.json`.
  - Part A (Clean-up): Complete. Fixed cti-taa table labels, replaced Section 4 of REVIEW_PHASE_6C.md with descriptive diagnostics, computed missing cti-taa contrasts (Vrel vs V0h, V0h vs V0 across all 4 scorers with bootstrap and exact sign p), and computed Holm step-down correction over 4 primary generation comparisons.
  - Part C (Diagnostics): Complete. Descriptive diagnostics for E0'(raw), E0'-HD-k200, E1h, LLM-only on cti-ate/CTI-ATTACK computed. Spearman rank correlation between context recall and F1 computed. Mobile domain filter compliance verified (100%).
  - Part G (Case Studies): Complete. Script-generated case studies for cti-taa (5 Vrel wins, 3 Vrel losses by row_idx) with top-3 voted groups, ground-truth presence, model response, and verbatim query span assertions passed.
  - Part E (Secondary KB): In progress (actively computing B2/B3 retrieval across cti-taa, cti-ate, CTI-ATTACK on E0-STIX-ENT).
  - Part F (Second Generator): Pre-declared model `models/gemini-3.1-flash-lite` (newest Flash-Lite model in API listing != gemini-3.5-flash-lite). Pipeline script `scripts/run_phase6d_second_generator.py` prepared.
  - Part D (B1 Robustness): Dense long-context embedding pipeline `scripts/run_phase6d_b1_robustness.py` prepared with local `nomic-ai/nomic-embed-text-v1.5`.
  - Part B (API Generation): Section 14 arms (D1, D2a, D3, D2b, D4) implemented in `scripts/api_runner.py` and validated via dry-run simulation. Ready for live execution.
- **Active Errors / Blockers**: None.


---

## Completed Milestones
1. `STEP 1 — OFFLINE FIXES`: Complete. Artifacts in `results/phase_5b/`.
2. `STEP 1b — PRE-DECLARED EXTENSIONS`: Complete. Pre-registered in `analysis_plan.md` Section 11 and `results/phase_6/variants_ledger.json`. Artifacts in `results/phase_6/`.
3. `PHASE 6B — FIX ROUND (OFFLINE)`: Complete. Rebuilt claims table, leakage audit, detector audit (D0 vs D1), common-budget & k=200 ladders, Family P6 M=2 correction. Artifacts in `results/phase_6b/`.
4. `PHASE 7 — O2 REDESIGN (OFFLINE, POST-HOC ROUND 4, EXPLORATORY)`: Complete. Diagnostics, $E_{1h}$ & $E_{1h}\text{-div}$ implementations, Family P7 contrasts, 4-budget scaling table, and `reviews/REVIEW_PHASE_7.md` report.
5. `REPORTING & REVIEWS`: All review markdown documents updated.
6. `FREEZE & MANIFEST`: Phase 0–6 frozen results strictly preserved. Ready for push to `main`.

