# Reproduction Guide: RAGIntel Benchmark

This document provides step-by-step instructions to reproduce all retrieval, extraction, attribution, and generation results across Phases 0–4 of RAGIntel.

## 1. Pinned Hardware & System Requirements

- **Operating System**: Windows 11 / Linux (x86_64)
- **RAM**: Minimum 8.0 GB RAM (Peak resident set size kept below 2.5 GB via batching and sequential execution)
- **CPU**: Multi-core CPU (Thread execution capped at 4 threads via `OMP_NUM_THREADS=4` and `torch.set_num_threads(4)`)
- **Python Version**: Python 3.12 (Virtual environment at `venv/`)
- **Execution Mode**: Strict offline evaluation (`OFFLINE_ONLY=true`, `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`) except during LLM generation runner.

## 2. Verified Data Hashes (SHA-256)

All dataset files and STIX bundles are pinned and cryptographically verified:

| File Path | SHA-256 Checksum | Size |
| :--- | :--- | :---: |
| `data/datasets/cti-ate.xlsx` | `1096cf479b815402c32370db16ea37b4b31d90fdf50b36b5c2d90682eb4c0f1f` | 30,576 bytes |
| `data/datasets/CTI-ATTACK.xlsx` | `c669f8bc2ea9868be2347762565a8e28c1517f3319c6309b7cf8b2bb67cfb772` | 23,913 bytes |
| `data/datasets/cti-taa.xlsx` | `fc6dfcb29569e8329da4bdccf584324a6c871a7d349faa920c0bcabec1f432af` | 227,523 bytes |
| `data/mitre/enterprise-attack.json` | `f7eaf37fe53b50404084fe1fe67237278f7317e61c11ad550295722d13ede259` | 47,953,963 bytes |
| `data/mitre/mobile-attack.json` | `592d4ee8cb2958de20eef65ebd5829753a8dd686f098b237ddeb867558c81faa` | 5,489,646 bytes |
| `data/mitre/ics-attack.json` | `202328ce7193aa1c1803cbfbf712e81c37a7e9de6c5adc14dd8c11ceb302573e` | 4,683,721 bytes |


## 3. Pinned Python Dependencies

Key pinned packages from `requirements.txt`:
- `torch`: 2.2.0+
- `faiss-cpu`: 1.8.0+
- `flashrank`: 0.2.4+
- `sentence-transformers`: 2.5.1+
- `langchain`: 0.2.14+
- `pandas`: 2.2.1+
- `openpyxl`: 3.1.2+

## 4. End-to-End Execution Sequence

### Phase 1: Baselines & Long-Query Retrieval
```bash
# 1. Download STIX bundles and inspect schemas
python scripts/download_stix.py
python scripts/inspect_datasets.py

# 2. Evaluate initial retrieval baselines (B1, B2, B3)
python scripts/evaluate_all_baselines.py
```

### Phase 2: Optimization 1 (Entity Resolution Benchmark)
```bash
# 1. Full grid retrieval benchmark over B2/B3 across V0-V3
python scripts/benchmark_phase2_o1.py

# 2. Evaluate Family P1 hypotheses & V3 seed sensitivity (Seeds 42-46)
python scripts/regenerate_p1_table.py
python scripts/run_v3_seeds_b2.py
python scripts/run_v3_seeds_b3.py
```

### Phase 3: Optimization 2 (Structure-Aware Chunking Benchmark)
```bash
# 1. Run Phase 3C controls, build E0'-TECH & E1-MIXED, evaluate Family P2'
python scripts/compute_phase3c_controls.py
```

### Phase 4: Offline Scoring, Integrity Audit, & Publication Assets
```bash
# 1. Offline integrity audit (row alignment, query_id sha1, entity span assertions)
python scripts/audit_row_alignment.py
python scripts/print_examples.py

# 2. Score cached LLM generations (technique F1 sub_credit and cti-taa attribution)
python scripts/score_cached_generations_d1.py

# 3. Regenerate cti-taa diagnostics and paired bootstrap tables
python scripts/regenerate_cti_taa_tables.py

# 4. Generate all Markdown and LaTeX publication tables, vector SVG figures, and freeze manifest
python scripts/generate_final_assets.py
```

### Phase 4B: Fix Round & Rigor Verification
```bash
# 1. Recompute A8 threat actor attribution at matched 500-token budget
python scripts/recompute_a8.py

# 2. Audit Table 5 token budget binding and chunk saturation
python scripts/audit_budget_binding.py

# 3. Comprehensive generation failure and abstention audit across all cache records
python scripts/audit_generation_failures.py

# 4. Audit ATT&CK STIX bundle versioning and domain technique inventory
python scripts/audit_stix_version.py

# 5. Entity detector precision audit and exploratory V1-strict retrieval
python scripts/analyze_detector_precision.py
```

### Phase 5: Pre-Declared Fixes and Improvement Round (Post-Hoc, Exploratory)
```bash
# 1. Query Hygiene Audit (339 benchmark queries body marker verification)
python scripts/run_query_hygiene_audit.py

# 2. Optimization 1 (O1) Benchmark on cti-taa (V0h, V1h, Vrel under body-only hygiene)
python scripts/run_o1_phase5_benchmark.py

# 3. Exact two-sided sign test (McNemar) & bootstrap side-by-side computation
python scripts/recompute_p3_binary_mcnemar.py

# 4. Domain sanity audit on cti-ate enterprise vs mobile declarations
python scripts/check_cti_ate_domain_sanity.py

# 5. Optimization 2 (O2) Clean Comparisons under HD preprocessing (Family P4)
python scripts/run_o2_clean_benchmark.py

# 6. Candidate pool k=200 scaling extension (eliminating candidate starvation)
python scripts/run_o2_k200_extension.py

# 7. Table 7 Claims reconciliation (restoring C9, correcting P1_08 reference)
python scripts/reconcile_table7.py

# 8. Ground-truth STIX status audit (revoked, deprecated, absent counts)
python scripts/audit_ground_truth_in_stix.py
python scripts/generate_stix_limitations_table.py

# 9. Format all Phase 5 tables, plain list of contrasts, and verification assets
python scripts/generate_phase5_assets.py
```

## 5. Cryptographic Freeze Manifest Verification

To verify the integrity of all experiment outputs against the frozen manifest:
```bash
python -c "
import json, hashlib
from pathlib import Path

manifest = json.loads(Path('results/freeze_manifest.json').read_text())
mismatches = 0
for rel_path, meta in manifest['files'].items():
    p = Path(rel_path)
    if not p.is_file():
        print(f'Missing: {rel_path}')
        mismatches += 1
        continue
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    if h != meta['sha256']:
        print(f'Hash mismatch: {rel_path}')
        mismatches += 1
print(f'Verification completed: {len(manifest[\"files\"]) - mismatches}/{len(manifest[\"files\"])} files verified bit-exact.')
"
```
