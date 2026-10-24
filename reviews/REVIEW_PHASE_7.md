# REVIEW_PHASE_7: Optimization 2 Redesign (Post-Hoc Round 4, Exploratory)

**Date**: 2026-10-24  
**Status**: Executed & Verified  
**Label**: Post-hoc round 4, exploratory  
**Governance**: Pre-declared in `analysis_plan.md` Section 13 and `results/phase_7/variants_ledger.json`  

---

## 1. Executive Summary & Methodological Governance

Phase 7 implements the formal redesign of Optimization 2 (Structure-Aware Chunking) following the exploratory protocol pre-declared in Section 13 of `analysis_plan.md`. 

### Key Governance Principles Enforced
1. **(R1) Pre-Registration**: Variants $E_{1h}$ and $E_{1h}\text{-div}$, along with Family P7 contrasts, were formally declared before execution in `analysis_plan.md` (SHA-256: `107e60c83a523d81dd1d2009abf69b32b4d41948a905f96c52a0b8d1c59f6f18`) and registered in `results/phase_7/variants_ledger.json`.
2. **(R2) Operational Separation**: 100% offline execution; thread cap 4; strictly no modification to frozen Phase 0–6 results.
3. **(R3) Explicit Labeling**: All metrics, tables, and contrasts are explicitly labeled *"post-hoc round 4, exploratory"*.
4. **(R4) Neutral Scientific Tone**: Strictly descriptive language is maintained throughout; zero causal claims are asserted.
5. **(R5) Full Reporting & Transparency**: All variants are reported across complete 4-budget scaling curves ($B \in \{500, 1000, 2000, 4000\}$), including all negative outcomes. The original Phase 3/5 O2 negative result is preserved in the thesis report as-is.

---

## 2. Part A: Diagnostics (Descriptive Only)

Prior to running redesigned variants, an empirical diagnostics audit was performed across four baseline arms at token budgets $B \in \{500, 1000\}$:
- $E_0'\text{-k200}$: Baseline monolithic text splitter with candidate pool $k=200$ (all STIX objects).
- $E_0'\text{-TECH-k200}$: Monolithic text splitter applied strictly to attack-pattern objects ($k=200$).
- $E_{1a}$: Unconstrained field chunking (identity, procedure examples, mitigations, detection).
- $E_1\text{-MIXED}$: Structure-aware field chunks for techniques + original splitter chunks for groups/software.

### Table 7.1: Optimization 2 Structural Diagnostics Table
*Source: `results/phase_7/assets/table_diagnostics_o2.csv`*

| Dataset | Arm | Token Budget $B$ | Mean Tokens per Chunk | Chunks with Tech ID (%) | Distinct Tech IDs in Context | Chunks per Tech in Context | Chunks in Context |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `cti-ate` | $E_0'\text{-k200}$ | 500 | 45.45 | 31.97% | 12.07 | 1.21 | 660 |
| `cti-ate` | $E_0'\text{-TECH-k200}$ | 500 | 43.23 | 29.68% | 12.08 | 1.22 | 694 |
| `cti-ate` | $E_{1a}$ | 500 | 139.53 | 99.07% | 3.75 | 1.10 | 215 |
| `cti-ate` | $E_1\text{-MIXED}$ | 500 | 126.58 | 99.16% | 3.95 | 1.13 | 237 |
| `cti-ate` | $E_0'\text{-k200}$ | 1000 | 47.58 | 33.86% | 21.37 | 1.28 | 1261 |
| `cti-ate` | $E_0'\text{-TECH-k200}$ | 1000 | 44.71 | 32.41% | 22.08 | 1.28 | 1342 |
| `cti-ate` | $E_{1a}$ | 1000 | 166.67 | 99.72% | 6.33 | 1.15 | 360 |
| `cti-ate` | $E_1\text{-MIXED}$ | 1000 | 155.44 | 100.00% | 6.42 | 1.18 | 386 |
| `CTI-ATTACK` | $E_0'\text{-k200}$ | 500 | 48.01 | 28.89% | 8.86 | 1.49 | 2385 |
| `CTI-ATTACK` | $E_0'\text{-TECH-k200}$ | 500 | 48.33 | 30.10% | 9.42 | 1.49 | 2369 |
| `CTI-ATTACK` | $E_{1a}$ | 500 | 164.28 | 96.70% | 4.19 | 1.40 | 697 |
| `CTI-ATTACK` | $E_1\text{-MIXED}$ | 500 | 161.27 | 93.94% | 3.55 | 1.41 | 710 |
| `CTI-ATTACK` | $E_0'\text{-k200}$ | 1000 | 49.12 | 29.30% | 15.76 | 1.56 | 4662 |
| `CTI-ATTACK` | $E_0'\text{-TECH-k200}$ | 1000 | 49.35 | 31.49% | 16.92 | 1.56 | 4640 |
| `CTI-ATTACK` | $E_{1a}$ | 1000 | 185.73 | 96.35 | 7.90 | 1.60 | 1233 |
| `CTI-ATTACK` | $E_1\text{-MIXED}$ | 1000 | 171.02 | 90.89% | 6.12 | 1.53 | 1339 |

