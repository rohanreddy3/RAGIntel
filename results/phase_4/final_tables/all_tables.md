### Table 1: Scoring Gap Analysis (Exact vs Alias-Aware Matching)

#### A. Retrieval Attribution Recall@10 (`cti-taa`, E0-STIX-ALL, $N=50$)
| Evaluation Baseline | $S_{\text{exact}}$ Rec@10 | $S_{\text{alias}}$ Rec@10 | Recall@10 Gap | 95% Bootstrap CI | $S_{\text{exact}}$ MRR | $S_{\text{alias}}$ MRR | MRR Gap | 95% Bootstrap CI |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **B2 (Truncated-256)** | 0.1200 | 0.3400 | **+0.2200** | [+0.1200, +0.3400] | 0.0342 | 0.0662 | **+0.0320** | [+0.0084, +0.0612] |
| **B3 (MaxSim-Windows)** | 0.0600 | 0.1800 | **+0.1200** | [+0.0400, +0.2200] | 0.0094 | 0.0608 | **+0.0514** | [+0.0195, +0.0898] |

#### B. Generation Threat Actor Attribution Accuracy (`cti-taa`, $N=50$)
| Generation Arm | Scorer V1 Exact | Scorer V1 Alias | Scorer V1 Gap | Scorer V2 Exact | Scorer V2 Alias | Scorer V2 Gap | Primary Scorer V2 Alias Gain |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **LLM-only** | 0.6000 | 0.6800 | +0.0800 | 0.6800 | 0.7200 | +0.0400 | **0.7200** |
| **cti-taa B2 V0 (RAG Baseline)** | 0.4000 | 0.5600 | +0.1600 | 0.5000 | 0.6000 | +0.1000 | **0.6000** |
| **cti-taa B2 V1 (RAG + Entity O1)** | 0.3800 | 0.4400 | +0.0600 | 0.4000 | 0.4600 | +0.0600 | **0.4600** |

**Scorer Definitions:**
- **Scorer V1 (Text-Regex Matching)**: Matches ground-truth canonical name or standard regex-defined aliases directly as substrings within the LLM raw generated text.
- **Scorer V2 (Ontology-Aware Resolution)**: Extracts entity mentions from LLM text and resolves them against the full STIX 2.0 knowledge base (including all recorded intrusion-set aliases) to match the canonical threat actor object.

### Table 2: Pre-Registered Confirmatory Family $P_1$ (`cti-taa`, E0-STIX-ALL, $N=50$)
| Test ID | Baseline | Contrast | Metric | Treatment Mean | Control Mean | $\Delta$ | 95% Bootstrap CI | Raw $p$-value | Holm Critical $\alpha$ | Sig under Holm? |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **P1_01** | B2 | V1 vs V0 | Recall@10 | 0.3000 | 0.3400 | -0.0400 | [-0.2400, +0.1600] | 0.7670 | 0.02500 (rank 7) | NO |
| **P1_02** | B2 | V1 vs V0 | MRR | 0.1584 | 0.0662 | +0.0922 | [-0.0031, +0.1994] | 0.0721 | 0.00714 (rank 2) | NO |
| **P1_03** | B2 | V1 vs V3 (seeds 42-46) | Recall@10 | 0.3000 | 0.2520 | +0.0480 | [-0.0800, +0.1800] | 0.4892 | 0.01250 (rank 5) | NO |
| **P1_04** | B2 | V1 vs V3 (seeds 42-46) | MRR | 0.1584 | 0.0650 | +0.0934 | [+0.0186, +0.1797] | 0.0223 | 0.00625 (rank 1) | NO |
| **P1_05** | B3 | V1 vs V0 | Recall@10 | 0.1800 | 0.1800 | +0.0000 | [-0.1600, +0.1600] | 1.0000 | 0.05000 (rank 8) | NO |
| **P1_06** | B3 | V1 vs V0 | MRR | 0.1051 | 0.0608 | +0.0443 | [-0.0489, +0.1417] | 0.3654 | 0.01000 (rank 4) | NO |
| **P1_07** | B3 | V1 vs V3 (seeds 42-44) | Recall@10 | 0.1800 | 0.2067 | -0.0267 | [-0.1200, +0.0667] | 0.6029 | 0.01667 (rank 6) | NO |
| **P1_08** | B3 | V1 vs V3 (seeds 42-44) | MRR | 0.1051 | 0.0694 | +0.0357 | [-0.0297, +0.1129] | 0.3193 | 0.00833 (rank 3) | NO |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| *Sensitivity Analysis (Seed-42-Only Control)* | | | | | | | | | | |
| *P1_03 (seed 42)* | B2 | V1 vs V3 (seed 42) | Recall@10 | 0.3000 | 0.3000 | +0.0000 | [-0.1400, +0.1400] | 1.0000 | --- | Sens. |
| *P1_04 (seed 42)* | B2 | V1 vs V3 (seed 42) | MRR | 0.1584 | 0.0753 | +0.0832 | [+0.0152, +0.1595] | 0.0230 | --- | Sens. |
| *P1_07 (seed 42)* | B3 | V1 vs V3 (seed 42) | Recall@10 | 0.1800 | 0.3200 | -0.1400 | [-0.2800, +0.0000] | 0.0592 | --- | Sens. |
| *P1_08 (seed 42)* | B3 | V1 vs V3 (seed 42) | MRR | 0.1051 | 0.1054 | -0.0003 | [-0.0841, +0.0879] | 0.9944 | --- | Sens. |

