"""Phase 5 Part B: Optimization 1 Benchmark (V0h, V1h, Vrel).

Evaluates:
- Baseline B2 and B3 on cti-taa (N=50)
- Preprocessing: Query body only (split_query)
- Arms:
  1. V0h: Query body only, no expansion
  2. V1h: High-precision alias expansion (intrusion-set / malware, len>=5, case-sensitive, stoplist, 64-tok cap)
  3. Vrel: STIX relationship co-occurrence expansion (uses relationships, inverse group frequency scoring)
- Dual attribution metrics: Object-level AND Text-inclusive
- Family P3: 8 tests, Holm-Bonferroni step-down, 10,000 paired bootstrap resamples (seed 42)
- Transfer check: cti-ate and CTI-ATTACK under B2 (non-inferiority margin -0.03)
"""

import json
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.data_loader import load_benchmark_dataset, load_stix_all_bundles
from src.retrieval_eval import (
    compute_paired_bootstrap_ci,
    normalize_group_name,
    parse_ground_truth_techniques,
    compute_retrieval_metrics_technique
)
from src.retriever import HybridSTIXRetriever

FIXED_STOPLIST = {
    "net", "cmd", "page", "play", "solar", "find", "sc", "at", "date", "time",
    "dir", "ping", "tasklist", "reg", "powershell", "wmic", "arp", "route",
    "hostname", "whoami", "ipconfig", "netstat", "schtasks", "nslookup",
    "systeminfo", "quser", "query", "run", "logoff", "shutdown", "format",
    "replace", "attrib", "assoc", "ftype", "tree", "move", "copy", "xcopy",
    "robocopy", "expand", "type", "more", "sort", "fc", "comp", "diskpart",
    "chkdsk", "sfc", "bcdedit", "vssadmin", "wevtutil", "certutil", "bitsadmin",
    "curl", "tar"
}

def split_query(q: str):
    markers = ["Threat Report:", "**Text:**"]
    pos = -1
    found_marker = None
    for m in markers:
        p = q.find(m)
        if p != -1:
            if pos == -1 or p < pos:
                pos = p
                found_marker = m
    if found_marker is None:
        raise ValueError(f"Marker not found in query: {q[:100]}...")
    instruction = q[:pos].strip()
    body = q[pos + len(found_marker):].strip()
    return instruction, body, found_marker


def build_stix_indices(stix_kb):
    """Build entity dictionaries and uses-relationship graph."""
    print("Building STIX entity and relationship indices...", flush=True)
    
    # 1. Intrusion sets
    intrusion_sets = {}  # id -> {canonical, aliases, mitre_id}
    name_to_group = {}   # alias/canonical -> id
    
    for obj in stix_kb.intrusion_sets:
        sid = obj["id"]
        name = obj.get("name", "").strip()
        ext_refs = obj.get("external_references", [])
        mid = next((r.get("external_id") for r in ext_refs if r.get("source_name") in ["mitre-attack", "mitre-mobile-attack", "mitre-ics-attack"]), None)
        aliases = set(obj.get("aliases", []))
        if obj.get("x_mitre_aliases"):
            aliases.update(obj.get("x_mitre_aliases", []))
        aliases.add(name)
        
        gdata = {
            "id": sid,
            "mitre_id": mid,
            "canonical_name": name,
            "aliases": sorted(list(aliases))
        }
        intrusion_sets[sid] = gdata
        for a in aliases:
            name_to_group[a] = sid

    # 2. Software (malware + tools)
    software = {}  # id -> {canonical, aliases, type, mitre_id}
    for obj in stix_kb.malware + stix_kb.tools:
        sid = obj["id"]
        name = obj.get("name", "").strip()
        etype = obj.get("type", "malware")
        ext_refs = obj.get("external_references", [])
        mid = next((r.get("external_id") for r in ext_refs if r.get("source_name") in ["mitre-attack", "mitre-mobile-attack", "mitre-ics-attack"]), None)
        aliases = set(obj.get("aliases", []))
        if obj.get("x_mitre_aliases"):
            aliases.update(obj.get("x_mitre_aliases", []))
        aliases.add(name)
        
        software[sid] = {
            "id": sid,
            "mitre_id": mid,
            "canonical_name": name,
            "entity_type": etype,
            "aliases": sorted(list(aliases))
        }

    # 3. Relationships: intrusion-set -[uses]-> software
    software_to_groups = defaultdict(set)
    for rel in stix_kb.relationships:
        if rel.get("relationship_type") != "uses":
            continue
        if rel.get("revoked") is True:
            continue
        s_ref = rel.get("source_ref", "")
        t_ref = rel.get("target_ref", "")
        if s_ref.startswith("intrusion-set--") and (t_ref.startswith("malware--") or t_ref.startswith("tool--")):
            if s_ref in intrusion_sets and t_ref in software:
                software_to_groups[t_ref].add(s_ref)

    # 4. Inverse group frequency weights
    software_weights = {}
    for sw_id, grps in software_to_groups.items():
        if grps:
            software_weights[sw_id] = 1.0 / len(grps)
            
    print(f"Indexed {len(intrusion_sets)} intrusion sets, {len(software)} software, {len(software_to_groups)} software with group uses links.", flush=True)
    return intrusion_sets, software, software_to_groups, software_weights


