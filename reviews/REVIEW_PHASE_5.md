# Phase 5 Review: Pre-Declared Fixes and Improvement Round

**Date**: 2026-10-23  
**Evaluation Status**: Post-hoc Round 2, Exploratory (`cti-taa` was previously observed)  
**Execution Environment**: Strict offline evaluation (`OFFLINE_ONLY=true`), multi-threading capped at 4 threads (`OMP_NUM_THREADS=4`, `torch.set_num_threads(4)`), single heavy process execution.  
**Pre-Registration Ledger**: [results/phase_5/variants_ledger.json](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/results/phase_5/variants_ledger.json) (SHA-256: `6216f77f6380ad4936d6a591e0a297be7bba31ba8ec202237976865d491eb3a7`, registered `2026-10-23T05:49:08Z`).  
**Cryptographic Freeze Manifest**: [results/freeze_manifest.json](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/results/freeze_manifest.json).

---

## 1. Executive Summary & Plain List of Statistical Decisions

All analyses in Phase 5 were pre-registered in Section 10 of [analysis_plan.md](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/analysis_plan.md) and frozen in the cryptographic ledger before computing any results. All variant rules derived exclusively from STIX knowledge base properties and benchmark prompt instruction boilerplate, with zero reference to ground-truth labels. In compliance with methodological rule R4, all findings are described using strictly non-causal statistical terminology.

### Plain List of Contrasts (Numbers Only)

#### A. Contrasts that Exhibited Statistically Significant Increases (Post-Hoc Round 2)
1. **P3_03** (`cti-taa` B2, Primary Object-Level Recall@10): $V_{\text{rel}}$ vs $V_{0h}$
   - Treatment Mean: $0.3200$, Control Mean: $0.1400$
   - Difference: $\Delta = +0.1800$ (95% Bootstrap CI $[+0.0600, +0.3000]$)
   - Concordance / Discordance: 10 wins, 39 ties, 1 loss (sum of diffs = $+9.0$)
   - Statistical Tests: $p_{\text{exact}} = 0.0117$ (two-sided binomial sign test / McNemar), $p_{\text{boot}} = 0.0054$ (paired bootstrap, 10,000 resamples)
   - Multiplicity Decision: Statistically significant under Holm step-down correction at rank 1 ($\alpha_1 = 0.00625$).
2. **P3_11** (`cti-taa` B2, Secondary Text-Inclusive Recall@10): $V_{\text{rel}}$ vs $V_{0h}$
   - Treatment Mean: $0.5000$, Control Mean: $0.3000$
   - Difference: $\Delta = +0.2000$ (95% Bootstrap CI $[+0.0800, +0.3200]$)
   - Concordance / Discordance: 11 wins, 38 ties, 1 loss (sum of diffs = $+10.0$)
   - Statistical Tests: $p_{\text{exact}} = 0.0063$, $p_{\text{boot}} = 0.0020$
   - Multiplicity Decision: Statistically significant under Holm step-down correction at rank 1 ($\alpha_1 = 0.00625$).
3. **P3_12** (`cti-taa` B2, Secondary Text-Inclusive MRR): $V_{\text{rel}}$ vs $V_{0h}$
   - Treatment Mean: $0.2931$, Control Mean: $0.1455$
   - Difference: $\Delta = +0.1475$ (95% Bootstrap CI $[+0.0446, +0.2502]$)
   - Concordance / Discordance: 19 wins, 29 ties, 2 losses (sum of diffs = $+7.376$)
   - Statistical Tests: $p_{\text{exact}} = 0.0002$, $p_{\text{boot}} = 0.0048$
   - Multiplicity Decision: Statistically significant under Holm step-down correction at rank 2 ($\alpha_2 = 0.00714$).
4. **Query Hygiene Effect Alone** ($E_0'$ HD vs $E_0'$ Raw, Baseline B2 / B3):
   - `cti-ate` B2: $\text{HD} = 0.3061$ vs $\text{Raw} = 0.1514$ ($\Delta = +0.1547$, 95% CI $[+0.0956, +0.2184]$, $p < 0.0001$, W/T/L: 44/4/12).
   - `cti-ate` B3: $\text{HD} = 0.3096$ vs $\text{Raw} = 0.2052$ ($\Delta = +0.1044$, 95% CI $[+0.0385, +0.1750]$, $p = 0.0032$, W/T/L: 36/7/17).
   - `CTI-ATTACK` B2: $\text{HD} = 0.6401$ vs $\text{Raw} = 0.2216$ ($\Delta = +0.4185$, 95% CI $[+0.3537, +0.4844]$, $p < 0.0001$, W/T/L: 122/97/10).
   - Decision: Statistically significant positive difference across all three benchmark evaluation settings.

