# Pre-Registered Statistical Analysis Plan: Phase 2 (Optimization 1 — Entity Resolution)

**Document Status**: Pre-registered prior to running Phase 2 Part C benchmark.  
**Project**: Dual-degree thesis: *Optimizing RAG for Cyber Threat Intelligence: Entity Resolution and Structure-Aware Chunking for Reliable LLM-Based Attack Investigation*.  
**Date**: October 19, 2026.  
**Random Seed**: 42 (locked across all stochastic resamples and controls).  
**Knowledge Bases**: Primary KB = `E0-STIX-ALL`; Secondary KB = `E0-STIX-ENT`.

---

## 1. Context and Objective

Phase 1 established that threat actor attribution (`cti-taa`) exhibits substantial retrieval degradation when long queries are segmented into sliding windows without entity context. In 82.0% of `cti-taa` queries, the adversary entity alias does not occur within the initial 256 tokens.

The objective of Optimization 1 (O1) is query-side entity resolution: detecting cyber threat entities (intrusion sets, malware, tools) in unstructured query text and injecting canonical identifiers and aliases into the query representation prior to retrieval.

This analysis plan pre-registers the statistical hypotheses, families of comparisons, error rate control procedures, and decision rules for Phase 2 evaluation.

---

## 2. Hypothesis Families and Multiplicity Control

To prevent false discovery rate inflation, all planned statistical tests are partitioned into three formal families: Primary ($P_1$), Secondary ($S_1$), and Exploratory ($E$).

### Family $P_1$: Primary Confirmatory Family (`cti-taa` Retrieval Performance)
- **Target Dataset**: `cti-taa` (50 threat actor attribution queries).
- **Primary Knowledge Base**: `E0-STIX-ALL` (2,062 active objects: Enterprise + Mobile + ICS).
- **Baselines**: Baseline B2 (MiniLM Truncated) and Baseline B3 (MiniLM MaxSim Windows).
- **Contrasts Comprising Family $P_1$** ($m = 8$ formal hypotheses pre-registered on `E0-STIX-ALL`):
  1. $H_{1}$: B2 Recall@10 ($V_1$ vs $V_0$)
  2. $H_{2}$: B2 MRR ($V_1$ vs $V_0$)
  3. $H_{3}$: B2 Recall@10 ($V_1$ vs $V_3$)
  4. $H_{4}$: B2 MRR ($V_1$ vs $V_3$)
  5. $H_{5}$: B3 Recall@10 ($V_1$ vs $V_0$)
  6. $H_{6}$: B3 MRR ($V_1$ vs $V_0$)
  7. $H_{7}$: B3 Recall@10 ($V_1$ vs $V_3$)
  8. $H_{8}$: B3 MRR ($V_1$ vs $V_3$)
- **Decision Rule & Multiplicity Control**: Holm-Bonferroni step-down correction at nominal $\alpha = 0.05$ across the $m = 8$ primary contrasts.
  - Raw two-sided paired bootstrap p-values ($B=10,000$, seed 42) are ordered: $p_{(1)} \le p_{(2)} \le \dots \le p_{(8)}$.
  - Compare $p_{(k)} \le \frac{0.05}{8 - k + 1}$. Rejections proceed sequentially until the first $k$ where $p_{(k)} > \frac{0.05}{9 - k}$, after which all remaining hypotheses are non-significant.
- **Timing of Scope Specification**: Confirmed and recorded as decided before benchmark results were finalized.

### Scope of Part C4 Benchmark (Exact Evaluation Cells)
The benchmark evaluates 48 discrete experimental cells (2 KBs × 2 Baselines × 4 Variants × 3 Datasets):
- **Knowledge Bases (2)**: `E0-STIX-ALL` (Primary, 2,062 objects), `E0-STIX-ENT` (Secondary, 1,698 objects).
- **Baselines (2)**: B2 (`MiniLM-Truncated-256`), B3 (`MiniLM-MaxSim-Windows`).
- **Variants (4)**: V0 (raw baseline), V1 (alias expansion), V2 (canonical ID prepending), V3 (length-matched random alias ablation).
- **Datasets (3)**: `cti-taa` (50 queries, primary attribution), `cti-ate` (60 queries, technique extraction), `CTI-ATTACK` (229 queries, technique extraction).

