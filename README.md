# RAGIntel

RAGIntel investigates the optimization of retrieval-augmented generation pipelines for cyber threat intelligence (CTI) mapping against the MITRE ATT&CK knowledge base. The study systematically evaluates two architectural interventions: O1 entity resolution (linking threat actors, malware, and tools in unstructured reports to canonical ATT&CK entities) and O2 structure-aware chunking (hierarchical STIX-aware object chunking preserving parent-child and sibling context). Evaluations span threat actor attribution and technique extraction across three benchmark datasets (`cti-ate`, `cti-taa`, and `CTI-ATTACK`).

## Status

Experiments in progress, see `reviews/api_status.md`.

## Repository Structure

```
├── analysis_plan.md        # Pre-registered experimental protocol and hypotheses
├── config.yaml             # Pipeline retrieval and model configurations
├── config_generation.yaml  # Generation model and prompt configuration
├── data/                   # Benchmark datasets and STIX download instructions
│   ├── datasets/           # cti-ate.xlsx, cti-taa.xlsx, CTI-ATTACK.xlsx
│   └── README.md           # Raw MITRE ATT&CK STIX bundle checksums & download notes
├── docs/                   # Documentation and reproduction guide (docs/REPRODUCE.md)
├── report/                 # Formatted publication tables, figures, and dataset stats
├── results/                # Complete per-query metrics, benchmark JSONs, and freeze manifest
├── reviews/                # Phase review reports, row audits, and API quota logs
├── scripts/                # Benchmark execution runners and audit scripts
├── src/                    # Pipeline source code (data loaders, chunkers, retrieval, LLM runner)
└── tests/                  # Integrity and test suites
```

## Setup

### Prerequisites
- Python 3.10+ (tested with Python 3.12)
- Git

### Installation
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env and set GOOGLE_API_KEY=your_key_here
   ```
3. Download raw MITRE STIX bundles (if running offline STIX parsing):
   See instructions in [`data/README.md`](data/README.md).

## Reproduction

To reproduce the benchmark evaluations and generate all summary tables and figures, refer to [`docs/REPRODUCE.md`](docs/REPRODUCE.md).
