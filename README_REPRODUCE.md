# Reproducibility Guide: RAGIntel Benchmark and Evaluation Suite

This guide provides complete instructions to set up the environment, run benchmark evaluation pipelines, execute offline scoring and statistical reconciliation, generate all writing assets, and verify reproducibility via automated unit tests.

---

## 1. Environment & Prerequisites

### 1.1 System Requirements
- **Operating System**: Windows 10/11, Ubuntu 22.04 LTS, or macOS 13+
- **Python Version**: Python 3.10 to 3.13 (verified on Python 3.13.1)
- **Disk Space**: ~3 GB (STIX bundle, embeddings cache, benchmark datasets)
- **RAM**: Minimum 8 GB (16 GB recommended for FAISS dense retrieval)

### 1.2 Python Environment Setup
```bash
# 1. Clone the repository
git clone https://github.com/rohanreddy3/RAGIntel.git
cd RAGIntel

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Linux / macOS:
source venv/bin/activate

# 4. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install matplotlib tabulate
```

---

## 2. API Key Configuration & Offline Mode

### 2.1 What Needs an API Key vs What is 100% Offline
| Workflow Stage | Requires API Key? | Notes |
| :--- | :---: | :--- |
| **STIX KB Parsing & Indexing** | **NO** | Purely local parsing of `data/mitre/enterprise-attack.json` |
| **Retrieval Evaluations (Phases 1–3, 5, 6B, 6D)** | **NO** | Local BM25, FAISS (MiniLM), and FlashRank reranking |
| **Cached Generation Analysis & Reconciliations** | **NO** | Evaluates pre-computed responses in `.cache/api_runner/` |
| **Attribution Scorer ($V_1$, $V_{0h}$, $V_{\text{rel}}$)** | **NO** | Local STIX relationship graph parsing & alias regex |
| **Report Assets Generation (`results_for_report/`)** | **NO** | 100% offline generation of figures and tables |
| **Freeze Manifest Dry-Run** | **NO** | Local SHA-256 integrity verification |
| **Unit Test Suite (`pytest`)** | **NO** | 100% offline unit tests |
| **Live API Generation (`scripts/api_runner.py --run`)** | **YES** | Dispatches requests to Gemini API |

> [!CAUTION]
> **API Key Security**: NEVER print, log, or commit API keys. Store keys strictly in a local `.env` file (which is git-ignored):
> ```env
> GEMINI_API_KEY="your_api_key_here"
> ```

---

## 3. Step-by-Step Execution Guide

### Step 1: Run Full Unit Test Suite (Offline)
Verifies that knowledge base loaders, chunking logic, configuration managers, and determinism guards operate correctly.
```bash
python -m pytest tests/
```
- **Expected Output**: `52 passed in ~2.5 minutes` (all unit tests passing).
- **Runtime**: ~2.5 minutes (CPU embedding and retriever determinism checks).

---

### Step 2: Knowledge Base & Retrieval Benchmarks (Offline)
Runs retrieval over `cti-ate`, `CTI-ATTACK`, and `cti-taa` across BM25, dense 8k embeddings, and hybrid STIX search.
```bash
# 1. Balanced ladder retrieval evaluation (Phase 6B)
python scripts/run_phase6b_balanced_eval.py

# 2. Secondary KB and Enterprise STIX evaluation (Phase 6D)
python scripts/compute_phase6d_part_e_enterprise_stix.py
python scripts/compute_phase6d_part_d_b1_robustness.py
```
- **Expected Outputs**:
  - `results/phase_6b/balanced_ladder_metrics.json`
  - `results/phase_6d/secondary_kb_evaluations.json`
  - `results/phase_6d/b1_robustness_metrics.json`
- **Runtime**: ~5–8 minutes.

---

