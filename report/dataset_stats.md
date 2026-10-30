# Dataset & Knowledge Base Characteristics

This document summarizes the quantitative properties, structural compositions, and reachable ceilings for all benchmark datasets and corpus objects used across RAGIntel.

## 1. Benchmark Datasets Overview

| Dataset | Target Task | Query Count | Words (Mean) | Words (Median) | Words (P95) | Tokens (Mean) | Tokens (P95) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `cti-ate` | Technique Extraction | 60 | 168.2 | 163.0 | 221.7 | 168.2 | 221.7 |
| `CTI-ATTACK` | Technique Extraction | 229 | 62.0 | 62.0 | 68.0 | 62.0 | 68.0 |
| `cti-taa` | Threat Actor Attribution | 50 | 1626.5 | 1464.0 | 3014.0 | 1626.5 | 3014.0 |

Total benchmark queries across all three datasets: **339**.

## 2. CTI-TAA Ground-Truth Attribution Formats

CTI-TAA evaluates actor attribution across 50 real-world incident queries. The ground truth contains heterogeneous alias annotations:
- **Single Canonical Name / Direct Identifier**: 30 queries (60.0%)
- **Parenthetical Known Aliases** (`Name (alias AltName1, AltName2)`): 17 queries (34.0%)
- **Disjunctive / Co-attribution Clauses** (`Name1 or Name2`): 3 queries (6.0%)

### Lazarus Attribution Analysis
- Exactly **2 rows** have exact string `ground_truth == "Lazarus"` (Row 18 and Row 46).
- Exactly **5 rows** reference Lazarus when case-insensitive substring matching is evaluated:
  - Row 18: `Lazarus`
  - Row 43: `Lazarus group`
  - Row 44: `Lazarus Group`
  - Row 45: `Lazarus Group`
  - Row 46: `Lazarus`

## 3. MITRE ATT&CK STIX 2.1 Knowledge Base Composition (`E0-STIX-ALL`)

Corpus combines Enterprise, Mobile, and ICS domains from MITRE ATT&CK STIX 2.1 rolling master snapshot (2026-07-31) (active, non-deprecated objects):

| Object Type | STIX 2.1 Type | Active Objects Count | Chunking Method ($E_0'$) | Chunks Count ($E_0'$) | Field Chunks ($E_{1a}$) |
| :--- | :--- | :---: | :--- | :---: | :---: |
| Techniques & Sub-techniques | `attack-pattern` | 926 | Recursive 2000/500 | 4,505 | 3,704 (4 fields) |
| Threat Groups / Actors | `intrusion-set` | 180 | Recursive 2000/500 | 555 | 360 (2 fields) |
| Malware Software | `malware` | 859 | Recursive 2000/500 | 1,486 | 1,718 (2 fields) |
| Tool Software | `tool` | 97 | Recursive 2000/500 | 147 | 194 (2 fields) |
| **Total Active KB Objects** | — | **2062** | **Total Corpus Chunks** | **6,693** | **5,976** |

### Reachable Ceilings
- `cti-ate`: 177 total ground-truth technique mentions; all 177 resolve to active ATT&CK techniques (**100.0% reachable ceiling**).
- `CTI-ATTACK`: 2,042 ground-truth technique instances; all resolve to active techniques (**100.0% reachable ceiling**).
- `cti-taa`: 50 threat groups; all 50 resolve to active STIX intrusion sets (**100.0% reachable ceiling**).
