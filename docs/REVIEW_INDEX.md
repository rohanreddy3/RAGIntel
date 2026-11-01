# Review Index: Chronological Phase Reviews & Audits

This document provides a concise, one-line navigational guide to all review, audit, and verification documents located in `reviews/`.

| File | Description |
| :--- | :--- |
| [`reviews/REVIEW_PHASE_0.md`](../reviews/REVIEW_PHASE_0.md) | STIX 2.1 JSON bundle parsing, entity schema extraction, and reachable ceiling verification (100% ceiling across benchmarks). |
| [`reviews/REVIEW_PHASE_1.md`](../reviews/REVIEW_PHASE_1.md) | Initial retrieval baselines (B1 dense Nomic, B2 truncated MiniLM, B3 MaxSim windowed MiniLM) across 339 queries. |
| [`reviews/REVIEW_PHASE_2.md`](../reviews/REVIEW_PHASE_2.md) | Optimization 1 (O1) query-side threat entity resolution benchmark (variants V0–V3, alias matching, and seed sensitivity). |
| [`reviews/REVIEW_PHASE_3.md`](../reviews/REVIEW_PHASE_3.md) | Optimization 2 (O2) structure-aware field chunking benchmark ($E_{1a}$, $E_0'\text{-TECH}$, $E_1\text{-MIXED}$) across token budgets. |
| [`reviews/REVIEW_PHASE_3C.md`](../reviews/REVIEW_PHASE_3C.md) | Strict negative controls and fair comparisons for structure-aware field chunking against baseline recursive splitters. |
| [`reviews/REVIEW_PHASE_4.md`](../reviews/REVIEW_PHASE_4.md) | Offline integrity audit, query-row alignments, sha1 query hashing, and initial Markdown/LaTeX publication tables. |
| [`reviews/REVIEW_PHASE_4B.md`](../reviews/REVIEW_PHASE_4B.md) | Verification round: budget saturation audit, STIX versioning, and initial detector precision measurements. |
| [`reviews/REVIEW_PHASE_5.md`](../reviews/REVIEW_PHASE_5.md) | Pre-declared query hygiene audit (339 query body markers), clean comparisons under HD, and exact binomial sign tests. |
| [`reviews/REVIEW_PHASE_5B.md`](../reviews/REVIEW_PHASE_5B.md) | Offline reconciliations, entity detector share reconciliation (3.49%), and candidate pool scaling ($k=200$). |
| [`reviews/REVIEW_PHASE_6C.md`](../reviews/REVIEW_PHASE_6C.md) | Primary live LLM generation benchmark (Gemini 3.5 Flash-Lite, 389 calls) and technique F1 evaluation. |
| [`reviews/REVIEW_PHASE_6D.md`](../reviews/REVIEW_PHASE_6D.md) | Extended round: secondary generator replication (Gemini 3.1 Flash-Lite), secondary KB ($E_0\text{-STIX-ENT}$), and B1 dense robustness. |
| [`reviews/REVIEW_PHASE_6F.md`](../reviews/REVIEW_PHASE_6F.md) | Rigorous audit of benchmark defects: ground-truth alias leakage in `cti-taa` (20%) and metadata-credit inflation. |
| [`reviews/REVIEW_PHASE_6G.md`](../reviews/REVIEW_PHASE_6G.md) | Programmatic corrections ledger and unified metrics harmonization across retrieval and generation arms. |
| [`reviews/REVIEW_PHASE_6H.md`](../reviews/REVIEW_PHASE_6H.md) | Pre-freeze asset alignment and publication table verification. |
| [`reviews/REVIEW_PHASE_6I.md`](../reviews/REVIEW_PHASE_6I.md) | Source-of-truth rebuild: deprecation of hand-typed tables and establishment of programmatic loading script. |
| [`reviews/REVIEW_PHASE_6J.md`](../reviews/REVIEW_PHASE_6J.md) | Restoration of balanced ladder retrieval point estimates (C1) and formal relabeling of status categories. |
| [`reviews/REVIEW_PHASE_6K.md`](../reviews/REVIEW_PHASE_6K.md) | Reconciliation of Claim C2 secondary KB means and verification assertions. |
| [`reviews/FINAL_AUDIT.md`](../reviews/FINAL_AUDIT.md) | Comprehensive adversarial audit of the codebase: 3 Critical, 7 Major, and 8 Minor findings identified. |
| [`reviews/REVIEW_PHASE_6L.md`](../reviews/REVIEW_PHASE_6L.md) | Phase 6L final consistency fixes: LaTeX table generation, bidirectional sensitivity audit, and certified freeze `v1.0-final4`. |
| [`reviews/RESULTS_MASTER.md`](../reviews/RESULTS_MASTER.md) | Canonical results ledger: single programmatic source of truth for all claims, Holm families, and generation tables. |
| [`reviews/REVIEW_PHASE_7P.md`](../reviews/REVIEW_PHASE_7P.md) | Phase 7P repository packaging, clean documentation overhaul, reproduction guide, and release freeze `v1.0-final5`. |
