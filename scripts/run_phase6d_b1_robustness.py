"""Phase 6D Part D: B1 Retriever Robustness (Long-Context Embedding Baseline).

Evaluates the long-context embedding baseline B1 (nomic-ai/nomic-embed-text-v1.5,
as timed in results/phase_2/b1_timing_benchmark.json) for:
1. cti-taa (50 queries): V0, V0h, and Vrel.
2. cti-ate (60 queries) and CTI-ATTACK (229 queries): E0'(raw) vs E0'-HD-k200.

Evaluates whether hygiene and Vrel effects preserve their sign and size under B1.
Strictly offline, thread cap 4, one heavy retrieval process at a time.
Strictly descriptive metrics; zero causal phrasing.
"""

import argparse
import json
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd
from scipy.stats import binomtest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.data_loader import load_benchmark_dataset, load_stix_all_bundles, STIXKnowledgeBase
from src.retriever import Document, build_stix_raw_documents
from src.retrieval_eval import (
    compute_paired_bootstrap_ci,
    compute_retrieval_metrics_technique,
    compute_retrieval_metrics_taa_alias_aware,
    normalize_group_name,
)
from scripts.run_o1_phase5_benchmark import (
    split_query,
    build_stix_indices,
    build_alias_matchers,
    expand_vrel,
)
from scripts.run_o2_clean_benchmark import (
    build_stix_domain_maps,
    doc_matches_domain,
)

MODEL_NAME = "nomic-ai/nomic-embed-text-v1.5"
CACHE_DIR = REPO_ROOT / ".cache" / "b1_retriever"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR = REPO_ROOT / "results" / "phase_6d"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def compute_exact_sign_test(scores_before: List[float], scores_after: List[float]) -> Dict[str, Any]:
    """Compute exact two-sided binomial sign test on discordant pairs."""
    a = np.array(scores_before, dtype=float)
    b = np.array(scores_after, dtype=float)
    valid = (~np.isnan(a)) & (~np.isnan(b))
    a, b = a[valid], b[valid]

    wins = int(np.sum(b > a))
    losses = int(np.sum(b < a))
    ties = int(np.sum(b == a))
    n_discordant = wins + losses

    if n_discordant == 0:
        p_val = 1.0
    else:
        res = binomtest(k=wins, n=n_discordant, p=0.5, alternative="two-sided")
        p_val = float(res.pvalue)

    return {
        "wins": wins,
        "ties": ties,
        "losses": losses,
        "n_discordant": n_discordant,
        "sign_p": round(p_val, 4),
    }


def evaluate_dual_attribution(
    docs: List[Document],
    gt_name: str,
    group_alias_map: Dict[str, Dict[str, Any]]
) -> Dict[str, Dict[str, float]]:
    raw_gt_norm = normalize_group_name(gt_name)
    all_gt_aliases: Set[str] = {raw_gt_norm}
    target_gid = None

    for gid, gdata in group_alias_map.items():
        canonical_norm = normalize_group_name(gdata.get("canonical_name", ""))
        alias_norms = {normalize_group_name(a) for a in gdata.get("aliases", [])}
        if raw_gt_norm == canonical_norm or raw_gt_norm in alias_norms or any(a in raw_gt_norm for a in alias_norms if len(a) > 3):
            target_gid = gid.lower()
            all_gt_aliases.add(target_gid)
            all_gt_aliases.add(canonical_norm)
            all_gt_aliases.update(alias_norms)

    obj_ranks: List[int] = []
    txt_ranks: List[int] = []

    for doc in docs:
        doc_text = doc.page_content if hasattr(doc, "page_content") else str(doc)
        doc_meta = doc.metadata if hasattr(doc, "metadata") else {}
        doc_meta_id = doc_meta.get("mitre_id", "").lower()
        doc_aliases = [normalize_group_name(a) for a in doc_meta.get("aliases", [])]

        is_obj = 0
        if target_gid and (doc_meta_id == target_gid or doc_meta.get("stix_id", "").lower() == target_gid):
            is_obj = 1
        elif doc_meta_id and doc_meta_id in all_gt_aliases:
            is_obj = 1
        elif any(a in all_gt_aliases for a in doc_aliases if a):
            is_obj = 1
        obj_ranks.append(is_obj)

        is_txt = is_obj
        if not is_txt:
            doc_text_norm = normalize_group_name(doc_text)
            for alias in all_gt_aliases:
                if len(alias) >= 4 and alias in doc_text_norm:
                    is_txt = 1
                    break
        txt_ranks.append(is_txt)

    def calc(ranks):
        r10 = 1.0 if any(ranks[:10]) else 0.0
        mrr = 0.0
        for idx, rel in enumerate(ranks):
            if rel:
                mrr = 1.0 / (idx + 1)
                break
        return r10, mrr

    obj_r10, obj_mrr = calc(obj_ranks)
    txt_r10, txt_mrr = calc(txt_ranks)

    return {
        "object_level": {"Recall@10": obj_r10, "MRR": obj_mrr},
        "text_inclusive": {"Recall@10": txt_r10, "MRR": txt_mrr},
    }


