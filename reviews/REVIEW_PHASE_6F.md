# Phase 6F Review: Corrections, Methodological Rigor, and Reproducibility Audits

**Date**: 2026-10-26  
**Status**: Certified & Verified Offline (Zero API Calls)  
**Execution Context**: Independent post-hoc audit following Phase 6D/6E; frozen results from Phases 0–6B strictly preserved.

---

## Executive Summary

Phase 6F implements comprehensive statistical corrections, data provenance reconciliations, and methodological rigor audits across all project evaluation streams. All computations were executed strictly offline using verified benchmark logs and source datasets:

1. **Statistical Test Rectification (GEN_01 / GEN_02)**: Mismatched raw $p$-values in the primary generation family were traced to paired bootstrap simulations rather than the pre-registered exact two-sided binomial sign test. Correcting this family with exact sign tests reveals an important statistical distinction: **`GEN_01` (`cti-ate` technique extraction) fails to reject the null hypothesis ($p=0.0198 > 0.0167$) under Holm step-down correction**. Only `GEN_02` (`CTI-ATTACK`) remains statistically significant ($p=0.0007 \le 0.0125$).
2. **Unified Hygiene Summary Table**: Regenerated directly from source benchmark CSVs with programmatic assertions against every cell. Reconciles Phase 5 single-budget gains ($+0.1525$ at $B=500$ with $k=200$ pool expansion) with Phase 6B balanced ladder gains ($+0.0849$ across $\{500, 1000\}$ with fixed $k=50$ pool). Certified Enterprise STIX numbers show a negative delta on `cti-ate` under B3 ($-0.0410$, $p=0.0037$).
3. **Metadata-Credit Audit**: Evaluates Recall@B with metadata credit versus surface text-visible matching. On `cti-ate`, retrieval hygiene gains under surface matching are smaller/null ($-0.0125$ delta), and downstream generation technique F1 shows a null difference ($+0.0129$ on `cti-ate`, $+0.0116$ on `CTI-ATTACK`, non-significant).
4. **Noise Floor Stratification**: Classifies the 50 `cti-taa` queries into Active ($N=34$, 68.0%) and Inactive ($N=16$, 32.0%) strata. Queries 22 and 41 have empty software detections and identical contexts, placing their nominal wins in the Inactive stratum, where 100% of queries exhibit run-to-run lexical variation at temperature 0.0.
5. **Aggregate Attribution Statistics & Stoplist**: Replaces hand-picked case studies with 50-query aggregate metrics. An extended generic OS binary stoplist alters detections in 22.0% of queries (11/50) but produces 0 net change in downstream attribution.
6. **GT-Alias Leakage Audit**: Identifies 10 of 50 threat reports (20.0%) that contain ground-truth threat group aliases directly in the query body text. Rescoring on the clean 40-query subset reveals baseline $V_{\text{rel}}$ accuracy of 0.7000 vs 0.6750 for $V_{0h}$ and 0.6500 for LLM-only.
7. **Knowledge Base Integrity Audit**: Identifies 62 non-standard `S9000`-series STIX objects bundled in `data/mitre/*.json` (created Dec 2025 – Oct 2026). Audits confirm zero occurrences in retrieved prompt contexts and zero influence on attribution outcomes.
8. **Entity Detector Precision Audit**: Analyzes 100 labeled matches from `results/phase_4b/detector_labels.csv`. Surface D0 detector achieves 74.0% real entity precision (63.0% informative), while the post-hoc filtered D1/V1h detector achieves 76.9% precision, categorizing 26 false positives into three distinct error classes.

---

## 1. Item 1: Primary Generation Holm Family Rectification (GEN_01–GEN_04)

### Source of Discrepancy
In earlier reporting, raw $p$-values of $0.0014$ on `cti-ate` and $0.0001$ on `CTI-ATTACK` were cited alongside discordant pair counts of W/T/L = 18/6/36 and 44/102/83. An audit of `results/phase_6c/contrasts_table.csv` revealed that:
- Column 9 (`boot_p`) recorded paired bootstrap $p$-values ($0.0014$ and $0.0001$).
- Column 10 (`exact_sign_p`) recorded exact two-sided binomial sign test $p$-values ($0.0198$ and $0.00068$).

