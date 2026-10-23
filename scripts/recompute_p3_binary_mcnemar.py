"""Phase 5 Addendum: Binary Outcomes Exact Sign Test (McNemar) for Family P3.

Addendum Requirement 2:
"Binary outcomes (object-level Recall, accuracy): use the exact two-sided sign test (McNemar) in addition
 to the bootstrap, and state which procedure each p-value uses. Fix any CI/p mismatch."
Addendum Requirement 5:
"Attribution tables: object-level credit is primary, text-inclusive secondary."
"""

import json
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd
from scipy.stats import binomtest

REPO_ROOT = Path(__file__).resolve().parent.parent

def run_p3_mcnemar_audit():
    p5_dir = REPO_ROOT / "results" / "phase_5"
    assets_dir = p5_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    o1_path = p5_dir / "o1_phase5_benchmark_results.json"
    with open(o1_path, "r", encoding="utf-8") as f:
        o1_data = json.load(f)

    p3_contrasts = o1_data["family_p3_contrasts"]

    # For each contrast, if metric is Recall@10, compute exact McNemar sign test
    updated_contrasts = []
    for c in p3_contrasts:
        c_copy = dict(c)
        metric = c["metric"]
        wtl = c["wtl"]  # format "wins/ties/losses"
        wins, ties, losses = [int(x) for x in wtl.split("/")]

        if metric == "Recall@10":
            # Binary outcome: y_i in {0, 1}
            # Discordant pairs: b = wins (treatment=1, control=0), c = losses (treatment=0, control=1)
            b = wins
            losses_c = losses
            n_discordant = b + losses_c
            if n_discordant == 0:
                p_exact = 1.0
            else:
                res = binomtest(b, n_discordant, p=0.5, alternative="two-sided")
                p_exact = float(res.pvalue)

            c_copy["p_exact_mcnemar"] = round(p_exact, 4)
            c_copy["p_boot_resamples"] = round(c["raw_p"], 4)
            c_copy["test_procedure"] = "Exact two-sided binomial sign test (McNemar) & Paired bootstrap (N=10,000)"
            c_copy["n_discordant"] = n_discordant
        else:
            # Continuous outcome (MRR): exact sign test over non-zero diffs
            b = wins
            losses_c = losses
            n_discordant = b + losses_c
            if n_discordant == 0:
                p_exact = 1.0
            else:
                res = binomtest(b, n_discordant, p=0.5, alternative="two-sided")
                p_exact = float(res.pvalue)

            c_copy["p_exact_mcnemar"] = round(p_exact, 4)
            c_copy["p_boot_resamples"] = round(c["raw_p"], 4)
            c_copy["test_procedure"] = "Paired bootstrap (primary for MRR, N=10,000) & Exact sign test"
            c_copy["n_discordant"] = n_discordant

        updated_contrasts.append(c_copy)

    o1_data["family_p3_contrasts_mcnemar"] = updated_contrasts
    with open(o1_path, "w", encoding="utf-8") as f:
        json.dump(o1_data, f, indent=2)
    print(f"Updated {o1_path} with exact McNemar sign test statistics.")

    # Generate CSV and Markdown table
    df_p3 = pd.DataFrame([
        {
            "Test ID": c["test_id"],
            "Credit Rule": c["credit_rule"],
            "Baseline": c["baseline"],
            "Contrast": c["contrast"],
            "Metric": c["metric"],
            "Treatment": c["treatment_mean"],
            "Control": c["control_mean"],
            "Delta": c["delta"],
            "95% CI": f"[{c['ci_95'][0]:+.4f}, {c['ci_95'][1]:+.4f}]",
            "W/T/L": c["wtl"],
            "p_exact (McNemar)": f"{c['p_exact_mcnemar']:.4f}",
            "p_boot (10k)": f"{c['p_boot_resamples']:.4f}",
            "Holm Alpha": c["holm_alpha"],
            "Decision": c["decision"],
        }
        for c in updated_contrasts
    ])

    csv_path = assets_dir / "table_family_p3_mcnemar.csv"
    df_p3.to_csv(csv_path, index=False)
    print(f"Saved {csv_path}")

    # Generate Markdown Table separating primary (object-level) and secondary (text-inclusive)
    md_lines = [
        "### Table: Family P3 Contrasts with Exact Sign Test (McNemar) and Bootstrap",
        "",
        "#### Primary Attribution Metric: Object-Level Credit",
        "| Test ID | Baseline | Contrast | Metric | Treat | Ctrl | Delta | 95% Bootstrap CI | W/T/L | $p_{\\text{exact}}$ (McNemar) | $p_{\\text{boot}}$ (10k) | Holm $\\alpha$ | Decision |",
        "| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |",
    ]
    for c in updated_contrasts:
        if c["credit_rule"] == "object_level":
            p_ex = "< 0.0001" if c["p_exact_mcnemar"] == 0.0 else f"{c['p_exact_mcnemar']:.4f}"
            p_bt = "< 0.0001" if c["p_boot_resamples"] == 0.0 else f"{c['p_boot_resamples']:.4f}"
            md_lines.append(
                f"| **{c['test_id']}** | {c['baseline']} | {c['contrast']} | {c['metric']} | {c['treatment_mean']:.4f} | {c['control_mean']:.4f} | {c['delta']:+.4f} | [{c['ci_95'][0]:+.4f}, {c['ci_95'][1]:+.4f}] | {c['wtl']} | {p_ex} | {p_bt} | {c['holm_alpha']:.5f} | {c['decision']} |"
            )

    md_lines.extend([
        "",
        "#### Secondary Attribution Metric: Text-Inclusive Credit",
        "| Test ID | Baseline | Contrast | Metric | Treat | Ctrl | Delta | 95% Bootstrap CI | W/T/L | $p_{\\text{exact}}$ (McNemar) | $p_{\\text{boot}}$ (10k) | Holm $\\alpha$ | Decision |",
        "| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |",
    ])
    for c in updated_contrasts:
        if c["credit_rule"] == "text_inclusive":
            p_ex = "< 0.0001" if c["p_exact_mcnemar"] == 0.0 else f"{c['p_exact_mcnemar']:.4f}"
            p_bt = "< 0.0001" if c["p_boot_resamples"] == 0.0 else f"{c['p_boot_resamples']:.4f}"
            md_lines.append(
                f"| **{c['test_id']}** | {c['baseline']} | {c['contrast']} | {c['metric']} | {c['treatment_mean']:.4f} | {c['control_mean']:.4f} | {c['delta']:+.4f} | [{c['ci_95'][0]:+.4f}, {c['ci_95'][1]:+.4f}] | {c['wtl']} | {p_ex} | {p_bt} | {c['holm_alpha']:.5f} | {c['decision']} |"
            )

    md_path = assets_dir / "table_family_p3_mcnemar.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines) + "\n")
    print(f"Saved {md_path}")

if __name__ == "__main__":
    run_p3_mcnemar_audit()