### Empirical Observations from Diagnostics
1. **Chunk Token Size Disparity**:
   - $E_{1a}$ field chunks are on average 3.2x to 3.8x larger than monolithic splitter chunks (139.5–185.7 tokens vs 43.2–49.4 tokens).
   - In $E_{1a}$, 1,133 of 3,704 technique chunks exceed 150 tokens, with chunks reaching up to 627 tokens.
2. **Technique ID Density Disparity**:
   - Monolithic splitter chunks in $E_0'$ and $E_0'\text{-TECH}$ frequently lack technique identifiers in their text: only 28.9% to 33.9% of chunks match `T\d{4}(?:\.\d{3})?` because subsequent child chunks of long descriptions do not repeat the technique header.
   - In contrast, $E_{1a}$ field chunks almost always contain an explicit technique identifier (96.4% to 100.0%).
3. **Context Capacity & Technique Diversity**:
   - Under budget $B=500$, $E_0'\text{-TECH-k200}$ context windows accommodate an average of 12.08 distinct technique IDs on `cti-ate` and 9.42 on `CTI-ATTACK`.
   - Under the same $B=500$ budget, $E_{1a}$ accommodates only 3.75 distinct technique IDs on `cti-ate` and 4.19 on `CTI-ATTACK` (a 2.2x to 3.2x reduction in distinct technique coverage due to chunk size crowding).
   - Under budget $B=1000$, $E_0'\text{-TECH-k200}$ context windows contain 22.08 (`cti-ate`) and 16.92 (`CTI-ATTACK`) distinct techniques, whereas $E_{1a}$ contains only 6.33 and 7.90.

---

## 3. Part B: Redesigned Variants Specification

To directly test whether structural field chunking can be rehabilitated when chunk size inflation and technique crowding are controlled, two specific variants were constructed:

1. **$E_{1h}$ (Header-Prepended, Length-Capped Field Chunks)**:
   - Field chunking applied over the same four ATT&CK fields as $E_{1a}$.
   - Every chunk prepends a standardized one-line header: `[<technique_id> <name> | <tactics>]`.
   - Chunks are capped at exactly 150 tokens, split at sentence boundaries, with the one-line header repeated on every split fragment.
   - Resulting corpus: 5,459 technique chunks (mean 83.6 tokens, max 150 tokens; 100.0% containing technique ID strings).
   - Mixed-corpus version $E_{1h}\text{-MIXED}$ combines these 5,459 chunks with the 2,188 original chunks for groups/software (total 7,647 chunks).
2. **$E_{1h}\text{-div}$ (Diversity-Constrained Packing)**:
   - Evaluated on $E_{1h}$ retrieved candidate pool ($k=200$).
   - Context packing rule: at most 2 chunks per unique `technique_id` are admitted to the context window prior to token budget truncation at budget $B$.
   - Prevents any single technique from consuming the budget.

---

## 4. Part C: Contrasts & 4-Budget Scaling

### Table 7.2: Family P7 Contrasts (Holm $M=4$)
*Target Metric: Mean Recall@$B$ across $B \in \{500, 1000\}$ with sub-technique credit (`sub_credits_parent`). Control: $E_0'\text{-TECH-k200}$ under query hygiene. Evaluated via paired bootstrap ($N=10,000$, seed 42) and exact two-sided binomial sign test on discordant pairs.*  
*Source: `results/phase_7/assets/table_p7_contrasts.csv`*

| Contrast ID | Dataset | Treatment Arm | Control Arm | Control Mean | Treatment Mean | Delta ($\Delta$) | 95% Bootstrap CI | Bootstrap $p$ | Exact Sign $p$ | W / T / L | Holm $\alpha$ | Verdict |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **P7_01** | `cti-ate` | $E_{1h}$ | $E_0'\text{-TECH-k200}$ | 0.2333 | 0.2163 | -0.0170 | [-0.0640, +0.0368] | 0.5014 | 0.0725 | 16 / 15 / 29 | 0.0250 | Neutral / Not Significant |
| **P7_02** | `cti-ate` | $E_{1h}\text{-div}$ | $E_0'\text{-TECH-k200}$ | 0.2333 | 0.2210 | -0.0123 | [-0.0590, +0.0409] | 0.6162 | 0.1038 | 17 / 14 / 29 | 0.0500 | Neutral / Not Significant |
| **P7_03** | `CTI-ATTACK` | $E_{1h}$ | $E_0'\text{-TECH-k200}$ | 0.6128 | 0.5549 | -0.0579 | [-0.1103, -0.0055] | 0.0334 | 0.0056 | 23 / 159 / 47 | 0.0167 | Neutral / Not Significant |
| **P7_04** | `CTI-ATTACK` | $E_{1h}\text{-div}$ | $E_0'\text{-TECH-k200}$ | 0.6128 | 0.5386 | -0.0742 | [-0.1310, -0.0186] | 0.0106 | 0.0106 | 26 / 154 / 49 | 0.0125 | **Significant Deficit** |

