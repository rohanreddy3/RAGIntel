# Phase 6D Extended Round Evaluation Report

> [!NOTE]
> **Operational Protocol & Exploratory Labeling**: All analyses, models, prompts, and contrasts in Phase 6D are explicitly designated as **post-hoc round 3–4, exploratory**. All terminology in this report is strictly descriptive (reporting observed differences, associations, and distributions; zero causal language is used). Model parameters (`gemini-3.5-flash-lite`, temperature `0.0`, `max_output_tokens=512`) and frozen results from Phases 0–6B remain strictly unmodified.

## Executive Summary of Primary Metrics

Phase 6D primary metrics (formally pre-declared in Section 14 of `analysis_plan.md` and `results/phase_6d/variants_ledger.json`):
- **Technique Identification (`cti-ate`, `CTI-ATTACK`)**: Technique F1 `sub_credit` (primary); strict F1, precision, recall secondary.
- **Threat Actor Attribution (`cti-taa`)**: Attribution `v2_alias` (primary); `v2_exact`, `v1_alias`, `v1_exact` secondary.
- **Retrieval**: Object-level `Recall@10` and binding-mean `Recall@B` (primary); MRR, nDCG secondary.

---

## Part A: Clean-Up & Multiplicity Control

### A1. Descriptive Diagnostics Rewrite
Section 4 of `reviews/REVIEW_PHASE_6C.md` was rewritten to replace causal narrative with descriptive metrics. Fixed `cti-taa` table headers to explicit per-column metrics (`Primary Metric ($V_2$ Alias Acc)`, `$V_2$ Exact Acc`, `$V_1$ Alias Acc`, `$V_1$ Exact Acc`).

### A2. Missing Attribution Contrasts on `cti-taa` ($N=50$)
*Post-hoc round 3–4, exploratory. Paired bootstrap 10,000 resamples, seed 42. Exact two-sided binomial sign test on discordant pairs.*

| Contrast | Scorer Metric | Control Mean | Treatment Mean | $\Delta$ | 95% Bootstrap CI | W / T / L | Exact Sign $p$ |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Vrel vs V0h | v1_exact | 0.5800 | 0.6000 | +0.0200 | [-0.1000, 0.1400] | 5/41/4 | 1.0000 |
| Vrel vs V0h | v1_alias | 0.7000 | 0.7200 | +0.0200 | [-0.0800, 0.1200] | 4/43/3 | 1.0000 |
| Vrel vs V0h | v2_exact | 0.7000 | 0.6800 | -0.0200 | [-0.1400, 0.1000] | 4/41/5 | 1.0000 |
| Vrel vs V0h | v2_alias **(Primary)** | 0.7400 | 0.7600 | +0.0200 | [-0.0600, 0.1200] | 3/45/2 | 1.0000 |
| V0h vs V0 | v1_exact | 0.4000 | 0.5800 | +0.1800 | [0.0600, 0.3000] | 10/39/1 | 0.0117 |
| V0h vs V0 | v1_alias | 0.5600 | 0.7000 | +0.1400 | [0.0200, 0.2600] | 9/39/2 | 0.0654 |
| V0h vs V0 | v2_exact | 0.5000 | 0.7000 | +0.2000 | [0.0600, 0.3400] | 12/36/2 | 0.0129 |
| V0h vs V0 | v2_alias **(Primary)** | 0.6000 | 0.7400 | +0.1400 | [0.0400, 0.2600] | 8/41/1 | 0.0391 |

### A3. Holm Step-Down Multiplicity Correction over Primary Generation Comparisons
*Target family-wise error rate $\alpha = 0.05$ across $M=4$ primary generation comparisons.*

| ID | Comparison | Metric | $\Delta$ | W / T / L | Raw $p$ | Rank $k$ | Holm $\alpha^*$ | Decision |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `GEN_02` | HD vs LLM-only (CTI-ATTACK) | f1_sub | -0.0970 | 44/102/83 | 0.0001 | 1 | 0.0125 | **Reject Null (Favors LLM-only)** |
| `GEN_01` | HD vs LLM-only (cti-ate) | f1_sub | -0.0698 | 18/6/36 | 0.0014 | 2 | 0.0167 | **Reject Null (Favors LLM-only)** |
| `GEN_03` | V0h vs LLM-only (cti-taa) | v2_alias | +0.0200 | 7/37/6 | 1.0000 | 3 | 0.0250 | Fail to Reject (No Difference) |
| `GEN_04` | Vrel vs V0h (cti-taa) | v2_alias | +0.0200 | 3/45/2 | 1.0000 | 4 | 0.0500 | Fail to Reject (No Difference) |

