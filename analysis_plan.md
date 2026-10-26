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

### 10.8 Dated Amendments (Phase 5B Amendments: 2026-10-24)
The following protocol refinements are adopted for Phase 5B unattended execution:
1. **Binary Outcomes Statistical Decision Protocol**:
   - For all binary outcomes (Recall@10, attribution accuracy), report the exact two-sided sign test $p$-value ($p_{\text{exact}}$ via `scipy.stats.binomtest`) alongside the paired bootstrap $p$-value ($p_{\text{boot}}$).
   - Contrasts P3_03 and P3_11 are explicitly classified as "bootstrap-significant, exact-test borderline/not significant under Holm step-down". Every decision explicitly notes which test procedure was evaluated.
2. **Claim C10 Reformulation with $k=200$ Controls**:
   - Claim C10 is updated using $k=200$ control pools: structure-aware field chunking ($E_{1a}$) does not outperform monolithic recursive splitting ($E_0'\text{-TECH-k200}$) at any token budget ($B \in \{500, 1000, 2000, 4000\}$).
3. **Primary O2 Scaling Table**:
   - The primary O2 comparison table reports contrasts against $k=200$ controls across all four budgets (where token budget is binding for all arms). The $k=50$ table is retained as secondary.
4. **CTI-ATTACK Detector Share Reconciliation**:
   - Formally reconcile the 3.49% (Phase 4 legacy detector) and 52.8% (Phase 5 high-precision regex/alias detector) query entity match shares within a single unified comparison script.
5. **Raw Query Condition Labeling**:
   - Claims C4, C5, and C7 are explicitly labeled as "measured under raw (unhygienic) queries".
6. **Mappable Subset Evaluation (`cti-taa`)**:
   - Report `cti-taa` attribution results on both the full dataset ($N=50$) and the mappable subset ($N=40$ rows whose ground-truth threat group exists in the pinned STIX knowledge base), listing all excluded rows.
7. **Query Splitting Uniformity Assertion**:
   - Assert programmatically that the instruction/body query splitting logic is applied identically across all evaluated arms.
8. **Generation Protocol Refinement**:
   - Evaluation utilizes the bare prompt (identical to LLM-only baseline; temperature 0, `max_output_tokens` 512, tracking `finish_reason` and usage metadata). Calls prioritized in order: (1) $E_0'\text{-HD}$ `cti-ate` (60), (2) $E_0'\text{-HD}$ `CTI-ATTACK` (229), (3) `cti-taa` $V_{0h}$ (50), (4) `cti-taa` $V_{\text{rel}}$ (50), (5) optional $E_1\text{-MIXED-HD}$ `cti-ate` (60).

## 11. Phase 6 Amendments: Pre-Declared Extensions (Post-Hoc Round 3, 2026-10-24)

### 11.1 Methodological Governance
- **(R1) Pre-Registration**: Formally declared prior to execution in `results/phase_6/variants_ledger.json`.
- **(R2) Independent Derivation**: Derived strictly from STIX knowledge base relationships (`uses` edges between `malware` and `attack-pattern`) and prompt boilerplate markers.
- **(R3) Explicit Labeling**: Labeled "post-hoc round 3, exploratory".
- **(R4) Neutral Scientific Tone**: Zero causal wording permitted.
- **(R5) Full Reporting**: All variants reported, including negative outcomes and failures.

### 11.2 Pre-Declared Variants
1. **$V_{\text{rel}}\text{-T}$ (Technique Co-occurrence Expansion)**:
   - **Target Datasets**: `cti-ate` ($N=60$) and `CTI-ATTACK` ($N=229$).
   - **Query Preprocessing**: Body-only queries via `split_query`. For `cti-ate`, HD domain routing restricts candidate techniques to the declared domain (`enterprise-attack` or `mobile-attack`).
   - **Entity Detection**: Same rules as $V_{1h}$:
     - Restrict to `malware` entity type.
     - Alias string length $\ge 5$ characters.
     - Case-sensitive exact match against STIX canonical name or alias casing.
     - Stoplist exclusion of common OS utilities and commands.
   - **Relationship Traversal**:
     - Traverse non-revoked STIX `uses` relationships where source is detected software $s$ and target is technique (attack-pattern) $t$ residing within the routed domain.
   - **Scoring Formula**:
     $$\text{score}(t) = \sum_{s \in \text{detected\_software}} \frac{1}{|\{t' \in \text{techniques} : s \text{ uses } t'\}|}$$
   - **Query Expansion**: Prepend the canonical names and MITRE technique IDs of the top 5 scoring techniques to the retrieval query (capped at 64 tokens). No other tuning.
2. **$E\text{-comb-taa}$**:
   - Query hygiene (body-only) + $V_{\text{rel}}$ relationship expansion on `cti-taa`.
3. **$E\text{-comb-ate}$**:
   - Query hygiene (body-only) + HD domain routing + $V_{\text{rel}}\text{-T}$ technique expansion on `cti-ate` (evaluated with $k=200$ candidate pool across 4 budgets).

### 11.3 Evaluation Metrics & Contrasts
- **Technique Benchmarks (`cti-ate`, `CTI-ATTACK`)**:
  - Primary metric: Recall@$B$ binding mean across budgets $B \in \{500, 1000, 2000, 4000\}$ using candidate pool $k=200$.
  - Contrast: $V_{\text{rel}}\text{-T}$ vs matching hygiene-only baseline ($E_0'\text{-HD-k200}$).
- **Threat Actor Attribution (`cti-taa`)**:
  - Metrics: Object-level Recall@10 (primary) and MRR.
  - Contrast: $E\text{-comb-taa}$ ($V_{\text{rel}}$) vs matching hygiene-only baseline ($V_{0h}$).
- **Statistical Testing**:
  - Paired bootstrap resampling ($N = 10,000$, seed 42) computing paired difference $\Delta$ and 95% bootstrap percentile confidence intervals.
  - Exact two-sided binomial sign test (`binomtest`) on discordant pairs for binary outcomes.
  - Multiplicity control: Holm step-down correction over the declared contrasts only.
- **Improvement Ladder Synthesis**:
  - Formally compile a unified cumulative progress table across evaluation stages:
    $$\text{raw RAGIntel} \longrightarrow +\text{hygiene} \longrightarrow +\text{domain routing} \longrightarrow +V_{\text{rel}} / V_{\text{rel}}\text{-T}$$
    reporting point estimates and 95% confidence intervals for each dataset.

## 12. Phase 6C Amendments: Generation Arms Implementation & Evaluation (Post-Hoc Round 3, 2026-10-24)

### 12.1 Generation Arms Declaration
- **Model & Configuration**: Locked strictly to `gemini-3.5-flash-lite`, temperature 0.0, `max_output_tokens` 512, bare prompt template identical to LLM-only and existing E0' arms.
- **Primary Arms ($B^* = 500$ tokens, 389 live calls)**:
  1. $E_0'\text{-HD-k200}$ on `cti-ate` ($N=60$), built from `results/phase_5/top200_hd_chunks.json.gz` via `truncate_to_token_budget(budget_tokens=500)`.
  2. $E_0'\text{-HD-k200}$ on `CTI-ATTACK` ($N=229$), built from `results/phase_5/top200_hd_chunks.json.gz` via `truncate_to_token_budget(budget_tokens=500)`.
  3. `cti-taa` $V_{0h}$ ($N=50$), built from top-10 chunks of `results/phase_5/o1_top10_cache.json` under body-only queries.
  4. `cti-taa` $V_{\text{rel}}$ ($N=50$), built from top-10 chunks of `results/phase_5/o1_top10_cache.json` under body-only queries with entity relationship expansion.
- **Secondary Arm (Next Quota Day)**:
  - $E_0'\text{-HD-k200}$ at $B = 2000$ tokens on `cti-ate` (60) and `CTI-ATTACK` (229), totaling 289 calls.
- **Evaluation Metrics & Contrasts**:
  - Technique Benchmarks: F1 (sub-technique credit and strict), precision, recall, abstention, empty, and truncation counts.
  - Threat Actor Attribution: Object-level accuracy (primary) and alias-aware match (Scorer V2).
  - Contrasts: Each arm vs existing LLM-only arm and vs matching raw-context arm, evaluated on identical rows.
  - Statistical Testing: Paired bootstrap (10,000 resamples, seed 42) and exact two-sided binomial sign test on discordant pairs.
  - Labeling: "post-hoc round 3, exploratory".

## 13. Phase 7 Amendments: Optimization 2 Redesign (Post-Hoc Round 4, 2026-10-24)

### 13.1 Methodological Governance
- **(R1) Pre-Registration**: Declared prior to execution in `analysis_plan.md` and registered with hash and timestamp in `results/phase_7/variants_ledger.json`.
- **(R2) Operational Constraints**: Offline execution only; thread cap 4; one heavy retrieval process at a time. No modification of frozen Phase 0–6 results.
- **(R3) Explicit Labeling**: Labeled strictly as "post-hoc round 4, exploratory".
- **(R4) Neutral Scientific Tone**: Strictly descriptive language; zero causal wording permitted.
- **(R5) Full Reporting & Transparency**: Report all evaluated variants, including negative outcomes and failures. Retain the original O2 negative result in the report as-is.

### 13.2 Part A: Diagnostics Protocol (Descriptive Only)
Evaluate across arms ($E_0'\text{-k200}$, $E_0'\text{-TECH-k200}$, $E_{1a}$, $E_1\text{-MIXED}$) on `cti-ate` ($N=60$) and `CTI-ATTACK` ($N=229$) at token budgets $B \in \{500, 1000\}$:
1. **Mean tokens per chunk**: Average token count of retrieved chunks entering the packed context.
2. **Share of chunks with technique ID**: Percentage of retrieved chunks whose text matches `T\d{4}(?:\.\d{3})?`.
3. **Mean distinct technique IDs per context**: Average count of unique parent technique IDs contained in the packed context per query.
4. **Mean chunks per context from the same technique**: Average ratio of chunks per distinct technique present in the packed context.

### 13.3 Part B: Redesigned Variants Specification
1. **$E_{1h}$ (Header-Prepended, Length-Capped Field Chunks)**:
   - Built over the same four ATT&CK technique fields as $E_{1a}$ (`identity_description`, `procedure_examples`, `mitigations`, `detection`).
   - Every chunk prepends a one-line header: `[<technique_id> <name> | <tactics>]`.
   - Each chunk is capped at exactly 150 tokens, split at sentence boundaries, with the one-line header repeated on every split chunk.
   - Mixed-corpus version $E_{1h}\text{-MIXED}$ combines $E_{1h}$ technique chunks with original splitter chunks for groups/software, analogous to $E_1\text{-MIXED}$.
2. **$E_{1h}\text{-div}$ (Diversity-Constrained Packing)**:
   - Applies post-retrieval diversity packing to $E_{1h}$: at most 2 chunks per technique ID are admitted to the context window before truncation at token budget $B$.
3. **Retrieval Pipeline**:
   - Both variants use query hygiene (body-only queries), domain routing for `cti-ate`, HybridSTIXRetriever (dense + BM25Okapi), FlashRank cross-encoder reranking, and a $k=200$ candidate pool.

### 13.4 Part C: Contrasts & Evaluation Protocol (Family P7, Holm $M=4$)
- **Target Datasets**: `cti-ate` ($N=60$) and `CTI-ATTACK` ($N=229$).
- **Primary Metric**: Mean Recall@$B$ across budgets $B \in \{500, 1000\}$ under sub-technique credit (`sub_credits_parent`).
- **Family P7 Contrasts ($M=4$)**:
  - $P7\_01$: $E_{1h}$ vs $E_0'\text{-TECH-k200}$ on `cti-ate`
  - $P7\_02$: $E_{1h}\text{-div}$ vs $E_0'\text{-TECH-k200}$ on `cti-ate`
  - $P7\_03$: $E_{1h}$ vs $E_0'\text{-TECH-k200}$ on `CTI-ATTACK`
  - $P7\_04$: $E_{1h}\text{-div}$ vs $E_0'\text{-TECH-k200}$ on `CTI-ATTACK`
- **Statistical Testing**:
  - Paired bootstrap resampling ($N = 10,000$, seed 42) reporting paired difference $\Delta$ and 95% bootstrap percentile confidence intervals.
  - Family-wise multiplicity control via Holm step-down correction at $\alpha = 0.05$ across $M=4$ contrasts.
  - Full 4-budget scaling table ($B \in \{500, 1000, 2000, 4000\}$) reporting binding flags alongside Phase 5 $E_{1a}$ and $E_1\text{-MIXED}$ baselines.

## 14. Phase 6D Amendments: Extended Round (Post-Hoc Round 3–4, Exploratory)

### 14.1 Methodological Governance & Operational Constraints
- **Date**: 2026-10-25
- **Status**: Formally pre-registered prior to Phase 6D computation in `analysis_plan.md` and `results/phase_6d/variants_ledger.json`.
- **Labeling**: Strictly designated as "post-hoc round 3–4, exploratory".
- **Tone**: Strictly descriptive; zero causal phrasing permitted.
- **Resource Limits**: Thread cap 4; strictly one heavy retrieval process at a time (API generation permitted in parallel).
- **Frozen Invariants**: Never change the model (`gemini-3.5-flash-lite`), temperature (`0.0`), `max_output_tokens` (`512`), existing prompts, or frozen results (Phases 0–6C).
- **Primary Metrics**:
  - Technique extraction (`cti-ate`, `CTI-ATTACK`): technique F1 sub_credit (primary); strict F1, precision, recall secondary.
  - Threat actor attribution (`cti-taa`): attribution v2_alias (primary); v1_exact, v1_alias, v2_exact secondary.
  - Retrieval: object-level Recall@10 and binding-mean Recall@$B$ (primary); MRR, nDCG secondary.
  - All arms reported, including neutral or negative outcomes.

### 14.2 Part A: Clean-Up & Multiplicity Control
1. **A1 (Section 4 Rewrite)**: Delete Section 4 of `REVIEW_PHASE_6C.md` (which contained causal interpretation) and replace with descriptive diagnostics from Part C. Fix `cti-taa` table labels.
2. **A2 (Missing Attribution Contrasts)**: Add contrasts on `cti-taa` for $V_{\text{rel}}$ vs $V_{0h}$ and $V_{0h}$ vs $V_0$ across all four scorers (v1_exact, v1_alias, v2_exact, v2_alias) reporting wins/ties/losses, paired bootstrap 95% CIs, and exact binomial sign test p-values.
3. **A3 (Multiplicity Control)**: Apply Holm step-down correction over the primary generation comparisons:
   - HD vs LLM-only on `cti-ate` (F1 sub_credit)
   - HD vs LLM-only on `CTI-ATTACK` (F1 sub_credit)
   - $V_{0h}$ vs LLM-only on `cti-taa` (v2_alias)
   - $V_{\text{rel}}$ vs $V_{0h}$ on `cti-taa` (v2_alias)

### 14.3 Part B: API Generation Extension (Pacing 5.0s, Cap 500 calls/day, Reset 07:00 UTC)
Live generation evaluated across declared priority arms:
1. **D1 ($B=2000$ Token Scaling)**: $E_0'\text{-HD-k200}$ at budget $B=2000$ tokens using bare prompt on `cti-ate` ($N=60$) and `CTI-ATTACK` ($N=229$), totaling 289 calls.
2. **D2a (Hybrid Prompt at $B^*=500$)**:
   - Prompt verbatim: `"Use the provided context if it is relevant; otherwise use your own knowledge. List the MITRE technique IDs."` on $E_0'\text{-HD-k200}$ for `cti-ate` ($N=60$).
   - For `cti-taa`: `"...attribute the incident to a threat group."` on $V_{0h}$ ($N=50$) and $V_{\text{rel}}$ ($N=50$), totaling 160 calls.
3. **D3 (O2 End-to-End)**: $E_{1h}\text{-MIXED}$ + HD preprocessing at budget $B^*=500$ tokens with bare prompt on `cti-ate` ($N=60$) and `CTI-ATTACK` ($N=229$), totaling 289 calls.
4. **D2b (Hybrid Prompt on `CTI-ATTACK`)**: Hybrid prompt at $B^*=500$ tokens on $E_0'\text{-HD-k200}$ for `CTI-ATTACK` ($N=229$).
5. **D4 (Optional Scaling)**: Hybrid prompt at $B=2000$ tokens on `cti-ate` ($N=60$) if quota remains.
6. **Contrasts**: Each arm compared against `LLM-only` and against matching Phase 6C arm using paired bootstrap (10,000 resamples, seed 42) and exact sign tests.

### 14.4 Part C: Descriptive Diagnostics Protocol
Descriptive inspection for $E_0'$ (raw), $E_0'\text{-HD-k200}$, $E_{1h}$, and `LLM-only` on `cti-ate` and `CTI-ATTACK`:
1. Mean predicted technique count.
2. Mean distinct technique IDs and chunks entering context.
3. Context recall (share of ground-truth techniques present in retrieved context).
4. Abstention, empty, and truncation counts.
5. Per-query Spearman rank correlation between context recall and generation F1.
6. Verification that domain filter is applied to Mobile rows of `cti-ate`.

### 14.5 Part D: B1 Retriever Robustness (Long-Context Embedding Baseline)
Evaluate long-context embedding baseline B1 on:
1. `cti-taa`: $V_0$, $V_{0h}$, and $V_{\text{rel}}$.
2. `cti-ate` and `CTI-ATTACK`: $E_0'$ (raw) vs $E_0'\text{-HD-k200}$.
3. Report whether hygiene and $V_{\text{rel}}$ differences preserve sign and magnitude under dense long-context retrieval (retrieval metrics only).

### 14.6 Part E: Secondary KB Replication (`E0-STIX-ENT`)
Repeat retrieval contrasts for query hygiene ($V_{0h}$) and relationship expansion ($V_{\text{rel}}$) over `E0-STIX-ENT` (Enterprise STIX only) across `cti-taa`, `cti-ate`, and `CTI-ATTACK` under baselines B2 and B3.

### 14.7 Part F: Second Generator Model Pre-Declaration
1. **Selection Rule (Pre-declared)**: Newest Gemma or Flash-Lite model returned by API model listing that is not `gemini-3.5-flash-lite`.
2. **Evaluation Arm**: Run on `cti-taa` ($N=50$) across `LLM-only`, $V_0$, $V_{0h}$, $V_{\text{rel}}$ (200 calls), bare prompt, temperature 0.0, max output tokens 512.
3. **Assessment**: Evaluate whether the relative ranking of arms replicates.

### 14.8 Part G: Deterministic Case Studies Protocol
Deterministic, script-generated case studies on `cti-taa` without manual curation:
1. Select the first 5 rows by `row_idx` where $V_{\text{rel}}$ wins over $V_{0h}$, and first 3 rows where $V_{\text{rel}}$ loses to $V_{0h}$.
2. Print query ID, ground truth, detected software, top-3 voted groups, presence of ground-truth group in context, and model output.
3. Assert that all printed text spans exist verbatim within the query text.

### 14.9 Part H: Reporting & Reproducibility
- Compile unified report in `reviews/REVIEW_PHASE_6D.md` with assertion-verified tables, numerical difference summaries, daily API usage logs, and complete documentation of any skipped items.
- Update `docs/REPRODUCE.md` and freeze manifest with newly generated artifacts without modifying historic hashes.

---

## 15. Phase 6E: Offline Fix Round & Methodological Reconciliation (2026-10-25)

**Governance**: Strictly offline execution. Thread cap 4. Zero modification to `api_runner.py` or frozen results (Phases 0–6B). Strictly descriptive scientific language; zero causal assertions.

### 15.1 Retrieval Metric Reconciliation Protocol
Define and distinguish two distinct retrieval coverage metrics:
1. **`Recall@B (sub_credits_parent)`**: Evaluates structured retrieval chunks truncated to token budget $B$ using chunk metadata (`mitre_id`). A ground-truth technique is scored as retrieved if either its exact ID or its parent technique ID is present in the metadata of any chunk in the context window.
2. **`Context Recall (GT)`**: Evaluates surface text coverage across the verbatim prompt string passed to the generator. Matches technique IDs via regex (`T\d{4}(?:\.\d{3})?`) and computes the fraction of exact ground-truth IDs present in the text, without parent credit.
Both metrics are recomputed across exact context files for $E_0'$ (raw), $E_0'\text{-HD-k200}$, and $E_{1h}$ on `cti-ate` and `CTI-ATTACK` at $B=500$ tokens, explicitly explaining any numerical divergence (e.g., 0.2042 vs 0.0517).

### 15.2 $V_{\text{rel}}$ Generation Noise Floor Stratification (`cti-taa`)
Stratify the 50 `cti-taa` generation queries into two disjoint subsets based on whether relationship expansion modified the retrieved prompt context relative to $V_{0h}$:
- **Active Stratum**: Queries where retrieved contexts for $V_{\text{rel}}$ and $V_{0h}$ differ.
- **Inactive Stratum**: Queries where retrieved contexts for $V_{\text{rel}}$ and $V_{0h}$ are identical.
Report $V_{\text{rel}}$ and $V_{0h}$ accuracy and W/T/L for each stratum. For inactive queries, quantify the run-to-run response variation (frequency of differing model outputs given identical prompt contexts at temperature 0.0).

### 15.3 Arm Labeling & Leakage Caveats
1. Relabel Priority Arm D3 as: `"E1h-MIXED structure-aware chunks (header-prefixed field chunks), no entities"`.
2. Remove unprincipled plain list summaries ("Improved / Not improved / Unchanged") unless formally governed by a pre-declared decision rule.
3. Apply the formal leakage caveat (`"KB-lookup upper bound; not evidence of generalization to unseen reports"`) to all Enterprise STIX (`E0-STIX-ENT`) `cti-ate` $V_{\text{rel}}$ evaluations.

### 15.4 Missing Statistical Contrasts Protocol
Compute paired bootstrap (10,000 resamples, seed 42) and exact two-sided binomial sign tests for:
1. **D1 ($B=2000$) vs raw $E_0'$ ($B=500$)** on `cti-ate` and `CTI-ATTACK`.
2. **Second Generator (`gemini-3.1-flash-lite`) `cti-taa` Arms**: Paired contrasts for all arm pairs ($V_{\text{rel}}$ vs $V_{0h}$, $V_{0h}$ vs $V_0$, $V_{\text{rel}}$ vs $V_0$, $V_{\text{rel}}$ vs `LLM-only`, $V_{0h}$ vs `LLM-only`).
3. **Rephrase Replicability**: Describe second generator ranking alignment as: *"same direction; gaps of 1–3 queries"*.
4. **D3 vs `LLM-only` on `CTI-ATTACK`**: Document as pending completion of remaining generation calls following quota replenishment.

### 15.5 Unified Query Hygiene Summary Table
Compile a single comparative matrix of the query hygiene effect on `cti-ate` and `CTI-ATTACK` across four evaluation regimes:
1. Recall@B common budgets (Phase 5).
2. Enterprise STIX (`E0-STIX-ENT`) Recall@10 under B2 and B3.
3. Long-context dense embedding (`nomic-ai/nomic-embed-text-v1.5`, 8k context) Recall@10 without chunking (B1).
4. Live generation technique F1 (Phase 6C).
Classify each cell as positive ($+$), null ($0$), or negative ($-$).

### 15.6 Quota Accounting Protocol
Reconcile call logs to show exact successful and rate-limited calls per model per UTC day. Clarify that the 998 successful calls on `gemini-3.5-flash-lite` on 2026-10-25 represent calls served across the 07:00 UTC daily quota reset boundary (391 pre-reset + 607 post-reset), rather than a single static 500-call quota bucket.

### 15.7 Detector Failure Case Study: Polysemy Collision
Document Case 26 ("Soldier" matching SysUpdate) within the limitations section using descriptive terminology: the token "Soldier" in an Iranian threat report matched the STIX alias for Chinese malware SysUpdate, injecting Threat Group-3390 context and illustrating entity detector homonym vulnerability.

---

## 16. Phase 6F: Corrections and Rigor Audits (2026-10-26)

**Governance**: Strictly offline execution. Thread cap 4. Zero modification to `api_runner.py` or frozen results (Phases 0–6B). Strictly descriptive scientific language; zero causal assertions.

### 16.1 Statistical Correction: Holm Family Exact Sign Test
1. Correct the statistical test input for the primary generation Holm family (GEN_01 to GEN_04). The previously reported raw p-values ($p=0.0014$ on `cti-ate`, $p=0.0001$ on `CTI-ATTACK`) reflected paired bootstrap p-values rather than the pre-registered exact two-sided binomial sign test p-values derived from discordant pair counts.
2. Under exact two-sided sign tests:
   - `GEN_02` (CTI-ATTACK HD vs LLM-only, W/T/L 44/102/83, discordant $N=127$): exact sign $p = 0.00068 \le 0.0125$ (Rank 1). **Rejects null hypothesis** (favors LLM-only).
   - `GEN_01` (`cti-ate` HD vs LLM-only, W/T/L 18/6/36, discordant $N=54$): exact sign $p = 0.0198 > 0.0167$ (Rank 2). **Fails to reject null hypothesis** (not statistically significant under Holm step-down correction).
   - `GEN_03` (`cti-taa` $V_{0h}$ vs LLM-only, W/T/L 7/37/6): exact sign $p = 1.0000 > 0.025$ (Rank 3). Fails to reject null.
   - `GEN_04` (`cti-taa` $V_{\text{rel}}$ vs $V_{0h}$, W/T/L 3/45/2): exact sign $p = 1.0000 > 0.050$ (Rank 4). Fails to reject null.
3. Update all text and decision citations across reports to state that `GEN_01` is not statistically significant under Holm step-down correction ($0.0198 > 0.0167$).

### 16.2 Regenerated Hygiene Summary Table & Metric Reconciliation
1. Regenerate the unified Hygiene Summary Table directly from source CSVs (`secondary_kb_contrasts.csv`, `b1_robustness_contrasts.csv`, `contrasts_table.csv`, `table_ladder_common_budgets.csv`, `retrieval_reconciliation_b500.csv`) with programmatic cell assertions.
2. In the Enterprise STIX (`E0-STIX-ENT`) regime, report exact primary metric `Subtech_Recall@10` values:
   - B2: control 0.0895, treatment 0.0813, delta $-0.0082$ ($p=0.1516$).
   - B3: control 0.1221, treatment 0.0811, delta $-0.0410$ ($p=0.0037$).
3. Explicitly reconcile Phase 5 `cti-ate` $+0.1525$ vs the balanced ladder $+0.0849$:
   - $+0.1525$ represents single-budget $B=500$ evaluation that confounds query hygiene with candidate pool expansion ($k=50 \to k=200$, control 0.0517 vs treatment 0.2042).
   - $+0.0849$ represents isolated query hygiene evaluated across balanced common token budgets $\{500, 1000\}$ with candidate pool fixed at $k=50$ (control 0.1601 vs treatment 0.2450).

### 16.3 Metadata-Credit Audit
1. For $E_0'$ raw, $E_0'\text{-HD-k200}$, and $E_{1h}$ across `cti-ate` and `CTI-ATTACK` at $B=500$, report Recall@500 under:
   - (a) Structured metadata credit (`sub_credits_parent`).
   - (b) Text-visible surface regex on verbatim prompt strings (`contexts_used`).
2. Document that under (b), the retrieval hygiene delta on `cti-ate` is smaller/null ($-0.0125$), and state in the claims table: *"retrieval gains do not carry to technique-F1 generation (+0.013 / +0.012, n.s.)."*

### 16.4 Noise Strata & Inactive Win Reclassification (`cti-taa`)
1. Recount active vs inactive strata over all 50 `cti-taa` queries with a full boolean ledger of `context_identical`.
2. Confirm that Cases 22 and 41 have empty entity detection / identical contexts between $V_{0h}$ and $V_{\text{rel}}$, so their nominal generation wins belong strictly to the inactive stratum ($N=16$).
3. Report reconciled W/T/L:
   - Under `v2_alias`: Active ($N=34$) W/T/L = 2/31/1; Inactive ($N=16$) W/T/L = 1/14/1.
   - Under `v1_exact`: Active ($N=34$) W/T/L = 3/29/2; Inactive ($N=16$) W/T/L = 2/12/2.
4. Establish that 100% of inactive queries (16/16) exhibit run-to-run lexical variation at temperature 0.0.

### 16.5 Aggregate Case Studies & Generic OS Binary Stoplist
1. Replace hand-picked case study selections with aggregate statistics over all 50 `cti-taa` queries:
   - Share with non-empty vote list: 68.0% (34/50).
   - Share with ground-truth in top-3 votes: 0.0% (0/50).
   - Share with ground-truth in context: 28.0% (14/50).
   - Stratified W/T/L counts by vote list presence, top-3 presence, and context presence.
2. Retain Case 26 ("Soldier" homonym matching SysUpdate) as a descriptive failure mode and detector limitation.
3. Test a stoplist targeting generic OS binaries (`cmd.exe`, `schtasks.exe`, `ipconfig`, `netstat`, `net`, `systeminfo`, `ftp`, `ping`, etc.):
   - Report that 22.0% of queries (11/50) alter detection.
   - Quantify shifts in group voting candidates and resulting prompt context.

### 16.6 Wording & Quota Corrections
1. Update D2a reporting text to: `'-0.0677 vs LLM-only on cti-ate (bootstrap CI [-0.117,-0.020], exact sign p=0.081)'`.
2. Update quota notes to state observed per-window maximum ($\ge 607$ successful calls) and remove all references to a "nominal 500" cap.

### 16.7 Ground-Truth Alias Leakage Audit (`cti-taa`)
1. Scan all 50 `cti-taa` query bodies (excluding instruction text) for exact word-boundary appearances of any ground-truth threat group alias (canonical or STIX alias, length $\ge 4$, case-insensitive).
2. Report total leaked query count (10/50, 20.0%) and list affected query indices (Rows 1, 22, 23, 26, 37, 38, 40, 42, 48, 49).
3. Re-score retrieval and generation for $V_0$, $V_{0h}$, and $V_{\text{rel}}$ on the clean subset ($N=40$) alongside full-50 numbers.

### 16.8 Knowledge Base Integrity Audit
1. Audit all objects across `enterprise-attack.json`, `mobile-attack.json`, and `ics-attack.json` whose `external_id` deviates from standard ATT&CK conventions.
2. Enumerate all 66 S9000-series objects (S9000–S9067). Document their provenance as extended STIX entries created between December 2025 and October 2026.
3. Audit usage: verify that 0 S9000-series objects appeared in retrieved prompt contexts sent to the LLM; document that 40 objects participate in `software_to_groups` graph links, with 1 detection in `cti-taa` (Query 6, `SystemBC` -> S9001) that did not affect context or attribution outcome.

### 16.9 Entity Detector Precision Audit (`results/phase_4b/detector_labels.csv`)
1. Ingest labeled 100-sample detector matches (`results/phase_4b/detector_labels.csv`).
2. Report baseline D0 precision: 74.0% for real entity mentions (74/100) and 63.0% for informative attribution mentions (63/100).
3. Evaluate D1/V1h survival filtering (drop length $\le 4$, drop common words/commands, retain intrusion-set and malware only): 65.0% survival rate (65/100), with 76.9% real precision (50/65) and 76.9% informative precision (50/65).
4. Categorize false positive error sources: (1) Template instruction examples (11/26, 42.3%), (2) Common English words / file extensions / homonyms (7/26, 26.9%), (3) Generic OS utilities (8/26, 30.8%).

