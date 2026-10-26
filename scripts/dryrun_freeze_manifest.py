"""Dry-run freeze manifest update into results/freeze_dryrun/.

Strict Constraint:
- MUST NOT overwrite results/freeze_manifest.json.
- Output dry-run manifest to results/freeze_dryrun/freeze_manifest_dryrun.json.
- Report any file whose hash would change, and list all new files to include.
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "results" / "freeze_manifest.json"
DRYRUN_DIR = REPO_ROOT / "results" / "freeze_dryrun"
DRYRUN_MANIFEST_PATH = DRYRUN_DIR / "freeze_manifest_dryrun.json"

DRYRUN_DIR.mkdir(parents=True, exist_ok=True)


def compute_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    print("Loading existing frozen manifest from:", MANIFEST_PATH)
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        original_manifest = json.load(f)

    existing_files = dict(original_manifest.get("files", {}))
    initial_count = len(existing_files)

    # Scanned directories
    target_dirs = [
        REPO_ROOT / "results" / "phase_6c",
        REPO_ROOT / "results" / "phase_6d",
    ]

    added_files = []
    updated_files = []
    unchanged_files = []

    dryrun_files = dict(existing_files)

    for t_dir in target_dirs:
        if not t_dir.is_dir():
            continue
        for p in sorted(t_dir.glob("*")):
            if p.is_file() and not p.name.endswith(".tmp") and not p.name.endswith(".npy"):
                rel_path = p.relative_to(REPO_ROOT).as_posix()
                h = compute_sha256(p)
                size = p.stat().st_size
                if rel_path not in dryrun_files:
                    dryrun_files[rel_path] = {
                        "sha256": h,
                        "size_bytes": size,
                    }
                    added_files.append((rel_path, h, size))
                elif dryrun_files[rel_path]["sha256"] != h or dryrun_files[rel_path]["size_bytes"] != size:
                    old_h = dryrun_files[rel_path]["sha256"]
                    old_size = dryrun_files[rel_path]["size_bytes"]
                    dryrun_files[rel_path] = {
                        "sha256": h,
                        "size_bytes": size,
                    }
                    updated_files.append((rel_path, old_h, h, old_size, size))
                else:
                    unchanged_files.append(rel_path)

    # Check analysis_plan.md
    ap_path = REPO_ROOT / "analysis_plan.md"
    if ap_path.is_file():
        ap_h = compute_sha256(ap_path)
        ap_size = ap_path.stat().st_size
        if "analysis_plan.md" in dryrun_files:
            if dryrun_files["analysis_plan.md"]["sha256"] != ap_h:
                old_h = dryrun_files["analysis_plan.md"]["sha256"]
                old_size = dryrun_files["analysis_plan.md"]["size_bytes"]
                dryrun_files["analysis_plan.md"] = {
                    "sha256": ap_h,
                    "size_bytes": ap_size,
                }
                updated_files.append(("analysis_plan.md", old_h, ap_h, old_size, ap_size))
            else:
                unchanged_files.append("analysis_plan.md")
        else:
            dryrun_files["analysis_plan.md"] = {
                "sha256": ap_h,
                "size_bytes": ap_size,
            }
            added_files.append(("analysis_plan.md", ap_h, ap_size))

    dryrun_manifest = {
        "dryrun": True,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "original_manifest_timestamp": original_manifest.get("timestamp_utc"),
        "initial_files_count": initial_count,
        "new_files_count": len(added_files),
        "changed_files_count": len(updated_files),
        "total_files_count": len(dryrun_files),
        "added_files": [
            {"path": p, "sha256": h, "size_bytes": s} for p, h, s in added_files
        ],
        "changed_files": [
            {"path": p, "old_sha256": oh, "new_sha256": nh, "old_size": os, "new_size": ns}
            for p, oh, nh, os, ns in updated_files
        ],
        "files": dryrun_files,
    }

    with open(DRYRUN_MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(dryrun_manifest, f, indent=2)

    print("\n" + "=" * 80)
    print("FREEZE DRY-RUN SUMMARY REPORT")
    print("=" * 80)
    print(f"Target Output Path:      {DRYRUN_MANIFEST_PATH.relative_to(REPO_ROOT)}")
    print(f"Original Frozen Path:    {MANIFEST_PATH.relative_to(REPO_ROOT)} (UNTOUCHED)")
    print(f"Total Base Files:        {initial_count}")
    print(f"New Files Found:         {len(added_files)}")
    print(f"Changed Files Found:     {len(updated_files)}")
    print(f"Unchanged Files:         {len(unchanged_files)}")
    print(f"Projected Total Files:   {len(dryrun_files)}")
    print("-" * 80)

    print(f"\n[CHANGED FILES] ({len(updated_files)}):")
    if updated_files:
        for p, oh, nh, os, ns in updated_files:
            print(f"  * {p}")
            print(f"      old: sha256={oh[:16]}... ({os} bytes)")
            print(f"      new: sha256={nh[:16]}... ({ns} bytes)")
    else:
        print("  None. All existing file hashes matched.")

    print(f"\n[NEW FILES TO INCLUDE] ({len(added_files)}):")
    if added_files:
        for p, h, s in added_files:
            print(f"  + {p} ({s} bytes, sha256={h[:16]}...)")
    else:
        print("  None.")

    print("\n" + "=" * 80)
    print("DRY-RUN COMPLETE. NO LIVE FREEZE PERFORMED.")
    print("=" * 80)


if __name__ == "__main__":
    main()
