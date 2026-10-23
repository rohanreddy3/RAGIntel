import os
import json
import re
import sys
from pathlib import Path
from collections import defaultdict
import pandas as pd
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.retrieval_eval import extract_technique_ids_from_text, parse_ground_truth_techniques
from src.data_loader import load_benchmark_dataset
import tiktoken

def run_failure_audit():
    enc = tiktoken.get_encoding("cl100k_base")
    cache_dir = REPO_ROOT / ".cache" / "api_runner"

    # Load datasets
    df_ate = load_benchmark_dataset("cti-ate").df
    df_attack = load_benchmark_dataset("CTI-ATTACK").df
    df_taa = load_benchmark_dataset("cti-taa").df

    gt_map = {
        "cti-ate": [set(parse_ground_truth_techniques(str(v))) for v in df_ate["ground_truth"]],
        "CTI-ATTACK": [set(parse_ground_truth_techniques(str(v))) for v in df_attack["ground_truth"]],
        "cti-taa": [str(v) for v in df_taa["ground_truth"]]
    }

    # Abstention patterns
    abstention_regex = re.compile(
        r"(not in (the )?context|cannot determine|cannot be determined|unable to determine|"
        r"not provided in (the )?context|not mentioned in (the )?context|"
        r"does not provide|does not contain|no techniques? (are |were )?mentioned|"
        r"insufficient context|insufficient information)",
        re.I
    )

    # Arms to audit:
    # 1. LLM-only
    # 2. E0'
    # 3. E1b-MIXED
    # 4. cti-taa V0
    # 5. cti-taa V1
    
    records_by_arm = defaultdict(list)
    for fname in os.listdir(cache_dir):
        if not fname.endswith(".json") or fname == "known_reset.json":
            continue
        with open(cache_dir / fname, "r", encoding="utf-8") as fp:
            d = json.load(fp)
            arm = d.get("arm")
            ds = d.get("dataset")
            # harmonize arm naming
            if arm == "E0_prime":
                records_by_arm["E0'"].append(d)
            elif arm == "E1b_mixed":
                records_by_arm["E1b-MIXED"].append(d)
            elif arm == "LLM-only":
                records_by_arm["LLM-only"].append(d)
            elif arm == "cti-taa_B2_V0":
                records_by_arm["cti-taa V0"].append(d)
            elif arm == "cti-taa_B2_V1":
                records_by_arm["cti-taa V1"].append(d)

    audit_summary = {}

    for arm_name in ["LLM-only", "E0'", "E1b-MIXED", "cti-taa V0", "cti-taa V1"]:
        items = records_by_arm[arm_name]
        total_count = len(items)
        empty_count = 0
        error_count = 0
        hit_512_cap_count = 0
        abstention_count = 0
        zero_parsed_tech_count = 0

        all_f1_sub = []
        clean_f1_sub = []

        for item in items:
            raw = str(item.get("raw_answer", ""))
            clean_text = raw.strip()
            ds = item.get("dataset")
            row_idx = int(item.get("row_idx", 0))

            # Empty
            if not clean_text:
                empty_count += 1

            # Error / blocked
            if "error" in item or "error" in raw.lower() and len(raw) < 50:
                error_count += 1

            # Hit 512 cap
            num_tokens = len(enc.encode(raw))
            if num_tokens >= 512:
                hit_512_cap_count += 1

            # Abstention
            is_abstaining = bool(abstention_regex.search(raw))
            if is_abstaining:
                abstention_count += 1

            # Parsed techniques
            if ds in ["cti-ate", "CTI-ATTACK"]:
                gt_techs = gt_map[ds][row_idx] if row_idx < len(gt_map[ds]) else set()
                parsed = extract_technique_ids_from_text(raw)
                if len(parsed) == 0:
                    zero_parsed_tech_count += 1

                # Sub-credit F1
                credited_pred = set(parsed)
                for t in parsed:
                    if "." in t:
                        credited_pred.add(t.split(".")[0])
                tp = len(credited_pred & gt_techs)
                p = tp / len(credited_pred) if credited_pred else 0.0
                r = tp / len(gt_techs) if gt_techs else 0.0
                f1 = (2 * p * r / (p + r)) if (p + r) > 0 else 0.0
                all_f1_sub.append(f1)

                # Clean / non-abstaining parsed subset
                if (not is_abstaining) and len(parsed) > 0 and (not not clean_text):
                    clean_f1_sub.append(f1)

        audit_summary[arm_name] = {
            "total_rows": total_count,
            "empty": empty_count,
            "error_blocked": error_count,
            "hit_512_cap": hit_512_cap_count,
            "abstention": abstention_count,
            "zero_parsed_tech_ids": zero_parsed_tech_count if arm_name not in ["cti-taa V0", "cti-taa V1"] else "N/A (attribution)",
            "mean_f1_all": round(float(np.mean(all_f1_sub)), 4) if all_f1_sub else "N/A (attribution)",
            "mean_f1_non_abstaining_parsed": round(float(np.mean(clean_f1_sub)), 4) if clean_f1_sub else "N/A (attribution)",
            "non_abstaining_parsed_count": len(clean_f1_sub) if all_f1_sub else "N/A"
        }

    out_path = REPO_ROOT / "results" / "phase_4b" / "generation_failure_audit.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fp:
        json.dump(audit_summary, fp, indent=2)

    print("=== GENERATION FAILURE AUDIT RESULTS ===")
    for arm_name, stats in audit_summary.items():
        print(f"\nArm: {arm_name} (Total rows: {stats['total_rows']})")
        print(f"  Empty: {stats['empty']}")
        print(f"  Error/Blocked: {stats['error_blocked']}")
        print(f"  Hit 512-token cap: {stats['hit_512_cap']}")
        print(f"  Abstention ('not in context'): {stats['abstention']}")
        print(f"  Zero parsed technique IDs: {stats['zero_parsed_tech_ids']}")
        print(f"  F1 (all rows): {stats['mean_f1_all']}")
        print(f"  F1 (non-abstaining parsed): {stats['mean_f1_non_abstaining_parsed']} (N={stats['non_abstaining_parsed_count']})")

if __name__ == "__main__":
    run_failure_audit()
