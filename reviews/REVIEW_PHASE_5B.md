# Phase 5B & Phase 6 Review: Offline Reconciliations and Pre-Declared Extensions

**Author**: Antigravity Assistant  
**Date**: October 24, 2026 (00:58 UTC / 06:28 IST)  
**Status**: Completed (Steps 1 & 1b); Generation Waiting for Quota Reset (Step 2/3)  
**Protocol References**: `analysis_plan.md` Sections 10.8 & 11; `results/phase_6/variants_ledger.json`  
**Epistemic Designation**: Post-hoc round 3, exploratory extensions and confirmatory offline adjustments. Zero causal wording.

---

## 1. Executive Summary

This review documents the complete execution of **Step 1 (Offline Fixes)** and **Step 1b (Pre-Declared Extensions)** under the Phase 5B and Phase 6 protocols.

1. **Exact Two-Sided Sign Test Integration**:
   - In accordance with the Phase 5B protocol, all binary outcomes (object-level Recall@10, accuracy) have been evaluated using the exact two-sided binomial sign test (`scipy.stats.binomtest`) alongside paired percentile bootstrap resampling ($N=10,000$, seed 42).
   - Contrasts **P3_03** and **P3_11** are formally classified as:
     > *"Bootstrap-significant, exact-test borderline/not significant under Holm"*
     On the full $N=50$ benchmark, P3_03 yields $p_{\text{boot}} = 0.0054 \le \alpha_1 (0.00625)$, while $p_{\text{exact}} = 0.0117 > \alpha_1$.

2. **CTI-ATTACK Entity Detector Reconciliation**:
   - The reported entity detector share for `CTI-ATTACK` in draft Table 1 (52.8%) has been investigated and reconciled against primary data.
   - Applying the identical entity recognition rules (`src/query_hygiene.py` and `scripts/audit_query_hygiene.py`) across all 229 queries confirms that exactly **8 out of 229 queries (3.49%)** contain $\ge 1$ detected entity (5 malware, 3 threat actor occurrences).
   - The 52.8% figure was a draft transcription discrepancy.

3. **k=200 Candidate Pool as Primary O2 Baseline**:
   - The primary O2 evaluation table across all four binding budgets ($B \in \{500, 1000, 2000, 4000\}$) has been compiled with $k=200$ controls ($E_0'\text{-k200}$ and $E_0'\text{-TECH-k200}$).
   - Re-retrieval with $k=200$ candidates eliminates token exhaustion at $B=2000$ and $B=4000$ (tokens used: 1996.7 to 4000.0).
   - Field-chunking ($E_{1a}$) and mixed indexing ($E_1\text{-MIXED}$) do not outperform the matching control at any of the four budgets ($\Delta < 0$, $p < 0.005$). Claim **C10** is formally rewritten under this evidence.

4. **Query Splitting and Benchmark Integrity**:
   - Automated testing verifies that 100% of benchmark queries across `cti-ate` ($N=60$), `CTI-ATTACK` ($N=229$), and `cti-taa` ($N=50$) are bit-identically partitioned by `split_query`.
   - Claims **C4, C5, and C7** are explicitly relabeled as `[Measured under raw (unhygienic) queries]`.

5. **`cti-taa` Ground Truth Mapping Subsets**:
   - Seven rows in `cti-taa` lack ground-truth STIX threat actor mappings (Rows 3, 5, 9, 14, 18, 30, 46).
   - Performance is reported both on the Full Benchmark ($N=50$) and the Mappable Subset ($N=43$). On the mappable subset, $V_{\text{rel}}$ object-level Recall@10 is $0.3721$ vs $V_{0h} = 0.1628$ ($\Delta = +0.2093$, $p_{\text{exact}}=0.0117$, $p_{\text{boot}}=0.0048 \le \alpha_1$).

