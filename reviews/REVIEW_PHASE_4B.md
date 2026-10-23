# Phase 4B Review Report: Fix Round & Rigor Audit

**Date**: 2026-10-23  
**Status**: COMPLETE (Offline Audit & Rigor Verification)  
**Execution Environment**: Strict offline evaluation (`OFFLINE_ONLY=true`, thread cap = 4 via `OMP_NUM_THREADS=4`, `torch.set_num_threads(4)`)  
**Cryptographic Freeze Manifest**: `results/freeze_manifest.json` (74 verified artifacts)  
**Parent Review**: [reviews/REVIEW_PHASE_4.md](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/reviews/REVIEW_PHASE_4.md)  

---

## Scope & Delta Overview

This document reports exclusively the corrections, recomputations, audits, and scope adjustments executed in **Phase 4B** relative to [reviews/REVIEW_PHASE_4.md](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/reviews/REVIEW_PHASE_4.md). All statements adhere to a neutral scientific tone without causal language.

Summary of changes across the 10 audit items:
1. **Item 1 (Generation Completion)**: Documented 47 uncached rows remaining for $E_{1b}\text{-MIXED}$ on `CTI-ATTACK` (rows 182–228) due to the daily API quota cap; skipped offline freeze without freezing incomplete runs.
2. **Item 2 (A8 Recompute on `cti-taa` B2)**: Recomputed both object-level and text-inclusive credit under matched $B=500$ tokens and unconstrained top-10 chunks. Verified programmatic identity $\sum \Delta_i = \text{wins} - \text{losses}$. Resolved three empirical values of $E_0'$ (0.30, 0.34, 0.12). Reclassified Claim C6 to "Not established".
3. **Item 3 (Budget-Binding Audit)**: Audited all 48 cells in Table 5 for chunk saturation and token caps. Identified 6 non-binding cells where token count was constrained by the retriever $k=50$ chunk cap rather than the token budget; marked them with dagger `†`.
4. **Item 4 (Generation Failure Audit)**: Enumerated empty answers (1), errors/blocks (0), 512-token cap truncations (29 across all arms), abstentions (38), and zero-parsed outputs (3). Reported technique F1 and attribution accuracy for both All ($N$) and Clean subsets.
5. **Item 5 (Row Accounting)**: Reconciled 850 rows in `per_query_technique_f1.csv` (identifying 30 superseded Phase 3A pilot rows) and 1,001 cache files in `.cache/api_runner/`.
6. **Item 6 (ATT&CK Version Audit)**: Replaced designation "v14.1" with the verifiable STIX 2.0 unversioned rolling master snapshot (`x_mitre_attack_spec_version = 3.3.0`, modified `2026-07-31`). Reconciled active and revoked technique counts across Enterprise (697 active), Mobile (125 active), and ICS (104 active), totaling 926 active techniques.
7. **Item 7 (Detector Precision & V1-Strict)**: Exported top 30 detected aliases in `cti-taa` queries and generated a 100-sample randomized verification dataset (`results/phase_4b/detector_labels.csv`). Executed exploratory V1-strict retrieval on Baseline B2 (Recall@10 = 0.3600, MRR = 0.1326; $\Delta = +0.0200, +0.0664$ vs V0).
8. **Item 8 (Table Fixes)**: Merged `P2'_03` and `P2'_04` in Table 4; formatted empirical zero $p$-values as `$p < 0.0001$`; labeled negative Holm-significant rows as "Significant decrease"; added `cti-taa` generation contrasts with 95% bootstrap CIs to Table 6; added explicit definitions of Scorer V1 and Scorer V2 to Table 1.
9. **Item 9 (Claim C9 & C8 Scoping)**: Re-scoped Claim C9 to STIX-based retrieval alias expansion on `cti-taa`. Annotated Claim C8 with an explicit pretraining test-set contamination hypothesis.
10. **Item 10 (Reproduction Pipeline)**: Updated [docs/REPRODUCE.md](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/docs/REPRODUCE.md) with reproduction commands for all Phase 4B audits and scripts.