Under the pre-registered protocol specifying exact sign tests on discordant pairs ($n_{\text{discordant}} = W + L$):
- For `cti-ate` (`GEN_01`): $W=18, L=36 \implies n_{\text{discordant}}=54$. Exact binomial test: $p = 2 \times \sum_{k=0}^{18} \binom{54}{k} 0.5^{54} = 0.01980$.
- For `CTI-ATTACK` (`GEN_02`): $W=44, L=83 \implies n_{\text{discordant}}=127$. Exact binomial test: $p = 2 \times \sum_{k=0}^{44} \binom{127}{k} 0.5^{127} = 0.00068$.

### Corrected Holm Step-Down Table ($\alpha = 0.05, M=4$)

| Rank ($k$) | Test ID | Comparison | Metric | $\Delta$ | W / T / L | Exact Sign $p$ | Historical Bootstrap $p$ | Holm Threshold $\alpha^*$ | Corrected Decision |
| :---: | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **1** | `GEN_02` | HD vs LLM-only (`CTI-ATTACK`) | `f1_sub` | -0.0970 | 44/102/83 | **0.0007** | 0.0001 | 0.01250 ($0.05/4$) | **Reject Null (Favors LLM-only)** |
| **2** | `GEN_01` | HD vs LLM-only (`cti-ate`) | `f1_sub` | -0.0698 | 18/6/36 | **0.0198** | 0.0014 | 0.01667 ($0.05/3$) | **Fail to Reject Null (Not Significant)** |
| **3** | `GEN_03` | V0h vs LLM-only (`cti-taa`) | `v2_alias` | +0.0200 | 7/37/6 | **1.0000** | 0.8924 | 0.02500 ($0.05/2$) | Fail to Reject Null (No Difference) |
| **4** | `GEN_04` | Vrel vs V0h (`cti-taa`) | `v2_alias` | +0.0200 | 3/45/2 | **1.0000** | 1.0000 | 0.05000 ($0.05/1$) | Fail to Reject Null (No Difference) |

> [!IMPORTANT]
> **Key Methodological Finding**: Under multiplicity-controlled exact sign testing, **`GEN_01` is NOT statistically significant** ($p=0.0198 > 0.01667$). While raw paired bootstrap testing yielded $p=0.0014$, the exact sign test on 54 discordant pairs does not survive the Holm step-down boundary. Only `GEN_02` on `CTI-ATTACK` demonstrates a statistically significant performance deficit relative to `LLM-only`.

---

## 2. Item 2: Unified Query Hygiene Table & Data Provenance Reconciliation

The Query Hygiene summary table was regenerated directly from source CSVs (`secondary_kb_contrasts.csv`, `b1_robustness_contrasts.csv`, and `results/phase_6c/contrasts_table.csv`), with automated assertions verifying each cell against frozen evaluation artifacts.

### Certified Hygiene Summary Table across All Evaluation Regimes