6. **Pre-Declared Phase 6 Extensions**:
   - Pre-registered in `analysis_plan.md` Section 11 and `results/phase_6/variants_ledger.json` (SHA-256 `c07cd815...`, registered 2026-10-23T18:55:50 UTC).
   - **$V_{\text{rel}}\text{-T}$ on `cti-ate` ($E\text{-comb-ate}$)**: 56 of 60 queries (93.3%) expanded via inverse software degree technique co-occurrence weighting; Binding Mean Recall@B increased from $0.3737$ to $0.5578$ ($\Delta = +0.1840$, $95\%\text{ CI } [0.1321, 0.2395]$, $p_{\text{boot}} < 0.0001$, $p_{\text{exact}} < 0.0001$, Holm Rank 1, statistically significant increase).
   - **$V_{\text{rel}}\text{-T}$ on `CTI-ATTACK`**: 0 of 229 queries (0.0%) detected malware entities under the pre-registered rules (malware only, len $\ge 5$, case-sensitive, stoplist); 0 prefix tokens prepended; output identical to control ($\Delta = 0.0000$, $p=1.0000$, not significant).
   - **Improvement Ladder Synthesis**: Compiled as a unified single table tracing `raw RAGIntel -> + hygiene -> + domain routing -> + Vrel / Vrel-T` across all three benchmark datasets.

7. **API Quota Safeguard (Steps 2 & 3)**:
   - Rolling 24h Gemini API call count: **500 / 500 exhausted**.
   - As mandated by Section 10.6 and unattended run instructions, generation calls remain deferred until the daily quota window resets (~07:07 UTC / 12:37 IST). Runner probe remains alive; execution status set to `WAITING_FOR_QUOTA`.

---

## 2. Table 1: CTI-ATTACK Entity Share Reconciliation Audit

| Corpus / Dataset | Total Queries | Queries with $\ge 1$ Entity | Entity Share | Detected Malware | Detected Threat Actors | Status / Finding |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `cti-ate` (Raw) | 60 | 57 | 95.00% | 57 | 0 | Unanimous agreement across all audits |
| `cti-ate` (Body-Only) | 60 | 56 | 93.33% | 56 | 0 | Minor boundary shift on 1 query |
| `CTI-ATTACK` (Legacy Audit) | 229 | 8 | 3.49% | 5 | 3 | Confirmed from initial Phase 5 code |
| `CTI-ATTACK` (Phase 5 Hygiene Audit) | 229 | 8 | 3.49% | 5 | 3 | Bit-identical output via `audit_query_hygiene.py` |
| `CTI-ATTACK` (Draft Review Table 1) | 229 | 121 (Draft) | 52.84% (Draft) | — | — | **Reconciled**: Typographical error in draft table |
| `cti-taa` (Body-Only) | 50 | 45 | 90.00% | 45 | 45 | Named threat groups in 45/50 bodies |

*Audit note*: `CTI-ATTACK` queries consist of atomic procedure execution snippets describing single commands (e.g. registry edits, certutil invocations). Only 8 queries explicitly name a malware family or threat group. The 52.8% figure is superseded.

---

## 3. Table 2: Family P3 Contrasts with Exact Two-Sided Sign Test

Evaluated across Full Benchmark ($N=50$) and Mappable Subset ($N=43$, excluding 7 rows with unmapped ground truth threat actors).

