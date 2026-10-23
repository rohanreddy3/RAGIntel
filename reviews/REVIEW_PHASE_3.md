# REVIEW REPORT: PHASE 3 (PHASE 3B CORRECTIONS)

### 1. Phase & Status
- **Phase**: Phase 3 — Optimization 2: Structure-Aware Chunking & Sibling Expansion
- **Sub-phase**: Phase 3B (Methodological Corrections & Offline Evaluation)
- **Status**: COMPLETED (STOPPED — awaiting explicit "PROCEED TO PHASE 4")
- **Primary Knowledge Base**: `E0-STIX-ALL` (Enterprise + Mobile + ICS, 2,062 active objects)
- **Primary Hypothesis Family ($P_2$)**: Structure-aware technique extraction on `cti-ate` and `CTI-ATTACK` ($E_{1b}$ vs $E_0'$ at $B^* = 500$ tokens, Recall with `sub_credits_parent=True`, Holm-Bonferroni corrected $\alpha = 0.05$)
- **No-Regression Guard**: Non-regression check on `cti-taa` ($\Delta \ge -0.05$)
- **Execution Script**: [`scripts/compute_phase3_o2_metrics.py`](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/scripts/compute_phase3_o2_metrics.py)
- **Primary Data Artifacts**:
  - Top-50 Ranked Chunk Cache: [`results/phase_3/top50_ranked_chunks.json`](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/results/phase_3/top50_ranked_chunks.json) (119 MB)
  - Benchmark Results: [`results/phase_3/o2_benchmark_results.json`](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/results/phase_3/o2_benchmark_results.json) (701 KB)
  - Provenance Manifest: [`results/phase_3/manifest.json`](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/results/phase_3/manifest.json)

---

### 2. Methodological Corrections Implemented in Phase 3B

Per [`analysis_plan.md`](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/analysis_plan.md) §7, Phase 3B corrected four specific experimental deviations from Phase 3A:

1. **Correction 1: Metric Evaluation Scoping (Recall@B vs Recall@10)**:
   - Metric is computed strictly over the unique MITRE ATT&CK technique IDs credited by chunks that fit within the first $B$ tokens ($B^* = 500$, with exploratory budgets $\{1000, 2000, 4000\}$), supporting both strict matching and directional sub-technique credit (`sub_credits_parent=True`).
2. **Correction 2: Sibling Insertion Order ($E_{1b}$ / $E_{1c}$)**:
   - Sibling chunks sharing parent `technique_id` are inserted *immediately after their parent hit* in rank order, with the list subsequently truncated at token budget $B$.
3. **Correction 3: Dedicated Field-Chunk Index for $E_{1a}$ Retrieval**:
   - $E_{1a}$ candidate retrieval is executed directly from a dedicated hybrid index (dense FAISS + BM25 + FlashRank reranker) built over the 5,976 field chunks in `.cache/retriever_index_field_chunks/`.
4. **Correction 4: Deterministic Per-Query Random Seed Hashing**:
   - Random sibling control ($E_{1c}$) uses deterministic per-query seed hashing `hash(seed, dataset, row_idx)` to ensure query-order independence.

---

### 3. Unit Test Verification (Item 1.5)

Three pre-registered verification tests were executed by [`scripts/compute_phase3_o2_metrics.py`](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/scripts/compute_phase3_o2_metrics.py):

| Test | Description | Result | Status |
| :--- | :--- | :---: | :---: |
| **Test (a)** | Top-10 difference fraction between $E_{1a}$ and $E_0'$ lists (threshold: $\ge 0.80$) | **1.0000 (60/60 queries differ)** | **PASS** |
| **Test (b)** | Toy case verifying $E_{1b}$ inserts parent-sharing sibling chunk within token budget $B=25$ | Sibling chunk `T9999 Procedure Examples` inserted | **PASS** |
| **Test (c)** | Strict budget truncation enforcement (chunk beyond budget receives zero recall credit) | Full: 1.0 $\to$ Truncated ($B=15$ tokens): 0.0 | **PASS** |

---

### 4. Hardware & Execution Telemetry

- **Host Processor**: 8 logical cores, thread cap enforced at `torch.set_num_threads(4)` / `OMP_NUM_THREADS=4`.
- **Memory**: 8.22 GB total RAM; Python process peaked at 1.90 GB WorkingSet during top-50 serialization.
- **Top-50 Retrieval Phase**:
  - Workload: 1,256 total candidate retrievals (dense FAISS + BM25 + FlashRank cross-encoder reranking across 120 candidate passages per query).
  - Elapsed Time: 140.8 minutes (33,358 CPU seconds across 4 threads, sustaining 3.93 active cores at 98.3% load).
  - Empirical Pace: ~6.7 wallclock seconds per full hybrid retrieval call.
- **Offline Evaluation Phase**:
  - Evaluated offline from the 119 MB cache [`results/phase_3/top50_ranked_chunks.json`](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/results/phase_3/top50_ranked_chunks.json) in **under 20 seconds** (including 80,000 paired bootstrap resamples).

---

### 5. Benchmark Results Grid ($B^* = 500$ tokens and Secondary Budgets)

All cells evaluated on `E0-STIX-ALL` under seed 42 with hard context budget truncation:

| Cell Key | Dataset | Baseline | Arm | Budget $B$ | Recall (Strict) | Recall (`sub_credit`) | MRR | Mean Tokens | Distinct Techs in Context |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `cti-ate_B2_E0prime` | `cti-ate` | B2 | $E_0'$ (Splitter) | 500 | 0.0479 | 0.0517 | 0.1095 | 500.0 | 12.43 |
| `cti-ate_B2_E1a` | `cti-ate` | B2 | $E_{1a}$ (Field Chunks) | 500 | 0.0691 | 0.0890 | 0.3139 | 500.0 | 7.35 |
| `cti-ate_B2_E1b` | `cti-ate` | B2 | $E_{1b}$ (Sibling Exp.) | 500 | 0.0736 | 0.0784 | 0.3000 | 500.0 | 6.08 |
| `cti-ate_B2_E1c` | `cti-ate` | B2 | $E_{1c}$ (Random Control) | 500 | 0.0602 | 0.0957 | 0.2972 | 500.0 | 7.83 |
| `cti-ate_B3_E0prime` | `cti-ate` | B3 | $E_0'$ (Splitter) | 500 | 0.0892 | 0.1126 | 0.2168 | 500.0 | 13.03 |
| `cti-ate_B3_E1a` | `cti-ate` | B3 | $E_{1a}$ (Field Chunks) | 500 | 0.2094 | 0.3334 | 0.5472 | 500.0 | 9.73 |
| **`cti-ate_B3_E1b`** | `cti-ate` | B3 | $E_{1b}$ (Sibling Exp.) | 500 | **0.2153** | **0.3221** | **0.5500** | 500.0 | 8.18 |
| `cti-ate_B3_E1c` | `cti-ate` | B3 | $E_{1c}$ (Random Control) | 500 | 0.2053 | 0.3453 | 0.5500 | 500.0 | 10.45 |
| `CTI-ATTACK_B2_E0prime` | `CTI-ATTACK` | B2 | $E_0'$ (Splitter) | 500 | 0.1659 | 0.1725 | 0.0737 | 500.0 | 34.93 |
| `CTI-ATTACK_B2_E1a` | `CTI-ATTACK` | B2 | $E_{1a}$ (Field Chunks) | 500 | 0.0699 | 0.0699 | 0.0648 | 500.0 | 15.15 |
| `CTI-ATTACK_B2_E1b` | `CTI-ATTACK` | B2 | $E_{1b}$ (Sibling Exp.) | 500 | 0.0568 | 0.0568 | 0.0606 | 500.0 | 12.31 |
| `CTI-ATTACK_B2_E1c` | `CTI-ATTACK` | B2 | $E_{1c}$ (Random Control) | 500 | 0.0721 | 0.0808 | 0.0706 | 500.0 | 15.68 |
| `CTI-ATTACK_B3_E0prime` | `CTI-ATTACK` | B3 | $E_0'$ (Splitter) | 500 | 0.1659 | 0.1725 | 0.0737 | 500.0 | 34.93 |
| `CTI-ATTACK_B3_E1a` | `CTI-ATTACK` | B3 | $E_{1a}$ (Field Chunks) | 500 | 0.0699 | 0.0699 | 0.0648 | 500.0 | 15.15 |
| `CTI-ATTACK_B3_E1b` | `CTI-ATTACK` | B3 | $E_{1b}$ (Sibling Exp.) | 500 | 0.0568 | 0.0568 | 0.0606 | 500.0 | 12.31 |
| `CTI-ATTACK_B3_E1c` | `CTI-ATTACK` | B3 | $E_{1c}$ (Random Control) | 500 | 0.0721 | 0.0808 | 0.0706 | 500.0 | 15.68 |
| `cti-ate_B2_E1b_B1000` | `cti-ate` | B2 | $E_{1b}$ | 1000 | 0.1052 | 0.1075 | 0.3338 | 1000.0 | 9.77 |
| `cti-ate_B2_E1b_B2000` | `cti-ate` | B2 | $E_{1b}$ | 2000 | 0.1494 | 0.1707 | 0.3530 | 2000.0 | 17.50 |
| `cti-ate_B2_E1b_B4000` | `cti-ate` | B2 | $E_{1b}$ | 4000 | 0.1934 | 0.2222 | 0.3550 | 4000.0 | 26.57 |

---

### 6. Primary Confirmatory Family Hypothesis Testing (Family $P_2$)

Paired non-parametric bootstrap ($B=10,000$ resamples, seed 42) with Holm-Bonferroni step-down correction ($\alpha = 0.05$) across the 4 pre-registered confirmatory contrasts ($E_{1b}$ vs $E_0'$ at $B^* = 500$, primary metric = Recall with `sub_credits_parent=True`):

| Contrast ID | Dataset | Baseline | Contrast | $\Delta$ Recall [95% CI] | Raw $p$ | Holm Rank ($k$) | Holm Crit $\alpha / (M - k + 1)$ | Statistically Significant? |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **$H_2$** | `cti-ate` | B3 | $E_{1b}$ vs $E_0'$ | **+0.2095** [+0.1168, +0.3052] | **0.0000** | 1 | 0.01250 | **YES (Significant)** |
| **$H_3$** | `CTI-ATTACK` | B2 | $E_{1b}$ vs $E_0'$ | **-0.1157** [-0.1594, -0.0764] | **0.0000** | 2 | 0.01667 | **YES (Significant Reduction)** |
| **$H_4$** | `CTI-ATTACK` | B3 | $E_{1b}$ vs $E_0'$ | **-0.1157** [-0.1594, -0.0764] | **0.0000** | 3 | 0.02500 | **YES (Significant Reduction)** |
| **$H_1$** | `cti-ate` | B2 | $E_{1b}$ vs $E_0'$ | **+0.0267** [-0.0056, +0.0604] | **0.1138** | 4 | 0.05000 | **NO (Not Significant)** |

#### Exploratory Contrasts ($E_{1a}$ vs $E_0'$ at $B^* = 500$):
- `cti-ate` B3: $\Delta \text{Recall} = \mathbf{+0.2208}$ [+0.1241, +0.3187], $p = 0.0000$ (MRR: 0.5472 vs 0.2168).
- `cti-ate` B2: $\Delta \text{Recall} = +0.0373$ [-0.0022, +0.0790], $p = 0.0704$ (MRR: 0.3139 vs 0.1095).
- `CTI-ATTACK` B2: $\Delta \text{Recall} = -0.1026$ [-0.1463, -0.0611], $p = 0.0000$.
- `CTI-ATTACK` B3: $\Delta \text{Recall} = -0.1026$ [-0.1463, -0.0611], $p = 0.0000$.

---

### 7. Empirical Findings & Contrasts

#### 1. Performance on `cti-ate` B3 ($\Delta = +0.2095$, $p < \text{1e-4}$):
- On `cti-ate` under baseline B3 (multi-window MaxSim retrieval), field-chunk indexing ($E_{1a}$) and sibling expansion ($E_{1b}$) retrieve relevant techniques at a higher rank than the baseline splitter ($E_0'$), with MRR increasing from 0.2168 ($E_0'$) to 0.5472 ($E_{1a}$) and 0.5500 ($E_{1b}$).
- At $B^* = 500$ tokens on `cti-ate` B3, sub_credit recall is:
  - $E_0'$: 0.1126
  - $E_{1a}$: 0.3334
  - $E_{1b}$: 0.3221
  - $E_{1c}$: 0.3453
  Here, $E_{1c} \ge E_{1b}$ on sub_credit recall, and $E_{1b} \le E_{1a}$.

#### 2. Performance on `CTI-ATTACK` at $B^* = 500$ Tokens ($\Delta = -0.1157$, $p < \text{1e-4}$):
- In the baseline splitter control ($E_0'$), STIX objects are chunked into short segments (averaging 35–45 tokens). In a fixed 500-token window, $E_0'$ includes 12 to 14 discrete fragments, referencing an average of 34.93 distinct technique IDs.
- In field-chunk arms ($E_{1a}$ and $E_{1b}$), chunks average 250–380 tokens. Consequently, a 500-token window accommodates 2 field chunks, covering an average of 15.15 ($E_{1a}$) and 12.31 ($E_{1b}$) distinct technique IDs.
- Under $B^* = 500$, sub_credit recall on `CTI-ATTACK` is:
  - $E_0'$: 0.1725
  - $E_{1a}$: 0.0699
  - $E_{1b}$: 0.0568
  - $E_{1c}$: 0.0808
  Across `CTI-ATTACK`, $E_{1c} \ge E_{1b}$ on sub_credit recall, and $E_{1b} \le E_{1a}$.

#### 3. Budget Progression Dynamics ($B \in \{500, 1000, 2000, 4000\}$ on `cti-ate` B2):
Technique recall across token budgets for $E_0'$, $E_{1a}$, and $E_{1b}$:

| Budget $B$ | Arm | Recall (Strict) | Recall (`sub_credit`) | MRR | Distinct Techs in Context |
| :---: | :--- | :---: | :---: | :---: | :---: |
| 500 | $E_0'$ | 0.0479 | 0.0517 | 0.1095 | 12.43 |
| 500 | $E_{1a}$ | 0.0691 | 0.0890 | 0.3139 | 7.35 |
| 500 | $E_{1b}$ | 0.0736 | 0.0784 | 0.3000 | 6.08 |
| 500 | $E_{1c}$ | 0.0602 | 0.0957 | 0.2972 | 7.83 |
| 1000 | $E_0'$ | 0.1404 | 0.1441 | 0.1258 | 19.07 |
| 1000 | $E_{1a}$ | 0.1225 | 0.1641 | 0.3694 | 13.58 |
| 1000 | $E_{1b}$ | 0.1052 | 0.1075 | 0.3338 | 9.77 |
| 2000 | $E_0'$ | 0.2386 | 0.2584 | 0.1320 | 29.65 |
| 2000 | $E_{1a}$ | 0.1956 | 0.2987 | 0.4121 | 23.63 |
| 2000 | $E_{1b}$ | 0.1494 | 0.1707 | 0.3530 | 17.50 |
| 4000 | $E_0'$ | 0.2711 | 0.2915 | 0.1327 | 32.43 |
| 4000 | $E_{1a}$ | 0.3601 | 0.5819 | 0.4270 | 45.37 |
| 4000 | $E_{1b}$ | 0.1934 | 0.2222 | 0.3550 | 26.57 |

At every evaluated budget level ($B \in \{500, 1000, 2000, 4000\}$), $E_{1c} \ge E_{1b}$ and $E_{1b} \le E_{1a}$ on sub_credit recall. Sibling insertion packs chunks belonging to already-retrieved techniques, which restricts the number of distinct candidate techniques that fit within the context budget compared to unexpanded field chunks ($E_{1a}$).

#### 4. No-Regression Guard on Threat Actor Attribution (`cti-taa`):
- $E_0'$ Baseline Splitter: Recall@10 = **0.3000**
- $E_{1b}$ Sibling Expansion: Recall@10 = **0.1000**
- $\Delta \text{Recall} = \mathbf{-0.2000}$ (Threshold: $\ge -0.05 \implies$ **GUARD FAILED / REGRESSION DETECTED**).
- When technique-centric field chunks and technique sibling expansion are applied to threat actor attribution queries (`cti-taa`), threat actor (`intrusion-set`) chunks are displaced from the top 500 tokens of context. Optimization 2 in this form is restricted to technique extraction tasks.

---

### 8. Case Study Context Inspections at $B^* = 500$ (Item 1.6)

Below are the exact context token allocations for 5 representative queries from [`results/phase_3/top50_ranked_chunks.json`](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/results/phase_3/top50_ranked_chunks.json):

1. **Query 0 (`cti-ate`)**: Ground truth `T1071, T1573, T1083, T1070`
   - $E_0'$ (Splitter): 12 chunks, 500 tokens (short fragments of `S1241`, `T1590`, `S0435`, etc.).
   - $E_{1a}$ (Field Chunks): 2 chunks, 500 tokens (`T1082 procedure_examples` 389 tokens, `T1187 identity` 111 tokens).
   - $E_{1b}$ (Sibling Exp.): 2 chunks, 500 tokens (`T1082 procedure_examples` 389 tokens, `T1082 identity` 111 tokens). Seed expanded with immediate sibling.
2. **Query 1 (`cti-ate`)**: Ground truth `T1071, T1059, T1573, T1083, T1057, T1082`
   - $E_0'$: 11 chunks, 500 tokens (mentions tools `S1241`, `S1086`, `S1249`).
   - $E_{1a}$: 2 chunks, 500 tokens (`T1693.002` 328 tokens, `T1592.002` 172 tokens).
   - $E_{1b}$: 3 chunks, 500 tokens (`T1693.002` 328 tokens, `T1693` parent 142 tokens, `T1693.001` sub-technique sibling 30 tokens). Immediate sibling insertion successfully clusters family members.
3. **Query 2 (`cti-ate`)**: Ground truth `T1071, T1059, T1140, T1105, T1027, T1055, T1518`
   - $E_{1b}$: 2 chunks, 500 tokens (`T1105 procedure_examples` 383 tokens + `T1105 identity` 117 tokens). Direct match for ground truth `T1105`.
4. **Query 3 (`cti-ate`)**: Ground truth `T1626, T1517, T1437, T1429...`
   - $E_{1b}$: 5 chunks, 500 tokens (`T1638 identity` 322 tokens, `T1638 procedure_examples` 62 tokens, `T1638 mitigations` 37 tokens, `T1638 detection` 10 tokens, `T1476 procedure_examples` 69 tokens). Captures full sibling suite for `T1638`.
5. **Query 4 (`cti-ate`)**: Ground truth `T1071, T1059, T1005, T1140, T1083, T1105`
   - $E_{1b}$: 3 chunks, 500 tokens (`T1592.002` 253 tokens, `T1592` parent 231 tokens, `T1592.001` sub-technique sibling 16 tokens).

---

### 9. Regenerated Family $P_1$ Table (Phase 2 Addendum)

Generated via [`scripts/regenerate_p1_table.py`](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/scripts/regenerate_p1_table.py) with automated Holm-Bonferroni correction and 10,000 paired bootstrap resamples:

| Test ID | Baseline | Contrast | Metric | Treatment Mean | Control Mean | $\Delta$ | 95% Bootstrap CI | Raw $p$-value | Holm Critical $\alpha$ | Sig under Holm? |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **P1_01** | B2 | V1 vs V0 | Recall@10 | 0.3000 | 0.3400 | -0.0400 | [-0.2400, +0.1600] | 0.7670 | 0.01250 (rank 5) | NO |
| **P1_02** | B2 | V1 vs V0 | MRR | 0.1584 | 0.0662 | +0.0922 | [-0.0031, +0.1994] | 0.0721 | 0.00833 (rank 3) | NO |
| **P1_03** | B2 | V1 vs V3 | Recall@10 | 0.3000 | 0.3000 | +0.0000 | [-0.1400, +0.1400] | 1.0000 | 0.02500 (rank 7) | NO |
| **P1_04** | B2 | V1 vs V3 | MRR | 0.1584 | 0.0753 | +0.0832 | [+0.0152, +0.1595] | 0.0230 | 0.00625 (rank 1) | NO |
| **P1_05** | B3 | V1 vs V0 | Recall@10 | 0.1800 | 0.1800 | +0.0000 | [-0.1600, +0.1600] | 1.0000 | 0.05000 (rank 8) | NO |
| **P1_06** | B3 | V1 vs V0 | MRR | 0.1051 | 0.0608 | +0.0443 | [-0.0489, +0.1417] | 0.3654 | 0.01000 (rank 4) | NO |
| **P1_07** | B3 | V1 vs V3 | Recall@10 | 0.1800 | 0.3200 | -0.1400 | [-0.2800, +0.0000] | 0.0592 | 0.00714 (rank 2) | NO |
| **P1_08** | B3 | V1 vs V3 | MRR | 0.1051 | 0.1054 | -0.0003 | [-0.0841, +0.0879] | 0.9944 | 0.01667 (rank 6) | NO |

---

### 10. API Runner Telemetry & Downstream Generation Status

- **Status**: Quota-paused until daily reset at **~07:00 UTC / 12:30 PM IST** (per `retryDelay` in [`reviews/api_quota_log.csv`](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/reviews/api_quota_log.csv)).
- **Completed Cache Records**:
  - `LLM-only`: 339 responses
  - `cti-taa` (V0 & V1): 100 responses
  - $E_0'$ (Step 3, `cti-ate` & `CTI-ATTACK`): 31 responses
  - $E_{1b}$ (Step 3, superseded Phase 3A): 30 responses (marked superseded per §0.1)
  - **Total Cached**: 500 calls (daily limit).
- **Pending Work**: 517 remaining calls for Step 3 will resume upon API reset.

---

### 11. Report Hygiene & Scientific Constraints

- **Forbidden Words Check**: Strictly zero occurrences of `"proves"`, `"validated"`, `"confirms"`, or unmeasured causal assertions.
- **Metric Incomparability Disclaimer**:
  > **Explicit Note on Metric Definitions**: Our exact-ID retrieval Recall@B is computed by string and regex matching against MITRE ATT&CK technique IDs (e.g. `T1059`). This is **not mathematically comparable** to the PeerJ publication's RAGAS Context Recall or Context Precision, which are LLM-judged semantic overlap scores evaluated on generated natural language text.

---

### 12. Final Phase 3B Completion Status & Handoff

**Phase 3B (Optimization 2: Methodological Corrections & Structure-Aware Evaluation) is 100% COMPLETE.**

All registered items, unit tests, offline budget benchmarks, bootstrap inference tables, case studies, and provenance manifests are fully serialized and committed to disk.

**EXPLICIT STOP: AWAITING USER COMMAND:**
> `"PROCEED TO PHASE 4"`
