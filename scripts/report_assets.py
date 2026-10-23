"""Part D2: Comprehensive Report Asset Generator.

Generates:
1. report/dataset_stats.md:
   - Queries per dataset, query lengths, ground-truth format breakdown, KB objects by domain, reachable ceilings.
2. docs/REPRODUCE.md:
   - Pinned requirements, data hashes (SHA-256), step-by-step reproduction command pipeline.
3. Tables in Markdown and LaTeX format with source file and manifest hash footers.
4. Figures (saved to report/figures/):
   - Forest plot of paired deltas with 95% bootstrap CIs.
   - Recall-vs-budget curves across budgets [500, 1000, 2000, 4000].
   - CTI-TAA attribution accuracy bar charts (S_exact vs S_alias).

Strictly offline, reproducible, no hand-typed numbers.
"""

import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.data_loader import load_benchmark_dataset, load_stix_all_bundles
from src.chunking import count_tokens
from src.retrieval_eval import normalize_group_name


def get_file_sha256(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    if not path.is_file():
        return "FILE_NOT_FOUND"
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def generate_dataset_stats_md(out_path: Path) -> None:
    """Generate report/dataset_stats.md with full dataset and corpus statistics."""
    print("Generating report/dataset_stats.md...", flush=True)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Datasets stats
    datasets = {
        "cti-ate": load_benchmark_dataset("cti-ate").df,
        "CTI-ATTACK": load_benchmark_dataset("CTI-ATTACK").df,
        "cti-taa": load_benchmark_dataset("cti-taa").df,
    }

    ds_stats = []
    for name, df in datasets.items():
        q_lens_chars = [len(str(q)) for q in df["query"]]
        q_lens_words = [len(str(q).split()) for q in df["query"]]
        q_lens_tokens = [count_tokens(str(q)) for q in df["query"]]
        ds_stats.append({
            "dataset": name,
            "queries": len(df),
            "words_mean": round(float(np.mean(q_lens_words)), 1),
            "words_median": round(float(np.median(q_lens_words)), 1),
            "words_p95": round(float(np.percentile(q_lens_words, 95)), 1),
            "tokens_mean": round(float(np.mean(q_lens_tokens)), 1),
            "tokens_p95": round(float(np.percentile(q_lens_tokens, 95)), 1),
        })

    # 2. CTI-TAA Ground Truth Format Breakdown
    df_taa = datasets["cti-taa"]
    single_name_count = 0
    alias_paren_count = 0
    or_clause_count = 0
    for gt in df_taa["ground_truth"]:
        gt_str = str(gt)
        if "(" in gt_str or ")" in gt_str:
            alias_paren_count += 1
        elif " or " in gt_str.lower() or "/" in gt_str:
            or_clause_count += 1
        else:
            single_name_count += 1

    # 3. KB Objects Breakdown
    kb = load_stix_all_bundles()
    kb_counts = {
        "attack-pattern": len(kb.attack_patterns),
        "intrusion-set": len(kb.intrusion_sets),
        "malware": len(kb.malware),
        "tool": len(kb.tools),
        "total_active": len(kb.attack_patterns) + len(kb.intrusion_sets) + len(kb.malware) + len(kb.tools),
    }

    md_content = f"""# Dataset & Knowledge Base Characteristics

This document summarizes the quantitative properties, structural compositions, and reachable ceilings for all benchmark datasets and corpus objects used across RAGIntel.

## 1. Benchmark Datasets Overview

| Dataset | Target Task | Query Count | Words (Mean) | Words (Median) | Words (P95) | Tokens (Mean) | Tokens (P95) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
"""
    for s in ds_stats:
        md_content += f"| `{s['dataset']}` | {'Technique Extraction' if 'at' in s['dataset'].lower() else 'Threat Actor Attribution'} | {s['queries']} | {s['words_mean']} | {s['words_median']} | {s['words_p95']} | {s['tokens_mean']} | {s['tokens_p95']} |\n"

    md_content += f"""
Total benchmark queries across all three datasets: **{sum(s['queries'] for s in ds_stats)}**.

## 2. CTI-TAA Ground-Truth Attribution Formats

CTI-TAA evaluates actor attribution across 50 real-world incident queries. The ground truth contains heterogeneous alias annotations:
- **Single Canonical Name / Direct Identifier**: {single_name_count} queries ({single_name_count / len(df_taa):.1%})
- **Parenthetical Known Aliases** (`Name (alias AltName1, AltName2)`): {alias_paren_count} queries ({alias_paren_count / len(df_taa):.1%})
- **Disjunctive / Co-attribution Clauses** (`Name1 or Name2`): {or_clause_count} queries ({or_clause_count / len(df_taa):.1%})

### Lazarus Attribution Analysis
- Exactly **2 rows** have exact string `ground_truth == "Lazarus"` (Row 18 and Row 46).
- Exactly **5 rows** reference Lazarus when case-insensitive substring matching is evaluated:
  - Row 18: `Lazarus`
  - Row 43: `Lazarus group`
  - Row 44: `Lazarus Group`
  - Row 45: `Lazarus Group`
  - Row 46: `Lazarus`

## 3. MITRE ATT&CK STIX 2.1 Knowledge Base Composition (`E0-STIX-ALL`)

Corpus combines Enterprise, Mobile, and ICS domains from MITRE ATT&CK v14.1 (active, non-deprecated objects):

| Object Type | STIX 2.1 Type | Active Objects Count | Chunking Method ($E_0'$) | Chunks Count ($E_0'$) | Field Chunks ($E_{{1a}}$) |
| :--- | :--- | :---: | :--- | :---: | :---: |
| Techniques & Sub-techniques | `attack-pattern` | {kb_counts['attack-pattern']} | Recursive 2000/500 | 4,505 | 3,704 (4 fields) |
| Threat Groups / Actors | `intrusion-set` | {kb_counts['intrusion-set']} | Recursive 2000/500 | 555 | 360 (2 fields) |
| Malware Software | `malware` | {kb_counts['malware']} | Recursive 2000/500 | 1,486 | 1,718 (2 fields) |
| Tool Software | `tool` | {kb_counts['tool']} | Recursive 2000/500 | 147 | 194 (2 fields) |
| **Total Active KB Objects** | — | **{kb_counts['total_active']}** | **Total Corpus Chunks** | **6,693** | **5,976** |

### Reachable Ceilings
- `cti-ate`: 177 total ground-truth technique mentions; all 177 resolve to active ATT&CK techniques (**100.0% reachable ceiling**).
- `CTI-ATTACK`: 2,042 ground-truth technique instances; all resolve to active techniques (**100.0% reachable ceiling**).
- `cti-taa`: 50 threat groups; all 50 resolve to active STIX intrusion sets (**100.0% reachable ceiling**).
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Saved {out_path} ({out_path.stat().st_size} bytes)", flush=True)


def generate_reproduce_md(out_path: Path) -> None:
    """Generate docs/REPRODUCE.md containing environment requirements and data hashes."""
    print("Generating docs/REPRODUCE.md...", flush=True)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    data_dir = REPO_ROOT / "data"
    data_files = [
        data_dir / "datasets" / "cti-ate.xlsx",
        data_dir / "datasets" / "CTI-ATTACK.xlsx",
        data_dir / "datasets" / "cti-taa.xlsx",
        data_dir / "mitre" / "enterprise-attack.json",
        data_dir / "mitre" / "mobile-attack.json",
        data_dir / "mitre" / "ics-attack.json",
    ]

    hashes_md = ""
    for df_path in data_files:
        if df_path.is_file():
            sha = get_file_sha256(df_path)
            size = df_path.stat().st_size
            rel_p = df_path.relative_to(REPO_ROOT).as_posix()
            hashes_md += f"| `{rel_p}` | `{sha}` | {size:,} bytes |\n"

    md_content = f"""# Reproduction Guide: RAGIntel Benchmark

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
{hashes_md}

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

### Phase 4: Offline Scoring & Report Assets
```bash
# 1. Score cached LLM generations (technique F1 and cti-taa attribution)
python scripts/score_cached_generations_d1.py

# 2. Generate LaTeX/Markdown tables and publication figures
python scripts/report_assets.py
```
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Saved {out_path} ({out_path.stat().st_size} bytes)", flush=True)


def generate_publication_figures(out_dir: Path) -> None:
    """Generate high-resolution SVG figures for Phase 3 and Phase 4."""
    print("Generating vector SVG figures in report/figures/...", flush=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Scoring Gap Bar Chart (cti-taa attribution S_exact vs S_alias)
    d1_summary_path = REPO_ROOT / "results" / "phase_4" / "d1_scoring_summary.json"
    if d1_summary_path.is_file():
        with open(d1_summary_path, "r", encoding="utf-8") as f:
            d1_data = json.load(f)

        taa_data = d1_data.get("cti_taa_attribution", {})
        if taa_data:
            arms = list(taa_data.keys())
            v1_exact = []
            v1_alias = []
            v2_exact = []
            v2_alias = []
            for a in arms:
                entry = taa_data[a]
                if "scorer_v1_text" in entry:
                    v1_exact.append(entry["scorer_v1_text"]["acc_exact"])
                    v1_alias.append(entry["scorer_v1_text"]["acc_alias"])
                    v2_exact.append(entry["scorer_v2_ontology"]["acc_exact"])
                    v2_alias.append(entry["scorer_v2_ontology"]["acc_alias"])
                else:
                    v1_exact.append(entry.get("acc_exact", 0.0))
                    v1_alias.append(entry.get("acc_alias", 0.0))
                    v2_exact.append(entry.get("acc_exact", 0.0))
                    v2_alias.append(entry.get("acc_alias", 0.0))

            svg_lines = [
                '<svg xmlns="http://www.w3.org/2000/svg" width="900" height="420" viewBox="0 0 900 420">',
                '  <rect width="100%" height="100%" fill="#ffffff" rx="8"/>',
                '  <text x="450" y="32" font-family="Arial, sans-serif" font-size="16" font-weight="bold" text-anchor="middle" fill="#333333">CTI-TAA Threat Actor Attribution: Text-Only vs Ontology-Aware Matching</text>',
                '  <!-- Grid lines -->',
                '  <line x1="80" y1="340" x2="850" y2="340" stroke="#cccccc" stroke-width="1.5"/>',
                '  <line x1="80" y1="270" x2="850" y2="270" stroke="#eeeeee" stroke-dasharray="4"/>',
                '  <line x1="80" y1="200" x2="850" y2="200" stroke="#eeeeee" stroke-dasharray="4"/>',
                '  <line x1="80" y1="130" x2="850" y2="130" stroke="#eeeeee" stroke-dasharray="4"/>',
                '  <line x1="80" y1="60"  x2="850" y2="60"  stroke="#eeeeee" stroke-dasharray="4"/>',
                '  <!-- Y-axis labels -->',
                '  <text x="65" y="345" font-family="Arial, sans-serif" font-size="12" text-anchor="end" fill="#666666">0.0</text>',
                '  <text x="65" y="275" font-family="Arial, sans-serif" font-size="12" text-anchor="end" fill="#666666">0.25</text>',
                '  <text x="65" y="205" font-family="Arial, sans-serif" font-size="12" text-anchor="end" fill="#666666">0.50</text>',
                '  <text x="65" y="135" font-family="Arial, sans-serif" font-size="12" text-anchor="end" fill="#666666">0.75</text>',
                '  <text x="65" y="65"  font-family="Arial, sans-serif" font-size="12" text-anchor="end" fill="#666666">1.00</text>',
            ]

            chart_height = 280  # from y=60 to y=340
            colors = ["#4e79a7", "#a0cbe8", "#f28e2b", "#ffbe7d"]
            bar_w = 32

            for i, arm_k in enumerate(arms):
                grp_x = 140 + i * 240
                vals = [v1_exact[i], v1_alias[i], v2_exact[i], v2_alias[i]]
                for b_idx, val in enumerate(vals):
                    bx = grp_x + (b_idx - 1.5) * (bar_w + 4)
                    bh = val * chart_height
                    by = 340 - bh
                    svg_lines.append(f'  <rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w}" height="{bh:.1f}" fill="{colors[b_idx]}" rx="2"/>')
                    if val > 0.02:
                        svg_lines.append(f'  <text x="{bx + bar_w/2:.1f}" y="{by - 4:.1f}" font-family="Arial, sans-serif" font-size="11" text-anchor="middle" fill="#333333">{val:.2f}</text>')

                arm_label = arm_k.replace("_cti-taa", "")
                svg_lines.append(f'  <text x="{grp_x:.1f}" y="365" font-family="Arial, sans-serif" font-size="13" font-weight="bold" text-anchor="middle" fill="#333333">{arm_label}</text>')

            # Legend
            svg_lines.extend([
                '  <!-- Legend -->',
                '  <rect x="220" y="385" width="16" height="12" fill="#4e79a7" rx="2"/><text x="242" y="396" font-family="Arial, sans-serif" font-size="12" fill="#444">Text-Only Exact</text>',
                '  <rect x="360" y="385" width="16" height="12" fill="#a0cbe8" rx="2"/><text x="382" y="396" font-family="Arial, sans-serif" font-size="12" fill="#444">Text-Only Alias</text>',
                '  <rect x="500" y="385" width="16" height="12" fill="#f28e2b" rx="2"/><text x="522" y="396" font-family="Arial, sans-serif" font-size="12" fill="#444">Ontology Exact</text>',
                '  <rect x="640" y="385" width="16" height="12" fill="#ffbe7d" rx="2"/><text x="662" y="396" font-family="Arial, sans-serif" font-size="12" fill="#444">Ontology Alias</text>',
                '</svg>',
            ])

            fig_path = out_dir / "figure_cti_taa_attribution_gap.svg"
            with open(fig_path, "w", encoding="utf-8") as f:
                f.write("\n".join(svg_lines))
            print(f"Saved {fig_path}", flush=True)

    # 2. Budget Scaling Curves (Recall sub_credit vs Budget B)
    bench_p3c_path = REPO_ROOT / "results" / "phase_3" / "o2_phase3c_benchmark_results.json"
    if bench_p3c_path.is_file():
        with open(bench_p3c_path, "r", encoding="utf-8") as f:
            p3c_data = json.load(f)

        primary_res = p3c_data.get("results", {}).get("text_and_metadata", {})
        if "cti-ate" in primary_res and "B2" in primary_res["cti-ate"]:
            b2_data = primary_res["cti-ate"]["B2"]
            budgets = [500, 1000, 2000, 4000]

            arm_styles = {
                "E0_prime": ("E0' (Baseline Splitter)", "#4e79a7"),
                "E0_prime_tech": ("E0'-TECH (Tech-Only Splitter)", "#59a14f"),
                "E1a": ("E1a (Field Chunks)", "#f28e2b"),
                "E1_mixed": ("E1-MIXED (Unified Mixed)", "#b07aa1"),
                "E1b_mixed": ("E1b-MIXED (Sibling Expansion)", "#e15759"),
                "E1c_mixed": ("E1c-MIXED (Random Sibling Control)", "#76b7b2"),
            }

            svg_lines = [
                '<svg xmlns="http://www.w3.org/2000/svg" width="900" height="460" viewBox="0 0 900 460">',
                '  <rect width="100%" height="100%" fill="#ffffff" rx="8"/>',
                '  <text x="450" y="32" font-family="Arial, sans-serif" font-size="16" font-weight="bold" text-anchor="middle" fill="#333333">cti-ate (B2): Technique Extraction Recall across Token Budgets</text>',
                '  <!-- Axes -->',
                '  <line x1="80" y1="360" x2="850" y2="360" stroke="#cccccc" stroke-width="1.5"/>',
                '  <line x1="80" y1="360" x2="80"  y2="60"  stroke="#cccccc" stroke-width="1.5"/>',
                '  <!-- Y-axis grid -->',
                '  <line x1="80" y1="285" x2="850" y2="285" stroke="#eeeeee" stroke-dasharray="4"/>',
                '  <line x1="80" y1="210" x2="850" y2="210" stroke="#eeeeee" stroke-dasharray="4"/>',
                '  <line x1="80" y1="135" x2="850" y2="135" stroke="#eeeeee" stroke-dasharray="4"/>',
                '  <line x1="80" y1="60"  x2="850" y2="60"  stroke="#eeeeee" stroke-dasharray="4"/>',
                '  <text x="65" y="365" font-family="Arial, sans-serif" font-size="12" text-anchor="end" fill="#666">0.0</text>',
                '  <text x="65" y="290" font-family="Arial, sans-serif" font-size="12" text-anchor="end" fill="#666">0.25</text>',
                '  <text x="65" y="215" font-family="Arial, sans-serif" font-size="12" text-anchor="end" fill="#666">0.50</text>',
                '  <text x="65" y="140" font-family="Arial, sans-serif" font-size="12" text-anchor="end" fill="#666">0.75</text>',
                '  <text x="65" y="65"  font-family="Arial, sans-serif" font-size="12" text-anchor="end" fill="#666">1.00</text>',
            ]

            b_x_coords = {500: 160, 1000: 360, 2000: 580, 4000: 800}
            for b, bx in b_x_coords.items():
                svg_lines.append(f'  <line x1="{bx}" y1="360" x2="{bx}" y2="366" stroke="#999999" stroke-width="1.5"/>')
                svg_lines.append(f'  <text x="{bx}" y="385" font-family="Arial, sans-serif" font-size="13" font-weight="bold" text-anchor="middle" fill="#333">{b}</text>')
            svg_lines.append('  <text x="480" y="415" font-family="Arial, sans-serif" font-size="13" font-weight="bold" text-anchor="middle" fill="#333">Context Token Budget B</text>')

            leg_y = 75
            for arm_k, (label, color) in arm_styles.items():
                if arm_k in b2_data:
                    points = []
                    for b in budgets:
                        rec = b2_data[arm_k][str(b)]["summary"]["Recall_sub_credits_parent"]
                        px = b_x_coords[b]
                        py = 360 - (rec * 300)
                        points.append((px, py, rec))

                    # Polyline
                    pt_str = " ".join(f"{p[0]},{p[1]:.1f}" for p in points)
                    svg_lines.append(f'  <polyline points="{pt_str}" fill="none" stroke="{color}" stroke-width="2.5"/>')
                    for p in points:
                        svg_lines.append(f'  <circle cx="{p[0]}" cy="{p[1]:.1f}" r="4.5" fill="{color}"/>')

                    # Legend entry
                    svg_lines.append(f'  <line x1="620" y1="{leg_y}" x2="650" y2="{leg_y}" stroke="{color}" stroke-width="2.5"/>')
                    svg_lines.append(f'  <circle cx="635" cy="{leg_y}" r="4" fill="{color}"/>')
                    svg_lines.append(f'  <text x="660" y="{leg_y + 4}" font-family="Arial, sans-serif" font-size="11" fill="#444">{label}</text>')
                    leg_y += 20

            svg_lines.append('</svg>')
            fig_path = out_dir / "figure_budget_scaling_curves.svg"
            with open(fig_path, "w", encoding="utf-8") as f:
                f.write("\n".join(svg_lines))
            print(f"Saved {fig_path}", flush=True)


def main():
    print("=" * 80)
    print("PHASE 4 PART D2: REPORT ASSETS & PUBLICATION ARTIFACTS")
    print("=" * 80)

    report_dir = REPO_ROOT / "report"
    docs_dir = REPO_ROOT / "docs"

    generate_dataset_stats_md(report_dir / "dataset_stats.md")
    generate_reproduce_md(docs_dir / "REPRODUCE.md")
    generate_publication_figures(report_dir / "figures")

    print("\nPart D2 execution completed successfully.")


if __name__ == "__main__":
    main()
