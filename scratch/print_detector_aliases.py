import pandas as pd
df = pd.read_csv('results/phase_4b/detector_labels.csv').set_index('sample_id')
template_ids = [7, 25, 29, 40, 59, 60, 66, 71, 72, 84, 92]
common_word_ids = [1, 14, 16, 21, 23, 24, 33, 35, 39, 45, 48, 57, 58, 82, 91]
generic_os_ids = [10, 17, 27, 32, 55, 67, 74, 93, 95, 96, 99]

print("=== 1. Instruction Template Examples (11) ===")
for sid in template_ids:
    r = df.loc[sid]
    m_alias = r['matched_alias']
    c_name = r['canonical_name']
    m_id = r['mitre_id']
    e_type = r['entity_type']
    print(f"Sample {sid:2d}: matched='{m_alias}', canonical='{c_name}', mitre_id={m_id}, type={e_type}")

print("\n=== 2. Common Words, .NET, and Ping Homonyms (15) ===")
for sid in common_word_ids:
    r = df.loc[sid]
    m_alias = r['matched_alias']
    c_name = r['canonical_name']
    m_id = r['mitre_id']
    e_type = r['entity_type']
    print(f"Sample {sid:2d}: matched='{m_alias}', canonical='{c_name}', mitre_id={m_id}, type={e_type}")

print("\n=== 3. Generic OS Utilities (11) ===")
for sid in generic_os_ids:
    r = df.loc[sid]
    m_alias = r['matched_alias']
    c_name = r['canonical_name']
    m_id = r['mitre_id']
    e_type = r['entity_type']
    print(f"Sample {sid:2d}: matched='{m_alias}', canonical='{c_name}', mitre_id={m_id}, type={e_type}")
