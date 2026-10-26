import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from src.data_loader import load_benchmark_dataset

df = load_benchmark_dataset('cti-taa').df
print("Total queries:", len(df))
for i in [0, 1, 2, 7, 25]:
    q = str(df.iloc[i]['query'])
    print(f"\n--- Query {i} ---")
    print("Full query length:", len(q))
    print("First 300 chars:")
    print(repr(q[:300]))