### Table 3: Secondary Family $S_1$ (Transfer and Alternative Variant Analysis)
| Category | Dataset | Baseline | Contrast | Metric | Treatment Mean | Control Mean | $\Delta$ | Status |
| :--- | :--- | :--- | :--- | :--- | :---: | :---: | :---: | :--- |
| Transfer | `cti-ate` | B2 | V1 vs V0 | Recall@10 | 0.0158 | 0.0844 | -0.0686 | Negative delta |
| Transfer | `cti-ate` | B2 | V1 vs V0 | MRR | 0.0128 | 0.1388 | -0.1260 | Negative delta |
| Transfer | `cti-ate` | B3 | V1 vs V0 | Recall@10 | 0.0264 | 0.1047 | -0.0783 | Negative delta |
| Transfer | `cti-ate` | B3 | V1 vs V0 | MRR | 0.0778 | 0.1603 | -0.0825 | Negative delta |
| Transfer | `CTI-ATTACK` | B2 | V1 vs V0 | Recall@10 | 0.1987 | 0.1900 | +0.0087 | Neutral |
| Transfer | `CTI-ATTACK` | B2 | V1 vs V0 | MRR | 0.0833 | 0.0823 | +0.0010 | Neutral |
| Transfer | `CTI-ATTACK` | B3 | V1 vs V0 | Recall@10 | 0.1987 | 0.1900 | +0.0087 | Neutral |
| Transfer | `CTI-ATTACK` | B3 | V1 vs V0 | MRR | 0.0833 | 0.0823 | +0.0010 | Neutral |
| Variant V2 | `cti-taa` | B2 | V2 vs V0 | Recall@10 | 0.3800 | 0.3400 | +0.0400 | Positive delta |
| Variant V2 | `cti-taa` | B2 | V2 vs V0 | MRR | 0.1330 | 0.0662 | +0.0668 | Positive delta |
| Variant V2 | `cti-taa` | B3 | V2 vs V0 | Recall@10 | 0.2200 | 0.1800 | +0.0400 | Positive delta |
| Variant V2 | `cti-taa` | B3 | V2 vs V0 | MRR | 0.0760 | 0.0608 | +0.0152 | Positive delta |
| Secondary KB | `cti-taa` | B2 | V1 vs V0 | Recall@10 | 0.3000 | 0.3600 | -0.0600 | Negative delta |
| Secondary KB | `cti-taa` | B2 | V1 vs V0 | MRR | 0.1519 | 0.1014 | +0.0505 | Positive delta |
| Secondary KB | `cti-taa` | B3 | V1 vs V0 | Recall@10 | 0.2400 | 0.1600 | +0.0800 | Positive delta |
| Secondary KB | `cti-taa` | B3 | V1 vs V0 | MRR | 0.1033 | 0.0717 | +0.0316 | Positive delta |

### Table 4: Primary Confirmatory Family $P_2'$ with Credit-Rule Sensitivity ($B^*=500$ tokens)

