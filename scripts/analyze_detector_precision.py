import csv
import json
import os
import random
import re
import sys

import numpy as np

os.environ["OMP_NUM_THREADS"] = "4"
try:
    import torch
    torch.set_num_threads(4)
except ImportError:
    pass
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.data_loader import load_benchmark_dataset, load_stix_all_bundles
from src.entity_resolver import CyberEntityResolver, DetectedEntity
from src.retriever import HybridSTIXRetriever
from src.retrieval_eval import compute_retrieval_metrics_taa_alias_aware

# Common English words and Windows commands
COMMON_WORDS_AND_COMMANDS = {
    # Windows commands & CLI utilities
    "cmd", "net", "at", "ping", "reg", "sc", "find", "whoami", "ipconfig", "powershell",
    "certutil", "curl", "bitsadmin", "wmic", "schtasks", "copy", "del", "move", "type",
    "echo", "dir", "run", "start", "tasklist", "netstat", "hostname", "assoc", "ftype",
    "tree", "attrib", "systeminfo", "gpupdate", "nslookup", "tracert", "route", "arp", "nbtstat",
    # Common English nouns, verbs, prepositions often colliding with aliases
    "and", "the", "for", "with", "from", "that", "this", "car", "top", "man", "sun", "oil",
    "red", "star", "drop", "fire", "bad", "cut", "fast", "gold", "help", "iron", "jump",
    "king", "lead", "moon", "open", "pass", "rain", "safe", "test", "time", "view", "zero",
    "base", "host", "line", "read", "side", "unit", "work", "agent", "power", "shell",
    "system", "service", "process", "drive", "disk", "file", "port", "data", "code",
    "date", "name", "node", "note", "path", "user", "web", "win", "key", "log", "set",
    "use", "task", "share", "stop", "tool", "target", "source", "client", "server", "rat",
    "agent", "trojan", "miner", "worm", "backdoor", "root", "admin", "admin$", "c$", "ipc$",
    "page", "play", "solar", "band"
}

def extract_sentence_context(text: str, start: int, end: int, window: int = 150) -> str:
    """Extract local context surrounding match span."""
    s = max(0, start - window)
    e = min(len(text), end + window)
    snippet = text[s:e].replace("\n", " ").replace("\r", " ")
    prefix = "..." if s > 0 else ""
    suffix = "..." if e < len(text) else ""
    return f"{prefix}{snippet}{suffix}"

