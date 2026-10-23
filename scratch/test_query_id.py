import hashlib
import json
import sys
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import pandas as pd
from src.data_loader import load_benchmark_dataset

def norm_q(text: str) -> str:
    return str(text).strip()

def compute_qid(text: str) -> str:
    return hashlib.sha1(norm_q(text).encode("utf-8")).hexdigest()[:12]

# Map each (dataset, row_idx) -> (query, query_id)
dataset_qids = {}
for name in ["cti-ate", "cti-taa", "CTI-ATTACK"]:
    ds = load_benchmark_dataset(name)
    dataset_qids[name] = {}
    for idx, row in ds.df.iterrows():
        q = row["query"]
        dataset_qids[name][int(idx)] = {
            "query": q,
            "query_id": compute_qid(q),
        }

print("Loaded canonical dataset query_ids:")
for name in dataset_qids:
    print(f"  {name}: {len(dataset_qids[name])} rows")

# Check 3C cache structure
p_3c = Path("results/phase_3/top50_phase3c_chunks.json")
with open(p_3c, "r", encoding="utf-8") as f:
    c_3c = json.load(f)

for ds in c_3c:
    print(f"\n3C dataset {ds}: baselines={list(c_3c[ds].keys())}")
    for b in c_3c[ds]:
        print(f"  baseline {b}: arms={list(c_3c[ds][b].keys())}")
        for arm in list(c_3c[ds][b].keys())[:1]:
            queries = c_3c[ds][b][arm]
            print(f"    arm {arm}: type={type(queries)}, len={len(queries)}")
            if isinstance(queries, list) and len(queries) > 0:
                print(f"      sample query dict keys: {list(queries[0].keys())}")
                if "query" in queries[0]:
                    print(f"      sample query: {queries[0]['query'][:60]!r}")
                    print(f"      row 0 match QID? {compute_qid(queries[0]['query']) == dataset_qids[ds][0]['query_id']}")

# Check 3B cache structure
p_3b = Path("results/phase_3/top50_ranked_chunks.json")
with open(p_3b, "r", encoding="utf-8") as f:
    c_3b = json.load(f)

for ds in c_3b:
    print(f"\n3B dataset {ds}: baselines={list(c_3b[ds].keys())}")
    for b in c_3b[ds]:
        print(f"  baseline {b}: arms={list(c_3b[ds][b].keys())}")
        for arm in list(c_3b[ds][b].keys())[:1]:
            queries = c_3b[ds][b][arm]
            print(f"    arm {arm}: type={type(queries)}, len={len(queries)}")
            if isinstance(queries, list) and len(queries) > 0:
                print(f"      sample query dict keys: {list(queries[0].keys())}")
                if "query" in queries[0]:
                    print(f"      sample query: {queries[0]['query'][:60]!r}")
                    print(f"      row 0 match QID? {compute_qid(queries[0]['query']) == dataset_qids[ds][0]['query_id']}")

# Check Phase 2 checkpoint
p_p2 = Path("results/phase_2/p1_eval_checkpoint.json")
with open(p_p2, "r", encoding="utf-8") as f:
    c_p2 = json.load(f)
print("\nP2 checkpoint top keys:", list(c_p2.keys())[:5])
for k in list(c_p2.keys())[:2]:
    val = c_p2[k]
    print(f"  P2 key {k}: len={len(val)}, sample keys={list(val[0].keys())}")
    if "query" in val[0]:
        print(f"    sample query: {val[0]['query'][:60]!r}")
