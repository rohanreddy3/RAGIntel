# RESULTS_MASTER: Canonical Claims, Contrasts, and Evidence Ledger

**Generated programmatically by `scripts/build_results_master.py` — Phase 6J (2026-10-30 09:33 UTC)**
All numbers read from source CSV/JSON in `results/phase_*`; zero hand-typed values.

### Status Label Definitions
- **Robust**: Statistically significant after declared multiple-testing correction AND replicated on a second KB, second retriever, or second generator.
- **Exploratory**: Statistically notable or significant under an isolated setting, but not replicated across multiple axes or failed family-wise correction.
- **Mixed**: Heterogeneous effects observed across benchmark datasets or metrics (e.g., significant positive on one dataset, negative or null on another).
- **Null / Negative**: Empirical effect not statistically distinguishable from zero ($p \ge 0.05$ or CI crossing 0) or statistically significant in the adverse direction ($\Delta < 0$).

## Claims Table

| Claim ID | Summary | Metric | Dataset | Control | Treatment | N | Delta (ate / att) | CI (ate) | CI (att) | W/T/L (ate) | W/T/L (att) | p (ate) | p (att) | Source | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **C1** | Balanced retrieval query hygiene improves Mean Recall@B across balanced budgets {500, 1000} with fixed pool k=50 (cti-ate: 0.1601 -> 0.2450; CTI-ATTACK: 0.3064 -> 0.6074) | `Mean Recall@B` | cti-ate (N=60) & CTI-ATTACK (N=229) | Raw (E0' raw, k=50) | Hygiene (E0' body-only, k=50) | 60 / 229 | +0.0849 / +0.3010 | [+0.0382, +0.1315] | [+0.2520, +0.3500] | 29/21/10 | 175/27/27 | 0.0034 | <0.0001 | `results/phase_6b/assets/table_ladder_common_budgets.csv` | **Robust** |
| **C2** | Enterprise STIX (E0-STIX-ENT): query hygiene is negative under B3 on cti-ate (-0.0410, p=0.0037) but massive positive under B2 on CTI-ATTACK (+0.4491, p<0.0001) | `Subtech_Recall@10` | cti-ate B3 (N=60) & CTI-ATTACK B2 (N=229) | E0-STIX-ENT Raw (V0) | E0-STIX-ENT Hygiene (V0h) | 60 / 229 | -0.0410 / +0.4491 | [-0.1033, +0.0293] | [+0.3785, +0.5168] | 6/32/22 | 117/104/8 | 0.0037 | <0.0001 | `results/phase_6d/secondary_kb_contrasts.json` | **Mixed** |
| **C3** | Long-context B1 dense embeddings benefit from query hygiene | `Recall@10 (Subtech_Recall@10)` | cti-ate (N=60) & CTI-ATTACK (N=229) | B1 Raw Unchunked | B1 Hygiene Unchunked | 60 / 229 | +0.0935 / +0.3544 | [+0.0484, +0.1463] | [+0.2933, +0.4156] | 24/32/4 | 90/137/2 | 0.0002 | <0.0001 | `results/phase_6d/b1_robustness_contrasts.csv` | **Robust** |
| **C4** | Downstream generation hygiene (HD vs E0') hurts cti-ate (negative, significant), mixed on CTI-ATTACK (positive mean, CI excludes 0, sign test p=0.355) | `Technique F1 (f1_sub)` | cti-ate (N=60) & CTI-ATTACK (N=229) | True Raw E0' (B=500, k=all) | HD (B=500, k=200) | 60 / 229 | -0.0855 / +0.0540 | [-0.1356, -0.0386] | [+0.0069, +0.1027] | 17/7/36 | 64/112/53 | 0.0127 | 0.3553 | `results/phase_6d/phase6g_corrections.json + results/phase_6c/contrasts_table.json` | **Mixed** |
| **C5** | Primary generation family: HD vs LLM-only significant on CTI-ATTACK, not cti-ate under Holm M=4 | `Technique F1 (f1_sub)` | CTI-ATTACK (GEN_02) & cti-ate (GEN_01) | LLM-only Baseline | HD (B=500) | 229 / 60 | -0.0698 / -0.0970 | [-0.1120, -0.0296] | [-0.1432, -0.0502] | 18/6/36 | 44/102/83 | 0.01983 (Holm α*=0.01667, Not Sig) | 0.00068 (Holm α*=0.0125, Sig) | `results/phase_6d/holm_primary_generation.json + results/phase_6c/contrasts_table.json` | **Robust (CTI-ATTACK) / Not Sig under Holm (cti-ate)** |
| **C6** | On cti-taa Clean-40, Vrel recovers retrieval recall but generation null on both primary and secondary generators | `Retrieval Recall@10 / Gen v2_alias` | cti-taa Clean-40 (N=40) | V0h | Vrel | 40 | +0.2000 / See headline table | [+0.0750, +0.3250] | N/A | 8/32/0 | N/A | 0.0078 | N/A | `results/phase_6d/phase6g_corrections.json` | **Exploratory (Retrieval Sig / Generation Null)** |
| **C7** | GT alias leakage: 20% of cti-taa queries have leaked aliases, producing high accuracy; Fisher exact values are uncorrected and descriptive | `Leakage Share / v2_alias Accuracy` | cti-taa (N=50: Leaked=10, Clean=40) | Clean-40 | Leaked-10 | 40 vs 10 | 20.0% leakage / Fisher p (uncorrected, descriptive): LLM-only=0.0445, V0=0.0366, V0h=0.0463, Vrel=0.0920 | N/A (partition audit) | N/A | 10/10 leaked correct (LLM-only, V0h, Vrel); 9/10 (V0) | N/A | 0.0445 (LLM) / 0.0366 (V0) / 0.0463 (V0h) / 0.0920 (Vrel) [uncorrected, descriptive] | N/A | `results/phase_6d/gt_alias_leakage_audit.json` | **Robust Benchmark Defect** |
| **C8** | Survival filtering purifies entity detection precision from 74.0% to 93.9% real entity (counts only) | `Real Entity / Informative Precision` | Annotated detector matches | D0 (Raw Prompt Detections) | D1/V1h (Body-only + Survival Filter) | 89 / 66 | +10.8pp real (83.1% -> 93.9%) / +23.2pp informative (70.8% -> 93.9%) | N/A (annotated sample) | N/A | 66 surviving / 89 raw | N/A | N/A (counts only; no valid binomial null) | N/A | `results/phase_6d/phase6g_corrections.json (item6)` | **Exploratory Precision (Recall unmeasured, single annotator)** |
| **C9** | Chunk metadata tagging creates artificial recall advantage over text-visible matching (+0.1556 ate / +0.3475 att) | `Recall@B (B=500)` | cti-ate & CTI-ATTACK | Text-Visible Only | Metadata Credit | 60 / 229 | +0.1496 / +0.3516 | N/A (deterministic scoring difference) | N/A | metadata=0.2042 text=0.0546 | metadata=0.5670 text=0.2154 | N/A (deterministic scoring discrepancy; no valid test) | N/A | `results/phase_6d/metadata_credit_audit.json` | **Robust Methodological Defect** |
| **C10** | Budget expansion B=500->B=2000: CTI-ATTACK significant only; cti-ate p=0.0704; D4 null | `Technique F1 (f1_sub)` | cti-ate (N=60) & CTI-ATTACK (N=229) | HD B=500 | D1 B=2000 / D4 Hybrid B=2000 | 60 / 229 | +0.0496 (D1) / +0.0354 (D4) / +0.0599 | [+0.0030, +0.0969] | [+0.0212, +0.0985] | 33/8/19 (D1) | 60/141/28 | 0.0704 (D1 sign p) / p=0.0704 (ate) / 0.6778 (D4 null) | 0.0008 | `results/phase_6d/generation_contrasts.json` | **Exploratory** |

---

## Holm Primary Family (M=4, Pre-Declared)

| Rank | ID | Comparison | Metric | Δ | W/T/L | Raw p | Holm α* | Decision |
| :---: | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| 1 | `GEN_02` | HD vs LLM-only (CTI-ATTACK) | f1_sub | -0.0970 | 44/102/83 | 0.0007 | 0.0125 | **Statistically Significant** |
| 2 | `GEN_01` | HD vs LLM-only (cti-ate) | f1_sub | -0.0698 | 18/6/36 | 0.0198 | 0.01667 | **Not Significant** |
| 3 | `GEN_03` | V0h vs LLM-only (cti-taa) | v2_alias | +0.0200 | 7/37/6 | 1.0000 | 0.025 | **Not Significant** |
| 4 | `GEN_04` | Vrel vs V0h (cti-taa) | v2_alias | +0.0200 | 3/45/2 | 1.0000 | 0.05 | **Not Significant** |

## Post-Hoc Exploratory Family (M=2, HD vs Raw E0' Hygiene)

| Rank | ID | Comparison | Metric | Δ | W/T/L | Raw p | Holm α* | Decision |
| :---: | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| 1 | `HYG_01` | HD vs E0' (cti-ate) | f1_sub | -0.0855 | 17/7/36 | 0.0127 | 0.025 | **Significant** |
| 2 | `HYG_02` | HD vs E0' (CTI-ATTACK) | f1_sub | +0.0540 | 64/112/53 | 0.3553 | 0.05 | **Not Significant** |

---

## cti-taa Headline Comparison Table

| Section (Metric) | Arm | Full-50 | Clean-40 | Source File |
| :--- | :--- | :---: | :---: | :--- |
| Retrieval Recall@10 | V0 (Raw prompt, no detector/hygiene) | 0.34 | 0.4 | `results/phase_6d/phase6g_corrections.json (item8)` |
| Retrieval Recall@10 | V0h (Hygienic body-only, no expansion) | 0.14 | 0.125 | `results/phase_6d/phase6g_corrections.json (item8)` |
| Retrieval Recall@10 | Vrel (Hygienic + STIX relationship exp) | 0.32 | 0.325 | `results/phase_6d/phase6g_corrections.json (item8)` |
| Primary Generator v2_alias | LLM-only | 0.72 | 0.65 | `results/phase_6d/phase6g_corrections.json (item8)` |
| Primary Generator v2_alias | V0 (Raw prompt RAG) | 0.6 | 0.525 | `results/phase_6d/phase6g_corrections.json (item8)` |
| Primary Generator v2_alias | V0h (Hygienic RAG) | 0.74 | 0.675 | `results/phase_6d/phase6g_corrections.json (item8)` |
| Primary Generator v2_alias | Vrel (Relationship RAG, standard prompt) | 0.76 | 0.7 | `results/phase_6d/phase6g_corrections.json (item8)` |
| Primary Generator v2_alias | Vrel (Relationship RAG, hybrid prompt) | 0.74 | 0.675 | `results/phase_6d/phase6g_corrections.json (item8)` |
| Secondary Generator v2_alias | LLM-only | 0.66 | 0.575 | `results/phase_6d/phase6g_corrections.json (item8)` |
| Secondary Generator v2_alias | V0 (Raw prompt RAG) | 0.66 | 0.575 | `results/phase_6d/phase6g_corrections.json (item8)` |
| Secondary Generator v2_alias | V0h (Hygienic RAG) | 0.7 | 0.625 | `results/phase_6d/phase6g_corrections.json (item8)` |
| Secondary Generator v2_alias | Vrel (Relationship RAG) | 0.72 | 0.65 | `results/phase_6d/phase6g_corrections.json (item8)` |

> **Note**: LLM-only v2_alias full-50 = 0.72 (this is v2_alias; v1_alias = 0.68).
> Primary generator Vrel standard prompt = 0.76 / 0.70; Vrel hybrid prompt = 0.74 / 0.675.
> Secondary generator V0 = 0.66 / 0.575 (from `results/phase_6d/phase6g_corrections.json`).

---

## Key Project Findings (Descriptive)

1. **Retrieval gains do not translate proportionally to generation gains**: While query hygiene yields retrieval recall improvements on CTI-ATTACK (up to +0.4491 on E0-STIX-ENT B2 and +0.3010 on balanced ladder), downstream technique F1 at B=500 shows a null effect on CTI-ATTACK (+0.0540, p=0.3553) and a negative effect on cti-ate (−0.0855, p=0.0127).
2. **Zero-shot LLM-only obtains higher technique F1 than B=500 RAG on both datasets** (cti-ate: 0.4634 vs 0.3936; CTI-ATTACK: 0.3964 vs 0.2994). This observation is consistent with context window choking under tight budgets.
3. **Budget expansion (B=2000) partially closes the gap**: D1 at B=2000 achieves 0.4432 on cti-ate and 0.3593 on CTI-ATTACK, a significant improvement over B=500 HD on CTI-ATTACK (p<0.0001) but non-significant on cti-ate by sign test (p=0.0704).
4. **Attribution benchmark disclosures**: cti-taa contains 20% ground-truth alias leakage. On the clean 40-query subset, relationship expansion (Vrel vs V0h) recovers retrieval recall (+0.2000, p=0.0078) but generation accuracy differences remain non-significant. Recall@B uses metadata credit; text-visible values are lower (see C9).
5. **Knowledge base provenance**: The KB is an unversioned rolling MITRE ATT&CK snapshot (spec 2.1, schema 3.3.0). S9000-series objects are authentic upstream MITRE draft objects (see `results/phase_6d/kb_integrity_audit.csv`).