class B1DenseRetriever:
    """Long-context dense embedding retriever (no chunking) with FAISS cosine indexing."""

    def __init__(self, stix_kb: STIXKnowledgeBase, model_name: str = MODEL_NAME):
        self.model_name = model_name
        self.stix_kb = stix_kb
        
        import torch
        import transformers

        # Patch get_extended_attention_mask for transformers 5.x compatibility with nomic-bert
        if not hasattr(transformers.PreTrainedModel, "get_extended_attention_mask"):
            def get_extended_attention_mask(self, attention_mask, input_shape, device=None, dtype=None):
                if dtype is None:
                    dtype = getattr(self, "dtype", torch.float32)
                if attention_mask.dim() == 3:
                    extended_attention_mask = attention_mask[:, None, :, :]
                elif attention_mask.dim() == 2:
                    extended_attention_mask = attention_mask[:, None, None, :]
                else:
                    raise ValueError(f"Wrong shape for attention_mask {attention_mask.shape}")
                extended_attention_mask = extended_attention_mask.to(dtype=dtype)
                extended_attention_mask = (1.0 - extended_attention_mask) * torch.finfo(dtype).min
                return extended_attention_mask

            transformers.PreTrainedModel.get_extended_attention_mask = get_extended_attention_mask

        from sentence_transformers import SentenceTransformer
        print(f"Loading B1 model: {model_name} (trust_remote_code=True)...", flush=True)
        self.model = SentenceTransformer(model_name, trust_remote_code=True)
        print(f"Loaded {model_name}. max_seq_length={self.model.max_seq_length}", flush=True)

        # 1. Build unchunked raw documents from STIX KB
        print("Extracting raw unchunked STIX documents...", flush=True)
        self.raw_docs = build_stix_raw_documents(stix_kb)
        print(f"Total unchunked STIX documents: {len(self.raw_docs)}", flush=True)

        # 2. Compute or load document embeddings
        emb_cache_file = CACHE_DIR / f"b1_doc_embs_{len(self.raw_docs)}.npy"
        if emb_cache_file.exists():
            print(f"Loading cached document embeddings from {emb_cache_file}...", flush=True)
            self.doc_embeddings = np.load(emb_cache_file)
        else:
            print("Encoding raw documents on CPU with B1...", flush=True)
            doc_texts = [f"search_document: {d.page_content}" for d in self.raw_docs]
            self.doc_embeddings = self.model.encode(
                doc_texts, batch_size=8, show_progress_bar=True, normalize_embeddings=True
            )
            np.save(emb_cache_file, self.doc_embeddings)
            print(f"Saved document embeddings to {emb_cache_file}", flush=True)

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        target_domain: Optional[str] = None,
        stix_id_to_domains: Optional[Dict] = None,
        mitre_id_to_domains: Optional[Dict] = None,
    ) -> List[Document]:
        """Encode query and return top-k cosine similarity raw documents."""
        q_text = f"search_query: {query}"
        q_emb = self.model.encode([q_text], normalize_embeddings=True)[0]

        # Cosine similarity via inner product on normalized vectors
        scores = np.dot(self.doc_embeddings, q_emb)

        # Sort descending
        ranked_indices = np.argsort(scores)[::-1]

        selected_docs = []
        for idx in ranked_indices:
            doc = self.raw_docs[idx]
            if target_domain and stix_id_to_domains:
                if not doc_matches_domain(doc, target_domain, stix_id_to_domains, mitre_id_to_domains):
                    continue
            selected_docs.append(doc)
            if len(selected_docs) >= top_k:
                break

        return selected_docs


