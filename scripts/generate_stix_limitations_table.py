"""Phase 5 Addendum: Limitations Table Ground-Truth STIX Status Audit.

Addendum Requirement 7:
"Add one line to the limitations table: count of ground-truth IDs that are revoked/deprecated/absent in
 the pinned KB, per dataset."
"""

import json
from pathlib import Path
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent

def generate_limitations_stix_status_table():
    audit_path = REPO_ROOT / "results" / "phase_5" / "ground_truth_stix_audit.json"
    with open(audit_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    rows = []
    for ds, stats in data.items():
        total = stats.get("total_unique_gt_ids", stats.get("total_unique_gt_strings", 0))
        active = stats.get("active", 0)
        dep = stats.get("deprecated", 0)
        rev = stats.get("revoked", 0)
        absent = stats.get("absent", 0)
        
        detail_items = []
        if stats.get("revoked_ids"):
            detail_items.append(f"Revoked: {', '.join(stats['revoked_ids'])}")
        if stats.get("absent_strings"):
            detail_items.append(f"Absent: {', '.join(stats['absent_strings'])}")
        if stats.get("deprecated_ids"):
            detail_items.append(f"Deprecated: {', '.join(stats['deprecated_ids'])}")
        
        detail_str = "; ".join(detail_items) if detail_items else "None"

        rows.append({
            "Dataset": ds,
            "Total Unique GT Entities": total,
            "Active in Pinned KB": active,
            "Revoked in Pinned KB": rev,
            "Deprecated in Pinned KB": dep,
            "Absent in Pinned KB": absent,
            "Non-Active Share (%)": round((rev + dep + absent) / total * 100, 2),
            "Specific Non-Active Entities": detail_str,
        })

    df = pd.DataFrame(rows)
    out_dir = REPO_ROOT / "results" / "phase_5" / "assets"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    csv_path = out_dir / "table_limitations_stix_status.csv"
    df.to_csv(csv_path, index=False)
    print(f"Saved {csv_path}")

    md_lines = [
        "### Limitations Table Addendum: Ground-Truth STIX Status in Pinned Knowledge Base",
        "",
        "| Dataset | Total Unique GT | Active | Revoked | Deprecated | Absent | Non-Active Share (%) | Specific Non-Active Entities |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |",
    ]
    for r in rows:
        md_lines.append(
            f"| **{r['Dataset']}** | {r['Total Unique GT Entities']} | {r['Active in Pinned KB']} | {r['Revoked in Pinned KB']} | {r['Deprecated in Pinned KB']} | {r['Absent in Pinned KB']} | {r['Non-Active Share (%)']}% | {r['Specific Non-Active Entities']} |"
        )

    md_path = out_dir / "table_limitations_stix_status.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines) + "\n")
    print(f"Saved {md_path}")

if __name__ == "__main__":
    generate_limitations_stix_status_table()