| Evaluation Regime | Representation / Budget | Metric | `cti-ate` Control | `cti-ate` Treatment | `cti-ate` $\Delta$ | `cti-ate` Effect | `CTI-ATTACK` Control | `CTI-ATTACK` Treatment | `CTI-ATTACK` $\Delta$ | `CTI-ATTACK` Effect | Statistical Status |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **1. Recall@B Common Budgets (Phase 5)** | STIX-ALL chunks at single $B=500$ ($k=200$ pool) | `Recall_sub` | 0.0517 | 0.2042 | +0.1525 | **+ (Positive)** | 0.1725 | 0.5670 | +0.3945 | **+ (Positive)** | Significant gains at $B=500$ (confounds query hygiene with $k=200$ pool expansion) |
| **1b. Recall@B Balanced Budgets (Phase 6B)** | STIX-ALL chunks balanced $\{500, 1000\}$ ($k=50$ fixed pool) | `Mean Recall@B` | 0.1601 | 0.2450 | +0.0849 | **+ (Positive)** | 0.3064 | 0.6074 | +0.3010 | **+ (Positive)** | Significant isolated query hygiene gains under balanced evaluation with fixed pool $k=50$ |
| **2. Enterprise STIX Bundle (Phase 6D Part E)** | E0-STIX-ENT objects under B2 / B3 baselines | `Subtech_Recall@10` | 0.0895 (B2) / 0.1221 (B3) | 0.0813 (B2) / 0.0811 (B3) | -0.0082 (B2) / -0.0410 (B3) | **- (Negative on B3, Null on B2)** | 0.1812 (B2) / 0.1812 (B3) | 0.6303 (B2) / 0.6303 (B3) | +0.4491 (B2) / +0.4491 (B3) | **+ (Positive)** | Significantly negative on `cti-ate` B3 ($p=0.0037$); null on B2 ($p=0.1516$); massive positive on `CTI-ATTACK` ($p < 0.0001$) |
| **3. Long-Context Embeddings (Phase 6D Part D)** | B1 `nomic-embed-text-v1.5` (8k unchunked) | `Recall@10` | 0.0874 | 0.1809 | +0.0935 | **+ (Positive)** | 0.2118 | 0.5662 | +0.3544 | **+ (Positive)** | Significant on both datasets (exact sign $p=0.0033$ on `cti-ate`; $p < 0.0001$ on `CTI-ATTACK`) |
| **4. Downstream Live Generation (Phase 6C)** | `gemini-3.5-flash-lite` technique F1 at $B^*=500$ | `Technique F1 (f1_sub)` | 0.3807 | 0.3936 | +0.0129 | **0 (Null)** | 0.2878 | 0.2994 | +0.0116 | **0 (Null)** | Non-significant on both datasets (+0.013 on `cti-ate`, +0.012 on `CTI-ATTACK`; retrieval gains do not carry to generation) |

### Reconciliation: Phase 5 (+0.1525) vs Balanced Ladder (+0.0849) on `cti-ate`
- **Phase 5 Single-Budget Evaluation ($B=500$)**:
  - Evaluated at a single budget $B=500$ tokens.
  - Accompanied by candidate pool expansion from $k=50$ (raw splitter baseline) to $k=200$ (HD preprocessing).
  - Yielded raw baseline recall of $0.0517$ and HD recall of $0.2042$ ($\Delta = +0.1525$).
  - **Limitation**: Confounds pure query hygiene with candidate retrieval depth expansion ($k=50 \to k=200$).
- **Phase 6B Balanced Evaluation ($\{500, 1000\}$)**:
  - Evaluated across balanced budget intervals $\{500, 1000\}$ tokens.
  - Held candidate retrieval pool strictly fixed at $k=50$ for both control and treatment arms.
  - Yielded mean raw recall of $0.1601$ and mean hygiene recall of $0.2450$ ($\Delta = +0.0849$).
  - **Interpretation**: Isolates the genuine query hygiene effect without pool size confounding.

---

## 3. Item 3: Metadata-Credit Audit

To evaluate whether retrieval gains stem from ground-truth technique text presence or chunk-level metadata tagging, Recall@B was evaluated under two scoring paradigms across identical chunks and budgets ($B=500$):
1. **Metadata Credit**: Credit granted if the retrieved chunk's STIX metadata contains the ground-truth MITRE ID or if a retrieved child subtechnique credits its parent technique.
2. **Text-Visible Only**: Credit granted strictly via surface text regex matching on the verbatim prompt text (`contexts_used`).

### Comparative Audit Results ($B=500$)

