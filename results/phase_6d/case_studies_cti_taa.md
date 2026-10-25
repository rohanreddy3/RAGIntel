# Phase 6D: Deterministic Case Studies on Threat Actor Attribution (`cti-taa`)

Selection rule: First 5 rows where Vrel wins over V0h, and first 3 rows where Vrel loses.
All detected entity spans asserted to exist verbatim within query text.

### WIN (Vrel > V0h): Row 0 (8b8e568edda9)
- **Ground Truth Threat Group**: `SideCopy`
- **Detected Software in Query**: Action RAT (canonical: Action RAT), Action RAT (canonical: Action RAT), Action RAT (canonical: Action RAT), Raindrop (canonical: Raindrop), Crimson (canonical: Crimson)
- **Top-3 Voted Groups (via STIX uses relationships)**: SideCopy (G1008, score: 3.0), APT29 (G0016, score: 1.0), Transparent Tribe (G0134, score: 1.0)
- **Ground-Truth Group Profile in Context**: `True`
- **Vrel Output**: Based on the provided threat report and MITRE ATT&CK framework, the incident and threat actor can be attributed as follows:

* **Threat Group / APT:** **SideCopy** (associated as a sub-division of **Transparent Tribe** / **APT36** / **G1008**)
* **Software / Tools:** 
  * **AllaKore RAT**
  * **Ares RAT**
  * **Crimson RAT**
  * **Poseidon**
- **V0h Output**: Based on the provided threat report and MITRE ATT&CK framework, the incident and threat group can be mapped as follows:

*   **Threat Actor Group:** **Transparent Tribe** (also known as **APT36**, associated with aliases such as **Operation Transparent Tribe** or **Mythic Leopard**).
*   **Software / Tools:** 
    *   **Crimson RAT** (S0334)
    *   **Ares RAT**
    *   **AllaKore RAT**
    *   **Action RAT**
    *   **Capra RAT**
    *   **Oblique RAT**
- **Scorer Match**: Vrel exact=1, alias=1 vs V0h exact=0, alias=0

### WIN (Vrel > V0h): Row 8 (92723fd96f20)
- **Ground Truth Threat Group**: `APT-C-36, also known as Blind Eagle`
- **Detected Software in Query**: QuasarRAT (canonical: QuasarRAT), QuasarRAT (canonical: QuasarRAT), QuasarRAT (canonical: QuasarRAT)
- **Top-3 Voted Groups (via STIX uses relationships)**: APT-C-36 (G0099, score: 0.4286), Gorgon Group (G0078, score: 0.4286), Kimsuky (G0094, score: 0.4286)
- **Ground-Truth Group Profile in Context**: `False`
- **Vrel Output**: Based on the provided threat report details—specifically the targeting of government institutions and financial/banking entities in Colombia and Latin America (such as Bancolombia, Davivienda, and the Colombian Ministry of Foreign Affairs), the use of Spanish-language artifacts, custom modifications to QuasarRAT, and the attribution context from the MITRE ATT&CK reference data—the incident can be attributed to the following threat actor:

* **Threat Actor Group:** **APT-C-36** (also known in public threat intelligence reporting as **BlindEagle**)
* **Associated Software/Tools:** **QuasarRAT** / **Meterpreter**
- **V0h Output**: Based on the provided threat report, the incident can be attributed to the following known software and toolset used by the threat actors:

* **Software/Tools:** 
  * **QuasarRAT** (modified open-source remote access trojan used in the initial campaign targeting Colombian financial entities).
  * **Meterpreter** (delivered via Python scripts in subsequent campaigns targeting Ecuador).

*(Note: The threat report specifically redacts the threat actor group name using `[PLACEHOLDER]`, focusing heavily on the customization and deployment of QuasarRAT and Meterpreter by Spanish-speaking financially motivated actors targeting Latin America.)*
- **Scorer Match**: Vrel exact=1, alias=1 vs V0h exact=0, alias=0

