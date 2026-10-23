"""Dataset and STIX Schema Inspector for RAG CTI Thesis Project.
Inspects real file schemas, column names, null counts, and data distributions.
Saves detailed JSON and Markdown reports to results/phase_0/.
"""

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd


def get_file_stats(filepath: str) -> Dict[str, Any]:
    p = Path(filepath)
    hasher = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(1024 * 1024):
            hasher.update(chunk)
    return {
        "filename": p.name,
        "path": str(p),
        "size_bytes": p.stat().st_size,
        "size_mb": round(p.stat().st_size / (1024 * 1024), 3),
        "sha256": hasher.hexdigest(),
    }


def inspect_excel_dataset(filepath: str, dataset_key: str) -> Dict[str, Any]:
    stats = get_file_stats(filepath)
    excel_file = pd.ExcelFile(filepath)
    sheet_names = excel_file.sheet_names

    sheets_data = {}
    for sheet in sheet_names:
        df = pd.read_excel(filepath, sheet_name=sheet)
        col_info = []
        for col in df.columns:
            non_null = int(df[col].notna().sum())
            null_count = int(df[col].isna().sum())
            sample_vals = [
                str(v) if pd.notna(v) else None
                for v in df[col].dropna().head(3).tolist()
            ]
            col_info.append({
                "column_name": str(col),
                "dtype": str(df[col].dtype),
                "non_null_count": non_null,
                "null_count": null_count,
                "null_percentage": round(null_count / max(1, len(df)) * 100, 2),
                "samples": sample_vals,
            })

        # Check for query and ground truth characteristics
        text_stats = {}
        for candidate_col in ["query", "ground_truth", "text", "label", "Technique", "Group"]:
            for actual_col in df.columns:
                if candidate_col.lower() in str(actual_col).lower():
                    series = df[actual_col].dropna().astype(str)
                    lengths = series.apply(len)
                    words = series.apply(lambda x: len(x.split()))
                    text_stats[actual_col] = {
                        "count": len(series),
                        "char_len_min": int(lengths.min()) if not lengths.empty else 0,
                        "char_len_max": int(lengths.max()) if not lengths.empty else 0,
                        "char_len_mean": round(float(lengths.mean()), 1) if not lengths.empty else 0,
                        "word_count_min": int(words.min()) if not words.empty else 0,
                        "word_count_max": int(words.max()) if not words.empty else 0,
                        "word_count_mean": round(float(words.mean()), 1) if not words.empty else 0,
                    }

        # Check for MITRE technique / group ID patterns
        mitre_patterns = {}
        for col in df.columns:
            series = df[col].dropna().astype(str)
            tech_matches = series.apply(lambda x: re.findall(r"T\d{4}(?:\.\d{3})?", x))
            group_matches = series.apply(lambda x: re.findall(r"G\d{4}", x))
            total_techs = sum(len(m) for m in tech_matches)
            total_groups = sum(len(m) for m in group_matches)
            if total_techs > 0 or total_groups > 0:
                mitre_patterns[col] = {
                    "technique_id_mentions": total_techs,
                    "group_id_mentions": total_groups,
                }

        sheets_data[sheet] = {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "columns": col_info,
            "text_length_stats": text_stats,
            "mitre_id_patterns": mitre_patterns,
        }

    return {
        "dataset_key": dataset_key,
        "file_stats": stats,
        "sheets": sheets_data,
    }


