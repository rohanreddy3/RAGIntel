import os
import gzip
import json
import hashlib
import sys
from pathlib import Path
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

def prepare_data():
    print("=" * 80)
    print("PREPARING ANALYSIS-DATA BRANCH ASSETS")
    print("=" * 80)
    
    # 1. Check STIX bundle sizes
    stix_files = [
        REPO_ROOT / "data" / "mitre" / "enterprise-attack.json",
        REPO_ROOT / "data" / "mitre" / "mobile-attack.json",
        REPO_ROOT / "data" / "mitre" / "ics-attack.json"
    ]
    for p in stix_files:
        sz_mb = p.stat().st_size / (1024 * 1024)
        print(f"STIX: {p.name}: {sz_mb:.2f} MB (< 90 MB: {sz_mb < 90})")
        
    # 2. Compress top50 retrieval caches
    top50_files = [
        REPO_ROOT / "results" / "phase_3" / "top50_ranked_chunks.json",
        REPO_ROOT / "results" / "phase_3" / "top50_phase3c_chunks.json"
    ]
    for p in top50_files:
        if p.is_file():
            out_gz = p.with_name(p.name + ".gz")
            print(f"Compressing {p.name} to {out_gz.name}...")
            with open(p, "rb") as f_in, gzip.open(out_gz, "wb", compresslevel=9) as f_out:
                while chunk := f_in.read(1024 * 1024):
                    f_out.write(chunk)
            sz_mb = out_gz.stat().st_size / (1024 * 1024)
            print(f"  Result: {out_gz.name}: {sz_mb:.2f} MB (< 90 MB: {sz_mb < 90})")

    # 3. Create generations.jsonl.gz
    # Load dataset query_id maps to ensure bit-exact query_id alignment
    from src.data_loader import load_benchmark_dataset
    df_ate = load_benchmark_dataset("cti-ate").df
    df_attack = load_benchmark_dataset("CTI-ATTACK").df
    df_taa = load_benchmark_dataset("cti-taa").df
    
    qid_map = {
        "cti-ate": dict(zip(df_ate.index, df_ate["query_id"])),
        "CTI-ATTACK": dict(zip(df_attack.index, df_attack["query_id"])),
        "cti-taa": dict(zip(df_taa.index, df_taa["query_id"]))
    }

    cache_dir = REPO_ROOT / ".cache" / "api_runner"
    gen_records = []
    
    for fname in sorted(os.listdir(cache_dir)):
        if not fname.endswith(".json") or fname == "known_reset.json":
            continue
        with open(cache_dir / fname, "r", encoding="utf-8") as fp:
            d = json.load(fp)
            arm = d.get("arm")
            ds = d.get("dataset")
            row_idx = int(d.get("row_idx", 0))
            
            # Map query_id
            qid = qid_map.get(ds, {}).get(row_idx, "")
            if not qid:
                # compute fallback sha1[:12]
                q_text = str(d.get("prompt_text", ""))
                qid = hashlib.sha1(q_text.strip().encode("utf-8")).hexdigest()[:12]
                
            # Context IDs used
            contexts = d.get("contexts_used", [])
            ctx_ids = []
            for c in contexts:
                if isinstance(c, dict) and "id" in c:
                    ctx_ids.append(c["id"])
                elif isinstance(c, str):
                    ctx_ids.append(c)
                    
            raw_ans = d.get("raw_answer", "")
            
            gen_records.append({
                "arm": arm,
                "dataset": ds,
                "row_idx": row_idx,
                "query_id": qid,
                "prompt_context_ids": ctx_ids,
                "raw_response": raw_ans
            })

    print(f"\nCollected {len(gen_records)} generation records from cache.")
    
    # Save to generations.jsonl.gz in results/phase_4/
    out_gen_gz = REPO_ROOT / "results" / "phase_4" / "generations.jsonl.gz"
    with gzip.open(out_gen_gz, "wt", encoding="utf-8", compresslevel=9) as fp:
        for r in gen_records:
            fp.write(json.dumps(r) + "\n")
            
    sz_mb = out_gen_gz.stat().st_size / (1024 * 1024)
    print(f"Saved {out_gen_gz.name}: {sz_mb:.2f} MB (< 90 MB: {sz_mb < 90})")

    # Also check results/phase_4b/* sizes
    print("\nChecking results/phase_4b/* sizes:")
    p4b_dir = REPO_ROOT / "results" / "phase_4b"
    for p in sorted(p4b_dir.iterdir()):
        if p.is_file():
            sz_mb = p.stat().st_size / (1024 * 1024)
            print(f"  {p.name}: {sz_mb:.4f} MB (< 90 MB: {sz_mb < 90})")

    print("\nData preparation complete!")

if __name__ == "__main__":
    prepare_data()