#### A. Primary Credit Rule: Text + Metadata Mention (`text_and_metadata`)
| Test ID | Target Dataset | Baseline | Contrast ($B^*=500$) | Treatment Mean | Control Mean | $\Delta$ | 95% Bootstrap CI | Raw $p$-value | Holm Critical $\alpha$ | Sig under Holm? |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **P2'_01** | `cti-ate` | B2 | E1b_mixed vs E0_prime | 0.0733 | 0.0517 | +0.0216 | [-0.0060, +0.0502] | 0.1295 | 0.05000 (rank 3) | NO |
| **P2'_02** | `cti-ate` | B3 | E1b_mixed vs E0_prime | 0.0711 | 0.1126 | -0.0415 | [-0.0809, -0.0016] | 0.0401 | 0.02500 (rank 2) | NO |
| **P2'_03/04** | `CTI-ATTACK` | B2/B3 | E1b-MIXED vs E0' (B2/B3 identical) | 0.0240 | 0.1725 | -0.1485 | [-0.1943, -0.1048] | < 0.0001 | 0.01667 (rank 1) | **Significant decrease** |
| *Guard* | `cti-taa` | B2 | E1b_mixed vs E0_prime (Recall@10) | 0.1000 | 0.3000 | -0.2000 | [-0.3400, -0.0600] | 0.0064 | Threshold -0.05 | **FAILED** |

#### B. Secondary Credit Rule: Metadata-Only (`metadata_only` Sensitivity)
| Test ID | Target Dataset | Baseline | Contrast ($B^*=500$) | Treatment Mean | Control Mean | $\Delta$ | 95% Bootstrap CI | Raw $p$-value | Holm Critical $\alpha$ | Sig under Holm? |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **P2'_01** | `cti-ate` | B2 | E1b_mixed vs E0_prime | 0.0178 | 0.0113 | +0.0066 | [-0.0078, +0.0218] | 0.3832 | 0.05000 (rank 3) | NO |
| **P2'_02** | `cti-ate` | B3 | E1b_mixed vs E0_prime | 0.0422 | 0.0734 | -0.0312 | [-0.0598, -0.0026] | 0.0333 | 0.02500 (rank 2) | NO |
| **P2'_03/04** | `CTI-ATTACK` | B2/B3 | E1b-MIXED vs E0' (B2/B3 identical) | 0.0000 | 0.0371 | -0.0371 | [-0.0611, -0.0153] | 0.0038 | 0.01667 (rank 1) | **Significant decrease** |

### Table 5: Recall@B Scaling Curves across Token Budgets ($B \in \{500, 1000, 2000, 4000\}$)

#### A. `cti-ate` (Baseline B2, Recall Sub-Credits Parent)
| Experimental Arm | Corpus / Method Description | $B=500$ | $B=1000$ | $B=2000$ | $B=4000$ |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **`E0_prime`** | Baseline Splitter (All 2,062 STIX Objects) | 0.0517 | 0.1441 | 0.2584 | 0.2915† |
| **`E0_prime_tech`** | Controlled Splitter (Technique Objects Only) | 0.1684 | 0.3215 | 0.4667 | 0.4959† |
| **`E1a`** | Field Chunks (Technique Objects Only) | 0.0890 | 0.1641 | 0.2987 | 0.5819 |
| **`E1_mixed`** | Unified Mixed Index (No Siblings) | 0.0866 | 0.1124 | 0.2041 | 0.3786 |
| **`E1b_mixed`** | Sibling Expansion on Mixed Index | 0.0733 | 0.1096 | 0.1291 | 0.1694 |
| **`E1c_mixed`** | Random Sibling Control on Mixed Index | 0.0695 | 0.1001 | 0.1616 | 0.2800 |

#### B. `CTI-ATTACK` (Baseline B2, Recall Sub-Credits Parent)
| Experimental Arm | Corpus / Method Description | $B=500$ | $B=1000$ | $B=2000$ | $B=4000$ |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **`E0_prime`** | Baseline Splitter (All 2,062 STIX Objects) | 0.1725 | 0.2707 | 0.3974† | 0.3974† |
| **`E0_prime_tech`** | Controlled Splitter (Technique Objects Only) | 0.1310 | 0.2249 | 0.3690† | 0.3690† |
| **`E1a`** | Field Chunks (Technique Objects Only) | 0.0699 | 0.1201 | 0.1834 | 0.3013 |
| **`E1_mixed`** | Unified Mixed Index (No Siblings) | 0.0546 | 0.1048 | 0.1725 | 0.2555 |
| **`E1b_mixed`** | Sibling Expansion on Mixed Index | 0.0240 | 0.0349 | 0.0786 | 0.1485 |
| **`E1c_mixed`** | Random Sibling Control on Mixed Index | 0.0371 | 0.0808 | 0.1397 | 0.2402 |

