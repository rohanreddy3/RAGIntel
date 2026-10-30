# MITRE ATT&CK STIX 2.1 Raw Data

The raw MITRE ATT&CK STIX 2.1 JSON bundles are not tracked in this Git repository due to their size (~59 MB total). They can be downloaded directly from the official MITRE ATT&CK STIX repository (`mitre-attack/attack-stix-data` or `mitre/cti`).

## Bundles & Checksums

| File | Exact SHA-256 Checksum | Size (bytes) | Official Source URL |
|---|---|---|---|
| `enterprise-attack.json` | `66f3fe3f07ef1a2de0bd2fe4b3e8a9ea06c1d0bb2c46171bdbb57c7f7b666524` | 49,253,343 | `https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json` |
| `mobile-attack.json` | `592d4ee8cb2958de20eef65ebd5829753a8dd686f098b237ddeb867558c81faa` | 5,489,646 | `https://raw.githubusercontent.com/mitre/cti/master/mobile-attack/mobile-attack.json` |
| `ics-attack.json` | `202328ce7193aa1c1803cbfbf712e81c37a7e9de6c5adc14dd8c11ceb302573e` | 4,683,721 | `https://raw.githubusercontent.com/mitre/cti/master/ics-attack/ics-attack.json` |

## Re-downloading

To download and verify the primary enterprise bundle:
```bash
python scripts/download_stix.py
```
Place all downloaded `.json` bundle files directly into `data/mitre/`.
