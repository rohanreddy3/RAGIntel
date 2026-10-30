# REVIEW_PHASE_6K: Claim C2 Enterprise STIX Baseline/Treatment Means Correction

**Phase**: 6K — C2 Enterprise STIX Means Correction and Repository Re-Freeze  
**Execution Mode**: Offline (Zero API Calls)  
**Release Tag**: `v1.0-final3`  
**Date**: 2026-10-30  

---

## 1. Executive Summary: C2 Correction Note

In Phase 6K, the baseline (control) and treatment means for **Claim C2 (Enterprise STIX Retrieval Hygiene, `E0-STIX-ENT`)** were corrected across `results_for_report/` (`RESULTS_MASTER.md`, `claims_master.csv`, `T3_main_results`, captions), `reviews/RESULTS_MASTER.md`, and `scripts/verify_master.py`.

The erroneous draft means (`0.2797`, `0.2762`, `0.2387`, `0.7253`) were audited, removed from the entire repository, and replaced with the ground-truth values read directly from [`results/phase_6d/secondary_kb_contrasts.csv`](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/results/phase_6d/secondary_kb_contrasts.csv):

- **`cti-ate` (E0-STIX-ENT, B3, `Subtech_Recall@10`, $V_{0h}$ vs $V_0$)**:
  - Baseline Control Mean ($V_0$): **0.1221** (was erroneously stated as 0.2797)
  - Treatment Mean ($V_{0h}$): **0.0811** (was erroneously stated as 0.2387)
  - Delta ($\Delta$): **-0.0410**
  - Wins / Ties / Losses: **6 / 32 / 22**
  - Exact Binomial Sign Test $p$: **0.0037** (statistically significant negative)
  - 95% Bootstrap CI: **[-0.1033, +0.0293]**

- **`CTI-ATTACK` (E0-STIX-ENT, B2, `Subtech_Recall@10`, $V_{0h}$ vs $V_0$)**:
  - Baseline Control Mean ($V_0$): **0.1812** (was erroneously stated as 0.2762)
  - Treatment Mean ($V_{0h}$): **0.6303** (was erroneously stated as 0.7253)
  - Delta ($\Delta$): **+0.4491**
  - Wins / Ties / Losses: **117 / 104 / 8**
  - Exact Binomial Sign Test $p$: **<0.0001** ($5.93 \times 10^{-26}$, statistically significant positive)
  - 95% Bootstrap CI: **[+0.3785, +0.5168]**

---

## 2. Programmatic Loading in Verifier Suite

[`scripts/verify_master.py`](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/scripts/verify_master.py) was updated to load these means dynamically from `results/phase_6d/secondary_kb_contrasts.csv` by dataset, baseline, and metric key:
```python
sec_kb_csv = load_csv(P6D / "secondary_kb_contrasts.csv")
c2_ate = find(sec_kb_csv, kb="E0-STIX-ENT", baseline="B3", dataset="cti-ate", contrast="V0h vs V0", metric="Subtech_Recall@10")
c2_att = find(sec_kb_csv, kb="E0-STIX-ENT", baseline="B2", dataset="CTI-ATTACK", contrast="V0h vs V0", metric="Subtech_Recall@10")
```
No values are hardcoded in the verifier. All 81 assertions in `scripts/verify_master.py` passed with zero errors.

---

## 3. Repository Search & Eradication Verification

A full repository audit confirmed that zero occurrences of the legacy values `0.2797`, `0.2762`, `0.2387`, and `0.7253` remain in any code, documentation, or table across the repository.

---

## 4. Test Suite and Freeze Certification

- **Pytest Suite**: All 52 tests collected across 11 test files passed in strictly offline execution mode.
- **Manifest Re-Freeze**: `results/freeze_manifest.json` recomputed and certified under `v1.0-final3`.

