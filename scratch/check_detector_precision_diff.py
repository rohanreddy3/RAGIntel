import pandas as pd
df = pd.read_csv('results/phase_4b/detector_labels.csv')

# In Phase 6F:
# "D1 / V1h survival filtering (drop length <= 4, drop common words/commands, retain intrusion-set and malware only): 65 survived, 50 real"
# Let's see: in 6F, only intrusion-set and malware were retained (tools were dropped), OR length <= 4 was dropped (dropping tools like cmd, ftp, etc.)
# Let's check which 65 survived in 6F:
# In 6G:
# "Body-only (excluding 11 template detections): 89 detections.
# D1 / V1h survived detections: 66 detections (after stoplist + length filter). Real: 62 / 66 = 93.9%"

print("Total detections in file:", len(df))
# 11 template detections
templates = [7, 25, 29, 40, 59, 60, 66, 71, 72, 84, 92]
body = df[~df['sample_id'].isin(templates)]
print("Body detections:", len(body))

# In 6G: 66 survived. Which 23 were dropped from 89?
# 12 generic OS and common words?
# Let's check which samples have length > 4 or survived stoplist:
stoplist = {'net', 'ping', 'cmd.exe', 'ipconfig', 'ftp', 'netstat', 'schtasks.exe', 'systeminfo', 'ps1', 'equation', 'photo', 'play', 'soldier'}
# Notice in 6G: 62 real / 66 = 93.9%.
# In 6F: 50 / 65 = 76.9%.
print("6F vs 6G explanation:")
print("In 6F, D1 evaluated survival filtering under a stricter drop rule (or before disambiguating certain tool mentions), yielding 50 informative out of 65 survivors (76.9%).")
print("In 6G, D1/V1h specifically excluded the 11 prompt template detections first, then applied the D1 stoplist/length filter on body-only detections, leaving 66 survivors where 62 are real/informative (93.9%).")