#### B. Contrasts that Exhibited Statistically Significant Decreases (Control Arms Maintained Higher Recall)
All 6 confirmatory contrasts in Family P4 exhibited statistically significant negative differences ($\Delta < 0$), with the monolithic recursive splitting controls ($E_0'$ and $E_0'\text{-TECH}$) achieving higher Mean Binding Recall than structure-aware field chunking ($E_{1a}$) and mixed STIX-ALL ($E_1\text{-MIXED}$):
1. **P4_01** (`cti-ate` B2, Mean Binding Recall): $E_{1a}$ vs $E_0'\text{-TECH}$
   - Treatment Mean: $0.2053$, Control Mean: $0.2973$
   - Difference: $\Delta = -0.0920$ (95% Bootstrap CI $[-0.1491, -0.0366]$), $p = 0.0010$ (Holm $\alpha_4 = 0.01667$).
2. **P4_02** (`cti-ate` B2, Mean Binding Recall): $E_1\text{-MIXED}$ vs $E_0'$
   - Treatment Mean: $0.2124$, Control Mean: $0.3061$
   - Difference: $\Delta = -0.0936$ (95% Bootstrap CI $[-0.1479, -0.0407]$), $p = 0.0006$ (Holm $\alpha_3 = 0.01250$).
3. **P4_03** (`cti-ate` B3, Mean Binding Recall): $E_{1a}$ vs $E_0'\text{-TECH}$
   - Treatment Mean: $0.2154$, Control Mean: $0.2924$
   - Difference: $\Delta = -0.0771$ (95% Bootstrap CI $[-0.1306, -0.0247]$), $p = 0.0040$ (Holm $\alpha_6 = 0.05000$).
4. **P4_04** (`cti-ate` B3, Mean Binding Recall): $E_1\text{-MIXED}$ vs $E_0'$
   - Treatment Mean: $0.2196$, Control Mean: $0.3096$
   - Difference: $\Delta = -0.0900$ (95% Bootstrap CI $[-0.1444, -0.0368]$), $p = 0.0010$ (Holm $\alpha_5 = 0.02500$).
5. **P4_05** (`CTI-ATTACK` B2, Mean Binding Recall): $E_{1a}$ vs $E_0'\text{-TECH}$
   - Treatment Mean: $0.5146$, Control Mean: $0.6543$
   - Difference: $\Delta = -0.1397$ (95% Bootstrap CI $[-0.1764, -0.1030]$), $p < 0.0001$ (Holm $\alpha_1 = 0.00833$).
6. **P4_06** (`CTI-ATTACK` B2, Mean Binding Recall): $E_1\text{-MIXED}$ vs $E_0'$
   - Treatment Mean: $0.4687$, Control Mean: $0.6401$
   - Difference: $\Delta = -0.1714$ (95% Bootstrap CI $[-0.2084, -0.1348]$), $p < 0.0001$ (Holm $\alpha_2 = 0.01000$).

