# REVIEW REPORT: PHASE 0

### 1. Phase & Status
- **Phase**: Phase 0 — Setup & Data
- **Status**: DONE

---

### 2. What Was Built
- `vendor/RAGIntel/`: Cloned original RAGIntel repository (unmodified base system).
- `data/mitre/enterprise-attack.json`: MITRE ATT&CK Enterprise STIX 2.1 knowledge base bundle (45.73 MB, 26,085 objects).
- `data/datasets/cti-ate.xlsx`: Adversary Technique Extraction benchmark dataset (60 samples).
- `data/datasets/cti-taa.xlsx`: Threat Actor Attribution benchmark dataset (50 samples).
- `data/datasets/CTI-ATTACK.xlsx`: Technique Pattern Extraction benchmark dataset (229 samples).
- `.env.example`: Environment variable template for credentials (`OPENAI_API_KEY`, seeds).
- `.gitignore`: Git exclusion rules for virtual environments, secrets, caches, and checkpoints.
- `config.yaml`: Central experiment configuration with flags for E0–E3, matched budget, dataset, and LLM.
- `requirements.txt`: 115 pinned Python package versions.
- `src/__init__.py`: Package root initialization.
- `src/config.py`: Configuration dataclass, loader, schema validator, and deterministic seed setter (`set_seed`).
- `src/data_loader.py`: Benchmark dataset and STIX bundle parsing and validation engine.
- `scripts/download_stix.py`: Script to download and cryptographically verify MITRE STIX bundle.
- `scripts/inspect_datasets.py`: Automated schema inspection and distribution analysis script.
- `tests/test_config.py`: Unit tests for config loading, ablation flags (E0–E3), and determinism.
- `tests/test_data_loader.py`: Unit tests for dataset loaders, schemas, and STIX entities.
- `results/phase_0/stix_metadata.json`: Machine-readable metadata of the STIX knowledge base.
- `results/phase_0/dataset_schemas.json`: Full schema and distribution JSON for all datasets.
- `results/phase_0/schema_report.md`: Markdown summary report of schemas and statistics.
- `logs/phase_0.log`: Sequential command execution log for Phase 0.
- `reviews/REVIEW_PHASE_0.md`: Formal phase review report.

---

### 3. Commands Run (Exact) and Where Raw Outputs Are Saved
1. `git clone https://github.com/AbeerAlhuthali/RAGIntel.git vendor/RAGIntel`
   - Output: `vendor/RAGIntel/`
2. `python -m venv venv`
   - Output: `venv/`
3. `python scripts/download_stix.py 2>&1 | Tee-Object -FilePath logs/phase_0.log -Append`
   - Raw output: `logs/phase_0.log`, `results/phase_0/stix_metadata.json`
4. `Copy-Item vendor/RAGIntel/*.xlsx -Destination data/datasets/ -Verbose`
   - Raw output: `data/datasets/`
5. `./venv/Scripts/python.exe -m pip install pandas openpyxl pyyaml pytest python-dotenv requests tqdm`
   - Raw output: `logs/phase_0.log`
6. `./venv/Scripts/python.exe -m pip install rank_bm25 faiss-cpu torch transformers sentence-transformers flashrank ragas==0.2.13 langchain langchain-community langchain-openai scikit-learn`
   - Raw output: `logs/phase_0.log`
7. `./venv/Scripts/python.exe -m pip freeze | Out-File -Encoding utf8 requirements.txt`
   - Raw output: `requirements.txt`
8. `./venv/Scripts/python.exe scripts/inspect_datasets.py 2>&1 | Tee-Object -FilePath logs/phase_0.log -Append`
   - Raw output: `logs/phase_0.log`, `results/phase_0/dataset_schemas.json`, `results/phase_0/schema_report.md`
9. `./venv/Scripts/python.exe -m pytest tests/ -v 2>&1 | Tee-Object -FilePath logs/phase_0.log -Append`
   - Raw output: `logs/phase_0.log`

---

### 4. Results (Tables with Real Numbers Only)

#### Environment & Seed
- **OS**: Windows (AMD64)
- **Python**: 3.13.1
- **Random Seed**: 42 (pinned across Python, NumPy, PyTorch, and CUDA)
- **Pinned Dependencies**: 115 packages (including `torch==2.14.1`, `faiss-cpu==1.15.1`, `ragas==0.2.13`, `langchain==1.4.4`, `flashrank==0.2.10`, `sentence-transformers==6.1.0`)

#### STIX Knowledge Base
- **File**: `data/mitre/enterprise-attack.json`
- **File Size**: 47,953,963 bytes (45.732 MB)
- **SHA-256 (Recorded)**: `f7eaf37fe53b50404084fe1fe67237278f7317e61c11ad550295722d13ede259`
- **Total STIX Objects**: 26,085

| Object Type | Count | Role in Thesis |
| :--- | :--- | :--- |
| `relationship` | 21,262 | Graph connections (uses, mitigates, subtechnique-of) |
| `x-mitre-analytic` | 1,758 | Detection analytics |
| `attack-pattern` | 858 | Techniques/sub-techniques for structure-aware chunking (O2) |
| `malware` | 733 | Malware catalog |
| `x-mitre-detection-strategy` | 699 | Detection strategies |
| `course-of-action` | 268 | Mitigations |
| `intrusion-set` | 191 | Threat actors & aliases for entity resolution (O1) (191 canonical groups mapped) |
| `x-mitre-data-component` | 109 | Data components |
| `tool` | 95 | Software tools |
| `campaign` | 56 | Threat campaigns |
| `x-mitre-data-source` | 38 | Data sources |
| `x-mitre-tactic` | 15 | ATT&CK tactics |
| `x-mitre-matrix` / `identity` / `marking-definition` | 3 | Bundle metadata |