def inspect_stix_bundle(filepath: str) -> Dict[str, Any]:
    stats = get_file_stats(filepath)
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    objects = data.get("objects", [])
    type_counts = {}
    attack_pattern_samples = []
    intrusion_set_samples = []
    intrusion_set_aliases = {}

    for obj in objects:
        t = obj.get("type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

        # Extract attack pattern sample metadata
        if t == "attack-pattern" and len(attack_pattern_samples) < 3:
            ext_refs = obj.get("external_references", [])
            mitre_id = next((r.get("external_id") for r in ext_refs if r.get("source_name") == "mitre-attack"), None)
            attack_pattern_samples.append({
                "id": obj.get("id"),
                "mitre_id": mitre_id,
                "name": obj.get("name"),
                "has_description": bool(obj.get("description")),
                "description_len": len(obj.get("description", "")),
                "tactics": [kc.get("phase_name") for kc in obj.get("kill_chain_phases", [])],
            })

        # Extract intrusion-set (threat group) samples & aliases
        if t == "intrusion-set":
            ext_refs = obj.get("external_references", [])
            mitre_id = next((r.get("external_id") for r in ext_refs if r.get("source_name") == "mitre-attack"), None)
            name = obj.get("name")
            aliases = obj.get("aliases", [])
            if mitre_id and name:
                intrusion_set_aliases[mitre_id] = {
                    "canonical_name": name,
                    "aliases": aliases,
                }
            if len(intrusion_set_samples) < 3:
                intrusion_set_samples.append({
                    "id": obj.get("id"),
                    "mitre_id": mitre_id,
                    "name": name,
                    "alias_count": len(aliases),
                    "sample_aliases": aliases[:5],
                })

    return {
        "file_stats": stats,
        "bundle_type": data.get("type"),
        "total_objects": len(objects),
        "type_counts": type_counts,
        "attack_patterns_count": type_counts.get("attack-pattern", 0),
        "intrusion_sets_count": type_counts.get("intrusion-set", 0),
        "malware_count": type_counts.get("malware", 0),
        "tools_count": type_counts.get("tool", 0),
        "relationships_count": type_counts.get("relationship", 0),
        "sample_attack_patterns": attack_pattern_samples,
        "sample_intrusion_sets": intrusion_set_samples,
        "total_groups_with_aliases": len(intrusion_set_aliases),
        "total_alias_entries": sum(len(v["aliases"]) for v in intrusion_set_aliases.values()),
    }


def generate_markdown_report(report_data: Dict[str, Any]) -> str:
    md = []
    md.append("# Phase 0 Data & Schema Inspection Report\n")
    md.append("Generated by automated verification script `scripts/inspect_datasets.py`.\n")

    # STIX Knowledge Base
    stix = report_data["stix_bundle"]
    md.append("## 1. MITRE ATT&CK Enterprise STIX Knowledge Base\n")
    md.append(f"- **Path**: `{stix['file_stats']['path']}`")
    md.append(f"- **File Size**: {stix['file_stats']['size_bytes']:,} bytes ({stix['file_stats']['size_mb']} MB)")
    md.append(f"- **SHA-256**: `{stix['file_stats']['sha256']}`")
    md.append(f"- **STIX Bundle Type**: `{stix['bundle_type']}`")
    md.append(f"- **Total Objects**: {stix['total_objects']:,}\n")

    md.append("### STIX Object Type Distribution\n")
    md.append("| Object Type | Count | Description / Role in Project |")
    md.append("| :--- | :--- | :--- |")
    for t, c in sorted(stix["type_counts"].items(), key=lambda x: x[1], reverse=True):
        role = ""
        if t == "attack-pattern":
            role = "Core techniques for structure-aware chunking (O2)"
        elif t == "intrusion-set":
            role = f"Threat groups & aliases for entity resolution (O1) ({stix['total_groups_with_aliases']} mapped)"
        elif t == "relationship":
            role = "Links (uses, mitigates, subtechnique-of)"
        elif t == "malware":
            role = "Software tools / malware"
        elif t == "course-of-action":
            role = "Mitigations"
        md.append(f"| `{t}` | {c:,} | {role} |")

    # Datasets
    md.append("\n## 2. Benchmark Datasets\n")
    for key, ds in report_data["datasets"].items():
        fs = ds["file_stats"]
        md.append(f"### Dataset: `{key}` ({fs['filename']})\n")
        md.append(f"- **Path**: `{fs['path']}`")
        md.append(f"- **Size**: {fs['size_bytes']:,} bytes ({fs['size_mb']} MB)")
        md.append(f"- **SHA-256**: `{fs['sha256']}`\n")

        for sheet, sdata in ds["sheets"].items():
            md.append(f"#### Sheet: `{sheet}` (Rows: {sdata['total_rows']:,}, Columns: {sdata['total_columns']})\n")
            md.append("| Column Name | Dtype | Non-Null | Nulls (%) | Sample Values |")
            md.append("| :--- | :--- | :--- | :--- | :--- |")
            for c in sdata["columns"]:
                samples_str = ", ".join(f"`{s[:35]}...`" if len(str(s)) > 35 else f"`{s}`" for s in c["samples"][:2])
                md.append(f"| `{c['column_name']}` | `{c['dtype']}` | {c['non_null_count']} | {c['null_percentage']}% | {samples_str} |")

            if sdata["text_length_stats"]:
                md.append("\n**Text Length Statistics (Words / Characters):**\n")
                md.append("| Column | Words (Min / Mean / Max) | Chars (Min / Mean / Max) |")
                md.append("| :--- | :--- | :--- |")
                for col_name, tstats in sdata["text_length_stats"].items():
                    md.append(f"| `{col_name}` | {tstats['word_count_min']} / {tstats['word_count_mean']} / {tstats['word_count_max']} | {tstats['char_len_min']} / {tstats['char_len_mean']} / {tstats['char_len_max']} |")

            if sdata["mitre_id_patterns"]:
                md.append("\n**MITRE ID Mentions Detected:**\n")
                for col_name, pstats in sdata["mitre_id_patterns"].items():
                    md.append(f"- `{col_name}`: {pstats['technique_id_mentions']} Technique IDs (`TXXXX`), {pstats['group_id_mentions']} Group IDs (`GXXXX`)")
            md.append("\n")

    return "\n".join(md)


def main():
    results_dir = os.path.join("results", "phase_0")
    os.makedirs(results_dir, exist_ok=True)

    print("Inspecting STIX Bundle...")
    stix_report = inspect_stix_bundle(os.path.join("data", "mitre", "enterprise-attack.json"))

    datasets = {
        "CTI-ATE": "data/datasets/cti-ate.xlsx",
        "CTI-TAA": "data/datasets/cti-taa.xlsx",
        "CTI-ATTACK": "data/datasets/CTI-ATTACK.xlsx",
    }

    datasets_report = {}
    for key, path in datasets.items():
        print(f"Inspecting {key} at {path}...")
        datasets_report[key] = inspect_excel_dataset(path, key)

    master_report = {
        "stix_bundle": stix_report,
        "datasets": datasets_report,
    }

    json_path = os.path.join(results_dir, "dataset_schemas.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(master_report, f, indent=2)
    print(f"Saved full JSON schema data to {json_path}")

    md_report = generate_markdown_report(master_report)
    md_path = os.path.join(results_dir, "schema_report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_report)
    print(f"Saved Markdown schema report to {md_path}")


if __name__ == "__main__":
    main()