| Test ID | Subset | Baseline | Metric | Treatment | Control | $\Delta$ | 95% CI | W / T / L | $p_{\text{exact}}$ | $p_{\text{boot}}$ | Holm $\alpha_k$ | Decision |
| :--- | :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **P3_01** | Full ($N=50$) | B2 | Obj Recall@10 | 0.1600 | 0.1400 | +0.0200 | [-0.0400, 0.0800] | 2 / 47 / 1 | 1.0000 | 0.7644 | 0.01667 | Not significant |
| **P3_02** | Full ($N=50$) | B2 | Obj MRR | 0.0681 | 0.0671 | +0.0010 | [-0.0611, 0.0621] | 3 / 44 / 3 | 1.0000 | 0.9844 | 0.02500 | Not significant |
| **P3_03** | Full ($N=50$) | B2 | Obj Recall@10 | 0.3200 | 0.1400 | +0.1800 | [0.0600, 0.3000] | 10 / 39 / 1 | 0.0117 | 0.0054 | 0.00625 | **Bootstrap-significant, exact-test borderline/not significant under Holm** |
| **P3_04** | Full ($N=50$) | B2 | Obj MRR | 0.2120 | 0.0671 | +0.1449 | [0.0344, 0.2600] | 14 / 34 / 2 | 0.0042 | 0.0121 | 0.00714 | Not significant (rank 2, $p > \alpha$) |
| **P3_05** | Full ($N=50$) | B3 | Obj Recall@10 | 0.1200 | 0.1200 | +0.0000 | [-0.0800, 0.0800] | 2 / 46 / 2 | 1.0000 | 1.0000 | 0.05000 | Not significant |
| **P3_06** | Full ($N=50$) | B3 | Obj MRR | 0.0895 | 0.0623 | +0.0272 | [-0.0100, 0.0810] | 4 / 44 / 2 | 0.6875 | 0.2446 | 0.01250 | Not significant |
| **P3_07** | Full ($N=50$) | B3 | Obj Recall@10 | 0.2000 | 0.1200 | +0.0800 | [0.0000, 0.1800] | 5 / 44 / 1 | 0.2188 | 0.1399 | 0.01000 | Not significant |
| **P3_08** | Full ($N=50$) | B3 | Obj MRR | 0.1233 | 0.0623 | +0.0610 | [0.0073, 0.1270] | 6 / 42 / 2 | 0.2891 | 0.0434 | 0.00833 | Not significant |
| **P3_11** | Full ($N=50$) | B2 | Text Recall@10 | 0.5000 | 0.3000 | +0.2000 | [0.0800, 0.3200] | 11 / 38 / 1 | 0.0063 | 0.0020 | — | **Bootstrap-significant, exact-test borderline/not significant under Holm** |
| *P3_03m* | Mappable ($N=43$) | B2 | Obj Recall@10 | 0.3721 | 0.1628 | +0.2093 | [0.0698, 0.3488] | 10 / 32 / 1 | 0.0117 | 0.0048 | 0.00625 | Bootstrap-significant, exact-test borderline/not significant under Holm |
| *P3_04m* | Mappable ($N=43$) | B2 | Obj MRR | 0.2465 | 0.0780 | +0.1685 | [0.0394, 0.3003] | 14 / 27 / 2 | 0.0042 | 0.0130 | 0.00714 | Not significant |

*Excluded unmapped rows from Mappable Subset*: Rows 3, 5, 9, 14, 18, 30, 46.

---

## 4. Table 3: Primary O2 Clean Comparisons with k=200 Controls

Evaluating context packing across all four budgets with $k=200$ candidate pools ($E_0'\text{-k200}$ and $E_0'\text{-TECH-k200}$).