def run_b1_robustness():
    print("=" * 80)
    print("PHASE 6D PART D: B1 RETRIEVER ROBUSTNESS EVALUATION")
    print("=" * 80)

    stix_all = load_stix_all_bundles()
    group_alias_map = stix_all.get_group_alias_map()
    stix_id_to_domains, mitre_id_to_domains = build_stix_domain_maps(stix_all)
    intrusion_sets, software, software_to_groups, software_weights = build_stix_indices(stix_all)
    matchers = build_alias_matchers(intrusion_sets, software)

    retriever = B1DenseRetriever(stix_kb=stix_all)

    # 1. cti-taa Evaluation (V0, V0h, Vrel)
    print("\n" + "=" * 70)
    print("EVALUATING cti-taa UNDER B1 (V0, V0h, Vrel)")
    print("=" * 70)

    df_taa = load_benchmark_dataset("cti-taa").df
    taa_scores = defaultdict(lambda: defaultdict(list))

    for q_idx, row in df_taa.iterrows():
        raw_query = str(row["query"])
        gt = str(row.get("ground_truth", ""))
        _, body, _ = split_query(raw_query)

        q_v0 = raw_query
        q_v0h = body
        q_vrel, _ = expand_vrel(body, matchers, intrusion_sets, software_to_groups, software_weights)

        for arm, q_text in [("V0", q_v0), ("V0h", q_v0h), ("Vrel", q_vrel)]:
            docs = retriever.retrieve(q_text, top_k=10)
            m_dual = evaluate_dual_attribution(docs, gt, group_alias_map)
            taa_scores[arm]["Object_Recall@10"].append(m_dual["object_level"]["Recall@10"])
            taa_scores[arm]["Object_MRR"].append(m_dual["object_level"]["MRR"])
            taa_scores[arm]["Alias_Recall@10"].append(m_dual["text_inclusive"]["Recall@10"])
            taa_scores[arm]["Alias_MRR"].append(m_dual["text_inclusive"]["MRR"])

    # 2. cti-ate and CTI-ATTACK Evaluation (E0' raw vs E0'-HD)
    print("\n" + "=" * 70)
    print("EVALUATING cti-ate & CTI-ATTACK UNDER B1 (E0' raw vs E0'-HD)")
    print("=" * 70)

    tech_scores = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    for ds_name in ["cti-ate", "CTI-ATTACK"]:
        df = load_benchmark_dataset(ds_name).df
        print(f"Running B1 on {ds_name} ({len(df)} queries)...", flush=True)

        for q_idx, row in df.iterrows():
            raw_query = str(row["query"])
            gt = str(row.get("ground_truth", ""))
            instr, body, _ = split_query(raw_query)

            # Target domain for mobile queries in cti-ate
            target_dom = "mobile-attack" if (ds_name == "cti-ate" and "MITRE Mobile" in instr) else None

            # E0_prime_raw: raw query without domain filter
            docs_raw = retriever.retrieve(raw_query, top_k=10)
            # E0_prime_HD: body query with domain filter
            docs_hd = retriever.retrieve(
                body, top_k=10,
                target_domain=target_dom,
                stix_id_to_domains=stix_id_to_domains,
                mitre_id_to_domains=mitre_id_to_domains
            )

            for arm, docs in [("E0_prime_raw", docs_raw), ("E0_prime_HD", docs_hd)]:
                m_sub = compute_retrieval_metrics_technique(docs, gt, k_values=[10], subtechnique_parent_credit=True)
                m_exact = compute_retrieval_metrics_technique(docs, gt, k_values=[10], subtechnique_parent_credit=False)
                tech_scores[ds_name][arm]["Subtech_Recall@10"].append(m_sub["Recall@10"])
                tech_scores[ds_name][arm]["Subtech_MRR"].append(m_sub["MRR"])
                tech_scores[ds_name][arm]["Exact_Recall@10"].append(m_exact["Recall@10"])
                tech_scores[ds_name][arm]["Exact_MRR"].append(m_exact["MRR"])

    # 3. Compute Contrasts
    print("\n" + "=" * 80)
    print("B1 RETRIEVER ROBUSTNESS CONTRASTS & COMPARISONS")
    print("=" * 80)

    contrast_records = []

    # cti-taa Contrasts
    for c_name, ctrl_arm, treat_arm, c_desc in [
        ("V0h vs V0", "V0", "V0h", "Hygiene effect under B1"),
        ("Vrel vs V0h", "V0h", "Vrel", "Relationship effect under B1"),
        ("Vrel vs V0", "V0", "Vrel", "Total effect under B1"),
    ]:
        for met in ["Object_Recall@10", "Alias_Recall@10", "Object_MRR"]:
            c_vals = taa_scores[ctrl_arm][met]
            t_vals = taa_scores[treat_arm][met]
            boot = compute_paired_bootstrap_ci(c_vals, t_vals, n_resamples=10000, seed=42)
            st = compute_exact_sign_test(c_vals, t_vals)

            rec = {
                "baseline": "B1-LongContext",
                "model": MODEL_NAME,
                "dataset": "cti-taa",
                "contrast": c_name,
                "description": c_desc,
                "metric": met,
                "control_arm": ctrl_arm,
                "treatment_arm": treat_arm,
                "control_mean": boot["mean_before"],
                "treatment_mean": boot["mean_after"],
                "delta": boot["mean_delta"],
                "ci_lower_95": boot["ci_lower"],
                "ci_upper_95": boot["ci_upper"],
                "bootstrap_p": boot["p_value"],
                "wins": st["wins"],
                "ties": st["ties"],
                "losses": st["losses"],
                "exact_sign_p": st["sign_p"],
            }
            contrast_records.append(rec)
            if met == "Object_Recall@10":
                sign_str = "+" if rec["delta"] >= 0 else ""
                print(
                    f"[B1 | cti-taa] {c_name:<12} ({met}): ctrl={rec['control_mean']:.4f}, treat={rec['treatment_mean']:.4f}, "
                    f"Delta={sign_str}{rec['delta']:.4f} [95% CI {rec['ci_lower_95']:.4f}, {rec['ci_upper_95']:.4f}], "
                    f"W/T/L={rec['wins']}/{rec['ties']}/{rec['losses']}, p_exact={rec['exact_sign_p']:.4f}"
                )

    # cti-ate and CTI-ATTACK Contrasts
    for ds_name in ["cti-ate", "CTI-ATTACK"]:
        for met in ["Subtech_Recall@10", "Exact_Recall@10", "Subtech_MRR"]:
            c_vals = tech_scores[ds_name]["E0_prime_raw"][met]
            t_vals = tech_scores[ds_name]["E0_prime_HD"][met]
            boot = compute_paired_bootstrap_ci(c_vals, t_vals, n_resamples=10000, seed=42)
            st = compute_exact_sign_test(c_vals, t_vals)

            rec = {
                "baseline": "B1-LongContext",
                "model": MODEL_NAME,
                "dataset": ds_name,
                "contrast": "E0_prime_HD vs E0_prime_raw",
                "description": "HD preprocessing effect under B1",
                "metric": met,
                "control_arm": "E0_prime_raw",
                "treatment_arm": "E0_prime_HD",
                "control_mean": boot["mean_before"],
                "treatment_mean": boot["mean_after"],
                "delta": boot["mean_delta"],
                "ci_lower_95": boot["ci_lower"],
                "ci_upper_95": boot["ci_upper"],
                "bootstrap_p": boot["p_value"],
                "wins": st["wins"],
                "ties": st["ties"],
                "losses": st["losses"],
                "exact_sign_p": st["sign_p"],
            }
            contrast_records.append(rec)
            if met == "Subtech_Recall@10":
                sign_str = "+" if rec["delta"] >= 0 else ""
                print(
                    f"[B1 | {ds_name:<10}] E0_prime_HD vs raw ({met}): ctrl={rec['control_mean']:.4f}, treat={rec['treatment_mean']:.4f}, "
                    f"Delta={sign_str}{rec['delta']:.4f} [95% CI {rec['ci_lower_95']:.4f}, {rec['ci_upper_95']:.4f}], "
                    f"W/T/L={rec['wins']}/{rec['ties']}/{rec['losses']}, p_exact={rec['exact_sign_p']:.4f}"
                )

    # Save to CSV and JSON
    df_contrasts = pd.DataFrame(contrast_records)
    csv_file = OUT_DIR / "b1_robustness_contrasts.csv"
    json_file = OUT_DIR / "b1_robustness_metrics.json"

    df_contrasts.to_csv(csv_file, index=False)
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(contrast_records, f, indent=2)

    print(f"\nSaved B1 robustness contrasts to {csv_file} and {json_file}")


if __name__ == "__main__":
    run_b1_robustness()