#### C. Contrasts that Did Not Achieve Statistical Significance
1. **P3_01** (`cti-taa` B2, Object-Level Recall@10): $V_{1h}$ vs $V_{0h}$ ($\Delta = +0.0200$, $p_{\text{exact}} = 1.0000$, $p_{\text{boot}} = 0.7644$).
2. **P3_02** (`cti-taa` B2, Object-Level MRR): $V_{1h}$ vs $V_{0h}$ ($\Delta = +0.0010$, $p_{\text{exact}} = 1.0000$, $p_{\text{boot}} = 0.9844$).
3. **P3_04** (`cti-taa` B2, Object-Level MRR): $V_{\text{rel}}$ vs $V_{0h}$ ($\Delta = +0.1449$, $p_{\text{exact}} = 0.0042$, $p_{\text{boot}} = 0.0121$, Holm $\alpha_2 = 0.00714$; not significant under bootstrap).
4. **P3_05** (`cti-taa` B3, Object-Level Recall@10): $V_{1h}$ vs $V_{0h}$ ($\Delta = +0.0000$, $p_{\text{exact}} = 1.0000$, $p_{\text{boot}} = 1.0000$).
5. **P3_06** (`cti-taa` B3, Object-Level MRR): $V_{1h}$ vs $V_{0h}$ ($\Delta = +0.0272$, $p_{\text{exact}} = 0.6875$, $p_{\text{boot}} = 0.2446$).
6. **P3_07** (`cti-taa` B3, Object-Level Recall@10): $V_{\text{rel}}$ vs $V_{0h}$ ($\Delta = +0.0800$, $p_{\text{exact}} = 0.2188$, $p_{\text{boot}} = 0.1399$).
7. **P3_08** (`cti-taa` B3, Object-Level MRR): $V_{\text{rel}}$ vs $V_{0h}$ ($\Delta = +0.0610$, $p_{\text{exact}} = 0.2891$, $p_{\text{boot}} = 0.0434$, Holm $\alpha_3 = 0.00833$).
8. **P3_09** (`cti-taa` B2, Text-Inclusive Recall@10): $V_{1h}$ vs $V_{0h}$ ($\Delta = +0.0800$, $p_{\text{exact}} = 0.2891$, $p_{\text{boot}} = 0.2098$).
9. **P3_10** (`cti-taa` B2, Text-Inclusive MRR): $V_{1h}$ vs $V_{0h}$ ($\Delta = +0.1203$, $p_{\text{exact}} = 0.3018$, $p_{\text{boot}} = 0.0218$, Holm $\alpha_4 = 0.01000$).
10. **P3_13** (`cti-taa` B3, Text-Inclusive Recall@10): $V_{1h}$ vs $V_{0h}$ ($\Delta = +0.0200$, $p_{\text{exact}} = 1.0000$, $p_{\text{boot}} = 0.8463$).
11. **P3_14** (`cti-taa` B3, Text-Inclusive MRR): $V_{1h}$ vs $V_{0h}$ ($\Delta = +0.1048$, $p_{\text{exact}} = 0.1460$, $p_{\text{boot}} = 0.0149$, Holm $\alpha_3 = 0.00833$).
12. **P3_15** (`cti-taa` B3, Text-Inclusive Recall@10): $V_{\text{rel}}$ vs $V_{0h}$ ($\Delta = +0.1000$, $p_{\text{exact}} = 0.1250$, $p_{\text{boot}} = 0.0797$).
13. **P3_16** (`cti-taa` B3, Text-Inclusive MRR): $V_{\text{rel}}$ vs $V_{0h}$ ($\Delta = +0.0868$, $p_{\text{exact}} = 0.2668$, $p_{\text{boot}} = 0.0310$, Holm $\alpha_5 = 0.01250$).
14. **Cross-Dataset Transfer Checks** ($V_{1h}$ vs $V_{0h}$ on technique benchmarks):
    - `cti-ate` B2: $\Delta = -0.0009$ (passes pre-registered non-inferiority margin $-0.03$).
    - `CTI-ATTACK` B2: $\Delta = +0.0000$ (passes pre-registered non-inferiority margin $-0.03$).

---

## 2. Methodological Governance & Rule Compliance

Phase 5 was conducted under five explicit methodological rules:
- **(R1) Strict Pre-Declaration**: Every variant and statistical test was recorded in Section 10 of `analysis_plan.md` and hashed in `results/phase_5/variants_ledger.json` before any computation commenced. No variants were added, dropped, or retuned.
- **(R2) Independent Derivation**: All rules and filters were derived solely from the pinned STIX ontology bundles (`data/mitre/*.json`) and prompt instruction text (`"Threat Report:"` and `"**Text:**"`), with zero exposure to dataset ground-truth labels.
- **(R3) Explicit Labeling**: All tables and narratives are designated "post-hoc round 2, exploratory", reflecting prior exposure to benchmark queries during Phases 0–4.
- **(R4) Neutral Scientific Tone**: Zero causal terms ("due to", "attributable to", "confirms", "severely", "actual cause", "true expected center", "led to", "caused by", "responsible for") appear in this review.
- **(R5) Dual Attribution Credit & STIX Mapping**: Threat actor attribution tables report both object-level (primary) and text-inclusive (secondary) credit. In `cti-taa`, exactly 40 ground-truth threat groups mapped to active STIX canonical intrusion-set objects; 6 ground-truth strings were absent from the pinned STIX knowledge base (`ANDROMEDA`, `Black Basta`, `Emotet`, `Lazarus`, `Sharp Dragon (or  Sharp Panda)`, `Sharp Panda`).

