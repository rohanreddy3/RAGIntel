import json

with open("vendor/RAGIntel/rag_cti.ipynb", "r", encoding="utf-8") as f:
    nb = json.load(f)

print(f"Total cells in rag_cti.ipynb: {len(nb['cells'])}")
for i, cell in enumerate(nb["cells"]):
    src = "".join(cell.get("source", []))
    matched = False
    for keyword in ["html", "directory", "corpus", "drive", "path", "mitre"]:
        if keyword in src.lower():
            matched = True
            break
    if matched:
        print(f"\n--- Cell {i} ({cell.get('cell_type')}) ---")
        for line in src.splitlines():
            line_str = line.strip()
            if any(k in line_str.lower() for k in ["html", "path", "load", "dir", "drive", "file", "split", "doc"]):
                print(f"  {line_str[:120]}")