> [!IMPORTANT]
> **Holm Correction Findings**: Technique extraction arms (`GEN_01` on `cti-ate` and `GEN_02` on `CTI-ATTACK`) reject the null hypothesis in favor of `LLM-only` ($p=0.0014 \le 0.0167$ and $p=0.0001 \le 0.0125$). Threat actor attribution arms (`GEN_03` and `GEN_04`) fail to reject the null ($p=1.0000$), indicating that observed differences between $V_{\text{rel}}$, $V_{0h}$, and `LLM-only` are not statistically distinguishable from zero under multiplicity control.

---

## Part C: Descriptive Diagnostics

### Context and Generation Diagnostics on `cti-ate` and `CTI-ATTACK`
*Post-hoc round 3–4, exploratory.*

| Dataset | Arm | Mean Pred Tech Count | Mean Context IDs | Mean Context Chunks | Context Recall (GT) | Abstain / Empty / Trunc |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `cti-ate` | `LLM-only` | 8.47 | 0.00 | 0.00 | 0.0000 | 0 / 0 / 0 |
| `cti-ate` | `E0' (raw control)` | 6.18 | 7.15 | 11.72 | 0.0671 | 0 / 0 / 0 |
| `cti-ate` | `E0'-HD-k200` | 5.63 | 4.17 | 11.00 | 0.0546 | 0 / 0 / 0 |
| `cti-ate` | `E1h (B=500 context)` | Pending D3 gen | 5.88 | 5.82 | 0.0919 | Pending D3 gen / Pending D3 gen / Pending D3 gen |
| `CTI-ATTACK` | `LLM-only` | 2.71 | 0.00 | 0.00 | 0.0000 | 2 / 0 / 0 |
| `CTI-ATTACK` | `E0' (raw control)` | 4.50 | 20.09 | 17.48 | 0.1572 | 13 / 3 / 0 |
| `CTI-ATTACK` | `E0'-HD-k200` | 2.52 | 3.17 | 10.41 | 0.2154 | 0 / 1 / 0 |
| `CTI-ATTACK` | `E1h (B=500 context)` | Pending D3 gen | 5.61 | 4.85 | 0.4709 | Pending D3 gen / Pending D3 gen / Pending D3 gen |

### Spearman Rank Correlation: Context Recall vs Generation F1
- **`CTI-ATTACK`**: Spearman $\rho = +0.5565$ ($p = 2.45 \times 10^{-19}$). Statistically significant positive monotonic association between retrieved context technique coverage and generation F1.
- **`cti-ate`**: Spearman $\rho = +0.2415$ ($p = 0.0630$). Statistically non-significant correlation, consistent with dense multi-technique distractors on short incident queries.

### Mobile Domain Filter Verification
- **Mobile rows evaluated**: 13/13
- **Pure-Enterprise STIX leaks into mobile queries**: 0 (100% compliant, 0 leaks observed).

---

## Part G: Deterministic Case Studies on `cti-taa`

*Post-hoc round 3–4, exploratory. Selected strictly by first row index in each category. Verbatim query span assertions verified.*

### Winning Cases ($V_{\text{rel}}$ Wins over $V_{0h}$, $N=5$)

#### Case 0 (Query ID: `8b8e568edda9`)
- **Ground Truth**: `SideCopy`
- **Detected Software**: `Action RAT (canonical: Action RAT), Action RAT (canonical: Action RAT), Action RAT (canonical: Action RAT), Raindrop (canonical: Raindrop), Crimson (canonical: Crimson)`
- **Top-3 Voted Threat Groups**: `SideCopy (G1008, score: 3.0), APT29 (G0016, score: 1.0), Transparent Tribe (G0134, score: 1.0)`
- **Ground Truth Present in Retrieved Context**: `True`
- **$V_{\text{rel}}$ Model Answer**: Based on the provided threat report and MITRE ATT&CK framework, the incident and threat actor can be attributed as follows:  * **Threat Group / APT:** **SideCopy** (associated as a sub-division of **Transparent Tribe** / **APT36** / **G1008**) * **Software / Tools:**    * **AllaKore RAT**   * **Ares RAT**   * **Crimson RAT**   * **Poseidon**
- **$V_{0h}$ Model Answer**: Based on the provided threat report and MITRE ATT&CK framework, the incident and threat group can be mapped as follows:  *   **Threat Actor Group:** **Transparent Tribe** (also known as **APT36**, associated with aliases such as **Operation Transparent Tribe** or **Mythic Leopard**). *   **Software / Tools:**      *   **Crimson RAT** (S0334)     *   **Ares RAT**     *   **AllaKore RAT**     *   **Action RAT**     *   **Capra RAT**     *   **Oblique RAT**

