import urllib.request
import hashlib
import json
import time
import os
import sys

def download_stix():
    url = "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"
    out_dir = os.path.join("data", "mitre")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "enterprise-attack.json")

    print(f"Downloading MITRE STIX bundle from: {url}")
    print(f"Target location: {out_path}")

    start = time.time()
    # Stream download with progress
    req = urllib.request.Request(url, headers={"User-Agent": "RAGIntel-Thesis/1.0"})
    with urllib.request.urlopen(req) as response, open(out_path, "wb") as out_file:
        total_size = int(response.headers.get("Content-Length", 0))
        downloaded = 0
        chunk_size = 1024 * 1024  # 1MB chunks
        hasher = hashlib.sha256()

        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            downloaded += len(chunk)
            out_file.write(chunk)
            hasher.update(chunk)
            if total_size > 0:
                pct = downloaded / total_size * 100
                sys.stdout.write(f"\rDownloaded {downloaded:,} / {total_size:,} bytes ({pct:.1f}%)")
            else:
                sys.stdout.write(f"\rDownloaded {downloaded:,} bytes")
            sys.stdout.flush()

    elapsed = time.time() - start
    sha256 = hasher.hexdigest()
    file_size = os.path.getsize(out_path)
    print(f"\nDownload finished in {elapsed:.2f} seconds.")
    print(f"File size: {file_size:,} bytes ({file_size / (1024*1024):.2f} MB)")
    print(f"SHA-256: {sha256}")

    # Validate JSON parsing and STIX bundle contents
    print("Validating STIX JSON structure...")
    with open(out_path, "r", encoding="utf-8") as f:
        bundle = json.load(f)

    bundle_type = bundle.get("type")
    objects = bundle.get("objects", [])
    print(f"STIX bundle type: {bundle_type}")
    print(f"Total STIX objects: {len(objects):,}")

    type_counts = {}
    for obj in objects:
        t = obj.get("type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

    print("Object types summary:")
    for t, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:15]:
        print(f"  - {t}: {count:,}")

    # Save metadata summary
    meta = {
        "url": url,
        "file_size_bytes": file_size,
        "sha256": sha256,
        "bundle_type": bundle_type,
        "total_objects": len(objects),
        "object_counts": type_counts,
        "download_time_seconds": elapsed
    }
    meta_path = os.path.join("results", "phase_0", "stix_metadata.json")
    os.makedirs(os.path.dirname(meta_path), exist_ok=True)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(f"Saved STIX metadata to {meta_path}")

if __name__ == "__main__":
    download_stix()
