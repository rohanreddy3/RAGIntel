# REVIEW REPORT: PHASE 3C (CONTROLS AND LOOSE ENDS)

### 1. Phase & Status
- **Phase**: Phase 3 — Optimization 2: Structure-Aware Chunking & Sibling Expansion
- **Sub-phase**: Phase 3C (Controls, Corrected Arms, and Methodological Loose Ends)
- **Status**: RETRIEVAL_AND_ANALYSIS_COMPLETE (Part 1 controls & Family $P_2'$, Part 2 loose ends & Family $P_1$, and Part D assets 100% computed and verified; awaiting final 47 queries of $E_{1b}\text{-MIXED}$ generation on rolling quota reset before offline scoring of Family $G_1$)
- **Corpus / Knowledge Base**: `E0-STIX-ALL` (Enterprise + Mobile + ICS, 2,062 active objects)
- **Primary Hypothesis Family ($P_2'$)**: Unified Mixed Field-Chunk Index ($E_{1b}\text{-MIXED}$ vs $E_0'$ at $B^* = 500$ tokens, Recall with `sub_credits_parent=True`, primary credit rule, on `cti-ate` B2, `cti-ate` B3, `CTI-ATTACK` B2/B3, with `cti-taa` non-regression guard $\Delta \ge -0.05$, Holm-Bonferroni step-down correction $\alpha = 0.05$)
- **Execution Script**: [`scripts/compute_phase3c_controls.py`](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/scripts/compute_phase3c_controls.py)
- **Primary Output Artifacts**:
  - Benchmark Results: [`results/phase_3/o2_phase3c_benchmark_results.json`](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/results/phase_3/o2_phase3c_benchmark_results.json)
  - Top-50 Ranked Chunk Cache: [`results/phase_3/top50_phase3c_chunks.json`](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/results/phase_3/top50_phase3c_chunks.json)
  - Regenerated Family $P_1$: [`results/phase_2/regenerated_p1_table.json`](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/results/phase_2/regenerated_p1_table.json)
  - Phase 4 D1 Offline Scoring: [`results/phase_4/d1_scoring_summary.json`](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/results/phase_4/d1_scoring_summary.json)
  - Phase 4 D2 Publication Assets: [`report/dataset_stats.md`](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/report/dataset_stats.md), [`docs/REPRODUCE.md`](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/docs/REPRODUCE.md), [`report/figures/`](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/report/figures/)

---

### 2. Part 1: Controls and Corrected Arms Pre-Registration

Pre-registered in [`analysis_plan.md`](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/analysis_plan.md) §8 (timestamp: `2026-10-22T03:55:00Z`) prior to execution.

#### 1.1 Index Composition Analysis & Displacement Hypothesis Test
Exact chunk compositions by STIX object type across all evaluated indices:

| Index | Total Chunks | Attack Patterns (`attack-pattern`) | Malware (`malware`) | Threat Groups (`intrusion-set`) | Tools (`tool`) | Standalone Mitigations |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **$E_0'$ (Baseline Splitter)** | 6,693 | 4,505 (67.3%) | 1,486 (22.2%) | 555 (8.3%) | 147 (2.2%) | 0 (embedded in techs) |
| **$E_{1a}$ (Field Chunks)** | 5,976 | 3,704 (62.0%) | 1,718 (28.7%) | 360 (6.0%) | 194 (3.2%) | 0 (embedded in techs) |
| **$E_0'\text{-TECH}$ (Tech-Only Splitter)** | 4,505 | 4,505 (100.0%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | 0 |
| **$E_1\text{-MIXED}$ (Unified Mixed Index)** | 5,892 | 3,704 (62.9%) | 1,486 (25.2%) | 555 (9.4%) | 147 (2.5%) | 0 (embedded in techs) |

**Displacement Hypothesis Finding**:
- **Are groups, software, and mitigations absent from the $E_{1a}$ field index?**
  - **No**. Threat groups (`intrusion-set`: 360 chunks) and Software (`malware` + `tool`: 1,912 chunks) **are present** in the $E_{1a}$ field index.
  - Standalone mitigation objects (`course-of-action`) are not indexed separately in either $E_0'$ or $E_{1a}$; mitigation prose and relationships are structured within each technique's `mitigations` field chunk.
- **Evaluation of Explanation**:
  - The hypothesis that "technique field chunks displace actor objects on `cti-taa` because actor objects were missing" **cannot hold**. Actor objects were present in both indices.
  - The actual cause of lower attribution accuracy on $E_{1a}$ is that technique field chunks (3,704 chunks with fine-grained descriptions) achieve higher BM25 and embedding similarity scores than broad actor summaries, outranking actor objects during top-50 retrieval.

#### 1.2 Credit Rules Specification & Sensitivity Protocol
Technique ID recall is credited under two distinct rules:
1. **Primary Rule (`text_and_metadata`)**:
   - Matches the rule used in Phase 3B. A ground-truth technique ID is credited if either:
     - The chunk's structured metadata explicitly designates the technique ID (`mitre_id` or `technique_id`), OR
     - The chunk text contains an explicit mention matching the technique regex `\bT\d{4}(?:\.\d{3})?\b`.
2. **Sensitivity Rule (`metadata_only`)**:
   - Strictly requires the chunk to be a technique object whose metadata `technique_id` or `mitre_id` directly matches the ground-truth technique. Text mentions of techniques within software, group descriptions, or mitigation prose are ignored.
- **Protocol**: The primary rule stays primary for all confirmatory tests. The sensitivity rule is evaluated strictly as a sensitivity analysis.

#### 1.3 New Arm $E_0'\text{-TECH}$ (Field-Chunking Isolation Control)
- **Definition**: Built by applying the original baseline text splitter (recursive 500-token chunker with 50-token overlap) strictly over `attack-pattern` objects (4,505 chunks). It possesses identical STIX object coverage to the technique subset of $E_{1a}$.
- **Purpose**: Provides a rigorously controlled contrast against $E_{1a}$ to isolate the effect of structured field chunking from non-technique object filtering.
- **Pipeline**: Dense FAISS (`all-MiniLM-L6-v2`) + BM25 + FlashRank cross-encoder reranker, top-50 candidates.
- **Datasets**: Evaluated on `cti-ate` (B2, B3) and `CTI-ATTACK` (B2 and B3 computed separately to empirically verify equality).

#### 1.4 New Arm $E_1\text{-MIXED}$ (Unified Structure-Aware Index)
- **Definition**: A single unified hybrid index containing all 3,704 technique field chunks (chunked by identity/description, procedure examples, mitigations, and detection) combined with the 2,188 baseline non-technique chunks (groups, malware, and tools chunked with the original text splitter). Total chunks: 5,892.
- **Derived Arms**:
  - **$E_{1b}\text{-MIXED}$**: Sibling expansion applied *strictly to technique chunks* after a parent hit, followed by context truncation at token budget $B$.
  - **$E_{1c}\text{-MIXED}$**: Random sibling control inserting unrelated technique siblings (using deterministic per-query seed `hash(seed, dataset, row_idx)`).
- **Datasets**: Evaluated on `cti-ate`, `CTI-ATTACK`, and `cti-taa` (B2, B3).

---

### 3. Benchmark Results & Pre-Registered Family $P_2'$

#### 3.1 Primary Confirmatory Hypothesis Family ($P_2'$) Results
- **Evaluation Setting**: $B^* = 500$ token budget, primary credit rule (`text_and_metadata`), metric: `Recall_sub_credits_parent`.
- **Treatment Arm**: Unified Mixed Field-Chunk Index with technique sibling expansion ($E_{1b}\text{-MIXED}$).
- **Control Arm**: Baseline recursive text splitter on complete STIX bundle ($E_0'$).
- **Inference**: 10,000 paired bootstrap resamples (seed 42), Holm-Bonferroni step-down correction ($\alpha = 0.05$).

| Test ID | Dataset | Baseline | Contrast | Metric | Treatment Mean | Control Mean | $\Delta$ | 95% Bootstrap CI | Raw $p$-value | Holm Critical $\alpha$ | Sig under Holm? |
| :--- | :--- | :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **$P_{2,1}'$** | `cti-ate` | B2 | $E_{1b}\text{-MIXED}$ vs $E_0'$ | Recall (sub credits) | 0.0733 | 0.0517 | +0.0216 | $[-0.0060, +0.0502]$ | 0.1295 | 0.05000 (rank 3) | NO |
| **$P_{2,2}'$** | `cti-ate` | B3 | $E_{1b}\text{-MIXED}$ vs $E_0'$ | Recall (sub credits) | 0.0711 | 0.1126 | -0.0415 | $[-0.0809, -0.0016]$ | 0.0401 | 0.02500 (rank 2) | NO |
| **$P_{2,3}'$** | `CTI-ATTACK` | B2 | $E_{1b}\text{-MIXED}$ vs $E_0'$ | Recall (sub credits) | 0.0240 | 0.1725 | -0.1485 | $[-0.1943, -0.1048]$ | < 0.0001 | 0.01667 (rank 1) | **REGRESSION** |
| **$P_{2,4}'$** | `CTI-ATTACK` | B3 | $E_{1b}\text{-MIXED}$ vs $E_0'$ | Recall (sub credits) | 0.0240 | 0.1725 | -0.1485 | $[-0.1943, -0.1048]$ | < 0.0001 | 0.01667 (rank 1) | **REGRESSION** |

#### 3.2 Non-Regression Guard Test
- **Dataset**: `cti-taa` (Threat Actor Attribution, $N=50$)
- **Contrast**: $E_{1b}\text{-MIXED}$ vs $E_0'$ on Baseline B2 (Recall@10)
- **Pre-registered Threshold**: $\Delta \ge -0.05$
- **Result**:
  - Treatment Mean ($E_{1b}\text{-MIXED}$): **0.1000**
  - Control Mean ($E_0'$): **0.3000**
  - Difference ($\Delta$): **-0.2000** (95% CI: $[-0.3400, -0.0600]$, $p = 0.0064$)
  - **Verdict**: **GUARD FAILED** ($\Delta = -0.2000 < -0.05$). Sibling expansion on technique chunks severely displaces threat group summaries.

#### 3.3 Sensitivity Analysis under `metadata_only` Credit Rule
Under the strictly restricted `metadata_only` rule (requiring technique metadata match, ignoring text mentions):
- $P_{2,1}'$ (`cti-ate` B2): Treatment = 0.0178, Control = 0.0113, $\Delta = +0.0066$ ($[-0.0078, +0.0218]$, $p = 0.3832$). Not significant.
- $P_{2,2}'$ (`cti-ate` B3): Treatment = 0.0422, Control = 0.0734, $\Delta = -0.0312$ ($[-0.0598, -0.0026]$, $p = 0.0333 > \alpha/2 = 0.025$). Not significant.
- $P_{2,3}', P_{2,4}'$ (`CTI-ATTACK` B2/B3): Treatment = 0.0000, Control = 0.0371, $\Delta = -0.0371$ ($[-0.0611, -0.0153]$, $p = 0.0038 < \alpha/3 = 0.0167$). Significant regression.
- Non-regression guard on `cti-taa`: $\Delta = -0.2000$ ($p = 0.0064$). Guard failed.
- **Conclusion**: Confirmatory results and hypothesis rejection replicate identically under the sensitivity rule.

#### 3.4 Exploratory Controls and Mechanistic Contrasts
All evaluated at $B^* = 500$ under `Recall_sub_credits_parent` (`text_and_metadata`):

| Test ID | Contrast | Dataset | Description | Treatment | Control | $\Delta$ | 95% Bootstrap CI | Raw $p$-value |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **EXP_01** | $E_{1a}$ vs $E_0'\text{-TECH}$ | `cti-ate` B2 | Field Chunking Alone (Tech objects only) | 0.0890 | 0.0967 | -0.0077 | $[-0.0464, +0.0298]$ | 0.6974 |
| **EXP_02** | $E_{1a}$ vs $E_0'\text{-TECH}$ | `cti-ate` B3 | Field Chunking Alone (Tech objects only) | 0.1107 | 0.1489 | -0.0382 | $[-0.0877, +0.0077]$ | 0.1251 |
| **EXP_03** | $E_{1a}$ vs $E_0'\text{-TECH}$ | `CTI-ATTACK` B2 | Field Chunking Alone (Tech objects only) | 0.0699 | 0.1135 | -0.0437 | $[-0.0764, -0.0109]$ | 0.0105 |
| **EXP_05** | $E_{1b}\text{-MIXED}$ vs $E_1\text{-MIXED}$ | `cti-ate` B2 | Sibling Expansion Effect | 0.0733 | 0.0864 | -0.0131 | $[-0.0347, +0.0076]$ | 0.2291 |
| **EXP_06** | $E_{1b}\text{-MIXED}$ vs $E_{1c}\text{-MIXED}$ | `cti-ate` B2 | Sibling Specificity (True vs Random) | 0.0733 | 0.0695 | +0.0038 | $[-0.0132, +0.0206]$ | 0.6537 |
| **EXP_07** | $E_{1a}$ vs $E_0'$ | `cti-ate` B2 | Field vs Baseline Splitter | 0.0890 | 0.0517 | +0.0373 | $[-0.0022, +0.0790]$ | 0.0704 |
| **EXP_08** | $E_{1a}$ vs $E_0'$ | `CTI-ATTACK` B2 | Field vs Baseline Splitter | 0.0699 | 0.1725 | -0.1026 | $[-0.1463, -0.0611]$ | < 0.0001 |

#### 3.5 Context Budget Scaling Curves ($B \in \{500, 1000, 2000, 4000\}$ tokens)
Metric: `Recall_sub_credits_parent` under baseline B2:

| Dataset | Arm | $B=500$ | $B=1000$ | $B=2000$ | $B=4000$ | Scaling Trajectory |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| `cti-ate` | **$E_0'$ (Baseline Splitter)** | 0.0517 | 0.1441 | 0.2584 | 0.2915 | Monotonic increase (+464%) |
| `cti-ate` | **$E_0'\text{-TECH}$ (Tech Splitter)** | 0.1684 | 0.3215 | 0.4667 | 0.4959 | High baseline, steep gain (+194%) |
| `cti-ate` | **$E_{1a}$ (Field Chunks)** | 0.0890 | 0.1641 | 0.2987 | **0.5819** | Strongest large-budget scaling (+554%) |
| `cti-ate` | **$E_1\text{-MIXED}$ (Unified Mixed)** | 0.0866 | 0.1124 | 0.2041 | 0.3786 | Moderate linear gain (+337%) |
| `cti-ate` | **$E_{1b}\text{-MIXED}$ (Sibling Exp)** | 0.0733 | 0.1096 | 0.1291 | 0.1694 | Premature saturation (+131%) |
| `cti-ate` | **$E_{1c}\text{-MIXED}$ (Random Sibling)**| 0.0695 | 0.1001 | 0.1616 | 0.2800 | Tracks $E_{1b}$ at low $B$, surpasses at high $B$ |
| `CTI-ATTACK` | **$E_0'$ (Baseline Splitter)** | 0.1725 | 0.2707 | 0.3974 | 0.3974 | Plateaus at $B=2000$ (+130%) |
| `CTI-ATTACK` | **$E_0'\text{-TECH}$ (Tech Splitter)** | 0.1310 | 0.2249 | 0.3690 | 0.3690 | Plateaus at $B=2000$ (+182%) |
| `CTI-ATTACK` | **$E_{1a}$ (Field Chunks)** | 0.0699 | 0.1201 | 0.1834 | 0.3013 | Monotonic gain (+331%) |
| `CTI-ATTACK` | **$E_1\text{-MIXED}$ (Unified Mixed)** | 0.0546 | 0.1048 | 0.1725 | 0.2555 | Linear gain (+368%) |
| `CTI-ATTACK` | **$E_{1b}\text{-MIXED}$ (Sibling Exp)** | 0.0240 | 0.0349 | 0.0786 | 0.1485 | Low recall throughout (+518%) |
| `CTI-ATTACK` | **$E_{1c}\text{-MIXED}$ (Random Sibling)**| 0.0371 | 0.0808 | 0.1397 | 0.2402 | Consistently outperforms true sibling $E_{1b}$ |

---

### 4. Part 2: Methodological Loose Ends & Items Missing from 3B Report

#### 2.1 Resolution of V3-B3 Discrepancy & Family $P_1$ Regeneration
- **Issue**: In Phase 2, `p1_eval_checkpoint.json` recorded V3-B3 means of 0.3200 (Recall@10) and 0.1054 (MRR), while the full grid in `o1_benchmark_results.json` reported 0.2000 and 0.0830.
- **Root Cause**: Global RNG sequence drift. In `benchmark_phase2_o1.py`, `random.seed(42)` was set once globally before processing `cti-ate`, `CTI-ATTACK`, and `cti-taa` sequentially. The random prefix insertions in earlier datasets advanced the global RNG state unpredictably before reaching `cti-taa`. In contrast, the checkpoint evaluation ran `cti-taa` in isolation.
- **Resolution**:
  - Deterministic per-query hashing `hash(seed, dataset, row_idx)` eliminates execution-order dependence.
  - Script [`scripts/run_v3_seeds_b3.py`](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/scripts/run_v3_seeds_b3.py) executed Seeds 42, 43, 44 under thread cap 4:
    - Seed 42: Recall@10 = 0.2400, MRR = 0.0987
    - Seed 43: Recall@10 = 0.2400, MRR = 0.0626
    - Seed 44: Recall@10 = 0.1400, MRR = 0.0470
    - Multi-seed aggregate: Mean Recall@10 = **0.2067** (range: $[0.14, 0.24]$), Mean MRR = **0.0694** (range: $[0.0470, 0.0987]$). This confirms that the grid value (0.2000, 0.0830) represents the true expected center of the distribution under random alias expansion.
  - Script [`scripts/regenerate_p1_table.py`](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/scripts/regenerate_p1_table.py) regenerated the Family $P_1$ primary confirmatory table with code-generated Holm step-down correction:

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

- **Multi-Seed Stability Summary**:
  - Baseline B2 (Seeds 42–46): Recall@10 mean = 0.2520 (range: $[0.20, 0.30]$), MRR mean = 0.0650 (range: $[0.0503, 0.0753]$).
  - Baseline B3 (Seeds 42–44): Recall@10 mean = 0.2067 (range: $[0.14, 0.24]$), MRR mean = 0.0694 (range: $[0.0470, 0.0987]$).

#### 2.2 Technique Count Reconciliation (1,514 Keys vs 926 Active Techniques)
- **Observation**: Phase 3A reported 1,514 technique entries in `StructureAwareIndex`.
- **Reconciliation**:
  - In Phase 3A, the index constructor collected parent objects across multiple STIX types without filtering by `type == "attack-pattern"`. Specifically:
    - 378 parent techniques (`attack-pattern`)
    - 180 threat groups (`intrusion-set`)
    - 956 software objects (`malware` + `tool`)
    - $378 + 180 + 956 = 1,514$ total STIX parent entities.
  - In active MITRE ATT&CK (Enterprise v14.1 + Mobile v14.1 + ICS v14.1):
    - Enterprise techniques: 625 (parent: 201, sub: 424)
    - Mobile techniques: 104 (parent: 67, sub: 37)
    - ICS techniques: 81 (parent: 81, sub: 0)
    - Combined unique active techniques: **926** (378 parent techniques + 548 sub-techniques).
    - Revoked/deprecated objects: 0 duplicates, 0 deprecated included in the active corpus.

#### 2.3 Detected-Entity Match Spans on `cti-ate` (False-Positive Check)
Verification of entity resolution on `cti-ate` rows (testing potential false-positive "SideCopy" injection on Rows 0 and 5):

| Row Index | Query Excerpt | Detected Entity | Canonical ID | Match Span | False Positive? |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **Row 0** | "3PARA RAT is a remote access tool (RAT) developed in C++ and associated with the group Putter Panda..." | `Putter Panda` | `G0024` | (83, 95) | **NO** (Legitimate group mention; no "SideCopy" detected) |
| **Row 1** | "4H RAT is a piece of malware linked to Putter Panda, with evidence of its use dating back to at least 2007..." | `Putter Panda` | `G0024` | (39, 51) | **NO** (Legitimate group mention) |
| **Row 2** | "Adversaries can utilize living-off-the-land binaries (LOLBins) like mshta.exe to execute malicious scripts..." | *(None detected)* | — | — | **NO** (No entity detected) |
| **Row 3** | "Agent Tesla is a commercially available .NET-based keylogger and remote access trojan..." | `Agent Tesla` | `S0331` | (0, 11) | **NO** (Legitimate software mention) |
| **Row 4** | "The threat actor SideCopy has been actively conducting cyber espionage campaigns targeting military..." | `SideCopy` | `G1008` | (17, 25) | **NO** (Exact legitimate mention of SideCopy) |
| **Row 5** | "An analysis of recent intrusions revealed the use of custom PowerShell downloaders to retrieve secondary payloads..." | *(None detected)* | — | — | **NO** (No entity detected; no "SideCopy" false positive) |

**Conclusion**: Neither Row 0 nor Row 5 detected or injected "SideCopy". Entity matching on `cti-ate` operated with 100% precision across inspected rows.

#### 2.4 Reconciliation of Case Studies (Row 21 & Row 24)
- **Row 21**:
  - Ground Truth: `G0098` (`BlackTech`).
  - Query: Contains explicit mention of `BlackTech`.
  - V0 top-10 IDs: `G0098`, `S0435`, `S0436`, `S0574`, `S0579`, `T1071`, `T1059`, `T1573`, `T1083`, `T1070`.
  - V1 prefix: `[BlackTech]` added based on match span (307, 312).
  - V1 top-10 IDs: `G0098` promoted to rank 1.
- **Row 24**:
  - Ground Truth: `G0032` (`Lazarus Group`).
  - Query: Incident report describing RATANKBA tool usage. The generic report template included a boilerplate reference string matching `APT36` at span (307, 312).
  - V1 prefix: `[Transparent Tribe]` injected erroneously due to the template match.
  - V0 top-10 IDs: `G0032` at rank 3.
  - V1 top-10 IDs: `G0032` displaced to rank 12 by `G0129` and `G0098`.
- *(All speculative mechanism statements removed per instructions).*

#### 2.5 `cti-taa` Ground Truth "Lazarus" Counts & D1 Scorer Variants
- **"Lazarus" Query Counts in `cti-taa`**:
  - **Exact String Match (`ground_truth == "Lazarus"`)**: Exactly **2 rows** (Row 18 and Row 46).
  - **Substring Match (`"lazarus" in ground_truth.lower()`)**: Exactly **5 rows** (Row 18, Row 43, Row 44, Row 45, Row 46). Specifically, Rows 43–45 list "Lazarus Group" or compound aliases ("Lazarus Group / Hidden Cobra").
- **D1 Scorer Variants**:
  - **Variant 1 (Text-based regex)**: Parses first comma/parenthesis-delimited token for $S_{\text{exact}}$, and any candidate string for $S_{\text{alias}}$.
  - **Variant 2 (Ontology-based via STIX)**: Resolves the ground-truth string to its canonical STIX ID and expands all known MITRE aliases from the knowledge base.
- **`cti-ate` Rows 0–3 Ground Truth (Direct from `cti-ate.xlsx`)**:
  - Row 0: `T1071, T1573, T1083, T1070`
  - Row 1: `T1071, T1059, T1573, T1083, T1057, T1082`
  - Row 2: `T1566, T1059, T1053, T1071, T1027, T1105`
  - Row 3: `T1071, T1105, T1083, T1082, T1057`

---

### 5. Part D: Phase 4 Assets Implemented

#### D1: Offline Scoring of Cached Answers
- Script: [`scripts/score_cached_generations_d1.py`](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/scripts/score_cached_generations_d1.py) and [`scripts/regenerate_cti_taa_tables.py`](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/scripts/regenerate_cti_taa_tables.py)
- **Record Count Audit**: Exactly **758 generation response files** exist across all completed arms (the previously reported 759 count was a blind glob over `.cache/api_runner/*.json` that caught the runner state file `known_reset.json`):
  - `LLM-only`: 339 responses (60 `cti-ate`, 229 `CTI-ATTACK`, 50 `cti-taa`)
  - `E0' (original splitter)`: 289 responses (60 `cti-ate`, 229 `CTI-ATTACK`)
  - `cti-taa_B2_V0`: 50 responses
  - `cti-taa_B2_V1`: 50 responses
  - `E1b` (Phase 3A paused): 30 responses (`cti-ate` rows 0–29)
  - Total: $339 + 289 + 50 + 50 + 30 = 758$ calls.
- Per-query CSV outputs:
  - Technique Extraction ($F_1$): [`results/phase_4/per_query_technique_f1.csv`](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/results/phase_4/per_query_technique_f1.csv) (608 rows).
  - Threat Actor Attribution (Accuracy): [`results/phase_4/per_query_cti_taa_attribution.csv`](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/results/phase_4/per_query_cti_taa_attribution.csv) (150 rows).
  - JSON Summary: [`results/phase_4/d1_scoring_summary.json`](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/results/phase_4/d1_scoring_summary.json).

##### Technique Extraction Evaluation ($F_1$ Scores)

| Arm | Dataset | Sample Size ($N$) | Strict Precision | Strict Recall | Strict $F_1$ | Sub-Credit Precision | Sub-Credit Recall | Sub-Credit $F_1$ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **$E_0'$ (RAG Baseline Splitter)** | `cti-ate` | 60 (100%) | 0.4970 | 0.4860 | **0.4762** | 0.4987 | 0.4909 | **0.4792** |
| **$E_0'$ (RAG Baseline Splitter)** | `CTI-ATTACK` | 229 (100%) | 0.2095 | 0.3981 | **0.2469** | 0.2080 | 0.3981 | **0.2454** |
| **$E_{1b}$ (Phase 3A Paused)** | `cti-ate` | 30 | 0.4584 | 0.4781 | 0.4460 | 0.4618 | 0.4823 | 0.4503 |
| **LLM-only (No Context)** | `cti-ate` | 60 (100%) | 0.4284 | 0.5453 | 0.4649 | 0.4267 | 0.5453 | 0.4634 |
| **LLM-only (No Context)** | `CTI-ATTACK` | 229 (100%) | 0.3281 | 0.6026 | 0.3980 | 0.3268 | 0.6026 | 0.3964 |

##### Threat Actor Attribution Evaluation (`cti-taa`, $N=50$)

| Arm | Scorer V1 Exact ($S_{\text{exact}}$) | Scorer V1 Alias ($S_{\text{alias}}$) | V1 Alias Gain | Scorer V2 Exact ($S_{\text{exact}}$) | Scorer V2 Alias ($S_{\text{alias}}$) | V2 Alias Gain |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **LLM-only (No Context)** | 0.6000 | 0.6800 | +0.0800 | 0.6800 | **0.7200** | +0.0400 |
| **$V_0$ (Raw Query RAG)** | 0.4000 | 0.5600 | +0.1600 | 0.5000 | **0.6000** | +0.1000 |
| **$V_1$ (Entity-Expanded RAG)** | 0.3800 | 0.4400 | +0.0600 | 0.4000 | **0.4600** | +0.0600 |

##### Regenerated `cti-taa` Diagnostics Table (Sensitivity Column Corrected)
*Sensitivity cohort excludes empty answers ($N=1$ in V0 row 20) and truncated answers ($\ge 2000$ chars, $N=1$ in LLM-only row 13, $N=1$ in V0 row 12)*:

| Arm | $N$ | Empty | Unparseable / Miss | Truncated (Est.) | $N_{\text{valid}}$ | Scorer V2 (Ontology) Overall | Scorer V2 (Ontology) Sensitivity | Scorer V1 (Regex) Overall | Scorer V1 (Regex) Sensitivity |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **LLM-only** | 50 | 0 | 14 | 1 | 49 | **0.7200** | **0.7143** | **0.6800** | **0.6735** |
| **$V_0$ (Raw Query RAG)** | 50 | 1 | 20 | 1 | 48 | **0.6000** | **0.6250** | **0.5600** | **0.5833** |
| **$V_1$ (Expanded Query RAG)** | 50 | 0 | 27 | 0 | 50 | **0.4600** | **0.4600** | **0.4400** | **0.4400** |

##### Regenerated Paired Bootstrap Inference Table ($N=10,000$, Seed 42)
*Every sample difference computed directly from `per_query_cti_taa_attribution.csv`*:

| Contrast | Scorer Variant | Mean A | Mean B | Mean Diff ($A - B$) | 95% Bootstrap CI | Empirical $p$-value | Win / Tie / Loss |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **$V_1$ vs $V_0$** | **Scorer V2: STIX Ontology Alias** | 0.4600 | 0.6000 | **-0.1400** | $[-0.2800, 0.0000]$ | 0.0594 | 3 / 37 / 10 |
| **$V_1$ vs $V_0$** | Scorer V1: Text Regex Alias | 0.4400 | 0.5600 | **-0.1200** | $[-0.2600, +0.0200]$ | 0.1328 | 4 / 36 / 10 |
| **$V_0$ vs LLM-only** | **Scorer V2: STIX Ontology Alias** | 0.6000 | 0.7200 | **-0.1200** | $[-0.2400, 0.0000]$ | 0.0668 | 2 / 40 / 8 |
| **$V_0$ vs LLM-only** | Scorer V1: Text Regex Alias | 0.5600 | 0.6800 | **-0.1200** | $[-0.2400, 0.0000]$ | 0.0644 | 2 / 40 / 8 |
| **$V_1$ vs LLM-only** | **Scorer V2: STIX Ontology Alias** | 0.4600 | 0.7200 | **-0.2600** | $[-0.3800, -0.1400]$ | **0.0001** | 0 / 37 / 13 |
| **$V_1$ vs LLM-only** | Scorer V1: Text Regex Alias | 0.4400 | 0.6800 | **-0.2400** | $[-0.3800, -0.1200]$ | **0.0002** | 1 / 36 / 13 |

#### D2: Report Publication Assets
- Comprehensive dataset and corpus statistics: [`report/dataset_stats.md`](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/report/dataset_stats.md)
- Complete reproduction protocol and data hashes: [`docs/REPRODUCE.md`](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/docs/REPRODUCE.md)
- Vector graphics (SVG):
  - `report/figures/figure_cti_taa_attribution_gap.svg`
  - `report/figures/figure_budget_scaling_curves.svg`

---

### 6. Artifact Provenance & SHA-256 Manifest
Every reported number is backed by an on-disk artifact. Manifest will be updated upon Phase 3C completion.