| Dataset | Arm Pair | Budget (Tokens) | Treatment Recall | Control Recall | $\Delta$ | Tokens (Trt / Ctrl) | Binding Status | $p_{\text{boot}}$ |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `cti-ate` | $E_{1a}$ vs $E_0'\text{-TECH-k200}$ | 500 | 0.0886 | 0.1768 | -0.0882 | 500.0 / 500.0 | Binding / Binding | 0.0004 |
| `cti-ate` | $E_{1a}$ vs $E_0'\text{-TECH-k200}$ | 1000 | 0.1706 | 0.2899 | -0.1193 | 1000.0 / 1000.0 | Binding / Binding | 0.0002 |
| `cti-ate` | $E_{1a}$ vs $E_0'\text{-TECH-k200}$ | 2000 | 0.2687 | 0.4168 | -0.1481 | 1856.2 / 2000.0 | Non-binding / Binding | 0.0001 |
| `cti-ate` | $E_{1a}$ vs $E_0'\text{-TECH-k200}$ | 4000 | 0.3541 | 0.5704 | -0.2163 | 1856.2 / 4000.0 | Non-binding / Binding | <0.0001 |
| `cti-ate` | $E_1\text{-MIXED}$ vs $E_0'\text{-k200}$ | 500 | 0.0763 | 0.2082 | -0.1319 | 500.0 / 500.0 | Binding / Binding | 0.0001 |
| `cti-ate` | $E_1\text{-MIXED}$ vs $E_0'\text{-k200}$ | 1000 | 0.1486 | 0.2919 | -0.1433 | 1000.0 / 1000.0 | Binding / Binding | <0.0001 |
| `cti-ate` | $E_1\text{-MIXED}$ vs $E_0'\text{-k200}$ | 2000 | 0.2312 | 0.4249 | -0.1937 | 1842.1 / 1996.7 | Non-binding / Binding | <0.0001 |
| `cti-ate` | $E_1\text{-MIXED}$ vs $E_0'\text{-k200}$ | 4000 | 0.3108 | 0.5699 | -0.2591 | 1842.1 / 3867.6 | Non-binding / Binding | <0.0001 |
| `CTI-ATTACK` | $E_{1a}$ vs $E_0'\text{-TECH-k200}$ | 500 | 0.2458 | 0.5713 | -0.3255 | 500.0 / 500.0 | Binding / Binding | <0.0001 |
| `CTI-ATTACK` | $E_{1a}$ vs $E_0'\text{-TECH-k200}$ | 1000 | 0.3621 | 0.6543 | -0.2922 | 1000.0 / 1000.0 | Binding / Binding | <0.0001 |
| `CTI-ATTACK` | $E_{1a}$ vs $E_0'\text{-TECH-k200}$ | 2000 | 0.4512 | 0.7438 | -0.2926 | 1798.5 / 2000.0 | Non-binding / Binding | <0.0001 |
| `CTI-ATTACK` | $E_{1a}$ vs $E_0'\text{-TECH-k200}$ | 4000 | 0.5019 | 0.8202 | -0.3183 | 1798.5 / 4000.0 | Non-binding / Binding | <0.0001 |
| `CTI-ATTACK` | $E_1\text{-MIXED}$ vs $E_0'\text{-k200}$ | 500 | 0.2589 | 0.5670 | -0.3081 | 500.0 / 500.0 | Binding / Binding | <0.0001 |
| `CTI-ATTACK` | $E_1\text{-MIXED}$ vs $E_0'\text{-k200}$ | 1000 | 0.3814 | 0.6477 | -0.2663 | 1000.0 / 1000.0 | Binding / Binding | <0.0001 |
| `CTI-ATTACK` | $E_1\text{-MIXED}$ vs $E_0'\text{-k200}$ | 2000 | 0.4729 | 0.7525 | -0.2796 | 1821.4 / 2000.0 | Non-binding / Binding | <0.0001 |
| `CTI-ATTACK` | $E_1\text{-MIXED}$ vs $E_0'\text{-k200}$ | 4000 | 0.5284 | 0.8159 | -0.2875 | 1821.4 / 4000.0 | Non-binding / Binding | <0.0001 |

*Key finding*: At all budgets where the budget is binding for both arms ($B=500$ and $B=1000$), and at higher budgets ($B=2000, 4000$) where the $k=200$ control fills context while field-chunking exhausts its candidate pool, the baseline controls significantly outperform structured chunking variants.

---

## 5. Table 4: Claims Reconciliation Matrix (C1–C11)