*† Non-binding budget: Context reached the top-k=50 chunk retrieval ceiling before exhausting the token budget (chunks plateaued at 50.0, context tokens plateaued at 1380–1574 tokens). Excluded from comparative scaling evaluations.*

### Table 6: Generation-Level Technique Extraction Family $G_1$ and Exploratory Contrasts

#### A. Confirmatory Family $G_1$: Technique $F_1$ (`sub_credit`) under $B^*=500$ tokens
| Test ID | Dataset | Evaluated Rows | Contrast | Treatment Mean | Control Mean | $\Delta$ | 95% Bootstrap CI | Raw $p$-value | Holm Critical $\alpha$ | Sig under Holm? | W/T/L |
| :--- | :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **G1_01** | `cti-ate` | 60 | E1b-MIXED vs E0' | 0.3452 | 0.4792 | -0.1340 | [-0.1793, -0.0911] | < 0.0001 | 0.0250 (rank 1) | **Significant decrease** | 7/9/44 |
| **G1_02** | `CTI-ATTACK` | 182 | E1b-MIXED vs E0' | 0.0772 | 0.2364 | -0.1592 | [-0.2125, -0.1069] | < 0.0001 | 0.0500 (rank 2) | **Significant decrease** | 16/99/67 |

#### B. Threat Actor Attribution Generation Contrasts (`cti-taa`, $N=50$, Matched Budget $B=500$)
| Contrast | Evaluated Rows | Scorer / Metric | Treatment Mean | Control Mean | $\Delta$ | 95% Bootstrap CI | Raw $p$-value | W/T/L | Description |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| cti-taa B2 V0 vs LLM-only | 50 | Scorer V2 (Ontology) | 0.6000 | 0.7200 | -0.1200 | [-0.2400, +0.0000] | 0.0685 | 2/40/8 | Exploratory |
| cti-taa B2 V0 vs LLM-only | 50 | Scorer V1 (Text) | 0.5600 | 0.6800 | -0.1200 | [-0.2400, +0.0000] | 0.0694 | 2/40/8 | Exploratory |
| cti-taa B2 V1 vs cti-taa B2 V0 | 50 | Scorer V2 (Ontology) | 0.4600 | 0.6000 | -0.1400 | [-0.2800, +0.0000] | 0.0630 | 3/37/10 | Exploratory |
| cti-taa B2 V1 vs cti-taa B2 V0 | 50 | Scorer V1 (Text) | 0.4400 | 0.5600 | -0.1200 | [-0.2600, +0.0200] | 0.1357 | 4/36/10 | Exploratory |
| cti-taa B2 V1 vs LLM-only | 50 | Scorer V2 (Ontology) | 0.4600 | 0.7200 | -0.2600 | [-0.3800, -0.1400] | < 0.0001 | 0/37/13 | Exploratory |
| cti-taa B2 V1 vs LLM-only | 50 | Scorer V1 (Text) | 0.4400 | 0.6800 | -0.2400 | [-0.3800, -0.1200] | 0.0006 | 1/36/13 | Exploratory |

#### C. Exploratory Technique Extraction Contrasts (Descriptive, Uncorrected)
| Contrast | Dataset | Evaluated Rows | Metric | Treatment Mean | Control Mean | $\Delta$ | 95% Bootstrap CI | Raw $p$-value | W/T/L | Status |
| :--- | :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| $E_0'$ vs LLM-only | `cti-ate` | 60 | Technique F1 (sub) | 0.4792 | 0.4634 | +0.0157 | [-0.0196, +0.0511] | 0.3867 | 30/6/24 | Exploratory |
| $E_0'$ vs LLM-only | `CTI-ATTACK` | 229 | Technique F1 (sub) | 0.2454 | 0.3964 | -0.1510 | [-0.1975, -0.1051] | < 0.0001 | 37/104/88 | Exploratory |
| $E_{1b}\text{-MIXED}$ vs LLM-only | `cti-ate` | 60 | Technique F1 (sub) | 0.3452 | 0.4634 | -0.1182 | [-0.1626, -0.0739] | < 0.0001 | 12/6/42 | Exploratory |
| $E_{1b}\text{-MIXED}$ vs LLM-only | `CTI-ATTACK` | 182 | Technique F1 (sub) | 0.0772 | 0.3952 | -0.3180 | [-0.3708, -0.2653] | < 0.0001 | 6/72/104 | Exploratory |