---

## 1. Generation Completion Audit

- **Runner Status**: Autonomous background runner (`task-6874`, PID 22196) encountered HTTP 429 `RESOURCE_EXHAUSTED` (Google Gemini API daily rolling quota limit of 500 requests per 24 hours).
- **Completed Cache Count**:
  - `LLM-only`: 339 / 339 complete (`cti-ate`: 60, `CTI-ATTACK`: 229, `cti-taa`: 50)
  - $E_0'$ (Baseline Splitter RAG): 289 / 289 complete (`cti-ate`: 60, `CTI-ATTACK`: 229)
  - $E_{1b}\text{-MIXED}$ (Structure-Aware Sibling Expansion, $B^* = 500$):
    - `cti-ate`: 60 / 60 complete
    - `CTI-ATTACK`: 182 / 229 complete (rows 0–181 cached; **exactly 47 uncached rows remaining**, rows 182–228)
  - `cti-taa` Baseline B2 $V_0$: 50 / 50 complete
  - `cti-taa` Baseline B2 $V_1$: 50 / 50 complete
  - Superseded Pilot $E_{1b}$ (Phase 3A): 30 / 30 complete (`cti-ate` rows 0–29)
- **Protocol Action**: In accordance with Phase 4B protocol Item 1, generation runs for Family $G_1$ were not frozen while `CTI-ATTACK` $E_{1b}\text{-MIXED}$ remains incomplete. Final re-evaluation of $G_1$ at $N=229$ is deferred until all 47 rows are cached. The $E_1\text{-MIXED}$ (no-sibling) generation arm is recorded as optional and lowest priority.

---

## 2. Threat Actor Attribution Recompute (A8 Recompute on `cti-taa` B2)

Recomputed strictly from per-query retrieval context files on `cti-taa` Baseline B2 ($N=50$) across $E_0'$, $E_1\text{-MIXED}$ (no siblings), and $E_{1b}\text{-MIXED}$ (with siblings).

### Credit Rules Evaluated
- **Object-Level Credit**: A STIX intrusion-set object whose canonical name or aliases match ground truth is present in the retrieved context metadata.
- **Text-Inclusive Credit**: The canonical name or alias string of the ground-truth threat group appears anywhere within the retrieved context text.

### Empirical Results