def run_detector_precision_audit():
    print("=" * 70)
    print("PHASE 4B ITEM 7: DETECTOR PRECISION & EXPLORATORY V1-STRICT")
    print("=" * 70)

    kb = load_stix_all_bundles()
    resolver = CyberEntityResolver(stix_kb=kb, min_alias_len=3, random_seed=42)
    df_taa = load_benchmark_dataset("cti-taa").df

    all_detections = []
    alias_counts = Counter()
    alias_meta = {}

    for q_idx, row in df_taa.iterrows():
        query_text = str(row["query"])
        detected = resolver.detect_entities(query_text)
        for d in detected:
            alias_lower = d.matched_text.lower()
            alias_counts[alias_lower] += 1
            if alias_lower not in alias_meta:
                is_common = (
                    alias_lower in COMMON_WORDS_AND_COMMANDS
                    or len(alias_lower) <= 3
                )
                alias_meta[alias_lower] = {
                    "matched_text": d.matched_text,
                    "canonical_name": d.entity.canonical_name,
                    "mitre_id": d.entity.mitre_id,
                    "entity_type": d.entity.entity_type,
                    "alias_len": len(d.matched_text),
                    "is_common_english_or_cmd": is_common
                }
            
            # Record for sampling
            context = extract_sentence_context(query_text, d.start_char, d.end_char)
            all_detections.append({
                "query_idx": q_idx,
                "matched_text": d.matched_text,
                "alias_lower": alias_lower,
                "canonical_name": d.entity.canonical_name,
                "mitre_id": d.entity.mitre_id,
                "entity_type": d.entity.entity_type,
                "start_char": d.start_char,
                "end_char": d.end_char,
                "sentence_context": context
            })

    print(f"\nTotal detections across all 50 CTI-TAA queries: {len(all_detections)}")
    print(f"Distinct detected aliases: {len(alias_counts)}")

    # 7a: Top 30 detected aliases
    top30 = alias_counts.most_common(30)
    top30_table = []
    print("\n--- Top 30 Detected Aliases on cti-taa ---")
    print(f"{'Rank':<5} | {'Alias':<20} | {'Freq':<6} | {'Len':<5} | {'Entity Type':<15} | {'Canonical Name':<25} | {'Common/Cmd?'}")
    print("-" * 105)
    for rank, (alias_l, freq) in enumerate(top30, 1):
        meta = alias_meta[alias_l]
        is_common = meta["is_common_english_or_cmd"]
        top30_table.append({
            "rank": rank,
            "alias": meta["matched_text"],
            "frequency": freq,
            "length": meta["alias_len"],
            "entity_type": meta["entity_type"],
            "canonical_name": meta["canonical_name"],
            "is_common_english_or_cmd": is_common
        })
        print(f"{rank:<5} | {meta['matched_text']:<20} | {freq:<6} | {meta['alias_len']:<5} | {meta['entity_type']:<15} | {meta['canonical_name']:<25} | {is_common}")

    # Save 7a results
    out_dir = REPO_ROOT / "results" / "phase_4b"
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "top30_detected_aliases.json", "w", encoding="utf-8") as fp:
        json.dump(top30_table, fp, indent=2)

    # 7b: Draw 100 random detected matches (seed 42) into detector_labels.csv
    rng = random.Random(42)
    sample_indices = rng.sample(range(len(all_detections)), min(100, len(all_detections)))
    sample_matches = [all_detections[i] for i in sample_indices]

    csv_path = out_dir / "detector_labels.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fp:
        writer = csv.writer(fp)
        writer.writerow([
            "sample_id",
            "query_idx",
            "matched_alias",
            "canonical_name",
            "mitre_id",
            "entity_type",
            "sentence_context",
            "is_real_entity_mention"  # Left empty for USER to label
        ])
        for s_id, m in enumerate(sample_matches, 1):
            writer.writerow([
                s_id,
                m["query_idx"],
                m["matched_text"],
                m["canonical_name"],
                m["mitre_id"],
                m["entity_type"],
                m["sentence_context"],
                ""  # Empty for USER
            ])
    print(f"\nSaved 100 random detected matches to {csv_path} with empty 'is_real_entity_mention' column.")

    # 7c: Exploratory V1-strict run
    # Drop aliases length <= 4 AND common English / Windows commands
    # Keep group + malware names
    print("\n--- Running Exploratory V1-Strict Retrieval on cti-taa (B2 & B3) ---")
    retriever = HybridSTIXRetriever(stix_kb=kb, cache_dir=".cache/retriever_index_all")
    group_alias_map = kb.get_group_alias_map()

    # Define custom V1-strict query expansion
    def expand_v1_strict(query: str, max_tokens: int = 64) -> str:
        detected = resolver.detect_entities(query)
        # Filter detections
        strict_detected = []
        for d in detected:
            alias_clean = d.matched_text.strip().lower()
            # Drop length <= 4
            if len(alias_clean) <= 4:
                continue
            # Drop common English / commands
            if alias_clean in COMMON_WORDS_AND_COMMANDS:
                continue
            # Keep group + malware
            if d.entity.entity_type in ["intrusion-set", "malware"]:
                strict_detected.append(d)

        if not strict_detected:
            return query

        # Prepend unique canonical / alias names up to budget
        expansion_tokens = []
        seen = set()
        for d in strict_detected:
            cand = d.entity.canonical_name
            if cand.lower() not in seen:
                seen.add(cand.lower())
                expansion_tokens.append(cand)
            for a in d.entity.aliases[:2]:
                if a.lower() not in seen and len(a) > 4 and a.lower() not in COMMON_WORDS_AND_COMMANDS:
                    seen.add(a.lower())
                    expansion_tokens.append(a)

        expansion_prefix = " ".join(expansion_tokens)
        return f"{expansion_prefix} {query}".strip()

    # Evaluate across B2 and B3
    # Load pre-registered V0 baseline evaluations to avoid redundant computation
    cp_path = REPO_ROOT / "results" / "phase_2" / "p1_eval_checkpoint.json"
    with open(cp_path, "r", encoding="utf-8") as fp:
        p1_cp = json.load(fp)

    v1_strict_results = {}
    for b_code, enable_chunking in [("B2", False), ("B3", True)]:
        print(f"\nEvaluating Baseline {b_code} (enable_chunking={enable_chunking})...", flush=True)
        # Precomputed V0 metrics from verified checkpoint
        v0_rec10 = [float(x["Recall@10"]) for x in p1_cp[f"E0-STIX-ALL_{b_code}_V0_cti-taa"]]
        v0_mrr = [float(x["MRR"]) for x in p1_cp[f"E0-STIX-ALL_{b_code}_V0_cti-taa"]]

        v1_strict_rec10 = []
        v1_strict_mrr = []

        for q_idx, row in df_taa.iterrows():
            q_raw = str(row["query"])
            gt = str(row["ground_truth"])

            # V1-strict query
            q_strict = expand_v1_strict(q_raw)
            docs_strict = retriever.retrieve(
                q_strict,
                top_k=10,
                enable_query_chunking=enable_chunking
            )
            ret_docs_strict = [{"id": d.metadata.get("id"), "canonical_name": d.metadata.get("name"), "aliases": d.metadata.get("aliases", []), "page_content": d.page_content} for d in docs_strict]
            m_strict = compute_retrieval_metrics_taa_alias_aware(ret_docs_strict, gt, group_alias_map, k_values=[10])
            v1_strict_rec10.append(float(m_strict["Recall@10"]))
            v1_strict_mrr.append(float(m_strict["MRR"]))
            if (q_idx + 1) % 10 == 0 or q_idx == len(df_taa) - 1:
                print(f"  [{b_code}] Processed {q_idx + 1}/{len(df_taa)} queries...", flush=True)

        mean_v0_r10 = float(np.mean(v0_rec10))
        mean_v0_mrr = float(np.mean(v0_mrr))
        mean_strict_r10 = float(np.mean(v1_strict_rec10))
        mean_strict_mrr = float(np.mean(v1_strict_mrr))

        delta_r10 = mean_strict_r10 - mean_v0_r10
        delta_mrr = mean_strict_mrr - mean_v0_mrr

        v1_strict_results[b_code] = {
            "baseline": b_code,
            "label": "post-hoc exploratory, outside P1, no Holm",
            "V0_Recall@10": round(mean_v0_r10, 4),
            "V0_MRR": round(mean_v0_mrr, 4),
            "V1_Strict_Recall@10": round(mean_strict_r10, 4),
            "V1_Strict_MRR": round(mean_strict_mrr, 4),
            "Delta_Recall@10": round(delta_r10, 4),
            "Delta_MRR": round(delta_mrr, 4)
        }

        print(f"  {b_code}: V0 Rec@10={mean_v0_r10:.4f}, V1-strict Rec@10={mean_strict_r10:.4f} (Delta={delta_r10:+.4f})", flush=True)
        print(f"  {b_code}: V0 MRR   ={mean_v0_mrr:.4f}, V1-strict MRR   ={mean_strict_mrr:.4f} (Delta={delta_mrr:+.4f})", flush=True)

        # Save intermediate
        with open(out_dir / "v1_strict_exploratory_results.json", "w", encoding="utf-8") as fp:
            json.dump(v1_strict_results, fp, indent=2)

    print(f"\nSaved exploratory V1-strict results to {out_dir / 'v1_strict_exploratory_results.json'}", flush=True)

if __name__ == "__main__":
    run_detector_precision_audit()
