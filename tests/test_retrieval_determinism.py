"""Determinism unit test for HybridSTIXRetriever Baseline B3 (Step A1).

Verifies that B3 (sliding-window MaxSim pooling) executed twice produces
bit-exact and metric-exact results to 4 decimal places.
"""

import sys
from pathlib import Path
import pytest
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data_loader import load_stix_bundle
from src.retriever import HybridSTIXRetriever
from src.retrieval_eval import compute_retrieval_metrics_technique


def test_b3_retrieval_determinism():
    """Verify that running B3 retrieval across queries produces identical results."""
    kb = load_stix_bundle()
    retriever = HybridSTIXRetriever(stix_kb=kb, cache_dir=".cache/retriever_index")
    
    df = pd.read_excel("data/datasets/cti-ate.xlsx")
    test_indices = [0, 7, 14, 25, 58]  # sample of short, medium, long, and multi-window queries
    
    run1_results = []
    run2_results = []
    
    # Run 1
    for idx in test_indices:
        q = df.iloc[idx]["query"]
        gt = df.iloc[idx]["ground_truth"]
        docs = retriever.retrieve(q, top_k=10, enable_query_chunking=True)
        m = compute_retrieval_metrics_technique(docs, gt, k_values=[5, 10])
        doc_ids = [d.metadata.get("mitre_id") for d in docs]
        run1_results.append((doc_ids, m["Recall@5"], m["Recall@10"], m["MRR"], m["nDCG@10"]))
        
    # Run 2
    for idx in test_indices:
        q = df.iloc[idx]["query"]
        gt = df.iloc[idx]["ground_truth"]
        docs = retriever.retrieve(q, top_k=10, enable_query_chunking=True)
        m = compute_retrieval_metrics_technique(docs, gt, k_values=[5, 10])
        doc_ids = [d.metadata.get("mitre_id") for d in docs]
        run2_results.append((doc_ids, m["Recall@5"], m["Recall@10"], m["MRR"], m["nDCG@10"]))
        
    for i, idx in enumerate(test_indices):
        ids1, r5_1, r10_1, mrr1, ndcg1 = run1_results[i]
        ids2, r5_2, r10_2, mrr2, ndcg2 = run2_results[i]
        
        assert ids1 == ids2, f"Query {idx} retrieved doc IDs differed between run 1 and run 2: {ids1} vs {ids2}"
        assert abs(r5_1 - r5_2) < 1e-4, f"Query {idx} Recall@5 differed: {r5_1} vs {r5_2}"
        assert abs(r10_1 - r10_2) < 1e-4, f"Query {idx} Recall@10 differed: {r10_1} vs {r10_2}"
        assert abs(mrr1 - mrr2) < 1e-4, f"Query {idx} MRR differed: {mrr1} vs {mrr2}"
        assert abs(ndcg1 - ndcg2) < 1e-4, f"Query {idx} nDCG@10 differed: {ndcg1} vs {ndcg2}"