| Setting | Credit Rule | Contrast | Treatment Mean | Control Mean | Mean $\Delta$ | 95% Bootstrap CI | Raw $p$-value | Wins / Ties / Losses | $\sum \Delta_i$ | $\text{Wins} - \text{Losses}$ |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **$B=500$ tokens** | Object-level | $E_1\text{-MIXED}$ vs $E_0'$ | 0.0000 | 0.0200 | -0.0200 | [-0.0600, 0.0000] | 0.6336 | 0 / 49 / 1 | -1 | -1 |
| **$B=500$ tokens** | Object-level | $E_{1b}\text{-MIXED}$ vs $E_0'$ | 0.1000 | 0.0200 | +0.0800 | [+0.0200, +0.1600] | 0.0579 | 4 / 46 / 0 | +4 | +4 |
| **$B=500$ tokens** | Object-level | $E_{1b}\text{-MIXED}$ vs $E_1\text{-MIXED}$ | 0.1000 | 0.0000 | +0.1000 | [+0.0200, +0.1800] | 0.0301 | 5 / 45 / 0 | +5 | +5 |
| **$B=500$ tokens** | Text-inclusive | $E_1\text{-MIXED}$ vs $E_0'$ | 0.0400 | 0.3000 | -0.2600 | [-0.4000, -0.1200] | 0.0001 | 1 / 35 / 14 | -13 | -13 |
| **$B=500$ tokens** | Text-inclusive | $E_{1b}\text{-MIXED}$ vs $E_0'$ | 0.1000 | 0.3000 | -0.2000 | [-0.3400, -0.0600] | 0.0064 | 2 / 36 / 12 | -10 | -10 |
| **$B=500$ tokens** | Text-inclusive | $E_{1b}\text{-MIXED}$ vs $E_1\text{-MIXED}$ | 0.1000 | 0.0400 | +0.0600 | [0.0000, +0.1400] | 0.1190 | 3 / 47 / 0 | +3 | +3 |
| **$B=\text{None}$ (Top-10)** | Object-level | $E_1\text{-MIXED}$ vs $E_0'$ | 0.0400 | 0.0200 | +0.0200 | [-0.0400, +0.0800] | 0.7639 | 2 / 47 / 1 | +1 | +1 |
| **$B=\text{None}$ (Top-10)** | Object-level | $E_{1b}\text{-MIXED}$ vs $E_0'$ | 0.0400 | 0.0200 | +0.0200 | [-0.0400, +0.0800] | 0.7639 | 2 / 47 / 1 | +1 | +1 |
| **$B=\text{None}$ (Top-10)** | Object-level | $E_{1b}\text{-MIXED}$ vs $E_1\text{-MIXED}$ | 0.0400 | 0.0400 | 0.0000 | [0.0000, 0.0000] | 1.0000 | 0 / 50 / 0 | 0 | 0 |
| **$B=\text{None}$ (Top-10)** | Text-inclusive | $E_1\text{-MIXED}$ vs $E_0'$ | 0.6000 | 0.3000 | +0.3000 | [+0.1400, +0.4600] | 0.0002 | 18 / 29 / 3 | +15 | +15 |
| **$B=\text{None}$ (Top-10)** | Text-inclusive | $E_{1b}\text{-MIXED}$ vs $E_0'$ | 0.6000 | 0.3000 | +0.3000 | [+0.1400, +0.4600] | 0.0002 | 18 / 29 / 3 | +15 | +15 |
| **$B=\text{None}$ (Top-10)** | Text-inclusive | $E_{1b}\text{-MIXED}$ vs $E_1\text{-MIXED}$ | 0.6000 | 0.6000 | 0.0000 | [0.0000, 0.0000] | 1.0000 | 0 / 50 / 0 | 0 | 0 |

- **Identity Verification**: Across all 12 contrasts, the programmatic identity $\sum \Delta_i = \text{wins} - \text{losses}$ was evaluated and confirmed without discrepancies.
- **Reconciliation of $E_0'$ Empirical Means on `cti-taa` (50 queries)**:
  1. **`0.30` in A8 Recompute ($B=500$, Text-inclusive)**: Under 500-token prompt truncation, approximately 12 recursive chunks fit into context; text substring matching for group canonical names and aliases matched in 15 of 50 queries ($15 / 50 = 0.3000$).
  2. **`0.34` in Phase 1 / Family P1 ($B=\text{None}$, Top-10 Chunks, $S_{\text{alias}}$)**: Evaluated over unconstrained top-10 chunks under alias scoring, where 17 of 50 queries contained an alias match in the top 10 chunks ($17 / 50 = 0.3400$).
  3. **`0.12` under Exact Scoring ($S_{\text{exact}}$)**: Canonical string or MITRE ID matching strictly required the canonical STIX intrusion-set name or ID in the retrieved chunks, which was present in only 6 of 50 queries ($6 / 50 = 0.1200$).
- **Claim C6 Status Reclassification**: In Table 7, the status of Claim C6 is changed to **"Not established"**. Under matched 500-token budget, object-level evaluation shows no gain ($\Delta = -0.0200$, 0 wins, 49 ties, 1 loss) and text-inclusive evaluation shows a negative delta ($\Delta = -0.2600$); positive differences only appear when evaluation is unconstrained by token budget.

---

## 3. Token Budget Binding Audit on Table 5