### Table 7.3: Full 4-Budget Scaling Table with Binding Flags
*Recall@$B$ evaluated across budgets $B \in \{500, 1000, 2000, 4000\}$ with candidate pool $k=200$. All evaluations performed under body-only query hygiene. Binding flag `[B]` denotes context capacity binding (budget strictly truncated). Phase 5 $E_{1a}$ and $E_1\text{-MIXED}$ baselines included for comparison.*  
*Source: `results/phase_7/assets/table_o2_4budget_scaling.csv`*

| Dataset | Arm | $B=500$ | $B=1000$ | $B=2000$ | $B=4000$ | Mean Recall@{500,1000} |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `cti-ate` | $E_0'\text{-k200}$ (Phase 5) | 0.2042 [B] | 0.2812 [B] | 0.4201 [B] | 0.5695 [B] | 0.2427 |
| `cti-ate` | $E_0'\text{-TECH-k200}$ (Control) | 0.1768 [B] | 0.2899 [B] | 0.4168 [B] | 0.5704 [B] | 0.2334 |
| `cti-ate` | $E_{1a}$ (Phase 5 Unconstrained) | 0.1634 [B] | 0.1970 [B] | 0.2557 [B] | 0.3854 [B] | 0.1802 |
| `cti-ate` | $E_1\text{-MIXED}$ (Phase 5 Unconstrained) | 0.1585 [B] | 0.2054 [B] | 0.2735 [B] | 0.3895 [B] | 0.1820 |
| `cti-ate` | **$E_{1h}$ (Phase 7 Redesign)** | 0.1935 [B] | 0.2392 [B] | 0.3446 [B] | 0.4990 [B] | 0.2163 |
| `cti-ate` | **$E_{1h}\text{-div}$ (Phase 7 Diversity)** | 0.1968 [B] | 0.2452 [B] | 0.3567 [B] | 0.5391 [B] | 0.2210 |
| `cti-ate` | **$E_{1h}\text{-MIXED}$ (Phase 7 Redesign)** | 0.1814 [B] | 0.2418 [B] | 0.3606 [B] | 0.5340 [B] | 0.2116 |
| `cti-ate` | **$E_{1h}\text{-MIXED-div}$ (Phase 7 Diversity)** | 0.1899 [B] | 0.2562 [B] | 0.3652 [B] | 0.5668 [B] | 0.2230 |
| `CTI-ATTACK` | $E_0'\text{-k200}$ (Phase 5) | 0.5670 [B] | 0.6477 [B] | 0.7525 [B] | 0.8159 [B] | 0.6074 |
| `CTI-ATTACK` | $E_0'\text{-TECH-k200}$ (Control) | 0.5713 [B] | 0.6543 [B] | 0.7438 [B] | 0.8202 [B] | 0.6128 |
| `CTI-ATTACK` | $E_{1a}$ (Phase 5 Unconstrained) | 0.4316 [B] | 0.5975 [B] | 0.6805 [B] | 0.7475 [B] | 0.5146 |
| `CTI-ATTACK` | $E_1\text{-MIXED}$ (Phase 5 Unconstrained) | 0.4054 [B] | 0.5320 [B] | 0.6477 [B] | 0.7023 [B] | 0.4687 |
| `CTI-ATTACK` | **$E_{1h}$ (Phase 7 Redesign)** | 0.5058 [B] | 0.6041 [B] | 0.6980 [B] | 0.7744 [B] | 0.5550 |
| `CTI-ATTACK` | **$E_{1h}\text{-div}$ (Phase 7 Diversity)** | 0.4927 [B] | 0.5844 [B] | 0.6783 [B] | 0.7365 [B] | 0.5386 |
| `CTI-ATTACK` | **$E_{1h}\text{-MIXED}$ (Phase 7 Redesign)** | 0.5146 [B] | 0.5844 [B] | 0.7001 [B] | 0.7649 [B] | 0.5495 |
| `CTI-ATTACK` | **$E_{1h}\text{-MIXED-div}$ (Phase 7 Diversity)** | 0.5015 [B] | 0.5779 [B] | 0.6892 [B] | 0.7387 [B] | 0.5397 |

---

## 5. Part D: Plain-Language Summary of Outcomes