---

## 3. Part A: Query Hygiene Audit (`split_query`)

Every benchmark query across the 339 queries in RAGIntel was parsed into an instruction prefix and report body:
- **Marker Assertion**: 339 / 339 queries (100.0%) successfully matched either `"Threat Report:"` or `"**Text:**"`.
- **False Positive Elimination**: In `cti-taa`, the prompt boilerplate instruction contains an example mentioning `"APT36"` and `"Crimson"`. In Phase 2, entity resolution matched these two template strings in 50 / 50 queries (100 template false positives). Query hygiene completely eliminated all 100 template false-positive detections.

### Table 1: Query Hygiene Entity Detector Audit
| Dataset | $N$ | Body Matches / Query | Full Matches / Query | Matches Difference | Body Share $\ge 1$ Entity | Full Share $\ge 1$ Entity |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`cti-taa`** | 50 | 11.46 | 13.46 | $-2.00$ | 98.0% | 100.0% |
| **`cti-ate`** | 60 | 5.43 | 5.43 | $0.00$ | 98.3% | 98.3% |
| **`CTI-ATTACK`** | 229 | 0.99 | 0.99 | $0.00$ | 52.8% | 52.8% |

---

## 4. Part B: Optimization 1 Benchmark (High-Precision & Relationship Expansion)

Evaluated on `cti-taa` ($N=50$) across baselines B2 (standard hybrid) and B3 (multi-window MaxSim) under the body-only query hygiene protocol. All reported variants evaluate the body text only ($V_{0h}$, $V_{1h}$, $V_{\text{rel}}$).

### Table 2: O1 Retrieval Performance (Dual Credit Rules)
| Baseline | Arm | Credit Rule | Recall@10 | MRR |
| :---: | :---: | :---: | :---: | :---: |
| **B2** | $V_{0h}$ | **Object-Level (Primary)** | **0.1400** | **0.0671** |
| **B2** | $V_{1h}$ | **Object-Level (Primary)** | **0.1600** | **0.0681** |
| **B2** | $V_{\text{rel}}$ | **Object-Level (Primary)** | **0.3200** | **0.2120** |
| **B3** | $V_{0h}$ | **Object-Level (Primary)** | **0.1200** | **0.0623** |
| **B3** | $V_{1h}$ | **Object-Level (Primary)** | **0.1200** | **0.0895** |
| **B3** | $V_{\text{rel}}$ | **Object-Level (Primary)** | **0.2000** | **0.1233** |
| B2 | $V_{0h}$ | Text-Inclusive (Secondary) | 0.3000 | 0.1455 |
| B2 | $V_{1h}$ | Text-Inclusive (Secondary) | 0.3800 | 0.2658 |
| B2 | $V_{\text{rel}}$ | Text-Inclusive (Secondary) | 0.5000 | 0.2931 |
| B3 | $V_{0h}$ | Text-Inclusive (Secondary) | 0.2400 | 0.1219 |
| B3 | $V_{1h}$ | Text-Inclusive (Secondary) | 0.2600 | 0.2267 |
| B3 | $V_{\text{rel}}$ | Text-Inclusive (Secondary) | 0.3400 | 0.2087 |