Every cell in Table 5 (48 total cells: 2 datasets $\times$ 6 arms $\times$ 4 budgets) was programmatically audited for chunk saturation and token budget binding:

- **Audit Metrics Computed**:
  - Mean chunks retrieved per query.
  - Mean tokens in prompt context.
  - Fraction of queries where prompt tokens reached budget.
- **Non-Binding Criterion**: When mean prompt tokens are strictly below budget on $>50\%$ of queries due to exhaustion of the top-$k=50$ retrieval candidate pool, the cell is classified as non-binding.
- **Identified Non-Binding Cells**:
  1. `cti-ate`, $B=4000$, $E_0'$: Mean chunks = 50.0 (top-$k$ capped), Mean tokens = 2273.6 tokens (< 4000 tokens on 100% of queries). **Non-binding**.
  2. `cti-ate`, $B=4000$, $E_0'\text{-TECH}$: Mean chunks = 50.0 (top-$k$ capped), Mean tokens = 2095.2 tokens (< 4000 tokens on 100% of queries). **Non-binding**.
  3. `CTI-ATTACK`, $B=2000$, $E_0'$: Mean chunks = 49.97, Mean tokens = 1572.4 tokens (< 2000 tokens on 100% of queries). **Non-binding**.
  4. `CTI-ATTACK`, $B=2000$, $E_0'\text{-TECH}$: Mean chunks = 50.0, Mean tokens = 1379.9 tokens (< 2000 tokens on 100% of queries). **Non-binding**.
  5. `CTI-ATTACK`, $B=4000$, $E_0'$: Mean chunks = 50.0, Mean tokens = 1574.4 tokens (< 4000 tokens on 100% of queries). **Non-binding**.
  6. `CTI-ATTACK`, $B=4000$, $E_0'\text{-TECH}$: Mean chunks = 50.0, Mean tokens = 1379.9 tokens (< 4000 tokens on 100% of queries). **Non-binding**.
- **Table 5 Update**: All 6 non-binding cells are marked with a dagger (`†`) in Table 5 with the footnote: *"† Non-binding: candidate pool was exhausted before the token budget was filled"*. All structure-aware arms ($E_{1a}$, $E_1\text{-MIXED}$, $E_{1b}\text{-MIXED}$, $E_{1c}\text{-MIXED}$) remained binding at 4000 tokens.

---

## 4. Generation Failure & Abstention Audit

Audited across all 1,001 on-disk cache records in `.cache/api_runner/`.

### Failure Enumeration by Arm

| Arm | Dataset(s) | Total Rows ($N$) | Empty Answers | Error / Blocked | Hit 512 Cap (`cl100k_base`)* | Abstentions ("not in context") | Zero Parsed IDs | Excluded Failure Rows | Clean Evaluated ($N$) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `LLM-only` | `cti-ate`, `CTI-ATTACK`, `cti-taa` | 339 | 0 | 0 | 19 | 0 | 0 | 0 | 339 (289 tech) |
| $E_0'$ | `cti-ate`, `CTI-ATTACK` | 289 | 0 | 0 | 7 | 22 | 3 | 25 | 264 |
| $E_{1b}\text{-MIXED}$ | `cti-ate`, `CTI-ATTACK` | 242 | 0 | 0 | 3 | 16 | 0 | 16 | 226 |
| `cti-taa V0` | `cti-taa` (B2) | 50 | 1 | 0 | 0 | 0 | N/A | 1 | 49 |
| `cti-taa V1` | `cti-taa` (B2) | 50 | 0 | 0 | 0 | 0 | N/A | 0 | 50 |

*\*Note on Truncation Metric*: Native API `finish_reason` was not captured in the cache JSON structure; token truncation was therefore measured via `tiktoken` (`cl100k_base`) $\ge 512$ tokens.

### Performance Comparison: All ($N$) vs Clean