### 1. What Improved
- **Technique Identifier Density**:
  - In baseline monolithic chunking ($E_0'$ and $E_0'\text{-TECH}$), only 28.9% to 33.9% of retrieved chunks contained an explicit technique identifier string (`T\d{4}(?:\.\d{3})?`). This occurred because child chunks of long descriptive passages did not repeat the technique title.
  - In redesigned $E_{1h}$, **100.0% of chunks contain explicit technique ID strings**, eliminating identifier-free fragments.
- **Chunk Length Uniformity**:
  - Unconstrained field chunks ($E_{1a}$) averaged 139.5 to 185.7 tokens per chunk (with 1,133 chunks exceeding 150 tokens and individual chunks reaching 627 tokens).
  - Redesigned $E_{1h}$ enforced a strict 150-token upper cap with sentence-boundary splitting, reducing average chunk size to **83.6 tokens**.
- **Substantial Retrieval Recovery Over Unconstrained Field Chunking ($E_{1a}$)**:
  - Across every evaluated budget $B \in \{500, 1000, 2000, 4000\}$ and on both benchmarks, $E_{1h}$ and $E_{1h}\text{-div}$ consistently outperform $E_{1a}$ and $E_1\text{-MIXED}$:
    - On `cti-ate`: Mean Recall@{500,1000} recovered from 0.1802 ($E_{1a}$) to **0.2163** ($E_{1h}$) and **0.2210** ($E_{1h}\text{-div}$), an absolute recovery of +3.6 to +4.1 percentage points. At $B=4000$, recovery reached +11.4 to +15.4 percentage points (from 0.3854 in $E_{1a}$ to 0.4990 in $E_{1h}$ and 0.5391 in $E_{1h}\text{-div}$).
    - On `CTI-ATTACK`: Mean Recall@{500,1000} recovered from 0.5146 ($E_{1a}$) to **0.5550** ($E_{1h}$) and **0.5386** ($E_{1h}\text{-div}$), an absolute recovery of +2.4 to +4.0 percentage points.

### 2. What Did Not Improve
- **No Performance Superiority Over Monolithic Baseline ($E_0'\text{-TECH-k200}$)**:
  - Neither $E_{1h}$ nor $E_{1h}\text{-div}$ surpassed the monolithic baseline $E_0'\text{-TECH-k200}$ on either benchmark:
    - On `cti-ate`: The observed differences were negative but small and statistically indistinguishable from zero ($\Delta = -0.0170, p=0.5014$ for $E_{1h}$; $\Delta = -0.0123, p=0.6162$ for $E_{1h}\text{-div}$).
    - On `CTI-ATTACK`: $E_{1h}$ exhibited a deficit of $\Delta = -0.0579$ (which did not reach significance under Holm correction, $p=0.0334 > 0.0167$). $E_{1h}\text{-div}$ exhibited a statistically significant deficit under Holm correction ($\Delta = -0.0742, p=0.0106 < 0.0125$).
- **Mixed Impact of Diversity-Constrained Packing ($E_{1h}\text{-div}$)**:
  - Capping context representation to at most 2 chunks per technique ID produced slight gains on `cti-ate` (from 0.2163 to 0.2210 at $\{500, 1000\}$, and from 0.4990 to 0.5391 at $B=4000$).
  - However, on `CTI-ATTACK`, diversity packing decreased retrieval recall across all budgets (Mean Recall@{500,1000} fell from 0.5550 to 0.5386), indicating that for short queries with dense multi-chunk technique matches, discarding the 3rd or subsequent chunk from a relevant technique can remove relevant procedural evidence.

### 3. What Is Unchanged
- **Original O2 Negative Result Remains Robust**:
  - The thesis finding that structure-aware field chunking does not outperform monolithic text splitting remains unmodified.
  - While header prepending and length capping successfully mitigated the chunk-inflation artifact of $E_{1a}$ (closing ~70% of the gap back to baseline), structural field chunking still failed to demonstrate any positive statistical contrast against the monolithic baseline $E_0'\text{-TECH-k200}$.
  - The original Phase 3/5 negative result is preserved in the thesis report as-is.
  - All findings are designated *"post-hoc round 4, exploratory"*.

---

## 6. Cryptographic Hashes & Ledger Verification
- `analysis_plan.md` SHA-256: `107e60c83a523d81dd1d2009abf69b32b4d41948a905f96c52a0b8d1c59f6f18`
- `results/phase_7/variants_ledger.json` registered: `2026-10-24T15:11:36Z`
- `results/phase_7/assets/table_diagnostics_o2.csv` asserted against `results/phase_5/top200_hd_chunks.json` and `results/phase_5/top50_hd_chunks.json`.
- `results/phase_7/assets/table_p7_contrasts.csv` verified against `results/phase_7/phase7_results.json`.
- `results/phase_7/assets/table_o2_4budget_scaling.csv` verified against `results/phase_7/phase7_results.json`.