### Table 3: Family P3 Confirmatory Contrasts (Exact Sign Test & Bootstrap)
| Test ID | Metric | Credit Rule | Treat | Ctrl | $\Delta$ | 95% Bootstrap CI | W/T/L | $p_{\text{exact}}$ (McNemar) | $p_{\text{boot}}$ (10k) | Holm $\alpha_k$ | Decision |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **P3_01** | Recall@10 | Object-Level | 0.1600 | 0.1400 | $+0.0200$ | $[-0.0400, +0.0800]$ | 2/47/1 | 1.0000 | 0.7644 | 0.01667 | Not significant |
| **P3_02** | MRR | Object-Level | 0.0681 | 0.0671 | $+0.0010$ | $[-0.0611, +0.0621]$ | 3/44/3 | 1.0000 | 0.9844 | 0.02500 | Not significant |
| **P3_03** | Recall@10 | Object-Level | 0.3200 | 0.1400 | $+0.1800$ | $[+0.0600, +0.3000]$ | 10/39/1 | 0.0117 | 0.0054 | 0.00625 | **Significant increase** |
| **P3_04** | MRR | Object-Level | 0.2120 | 0.0671 | $+0.1449$ | $[+0.0344, +0.2600]$ | 14/34/2 | 0.0042 | 0.0121 | 0.00714 | Not significant |
| **P3_05** | Recall@10 | Object-Level | 0.1200 | 0.1200 | $+0.0000$ | $[-0.0800, +0.0800]$ | 2/46/2 | 1.0000 | 1.0000 | 0.05000 | Not significant |
| **P3_06** | MRR | Object-Level | 0.0895 | 0.0623 | $+0.0272$ | $[-0.0100, +0.0810]$ | 4/44/2 | 0.6875 | 0.2446 | 0.01250 | Not significant |
| **P3_07** | Recall@10 | Object-Level | 0.2000 | 0.1200 | $+0.0800$ | $[+0.0000, +0.1800]$ | 5/44/1 | 0.2188 | 0.1399 | 0.01000 | Not significant |
| **P3_08** | MRR | Object-Level | 0.1233 | 0.0623 | $+0.0610$ | $[+0.0073, +0.1270]$ | 6/42/2 | 0.2891 | 0.0434 | 0.00833 | Not significant |

---

## 5. Part C: Optimization 2 Clean Comparisons (HD Preprocessing & $k=200$ Extension)

Evaluates:
- **Preprocessing HD**: Query body text only; candidate pool domain filtering derived from prompt instruction (`enterprise-attack` vs `mobile-attack` for `cti-ate`).
- **Domain Sanity Check**: 396 / 397 ground-truth IDs in `cti-ate` (99.75%) reside within the declared target domain.
- **Candidate Pool Extension ($k=200$)**: Evaluates $E_0'\text{-k200}$ and $E_0'\text{-TECH-k200}$ with a candidate pool of 200 chunks, enabling the retriever to fill 2,000 and 4,000 token budgets without candidate starvation.

### Table 4: Unified 4-Budget Scaling Table (Recall@B, sub_credit)
*Note: `[B]` indicates binding token budgets; `[C]` indicates non-binding budgets capped by candidate pool saturation.*

| Dataset | Baseline | Arm | $B=500$ | $B=1000$ | $B=2000$ | $B=4000$ | Binding Mean (AUC) |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| **`cti-ate`** | B2 | $E_0'$ ($k=50$) | 0.2091 [B] | 0.2853 [B] | 0.4239 [B] | 0.4719 [C] | **0.3061** |
| **`cti-ate`** | B2 | $E_0'\text{-TECH}$ ($k=50$) | 0.1900 [B] | 0.2834 [B] | 0.4186 [B] | 0.4842 [C] | **0.2973** |
| **`cti-ate`** | B2 | $E_{1a}$ ($k=50$) | 0.1634 [B] | 0.1970 [B] | 0.2557 [B] | 0.3854 [B] | **0.2053** |
| **`cti-ate`** | B2 | $E_1\text{-MIXED}$ ($k=50$) | 0.1585 [B] | 0.2054 [B] | 0.2735 [B] | 0.3895 [B] | **0.2124** |
| **`cti-ate`** | B2 | $E_0'\text{-k200}$ (pool=200) | 0.2042 [B] | 0.2812 [B] | 0.4201 [B] | 0.5695 [B] | **0.3688** |
| **`cti-ate`** | B2 | $E_0'\text{-TECH-k200}$ (pool=200) | 0.1768 [B] | 0.2899 [B] | 0.4168 [B] | 0.5704 [B] | **0.3635** |
| **`CTI-ATTACK`** | B2 | $E_0'$ ($k=50$) | 0.5953 [B] | 0.6849 [B] | 0.6914 [C] | 0.6914 [C] | **0.6401** |
| **`CTI-ATTACK`** | B2 | $E_0'\text{-TECH}$ ($k=50$) | 0.6237 [B] | 0.6849 [B] | 0.7023 [C] | 0.7023 [C] | **0.6543** |
| **`CTI-ATTACK`** | B2 | $E_{1a}$ ($k=50$) | 0.4316 [B] | 0.5975 [B] | 0.6805 [B] | 0.7475 [B] | **0.5146** |
| **`CTI-ATTACK`** | B2 | $E_1\text{-MIXED}$ ($k=50$) | 0.4054 [B] | 0.5320 [B] | 0.6477 [B] | 0.7023 [B] | **0.4687** |
| **`CTI-ATTACK`** | B2 | $E_0'\text{-k200}$ (pool=200) | 0.5670 [B] | 0.6477 [B] | 0.7525 [B] | 0.8159 [B] | **0.6958** |
| **`CTI-ATTACK`** | B2 | $E_0'\text{-TECH-k200}$ (pool=200) | 0.5713 [B] | 0.6543 [B] | 0.7438 [B] | 0.8202 [B] | **0.6974** |

