import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

def get_sha256(p: Path) -> str:
    if not p.is_file():
        return "MISSING"
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

manifest_path = REPO_ROOT / "results" / "phase_3" / "manifest.json"
manifest = {}
if manifest_path.is_file():
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

artifacts = {
    "o2_phase3c_benchmark_results_sha256": REPO_ROOT / "results" / "phase_3" / "o2_phase3c_benchmark_results.json",
    "top50_phase3c_chunks_sha256": REPO_ROOT / "results" / "phase_3" / "top50_phase3c_chunks.json",
    "regenerated_p1_table_sha256": REPO_ROOT / "results" / "phase_2" / "regenerated_p1_table.json",
    "v3_seeds_b3_results_sha256": REPO_ROOT / "results" / "phase_2" / "v3_seeds_b3_results.json",
    "regenerated_cti_taa_evaluation_sha256": REPO_ROOT / "results" / "phase_4" / "regenerated_cti_taa_evaluation.json",
    "figure_budget_scaling_curves_sha256": REPO_ROOT / "report" / "figures" / "figure_budget_scaling_curves.svg",
    "figure_cti_taa_attribution_gap_sha256": REPO_ROOT / "report" / "figures" / "figure_cti_taa_attribution_gap.svg",
    "dataset_stats_md_sha256": REPO_ROOT / "report" / "dataset_stats.md",
    "reproduce_md_sha256": REPO_ROOT / "docs" / "REPRODUCE.md",
    "review_phase_3c_md_sha256": REPO_ROOT / "reviews" / "REVIEW_PHASE_3C.md",
}

manifest["phase_3c_artifacts"] = {k: get_sha256(v) for k, v in artifacts.items()}
manifest["phase_3c_completed_at"] = "2026-10-22T13:25:00Z"

with open(manifest_path, "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2)

print("Updated results/phase_3/manifest.json successfully:")
print(json.dumps(manifest["phase_3c_artifacts"], indent=2))
