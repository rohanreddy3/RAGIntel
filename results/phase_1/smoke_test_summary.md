# Phase 1 Generation & RAGAS Smoke Test Report

- **Generator Model**: `gemini-3.5-flash-lite` (temperature=0.1)
- **RAGAS Judge Model**: `gemini-3.5-flash-lite`
- **Embedding Model**: `sentence-transformers/all-MiniLM-L6-v2` (local CPU, 100% offline)
- **Retriever / Compressor**: FAISS + BM25 + FlashRank (`ms-marco-MiniLM-L-12-v2`, top-k=5)
- **Rows Tested**: 5 rows from `CTI-ATE` (rows 0–4)

---

## 1. Measured Smoke Test Execution

| Metric | Measured Value | Notes |
| :--- | :--- | :--- |
| **Generation Wall Time** | 28.5 s | 5 calls at 14 RPM (~4.3s pacing) |
| **RAGAS Evaluation Wall Time** | 189.2 s | 5 metrics across 5 rows = 25 evaluations |
| **Total Smoke Wall Time** | 217.7 s (~3.63 min) | Generation + Judging |
| **API Calls Made** | 30 calls | 5 generation + 25 RAGAS judge |
| **API Calls Per Row** | 6.0 calls/row | 1 generator + 5 metric judges |
| **Rate Limiter Pacing** | 4.3 s / call | Enforcing 14 RPM (under 15 RPM limit) |
| **On-Disk Checkpoints** | 5 files | Saved to `results/phase_1/smoke_checkpoints/` |

---

## 2. RAGAS Scores (5-Row Sample)

| Metric | Score | Interpretation |
| :--- | :--- | :--- |
| **Context Recall** | `0.0000` | Retrieved STIX chunks did not contain full GT techniques |
| **Context Precision** | `0.0000` | STIX baseline rank precision low on raw CTI text |
| **Faithfulness** | `0.0000` | Extracted IDs not grounded in un-optimized retrieved context |
| **Factual Correctness** | `0.4533` | Model extracted partial ground truth techniques |
| **Answer Relevancy** | `0.4105` | Model extracted MITRE technique IDs aligned with prompt |

---

## 3. Extrapolation to Full Benchmark (339 Rows)

Total rows across all 3 benchmark datasets:
- `CTI-ATE`: 60 rows
- `CTI-TAA`: 50 rows
- `CTI-ATTACK`: 229 rows
- **Total Rows**: **339 rows**

### Resource & Quota Calculations:
1. **Total Extrapolated API Calls**:
   $$339 \text{ rows} \times 6.0 \text{ calls/row} = 2,034 \text{ calls}$$
   - Generation calls: 339
   - RAGAS judge calls: 1,695
2. **Active Compute Time (at 14 RPM)**:
   $$\frac{2,034 \text{ calls}}{14 \text{ RPM}} = 145.3 \text{ minutes} = \mathbf{2.42 \text{ hours}}$$
3. **Calendar Days Under Free-Tier Quota (1,500 Requests/Day)**:
   $$\frac{2,034 \text{ calls}}{1,500 \text{ calls/day}} = \mathbf{1.36 \text{ days}} \quad (\approx 32.6 \text{ hours})$$
4. **Constraint Verification**:
   - Threshold limit: **3 days**
   - Projected calendar duration: **1.36 days**
   - **Exceeds 3 days?**: **NO (Safe to proceed with checkpointing and 14 RPM limiter)**