| Dataset | Retrieval Arm | Recall@B (Metadata Credit) | Recall@B (Text-Visible Only) | Discrepancy ($\Delta$) | Explanatory Mechanism |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `cti-ate` | $E_0'$ (raw control) | 0.0517 | 0.0671 | -0.0154 | Raw chunks lack explicit ID prefixes; surface regex matches incidental technique mentions. |
| `cti-ate` | $E_0'\text{-HD-k200}$ | 0.2042 | 0.0546 | **+0.1496** | Structured metadata yields 0.2042 recall, but verbatim text context recall drops to 0.0546. |
| `cti-ate` | $E_{1h}$ (header-prefixed) | 0.1935 | 0.0919 | +0.1016 | Field headers bring technique IDs into surface text, increasing text visibility to 0.0919. |
| `CTI-ATTACK` | $E_0'$ (raw control) | 0.1725 | 0.1572 | +0.0153 | Balanced baseline alignment between metadata and verbatim text. |
| `CTI-ATTACK` | $E_0'\text{-HD-k200}$ | 0.5670 | 0.2154 | **+0.3516** | Structured metadata awards 0.5670 recall, whereas prompt text context coverage is 0.2154. |
| `CTI-ATTACK` | $E_{1h}$ (header-prefixed) | 0.5058 | 0.4709 | +0.0349 | Explicit text headers bridge the metadata-text gap, reaching 0.4709 text context recall. |

> [!NOTE]
> **Implications for Claims Table**:
> Under text-visible surface matching, the retrieval hygiene effect on `cti-ate` is smaller/null ($-0.0125$, from 0.0671 down to 0.0546). Furthermore, large retrieval recall gains on `CTI-ATTACK` (+0.35 to +0.39) do not translate into downstream generation improvements: live technique F1 changes by only $+0.0129$ on `cti-ate` and $+0.0116$ on `CTI-ATTACK` ($p \ge 0.4069$, statistically non-significant).

---

## 4. Item 4: Noise Strata Reclassification (`cti-taa`, $V_{\text{rel}}$ vs $V_{0h}$)

A query-by-query ledger was generated for all 50 `cti-taa` queries, tracking a strict boolean `context_identical` indicating whether relationship expansion added new prompt context relative to $V_{0h}$.

### Stratification Summary ($N=50$)

| Stratum | Definition | Queries ($N$) | Share (%) | $V_{0h}$ Accuracy | $V_{\text{rel}}$ Accuracy | W / T / L (Variant 2) | Run-to-Run Lexical Variation |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Active Stratum** | Context modified by $V_{\text{rel}}$ (`context_identical = False`) | 34 | 68.0% | 0.7647 (26/34) | 0.7941 (27/34) | 2 / 31 / 1 | N/A (contexts differ) |
| **Inactive Stratum** | Context 100% identical (`context_identical = True`) | 16 | 32.0% | 0.6875 (11/16) | 0.6875 (11/16) | 1 / 14 / 1 | **16 / 16 (100.0%)** |

### Reclassification of Cases 22 and 41
- **Case 22 (Query ID `337b6a14a4b4`)**: Entity detector matched zero entities; candidate vote list was empty. Context was 100% identical between $V_{0h}$ and $V_{\text{rel}}$ (`context_identical = True`).
- **Case 41 (Query ID `7172731bb34b`)**: Entity detector matched zero entities; candidate vote list was empty. Context was 100% identical between $V_{0h}$ and $V_{\text{rel}}$ (`context_identical = True`).
- **Audit Decision**: The nominal "wins" of $V_{\text{rel}}$ in Cases 22 and 41 **belong strictly to the Inactive stratum**.
- **Lexical Noise Floor**: Across all 16 queries in the Inactive stratum, the model produced differing text answers on 100% of queries (16/16) despite temperature `0.0`. The 1 win and 1 loss observed in this stratum represent non-deterministic sampling variation. In the Active stratum, $V_{\text{rel}}$ won 2 queries and lost 1 query. The overall net difference (+1 query, 76% vs 74%) is within the stochastic noise margin.

---

## 5. Item 5: Aggregate Case Studies & Generic OS Stoplist Audit

### Full 50-Query Aggregate Diagnostic Statistics

| Metric | Count ($N=50$) | Percentage | Description |
| :--- | :---: | :---: | :--- |
| **Non-Empty Candidate Vote List** | 34 / 50 | **68.0%** | Threat report contained software entities linked to threat groups. |
| **Ground Truth Group in Top-3 Votes** | 0 / 50 | **0.0%** | Zero queries had the ground-truth threat group in the top-3 candidate vote list. |
| **Ground Truth Group in Context** | 14 / 50 | **28.0%** | Retrieved context contained a valid alias ($\ge 4$ characters) of the ground truth group. |

