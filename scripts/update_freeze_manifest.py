#!/usr/bin/env python3
"""
Update freeze_manifest.json with Phase 6D, 6L artifacts and analysis_plan.md.

Strict Rule:
- Only update newly created or modified Phase 6D/6L files and analysis_plan.md.
- Historic file entries from Phases 0–6B and their hashes MUST NOT be modified.
- Supports both raw_sha256 and LF-normalized sha256 for cross-platform integrity.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "results" / "freeze_manifest.json"


def hash_file(p: Path) -> dict:
    raw = p.read_bytes()
    raw_hash = hashlib.sha256(raw).hexdigest()
    raw_size = len(raw)
    try:
        raw.decode("utf-8")
        norm = raw.replace(b"\r\n", b"\n")
        norm_hash = hashlib.sha256(norm).hexdigest()
        norm_size = len(norm)
        return {
            "sha256": norm_hash,
            "raw_sha256": raw_hash,
            "size_bytes": raw_size,
            "norm_size_bytes": norm_size,
        }
    except UnicodeDecodeError:
        return {
            "sha256": raw_hash,
            "raw_sha256": raw_hash,
            "size_bytes": raw_size,
        }


def main():
    print("Loading freeze manifest...")
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    existing_files = manifest.get("files", {})
    initial_count = len(existing_files)

    target_dirs = [
        REPO_ROOT / "results" / "phase_6c",
        REPO_ROOT / "results" / "phase_6d",
        REPO_ROOT / "results" / "phase_6l",
    ]

    added_files = []
    updated_files = []

    for t_dir in target_dirs:
        if not t_dir.is_dir():
            continue
        for p in sorted(t_dir.glob("*")):
            if p.is_file() and not p.name.endswith(".tmp") and not p.name.endswith(".npy"):
                rel_path = p.relative_to(REPO_ROOT).as_posix()
                info = hash_file(p)
                if rel_path not in existing_files:
                    existing_files[rel_path] = info
                    added_files.append((rel_path, info["raw_sha256"], info["size_bytes"]))
                elif ("phase_6d" in rel_path or "phase_6l" in rel_path):
                    existing_files[rel_path] = info
                    updated_files.append((rel_path, info["raw_sha256"], info["size_bytes"]))

    # Also update analysis_plan.md
    ap_path = REPO_ROOT / "analysis_plan.md"
    if ap_path.is_file() and "analysis_plan.md" in existing_files:
        info = hash_file(ap_path)
        existing_files["analysis_plan.md"] = info
        updated_files.append(("analysis_plan.md", info["raw_sha256"], info["size_bytes"]))

    manifest["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    manifest["freeze_version"] = "v1.0-final4"
    manifest["total_files"] = len(existing_files)
    manifest["files"] = existing_files

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Successfully updated freeze manifest to v1.0-final4:")
    print(f"- Initial files: {initial_count}")
    print(f"- Added files:   {len(added_files)}")
    print(f"- Updated files: {len(updated_files)}")
    print(f"- Total files:   {len(existing_files)}")
    for rel_path, h, size in added_files:
        print(f"  + Added:   {rel_path} ({size} bytes, raw_sha256={h[:16]}...)")
    for rel_path, h, size in updated_files:
        print(f"  * Updated: {rel_path} ({size} bytes, raw_sha256={h[:16]}...)")


if __name__ == "__main__":
    main()