### Family $S_1$: Secondary Confirmatory Family (Transfer & Alternative Variant Comparison)
- **Comparisons**:
  1. **Variant V2**: Prepend canonical name + MITRE ID only vs V0 and vs V3 on `cti-taa` (Recall@10 and MRR under B2 and B3).
  2. **Non-Attribution Transfer**: Variant V1 vs V0 on `cti-ate` (60 queries) and `CTI-ATTACK` (229 queries) under B2 and B3.
  3. **Secondary KB Evaluation**: Replication of $P_1$ contrasts on `E0-STIX-ENT`.
- **Metrics**: Recall@5, Recall@10, MRR, nDCG@10.
- **Reporting**: Point estimates, paired bootstrap 95% CIs, and Benjamini-Hochberg FDR-adjusted q-values ($\alpha = 0.05$).

### Family $E$: Exploratory Family
- **Metrics & Analyses**:
  - Sub-technique credit metrics (`SubtechCredit_Recall@10`, `SubtechCredit_MRR`).
  - Reachable ceiling metrics on `E0-STIX-ENT` ($N=46$).
  - Per-query win/tie/loss counts.
  - Per-query latency overhead (mean and 95th percentile).
  - Downstream offline answer generation scoring (Hit, Precision, Recall, F1 against canonical/alias ground truth).
- **Post-Hoc Status Disclaimer**:
  > **Explicit Pre-Registration Clarification**: The Phase 1c retrieval comparisons between Baseline B3 (MaxSim) and Baseline B2 (Truncated) on `cti-taa` (e.g., $p = 0.0126$ on ENT, $p = 0.0371$ on ALL) were computed post-hoc during initial baseline exploration. They are formally designated as **exploratory (not pre-registered)**. Confirmatory claims regarding entity resolution are strictly restricted to Family $P_1$.

---

## 3. Resampling and Estimation Methodology

- **Resampling Method**: Paired non-parametric bootstrap resampling.
- **Resamples**: $B = 10,000$ iterations.
- **Random Seed**: Fixed at `42` (`numpy.random.default_rng(42)`).
- **Pairing Rule**: For each bootstrap replicate $b \in \{1, \dots, B\}$, sample query indices with replacement: $\mathcal{I}_b = \{i_1^*, \dots, i_n^*\}$.
- **Metric Delta**: Compute $\Delta_b^* = \frac{1}{n} \sum_{i \in \mathcal{I}_b} M_i(V_1) - \frac{1}{n} \sum_{i \in \mathcal{I}_b} M_i(V_0)$.
- **95% Confidence Interval**: Percentile bootstrap interval $[\Delta^*_{0.025}, \Delta^*_{0.975}]$.
- **Two-Sided Empirical p-value**:
  $$p = 2 \cdot \min\left( \frac{1}{B}\sum_{b=1}^B \mathbb{I}(\Delta_b^* \le 0), \; \frac{1}{B}\sum_{b=1}^B \mathbb{I}(\Delta_b^* \ge 0) \right)$$
  bounded above by $1.0$.

---

## 4. Query-Side Optimization 1 Variants

- **V0 (Baseline)**: Raw query string unmodified.
- **V1 (Alias Expansion)**: Regex-detected entity aliases prepended to query text, capped at 64 tokens budget.
- **V2 (Canonical ID Expansion)**: Prepend only `[Entity: <Canonical_Name> (<MITRE_ID>)]`.
- **V3 (Random Control)**: Prepend randomly selected threat entity aliases with length matched to V1 under seed 42.

---

## 5. Artifact and Verification Manifest

All Phase 2 experimental result artifacts must include an accompanying `manifest.json` detailing:
1. Git / code directory SHA-256 hash.
2. Configuration file (`config.yaml`) SHA-256 hash.
3. Knowledge base index files (`.faiss` and `.pkl`) SHA-256 hashes.
4. Execution timestamp (ISO 8601 UTC).
5. Fixed pseudo-random number generator seed (`42`).

---

## 6. Pre-Registered Statistical Analysis Plan: Phase 3 (Optimization 2 — Structure-Aware Chunking)