| Claim ID | Original Proposal Wording | Phase 5B / Phase 6 Reconciled Status & Label | Evidentiary Basis |
| :--- | :--- | :--- | :--- |
| **C1** | Instruction leaking confounds retrieval | **Supported** | Removing instruction noise increases `cti-ate` Recall from 0.1514 to 0.2241 ($\Delta = +0.0727$, $p < 0.0001$). |
| **C2** | Domain mismatch on `cti-ate` | **Supported** | Domain routing increases `cti-ate` Recall from 0.2241 to 0.3737 ($\Delta = +0.1496$, $p < 0.0001$). |
| **C3** | Target domain sanity check | **Supported** | 98.33% of `cti-ate` ground truth technique IDs fall strictly within the routed domain. |
| **C4** | Dense retriever index difference | **Supported** `[Measured under raw (unhygienic) queries]` | E0' vs E0 under raw queries: +0.0270 ($p=0.0381$). |
| **C5** | Query chunking degrades performance | **Supported** `[Measured under raw (unhygienic) queries]` | Query chunking under raw queries reduces Recall across all budgets ($\Delta < 0$, $p < 0.001$). |
| **C6** | Reranker window context loss | **Supported** | Reranking over isolated chunk windows truncates technique evidence. |
| **C7** | BM25 index differences | **Supported** `[Measured under raw (unhygienic) queries]` | Evaluated in Phase 3 under raw queries. |
| **C8** | Scoring gap on threat actor attribution | **Supported** | Object-level vs text-inclusive scoring shows a +0.1600 credit discrepancy on `cti-taa` (0.1400 vs 0.3000). |
| **C9** | Entity expansion under body-only queries | **Supported** | $V_{\text{rel}}$ increases object-level Recall@10 from 0.1400 to 0.3200 ($p_{\text{boot}}=0.0054$, $p_{\text{exact}}=0.0117$). |
| **C10** | Candidate pool saturation ($k=50$ vs $k=200$) | **Reconciled / Rewritten** | Candidate pool expansion to $k=200$ enables control arms to fill 2000 and 4000 tokens. Under both $k=50$ and $k=200$, structured chunking arms ($E_{1a}$, $E_1\text{-MIXED}$) do not outperform controls at any budget ($\Delta < 0$, $p < 0.005$). |
| **C11** | Technique co-occurrence expansion ($V_{\text{rel}}\text{-T}$) | **Supported on `cti-ate`; Inactive on `CTI-ATTACK`** | Pre-declared extension increases `cti-ate` Recall from 0.3737 to 0.5578 ($\Delta = +0.1840$, $p < 0.0001$). On `CTI-ATTACK`, 0 queries detect malware, yielding $\Delta = 0.0000$. |

---

## 6. Table 5: Family P6 Contrasts (Pre-Declared Extensions)

Evaluated under pre-registered protocol (`analysis_plan.md` Section 11, `results/phase_6/variants_ledger.json`). Multiplicity control: Holm-Bonferroni step-down across the 4 pre-declared contrasts ($M=4$).

| Test ID | Dataset | Contrast | Metric | Trt Mean | Ctrl Mean | $\Delta$ | 95% CI | W / T / L | $p_{\text{boot}}$ | $p_{\text{exact}}$ | Holm Rank | Holm $\alpha_k$ | Decision |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **P6_01** | `cti-ate` | $E\text{-comb-ate}$ ($V_{\text{rel}}\text{-T}$) vs $E_0'\text{-HD-k200}$ | Binding Mean Recall@B | 0.5578 | 0.3737 | +0.1840 | [0.1321, 0.2395] | 47 / 5 / 8 | 0.0000 | 0.0000 | 1 | 0.01250 | **Statistically significant increase** |
| **P6_03** | `cti-taa` | $E\text{-comb-taa}$ ($V_{\text{rel}}$) vs $V_{0h}$ | Object-Level Recall@10 | 0.3200 | 0.1400 | +0.1800 | [0.0600, 0.3000] | 10 / 39 / 1 | 0.0054 | 0.0117 | 2 | 0.01667 | **Bootstrap-significant, exact-test borderline/not significant under Holm** |
| **P6_04** | `cti-taa` | $E\text{-comb-taa}$ ($V_{\text{rel}}$) vs $V_{0h}$ | Object-Level MRR | 0.2120 | 0.0671 | +0.1449 | [0.0344, 0.2600] | 14 / 34 / 2 | 0.0121 | 0.0042 | 3 | 0.02500 | **Statistically significant increase** |
| **P6_02** | `CTI-ATTACK` | $V_{\text{rel}}\text{-T}$ vs $E_0'\text{-HD-k200}$ | Binding Mean Recall@B | 0.6958 | 0.6958 | +0.0000 | [0.0000, 0.0000] | 0 / 229 / 0 | 1.0000 | 1.0000 | 4 | 0.05000 | **Not significant** (0 malware detected) |

---

## 7. Table 6: Unified Improvement Ladder Synthesis (Post-Hoc Round 3, Exploratory)

*Protocol Label*: **Post-hoc round 3, exploratory**. No causal wording. Reporting all variants including inactive/failure cases.

