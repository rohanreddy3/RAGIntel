"""Append newly generated Phase 6C and Phase 6D files to results/freeze_manifest.json.

Strict Rule:
- Add newly created files only.
- Historic file entries and their hashes MUST NOT be modified.
"""

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
    for t_dir in target_dirs:
        if not t_dir.is_dir():
            continue
        for p in sorted(t_dir.glob("*")):
            if p.is_file() and not p.name.endswith(".tmp") and not p.name.endswith(".npy"):
                rel_path = p.relative_to(REPO_ROOT).as_posix()
                if rel_path not in existing_files:
                    h = hashlib.sha256(p.read_bytes()).hexdigest()
                    size = p.stat().st_size
                    existing_files[rel_path] = {
                        "sha256": h,
                        "size_bytes": size,
                    }
                    added_files.append((rel_path, h, size))

    manifest["total_files"] = len(existing_files)
    manifest["files"] = existing_files

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Successfully updated freeze manifest:")
    print(f"- Initial files: {initial_count}")
    print(f"- Added files:   {len(added_files)}")
    print(f"- Total files:   {len(existing_files)}")
    for rel_path, h, size in added_files:
        print(f"  + {rel_path} ({size} bytes, sha256={h[:16]}...)")


if __name__ == "__main__":
    main()
