# Offline Retrieval Evaluation: Before vs After Long-Query Strategy

Comparison of **Baseline (256-token truncation)** vs **Long-Query MaxSim Pooling** across all 339 queries.

Zero LLM calls used (offline evaluation).


### 1. Main Retrieval Metrics Comparison

| Dataset | Mode | Queries | Recall@1 | Recall@5 | Recall@10 | MRR | nDCG@10 | Latency (ms) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **cti-ate** | BEFORE (Truncated) | 60 | 0.0154 | 0.0588 | 0.0769 | 0.1335 | 0.0629 | 3265.1 |
| **cti-ate** | AFTER (MaxSim) | 60 | 0.0088 | 0.0644 | 0.1030 | 0.1327 | 0.0819 | 15084.8 |
| **cti-taa** | BEFORE (Truncated) | 50 | 0.0400 | 0.1600 | 0.3600 | 0.1014 | 0.1718 | 6283.6 |
| **cti-taa** | AFTER (MaxSim) | 50 | 0.0200 | 0.1400 | 0.1600 | 0.0717 | 0.1148 | 42114.5 |
| **CTI-ATTACK** | BEFORE (Truncated) | 229 | 0.0328 | 0.1026 | 0.1914 | 0.0778 | 0.1808 | 3123.5 |
| **CTI-ATTACK** | AFTER (MaxSim) | 229 | 0.0328 | 0.1026 | 0.1914 | 0.0778 | 0.1808 | 2050.1 |

### 2. Reachable Ceiling & Sub-technique Credit Breakdown (AFTER: MaxSim)

| Dataset | Mode | Raw Recall@10 | Reachable Recall@10 | Subtech-Credit Recall@10 | Raw MRR | Reachable MRR | Subtech MRR |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **cti-ate** | AFTER (MaxSim) | 0.1030 | 0.1035 | 0.1316 | 0.1327 | 0.1327 | 0.2568 |
| **CTI-ATTACK** | AFTER (MaxSim) | 0.1914 | 0.1914 | 0.2689 | 0.0778 | 0.0778 | 0.1786 |