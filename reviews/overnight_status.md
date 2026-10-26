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
- **Timestamp (UTC)**: `2026-10-26T06:55:00Z`
- **Timestamp (Local IST)**: `2026-10-26T12:25:00+05:30`
- **Current Step**: `PHASE_6F_COMPLETED`
- **Phase 6C Generation Status**: Completed. All 389 live generation calls finished with code 0. Contrasts computed and saved in `results/phase_6c/`.
- **Phase 6D Extended Round (Post-Hoc Round 3–4, Exploratory)**: Completed Parts A, C, D, E, F, G, and priority arms D1/D2a (607 calls served).
- **Phase 6E Fix Round & Methodological Reconciliation (Offline)**: Completed. Section 15 pre-registered, retrieval reconciliation, Vrel noise floor stratification, missing contrasts, unified hygiene table, quota accounting, and Case 26 detector failure analysis incorporated.
- **Phase 6F Corrections & Rigor Audits (Offline)**: **100% Complete**.
  - Pre-registered in `analysis_plan.md` Section 16 (dated 2026-10-26).
  - **Item 1 (GEN_01/GEN_02 p-Values)**: Resolved bootstrap vs exact sign mismatch. Recomputed Holm family with exact sign tests. Certified that **`GEN_01` (`cti-ate`) is NOT statistically significant ($p=0.0198 > 0.0167$)** under Holm step-down correction. `GEN_02` (`CTI-ATTACK`) remains statistically significant ($p=0.0007 \le 0.0125$).
  - **Item 2 (Unified Hygiene Summary Table)**: Regenerated directly from source CSVs with automated assertions across all cells. Certified Enterprise STIX B3 negative delta on `cti-ate` ($-0.0410$, $p=0.0037$). Formally reconciled Phase 5 single-budget gains ($+0.1525$ at $B=500$ with $k=200$ pool expansion) with Phase 6B balanced ladder gains ($+0.0849$ across $\{500, 1000\}$ with fixed $k=50$ pool).
  - **Item 3 (Metadata-Credit Audit)**: Evaluated Recall@B under metadata credit vs surface text-visible matching. Highlighted that retrieval hygiene on `cti-ate` is smaller/null ($-0.0125$) under surface matching, and that large retrieval gains on `CTI-ATTACK` do not transfer to technique generation F1 (+0.0129 / +0.0116, non-significant).
  - **Item 4 (Noise Strata Ledger & Reclassification)**: Generated 50-query ledger with `context_identical` flag. Reclassified Cases 22 and 41 to the Inactive stratum ($N=16$, 32%), confirming 100% run-to-run lexical variation at temperature 0.0.
  - **Item 5 (Aggregate Attribution Statistics & Stoplist Audit)**: Replaced hand-picked case studies with 50-query aggregate metrics (34/50 non-empty votes, 0/50 GT in top-3, 14/50 GT in context). Generic OS stoplist alters 11/50 queries (22.0%) with 0 net change in downstream attribution. Preserved Case 26 ("Soldier" matching SysUpdate) as persistent polysemy collision limitation.
  - **Item 6 & 7 (Wording & Quota)**: Standardized D2a reporting string (`'-0.0677 vs LLM-only on cti-ate (bootstrap CI [-0.117,-0.020], exact sign p=0.081)'`) and replaced "nominal 500" with observed per-window maximum ($\ge 607$ calls).
  - **Item 7b (GT-Alias Leakage Audit)**: Tested all 50 queries for GT alias leakage in report body text; 10/50 queries leak (rows 1, 22, 23, 26, 37, 38, 40, 42, 48, 49), yielding an artificial 1.0000 ceiling. Rescored clean subset ($N=40$) where $V_{\text{rel}}$ achieves 0.7000 vs 0.6750 for $V_{0h}$ and 0.6500 for `LLM-only`.
  - **Item 7c (Knowledge Base Integrity Audit)**: Audited 62 non-standard `S9000`-series STIX objects (created Dec 2025 – Oct 2026); confirmed 0 occurrences in prompt contexts and 0 impact on attribution decisions.
  - **Item 7d (Entity Detector Precision Audit)**: Evaluated 100 labeled matches from `results/phase_4b/detector_labels.csv`; D0 precision = 74.0% (63.0% informative), D1/V1h precision = 76.9%; 26 FPs categorized into template examples, common words/homonyms, and generic OS utilities.
  - **Review Report**: Fully documented in `reviews/REVIEW_PHASE_6F.md` and integrated into `reviews/REVIEW_PHASE_6D.md`.
- **Background Daemon Status**: `task-12399` safely sleeping on quota backoff for remaining generation calls (D3 `CTI-ATTACK`, D2b, D4).
- **Post-Quota Execution Plan (Item 8)**: Upon quota replenishment, execute remaining calls, rerun affected tables, update report, STOP and wait for review.

---

## Completed Milestones
1. `STEP 1 — OFFLINE FIXES`: Complete. Artifacts in `results/phase_5b/`.
2. `STEP 1b — PRE-DECLARED EXTENSIONS`: Complete. Pre-registered in `analysis_plan.md` Section 11 and `results/phase_6/variants_ledger.json`. Artifacts in `results/phase_6/`.
3. `PHASE 6B — FIX ROUND (OFFLINE)`: Complete. Rebuilt claims table, leakage audit, detector audit (D0 vs D1), common-budget & k=200 ladders, Family P6 M=2 correction. Artifacts in `results/phase_6b/`.
4. `PHASE 7 — O2 REDESIGN (OFFLINE, POST-HOC ROUND 4, EXPLORATORY)`: Complete. Diagnostics, $E_{1h}$ & $E_{1h}\text{-div}$ implementations, Family P7 contrasts, 4-budget scaling table, and `reviews/REVIEW_PHASE_7.md` report.
5. `PHASE 6D — EXTENDED ROUND EVALUATION`: Complete Parts A, C, D, E, F, G, D1, D2a.
6. `PHASE 6E — FIX ROUND & METHODOLOGICAL RECONCILIATION (OFFLINE)`: Complete. Section 15 pre-registered, retrieval reconciliation, Vrel noise floor stratification, missing contrasts, unified hygiene table, quota accounting, and Case 26 detector failure analysis incorporated into `reviews/REVIEW_PHASE_6D.md`.
7. `PHASE 6F — CORRECTIONS AND RIGOR AUDITS (OFFLINE)`: Complete. Section 16 pre-registered, exact sign test Holm family recomputation (GEN_01 not significant), unified hygiene table regenerated and asserted, metadata-credit audit, noise strata 50-query ledger (Cases 22 & 41 reclassified), aggregate case statistics & stoplist audit, D2a wording & quota capacity updates, GT-alias leakage audit ($N=40$ clean rescore), KB integrity audit (62 objects), detector precision audit on 100 labeled matches (`results/phase_4b/detector_labels.csv`), and `reviews/REVIEW_PHASE_6F.md` written.
8. `FREEZE & MANIFEST`: Bit-exact file tracking with historic hashes strictly preserved. Ready for push to `main`.

