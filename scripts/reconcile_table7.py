"""Phase 5 Addendum: Table 7 Reconciliation (Phase 4 vs Phase 4B side-by-side).

Reconciles:
1. Claim C9: Restores original scoring-gap claim under original ID (C9, Supported).
2. Corrects the erroneous 'P1_08 -0.12' reference and explains origin of -0.12.
3. Explains the 0.22 vs 0.30 V1 value (strict S_exact vs alias S_alias).
4. Deprecates Phase 4B V1-strict numbers, replacing with Phase 5 Part B body-only numbers.
"""

import json
from pathlib import Path
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent

def generate_table7_reconciliation():
    reconciliation_data = [
        {
            "ID": "C1",
            "Phase_4_Claim": "Family P1: Query entity resolution (V1) statistically significantly improves threat actor attribution recall on cti-taa over raw query (V0).",
            "Phase_4_Status": "Not Supported",
            "Phase_4B_Claim": "Family P1: Query entity resolution (V1) statistically significantly improves threat actor attribution recall on cti-taa over raw query (V0).",
            "Phase_4B_Status": "Not Supported",
            "Phase_5_Reconciliation": "Maintained as Not Supported. In Phase 5 Part B (body-only hygiene), V1h achieves Recall@10 = 0.16 vs V0h = 0.14 (Delta = +0.02, p_exact = 1.000, p_boot = 0.7644; non-significant after Holm step-down)."
        },
        {
            "ID": "C2",
            "Phase_4_Claim": "Family P1 Sensitivity: Query entity resolution (V1) achieves positive reciprocal rank precision (MRR) gain over length-matched random control (V3).",
            "Phase_4_Status": "Exploratory",
            "Phase_4B_Claim": "Family P1 Sensitivity: Query entity resolution (V1) achieves positive reciprocal rank precision (MRR) gain over length-matched random control (V3).",
            "Phase_4B_Status": "Exploratory",
            "Phase_5_Reconciliation": "Maintained as Exploratory. Unadjusted p=0.0223 in Phase 2; not significant under family-wise Holm step-down."
        },
        {
            "ID": "C3",
            "Phase_4_Claim": "Family S1: Query entity resolution transfers positively to technique extraction on cti-ate and CTI-ATTACK.",
            "Phase_4_Status": "Not Supported",
            "Phase_4B_Claim": "Family S1: Query entity resolution transfers positively to technique extraction on cti-ate and CTI-ATTACK.",
            "Phase_4B_Status": "Not Supported",
            "Phase_5_Reconciliation": "Maintained as Not Supported. Under Phase 5 Part B body-only hygiene, non-inferiority margin (-0.03) passes on cti-ate (Delta = -0.0009) and CTI-ATTACK (Delta = +0.0000)."
        },
        {
            "ID": "C4",
            "Phase_4_Claim": "Family P2': Structure-aware sibling expansion (E1b-MIXED) improves technique retrieval recall over baseline splitter (E0') at B*=500.",
            "Phase_4_Status": "Not Supported",
            "Phase_4B_Claim": "Family P2': Structure-aware sibling expansion (E1b-MIXED) improves technique retrieval recall over baseline splitter (E0') at B*=500.",
            "Phase_4B_Status": "Not Supported",
            "Phase_5_Reconciliation": "Maintained as Not Supported. Significant negative delta on CTI-ATTACK (Delta = -0.1485, p < 0.0001)."
        },
        {
            "ID": "C5",
            "Phase_4_Claim": "cti-taa Guard: Sibling expansion (E1b-MIXED) preserves threat actor attribution recall within 5% of E0'.",
            "Phase_4_Status": "Not Supported",
            "Phase_4B_Claim": "cti-taa Guard: Sibling expansion (E1b-MIXED) preserves threat actor attribution recall within 5% of E0'.",
            "Phase_4B_Status": "Not Supported",
            "Phase_5_Reconciliation": "Maintained as Not Supported. Recall@10 drops from 0.3000 to 0.1000 (Delta = -0.2000, p=0.0064)."
        },
        {
            "ID": "C6",
            "Phase_4_Claim": "Unified Mixed Indexing (E1-MIXED without siblings) preserves actor attribution retrieval recall on cti-taa.",
            "Phase_4_Status": "Supported",
            "Phase_4B_Claim": "Unified Mixed Indexing (E1-MIXED without siblings) preserves actor attribution retrieval recall on cti-taa.",
            "Phase_4B_Status": "Not established",
            "Phase_5_Reconciliation": "Reclassified as Not established in Phase 4B. The earlier +0.30 gain was evaluated without token budget constraints; under matched 500-token budget, Delta = -0.0200 (object-level) and -0.2600 (text-inclusive)."
        },
        {
            "ID": "C7",
            "Phase_4_Claim": "Family G1: Structure-aware sibling expansion (E1b-MIXED) improves downstream LLM extraction F1 over E0' at B*=500.",
            "Phase_4_Status": "Not Supported",
            "Phase_4B_Claim": "Family G1: Structure-aware sibling expansion (E1b-MIXED) improves downstream LLM extraction F1 over E0' at B*=500.",
            "Phase_4B_Status": "Not Supported",
            "Phase_5_Reconciliation": "Maintained as Not Supported. Significantly lower F1 on cti-ate (Delta = -0.1340) and CTI-ATTACK (Delta = -0.1592)."
        },
        {
            "ID": "C8",
            "Phase_4_Claim": "RAG Retrieval Advantage: Retrieved STIX context improves threat actor attribution over direct LLM parametric generation (LLM-only).",
            "Phase_4_Status": "Not Supported",
            "Phase_4B_Claim": "RAG Retrieval Advantage: Retrieved STIX context improves threat actor attribution over direct LLM parametric generation (LLM-only) [with test-set contamination caveat].",
            "Phase_4B_Status": "Not Supported",
            "Phase_5_Reconciliation": "Maintained as Not Supported with formal pre-training contamination caveat: LLM-only achieves 0.72 accuracy without context."
        },
        {
            "ID": "C9",
            "Phase_4_Claim": "STIX Retrieval Scoring Gap: Exact canonical matching (S_exact) underestimates attribution recall relative to alias-aware matching (S_alias).",
            "Phase_4_Status": "Supported",
            "Phase_4B_Claim": "Errantly re-scoped in Phase 4B narrative: 'STIX-based retrieval alias expansion reduced recall by 0.12 (P1_08)...'",
            "Phase_4B_Status": "Errant Scoping in 4B",
            "Phase_5_Reconciliation": "RESTORED to original ID and claim: Supported. S_alias adds +0.1200 to +0.2200 to Recall@10 over S_exact across all evaluated baselines and KBs (s_exact_vs_alias_comparison.json). Corrections applied: (1) 'P1_08 -0.12' reference was erroneous; P1_08 evaluated MRR on B3 (+0.0357), while -0.12 was from V0 vs LLM-only generation accuracy. (2) V1 recall on cti-taa B2 was 0.22 under S_exact and 0.30 under S_alias (+0.08 scorer gap). (3) Phase 4B V1-strict numbers are deprecated and replaced by Phase 5 Part B body-only numbers."
        },
        {
            "ID": "C10",
            "Phase_4_Claim": "Field Chunking Alone (E1a) improves technique retrieval recall over monolithic recursive splitting (E0'-TECH) at B*=500.",
            "Phase_4_Status": "Not Supported",
            "Phase_4B_Claim": "Field Chunking Alone (E1a) improves technique retrieval recall over monolithic recursive splitting (E0'-TECH) at B*=500.",
            "Phase_4B_Status": "Not Supported",
            "Phase_5_Reconciliation": "Maintained as Not Supported. Under B*=500, E1a is lower than E0'-TECH on cti-ate (0.0890 vs 0.1684) and CTI-ATTACK (0.0699 vs 0.1310); only excels at B >= 4000."
        }
    ]

    out_dir = REPO_ROOT / "results" / "phase_5" / "assets"
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(reconciliation_data)
    csv_path = out_dir / "table7_reconciliation.csv"
    df.to_csv(csv_path, index=False)
    print(f"Saved Table 7 reconciliation CSV to {csv_path}")

    # Generate Markdown Table
    md_lines = [
        "### Table 7 Reconciliation: Side-by-Side Audit (Phase 4 vs Phase 4B vs Phase 5)",
        "",
        "| ID | Phase 4 Claim & Status | Phase 4B Claim & Status | Phase 5 Reconciliation & Status |",
        "| :---: | :--- | :--- | :--- |",
    ]
    for row in reconciliation_data:
        p4_text = f"**{row['Phase_4_Status']}**<br>{row['Phase_4_Claim']}"
        p4b_text = f"**{row['Phase_4B_Status']}**<br>{row['Phase_4B_Claim']}"
        p5_text = f"{row['Phase_5_Reconciliation']}"
        md_lines.append(f"| **{row['ID']}** | {p4_text} | {p4b_text} | {p5_text} |")

    md_path = out_dir / "table7_reconciliation.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines) + "\n")
    print(f"Saved Table 7 reconciliation Markdown to {md_path}")

if __name__ == "__main__":
    generate_table7_reconciliation()