**Pre-Registration Date**: October 21, 2026 (prior to running Phase 3 O2 benchmark cells).  
**Scope Reduction**: Applied per thesis amendment for October 28 freeze deadline.  
**Corpus**: `E0-STIX-ALL` (2,062 active objects: Enterprise + Mobile + ICS).  
**Random Seed**: 42 (locked across paired bootstrap and random controls).

### 6.1 Corpus Chunking and Matched Token Budget Determination (C0)
Analysis of the 6,693 active STIX child chunks reveals:
- `attack-pattern` (4,505 chunks): mean 297.9 chars (median 326.0), mean 39.0 words (median 42.0 words).
- `intrusion-set` (555 chunks): mean 249.4 chars (median 207.0), mean 28.7 words (median 24.0 words).
- `malware` / `tool` (1,633 chunks): mean 260.8 chars (median 283.0), mean 28.4 words (median 30.0 words).

Based on empirical sampling across the benchmark queries, the median top-10 retrieved context token size for the baseline control $E_0'$ is 349.5 words (~465 MiniLM subword tokens). Rounded to the nearest 50 tokens:
B* = 500 tokens

Exploratory secondary budgets evaluated: $B \in \{500, 1000, 2000, 4000\}$ tokens.

### 6.2 Optimization 2 Experimental Arms
1. **$E_0'$ (Baseline Splitter Control)**: STIX text converted to markdown and chunked via baseline recursive character splitter (parent 2000 / child 500), strictly truncated to token budget $B$.
2. **$E_{1a}$ (Field Chunks)**: Decomposed into 4 logical fields: `identity_description`, `procedure_examples`, `mitigations`, and `detection`.
3. **$E_{1b}$ (Structure-Aware Sibling Expansion)**: $E_{1a}$ seed chunks expanded with sibling chunks sharing the same parent `technique_id` under matched token budget $B$, strictly truncating the final chunk.
4. **$E_{1c}$ (Random Sibling Control)**: $E_{1a}$ seed chunks expanded with randomly sampled chunks from unrelated `technique_id`s (seed 42) under matched token budget $B$.