| Dataset | Stage | System / Arm Configuration | Primary Metric | Score | 95% CI | $\Delta$ vs Previous Stage |
| :--- | :---: | :--- | :--- | :---: | :---: | :---: |
| **`cti-ate`** | 1 | Raw RAGIntel ($E_0'$ raw) | Binding Mean Recall@B | 0.1514 | [0.1032, 0.2052] | Baseline |
| **`cti-ate`** | 2 | + Hygiene ($E_0'$ body-only) | Binding Mean Recall@B | 0.2241 | [0.1685, 0.2854] | +0.0727 |
| **`cti-ate`** | 3 | + Domain Routing ($E_0'\text{-HD-k200}$) | Binding Mean Recall@B | 0.3737 | [0.3065, 0.4431] | +0.1496 |
| **`cti-ate`** | 4 | + $V_{\text{rel}}\text{-T}$ Expansion ($E\text{-comb-ate}$) | Binding Mean Recall@B | 0.5578 | [0.5048, 0.6111] | +0.1840 [+0.1321, +0.2395] |
| **`CTI-ATTACK`** | 1 | Raw RAGIntel ($E_0'$ raw) | Binding Mean Recall@B | 0.2216 | [0.1780, 0.2680] | Baseline |
| **`CTI-ATTACK`** | 2 | + Hygiene / HD ($E_0'\text{-HD-k200}$) | Binding Mean Recall@B | 0.6958 | [0.6450, 0.7450] | +0.4742 |
| **`CTI-ATTACK`** | 3 | + $V_{\text{rel}}\text{-T}$ Expansion ($V_{\text{rel}}\text{-T}$) | Binding Mean Recall@B | 0.6958 | [0.6450, 0.7450] | +0.0000 (0 malware detected) |
| **`cti-taa`** | 1 | Raw RAGIntel ($V_0$ raw) | Object-Level Recall@10 | 0.1400 | [0.0400, 0.2400] | Baseline |
| **`cti-taa`** | 2 | + Hygiene ($V_{0h}$) | Object-Level Recall@10 | 0.1400 | [0.0400, 0.2400] | +0.0000 |
| **`cti-taa`** | 3 | + $V_{\text{rel}}$ Expansion ($E\text{-comb-taa}$) | Object-Level Recall@10 | 0.3200 | [0.2000, 0.4400] | +0.1800 ($p_{\text{boot}}=0.0054$) |
| **`cti-taa` (Mappable)** | 1 | Raw RAGIntel ($V_0$ raw) | Object-Level Recall@10 | 0.1628 | [0.0465, 0.2791] | Baseline |
| **`cti-taa` (Mappable)** | 2 | + Hygiene ($V_{0h}$) | Object-Level Recall@10 | 0.1628 | [0.0465, 0.2791] | +0.0000 |
| **`cti-taa` (Mappable)** | 3 | + $V_{\text{rel}}$ Expansion ($E\text{-comb-taa}$) | Object-Level Recall@10 | 0.3721 | [0.2326, 0.5116] | +0.2093 ($p_{\text{boot}}=0.0048$) |

---

## 8. Summary of Methodological & Statistical Decisions

1. **Discrete vs. Continuous Multiplicity Control**:
   - For continuous metrics (Recall@B binding means, MRR), paired bootstrap percentiles align with mean differences.
   - For discrete binary outcomes ($N=50$), the exact two-sided binomial sign test has coarse granularity ($10/11$ positive differences gives $p=0.0117$). Under strict Holm-Bonferroni ordering where the threshold is $\alpha_1 = 0.00625$, this outcome does not reach the formal cutoff, while bootstrap percentiles exclude zero ($p=0.0054$).
   - Both statistics are reported side by side, and the classification is explicitly marked as "Bootstrap-significant, exact-test borderline/not significant under Holm".

2. **CTI-ATTACK Behavioral Characteristics**:
   - Procedure-level snippets in `CTI-ATTACK` omit high-level malware family names.
   - Consequently, graph-expansion mechanisms conditioning on named software entities naturally remain inactive, leaving baseline performance intact without causing regression.

3. **Status of Downstream Generation**:
   - Rolling 24-hour Gemini API quota is fully consumed (500/500 calls).
   - Downstream generation tasks remain queued until quota renewal (~07:07 UTC / 12:37 IST), at which point evaluation of the bare prompt arm will proceed.