| Arm | Metric | All ($N$) Performance | Clean Performance | Difference |
| :--- | :--- | :---: | :---: | :---: |
| `LLM-only` | Technique F1 (`sub_credit`, $N=289$) | 0.4103 | 0.4103 | 0.0000 |
| $E_0'$ | Technique F1 (`sub_credit`) | 0.2939 ($N=289$) | 0.3064 ($N=264$) | +0.0125 |
| $E_{1b}\text{-MIXED}$ | Technique F1 (`sub_credit`) | 0.1437 ($N=242$) | 0.1466 ($N=226$) | +0.0029 |
| `cti-taa V0` | Attribution Accuracy (Scorer V2, Alias) | 0.6000 ($N=50$) | 0.6122 ($N=49$) | +0.0122 |
| `cti-taa V0` | Attribution Accuracy (Scorer V2, Exact) | 0.5000 ($N=50$) | 0.5102 ($N=49$) | +0.0102 |
| `cti-taa V1` | Attribution Accuracy (Scorer V2, Alias) | 0.4600 ($N=50$) | 0.4600 ($N=50$) | 0.0000 |
| `cti-taa V1` | Attribution Accuracy (Scorer V2, Exact) | 0.4000 ($N=50$) | 0.4000 ($N=50$) | 0.0000 |

Table 6 has been updated to include both All ($N$) and Clean performance metrics.

---

## 5. Row Accounting & Artifact Reconciliation

### 5.1 Reconciliation of `per_query_technique_f1.csv` (850 Rows)
- Total rows in file: 850 rows.
- Breakdown:
  - $E_0'$: 289 rows (`cti-ate`: 60, `CTI-ATTACK`: 229)
  - `LLM-only`: 289 rows (`cti-ate`: 60, `CTI-ATTACK`: 229)
  - $E_{1b}\text{-MIXED}$: 242 rows (`cti-ate`: 60, `CTI-ATTACK`: 182)
  - Superseded Pilot $E_{1b}$ (Phase 3A): 30 rows (`cti-ate` rows 0–29)
- **Resolution**: The 30 rows beyond 820 belong to the Phase 3A pilot arm $E_{1b}$ on `cti-ate`. Excluding these 30 pilot rows yields exactly 820 rows for the active experimental arms.

### 5.2 Reconciliation of Generation Cache (1,001 Files)
- Total files in `.cache/api_runner/`: 1,001 files.
- Breakdown:
  - $E_0'$: 289 files
  - Superseded Pilot $E_{1b}$: 30 files
  - $E_{1b}\text{-MIXED}$: 242 files
  - `LLM-only`: 339 files
  - `cti-taa_B2_V0`: 50 files
  - `cti-taa_B2_V1`: 50 files
  - Runner State: 1 file (`known_reset.json`)
  - **Sum**: $289 + 30 + 242 + 339 + 50 + 50 + 1 = 1,001\text{ files}$.

---

## 6. ATT&CK Knowledge Base Version Audit

- **Bundle Source**: The knowledge base files in `data/mitre/` represent an unversioned snapshot from the MITRE CTID rolling repository master branch (filesystem modification date: `2026-07-31`).
- **Specification Versions**:
  - STIX Specification: `spec_version = 2.0`
  - ATT&CK Specification: `x_mitre_attack_spec_version = 3.3.0` (with 3.2.0 objects)
- **Domain Technique Inventory**:
  - **Enterprise**: 222 active parents, 475 active sub-techniques (697 total active); 149 revoked, 12 deprecated.
  - **Mobile**: 78 active parents, 47 active sub-techniques (125 total active); 53 revoked, 12 deprecated.
  - **ICS**: 78 active parents, 26 active sub-techniques (104 total active); 9 revoked, 14 deprecated.
  - **Total Active Techniques Across All Domains**: 378 parent + 548 sub-techniques = **926 active techniques**.
- **Correction Applied**: The label "v14.1" was removed from all assets, tables, and documentation. Table 1 and Table 7 now state the exact rolling master modified date (`2026-07-31`) and specification version (`3.3.0`).

