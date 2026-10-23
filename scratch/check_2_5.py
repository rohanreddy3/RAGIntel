import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from src.data_loader import load_benchmark_dataset

print("=" * 80)
print("ITEM 2.5 INVESTIGATION")
print("=" * 80)

# 1. Count 'Lazarus' in cti-taa ground truth
ds_taa = load_benchmark_dataset("cti-taa").df
lazarus_rows = []
for idx, row in ds_taa.iterrows():
    gt = str(row.get("ground_truth", ""))
    if "lazarus" in gt.lower():
        lazarus_rows.append((idx, gt))

print(f"\n1. Rows in cti-taa with 'Lazarus' in ground truth (Total: {len(lazarus_rows)}):")
for idx, gt in lazarus_rows:
    print(f"  Row {idx}: '{gt}'")

# Also check query text for 'Lazarus'
lazarus_in_query = []
for idx, row in ds_taa.iterrows():
    q = str(row.get("query", ""))
    if "lazarus" in q.lower():
        lazarus_in_query.append(idx)
print(f"Rows in cti-taa with 'Lazarus' in query text (Total: {len(lazarus_in_query)}): {lazarus_in_query}")

# 2. Print cti-ate rows 0-3 directly from the Excel file
ate_xlsx_path = Path("data/benchmarks/CTI-ATE.xlsx")
if not ate_xlsx_path.exists():
    # search for xlsx in data/
    for p in Path("data").rglob("*.xlsx"):
        print("Found xlsx:", p)
        ate_xlsx_path = p
        break

print(f"\n2. Reading cti-ate rows 0-3 directly from {ate_xlsx_path}:")
df_excel = pd.read_excel(ate_xlsx_path)
print("Columns in Excel:", list(df_excel.columns))
gt_col = [c for c in df_excel.columns if "technique" in c.lower() or "ground" in c.lower() or "label" in c.lower()][0]
query_col = [c for c in df_excel.columns if "text" in c.lower() or "report" in c.lower() or "query" in c.lower()][0]

for i in range(min(4, len(df_excel))):
    print(f"\nExcel Row {i}:")
    print(f"  Query text ({len(str(df_excel.iloc[i][query_col]))} chars): {str(df_excel.iloc[i][query_col])[:100]}...")
    print(f"  Ground Truth: {df_excel.iloc[i][gt_col]}")

# Compare with load_benchmark_dataset('cti-ate')
ds_ate = load_benchmark_dataset("cti-ate").df
print("\n3. Comparing with load_benchmark_dataset('cti-ate'):")
for i in range(4):
    print(f"Dataset Loader Row {i} GT: {ds_ate.iloc[i].get('ground_truth')}")
