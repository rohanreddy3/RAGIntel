import subprocess
import os

out = subprocess.check_output(['git', 'add', '-n', '.']).decode('utf-8', errors='ignore')
files = []
for line in out.splitlines():
    line = line.strip()
    if line.startswith("add '") and line.endswith("'"):
        fpath = line[5:-1]
        sz = os.path.getsize(fpath)
        files.append((fpath, sz))

files.sort(key=lambda x: -x[1])

print("=== TOP 20 LARGEST FILES TO BE ADDED ===")
for i, (p, sz) in enumerate(files[:20], 1):
    print(f"{i:2d}. {p:65s}: {sz / (1024*1024):6.2f} MB ({sz:,} bytes)")

over_25mb = [x for x in files if x[1] > 25 * 1024 * 1024]
print(f"\nFiles over 25 MB: {len(over_25mb)}")
for p, sz in over_25mb:
    print(f"  - {p} ({sz / (1024*1024):.2f} MB)")

total_sz = sum(x[1] for x in files)
print(f"\nTotal size to be committed: {total_sz / (1024*1024):.2f} MB ({total_sz:,} bytes)")
print(f"Total number of files: {len(files)}")

top_level = {}
top_counts = {}
for p, sz in files:
    top = p.split('/')[0]
    top_level[top] = top_level.get(top, 0) + sz
    top_counts[top] = top_counts.get(top, 0) + 1

print("\n=== TOTAL COMMITTED SIZE BY TOP-LEVEL FOLDER ===")
for top, sz in sorted(top_level.items(), key=lambda x: -x[1]):
    print(f"{top:25s}: {sz / (1024*1024):6.2f} MB ({sz:,} bytes) across {top_counts[top]} files")

print("\n=== SUMMARY COUNTS PER TOP-LEVEL FOLDER ===")
for top, count in sorted(top_counts.items(), key=lambda x: x[0]):
    print(f"{top:25s}: {count} files")
