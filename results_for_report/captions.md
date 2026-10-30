# Figure and Table Captions (Phase 6J, auto-generated)

## Figure Captions

**F1 (Hygiene Effect Across 4 Regimes)**: Query hygiene effect (treatment minus control delta with 95% bootstrap CI) across four evaluation regimes: (1) Balanced retrieval ladder on common budgets {500, 1000} with fixed pool k=50; (2) Enterprise STIX objects (E0-STIX-ENT, cti-ate B3: 0.1221 -> 0.0811; CTI-ATTACK B2: 0.1812 -> 0.6303); (3) Long-context dense embeddings (B1 nomic-embed-text-v1.5); and (4) Downstream live generation technique F1 at B=500. Shows that large retrieval gains on CTI-ATTACK fail to translate to generation gains. Data: `results_for_report/data/F1_hygiene_effect.csv`.

**F2 (cti-taa Clean-40)**: Retrieval Object Recall@10 for V0, V0h, Vrel on full-50 and clean-40 query sets. Data: `results_for_report/data/F2_cti_taa_clean40.csv`.

**F3 (Leakage)**: v2_alias accuracy on full-50 vs clean-40 for LLM-only, V0h, Vrel. Data: `results_for_report/data/F3_leakage.csv`.

**F4 (Metadata Credit)**: Recall@B at B=500 under metadata credit vs text-visible scoring for E0'-HD-k200 on both datasets. Data: `results_for_report/data/F4_metadata_credit.csv`.

**F5 (RAG vs LLM-only)**: Technique F1 (f1_sub) for LLM-only, HD B=500, D1 B=2000 across cti-ate and CTI-ATTACK. Data: `results_for_report/data/F5_rag_vs_llm_only.csv`.

## Table Captions

**T3 (Main Results)**: Primary claim cells with deltas, CIs, W/T/L, p-values, source files. Data: `results_for_report/data/T3_main_results.csv`.

**T4 (Statistical Tests)**: Holm step-down results for primary (M=4) and post-hoc hygiene (M=2) families. Data: `results_for_report/data/T4_statistical_tests.csv`.

**T6 (Benchmark Defects)**: Known measurement artifacts and mitigations. Data: `results_for_report/data/T6_benchmark_defects.csv`.