def build_alias_matchers(intrusion_sets, software):
    """Build case-sensitive alias patterns len >= 5 not in stoplist."""
    matchers = []  # list of (compiled_regex, canonical, alias, type, sid)
    
    # Intrusion sets
    for sid, g in intrusion_sets.items():
        for a in g["aliases"]:
            if len(a) < 5 or a.lower() in FIXED_STOPLIST:
                continue
            # Regex: word boundary, case sensitive
            pat = re.compile(r'\b' + re.escape(a) + r'\b')
            matchers.append((pat, g["canonical_name"], a, "intrusion-set", sid))
            
    # Software
    for sid, s in software.items():
        for a in s["aliases"]:
            if len(a) < 5 or a.lower() in FIXED_STOPLIST:
                continue
            pat = re.compile(r'\b' + re.escape(a) + r'\b')
            matchers.append((pat, s["canonical_name"], a, s["entity_type"], sid))
            
    # Sort longest alias first
    matchers.sort(key=lambda x: len(x[2]), reverse=True)
    return matchers


def expand_v1h(body_text: str, matchers) -> Tuple[str, List[Dict[str, Any]]]:
    """Prepend aliases of detected intrusion-set or malware (case-sensitive, len>=5, stoplist, 64-tok cap)."""
    detected = []
    seen_spans = []
    
    for pat, can_name, alias, etype, sid in matchers:
        if etype not in ["intrusion-set", "malware"]:
            continue
        for m in pat.finditer(body_text):
            s, e = m.span()
            # Check overlap
            if any(s < oe and e > os_ for os_, oe in seen_spans):
                continue
            # Exact casing check
            matched_slice = body_text[s:e]
            if matched_slice == alias:
                seen_spans.append((s, e))
                detected.append({
                    "canonical": can_name,
                    "matched_alias": alias,
                    "type": etype,
                    "id": sid
                })
                
    if not detected:
        return body_text, []
        
    # Prepend unique canonical & aliases up to 64 tokens (~50 words)
    prefix_tokens = []
    seen = set()
    for d in detected:
        for term in [d["canonical"], d["matched_alias"]]:
            t_norm = term.strip()
            if t_norm.lower() not in seen and len(t_norm) >= 5 and t_norm.lower() not in FIXED_STOPLIST:
                seen.add(t_norm.lower())
                prefix_tokens.append(t_norm)
                if len(" ".join(prefix_tokens).split()) >= 45:
                    break
        if len(" ".join(prefix_tokens).split()) >= 45:
            break
            
    prefix_str = " ".join(prefix_tokens)
    expanded = f"{prefix_str} {body_text}".strip()
    return expanded, detected


