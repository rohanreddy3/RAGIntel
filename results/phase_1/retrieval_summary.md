# Phase 1 Retrieval Evaluation Summary (E0-STIX / Control Arm E0')

Retrieval metrics computed across all 339 benchmark queries without LLM dependency.

| Dataset | Queries | Recall@1 | Recall@3 | Recall@5 | Recall@10 | Precision@1 | Precision@5 | Precision@10 | MRR | nDCG@10 | Mean Latency (ms) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **cti-ate** | 60 | 0.0154 | 0.0282 | 0.0588 | 0.0769 | 0.0667 | 0.0600 | 0.0417 | 0.1335 | 0.0629 | 3466.1 |
| **cti-taa** | 50 | 0.0400 | 0.1000 | 0.1600 | 0.3600 | 0.0400 | 0.0320 | 0.0400 | 0.1014 | 0.1718 | 7048.6 |
| **CTI-ATTACK** | 229 | 0.0328 | 0.0764 | 0.1026 | 0.1914 | 0.0349 | 0.0463 | 0.0450 | 0.0778 | 0.1808 | 1870.5 |