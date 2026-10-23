# Overnight Unattended Run — Status

### Reasonable Reading & Execution Plan
- **Mode**: Overnight unattended run (thread cap 4, one heavy process at a time, no deletion, zero secrets printed/committed).
- **Scope**:
  - Step 1 offline fixes: Complete. Exact sign test p-values added, P3_03/P3_11 classified as bootstrap-significant/exact-test borderline, C10 rewritten with k200 pool, primary O2 tables updated with k200 controls, CTI-ATTACK entity detector share reconciled (3.49%), C4/C5/C7 relabeled as measured under raw queries, cti-taa evaluated on full and mappable subsets, query splitting asserted.
  - Step 1b pre-declared extensions: Complete. Pre-registered in `analysis_plan.md` Section 11 and `results/phase_6/variants_ledger.json`. Vrel-T and E-comb evaluated on `cti-ate`, `CTI-ATTACK`, and `cti-taa`. Family P6 contrasts computed. Improvement ladder synthesis table generated.
  - Step 2/3 generation: Quota exhausted (500/500). Expected reset ~07:07 UTC / 12:37 IST. Execution paused under Section 10.6 quota safeguard.
- **Integrity**: Frozen Phase 0–5 results and `analysis_plan.md` sections 1–10 remain strictly unmodified. New amendments added as Sections 10.8 and 11. Artifacts stored under `results/phase_5b/` and `results/phase_6/`.

---

## Current Status Snapshot
- **Timestamp (UTC)**: `2026-10-23T19:30:00Z`
- **Timestamp (Local IST)**: `2026-10-24T01:00:00+05:30`
- **Current Step**: `WAITING_FOR_QUOTA`
- **API Calls Used in Rolling 24h**: `500 / 500` (Quota exhausted; reset expected ~07:07 UTC / 12:37 IST)
- **Next Planned Action**: Keep api_runner probe alive; upon daily quota reset, launch Step 2 bare-prompt generation and Step 3 scoring.
- **Active Errors / Blockers**: None.

---

## Completed Milestones
1. `STEP 1 — OFFLINE FIXES`: Complete. Artifacts in `results/phase_5b/`.
2. `STEP 1b — PRE-DECLARED EXTENSIONS`: Complete. Pre-registered in `analysis_plan.md` Section 11 and `results/phase_6/variants_ledger.json`. Artifacts in `results/phase_6/`.
3. `STEP 5 (PARTIAL) — REPORTING`: `reviews/REVIEW_PHASE_5B.md` generated.
4. `STEP 6 — MANIFEST UPDATE & GIT`: Ready to update freeze manifest and push to `origin/main`.