### Win / Loss Counts Split by Diagnostic Flags ($V_{\text{rel}}$ vs $V_{0h}$, Scorer Variant 2)

| Diagnostic Condition | Subgroup $N$ | Wins | Losses | Ties | Win Rate ($\Delta$) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `has_votes = True` | 34 | 2 | 1 | 31 | +1 net win (+2.9%) |
| `has_votes = False` | 16 | 1 | 1 | 14 | 0 net win (0.0%) |
| `gt_in_context = True` | 14 | 1 | 0 | 13 | +1 net win (+7.1%) |
| `gt_in_context = False` | 36 | 2 | 2 | 32 | 0 net win (0.0%) |

### Generic OS Binary Stoplist Audit
Applying an extended stoplist (`arp`, `cmd.exe`, `fsutil`, `ftp`, `ipconfig`, `net`, `netstat`, `ping`, `powershell.exe`, `schtasks.exe`, `systeminfo`, `tasklist`, `whoami`):
- **Detection Altered**: **11 of 50 queries (22.0%)** changed their surface entity detections (Query indices: 4, 7, 11, 15, 17, 18, 20, 24, 25, 34, 43).
- **Attribution Impact**: Zero net change in downstream attribution accuracy (diffuse weights across hundreds of groups did not displace top-ranked groups).
- **Persistent Limitation (Case 26)**: In Case 26 (Iranian threat actor *Mint Sandstorm*), the report mentions a custom .NET backdoor named *Soldier*. The detector matches this to Chinese malware *SysUpdate* (S0663), injecting Chinese threat group *Threat Group-3390* (G0027) context into an Iranian incident report. This polysemy collision persists even after filtering generic utilities.

---

## 6. Item 6 & 7: Wording & Quota Accountings

### D2a Hybrid Prompting Reporting
- **Standardized Reporting String**: `'-0.0677 vs LLM-only on cti-ate (bootstrap CI [-0.117,-0.020], exact sign p=0.081)'`.
- Updated in Section 3 of `reviews/REVIEW_PHASE_6D.md`.

### Operational Quota Accounting
- **Observed Capacity**: The Gemini API served an observed per-window maximum of **$\ge 607$ successful calls** following the 07:00:00 UTC quota refresh on 2026-10-25 (totaling 998 calls across the reset boundary).
- **Documentation Update**: The phrase "nominal 500" has been removed across all reviews and replaced with observed per-window capacity notes.

---

## 7. Item 7b: Ground-Truth Alias Leakage Audit (`cti-taa`)

Each threat report body was tested for verbatim occurrences of ANY ground-truth group alias (canonical name or STIX aliases, length $\ge 4$ characters, case-insensitive) appearing outside the instruction template.

### Audit Findings
- **Leaked Queries Count**: Exactly **10 of 50 queries (20.0%)** contain ground-truth aliases directly in the report body:
  - Row 1 (`e1bc6616ddff`): Ground truth *Stately Taurus* contains alias *"Stately Taurus"*.
  - Row 22 (`337b6a14a4b4`): Ground truth *Mint Sandstorm* contains aliases *"APT35"*, *"Charming Kitten"*.
  - Row 23 (`488bd1c4770c`): Ground truth *MuddyWater* contains aliases *"MERCURY"*, *"TA450"*.
  - Row 26 (`b9933f2beb82`): Ground truth *Mint Sandstorm* contains aliases *"APT35"*, *"TA453"*, *"Charming Kitten"*, *"PHOSPHORUS"*.
  - Row 37 (`528efff074c3`): Ground truth *APT37* contains alias *"Reaper"*.
  - Row 38 (`1b269a49fca2`): Ground truth *APT33* contains aliases *"Peach Sandstorm"*, *"HOLMIUM"*.
  - Row 40 (`42f7ad174a80`): Ground truth *APT29* contains aliases *"NOBELIUM"*, *"The Dukes"*, *"CozyDuke"*, *"Midnight Blizzard"*, *"UNC2452"*, *"Cozy Bear"*, *"Dark Halo"*.
  - Row 42 (`9ebb692cad25`): Ground truth *Diamond Sleet* contains aliases *"Labyrinth Chollima"*, *"ZINC"*.
  - Row 48 (`3fd8c4b0f770`): Ground truth *MuddyWater* contains alias *"Crambus"*.
  - Row 49 (`159ae11fb113`): Ground truth *Turla APT* contains aliases *"Turla"*, *"Snake"*, *"WhiteBear"*.
