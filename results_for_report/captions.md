# Figure and Table Captions & Evidence Mapping

This document provides a one-line caption for every figure and table in `results_for_report/`, specifying what it shows and which empirical claim in `RESULTS_MASTER.md` it supports.

## Figures (`results_for_report/figures/`)

- **Figure F1 (`F1_hygiene_effect.png` / `.svg`)**: Shows the query hygiene delta across four evaluation regimes on `cti-ate` and `CTI-ATTACK` with 95% bootstrap CIs, demonstrating that retrieval recall gains fail to translate to downstream live generation where hygiene is negative on `cti-ate` (-0.0855, $p=0.0127$) and null on `CTI-ATTACK` (+0.0540, $p=0.3553$) (Supports Claims **C1**, **C2**, **C3**, **C4**).
- **Figure F2 (`F2_cti_taa_clean40.png` / `.svg`)**: Compares threat actor attribution accuracy on `cti-taa` between the full 50-query dataset and the clean 40-query primary benchmark across LLM-only, $V_0$, $V_{0h}$, and $V_{\text{rel}}$ on primary and secondary generators, showing the performance drop once leaked queries are excluded (Supports Claim **C6**).
- **Figure F3 (`F3_leakage.png` / `.svg`)**: Visualizes the benchmark ground-truth alias leakage defect in `cti-taa` (20% of query bodies contain a ground-truth threat group alias) and the resulting 100% accuracy saturation on leaked queries versus 52.5%–70.0% on clean queries (Supports Claim **C7**).
- **Figure F4 (`F4_metadata_credit.png` / `.svg`)**: Illustrates the artificial +0.15 to +0.35 retrieval recall discrepancy at $B=500$ between STIX metadata credit and surface text-visible regex matching across $E_0'$, HD, and $E_{1h}$ on both datasets (Supports Claim **C9**).
- **Figure F5 (`F5_rag_vs_llm_only.png` / `.svg`)**: Displays downstream live generation technique F1 across all evaluation arms ($E_0'$ raw, HD $B=500$, D1 $B=2000$, D2 hybrid, D3 $E_{1h}$, D4 hybrid) relative to the zero-shot LLM-only baseline with 95% bootstrap CIs, demonstrating that context choking at $B=500$ is partially relieved at $B=2000$ (Supports Claims **C5**, **C10**).

## Tables (`results_for_report/tables/`)

- **Table T1 (`T1_datasets.md` / `.tex`)**: Catalogs the benchmark evaluation datasets (`cti-ate`, `CTI-ATTACK`, `cti-taa`) and knowledge base inventories (1,698 active core entities, 26,243 active Enterprise STIX objects, 31,362 total active objects, and 62 upstream S9000-series objects) (Supports Claims **C1**, **C6**, **C7**).
- **Table T2 (`T2_arms.md` / `.tex`)**: Provides formal operational definitions, token budgets, prompt formulations, and retrieval pools for all project arms across retrieval, generation, and attribution (Supports Claims **C1**, **C4**, **C5**, **C6**, **C10**).
- **Table T3 (`T3_main_results.md` / `.tex`)**: Synthesizes the core empirical findings across Claims C1 through C10, detailing metrics, sample sizes, observed deltas, 95% bootstrap CIs, discordant pair tallies, and Holm-adjusted $p$-values (Supports Claims **C1** through **C10**).
- **Table T4 (`T4_statistical_tests.md` / `.tex`)**: Records formal statistical tests across all pre-registered and exploratory families, detailing discordant pairs $(W, L)$, exact binomial sign test $p$-values, Holm step-down thresholds, and significance outcomes (Supports Claims **C4**, **C5**, **C6**).
- **Table T5 (`T5_detector_precision.md` / `.tex`)**: Details the entity detector precision audit on 100 D0-sampled detections, documenting the purification from 74.0% (D0) to 93.9% (D1/V1h body-only) and partitioning the 37 non-informative detections into prompt templates (11), common words/.NET/ping (15), and generic OS utilities (11) (Supports Claim **C8**).
- **Table T6 (`T6_benchmark_defects.md` / `.tex`)**: Documents the five major benchmark defects, data artifacts, and methodological distortions identified during the project, along with their empirical impact and certified mitigation protocols (Supports Claims **C4**, **C7**, **C9**).