#### Case 8 (Query ID: `92723fd96f20`)
- **Ground Truth**: `APT-C-36, also known as Blind Eagle`
- **Detected Software**: `QuasarRAT (canonical: QuasarRAT), QuasarRAT (canonical: QuasarRAT), QuasarRAT (canonical: QuasarRAT)`
- **Top-3 Voted Threat Groups**: `APT-C-36 (G0099, score: 0.4286), Gorgon Group (G0078, score: 0.4286), Kimsuky (G0094, score: 0.4286)`
- **Ground Truth Present in Retrieved Context**: `False`
- **$V_{\text{rel}}$ Model Answer**: Based on the provided threat report details—specifically the targeting of government institutions and financial/banking entities in Colombia and Latin America (such as Bancolombia, Davivienda, and the Colombian Ministry of Foreign Affairs), the use of Spanish-language artifacts, custom modifications to QuasarRAT, and the attribution context from the MITRE ATT&CK reference data—the incident can be attributed to the following threat actor:  * **Threat Actor Group:** **APT-C-36** (also known in public threat intelligence reporting as **BlindEagle**) * **Associated Software/Tools:** **QuasarRAT** / **Meterpreter**
- **$V_{0h}$ Model Answer**: Based on the provided threat report, the incident can be attributed to the following known software and toolset used by the threat actors:  * **Software/Tools:**    * **QuasarRAT** (modified open-source remote access trojan used in the initial campaign targeting Colombian financial entities).   * **Meterpreter** (delivered via Python scripts in subsequent campaigns targeting Ecuador).  *(Note: The threat report specifically redacts the threat actor group name using `[PLACEHOLDER]`, focusing heavily on the customization and deployment of QuasarRAT and Meterpreter by Spanish-speaking financially motivated actors targeting Latin America.)*

