# MITRE ATT&CK STIX 2.0 Raw Data

The raw MITRE ATT&CK STIX 2.0 JSON bundles are not tracked in this Git repository due to their size (~56 MB total). They can be downloaded directly from the official MITRE ATT&CK STIX repository (`mitre-attack/attack-stix-data` or `mitre/cti`).

## Bundles & Checksums

| File | Exact SHA-256 Checksum | Size (bytes) | Official Source URL |
|---|---|---|---|
| `enterprise-attack.json` | `f7eaf37fe53b50404084fe1fe67237278f7317e61c11ad550295722d13ede259` | 47,953,963 | `https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json` |
| `mobile-attack.json` | `592d4ee8cb2958de20eef65ebd5829753a8dd686f098b237ddeb867558c81faa` | 5,489,646 | `https://raw.githubusercontent.com/mitre/cti/master/mobile-attack/mobile-attack.json` |
| `ics-attack.json` | `202328ce7193aa1c1803cbfbf712e81c37a7e9de6c5adc14dd8c11ceb302573e` | 4,683,721 | `https://raw.githubusercontent.com/mitre/cti/master/ics-attack/ics-attack.json` |

## Re-downloading

To download and verify the primary enterprise bundle:
```bash
python scripts/download_stix.py
```
Place all downloaded `.json` bundle files directly into `data/mitre/`.