- **Clean Queries Count**: **40 of 50 queries (80.0%)**.

### Comparative Rescoring: Clean Subset ($N=40$) vs Full Benchmark ($N=50$)

| Arm | Metric | Full Benchmark ($N=50$) | Clean Subset ($N=40$) | Leaked Subset ($N=10$) |
| :--- | :--- | :---: | :---: | :---: |
| **`LLM-only`** | Exact (`v1_exact`) | 0.6000 | 0.6000 | 0.6000 |
| **`LLM-only`** | Alias (`v2_alias`) | 0.7200 | 0.6500 | **1.0000** |
| **$V_{0h}$** | Exact (`v1_exact`) | 0.5800 | 0.5750 | 0.6000 |
| **$V_{0h}$** | Alias (`v2_alias`) | 0.7400 | 0.6750 | **1.0000** |
| **$V_{\text{rel}}$** | Exact (`v1_exact`) | 0.6000 | 0.6250 | 0.5000 |
| **$V_{\text{rel}}$** | Alias (`v2_alias`) | 0.7600 | 0.7000 | **1.0000** |
| **$V_0$** | Object Recall@10 | 0.3400 | 0.4000 | 0.1000 |
| **$V_{0h}$** | Object Recall@10 | 0.1400 | 0.1250 | 0.2000 |
| **$V_{\text{rel}}$** | Object Recall@10 | 0.3200 | 0.3250 | 0.3000 |

> [!NOTE]
> **Interpretation**: On the 10 leaked queries, `v2_alias` is 1.0000 across all generation arms because the model extracts the threat actor name directly from the threat report prose. On the clean subset ($N=40$), $V_{\text{rel}}$ achieves 0.7000 accuracy vs 0.6750 for $V_{0h}$ and 0.6500 for `LLM-only`, maintaining the same ordinal direction with no ceiling distortion.

---

## 8. Item 7c: Knowledge Base Integrity Audit

An exhaustive audit of `data/mitre/*.json` bundles was conducted to identify any objects with non-standard MITRE IDs (e.g. `S9000`-series) and determine their provenance and influence.

### Integrity Audit Findings
- **Identified Objects**: Exactly **62 non-standard objects** were detected (IDs `S9000` through `S9067`).
- **Object Types**: 53 malware objects and 9 tool objects (e.g., `S9001` *SystemBC*, `S9015` *BRICKSTORM*, `S9029` *IronWind*).
- **Provenance**: Created between December 2025 and October 2026; bundled in `data/mitre/enterprise-attack.json` and `mobile-attack.json`.
- **Relationship Links**: 40 of the 62 objects possess valid STIX `uses` relationship links to threat groups (`software_to_groups`).
- **Usage in Prompt Retrieval Contexts**: **0 across all queries and all benchmark arms**. No non-standard object was ever retrieved into a prompt context.
- **Occurrence in Surface Entity Detection**: Detected exactly once in Query 6 (`SystemBC` matched `S9001`).
  - Voted candidate groups: `FIN7` (G0046), `Fox Kitten` (G0117), `Wizard Spider` (G0102).
  - Outcome: None of these groups entered the prompt context, and the model attributed the query to the true ground truth (*Storm-1811*).
- **Conclusion**: The presence of `S9000`-series extended objects in the STIX bundles did not compromise benchmark integrity, prompt construction, or attribution outcomes.

---

## 9. Item 7d: Entity Detector Precision Audit