### Table 5: Confirmatory Family P4 Contrasts (Holm Step-Down on Binding Mean)
| Holm Rank | Test ID | Description | Treat | Ctrl | $\Delta$ | 95% Bootstrap CI | Empirical $p$ | Holm $\alpha_k$ | Decision |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **1** | **P4_05** | $E_{1a}$ vs $E_0'\text{-TECH}$ (`CTI-ATTACK` B2) | 0.5146 | 0.6543 | $-0.1397$ | $[-0.1764, -0.1030]$ | $< 0.0001$ | 0.00833 | **Significant decrease** |
| **2** | **P4_06** | $E_1\text{-MIXED}$ vs $E_0'$ (`CTI-ATTACK` B2) | 0.4687 | 0.6401 | $-0.1714$ | $[-0.2084, -0.1348]$ | $< 0.0001$ | 0.01000 | **Significant decrease** |
| **3** | **P4_02** | $E_1\text{-MIXED}$ vs $E_0'$ (`cti-ate` B2) | 0.2124 | 0.3061 | $-0.0936$ | $[-0.1479, -0.0407]$ | 0.0006 | 0.01250 | **Significant decrease** |
| **4** | **P4_01** | $E_{1a}$ vs $E_0'\text{-TECH}$ (`cti-ate` B2) | 0.2053 | 0.2973 | $-0.0920$ | $[-0.1491, -0.0366]$ | 0.0010 | 0.01667 | **Significant decrease** |
| **5** | **P4_04** | $E_1\text{-MIXED}$ vs $E_0'$ (`cti-ate` B3) | 0.2196 | 0.3096 | $-0.0900$ | $[-0.1444, -0.0368]$ | 0.0010 | 0.02500 | **Significant decrease** |
| **6** | **P4_03** | $E_{1a}$ vs $E_0'\text{-TECH}$ (`cti-ate` B3) | 0.2154 | 0.2924 | $-0.0771$ | $[-0.1306, -0.0247]$ | 0.0040 | 0.05000 | **Significant decrease** |

---

## 6. Table 7 Claims Audit Reconciliation (Phase 4 vs Phase 4B vs Phase 5)

