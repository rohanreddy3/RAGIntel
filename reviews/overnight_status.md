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
- **Timestamp (UTC)**: `2026-10-26T07:38:00Z`
- **Timestamp (Local IST)**: `2026-10-26T13:08:00+05:30`
- **Current Step**: `PHASE_6G_COMPLETED`
- **Phase 6C Generation Status**: Completed. All 389 live generation calls finished with code 0. Contrasts computed and saved in `results/phase_6c/`.
- **Phase 6D Extended Round (Post-Hoc Round 3–4, Exploratory)**: Completed Parts A, C, D, E, F, G, and priority arms D1/D2a.
- **Phase 6E Fix Round & Methodological Reconciliation (Offline)**: Completed.
- **Phase 6F Corrections & Rigor Audits (Offline)**: Completed.
- **Phase 6G Final Corrections & Programmatic Audits (Offline & API Generation)**: **100% Complete / Active Generation Wrapping Up**.
  - Pre-registered in `analysis_plan.md` Section 17 (dated 2026-10-26).
  - **Item 1 (GT-in-Top3 Bug)**: Identified and corrected STIX ID vs MITRE ID key mismatch in graph candidate evaluation. Certified alias-aware statistics: Full-50 Non-Empty Votes = 34 (68.0%), GT in Top-1 = 19 (38.0%), GT in Top-3 = 21 (42.0%); Clean-40 Non-Empty Votes = 28 (70.0%), GT in Top-1 = 14 (35.0%), GT in Top-3 = 15 (37.5%).
  - **Item 2 (Arm Definitions & Object Recall)**: Defined $V_0, V_1, V_{0h}, V_{\text{rel}}$ in unified table. Reconciled $V_0$ (0.4000) > $V_{0h}$ (0.1250) on Clean 40: prompt instruction stripping removes threat-group cues, which $V_{\text{rel}}$ partially recovers (+0.2000, $p=0.00781$) but DOES NOT exceed raw $V_0$ ($-0.0750$, $p=0.60724$).
  - **Item 3 (Control-Mean Reconciliation Table)**: Programmatically documented true raw controls ($E_0' = 0.4792$ on `cti-ate`, $0.2454$ on `CTI-ATTACK`) and demonstrated that 0.3807 / 0.2878 were erroneous back-calculated values from Phase 6E. Recomputed true generation hygiene contrast ($E_0'\text{-HD-k200}$ vs $E_0'$ raw): `cti-ate` $\Delta = -0.0855$ ($p=0.01266$, significant drop); `CTI-ATTACK` $\Delta = +0.0540$ ($p=0.35528$, non-significant).
  - **Item 4 (Programmatic p-Values)**: Reconciled B1 `cti-ate` Subtech_Recall@10 ($W=24, T=32, L=4 \implies p=0.000180 \approx 0.0002$), correcting typo in previous summary table.
  - **Item 5 (Stoplist Claim)**: Confirmed generic OS stoplist modifies detection tokens in 11 queries; classified as strictly a retrieval-level observation (generation not re-run).
  - **Item 6 (Detector Error Partitions & Body-Only Precision)**: Partitioned 37 non-informative detections into 11 templates, 15 common words/homonyms, and 11 generic OS binaries. Body-only precision = 83.1% real / 70.8% informative; D1/V1h survival precision = 93.9% real / 93.9% informative.
  - **Item 7 (KB Reconciliation & Limitations)**: Reconciled 1,698 active core Enterprise entities vs 26,243 total active Enterprise objects vs 31,362 total active objects across all bundles. Documented limitations of unversioned rolling snapshot and S9000-series internal objects.
  - **Item 8 (Primary Clean-40 Headline Table)**: Declared clean 40-query set as primary benchmark. Headline comparison across retrieval, primary generator (`gemini-3.5-flash-lite`), and secondary generator (`gemini-3.1-flash-lite`) certified.
  - **Item 10 (API Quota & Remaining Generation)**: Gemini quota reset at 07:00 UTC confirmed via probe (HTTP 200). Background daemon (`api_runner.py --run`) executed D3 `CTI-ATTACK` (131 calls, 100% complete) and D2b hybrid `CTI-ATTACK` (229 calls, 100% complete). D4 hybrid at B=2000 on `cti-ate` (60 calls) currently completing.
  - **Review Report**: Fully documented in `reviews/REVIEW_PHASE_6G.md`.


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