An audit of 100 randomly sampled detector matches was conducted against `results/phase_4b/detector_labels.csv` (`annotator = claude_draft_unverified`).

### Quantitative Precision Metrics ($N=100$)

| Detector Variant | Sample Matches | Real Entity Mentions | Precision (Real Entity) | Informative for Attribution | Precision (Informative) | False Positives |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **D0 Detector (Surface String Matching)** | 100 | 74 | **74.0%** (74/100) | 63 | **63.0%** (63/100) | 26 |
| **D1 / V1h Filtered Detector** | 65 (survived) | 50 | **76.9%** (50/65) | 50 | **76.9%** (50/65) | 15 |

### Breakdown of False Positive Error Sources ($N=26$)
The 26 false positive matches in D0 fall into three distinct structural categories:
1. **Instruction Template Examples ($N=11$, 42.3% of FPs)**:
   - Matches triggered on illustrative examples within prompt instructions (e.g., *"Map it to relevant MITRE ATT&CK threat groups (e.g., APT36) or Software/Tools (e.g., Crimson RAT - S0334)"*).
   - Sample IDs: 7, 25, 29, 40, 59, 60, 66, 71, 72, 84, 92.
2. **Common Words and Homonyms ($N=7$, 26.9% of FPs)**:
   - Surface string collisions with general software terms or file extensions (e.g., *"Equation 3.0"* OLE object matching group *Equation*; Windows *"Photo"* app matching *Derusbi*; *".ps1"* extension matching *PS1* malware; *"Soldier"* implant matching *SysUpdate*).
   - Sample IDs: 1, 14, 16, 24, 35, 82, 91.
3. **Generic Operating System Utilities ($N=8$, 30.8% of FPs)**:
   - Legitimate system administration commands discussed in reports as attacker activity or defense evasion (e.g., `cmd.exe`, `net.exe`, `ping`, `schtasks.exe`, `ipconfig`, `netstat`, `ftp`, `systeminfo`).
   - Sample IDs: 10, 17, 27, 32, 55, 74, 93, 95, 96, 99.

---

## 10. Summary of Generated Phase 6F Artifacts

| Artifact Path | Format | Description |
| :--- | :---: | :--- |
| `results/phase_4b/detector_labels.csv` | CSV | 100 annotated entity detector matches with binary flags and error sources. |
| `results/phase_6d/holm_primary_generation.json` | JSON | Corrected primary generation Holm step-down table with exact sign test $p$-values. |
| `results/phase_6d/holm_primary_generation.csv` | CSV | Tabular format of corrected Holm table. |
| `results/phase_6d/hygiene_summary_table.json` | JSON | Unified 4-regime hygiene summary table regenerated from source CSVs. |
| `results/phase_6d/hygiene_summary_table.csv` | CSV | Tabular format of unified hygiene summary table. |
| `results/phase_6d/metadata_credit_audit.json` | JSON | Recall@B comparison under metadata credit vs text-visible matching. |
| `results/phase_6d/metadata_credit_audit.csv` | CSV | Tabular format of metadata-credit audit. |
| `results/phase_6d/vrel_noise_strata_ledger.csv` | CSV | Query-level 50-row ledger classifying Active vs Inactive noise strata. |
| `results/phase_6d/vrel_noise_floor_stratification.json` | JSON | Summary statistics of Active vs Inactive strata and lexical variation. |
| `results/phase_6d/case_studies_aggregate_stats.json` | JSON | 50-query aggregate stats (votes, top-3, context, WTL splits, stoplist). |
| `results/phase_6d/gt_alias_leakage_audit.json` | JSON | Complete audit of GT alias leakage in threat reports and clean rescoring. |
| `results/phase_6d/gt_alias_leakage_audit.csv` | CSV | Query-level leakage ledger for all 50 queries. |
| `results/phase_6d/kb_integrity_audit.json` | JSON | Full audit of 62 non-standard `S9000`-series objects in STIX bundles. |
| `results/phase_6d/detector_precision_audit.json` | JSON | Precision metrics and false positive breakdown for D0 and D1/V1h detectors. |