---

## 7. Detector Precision & Exploratory V1-Strict Evaluation

### 7.1 Top 30 Detected Aliases on `cti-taa` (50 Queries)
Extracted and saved to `results/phase_4b/top30_detected_aliases.json`:
1. `NET` (79 matches, length 3, tool "Net", common English / command)
2. `Crimson` (67 matches, length 7, malware "Crimson")
3. `APT36` (54 matches, length 5, intrusion-set "Transparent Tribe")
4. `Hornbill` (40 matches, length 8, malware "Hornbill")
5. `SunBird` (35 matches, length 7, malware "Sunbird")
6. `cmd.exe` (33 matches, length 7, tool "cmd")
7. `Solar` (27 matches, length 5, malware "Solar", common English word)
8. `Quick Assist` (26 matches, length 12, tool "Quick Assist")
9. `Cobalt Strike` (24 matches, length 13, malware "Cobalt Strike")
10. `Bandook` (21 matches, length 7, malware "Bandook")
11. `AsyncRAT` (21 matches, length 8, tool "AsyncRAT")
12. `KOPILUWAK` (21 matches, length 9, malware "KOPILUWAK")
13. `Turla` (20 matches, length 5, intrusion-set "Turla")
14. `Gomir` (18 matches, length 5, malware "Gomir")
15. `SC5k` (17 matches, length 4, malware "SampleCheck5000")
16. `SideCopy` (15 matches, length 8, intrusion-set "SideCopy")
17. `TONESHELL` (14 matches, length 9, malware "TONESHELL")
18. `page` (14 matches, length 4, malware "Elise", common English word)
19. `QUIETCANARY` (14 matches, length 11, malware "QUIETCANARY")
20. `Impacket` (13 matches, length 8, tool "Impacket")
21. `Equation` (13 matches, length 8, intrusion-set "Equation")
22. `Qakbot` (12 matches, length 6, malware "QakBot")
23. `MagicRAT` (11 matches, length 8, malware "MagicRAT")
24. `POWERLESS` (11 matches, length 9, malware "PowerLess")
25. `ShadowPad` (10 matches, length 9, malware "ShadowPad")
26. `play` (10 matches, length 4, intrusion-set "Play", common English word)
27. `GoBear` (10 matches, length 6, malware "GoBear")
28. `MimiKatz` (8 matches, length 8, tool "Mimikatz")
29. `Troll Stealer` (8 matches, length 13, malware "Troll Stealer")
30. `SPICA` (8 matches, length 5, malware "Spica")

### 7.2 Human Verification Dataset
- A random sample of 100 detected matches (seed 42) with single-sentence context was exported to `results/phase_4b/detector_labels.csv` with an empty `is_real_entity_mention` column.
- No empirical precision estimate is assumed prior to completion of manual labeling.

### 7.3 Exploratory V1-Strict Retrieval Evaluation
- **Definition**: Filtered detection rule dropping aliases of length $\le 4$ and common English words / command names (`net`, `cmd`, `page`, `play`, `solar`, `find`, `sc`), retaining only intrusion-set and malware entity types.
- **Label**: *"post-hoc exploratory, outside P1, no Holm"*.
- **Baseline B2 Results ($N=50$)**:
  - $V_0$: Recall@10 = 0.3400, MRR = 0.0662
  - $V_{1\text{-strict}}$: Recall@10 = 0.3600, MRR = 0.1326
  - Differences vs $V_0$: $\Delta\text{Recall@10} = +0.0200$, $\Delta\text{MRR} = +0.0664$.
  - Comparison vs Unfiltered $V_1$: Unfiltered $V_1$ achieved Recall@10 = 0.2200 ($\Delta = -0.1200$ vs $V_0$). $V_{1\text{-strict}}$ achieved Recall@10 = 0.3600 ($\Delta = +0.0200$ vs $V_0$).

---

## 8. Table Fixes & Asset Updates

