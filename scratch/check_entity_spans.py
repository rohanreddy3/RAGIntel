import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data_loader import load_stix_all_bundles, load_benchmark_dataset
from src.entity_resolver import CyberEntityResolver

kb = load_stix_all_bundles()
resolver = CyberEntityResolver(stix_kb=kb, random_seed=42)
ds = load_benchmark_dataset("cti-ate").df

print("=" * 80)
print("ITEM 2.3: DETECTED ENTITY STRINGS & MATCH SPANS FOR CTI-ATE")
print("=" * 80)

for idx in [0, 1, 2, 3, 4, 5]:
    row = ds.iloc[idx]
    q = str(row["query"])
    detected = resolver.detect_entities(q)
    print(f"\n--- Row {idx} (Query length: {len(q)} chars) ---")
    print(f"Query preview: {q[:120]}...")
    print(f"Detected {len(detected)} entities:")
    for d in detected:
        span_text = q[d.start_char:d.end_char]
        print(f"  Match: '{d.matched_text}' | Span: [{d.start_char}:{d.end_char}] -> '{span_text}' | Canonical: {d.entity.canonical_name} ({d.entity.mitre_id}) | IsCanonical: {d.is_canonical}")
    
    # Check V1 expansion prefix
    v1_expanded, _ = resolver.expand_query(q, variant="V1")
    prefix = v1_expanded[:len(v1_expanded) - len(q)].strip()
    print(f"V1 Prepend Prefix: '{prefix}'")
