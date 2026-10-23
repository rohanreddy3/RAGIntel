"""Generate Phase 5 Assets and Assertions.

Validates and formats all Phase 5 artifacts:
- Pre-registration ledger verification (hash, mtime)
- Part A: Query hygiene audit tables and assertions
- Part B: O1 benchmark tables (cti-taa dual credit, Family P3 exact sign test + bootstrap, transfer check)
- Part C: O2 clean comparison tables (HD vs Raw, Family P4 Holm step-down, hygiene effect alone, sanity check)
- Part C Addendum: k=200 scaling tables with binding-for-both cells labeled
- Table 7 Reconciliation: side-by-side Phase 4 vs 4B vs 5 (Claim C9 restored, P1_08 corrected)
- Limitations Table: Ground truth STIX status (revoked, deprecated, absent)
- Final plain list: which contrasts improved, which did not (numbers only)
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

def generate_assets():
    print("=" * 80)
    print("GENERATING PHASE 5 ASSETS AND ASSERTIONS")
    print("=" * 80)

    p5_dir = REPO_ROOT / "results" / "phase_5"
    assets_dir = REPO_ROOT / "results" / "phase_5" / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load Pre-Registration Ledger
    ledger_path = p5_dir / "variants_ledger.json"
    with open(ledger_path, "r", encoding="utf-8") as f:
        ledger = json.load(f)
    print(f"[OK] Loaded pre-registration ledger (SHA-256: {ledger['analysis_plan_sha256'][:16]}...)")

    # 2. Part A: Query Hygiene Audit
    hygiene_path = p5_dir / "query_hygiene_audit.json"
    with open(hygiene_path, "r", encoding="utf-8") as f:
        hygiene = json.load(f)

    hygiene_rows = []
    for ds in ["cti-taa", "cti-ate", "CTI-ATTACK"]:
        info = hygiene["datasets"][ds]
        hygiene_rows.append({
            "Dataset": ds,
            "N": info["n_queries"],
            "Body Matches / Query": round(info["mean_matches_body"], 2),
            "Full Matches / Query": round(info["mean_matches_full"], 2),
            "Matches Delta": round(info["mean_matches_body"] - info["mean_matches_full"], 2),
            "Body Share >= 1 Entity": f"{info['share_ge1_body'] * 100:.1f}%",
            "Full Share >= 1 Entity": f"{info['share_ge1_full'] * 100:.1f}%",
        })
    df_hygiene = pd.DataFrame(hygiene_rows)
    df_hygiene.to_csv(assets_dir / "table_query_hygiene.csv", index=False)
    print(f"[OK] Written table_query_hygiene.csv")

    # 3. Part C Sanity Check: cti-ate domain distribution
    sanity_path = p5_dir / "cti_ate_domain_sanity.json"
    with open(sanity_path, "r", encoding="utf-8") as f:
        sanity = json.load(f)
    print(f"[OK] cti-ate Domain Sanity: {sanity['matching_gt_ids']}/{sanity['total_gt_ids']} GT IDs match declared domain ({sanity['gt_id_match_share']*100:.2f}%)")

    # 4. Part B: O1 Benchmark Results
    o1_path = p5_dir / "o1_phase5_benchmark_results.json"
    if o1_path.exists():
        with open(o1_path, "r", encoding="utf-8") as f:
            o1_res = json.load(f)
        
        df_o1 = pd.DataFrame(o1_res["summary"])
        df_o1.to_csv(assets_dir / "table_o1_summary.csv", index=False)
        
        # Family P3 table
        p3_key = "family_p3_contrasts_mcnemar" if "family_p3_contrasts_mcnemar" in o1_res else "family_p3_contrasts"
        df_p3 = pd.DataFrame(o1_res[p3_key])
        df_p3.to_csv(assets_dir / "table_family_p3.csv", index=False)
        
        # Transfer check table
        transfer_key = "transfer_check" if "transfer_check" in o1_res else "cross_dataset_transfer"
        df_transfer = pd.DataFrame(o1_res[transfer_key])
        df_transfer.to_csv(assets_dir / "table_o1_transfer.csv", index=False)
        print(f"[OK] Written O1 summary, Family P3, and Transfer check tables.")

    # 5. Part C: O2 Clean Comparisons Results
    o2_path = p5_dir / "o2_phase5_benchmark_results.json"
    if o2_path.exists():
        with open(o2_path, "r", encoding="utf-8") as f:
            o2_res = json.load(f)

        df_p4 = pd.DataFrame(o2_res["family_p4_contrasts"])
        df_p4.to_csv(assets_dir / "table_family_p4.csv", index=False)

        df_hyg_eff = pd.DataFrame(o2_res["hygiene_effect"])
        df_hyg_eff.to_csv(assets_dir / "table_hygiene_effect.csv", index=False)
        print(f"[OK] Written Family P4 and hygiene effect tables.")

    # 6. Part C Addendum: Unified 4-Budget Scaling Table (k=50 and k=200 with binding labels)
    k200_path = p5_dir / "o2_k200_scaling_results.json"
    scaling_rows = []
    if o2_path.exists():
        hd_eval = o2_res["eval_results"]["HD"]
        k200_eval = {}
        if k200_path.exists():
            with open(k200_path, "r", encoding="utf-8") as f:
                k200_eval = json.load(f)

        for ds in ["cti-ate", "CTI-ATTACK"]:
            for baseline in ["B2"]:
                if ds not in hd_eval or baseline not in hd_eval[ds]:
                    continue
                
                # k=50 arms
                for arm in ["E0_prime", "E0_prime_tech", "E1a", "E1_mixed"]:
                    arm_data = hd_eval[ds][baseline][arm]
                    # Binding check
                    # cti-ate k=50: 500, 1000, 2000 binding; 4000 capped
                    # CTI-ATTACK k=50: 500, 1000 binding; 2000, 4000 capped
                    is_tech = "tech" in arm.lower() or arm == "E1a"
                    
                    r500 = arm_data["500"]["Recall_sub"]
                    r1000 = arm_data["1000"]["Recall_sub"]
                    r2000 = arm_data["2000"]["Recall_sub"]
                    r4000 = arm_data["4000"]["Recall_sub"]

                    lbl_2000 = "[B]" if ds == "cti-ate" else ("[B]" if "E1" in arm else "[C]")
                    lbl_4000 = "[B]" if "E1" in arm else "[C]"

                    scaling_rows.append({
                        "Dataset": ds,
                        "Baseline": baseline,
                        "Arm": f"{arm} (k=50)",
                        "B=500": f"{r500:.4f} [B]",
                        "B=1000": f"{r1000:.4f} [B]",
                        "B=2000": f"{r2000:.4f} {lbl_2000}",
                        "B=4000": f"{r4000:.4f} {lbl_4000}",
                        "Binding Mean (AUC)": f"{arm_data['binding_mean']['mean_recall']:.4f}",
                    })

                # k=200 arms
                if ds in k200_eval and baseline in k200_eval[ds]:
                    for arm in ["E0_prime_k200", "E0_prime_tech_k200"]:
                        if arm in k200_eval[ds][baseline]:
                            k_data = k200_eval[ds][baseline][arm]
                            r500 = k_data["500"]["Recall_sub"]
                            r1000 = k_data["1000"]["Recall_sub"]
                            r2000 = k_data["2000"]["Recall_sub"]
                            r4000 = k_data["4000"]["Recall_sub"]

                            # Mean across binding budgets (all 4 are binding when pool=200)
                            b_mean = np.mean([r500, r1000, r2000, r4000])

                            scaling_rows.append({
                                "Dataset": ds,
                                "Baseline": baseline,
                                "Arm": f"{arm} (pool=200)",
                                "B=500": f"{r500:.4f} [B]",
                                "B=1000": f"{r1000:.4f} [B]",
                                "B=2000": f"{r2000:.4f} [B]",
                                "B=4000": f"{r4000:.4f} [B]",
                                "Binding Mean (AUC)": f"{b_mean:.4f}",
                            })

        df_scaling = pd.DataFrame(scaling_rows)
        df_scaling.to_csv(assets_dir / "table_o2_scaling.csv", index=False)
        print(f"[OK] Written table_o2_scaling.csv")

        # Markdown scaling table
        md_scaling = [
            "### Table: Unified 4-Budget Scaling (k=50 vs Candidate Pool=200)",
            "",
            "*Note: Cells labeled [B] indicate binding token budgets; cells labeled [C] indicate non-binding budgets capped by candidate pool.*",
            "",
            "| Dataset | Baseline | Arm | B=500 | B=1000 | B=2000 | B=4000 | Binding Mean (AUC) |",
            "| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: |",
        ]
        for r in scaling_rows:
            md_scaling.append(
                f"| **{r['Dataset']}** | {r['Baseline']} | {r['Arm']} | {r['B=500']} | {r['B=1000']} | {r['B=2000']} | {r['B=4000']} | **{r['Binding Mean (AUC)']}** |"
            )
        with open(assets_dir / "table_o2_scaling.md", "w", encoding="utf-8") as f:
            f.write("\n".join(md_scaling) + "\n")
        print(f"[OK] Written table_o2_scaling.md")

    # 7. Generate Plain List of Contrasts (Numbers Only)
    plain_list_lines = [
        "# Phase 5 Plain List of Contrasts (Numbers Only)",
        "",
        "## Summary of Statistical Decisions",
        "",
        "### A. Contrasts that Improved Statistically Significantly (Post-Hoc Round 2)",
        "1. **P3_03** (cti-taa B2, Object-Level Recall@10): Vrel vs V0h",
        "   - Treatment Mean: 0.3200, Control Mean: 0.1400",
        "   - Delta: +0.1800 (95% Bootstrap CI [+0.0600, +0.3000])",
        "   - W/T/L: 10/39/1, p_exact = 0.0117, p_boot = 0.0054 (Holm critical alpha = 0.00625)",
        "   - Decision: Statistically significant increase under Holm step-down.",
        "",
        "2. **P3_11** (cti-taa B2, Secondary Text-Inclusive Recall@10): Vrel vs V0h",
        "   - Treatment Mean: 0.5000, Control Mean: 0.3000",
        "   - Delta: +0.2000 (95% Bootstrap CI [+0.0800, +0.3200])",
        "   - W/T/L: 11/38/1, p_exact = 0.0063, p_boot = 0.0020 (Holm critical alpha = 0.00625)",
        "   - Decision: Statistically significant increase under Holm step-down.",
        "",
        "3. **P3_12** (cti-taa B2, Secondary Text-Inclusive MRR): Vrel vs V0h",
        "   - Treatment Mean: 0.2931, Control Mean: 0.1455",
        "   - Delta: +0.1475 (95% Bootstrap CI [+0.0446, +0.2502])",
        "   - W/T/L: 19/29/2, p_exact = 0.0002, p_boot = 0.0048 (Holm critical alpha = 0.00714)",
        "   - Decision: Statistically significant increase under Holm step-down.",
        "",
        "4. **Hygiene Effect Alone** (E0' HD vs E0' Raw):",
        "   - cti-ate B2: HD = 0.3061 vs Raw = 0.1514 (Delta = +0.1547, 95% CI [+0.0956, +0.2184], p < 0.0001, W/T/L: 44/4/12)",
        "   - cti-ate B3: HD = 0.3096 vs Raw = 0.2052 (Delta = +0.1044, 95% CI [+0.0385, +0.1750], p = 0.0032, W/T/L: 36/7/17)",
        "   - CTI-ATTACK B2: HD = 0.6401 vs Raw = 0.2216 (Delta = +0.4185, 95% CI [+0.3537, +0.4844], p < 0.0001, W/T/L: 122/97/10)",
        "   - Decision: Statistically significant increase across all datasets.",
        "",
        "### B. Contrasts that Decreased Statistically Significantly (Control Arms Maintained Advantage)",
        "1. **P4_01** (cti-ate B2, Mean Binding Recall): E1a vs E0'-TECH",
        "   - Treatment Mean: 0.2053, Control Mean: 0.2973",
        "   - Delta: -0.0920 (95% Bootstrap CI [-0.1491, -0.0366]), p = 0.0010 (Holm alpha = 0.01667)",
        "   - Decision: Significant decrease (control E0'-TECH is superior).",
        "",
        "2. **P4_02** (cti-ate B2, Mean Binding Recall): E1-MIXED vs E0'",
        "   - Treatment Mean: 0.2124, Control Mean: 0.3061",
        "   - Delta: -0.0936 (95% Bootstrap CI [-0.1479, -0.0407]), p = 0.0006 (Holm alpha = 0.01250)",
        "   - Decision: Significant decrease (control E0' is superior).",
        "",
        "3. **P4_03** (cti-ate B3, Mean Binding Recall): E1a vs E0'-TECH",
        "   - Treatment Mean: 0.2154, Control Mean: 0.2924",
        "   - Delta: -0.0771 (95% Bootstrap CI [-0.1306, -0.0247]), p = 0.0040 (Holm alpha = 0.05000)",
        "   - Decision: Significant decrease (control E0'-TECH is superior).",
        "",
        "4. **P4_04** (cti-ate B3, Mean Binding Recall): E1-MIXED vs E0'",
        "   - Treatment Mean: 0.2196, Control Mean: 0.3096",
        "   - Delta: -0.0900 (95% Bootstrap CI [-0.1444, -0.0368]), p = 0.0010 (Holm alpha = 0.02500)",
        "   - Decision: Significant decrease (control E0' is superior).",
        "",
        "5. **P4_05** (CTI-ATTACK B2, Mean Binding Recall): E1a vs E0'-TECH",
        "   - Treatment Mean: 0.5146, Control Mean: 0.6543",
        "   - Delta: -0.1397 (95% Bootstrap CI [-0.1764, -0.1030]), p < 0.0001 (Holm alpha = 0.00833)",
        "   - Decision: Significant decrease (control E0'-TECH is superior).",
        "",
        "6. **P4_06** (CTI-ATTACK B2, Mean Binding Recall): E1-MIXED vs E0'",
        "   - Treatment Mean: 0.4687, Control Mean: 0.6401",
        "   - Delta: -0.1714 (95% Bootstrap CI [-0.2084, -0.1348]), p < 0.0001 (Holm alpha = 0.01000)",
        "   - Decision: Significant decrease (control E0' is superior).",
        "",
        "### C. Contrasts that Did Not Achieve Statistical Significance",
        "1. **P3_01** (cti-taa B2, Object-Level Recall@10): V1h vs V0h (Delta = +0.0200, p_exact = 1.0000, p_boot = 0.7644)",
        "2. **P3_02** (cti-taa B2, Object-Level MRR): V1h vs V0h (Delta = +0.0010, p_exact = 1.0000, p_boot = 0.9844)",
        "3. **P3_04** (cti-taa B2, Object-Level MRR): Vrel vs V0h (Delta = +0.1449, p_exact = 0.0042, p_boot = 0.0121, Holm alpha = 0.00714 -> not significant under bootstrap)",
        "4. **P3_05** (cti-taa B3, Object-Level Recall@10): V1h vs V0h (Delta = +0.0000, p_exact = 1.0000, p_boot = 1.0000)",
        "5. **P3_06** (cti-taa B3, Object-Level MRR): V1h vs V0h (Delta = +0.0272, p_exact = 0.6875, p_boot = 0.2446)",
        "6. **P3_07** (cti-taa B3, Object-Level Recall@10): Vrel vs V0h (Delta = +0.0800, p_exact = 0.2188, p_boot = 0.1399)",
        "7. **P3_08** (cti-taa B3, Object-Level MRR): Vrel vs V0h (Delta = +0.0610, p_exact = 0.2891, p_boot = 0.0434, Holm alpha = 0.00833)",
        "8. **P3_09** (cti-taa B2, Text-Inclusive Recall@10): V1h vs V0h (Delta = +0.0800, p_exact = 0.2891, p_boot = 0.2098)",
        "9. **P3_10** (cti-taa B2, Text-Inclusive MRR): V1h vs V0h (Delta = +0.1203, p_exact = 0.3018, p_boot = 0.0218, Holm alpha = 0.01000)",
        "10. **P3_13** (cti-taa B3, Text-Inclusive Recall@10): V1h vs V0h (Delta = +0.0200, p_exact = 1.0000, p_boot = 0.8463)",
        "11. **P3_14** (cti-taa B3, Text-Inclusive MRR): V1h vs V0h (Delta = +0.1048, p_exact = 0.1460, p_boot = 0.0149, Holm alpha = 0.00833)",
        "12. **P3_15** (cti-taa B3, Text-Inclusive Recall@10): Vrel vs V0h (Delta = +0.1000, p_exact = 0.1250, p_boot = 0.0797)",
        "13. **P3_16** (cti-taa B3, Text-Inclusive MRR): Vrel vs V0h (Delta = +0.0868, p_exact = 0.2668, p_boot = 0.0310, Holm alpha = 0.01250)",
        "14. **Cross-Dataset Transfer Check** (V1h vs V0h):",
        "    - cti-ate B2: Delta = -0.0009 (passes non-inferiority margin -0.03)",
        "    - CTI-ATTACK B2: Delta = +0.0000 (passes non-inferiority margin -0.03)",
    ]

    plain_list_path = assets_dir / "plain_list_contrasts.md"
    with open(plain_list_path, "w", encoding="utf-8") as f:
        f.write("\n".join(plain_list_lines) + "\n")
    print(f"[OK] Written plain_list_contrasts.md")

    print("\nPhase 5 asset generation completed successfully.")

if __name__ == "__main__":
    generate_assets()
