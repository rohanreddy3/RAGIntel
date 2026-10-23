import math
import pytest
from src.retrieval_eval import (
    compute_retrieval_metrics_technique,
    compute_paired_bootstrap_ci,
)

class MockDoc:
    def __init__(self, content: str, mitre_id: str = ""):
        self.page_content = content
        self.metadata = {"mitre_id": mitre_id}

def test_reachable_metrics_with_unreachable_ids_toy_example():
    """Toy example proving how denominators are computed for reachable vs raw IDs."""
    reachable_kb = {"T1059", "T1071", "T1082"}
    
    # Query A: Ground truth has 1 reachable ID (T1059) and 1 unreachable ID (T1426)
    # Total GT = 2, Reachable GT = 1
    docs = [MockDoc("Command execution using powershell", mitre_id="T1059")]
    metrics = compute_retrieval_metrics_technique(
        retrieved_docs=docs,
        ground_truth_str="T1059, T1426",
        reachable_ids=reachable_kb,
        k_values=[1, 5, 10],
    )
    
    # Raw Recall denominator is 2: 1/2 = 0.5
    assert metrics["Recall@10"] == 0.5
    # Reachable Recall denominator is 1: 1/1 = 1.0!
    assert metrics["Reachable_Recall@10"] == 1.0
    assert metrics["num_gt"] == 2
    assert metrics["num_reachable_gt"] == 1

def test_reachable_metrics_all_unreachable_query():
    """Query where 100% of ground truth IDs are unreachable in the KB."""
    reachable_kb = {"T1059", "T1071"}
    
    # Ground truth only has Mobile techniques (unreachable in Enterprise KB)
    docs = [MockDoc("Some text", mitre_id="T1059")]
    metrics = compute_retrieval_metrics_technique(
        retrieved_docs=docs,
        ground_truth_str="T1426, T1417",
        reachable_ids=reachable_kb,
        k_values=[1, 5, 10],
    )
    
    # Raw Recall is 0.0 (retrieved 0 out of 2)
    assert metrics["Recall@10"] == 0.0
    # Reachable Recall is NaN because query has 0 reachable items (unreachable query)
    assert math.isnan(metrics["Reachable_Recall@10"])
    assert math.isnan(metrics["Reachable_MRR"])
    assert metrics["num_gt"] == 2
    assert metrics["num_reachable_gt"] == 0

def test_subtechnique_credit_direction_sub_credits_parent():
    """Test direction: retrieved sub-technique satisfies generic parent ground truth."""
    # Case 1: GT is parent T1059. Retrieved is sub-technique T1059.001.
    docs = [MockDoc("Powershell script execution", mitre_id="T1059.001")]
    
    # Strict exact-ID match: does NOT match
    metrics_strict = compute_retrieval_metrics_technique(
        retrieved_docs=docs,
        ground_truth_str="T1059",
        subtechnique_parent_credit=False,
    )
    assert metrics_strict["Recall@10"] == 0.0
    
    # Subtechnique credit (sub_credits_parent): DOES match
    metrics_sub = compute_retrieval_metrics_technique(
        retrieved_docs=docs,
        ground_truth_str="T1059",
        subtechnique_parent_credit=True,
        subtechnique_direction="sub_credits_parent",
    )
    assert metrics_sub["Recall@10"] == 1.0
    assert metrics_sub["MRR"] == 1.0

def test_subtechnique_credit_direction_parent_does_not_satisfy_sub():
    """Test direction: retrieved generic parent does NOT satisfy specific sub-technique GT."""
    # Case 2: GT is specific sub-technique T1059.001. Retrieved is generic parent T1059.
    docs = [MockDoc("Command execution interpreter", mitre_id="T1059")]
    
    metrics_sub = compute_retrieval_metrics_technique(
        retrieved_docs=docs,
        ground_truth_str="T1059.001",
        subtechnique_parent_credit=True,
        subtechnique_direction="sub_credits_parent",
    )
    # Generic parent does not satisfy specific sub-technique requirement
    assert metrics_sub["Recall@10"] == 0.0
    assert metrics_sub["MRR"] == 0.0

def test_paired_bootstrap_ci():
    """Test paired bootstrap 95% confidence intervals calculation."""
    before = [0.0, 0.1, 0.2, 0.0, 0.0, 0.3, 0.1, 0.2, 0.0, 0.1]
    after =  [0.1, 0.2, 0.3, 0.1, 0.0, 0.4, 0.2, 0.3, 0.1, 0.2]
    
    ci_res = compute_paired_bootstrap_ci(before, after, n_resamples=10000, seed=42)
    assert ci_res["mean_delta"] == 0.09
    assert ci_res["ci_lower"] > 0.0  # Confidently positive improvement
    assert ci_res["ci_upper"] >= ci_res["mean_delta"]
    assert ci_res["p_value"] < 0.05