### Table 6: Claims Audit Reconciliation Matrix
| ID | Phase 4 Claim & Status | Phase 4B Narrative Statement | Phase 5 Reconciled Finding & Final Status |
| :---: | :--- | :--- | :--- |
| **C1** | **Not Supported**<br>Query entity resolution (V1) improves attribution recall on cti-taa over raw query (V0). | Maintained as Not Supported. | **Not Supported**. Under body-only hygiene (Part B), V1h achieves Recall@10 = 0.16 vs V0h = 0.14 ($\Delta = +0.02$, $p_{\text{exact}} = 1.000$, $p_{\text{boot}} = 0.7644$; non-significant under Holm correction). |
| **C2** | **Exploratory**<br>V1 achieves MRR gain over random control (V3). | Maintained as Exploratory. | **Exploratory**. Unadjusted $p = 0.0223$ in Phase 2; non-significant after Holm step-down correction. |
| **C3** | **Not Supported**<br>Query entity resolution transfers positively to technique extraction. | Maintained as Not Supported. | **Not Supported**. Under Part B body-only hygiene, non-inferiority margin ($-0.03$) passes on `cti-ate` ($\Delta = -0.0009$) and `CTI-ATTACK` ($\Delta = +0.0000$). |
| **C4** | **Not Supported**<br>Structure-aware sibling expansion (E1b-MIXED) improves technique recall over E0'. | Maintained as Not Supported. | **Not Supported**. Significant negative difference on `CTI-ATTACK` ($\Delta = -0.1485$, $p < 0.0001$). |
| **C5** | **Not Supported**<br>Sibling expansion preserves threat actor attribution recall within 5% of E0'. | Maintained as Not Supported. | **Not Supported**. Recall@10 decreases from 0.3000 to 0.1000 ($\Delta = -0.2000$, $p = 0.0064$). |
| **C6** | **Supported** (earlier unconstrained)<br>Unified Mixed Indexing (E1-MIXED without siblings) preserves attribution recall. | Reclassified to **Not established**. | **Not established**. The earlier $+0.30$ gain was evaluated without token budget constraints; under matched 500-token budget, $\Delta = -0.0200$ (object-level) and $-0.2600$ (text-inclusive). |
| **C7** | **Not Supported**<br>Sibling expansion improves downstream LLM extraction F1 over E0' at B*=500. | Maintained as Not Supported. | **Not Supported**. Lower F1 on `cti-ate` ($\Delta = -0.1340$) and `CTI-ATTACK` ($\Delta = -0.1592$). |
| **C8** | **Not Supported**<br>Retrieved STIX context improves attribution over LLM parametric memory. | Maintained with test-set contamination caveat. | **Not Supported**. Parametric memory achieves 0.72 accuracy without retrieval context; test-set contamination caveat maintained. |
| **C9** | **Supported**<br>STIX Retrieval Scoring Gap: Canonical matching (S_exact) underestimates recall relative to alias matching (S_alias). | Errant narrative scoping: conflated entity linking with scoring gap and referenced "P1_08 -0.12". | **RESTORED to original ID and claim: Supported**. S_alias adds $+0.1200$ to $+0.2200$ to Recall@10 over S_exact across all evaluated baselines and KBs (`results/phase_2/s_exact_vs_alias_comparison.json`). **Corrections Applied**: (1) "P1_08 -0.12" reference was erroneous; P1_08 evaluated MRR on B3 ($\Delta = +0.0357$), while $-0.12$ was from V0 vs LLM-only generation accuracy. (2) V1 recall on `cti-taa` B2 was 0.22 under S_exact and 0.30 under S_alias ($+0.08$ scorer gap). (3) Phase 4B V1-strict numbers are deprecated and replaced by Phase 5 Part B body-only numbers. |
| **C10** | **Not Supported**<br>Field Chunking Alone (E1a) improves technique retrieval recall over E0'-TECH at B*=500. | Maintained as Not Supported. | **Not Supported**. Under B*=500, E1a achieves lower recall than E0'-TECH on `cti-ate` (0.0890 vs 0.1684) and `CTI-ATTACK` (0.0699 vs 0.1310); only excels at B $\ge$ 4000. |

---

## 7. Limitations Table Addendum: Ground-Truth STIX Status

In compliance with Addendum Requirement 7, all ground-truth entities across benchmark datasets were audited against the pinned STIX ontology knowledge base:

### Table 7: Ground-Truth STIX Status in Pinned Knowledge Base
| Dataset | Total Unique GT Entities | Active in Pinned KB | Revoked in Pinned KB | Deprecated in Pinned KB | Absent in Pinned KB | Non-Active Share (%) | Specific Non-Active Entities |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **`cti-ate`** | 115 | 114 | 1 | 0 | 0 | 0.87% | Revoked: `T1562` |
| **`CTI-ATTACK`** | 115 | 109 | 6 | 0 | 0 | 5.22% | Revoked: `T1024`, `T1035`, `T1070.001`, `T1508`, `T1562.001`, `T1562.004` |
| **`cti-taa`** | 46 | 40 | 0 | 0 | 6 | 13.04% | Absent: `ANDROMEDA`, `Black Basta`, `Emotet`, `Lazarus`, `Sharp Dragon (or  Sharp Panda)`, `Sharp Panda` |

---

## 8. Part D: API Telemetry & Generation Safeguard

- **API Telemetry Configuration**: In accordance with Addendum Item 6, all API calls store `finish_reason` and token `usage` metadata (`prompt_tokens`, `completion_tokens`, `total_tokens`), and technique/group identifiers are parsed across the entire response string.
- **Quota Safeguard**: Per Section 10.6 of `analysis_plan.md`, the Gemini API daily limit was reached (500 / 500 calls in rolling 24h window; 429 RESOURCE_EXHAUSTED logged in `reviews/api_status.md`). Generation ablation execution is formally deferred under the Section 10.6 quota safeguard without invalidating offline retrieval protocols.

---

## 9. Verification & Cryptographic Manifest

- All Phase 5 data, code, and review artifacts were verified bit-exact.
- [results/freeze_manifest.json](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/results/freeze_manifest.json) records the SHA-256 hashes for all 83 verified repository artifacts.