def expand_vrel(body_text: str, matchers, intrusion_sets, software_to_groups, software_weights) -> Tuple[str, List[Dict[str, Any]]]:
    """Score groups via STIX uses relationships from detected software; prepend top 3 groups."""
    detected_sw = []
    seen_spans = []
    
    for pat, can_name, alias, etype, sid in matchers:
        # Detect software (malware or tool)
        if etype not in ["malware", "tool"]:
            continue
        for m in pat.finditer(body_text):
            s, e = m.span()
            if any(s < oe and e > os_ for os_, oe in seen_spans):
                continue
            if body_text[s:e] == alias:
                seen_spans.append((s, e))
                detected_sw.append(sid)
                
    if not detected_sw:
        # Fallback to body_text
        return body_text, []
        
    # Score groups: sum over software of 1 / |groups using s|
    group_scores = defaultdict(float)
    for sw_id in detected_sw:
        w = software_weights.get(sw_id, 0.0)
        for g_id in software_to_groups.get(sw_id, []):
            group_scores[g_id] += w
            
    if not group_scores:
        return body_text, []
        
    # Rank groups by score descending
    sorted_groups = sorted(group_scores.items(), key=lambda x: x[1], reverse=True)
    top_3_groups = sorted_groups[:3]
    
    prefix_tokens = []
    seen = set()
    for g_id, sc in top_3_groups:
        g = intrusion_sets[g_id]
        can = g["canonical_name"]
        if can.lower() not in seen:
            seen.add(can.lower())
            prefix_tokens.append(can)
        # First alias if available
        for a in g["aliases"]:
            if a.lower() not in seen and len(a) >= 5 and a.lower() not in FIXED_STOPLIST:
                seen.add(a.lower())
                prefix_tokens.append(a)
                break
        if len(" ".join(prefix_tokens).split()) >= 45:
            break
            
    prefix_str = " ".join(prefix_tokens)
    expanded = f"{prefix_str} {body_text}".strip()
    return expanded, top_3_groups


def evaluate_dual_attribution(retrieved_docs, gt_str, group_alias_map):
    """Compute BOTH object-level AND text-inclusive attribution metrics."""
    raw_gt_norm = normalize_group_name(gt_str)
    all_gt_aliases = {raw_gt_norm}
    
    # Expand STIX known aliases for GT
    for gid, gdata in group_alias_map.items():
        canonical_norm = normalize_group_name(gdata.get("canonical_name", ""))
        alias_norms = {normalize_group_name(a) for a in gdata.get("aliases", [])}
        if raw_gt_norm == canonical_norm or raw_gt_norm in alias_norms or any(a in raw_gt_norm for a in alias_norms if len(a) > 3):
            all_gt_aliases.add(gid.lower())
            all_gt_aliases.add(canonical_norm)
            all_gt_aliases.update(alias_norms)

    # 1. Object-level relevance
    obj_ranks = []
    # 2. Text-inclusive relevance
    txt_ranks = []
    
    for doc in retrieved_docs:
        doc_text = doc.page_content if hasattr(doc, "page_content") else str(doc)
        doc_meta = doc.metadata if hasattr(doc, "metadata") else {}
        doc_meta_id = doc_meta.get("mitre_id", "").lower()
        doc_aliases = [normalize_group_name(a) for a in doc_meta.get("aliases", [])]
        
        # Object-level check: metadata matches
        is_obj = 0
        if doc_meta_id and doc_meta_id in all_gt_aliases:
            is_obj = 1
        elif any(a in all_gt_aliases for a in doc_aliases if a):
            is_obj = 1
        obj_ranks.append(is_obj)
        
        # Text-inclusive check: object match OR substring in text
        is_txt = is_obj
        if not is_txt:
            doc_text_norm = normalize_group_name(doc_text)
            for alias in all_gt_aliases:
                if len(alias) >= 4 and alias in doc_text_norm:
                    is_txt = 1
                    break
        txt_ranks.append(is_txt)

    def calc_metrics(ranks):
        r10 = 1.0 if any(ranks[:10]) else 0.0
        mrr = 0.0
        for idx, rel in enumerate(ranks):
            if rel:
                mrr = 1.0 / (idx + 1)
                break
        return r10, mrr
        
    obj_r10, obj_mrr = calc_metrics(obj_ranks)
    txt_r10, txt_mrr = calc_metrics(txt_ranks)
    
    return {
        "object_level": {"Recall@10": obj_r10, "MRR": obj_mrr},
        "text_inclusive": {"Recall@10": txt_r10, "MRR": txt_mrr}
    }