All publication tables in `results/phase_4/final_tables/` and figures in `report/figures/` were regenerated via `scripts/generate_final_assets.py`:

1. **Table 1 (Scoring Gap)**: Added explicit definitions of **Scorer V1** (text-based regex parsing) and **Scorer V2** (STIX ontology alias and canonical expansion).
2. **Table 4 (Family P2')**:
   - Merged `P2'_03` and `P2'_04` into single row `P2'_03/04` because `CTI-ATTACK` queries (~62 words) produce identical retrieved contexts under B2 and B3 windowing.
   - Formatted empirical zero $p$-values as `$p < 0.0001$`.
   - Labeled negative Holm-significant rows as "Significant decrease".
3. **Table 5 (Scaling Curves)**:
   - Added dagger (`†`) and footnote to all 6 non-binding cells identified in Item 3.
4. **Table 6 (Generation Contrasts)**:
   - Added `cti-taa` generation contrasts with 95% bootstrap confidence intervals:
     - $V_0$ vs LLM-only: $\Delta = -0.1200$ (95% CI [-0.2400, 0.0000], $p = 0.0685$)
     - $V_1$ vs $V_0$: $\Delta = -0.1400$ (95% CI [-0.2800, 0.0000], $p = 0.0630$)
     - $V_1$ vs LLM-only: $\Delta = -0.2600$ (95% CI [-0.3800, -0.1400], $p < 0.0001$)
   - Formatted $p = 0.0000$ as `$p < 0.0001$`.
   - Added Clean F1 and Clean Accuracy columns.
5. **Table 7 (Claims Audit Table)**:
   - Claim C6 status set to **"Not established"**.
   - Claim C8 updated with test-set contamination caveat.
   - Claim C9 re-scoped to STIX retrieval alias expansion.
6. **Figure Updates**:
   - `report/figures/figure_paired_deltas_forest.svg`: Updated to display merged `P2'_03/04` row.
7. **Freeze Manifest**:
   - Cryptographic manifest regenerated at `results/freeze_manifest.json` (74 verified files).

---

## 9. Claim C8 and C9 Scoping Amendments

### Claim C9 Scope
- **Previous Statement**: "Entity linking / graph expansion is harmful to RAG."
- **Amended Statement (in Table 7 and review)**:  
  *"The STIX-based retrieval alias expansion implemented in V1 reduced recall on cti-taa by 0.12 (P1_08), and generation accuracy by 0.14 under Scorer V2; whether other linkers or narrower aliases behave differently is not established by this experiment."*

### Claim C8 Caveat
- **Amended Statement (in Table 7 and review)**:  
  *"Under zero-shot technique extraction and actor attribution, Gemini 2.5 Flash-Lite achieves F1 = 0.41 and Attribution Accuracy = 0.72 without retrieval context, outperforming RAG baselines. [Hypothesis: Potential benchmark test-set contamination or high parametric pre-training exposure to public threat intelligence reports, as LLM-only achieves 0.72 accuracy on cti-taa and 0.41 F1 on technique extraction without context retrieval]."*

---

## 10. Reproduction Pipeline Verification

The reproduction document [docs/REPRODUCE.md](file:///c:/Users/Akshitha%20Reddy/OneDrive/Desktop/RAG%20Intel/docs/REPRODUCE.md) was updated with the full execution sequence for Phase 4B:
- A8 recompute: `python scripts/recompute_a8.py`
- Budget-binding audit: `python scripts/audit_budget_binding.py`
- Generation failure audit: `python scripts/audit_generation_failures.py`
- ATT&CK STIX version audit: `python scripts/audit_stix_version.py`
- Detector precision audit: `python scripts/analyze_detector_precision.py`
- Final asset and manifest regeneration: `python scripts/generate_final_assets.py`

**Programmatic Verification Assertion**: Every numerical value, percentage, test count, and confidence interval reported in this review and the publication tables is generated by executable scripts without manual entry.
