"""Experimental Manifest Generator for Result Artifacts.

Computes and saves provenance manifests:
- Code hash (SHA-256 over all source and script files)
- Config hash (SHA-256 of config.yaml)
- Knowledge base index hashes (.faiss, .pkl)
- Seed (42)
- Date (ISO 8601 UTC)
"""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def compute_file_sha256(filepath: Path) -> str:
    """Compute SHA-256 hash of a single file."""
    if not filepath.is_file():
        return "file_not_found"
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def compute_directory_code_hash(base_dir: Path) -> str:
    """Compute composite SHA-256 hash across all Python files in directory tree."""
    h = hashlib.sha256()
    py_files = sorted(base_dir.rglob("*.py"))
    for pf in py_files:
        if "__pycache__" in str(pf) or ".venv" in str(pf) or "venv" in str(pf):
            continue
        rel_path = pf.relative_to(base_dir).as_posix()
        h.update(rel_path.encode("utf-8"))
        with open(pf, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
    return h.hexdigest()


def generate_experiment_manifest(
    output_dir: Path,
    manifest_name: str = "manifest.json",
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> Path:
    """Generate and write manifest alongside results files."""
    repo_root = Path(__file__).resolve().parent.parent
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    src_hash = compute_directory_code_hash(repo_root / "src")
    scripts_hash = compute_directory_code_hash(repo_root / "scripts")
    config_hash = compute_file_sha256(repo_root / "config.yaml")

    index_ent_hash = compute_file_sha256(repo_root / ".cache" / "retriever_index" / "faiss_index" / "index.faiss")
    index_all_hash = compute_file_sha256(repo_root / ".cache" / "retriever_index_all" / "faiss_index" / "index.faiss")

    manifest_data = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "seed": 42,
        "code_hash": {
            "src_sha256": src_hash,
            "scripts_sha256": scripts_hash,
        },
        "config_hash": config_hash,
        "index_hashes": {
            "E0-STIX-ENT_faiss_sha256": index_ent_hash,
            "E0-STIX-ALL_faiss_sha256": index_all_hash,
        },
        "extra_metadata": extra_metadata or {},
    }

    manifest_path = output_dir / manifest_name
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    return manifest_path