def run_benchmark():
    print("=" * 80)
    print("PHASE 5 PART B: O1 VARIANTS BENCHMARK (V0h, V1h, Vrel)")
    print("=" * 80)

    stix_kb = load_stix_all_bundles()
    group_alias_map = stix_kb.get_group_alias_map()
    intrusion_sets, software, software_to_groups, software_weights = build_stix_indices(stix_kb)
    matchers = build_alias_matchers(intrusion_sets, software)
    
    retriever = HybridSTIXRetriever(stix_kb=stix_kb, cache_dir=".cache/retriever_index_all")
    
    df_taa = load_benchmark_dataset("cti-taa").df
    
    out_dir = REPO_ROOT / "results" / "phase_5"
    out_dir.mkdir(parents=True, exist_ok=True)

    top10_cache_file = out_dir / "o1_top10_cache.json"
    top10_cache: Dict[str, Dict[str, Dict[str, List]]] = defaultdict(lambda: defaultdict(dict))
    if top10_cache_file.exists():
        with open(top10_cache_file, "r", encoding="utf-8") as f:
            raw_c = json.load(f)
            for b_k in raw_c:
                for a_k in raw_c[b_k]:
                    for q_k in raw_c[b_k][a_k]:
                        top10_cache[b_k][a_k][q_k] = raw_c[b_k][a_k][q_k]

    # Store per-query metrics: arm -> baseline -> credit_rule -> list of metrics
    per_query_results = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    
    # Evaluate across Baselines B2 and B3
    for b_code, enable_chunking in [("B2", False), ("B3", True)]:
        print(f"\n=======================================================", flush=True)
        print(f"EVALUATING BASELINE {b_code} (enable_chunking={enable_chunking})", flush=True)
        print(f"=======================================================", flush=True)
        
        for q_idx, row in df_taa.iterrows():
            q_raw = str(row["query"])
            gt = str(row["ground_truth"])
            instr, body, marker = split_query(q_raw)
            
            # 1. V0h: body only
            q_v0h = body
            # 2. V1h: body + high-precision alias expansion
            q_v1h, _ = expand_v1h(body, matchers)
            # 3. Vrel: body + STIX uses relationship expansion
            q_vrel, _ = expand_vrel(body, matchers, intrusion_sets, software_to_groups, software_weights)
            
            queries = {
                "V0h": q_v0h,
                "V1h": q_v1h,
                "Vrel": q_vrel
            }
            
            for arm, q_text in queries.items():
                q_key = str(q_idx)
                if q_key in top10_cache[b_code][arm]:
                    cached_docs_data = top10_cache[b_code][arm][q_key]
                    docs = [
                        Document(page_content=d["page_content"], metadata=d["metadata"])
                        for d in cached_docs_data
                    ]
                else:
                    docs = retriever.retrieve(q_text, top_k=10, enable_query_chunking=enable_chunking)
                    top10_cache[b_code][arm][q_key] = [
                        {"page_content": d.page_content, "metadata": d.metadata}
                        for d in docs
                    ]

                m = evaluate_dual_attribution(docs, gt, group_alias_map)
                
                for crule in ["object_level", "text_inclusive"]:
                    for met_name in ["Recall@10", "MRR"]:
                        val = m[crule][met_name]
                        if met_name not in per_query_results[arm][b_code][crule]:
                            per_query_results[arm][b_code][crule][met_name] = []
                        per_query_results[arm][b_code][crule][met_name].append(val)
                        
            if (q_idx + 1) % 10 == 0 or q_idx == len(df_taa) - 1:
                print(f"  [{b_code}] Processed {q_idx + 1}/{len(df_taa)} queries...", flush=True)
                with open(top10_cache_file, "w", encoding="utf-8") as f:
                    json.dump(top10_cache, f)

    # Summary table
    summary_data = []
    print("\n" + "=" * 80)
    print("PART B RESULTS: cti-taa (N=50)")
    print("=" * 80)
    
    for crule in ["object_level", "text_inclusive"]:
        print(f"\n--- Credit Rule: {crule} ---")
        print(f"{'Baseline':<10} {'Arm':<10} {'Recall@10':<12} {'MRR':<12}")
        print("-" * 45)
        for b_code in ["B2", "B3"]:
            for arm in ["V0h", "V1h", "Vrel"]:
                r10_mean = float(np.mean(per_query_results[arm][b_code][crule]["Recall@10"]))
                mrr_mean = float(np.mean(per_query_results[arm][b_code][crule]["MRR"]))
                print(f"{b_code:<10} {arm:<10} {r10_mean:<12.4f} {mrr_mean:<12.4f}")
                summary_data.append({
                    "baseline": b_code,
                    "arm": arm,
                    "credit_rule": crule,
                    "Recall@10": round(r10_mean, 4),
                    "MRR": round(mrr_mean, 4)
                })

    # Statistical Contrasts: Family P3 (8 tests, Holm step-down)
    print("\n" + "=" * 80)
    print("FAMILY P3 CONFIRMATORY CONTRASTS (8 tests vs V0h, Holm-Bonferroni, seed 42)")
    print("=" * 80)
    
    # We evaluate both credit rules for Family P3 (primary: text_inclusive and object_level)
    p3_contrasts = []
    test_id = 1
    
    for crule in ["object_level", "text_inclusive"]:
        for b_code in ["B2", "B3"]:
            for arm in ["V1h", "Vrel"]:
                for met in ["Recall@10", "MRR"]:
                    t_vals = per_query_results[arm][b_code][crule][met]
                    c_vals = per_query_results["V0h"][b_code][crule][met]
                    
                    boot_res = compute_paired_bootstrap_ci(
                        c_vals, t_vals, n_resamples=10000, seed=42
                    )
                    ci_low = boot_res["ci_lower"]
                    ci_high = boot_res["ci_upper"]
                    raw_p = boot_res["p_value"]
                    mean_t = float(np.mean(t_vals))
                    mean_c = float(np.mean(c_vals))
                    delta = mean_t - mean_c
                    
                    diffs = [t - c for t, c in zip(t_vals, c_vals)]
                    wins = sum(1 for d in diffs if d > 0)
                    ties = sum(1 for d in diffs if d == 0)
                    losses = sum(1 for d in diffs if d < 0)
                    
                    p3_contrasts.append({
                        "test_id": f"P3_{test_id:02d}",
                        "credit_rule": crule,
                        "baseline": b_code,
                        "contrast": f"{arm} vs V0h",
                        "metric": met,
                        "treatment_mean": round(mean_t, 4),
                        "control_mean": round(mean_c, 4),
                        "delta": round(delta, 4),
                        "ci_95": [round(ci_low, 4), round(ci_high, 4)],
                        "raw_p": round(raw_p, 4),
                        "wtl": f"{wins}/{ties}/{losses}",
                        "sum_diffs": round(sum(diffs), 4)
                    })
                    test_id += 1

    # Apply Holm step-down on the 8 tests for each credit rule
    for crule in ["object_level", "text_inclusive"]:
        subset = [c for c in p3_contrasts if c["credit_rule"] == crule]
        subset.sort(key=lambda x: x["raw_p"])
        M = len(subset)  # 8 tests
        print(f"\n--- Holm-Bonferroni Step-Down: {crule} (M={M}, alpha=0.05) ---")
        sig_active = True
        for rank, c in enumerate(subset, 1):
            alpha_k = 0.05 / (M - rank + 1)
            p = c["raw_p"]
            if sig_active and p <= alpha_k:
                decision = "Significant decrease" if c["delta"] < 0 else "Significant increase"
            else:
                sig_active = False
                decision = "Not significant"
            c["holm_rank"] = rank
            c["holm_alpha"] = round(alpha_k, 5)
            c["decision"] = decision
            p_str = "< 0.0001" if p == 0.0 else f"{p:.4f}"
            print(f"Rank {rank}: {c['test_id']} ({c['baseline']} {c['contrast']} {c['metric']}): Delta={c['delta']:+.4f}, p={p_str}, alpha_k={alpha_k:.5f} -> {decision}")

    # Transfer check on cti-ate and CTI-ATTACK (Baseline B2)
    print("\n" + "=" * 80)
    print("CROSS-DATASET TRANSFER CHECK: V1h vs V0h on cti-ate and CTI-ATTACK (B2)")
    print("=" * 80)
    transfer_results = []
    
    transfer_cache_file = out_dir / "o1_transfer_cache.json"
    transfer_cache: Dict[str, Dict[str, Dict[str, List]]] = defaultdict(lambda: defaultdict(dict))
    if transfer_cache_file.exists():
        with open(transfer_cache_file, "r", encoding="utf-8") as f:
            raw_tc = json.load(f)
            for ds_k in raw_tc:
                for a_k in raw_tc[ds_k]:
                    for q_k in raw_tc[ds_k][a_k]:
                        transfer_cache[ds_k][a_k][q_k] = raw_tc[ds_k][a_k][q_k]

    for ds_name in ["cti-ate", "CTI-ATTACK"]:
        df = load_benchmark_dataset(ds_name).df
        v0h_r10, v0h_mrr = [], []
        v1h_r10, v1h_mrr = [], []
        
        for q_idx, row in df.iterrows():
            q_raw = str(row["query"])
            gt = str(row["ground_truth"])
            instr, body, marker = split_query(q_raw)
            
            q_key = str(q_idx)
            if q_key in transfer_cache[ds_name]["V0h"]:
                docs_v0h = [
                    Document(page_content=d["page_content"], metadata=d["metadata"])
                    for d in transfer_cache[ds_name]["V0h"][q_key]
                ]
            else:
                docs_v0h = retriever.retrieve(body, top_k=10, enable_query_chunking=False)
                transfer_cache[ds_name]["V0h"][q_key] = [
                    {"page_content": d.page_content, "metadata": d.metadata}
                    for d in docs_v0h
                ]

            if q_key in transfer_cache[ds_name]["V1h"]:
                docs_v1h = [
                    Document(page_content=d["page_content"], metadata=d["metadata"])
                    for d in transfer_cache[ds_name]["V1h"][q_key]
                ]
            else:
                q_v1h, _ = expand_v1h(body, matchers)
                docs_v1h = retriever.retrieve(q_v1h, top_k=10, enable_query_chunking=False)
                transfer_cache[ds_name]["V1h"][q_key] = [
                    {"page_content": d.page_content, "metadata": d.metadata}
                    for d in docs_v1h
                ]
            
            # Technique evaluation
            m_v0h = compute_retrieval_metrics_technique(docs_v0h, gt, k_values=[10], subtechnique_parent_credit=True)
            m_v1h = compute_retrieval_metrics_technique(docs_v1h, gt, k_values=[10], subtechnique_parent_credit=True)
            
            v0h_r10.append(float(m_v0h["Recall@10"]))
            v0h_mrr.append(float(m_v0h["MRR"]))
            v1h_r10.append(float(m_v1h["Recall@10"]))
            v1h_mrr.append(float(m_v1h["MRR"]))
            
            if (q_idx + 1) % 25 == 0 or q_idx == len(df) - 1:
                with open(transfer_cache_file, "w", encoding="utf-8") as f:
                    json.dump(transfer_cache, f)
            
        d_r10 = float(np.mean(v1h_r10)) - float(np.mean(v0h_r10))
        d_mrr = float(np.mean(v1h_mrr)) - float(np.mean(v0h_mrr))
        
        boot_r10 = compute_paired_bootstrap_ci(v0h_r10, v1h_r10, n_resamples=10000, seed=42)
        ci_l_r10, ci_h_r10, p_r10 = boot_r10["ci_lower"], boot_r10["ci_upper"], boot_r10["p_value"]
        boot_mrr = compute_paired_bootstrap_ci(v0h_mrr, v1h_mrr, n_resamples=10000, seed=42)
        ci_l_mrr, ci_h_mrr, p_mrr = boot_mrr["ci_lower"], boot_mrr["ci_upper"], boot_mrr["p_value"]
        
        pass_margin = (d_r10 >= -0.03) and (d_mrr >= -0.03)
        print(f"{ds_name} (N={len(df)}):")
        print(f"  Recall@10: V0h={np.mean(v0h_r10):.4f}, V1h={np.mean(v1h_r10):.4f}, Delta={d_r10:+.4f} (CI [{ci_l_r10:+.4f}, {ci_h_r10:+.4f}], p={p_r10:.4f})")
        print(f"  MRR      : V0h={np.mean(v0h_mrr):.4f}, V1h={np.mean(v1h_mrr):.4f}, Delta={d_mrr:+.4f} (CI [{ci_l_mrr:+.4f}, {ci_h_mrr:+.4f}], p={p_mrr:.4f})")
        print(f"  Non-inferiority margin (-0.03): {'PASSED' if pass_margin else 'FAILED'}")
        
        transfer_results.append({
            "dataset": ds_name,
            "metric": "Recall@10",
            "v0h_mean": round(float(np.mean(v0h_r10)), 4),
            "v1h_mean": round(float(np.mean(v1h_r10)), 4),
            "delta": round(d_r10, 4),
            "ci_95": [round(ci_l_r10, 4), round(ci_h_r10, 4)],
            "raw_p": round(p_r10, 4),
            "non_inferiority_passed": bool(d_r10 >= -0.03)
        })
        transfer_results.append({
            "dataset": ds_name,
            "metric": "MRR",
            "v0h_mean": round(float(np.mean(v0h_mrr)), 4),
            "v1h_mean": round(float(np.mean(v1h_mrr)), 4),
            "delta": round(d_mrr, 4),
            "ci_95": [round(ci_l_mrr, 4), round(ci_h_mrr, 4)],
            "raw_p": round(p_mrr, 4),
            "non_inferiority_passed": bool(d_mrr >= -0.03)
        })

    # Save output artifacts
    output_package = {
        "summary": summary_data,
        "family_p3_contrasts": p3_contrasts,
        "transfer_check": transfer_results,
        "per_query_archive": {
            arm: {
                b_code: {
                    crule: {
                        met: [round(x, 4) for x in vals]
                        for met, vals in met_dict.items()
                    }
                    for crule, met_dict in crule_dict.items()
                }
                for b_code, crule_dict in bcode_dict.items()
            }
            for arm, bcode_dict in per_query_results.items()
        }
    }
    
    out_file = out_dir / "o1_phase5_benchmark_results.json"
    with open(out_file, "w", encoding="utf-8") as fp:
        json.dump(output_package, fp, indent=2)
    print(f"\nSaved all Phase 5 Part B benchmark results to {out_file}", flush=True)


if __name__ == "__main__":
    run_benchmark()
