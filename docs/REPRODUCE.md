# Reproduction Guide: RAGIntel Benchmark

This document provides exact commands, expected outputs, runtime benchmarks, and environmental requirements to independently reproduce all evaluations, test suites, statistical assertions, and report tables in this repository.

> **Hardware & Environment Note**: All retrieval benchmarks, statistical evaluations, bootstrap resampling routines, and offline verification scripts execute **entirely on standard CPU hardware**. No GPU acceleration is required.

---

## 1. System Requirements & Environment Setup

- **Python Version**: Python 3.12 (recommended) or 3.11.
- **Operating System**: Linux (Ubuntu 22.04+), macOS (13+), or Windows 10/11.
- **RAM**: Minimum 8.0 GB RAM (resident memory consumption is capped below 2.5 GB via batched execution).

### Step 1.1: Clone and Create Virtual Environment
```bash
git clone https://github.com/rohanreddy3/RAGIntel.git
cd RAGIntel

# Create and activate virtual environment
python -m venv venv

# On Linux / macOS:
source venv/bin/activate

# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
```

### Step 1.2: Install Pinned Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 2. Verification Suite: Bit-Exact Consistency (Offline)

All experimental results, statistical tests, bootstrap confidence intervals, and publication tables are completely frozen under `results/` and verified by automated tools. **Zero external API calls are made during verification.**

### Step 2.1: Run the Source-of-Truth Verifier
The verifier re-derives every claim cell (deltas, 95% bootstrap CIs, W/T/L discordant pairs, binomial sign test $p$-values, Fisher exact tests) directly from raw per-query CSV/JSON files, asserts table cell equivalence against `claims_master.csv`, and cross-checks LaTeX `.tex` tables against Markdown `.md` tables.

```bash
python scripts/verify_master.py
```

**Expected Output**:
```
===========================================================================
VERIFICATION SUMMARY: 97 PASSED, 0 FAILED (TOTAL 97 CHECKS)
===========================================================================
ALL CHECKS PASSED PERFECTLY. ZERO DISCREPANCIES.
```
- **Runtime**: ~3–5 seconds.

### Step 2.2: Run the Unit & Integration Test Suite
The repository includes 52 unit and regression tests covering deterministic retrieval, STIX parsing, metric evaluation, prompt formatting, and tokenizer boundaries.

```bash
python -m pytest
```

**Expected Output**:
```
============================== 52 passed in ~130s ==============================
```
- **Runtime**: ~2 minutes (CPU only).

---

## 3. Rebuilding Publication Tables & Assets

To programmatically re-extract all data from raw `results/phase_*` files and regenerate `results_for_report/` (Markdown tables, LaTeX tables, figure data CSVs, and `claims_master.csv`):

```bash
python scripts/build_results_master.py
```

**Outputs Regenerated**:
- `results_for_report/RESULTS_MASTER.md`
- `results_for_report/data/claims_master.csv`
- `results_for_report/tables/T1_datasets` (`.csv`, `.md`, `.tex`)
- `results_for_report/tables/T2_arms` (`.csv`, `.md`, `.tex`)
- `results_for_report/tables/T3_main_results` (`.csv`, `.md`, `.tex`)
- `results_for_report/tables/T4_statistical_tests` (`.csv`, `.md`, `.tex`)
- `results_for_report/tables/T5_detector_precision` (`.csv`, `.md`, `.tex`)
- `results_for_report/tables/T6_benchmark_defects` (`.csv`, `.md`, `.tex`)
- `results_for_report/figures/F1_hygiene_effect` (`.csv`, `.png`, `.svg`)
- `results_for_report/figures/F2_cti_taa_clean40` (`.csv`, `.png`, `.svg`)
- `results_for_report/figures/F3_leakage` (`.csv`, `.png`, `.svg`)
- `results_for_report/figures/F4_metadata_credit` (`.csv`, `.png`, `.svg`)
- `results_for_report/figures/F5_rag_vs_llm_only` (`.csv`, `.png`, `.svg`)

- **Runtime**: ~5 seconds.

---

## 4. Bidirectional Credit Sensitivity Analysis (CRIT-02)

To recompute the parent/subtechnique bidirectional credit scoring on saved model generation outputs for `cti-ate` and `CTI-ATTACK`:

```bash
python scripts/compute_phase6l_bidirectional_sensitivity.py
```

**Expected Output**:
- Outputs saved to `results/phase_6l/bidirectional_sensitivity.csv` and `.json`.
- Confirms that relative model rankings on `CTI-ATTACK` remain 100% invariant (LLM-only > D1 > HD > E0').
- **Runtime**: ~2 seconds.

---

## 5. Live LLM Generation Note (API Optional)

All live generation responses (`gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`) are archived and cryptographically frozen under:
- `results/phase_6c/`
- `results/phase_6d/`
- `results/phase_6l/`

**You do NOT need a Google Gemini API key to verify or reproduce the results in this paper.** The tables and tests load from these frozen outputs.

If you wish to execute new live generation queries against the Google Gemini API:
1. Create a `.env` file containing:
   ```env
   GEMINI_API_KEY=your_api_key_here
   ```
2. Execute the runner:
   ```bash
   python scripts/api_runner.py --phase6c
   ```
*(Note: Never commit `.env` or API keys. `.env` is strictly ignored by `.gitignore`.)*

---

## 6. Cryptographic Freeze Manifest Verification

To verify that the offline results directory matches the frozen release snapshot:
```bash
python -c "
import json, hashlib
from pathlib import Path

manifest = json.loads(Path('results/freeze_manifest.json').read_text())
verified, missing, mismatched = 0, 0, 0
for rel_path, meta in manifest['files'].items():
    p = Path(rel_path)
    if not p.is_file():
        missing += 1
        continue
    raw_hash = hashlib.sha256(p.read_bytes()).hexdigest()
    text_content = p.read_bytes().replace(b'\r\n', b'\n')
    norm_hash = hashlib.sha256(text_content).hexdigest()
    if norm_hash == meta.get('sha256') or raw_hash == meta.get('raw_sha256'):
        verified += 1
    else:
        mismatched += 1
print(f'Freeze manifest verified: {verified} bit-exact, {missing} missing/ignored, {mismatched} mismatched.')
"
```
