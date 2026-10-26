"""Update freeze_manifest.json with Phase 6D, 6E, and 6G artifacts.

Strict Rule:
- Only update newly created or modified Phase 6D/6G files and analysis_plan.md.
- Historic file entries from Phases 0–6B and their hashes MUST NOT be modified.
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "results" / "freeze_manifest.json"


def main():
    print("Loading freeze manifest...")
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    existing_files = manifest.get("files", {})
    initial_count = len(existing_files)

    target_dirs = [
        REPO_ROOT / "results" / "phase_6c",
        REPO_ROOT / "results" / "phase_6d",
    ]

    added_files = []
    updated_files = []

    for t_dir in target_dirs:
        if not t_dir.is_dir():
            continue
        for p in sorted(t_dir.glob("*")):
            if p.is_file() and not p.name.endswith(".tmp") and not p.name.endswith(".npy"):
                rel_path = p.relative_to(REPO_ROOT).as_posix()
                h = hashlib.sha256(p.read_bytes()).hexdigest()
                size = p.stat().st_size
                if rel_path not in existing_files:
                    existing_files[rel_path] = {
                        "sha256": h,
                        "size_bytes": size,
                    }
                    added_files.append((rel_path, h, size))
                elif "phase_6d" in rel_path and (existing_files[rel_path]["sha256"] != h or existing_files[rel_path]["size_bytes"] != size):
                    existing_files[rel_path] = {
                        "sha256": h,
                        "size_bytes": size,
                    }
                    updated_files.append((rel_path, h, size))

    # Also update analysis_plan.md
    ap_path = REPO_ROOT / "analysis_plan.md"
    if ap_path.is_file() and "analysis_plan.md" in existing_files:
        ap_h = hashlib.sha256(ap_path.read_bytes()).hexdigest()
        ap_size = ap_path.stat().st_size
        if existing_files["analysis_plan.md"]["sha256"] != ap_h:
            existing_files["analysis_plan.md"] = {
                "sha256": ap_h,
                "size_bytes": ap_size,
            }
            updated_files.append(("analysis_plan.md", ap_h, ap_size))

    manifest["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    manifest["total_files"] = len(existing_files)
    manifest["files"] = existing_files

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Successfully updated freeze manifest:")
    print(f"- Initial files: {initial_count}")
    print(f"- Added files:   {len(added_files)}")
    print(f"- Updated files: {len(updated_files)}")
    print(f"- Total files:   {len(existing_files)}")
    for rel_path, h, size in added_files:
        print(f"  + Added:   {rel_path} ({size} bytes, sha256={h[:16]}...)")
    for rel_path, h, size in updated_files:
        print(f"  * Updated: {rel_path} ({size} bytes, sha256={h[:16]}...)")


if __name__ == "__main__":
    main()