#### Benchmark Dataset Schema Measurements

| Dataset Key | File Name | Sheet Name | Rows | Columns | Null Count (%) | Word Length (Min / Mean / Max) | Ground Truth Entity Type |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **CTI-ATE** | `cti-ate.xlsx` | `Sheet1` | 60 | 2 (`query`, `ground_truth`) | 0 (0.0%) | Query: 63 / 168.2 / 545<br>GT: 1 / 6.6 / 19 | MITRE Technique IDs (`TXXXX`, 397 total) |
| **CTI-TAA** | `cti-taa.xlsx` | `Sheet1` | 50 | 2 (`query`, `ground_truth`) | 0 (0.0%) | Query: 225 / 1,626.5 / 4,051<br>GT: 1 / 3.6 / 16 | Threat Group Names & Aliases (`SideCopy`, `Stately Taurus (alias Bronze President)`, etc.) |
| **CTI-ATTACK** | `CTI-ATTACK.xlsx` | `CTI-ATTACK` | 229 | 2 (`query`, `ground_truth`) | 0 (0.0%) | Query: 53 / 62.0 / 99<br>GT: 1 / 1.2 / 3 | MITRE Technique IDs (`TXXXX`, 262 total) |

---

### 5. Tests
- **Count Passed**: 13
- **Count Failed**: 0
- **Total**: 13
- **Execution Time**: 13.52s
- **Command to rerun**:
  ```powershell
  ./venv/Scripts/python.exe -m pytest tests/ -v
  ```

---

### 6. Deviations from the Plan and Why
- **PowerShell Encoding**: Default output redirection (`>`) in PowerShell writes UTF-16LE, which created an encoding mismatch for pip requirements. Handled by piping through `Out-File -Encoding utf8`.
- **Sheet Name Discrepancy**: `CTI-ATTACK.xlsx` uses the sheet name `"CTI-ATTACK"` rather than `"Sheet1"`. `src/data_loader.py` was implemented with explicit per-dataset sheet configuration to prevent sheet load failures.

---

### 7. Problems, Anomalies, or Suspicious Results (Blunt)
- **Corpus Format in Baseline**: In `vendor/RAGIntel/rag_cti.py`, `main()` loads raw HTML files using `load_html_files(html_directory)` with `UnstructuredHTMLLoader`. The project prompt specifies the knowledge base as the MITRE ATT&CK Enterprise STIX bundle (`enterprise-attack.json`). In Phase 1 reproduction, we must verify whether RAGIntel's baseline was indexed over the MITRE enterprise STIX objects converted to text or crawled HTML pages, to ensure apples-to-apples baseline reproduction.
- **Extreme Query Length in CTI-TAA**: `cti-taa.xlsx` queries average 1,626 words (~11,400 chars) and reach up to 4,051 words (~29,100 chars). When paired with retrieved context documents, standard 4k context windows would overflow; `gpt-4o-mini` handles 128k tokens, but strict token counting and budgeting are required to maintain the fairness rule across ablation arms.
- **Ground Truth Disparity**: `cti-taa.xlsx` contains group names and natural language aliases in `ground_truth` (e.g. `SideCopy`, `Stately Taurus (alias Bronze President)`), whereas `cti-ate.xlsx` and `CTI-ATTACK.xlsx` contain comma-separated technique IDs (`T1071, T1573`). This confirms why O1 (Entity Resolution) applies strictly to `CTI-TAA`.

---

### 8. Limitations of What Was Measured
- Phase 0 measured file schemas, STIX object distributions, package installations, and loader correctness.
- No LLM generation or embedding retrieval was executed in this phase; retrieval performance and RAGAS scores will be measured in Phase 1.

---

### 9. Blockers / Things Needed from User
- **OpenAI API Key**: Required for Phase 1 baseline reproduction (to invoke `gpt-4o-mini` / `gpt-3.5-turbo` and compute RAGAS metrics).
  - Please set `OPENAI_API_KEY` in your environment or populate `.env` (copied from `.env.example`).

---

### 10. Recommended Next Step and Risks for the Next Phase
- **Recommended Next Step**: Phase 1 — Baseline Reproduction (E0):
  1. Build a clean wrapper in `src/ragintel_wrapper.py` around `vendor/RAGIntel/rag_cti.py` to run unmodified E0 baseline on `cti-ate`, `cti-taa`, and `CTI-ATTACK`.
  2. Index the knowledge base and run retrieval + reranking + LLM inference.
  3. Compute RAGAS metrics (Context Precision, Context Recall, Faithfulness, Factual Correctness, Answer Relevancy).
  4. Compare measured metrics against published paper numbers.
- **Risks for Next Phase**:
  - API rate limits or cost during bulk LLM generation and RAGAS evaluation (339 total dataset rows across all 3 benchmarks).
  - Discrepancy between HTML corpus splitting and STIX object indexing if the paper's original HTML crawl is not identical to the STIX descriptions.