### 6.3 Family $P_2$: Primary Confirmatory Family (Structure-Aware Technique Extraction)
- **Target Datasets**: `cti-ate` (60 queries) and `CTI-ATTACK` (229 queries).
- **Baselines**: Baseline B2 (MiniLM Truncated) and Baseline B3 (MiniLM MaxSim Windows).
- **Primary Contrast**: $E_{1b}$ vs $E_0'$ at matched budget $B^* = 500$ tokens.
- **Primary Metric**: Recall at budget $B^*$ over technique IDs credited by chunks inside the first $B^*$ tokens with `sub_credits_parent=True` (and MRR over chunk rank).
- **Inference**: Paired non-parametric bootstrap ($B=10,000$, seed 42) with Holm-Bonferroni step-down correction ($\alpha = 0.05$).
- **No-Regression Guard**: Non-regression check on `cti-taa` ($H_0: \text{Recall}_{\text{taa}}(E_{1b}) \ge \text{Recall}_{\text{taa}}(E_0') - 0.05$).

---

## 7. Phase 3B Deviation Log & Methodological Corrections

The following deviations occurred during initial Phase 3A execution and are formally corrected in Phase 3B prior to final evaluation:

1. **Deviation 1: Metric Evaluation Scoping (Recall@B vs Recall@10)**:
   - *Registered Protocol*: The registered metric for Family $P_2$ is Recall at matched context budget $B^*$ ($B^*=500$ tokens), computed strictly over the unique MITRE ATT&CK technique IDs credited by the chunks that fit within the first $B^*$ tokens (with directional sub-technique credit `sub_credits_parent=True`).
   - *Executed Deviation in Phase 3A*: `benchmark_phase3_o2.py` evaluated `Recall@10` over the raw retrieved top-$k$ list rather than restricting technique credit to the truncated context budget.
   - *Correction*: Phase 3B computes Recall@B exclusively from the budget-truncated chunk list fitting within $B$ tokens ($B \in \{500, 1000, 2000, 4000\}$).

2. **Deviation 2: Sibling Insertion Order ($E_{1b}$ / $E_{1c}$)**:
   - *Registered Protocol*: Specification C2 dictates that siblings must be inserted *immediately after their parent hit* in rank order, with the list subsequently truncated at $B$ tokens.
   - *Executed Deviation in Phase 3A*: `StructureAwareIndex.expand_siblings_e1b` appended all candidate siblings to the end of the full seed document list. Because the seed documents alone exceeded 500 tokens, no siblings ever entered the context at $B^* = 500$.
   - *Correction*: Phase 3B inserts siblings immediately following their parent seed chunk before advancing to the next seed chunk, properly integrating siblings into the context budget.

3. **Deviation 3: Separate Field-Chunk Index for $E_{1a}$ Retrieval**:
   - *Registered Protocol*: $E_{1a}$ evaluates retrieval directly over the 4 decomposed field chunks (`identity_description`, `procedure_examples`, `mitigations`, `detection`).
   - *Executed Deviation in Phase 3A*: The retriever searched the baseline splitter index ($E_0'$) and merely performed budget truncation.
   - *Correction*: Phase 3B builds a dedicated hybrid index (dense FAISS + BM25 + FlashRank reranker) over the 5,976 field chunks in `.cache/retriever_index_field_chunks/` from which $E_{1a}$ ranks candidates directly.

4. **Deviation 4: Random Generator Execution-Order Independence (V3 Control)**:
   - *Registered Protocol*: Ablation arm $V_3$ should produce deterministic, reproducible random draws regardless of whether datasets or queries are executed together or in isolation.
   - *Executed Deviation in Phase 2*: The global `self.rng` advanced sequentially, causing seed draws to vary when subsets of queries were run.
   - *Correction*: Phase 3B re-implements per-query deterministic hashing `hash(seed, dataset, row_idx)` for all random controls ($V_3$ and $E_{1c}$).

---

## 8. Pre-Registered Statistical Analysis Plan: Phase 3C (Controls and Corrected Arms)

**Pre-Registration Date & Time**: October 22, 2026, 03:55:00 UTC (Pre-registered prior to running any Phase 3C retrieval or evaluation runs).  
**Project**: Dual-degree thesis: *Optimizing RAG for Cyber Threat Intelligence: Entity Resolution and Structure-Aware Chunking for Reliable LLM-Based Attack Investigation*.  
**Corpus**: `E0-STIX-ALL` (2,062 active objects: Enterprise + Mobile + ICS).  
**Random Seed**: 42 (locked across all paired bootstrap resamples and random controls; per-query seed via `hash(42, dataset, row_idx)`).

### 8.1 Experimental Arms
1. **$E_0'$ (Baseline Splitter Control - All Objects)**: STIX text converted to markdown and chunked via baseline recursive character splitter (parent 2000 / child 500) over all 2,062 active STIX objects (6,693 chunks). Truncated to budget $B$.
2. **$E_0'\text{-TECH}$ (Controlled Splitter - Technique Objects Only)**: Baseline recursive character splitter applied strictly to `attack-pattern` (technique/sub-technique) objects only, yielding the exact same STIX object coverage as $E_{1a}$. Evaluated on `cti-ate` (B2, B3) and `CTI-ATTACK` (B2, B3 computed separately to empirically verify equality).
3. **$E_{1a}$ (Field-Chunk Index - Technique Objects Only)**: Decomposed into 4 logical fields (`identity_description`, `procedure_examples`, `mitigations`, `detection`) across technique objects (5,976 field chunks).
4. **$E_1\text{-MIXED}$ (Unified Mixed Index)**: A single unified index combining technique objects decomposed into field chunks (as in $E_{1a}$, 5,976 chunks) with all non-technique active STIX objects (`intrusion-set`, `malware`, `tool`, `course-of-action`, `campaign`) chunked using the baseline splitter (2,188 chunks). Total chunks = 8,164.
5. **$E_{1b}\text{-MIXED}$ (Structure-Aware Sibling Expansion on Mixed Index)**: Retrieved seeds from $E_1\text{-MIXED}$ expanded with sibling chunks sharing the same parent `technique_id` (technique chunks only), inserted immediately after the parent hit, truncated at budget $B$.
6. **$E_{1c}\text{-MIXED}$ (Random Sibling Control on Mixed Index)**: Retrieved seeds from $E_1\text{-MIXED}$ expanded with random sibling chunks from unrelated techniques (per-query seed), inserted immediately after parent, truncated at budget $B$.

### 8.2 Technique Credit Rules
Every arm is evaluated under two pre-registered credit rules:
- **Primary Credit Rule (Text + Metadata Mention)**: Technique IDs identified via regex extraction on chunk text plus explicit `mitre_id` metadata if matching `T\d{4}(\.\d{3})?`. (The rule used in Phase 3B; designated as primary confirmatory).
- **Secondary Credit Rule (Metadata-Only)**: Technique IDs credited strictly if stored in chunk `metadata["mitre_id"]` or `metadata["technique_id"]`. Serves as pre-registered sensitivity analysis; no post-hoc switching.

### 8.3 Hypothesis Families and Multiplicity Control

#### Family $P_2'$: Primary Confirmatory Family (Mixed-Index Structure-Aware Technique Extraction)
- **Primary Contrast**: $E_{1b}\text{-MIXED}$ vs $E_0'$ at matched budget $B^* = 500$ tokens.
- **Primary Metric**: Recall at budget $B^*$ over technique IDs credited under `sub_credits_parent=True` (Primary Credit Rule).
- **Target Evaluation Cells**:
  1. $H_1'$: `cti-ate` B2 ($E_{1b}\text{-MIXED}$ vs $E_0'$)
  2. $H_2'$: `cti-ate` B3 ($E_{1b}\text{-MIXED}$ vs $E_0'$)
  3. $H_3'$: `CTI-ATTACK` B2 ($E_{1b}\text{-MIXED}$ vs $E_0'$; counted as one test with B3 if empirically identical)
  4. $H_4'$: `CTI-ATTACK` B3 ($E_{1b}\text{-MIXED}$ vs $E_0'$; if distinct from B2)
