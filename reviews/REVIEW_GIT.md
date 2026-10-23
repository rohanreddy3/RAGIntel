# REVIEW_GIT: Publication of RAGIntel to GitHub

- **Date / Timestamp**: 2026-10-23T04:32:00Z
- **Repository Remote URL**: [https://github.com/rohanreddy3/RAGIntel.git](https://github.com/rohanreddy3/RAGIntel.git)
- **Target Branch**: `main`
- **Commit Hash**: `4775850`
- **Commit Message**: `Initial commit: RAGIntel optimization project (code, results, reviews)`
- **Push Status**: Successfully pushed (`main -> main`, tracking `origin/main`)

---

## 1. Safety & Secret Audit

- **`.env` Safety**: Verified `.env` exists locally and is strictly ignored.
  - Checked with `git ls-files | Select-String '\.env$'`: **0 results** (not tracked).
  - Created `.env.example` containing only placeholder `GOOGLE_API_KEY=your_key_here`.
- **`.cache/` Safety**: Verified `.cache/` is strictly ignored.
  - Checked with `git ls-files | Select-String '\.cache'`: **0 results**.
- **Secret Scanner Execution**:
  - Scanned all project files across directories for secret patterns (`AIza...`, `api_key=...`, `GOOGLE_API_KEY=...`, `sk-...`).
  - **Candidate / Tracked Files**: **0 secret hits**.
  - Excluded raw MITRE STIX bundles (`data/mitre/ics-attack.json`, `data/mitre/mobile-attack.json`) contained attack description strings matching generic regex patterns; these files were excluded from tracking by `.gitignore` (`data/mitre/*.json`).
  - No secrets or keys are committed, logged, or printed.

---

## 2. Size & Excluded Files Audit

- **Files Excluded by Size (> 25 MB)**:
  1. `results/phase_3/top50_phase3c_chunks.json` (195.05 MB) — Added to `.gitignore`
  2. `results/phase_3/top50_ranked_chunks.json` (113.51 MB) — Added to `.gitignore`
  3. `data/mitre/enterprise-attack.json` (45.73 MB) — Excluded by `data/mitre/*.json` rule
- **External & Reference Material Excluded**:
  - `vendor/` (contains embedded clone repository)
  - `base paper/` (contains external PDF publication, 7.69 MB)
  - `base_paper_extracted.txt`

### Top 20 Largest Files Committed (All < 25 MB)
1. `results/phase_2/p1_eval_checkpoint.json` (10.13 MB)
2. `results/phase_3/o2_phase3c_benchmark_results.json` (8.99 MB)
3. `results/phase_2/v3_seeds_b3_results.json` (1.72 MB)
4. `results/phase_3/e1_mixed_no_siblings_contexts_b500.json` (1.32 MB)
5. `results/phase_3/e1b_mixed_contexts_b500.json` (1.32 MB)
6. `results/phase_3/o2_benchmark_results.json` (0.67 MB)
7. `results/phase_4/detected_examples_audit.json` (0.56 MB)
8. `scratch/sample_100_docs_20_queries.json` (0.33 MB)
9. `results/phase_2/o1_benchmark_results.json` (0.29 MB)
10. `data/datasets/cti-taa.xlsx` (0.22 MB)
11. `results/phase_2/phase2_corrections_data.json` (0.16 MB)
12. `reviews/api_ledger.csv` (0.12 MB)
13. `results/phase_4/per_query_technique_f1.csv` (0.10 MB)
14. `scripts/generate_final_assets.py` (0.05 MB)
15. `results/phase_0/dataset_schemas.json` (0.05 MB)
16. `reviews/REVIEW_PHASE_2.md` (0.04 MB)
17. `results/phase_4/per_query_cti_taa_attribution.csv` (0.04 MB)
18. `scripts/api_runner.py` (0.04 MB)
19. `results/phase_1/retrieval_metrics_cti_attack.csv` (0.03 MB)
20. `scripts/compute_phase3c_controls.py` (0.03 MB)

---

## 3. Commit & Repository Accounting

- **Total Committed Size**: **27.20 MB** (28,519,300 bytes) — well below the 150 MB ceiling.
- **Total Committed Files**: **171 files**.

### Breakdown by Top-Level Folder
| Folder / Item | File Count | Size |
|---|:---:|:---|
| `results/` | 61 | 25.66 MB |
| `scripts/` | 41 | 0.44 MB |
| `scratch/` | 19 | 0.37 MB |
| `reviews/` | 10 | 0.28 MB |
| `data/` | 4 | 0.27 MB |
| `src/` | 13 | 0.08 MB |
| `tests/` | 11 | 0.04 MB |
| `report/` | 4 | 0.02 MB |
| `analysis_plan.md` | 1 | 0.02 MB |
| `config.yaml` | 1 | 4.84 KB |
| `docs/` | 1 | 4.20 KB |
| `README.md` | 1 | 2.44 KB |
| `requirements.txt` | 1 | 2.17 KB |
| `config_generation.yaml` | 1 | 749 bytes |
| `.gitignore` | 1 | 497 bytes |
| `.env.example` | 1 | 29 bytes |
| **Total** | **171** | **27.20 MB** |

---

## 4. Verification Commands & Outputs

```powershell
# Verified total tracked files
(git ls-files).Count
# Output: 171

# Verified commit history
git log -n 1 --oneline
# Output: 4775850 Initial commit: RAGIntel optimization project (code, results, reviews)

# Verified .env is untracked
(git ls-files | Select-String '\.env$').Count
# Output: 0

# Verified remote tracking
git status
# Output:
# On branch main
# Your branch is up to date with 'origin/main'.
# nothing to commit, working tree clean
```

---

## 5. Problems Encountered

- **None**: Git Credential Manager authenticated automatically. All files cleanly committed and pushed to `https://github.com/rohanreddy3/RAGIntel.git` on branch `main`.
- **Running Processes**: No processes were stopped or modified. `api_runner.py` remains active.