### WIN (Vrel > V0h): Row 22 (337b6a14a4b4)
- **Ground Truth Threat Group**: `Mint Sandstorm (PHOSPHORUS)`
- **Detected Software in Query**: None detected
- **Top-3 Voted Groups (via STIX uses relationships)**: None
- **Ground-Truth Group Profile in Context**: `False`
- **Vrel Output**: Based on the threat report provided, the activity can be attributed to the following threat actor group and associated identifiers:

* **Threat Group:** **APT35** (also known as **Charming Kitten**, **Phosphorus**, or **Mint Sandstorm**)
* **MITRE ATT&CK Group ID:** [G0058](https://attack.mitre.org/groups/G0058) (Charming Kitten)
- **V0h Output**: Based on the provided threat report and context, the incident can be attributed to the following threat group:

* **MITRE ATT&CK Threat Group:** **APT35** (also known as **Charming Kitten** or **Phosphorus**, which overlap with the placeholders and are explicitly mentioned in the text as being tracked by other researchers). 

*(Note: While the primary group is APT35/Charming Kitten, the report also references specific custom malware tools associated with them, such as **MediaPl** and **MischiefTut**).*
- **Scorer Match**: Vrel exact=1, alias=1 vs V0h exact=0, alias=1

### WIN (Vrel > V0h): Row 24 (a1d56b2578c3)
- **Ground Truth Threat Group**: `Seedworm (or Muddywater)`
- **Detected Software in Query**: schtasks.exe (canonical: schtasks), Impacket (canonical: Impacket), cmd.exe (canonical: cmd)
- **Top-3 Voted Groups (via STIX uses relationships)**: BRONZE BUTLER (G0060, score: 0.5), Kimsuky (G0094, score: 0.3333), APT3 (G0022, score: 0.3333)
- **Ground-Truth Group Profile in Context**: `False`
- **Vrel Output**: Based on the provided threat report and context, the incident is attributed to the following threat actor group:

* **Threat Actor Group:** [MuddyWater](https://attack.mitre.org/groups/G0069) (also known as MERCURY, Seedworm, or Static Kitten)

**Attribution Details:**
* **Associated Organization:** Iran’s Ministry of Intelligence and Security (MOIS).
* **Tools and Infrastructure:** The report explicitly mentions tools and infrastructure heavily tied to this group, such as the **MuddyC2Go** framework (which replaced PhonyC2), **SimpleHelp**, **Venom Proxy**, **Revsocks**, and the use of legitimate utilities like AnyDesk for remote access and persistence.
- **V0h Output**: Based on the provided threat report and context, the incident is attributed to the following threat group:

* **Threat Group:** [MuddyWater](https://attack.mitre.org/groups/G0069) (also associated with Iran's Ministry of Intelligence and Security - MOIS)

### Mapping to MITRE ATT&CK:
* **Threat Group:** MuddyWater ([G0069](https://attack.mitre.org/groups/G0069))
- **Scorer Match**: Vrel exact=1, alias=1 vs V0h exact=0, alias=1

### WIN (Vrel > V0h): Row 41 (7172731bb34b)
- **Ground Truth Threat Group**: `APT29 (aka Cozy Bear, Nobelium and many other monikers)`
- **Detected Software in Query**: None detected
- **Top-3 Voted Groups (via STIX uses relationships)**: None
- **Ground-Truth Group Profile in Context**: `False`
- **Vrel Output**: Based on the provided context and threat report details (specifically the attribution by Ukrainian authorities to Russian intelligence services—referencing the SVR—and the specific mention of exploiting CVE-2023-3883 in conjunction with Russian APT activity typically associated with diplomatic targeting), the threat actor group described in the report corresponds to:

* **Threat Group:** [APT29](https://attack.mitre.org/groups/G0016) (also known as Cozy Bear / Midnight Blizzard, associated with Russia's SVR). 

*(Note: While APT29 is the widely recognized MITRE ATT&CK group matching these specific SVR-linked diplomatic targeting campaigns exploiting CVE-2023-3883, if strictly limiting choices to the provided text snippet's groups—such as Turla, Gamaredon, RedCurl, Saint Bear, CopyKittens, or Naikon—Turla is attributed to Russia's FSB, whereas the report specifically highlights the SVR and CVE-2023-3883 vectors commonly tracked under APT29/Cozy Bear).*
- **V0h Output**: Based on the threat report and the provided context, the campaign and vulnerability exploitation details point to the Russian cyber espionage group **Turla** (associated with MITRE ATT&CK Group ID **G0010**, which has ties to Russia's FSB/intelligence apparatus and has a history of targeting diplomatic entities and leveraging spear-phishing campaigns). 

Additionally, the specific mention of exploiting CVE-2023-3883 in connection with a Russian APT group targeting diplomats aligns with known threat intelligence attributing these specific WinRAR exploit campaigns to **Turla**.

* **Threat Actor Group:** Turla ([G0010](https://attack.mitre.org/groups/G0010))
- **Scorer Match**: Vrel exact=1, alias=1 vs V0h exact=0, alias=0

### LOSS (Vrel < V0h): Row 20 (bd007da00d41)
- **Ground Truth Threat Group**: `Kimsuky`
- **Detected Software in Query**: cmd.exe (canonical: cmd)
- **Top-3 Voted Groups (via STIX uses relationships)**: Orangeworm (G0071, score: 0.1667), APT18 (G0026, score: 0.1667), BRONZE BUTLER (G0060, score: 0.1667)
- **Ground-Truth Group Profile in Context**: `False`
- **Vrel Output**: Based on the threat report provided, the campaign features techniques, tools (such as TutRAT / C# R.A.T.), and targeting characteristics (South Korean victims, HWP document references, and specific script-based attack chains) historically associated with North Korean threat actors. 

However, looking specifically at the malware tools and tactics mentioned (such as the use of **TutRAT** / **C# R.A.T.** against Korean targets), this aligns with known activity attributed to the threat group **Dark Pink** (or related operations targeting the region). 

### Attribution Summary:
* **Threat Group:** Dark Pink (or North Korea-affiliated actors targeting South Korea)
* **Software/Tools:** TutRAT / C# R.A.T. (associated with open-source remote access trojans utilized in these campaigns)
- **V0h Output**: Based on the threat report provided, the campaign and associated tactics align closely with known activities attributed to North Korea-linked threat groups and specific malware frameworks. 

### Attribution and Mapping:

* **Threat Group:** **Kimsuky** (also tracked under various aliases such as *Thallium* or *APT43*, historically associated with targeting South Korean entities using tailored lures like PDF/document-based shortcut (.lnk) files and multi-stage script execution).
* **Malware/Software:** 
  * **TutRat / TutClient / C# R.A.T.** (identified in Stage 3 as the open-source C# remote access trojan used for full host control, keylogging, and surveillance).
  * **PowerShell / VBScript Stagers** leveraging legitimate cloud services (Dropbox, Google Docs) for command and control (C2) and payload delivery (often associated with custom toolsets used in campaigns like *DEEP#GOSU*).

### MITRE ATT&CK Mapping Summary:
* **T1204.002** - User Execution: Malicious File (.lnk shortcut files)
* **T1102** - Web Service (Dropbox used for C2 and payload staging)
* **T1059.005** - Command and Scripting Interpreter: VBScript
* **T1059.001** - Command and Scripting Interpreter: PowerShell
* **T1047** - Windows Management Instrumentation (WMI)
* **T1053** - Scheduled Task/Job (Persistence)
* **T1082** - System Information Discovery
* **T1041** - Exfiltration Over C2 Channel
* **T1056.001** - Input Capture: Keylogging
- **Scorer Match**: Vrel exact=0, alias=0 vs V0h exact=1, alias=1

### LOSS (Vrel < V0h): Row 26 (b9933f2beb82)
- **Ground Truth Threat Group**: `Mint Sandstorm`
- **Detected Software in Query**: CharmPower (canonical: CharmPower), CharmPower (canonical: CharmPower), CharmPower (canonical: CharmPower), CharmPower (canonical: CharmPower), Impacket (canonical: Impacket), Impacket (canonical: Impacket), Soldier (canonical: SysUpdate), Soldier (canonical: SysUpdate), Soldier (canonical: SysUpdate), Soldier (canonical: SysUpdate), Soldier (canonical: SysUpdate), Soldier (canonical: SysUpdate), Soldier (canonical: SysUpdate)
- **Top-3 Voted Groups (via STIX uses relationships)**: Threat Group-3390 (G0027, score: 7.1111), Magic Hound (G0059, score: 4.1111), Dragonfly (G0035, score: 0.1111)
- **Ground-Truth Group Profile in Context**: `False`
- **Vrel Output**: Based on the provided threat report and context, the threat actor group described is **APT42** (also tracked by Microsoft historically as *PHOSPHORUS* and overlapping with reporting on *APT35*, *Charming Kitten*, and *TA453*).

### Attribution Summary:
* **Threat Group:** APT42 / PHOSPHORUS (associated with MITRE ATT&CK Group **G1044** / APT42)
* **Associated Software/Tools mentioned in report:** 
  * Drokbk
  * Soldier
  * CharmPower
- **V0h Output**: Based on the provided threat report—which details operations by an Iranian nation-state actor historically named *PHOSPHORUS* by Microsoft, associated with the Islamic Revolutionary Guard Corps (IRGC), overlapping with public reporting for *APT35*, *APT42*, *Charming Kitten*, and *TA453*, and known for using custom malware such as *CharmPower*, *Drokbk*, and *Soldier*—the incident maps to the following MITRE ATT&CK threat groups:

### **Threat Actor Attribution**
* **Primary Group:** **APT35** / **TA453** / **Charming Kitten** (often tracked under MITRE as **APT35** or associated Iranian state-sponsored activity).
* **Specific Subgroup / Campaign Context:** **APT42** (the subgroup historically recognized within Mint Sandstorm/Phosphorus for targeted phishing, surveillance, and operations aligned with the IRGC).

### **Associated Software / Tools (Malware)**
* **CharmPower** (PowerShell backdoor)
* **Drokbk** (S0687 / .NET implant)
* **Soldier** (.NET backdoor)
- **Scorer Match**: Vrel exact=0, alias=1 vs V0h exact=1, alias=1

### LOSS (Vrel < V0h): Row 36 (a07eb7d47158)
- **Ground Truth Threat Group**: `Bahamut`
- **Detected Software in Query**: None detected
- **Top-3 Voted Groups (via STIX uses relationships)**: None
- **Ground-Truth Group Profile in Context**: `False`
- **Vrel Output**: Based on the threat report and the provided context, the incident can be attributed to the following MITRE ATT&CK groups and software:

### **Threat Actor Attribution**
* **APT-C-23** (also referenced indirectly through tactics, tradecraft, and historical naming conventions associated with the "Arabian Sea" fish reference/Bellingcat attribution to **DarkCaracal** / **APT-C-23**).

### **Malware / Software Attribution**
* **SpyC23** (Software ID: **S1195**) - The mobile spyware utilized by APT-C-23 targeting Android devices.
- **V0h Output**: Based on the threat report and the provided context, the incident can be attributed to the following MITRE ATT&CK groups and software:

### **Attribution Summary**
* **Threat Group:** **APT-C-23** (also referenced in the report through descriptions matching the Arabic mythology reference "Bahamut", which operates closely with or is documented alongside APT-C-23 infrastructure and mobile campaigns).
* **Software / Malware:** **SpyC23** (Software ID: **S1195**) — the Android mobile spyware utilized by APT-C-23 for espionage and data exfiltration.

### **Mapping Details**
* **Threat Group:** [APT-C-23](https://attack.mitre.org/groups/G1028)
* **Associated Malware:** [SpyC23](https://attack.mitre.org/software/S1195) (S1195)
- **Scorer Match**: Vrel exact=0, alias=0 vs V0h exact=1, alias=1

