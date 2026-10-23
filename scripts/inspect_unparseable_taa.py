import json
import pandas as pd
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
df = pd.read_csv(REPO_ROOT / 'results/phase_4/per_query_cti_taa_attribution.csv')
cache_dir = REPO_ROOT / '.cache/api_runner'

for arm in ['LLM-only', 'cti-taa_B2_V0', 'cti-taa_B2_V1']:
    print(f"\n{'='*70}\nARM: {arm}\n{'='*70}")
    sub = df[df['arm'] == arm].sort_values('row_idx')
    unparsed = sub[sub['v2_alias'] == 0]
    print(f"Total unparseable / unmatched under Scorer V2: {len(unparsed)} / 50")
    
    count = 0
    for _, r in unparsed.iterrows():
        row_idx = int(r['row_idx'])
        cache_file = cache_dir / f"{arm}_cti-taa_row_{row_idx}.json"
        raw_ans = ""
        if cache_file.is_file():
            with open(cache_file, 'r', encoding='utf-8') as f:
                d = json.load(f)
                raw_ans = d.get('raw_answer', '')
        
        gt = r['ground_truth']
        print(f"\n--- [Row {row_idx}] Ground Truth: {gt} ---")
        print(f"Raw answer (first 400 chars):\n{repr(raw_ans[:400])}")
        count += 1
        if count >= 5:
            break
