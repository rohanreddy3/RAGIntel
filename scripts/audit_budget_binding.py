import json
import os
import sys

sys.path.insert(0, ".")

def audit_budget_binding():
    top_k_cap = 50
    budgets = [500, 1000, 2000, 4000]

    with open("results/phase_3/o2_phase3c_benchmark_results.json", "r") as f:
        data = json.load(f)["results"]["text_and_metadata"]

    # arms in Table 5
    arms = ["E0_prime", "E0_prime_tech", "E1a", "E1_mixed", "E1b_mixed", "E1c_mixed"]
    datasets = ["cti-ate", "CTI-ATTACK"]

    results = {}

    for ds in datasets:
        results[ds] = {}
        for arm in arms:
            results[ds][arm] = {}
            for b in budgets:
                summary = data[ds]["B2"][arm][str(b)]["summary"]
                mean_chunks = summary.get("num_docs", 0.0)
                mean_tokens = summary.get("tokens_used", 0.0)
                rec = summary.get("Recall_sub_credits_parent", 0.0)
                
                # Check if budget is binding
                # Top-k cap is 50 chunks. If mean_chunks hits ~50 and mean_tokens is significantly below budget b,
                # the budget was not binding (the retriever ran out of candidate chunks before filling the budget).
                is_binding = True
                flag_reason = "Binding"
                if mean_chunks >= 49.5 and mean_tokens < b * 0.95:
                    is_binding = False
                    flag_reason = f"Non-binding (Capped by top-k=50: {mean_tokens:.1f} < {b} tok)"

                results[ds][arm][str(b)] = {
                    "mean_chunks": round(mean_chunks, 2),
                    "mean_tokens": round(mean_tokens, 1),
                    "top_k_cap": top_k_cap,
                    "recall": round(rec, 4),
                    "is_binding": is_binding,
                    "flag_reason": flag_reason
                }

    out_path = "results/phase_4b/budget_binding_audit.json"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Saved audit to {out_path}")

    # Print summary table
    for ds in datasets:
        print(f"\n=== Dataset: {ds} ===")
        for arm in arms:
            row_str = f"{arm:15s} | "
            for b in budgets:
                cell = results[ds][arm][str(b)]
                bind_flag = "" if cell["is_binding"] else " [NOT BINDING]"
                row_str += f"B={b}: {cell['mean_chunks']:.1f}chk/{cell['mean_tokens']:.0f}tok{bind_flag} | "
            print(row_str)

if __name__ == "__main__":
    audit_budget_binding()