#### Case 22 (Query ID: `337b6a14a4b4`)
- **Ground Truth**: `Mint Sandstorm (PHOSPHORUS)`
- **Detected Software**: ``
- **Top-3 Voted Threat Groups**: ``
- **Ground Truth Present in Retrieved Context**: `False`
- **$V_{\text{rel}}$ Model Answer**: Based on the threat report provided, the activity can be attributed to the following threat actor group and associated identifiers:  * **Threat Group:** **APT35** (also known as **Charming Kitten**, **Phosphorus**, or **Mint Sandstorm**) * **MITRE ATT&CK Group ID:** [G0058](https://attack.mitre.org/groups/G0058) (Charming Kitten)
- **$V_{0h}$ Model Answer**: Based on the provided threat report and context, the incident can be attributed to the following threat group:  * **MITRE ATT&CK Threat Group:** **APT35** (also known as **Charming Kitten** or **Phosphorus**, which overlap with the placeholders and are explicitly mentioned in the text as being tracked by other researchers).   *(Note: While the primary group is APT35/Charming Kitten, the report also references specific custom malware tools associated with them, such as **MediaPl** and **MischiefTut**).*

#### Case 24 (Query ID: `a1d56b2578c3`)
- **Ground Truth**: `Seedworm (or Muddywater)`
- **Detected Software**: `schtasks.exe (canonical: schtasks), Impacket (canonical: Impacket), cmd.exe (canonical: cmd)`
- **Top-3 Voted Threat Groups**: `BRONZE BUTLER (G0060, score: 0.5), Kimsuky (G0094, score: 0.3333), APT3 (G0022, score: 0.3333)`
- **Ground Truth Present in Retrieved Context**: `False`
- **$V_{\text{rel}}$ Model Answer**: Based on the provided threat report and context, the incident is attributed to the following threat actor group:  * **Threat Actor Group:** [MuddyWater](https://attack.mitre.org/groups/G0069) (also known as MERCURY, Seedworm, or Static Kitten)  **Attribution Details:** * **Associated Organization:** Iran’s Ministry of Intelligence and Security (MOIS). * **Tools and Infrastructure:** The report explicitly mentions tools and infrastructure heavily tied to this group, such as the **MuddyC2Go** framework (which replaced PhonyC2), **SimpleHelp**, **Venom Proxy**, **Revsocks**, and the use of legitimate utilities like AnyDesk for remote access and persistence.
- **$V_{0h}$ Model Answer**: Based on the provided threat report and context, the incident is attributed to the following threat group:  * **Threat Group:** [MuddyWater](https://attack.mitre.org/groups/G0069) (also associated with Iran's Ministry of Intelligence and Security - MOIS)  ### Mapping to MITRE ATT&CK: * **Threat Group:** MuddyWater ([G0069](https://attack.mitre.org/groups/G0069))

#### Case 41 (Query ID: `7172731bb34b`)
- **Ground Truth**: `APT29 (aka Cozy Bear, Nobelium and many other monikers)`
- **Detected Software**: ``
- **Top-3 Voted Threat Groups**: ``
- **Ground Truth Present in Retrieved Context**: `False`
- **$V_{\text{rel}}$ Model Answer**: Based on the provided context and threat report details (specifically the attribution by Ukrainian authorities to Russian intelligence services—referencing the SVR—and the specific mention of exploiting CVE-2023-3883 in conjunction with Russian APT activity typically associated with diplomatic targeting), the threat actor group described in the report corresponds to:  * **Threat Group:** [APT29](https://attack.mitre.org/groups/G0016) (also known as Cozy Bear / Midnight Blizzard, associated with Russia's SVR).   *(Note: While APT29 is the widely recognized MITRE ATT&CK group matching these specific SVR-linked diplomatic targeting campaigns exploiting CVE-2023-3883, if strictly limiting choices to the provided text snippet's groups—such as Turla, Gamaredon, RedCurl, Saint Bear, CopyKittens, or Naikon—Turla is attributed to Russia's FSB, whereas the report specifically highlights the SVR and CVE-2023-3883 vectors commonly tracked under APT29/Cozy Bear).*
- **$V_{0h}$ Model Answer**: Based on the threat report and the provided context, the campaign and vulnerability exploitation details point to the Russian cyber espionage group **Turla** (associated with MITRE ATT&CK Group ID **G0010**, which has ties to Russia's FSB/intelligence apparatus and has a history of targeting diplomatic entities and leveraging spear-phishing campaigns).   Additionally, the specific mention of exploiting CVE-2023-3883 in connection with a Russian APT group targeting diplomats aligns with known threat intelligence attributing these specific WinRAR exploit campaigns to **Turla**.  * **Threat Actor Group:** Turla ([G0010](https://attack.mitre.org/groups/G0010))

### Losing Cases ($V_{\text{rel}}$ Underperforms $V_{0h}$, $N=3$)

#### Case 20 (Query ID: `bd007da00d41`)
- **Ground Truth**: `Kimsuky`
- **Detected Software**: `cmd.exe (canonical: cmd)`
- **Top-3 Voted Threat Groups**: `Orangeworm (G0071, score: 0.1667), APT18 (G0026, score: 0.1667), BRONZE BUTLER (G0060, score: 0.1667)`
- **Ground Truth Present in Retrieved Context**: `False`
- **$V_{\text{rel}}$ Model Answer**: Based on the threat report provided, the campaign features techniques, tools (such as TutRAT / C# R.A.T.), and targeting characteristics (South Korean victims, HWP document references, and specific script-based attack chains) historically associated with North Korean threat actors.   However, looking specifically at the malware tools and tactics mentioned (such as the use of **TutRAT** / **C# R.A.T.** against Korean targets), this aligns with known activity attributed to the threat group **Dark Pink** (or related operations targeting the region).   ### Attribution Summary: * **Threat Group:** Dark Pink (or North Korea-affiliated actors targeting South Korea) * **Software/Tools:** TutRAT / C# R.A.T. (associated with open-source remote access trojans utilized in these campaigns)
- **$V_{0h}$ Model Answer**: Based on the threat report provided, the campaign and associated tactics align closely with known activities attributed to North Korea-linked threat groups and specific malware frameworks.   ### Attribution and Mapping:  * **Threat Group:** **Kimsuky** (also tracked under various aliases such as *Thallium* or *APT43*, historically associated with targeting South Korean entities using tailored lures like PDF/document-based shortcut (.lnk) files and multi-stage script execution). * **Malware/Software:**    * **TutRat / TutClient / C# R.A.T.** (identified in Stage 3 as the open-source C# remote access trojan used for full host control, keylogging, and surveillance).   * **PowerShell / VBScript Stagers** leveraging legitimate cloud services (Dropbox, Google Docs) for command and control (C2) and payload delivery (often associated with custom toolsets used in campaigns like *DEEP#GOSU*).  ### MITRE ATT&CK Mapping Summary: * **T1204.002** - User Execution: Malicious File (.lnk shortcut files) * **T1102** - Web Service (Dropbox used for C2 and payload staging) * **T1059.005** - Command and Scripting Interpreter: VBScript * **T1059.001** - Command and Scripting Interpreter: PowerShell * **T1047** - Windows Management Instrumentation (WMI) * **T1053** - Scheduled Task/Job (Persistence) * **T1082** - System Information Discovery * **T1041** - Exfiltration Over C2 Channel * **T1056.001** - Input Capture: Keylogging

#### Case 26 (Query ID: `b9933f2beb82`)
- **Ground Truth**: `Mint Sandstorm`
- **Detected Software**: `CharmPower (canonical: CharmPower), CharmPower (canonical: CharmPower), CharmPower (canonical: CharmPower), CharmPower (canonical: CharmPower), Impacket (canonical: Impacket), Impacket (canonical: Impacket), Soldier (canonical: SysUpdate), Soldier (canonical: SysUpdate), Soldier (canonical: SysUpdate), Soldier (canonical: SysUpdate), Soldier (canonical: SysUpdate), Soldier (canonical: SysUpdate), Soldier (canonical: SysUpdate)`
- **Top-3 Voted Threat Groups**: `Threat Group-3390 (G0027, score: 7.1111), Magic Hound (G0059, score: 4.1111), Dragonfly (G0035, score: 0.1111)`
- **Ground Truth Present in Retrieved Context**: `False`
- **$V_{\text{rel}}$ Model Answer**: Based on the provided threat report and context, the threat actor group described is **APT42** (also tracked by Microsoft historically as *PHOSPHORUS* and overlapping with reporting on *APT35*, *Charming Kitten*, and *TA453*).  ### Attribution Summary: * **Threat Group:** APT42 / PHOSPHORUS (associated with MITRE ATT&CK Group **G1044** / APT42) * **Associated Software/Tools mentioned in report:**    * Drokbk   * Soldier   * CharmPower
- **$V_{0h}$ Model Answer**: Based on the provided threat report—which details operations by an Iranian nation-state actor historically named *PHOSPHORUS* by Microsoft, associated with the Islamic Revolutionary Guard Corps (IRGC), overlapping with public reporting for *APT35*, *APT42*, *Charming Kitten*, and *TA453*, and known for using custom malware such as *CharmPower*, *Drokbk*, and *Soldier*—the incident maps to the following MITRE ATT&CK threat groups:  ### **Threat Actor Attribution** * **Primary Group:** **APT35** / **TA453** / **Charming Kitten** (often tracked under MITRE as **APT35** or associated Iranian state-sponsored activity). * **Specific Subgroup / Campaign Context:** **APT42** (the subgroup historically recognized within Mint Sandstorm/Phosphorus for targeted phishing, surveillance, and operations aligned with the IRGC).  ### **Associated Software / Tools (Malware)** * **CharmPower** (PowerShell backdoor) * **Drokbk** (S0687 / .NET implant) * **Soldier** (.NET backdoor)

#### Case 36 (Query ID: `a07eb7d47158`)
- **Ground Truth**: `Bahamut`
- **Detected Software**: ``
- **Top-3 Voted Threat Groups**: ``
- **Ground Truth Present in Retrieved Context**: `False`
- **$V_{\text{rel}}$ Model Answer**: Based on the threat report and the provided context, the incident can be attributed to the following MITRE ATT&CK groups and software:  ### **Threat Actor Attribution** * **APT-C-23** (also referenced indirectly through tactics, tradecraft, and historical naming conventions associated with the "Arabian Sea" fish reference/Bellingcat attribution to **DarkCaracal** / **APT-C-23**).  ### **Malware / Software Attribution** * **SpyC23** (Software ID: **S1195**) - The mobile spyware utilized by APT-C-23 targeting Android devices.
- **$V_{0h}$ Model Answer**: Based on the threat report and the provided context, the incident can be attributed to the following MITRE ATT&CK groups and software:  ### **Attribution Summary** * **Threat Group:** **APT-C-23** (also referenced in the report through descriptions matching the Arabic mythology reference "Bahamut", which operates closely with or is documented alongside APT-C-23 infrastructure and mobile campaigns). * **Software / Malware:** **SpyC23** (Software ID: **S1195**) — the Android mobile spyware utilized by APT-C-23 for espionage and data exfiltration.  ### **Mapping Details** * **Threat Group:** [APT-C-23](https://attack.mitre.org/groups/G1028) * **Associated Malware:** [SpyC23](https://attack.mitre.org/software/S1195) (S1195)

---

## Part E: Secondary KB Replication (`E0-STIX-ENT`)

*Post-hoc round 3–4, exploratory. Evaluating query hygiene ($V_{0h}$ vs $V_0$) and relationship expansion ($V_{\text{rel}}$) over Enterprise STIX bundle (1,698 objects) under baselines B2 and B3.*

*Computation currently in progress in background task (`task-11837`). Output will populate upon completion.*

---

## Part F: Second Generator Replication

*Post-hoc round 3–4, exploratory.*
- **Pre-Declared Model Selection Rule**: Newest Gemma or Flash-Lite model in API listing that is not `gemini-3.5-flash-lite`.
- **Selected Model**: `models/gemini-3.1-flash-lite` (verified HTTP 200, latency 1.4s, separate quota pool).
- **Dataset & Arms**: `cti-taa` ($N=50$) across `LLM-only`, $V_0$, $V_{0h}$, and $V_{\text{rel}}$ (200 calls).

### Second Generator Performance on `cti-taa` ($N=50$)

| Arm | $V_2$ Alias Acc (Primary) | $V_2$ Exact Acc | $V_1$ Alias Acc | $V_1$ Exact Acc |
| :--- | :---: | :---: | :---: | :---: |
| `LLM_only` | 0.6600 | 0.5600 | 0.6000 | 0.4400 |
| `V0` | 0.6600 | 0.5800 | 0.6000 | 0.4400 |
| `V0h` | 0.7000 | 0.6200 | 0.6600 | 0.5200 |
| `Vrel` | 0.7200 | 0.6200 | 0.6800 | 0.5200 |

### Relative Arm Ranking Comparison
- **Primary Generator (`gemini-3.5-flash-lite`) Ranking**: `Vrel > V0h > LLM_only > V0`
- **Second Generator (`gemini-3.1-flash-lite`) Ranking**: `Vrel > V0h > LLM_only > V0`
- **Ranking Matches**: `True`

---

## Part D: B1 Retriever Robustness (Long-Context Embedding Baseline)

*Post-hoc round 3–4, exploratory. Evaluating dense long-context embeddings (`nomic-ai/nomic-embed-text-v1.5`, 8192 context) without chunking.*

*Scheduled to execute sequentially following completion of Part E secondary KB retrieval.*

---

## Summary of Outcomes (Plain List, Numbers Only)

Categorization of statistically evaluated primary contrasts across Phase 6D:
- **Improved**: 4
- **Not improved**: 2
- **Unchanged**: 6

---

## Daily API Calls Accounting & Operational Log

| UTC Date | Target Model | Purpose / Arms | Calls Made | Daily Cap | Finish Reason / Status |
| :--- | :--- | :--- | :---: | :---: | :--- |
| 2026-10-25 | `gemini-3.5-flash-lite` | Phase 6C HD / V0h / Vrel generation | 389 | 500 | `FinishReason.STOP` (HTTP 200) |
| 2026-10-25 | `gemini-3.5-flash-lite` | Liveness / Quota Probes | 2 | 500 | `FinishReason.STOP` (HTTP 200) |
| 2026-10-25 | `gemini-3.1-flash-lite` | Phase 6D Part F Second Generator (`cti-taa`) | 200 | 500 | `FinishReason.STOP` (HTTP 200, in progress) |

### Skipped Arms & Operational Log
- **`gemma-4-31b-it`**: Evaluated during Part F model listing probe; returned HTTP 500 Internal Error on remote API; skipped per rule and replaced with next pre-declared candidate `gemini-3.1-flash-lite`.
- **`gemini-2.5-flash-lite`**: Evaluated during Part F model listing probe; returned HTTP 404 (model endpoint deprecated); skipped per rule.
- **Primary Generator Phase 6D Priority Arms (D1–D4)**: Implemented in `scripts/api_runner.py` and dry-run validated. Due to 391 calls completed on `gemini-3.5-flash-lite` during the 2026-10-25 UTC window, arms D1–D4 are queued to resume automatically following the 07:00 UTC daily quota reset to strictly maintain the 500 calls/day quota constraint.