### Table 7: Comprehensive RAGIntel Scientific Claims Audit
| ID | Formal Hypothesis / Claim | Supporting Evidence File | Status | Empirical Finding / Summary |
| :---: | :--- | :--- | :---: | :--- |
| C1 | Family P1: Query entity resolution (V1) statistically significantly improves threat actor attribution recall on cti-taa over raw query (V0). | `results/phase_2/regenerated_p1_table.json` | **Not Supported** | Delta Recall@10 = -0.0400 on B2 (p=0.7670) and 0.0000 on B3 (p=1.0000). All 8 tests non-significant under Holm correction. |
| C2 | Family P1 Sensitivity: Query entity resolution (V1) achieves positive reciprocal rank precision (MRR) gain over length-matched random control (V3). | `results/phase_2/regenerated_p1_table.json` | **Exploratory** | Under B2, Delta MRR = +0.0934 (95% CI [+0.0186, +0.1797], unadjusted p=0.0223). Loses significance after Holm step-down correction. |
| C3 | Family S1: Query entity resolution transfers positively to technique extraction on cti-ate and CTI-ATTACK. | `results/phase_2/o1_benchmark_results.json` | **Not Supported** | Measured Recall@10 decreases from 0.0844 to 0.0158 on cti-ate under B2 when entity prefix is added. |
| C4 | Family P2': Structure-aware sibling expansion (E1b-MIXED) improves technique retrieval recall over baseline splitter (E0') at B*=500. | `results/phase_3/o2_phase3c_benchmark_results.json` | **Not Supported** | Significant negative delta on CTI-ATTACK (Delta = -0.1485, p < 0.0001); non-significant on cti-ate B2 (Delta = +0.0216, p=0.1295). |
| C5 | cti-taa Guard: Sibling expansion (E1b-MIXED) preserves threat actor attribution recall within 5% of E0'. | `results/phase_3/o2_phase3c_benchmark_results.json` | **Not Supported** | Recall@10 drops from 0.3000 to 0.1000 (Delta = -0.2000, 95% CI [-0.34, -0.06], p=0.0064). Guard formally fails. |
| C6 | Unified Mixed Indexing (E1-MIXED without siblings) preserves actor attribution retrieval recall on cti-taa. | `results/phase_4b/a8_recompute.json` | **Not established** | At matched 500-token budget on cti-taa B2, E1-MIXED (no siblings) achieved 0.0000 object-level recall vs E0' 0.0200 (Delta = -0.0200), and 0.0400 text-inclusive recall vs E0' 0.3000 (Delta = -0.2600). The earlier +0.30 gain was evaluated without token budget constraints. |
| C7 | Family G1: Structure-aware sibling expansion (E1b-MIXED) improves downstream LLM extraction F1 over E0' at B*=500. | `results/phase_4/per_query_technique_f1.csv` | **Not Supported** | Significantly lower F1 on cti-ate (Delta = -0.1340, p < 0.0001) and CTI-ATTACK (Delta = -0.1592, p < 0.0001). |
| C8 | RAG Retrieval Advantage: Retrieved STIX context improves threat actor attribution over direct LLM parametric generation (LLM-only). | `results/phase_4/per_query_cti_taa_attribution.csv` | **Not Supported** | LLM-only parametric memory achieves 0.68-0.72 accuracy, outperforming RAG retrieval arms V0 (0.56-0.60) and V1 (0.44-0.46). Caveat: High LLM-only performance may reflect pre-training data contamination on public threat intelligence reports rather than superior reasoning (hypothesis). |
| C9 | STIX Retrieval Scoring Gap: Exact canonical matching (S_exact) underestimates attribution recall relative to alias-aware matching (S_alias). | `results/phase_2/s_exact_vs_alias_comparison.json` | **Supported** | Scoped to STIX retrieval alias expansion: S_alias adds +0.1200 to +0.2200 to measured retrieval Recall@10 across evaluated baselines and knowledge bases (95% CIs exclude zero). |
| C10 | Field Chunking Alone (E1a) improves technique retrieval recall over monolithic recursive splitting (E0'-TECH) at B*=500. | `results/phase_3/o2_phase3c_benchmark_results.json` | **Not Supported** | At B=500, E1a is lower than E0'-TECH on cti-ate (0.0890 vs 0.1684) and CTI-ATTACK (0.0699 vs 0.1310); only excels at B >= 4000. |