- **No-Regression Guard**: Non-regression test on `cti-taa` B2 ($H_0: \text{Recall}(E_{1b}\text{-MIXED}) \ge \text{Recall}(E_0') - 0.05$ with paired bootstrap 95% CI).
- **Multiplicity Correction**: Holm-Bonferroni step-down correction at nominal $\alpha = 0.05$ over the confirmatory family contrasts.

#### Family $E_2'$: Exploratory Comparisons
1. **Field Chunking Alone**: $E_{1a}$ vs $E_0'\text{-TECH}$ on `cti-ate` and `CTI-ATTACK` (direct controlled test of field chunking against recursive splitting on the identical object set).
2. **Sibling Expansion Effect**: $E_{1b}$ vs $E_{1a}$ and $E_{1b}\text{-MIXED}$ vs $E_1\text{-MIXED}$.
3. **Sibling Specificity vs Token Filler**: $E_{1b}$ vs $E_{1c}$ and $E_{1b}\text{-MIXED}$ vs $E_{1c}\text{-MIXED}$.
4. **Field vs Baseline Splitter**: $E_{1a}$ vs $E_0'$ under primary and sensitivity credit rules.
5. **Budget Scaling**: Offline evaluation across $B \in \{500, 1000, 2000, 4000\}$ tokens.

### 8.4 Execution Protocol
- Strict offline execution (`OFFLINE_ONLY=true`).
- Single-process execution to preserve system stability under memory constraints (thread cap = 4).
- Progress logging every 25 queries.
- Per-cell serialization to avoid uncommitted state.

---

## 9. Pre-Registration: Generation-Level Evaluation Family G1 and Exploratory Contrasts
**Timestamp**: `2026-10-22T07:45:00Z` (Pre-registered strictly before generation or scoring of any $E_{1b}\text{-MIXED}$ answers).

### 9.1 Confirmatory Family G1 (Generation-Level Technique Extraction)
- **Primary Contrast**: $E_{1b}\text{-MIXED}$ vs $E_0'$ at matched budget $B^* = 500$ tokens.
- **Metric**: End-to-end LLM Technique F1 under sub-technique credit rule (`sub_credit`: sub-technique prediction credits parent ground-truth).
- **Target Hypotheses (2 tests)**:
  1. $G_{1,1}$: `cti-ate` (60 queries) — $E_{1b}\text{-MIXED}$ vs $E_0'$
  2. $G_{1,2}$: `CTI-ATTACK` (229 queries) — $E_{1b}\text{-MIXED}$ vs $E_0'$
- **Statistical Testing**: Two-sided paired bootstrap resampling ($N = 10,000$, seed 42) computing paired difference $\Delta = F_1(E_{1b}\text{-MIXED}) - F_1(E_0')$, 95% bootstrap percentile confidence intervals, and empirical $p$-values.
- **Multiplicity Control**: Holm-Bonferroni step-down correction across $M = 2$ tests at family-wise $\alpha = 0.05$.

### 9.2 Exploratory Generation Contrasts (Descriptive, Uncorrected)
All other generation-level comparisons are explicitly designated as exploratory and uncorrected:
1. **RAG Arms vs LLM-Only Baseline**:
   - Technique F1 (`sub_credit` and `strict`) on `cti-ate` and `CTI-ATTACK` for $E_0'$ vs LLM-only and $E_{1b}\text{-MIXED}$ vs LLM-only.
   - Threat actor attribution accuracy on `cti-taa` for RAG arms (baseline B2 V0 and V1) vs LLM-only.
2. **Query Expansion Attribution**:
   - V1 (cyber entity-expanded query) vs V0 (raw query) attribution accuracy on `cti-taa` under alias scoring across both scorer variants.
3. **Threat Group Scorer Primary Designation**:
   - Both Scorer Variant 1 (Text-based regex extraction from ground-truth string) and Scorer Variant 2 (STIX ontology-based canonical and alias expansion) are computed.
   - **Status**: Designating Scorer Variant 2 as the primary scorer is explicitly designated as **post hoc** (decided after observing empirical baseline scores on V0/V1/LLM-only). Variant 1 is maintained and reported in full as the sensitivity metric.

---

## 10. Phase 5 Protocol: Pre-Declared Fixes and Improvement Round (Post-hoc, Exploratory)
**Date**: 2026-10-23  
**Status**: Pre-Declared Protocol (Phase 5 Round 2)  
**Execution Environment**: Strict offline evaluation (`OFFLINE_ONLY=true`, thread cap = 4 via `OMP_NUM_THREADS=4`, `torch.set_num_threads(4)`), one heavy process at a time.  
**Pre-existing Knowledge Baseline**: All Phase 0–4 results (retrieval benchmarks, generation caches, and failure audits) are frozen and untouched. All Phase 5 analyses are designated "post-hoc round 2, exploratory".

### 10.1 Methodological Governance Rules
- **(R1) Strict Pre-Declaration**: Every variant is defined prior to execution. No variants may be added, removed, or retuned after observing empirical results. All outcomes, including negative or neutral results, are reported in full.
- **(R2) Independent Derivation**: All rules and filters derive exclusively from STIX knowledge base properties and task prompt instruction text, never from dataset ground truths or per-query empirical distributions.
- **(R3) Explicit Labeling**: All tables, figures, and narratives are labeled "post-hoc round 2, exploratory", reflecting prior exposure to benchmark queries.
- **(R4) Neutral Scientific Tone**: Zero causal language ("due to", "attributable to", "confirms", "severely", "actual cause", "true expected center") is permitted.
- **(R5) Dual Attribution Credit & STIX Mapping**: Threat actor attribution tables report both object-level and text-inclusive credit rules. Every ground-truth threat group in `cti-taa` is asserted to map to exactly one STIX canonical intrusion-set object; any 0 or >1 matches are listed explicitly.

### 10.2 Query Hygiene Protocol (`split_query`)
To eliminate entity detector false positives triggered by prompt boilerplate instructions, every benchmark query $q$ is parsed into:
- `instruction`: Text preceding the marker (`"Threat Report:"` or `"**Text:**"`).
- `body`: Text following the marker.
- **Assertion**: Every query across all 339 benchmark queries (`cti-ate`: 60, `CTI-ATTACK`: 229, `cti-taa`: 50) must contain either `"Threat Report:"` or `"**Text:**"`.

### 10.3 Optimization 1 (O1) Variants (Retrieval Only, `cti-taa`, B2/B3, `E0-STIX-ALL`)
Evaluated strictly on query body text:
1. **$V_{0h}$ (Fair Baseline)**:
   - Evaluates the query body text directly without entity expansion.
2. **$V_{1h}$ (High-Precision Alias Expansion)**:
   - Detects entities within query body text.
   - Filter criteria:
     - Entity type restricted strictly to `intrusion-set` or `malware`.
     - Alias string length $\ge 5$ characters.
     - Case-sensitive exact match against STIX canonical name or alias casing.
     - Exclusion of common OS utilities and commands via fixed stoplist:
       `{"net", "cmd", "page", "play", "solar", "find", "sc", "at", "date", "time", "dir", "ping", "tasklist", "reg", "powershell", "wmic", "arp", "route", "hostname", "whoami", "ipconfig", "netstat", "schtasks", "nslookup", "systeminfo", "quser", "query", "run", "logoff", "shutdown", "format", "replace", "attrib", "assoc", "ftype", "tree", "move", "copy", "xcopy", "robocopy", "expand", "type", "more", "sort", "fc", "comp", "diskpart", "chkdsk", "sfc", "bcdedit", "vssadmin", "wevtutil", "certutil", "bitsadmin", "curl", "tar"}`.
     - Expansion prefix capped at 64 tokens.
3. **$V_{\text{rel}}$ (STIX Relationship Co-occurrence Expansion)**:
   - For each software entity (malware or tool) detected in query body using the $V_{1h}$ criteria, traverses non-revoked STIX `uses` relationships (`intrusion-set` $\to$ `malware`/`tool`).
   - Scores candidate threat groups $g$ via inverse group frequency:
     $$\text{score}(g) = \sum_{s \in \text{detected\_software}} \frac{1}{|\{g' \in \text{groups} : g' \text{ uses } s\}|}$$
   - Prepends the canonical name and first alias of the top 3 scoring groups to the query body (capped at 64 tokens).

### 10.4 Confirmatory Family P3 (O1 Hypotheses)
- **Contrasts (8 tests)**:
  - Baseline B2: $V_{1h}$ vs $V_{0h}$ (Recall@10, MRR); $V_{\text{rel}}$ vs $V_{0h}$ (Recall@10, MRR).
  - Baseline B3: $V_{1h}$ vs $V_{0h}$ (Recall@10, MRR); $V_{\text{rel}}$ vs $V_{0h}$ (Recall@10, MRR).
- **Secondary Sensitivity**: Contrasts against frozen full-query $V_0$.
- **Statistical Testing**: Paired bootstrap resampling ($N = 10,000$, seed 42) computing paired difference $\Delta$, 95% bootstrap percentile confidence intervals, and empirical $p$-values.
- **Multiplicity Control**: Holm-Bonferroni step-down correction across $M = 8$ tests at family-wise $\alpha = 0.05$.
- **Cross-Dataset Transfer Check**: $V_{1h}$ vs $V_{0h}$ evaluated on `cti-ate` and `CTI-ATTACK` with pre-declared non-inferiority margin $\Delta \ge -0.03$.

### 10.5 Optimization 2 (O2) Clean Comparisons (Retrieval Only, HD Preprocessing)
- **Preprocessing HD**:
  - Query body text only.
  - Domain filtering derived strictly from prompt instruction text:
    - If instruction contains `"MITRE Enterprise"`: restricts retriever candidate pool to Enterprise domain objects.
    - If instruction contains `"MITRE Mobile"`: restricts retriever candidate pool to Mobile domain objects.
    - `CTI-ATTACK` and `cti-taa`: no domain filter (all objects eligible).
  - Baseline comparison: Raw (frozen) full-query preprocessing without domain filtering.
  - Sanity check: Compute share of `cti-ate` rows whose ground-truth IDs reside in the declared domain.
- **Arms Evaluated**: $E_0'\text{-TECH}$, $E_{1a}$, $E_0'$, $E_1\text{-MIXED}$ (no sibling expansion arms).
- **Contrasts (Family P4, 6 tests, Holm-Bonferroni)**:
  - $E_{1a}$ vs $E_0'\text{-TECH}$ on: (1) `cti-ate` B2, (2) `cti-ate` B3, (3) `CTI-ATTACK`.
  - $E_1\text{-MIXED}$ vs $E_0'$ on: (4) `cti-ate` B2, (5) `cti-ate` B3, (6) `CTI-ATTACK`.
- **Metric**: Mean Recall@$B$ over $B \in \{500, 1000, 2000, 4000\}$, evaluated strictly for cells where token budget is binding. Full 4-budget scaling curves reported alongside.
- **Hygiene Effect Alone**: $E_0'$ under HD vs $E_0'$ raw.

### 10.6 Generation Ablation (API Protocol, Cap 250 Calls)
- **Execution Condition**: Executed strictly after completion of the 47 pending $E_{1b}\text{-MIXED}$ calls on `CTI-ATTACK`.
- **Hybrid Prompt Verbatim**:
  `"Use the provided context if it is relevant; otherwise use your own knowledge. List MITRE technique IDs."` (for `cti-taa`: `"attribute to a threat group"`).
- **Arms (220 calls total, within 250 call cap)**:
  - `cti-ate`: $E_0'\text{-HD}$ ($N=60$) and $E_1\text{-MIXED-HD}$ ($N=60$) = 120 calls.
  - `cti-taa`: $V_{0h}$ ($N=50$) and $V_{\text{rel}}$ ($N=50$) = 100 calls.
- **Reported Metrics**: End-to-end F1 / attribution accuracy vs existing `LLM-only` baseline; failure counts (empty, blocked, truncated, abstentions, unparseable outputs).
- **Quota Safeguard**: If API quota is exhausted, generation execution is deferred; all retrieval protocols remain active.

### 10.7 Dated Amendments (Phase 5 Addendum: 2026-10-23)
The following amendments are adopted as dated protocol extensions without altering pre-declared variants:
1. **Part C Budget Rule & Pool Extension ($k=200$)**:
   - Report Area Under the Curve (AUC) / binding mean only over budgets where the token budget is binding for **both** arms in the pair.
   - Introduce retriever arms $E_0'\text{-k200}$ and $E_0'\text{-TECH-k200}$ (re-retrieved with an expanded candidate pool of $k=200$ chunks) to fill higher token budgets ($B = 2000$ and $B = 4000$) where top-50 candidate pools run out of chunks; present these alongside the $k=50$ versions with explicit cell labeling.
2. **Binary Outcomes Testing (McNemar / Exact Sign Test)**:
   - For all binary paired retrieval and attribution outcomes (e.g., object-level Recall@10, attribution accuracy), compute the exact two-sided sign test (McNemar via binomial test with $p=0.5$ on discordant pairs) alongside paired bootstrap resampling ($N = 10,000$).
   - Explicitly annotate the origin of each reported $p$-value ($p_{\text{exact}}$ vs $p_{\text{boot}}$) and reconcile discrete confidence interval boundaries.
3. **Phase 4B V1-Strict Deprecation**:
   - Phase 4B V1-strict figures are deprecated and superseded by Phase 5 Part B body-only evaluation ($V_{0h}$, $V_{1h}$, $V_{\text{rel}}$); Phase 4B V1-strict numbers shall not be cited as valid benchmarks.
4. **Table 7 Claim Reconciliations ($C_9$)**:
   - Print Phase 4 vs Phase 4B Table 7 rows side-by-side.
   - Restore the original scoring-gap claim under its original identifier ($C_9$).
   - Reconcile the errant "P1_08 -0.12" reference and clarify the 0.22 vs 0.30 V1 value.
5. **Dual Attribution Primary/Secondary Designation**:
   - In all threat actor attribution tables, object-level credit is designated primary; text-inclusive credit is designated secondary.
6. **Part D API Call Telemetry & Parsing**:
   - Store `finish_reason` and token `usage` metadata for all generation API calls.
   - Parse technique and threat group identifiers from the entire response string.
7. **Ground-Truth STIX Status Audit**:
   - Add a dedicated row to the limitations table quantifying the count of ground-truth IDs that are revoked, deprecated, or absent in the pinned STIX knowledge base per dataset.