### Step 3: Threat Actor Attribution & Leakage Audit (Offline)
Evaluates threat actor attribution on `cti-taa`, runs the ground-truth alias leakage audit, and computes the Clean-40 benchmark.
```bash
# 1. GT Alias leakage audit
python scripts/audit_gt_alias_leakage.py

# 2. Clean-40 primary benchmark calculation
python scratch/compute_clean40_table.py
```
- **Expected Outputs**:
  - `results/phase_6d/gt_alias_leakage_audit.json` (confirms exactly 10 leaked queries = 20.0%)
  - Clean-40 contrasts with exact binomial sign tests and bootstrap CIs
- **Runtime**: ~1–2 minutes.

---

### Step 4: Statistical Reconciliations & Quality Audits (Offline)
Executes all corrections, p-value certifications, detector audits, and quota accountings.
```bash
# 1. Phase 6F corrections
python scripts/compute_phase6f_corrections.py

# 2. Phase 6G corrections & true raw control reconciliation
python scripts/compute_phase6g_corrections.py
```
- **Expected Outputs**:
  - `results/phase_6d/phase6g_corrections.json`
  - `results/phase_6d/hygiene_summary_table.json` (certified with true raw controls and p=0.0002)
- **Runtime**: ~30 seconds.

---

### Step 5: Generate All Publication Assets (Figures & Tables)
Generates high-resolution figures (PNG 300 dpi and SVG), LaTeX and Markdown tables, source data CSVs, and `RESULTS_MASTER.md`.
```bash
python scripts/generate_all_writing_assets.py
```
- **Expected Outputs in `results_for_report/`**:
  - `results_for_report/figures/`:
    - `F1_hygiene_effect.png`, `.svg`, `.csv`, `.caption.txt`
    - `F2_cti_taa_clean40.png`, `.svg`, `.csv`, `.caption.txt`
    - `F3_leakage.png`, `.svg`, `.csv`, `.caption.txt`
    - `F4_metadata_credit.png`, `.svg`, `.csv`, `.caption.txt`
    - `F5_rag_vs_llm_only.png`, `.svg`, `.csv`, `.caption.txt`
  - `results_for_report/tables/`:
    - `T1_datasets.md`, `.tex`
    - `T2_arms.md`, `.tex`
    - `T3_main_results.md`, `.tex`
    - `T4_statistical_tests.md`, `.tex`
    - `T5_detector_precision.md`, `.tex`
    - `T6_benchmark_defects.md`, `.tex`
  - `results_for_report/data/`: Complete source CSV for every figure and table.
  - `results_for_report/captions.md`: One-line captions mapping each asset to claims.
  - `results_for_report/RESULTS_MASTER.md`: Master claim ledger.
- **Runtime**: ~15 seconds.

---

### Step 6: Freeze Manifest Dry-Run (Integrity Verification)
Runs the freeze manifest integrity audit without modifying the frozen baseline `results/freeze_manifest.json`.
```bash
python scripts/dryrun_freeze_manifest.py
```
- **Expected Output**:
  - Writes dry run to `results/freeze_dryrun/freeze_manifest_dryrun.json`
  - Reports exactly 3 modified files (`analysis_plan.md`, `hygiene_summary_table.csv`, `hygiene_summary_table.json`)
  - Confirms zero regressions in 163 historic frozen result files.
- **Runtime**: ~5 seconds.

---

## 4. Total Computational Budget & Runtime Summary
| Pipeline Stage | Compute Mode | Wall-Clock Time | External Network / API |
| :--- | :--- | :---: | :---: |
| **Unit Tests** | Local CPU | ~2.5 min | None (0 calls) |
| **Retrieval Benchmarks** | Local CPU / FAISS | ~6 min | None (0 calls) |
| **Attribution & Leakage** | Local CPU | ~2 min | None (0 calls) |
| **Statistical Reconciliation** | Local CPU | ~30 sec | None (0 calls) |
| **Asset Generation (F1–F5, T1–T6)** | Local CPU (Matplotlib) | ~15 sec | None (0 calls) |
| **Freeze Dry-Run** | Local CPU | ~5 sec | None (0 calls) |
| **Total Full Reproduction** | **Offline Local** | **~11.5 min** | **Zero API Calls** |
