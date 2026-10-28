# AgriIntel Patent Evidence Packet

**Status:** Pre-Filing Reproducible Technical Artifacts  
**Date:** October 28, 2026  
**Applicability:** Indian Patent Office (Form 1 / Form 2, Section 3(k) Compliance) & USPTO (§ 101 *Alice/Mayo* Technical Effect)

---

## Directory Overview

```text
patent_evidence/
├── README.md                      <- This document
├── environment.txt                <- Hardware, OS, Python, and dependency versions
├── test_report.txt                <- Full pytest execution log (118/118 passing tests)
├── benchmark_config.json          <- Mathematical parameters, seeds, and scenario definitions
├── implementation_manifest.csv    <- Traceability table linking claims to source files and tests
├── prior_art_matrix.csv           <- Claim-by-claim differentiation against closest prior art
├── known_limitations.md           <- Explicit operational boundaries and statistical approximations
├── raw_results/                   <- Machine-readable empirical output (JSON)
│   ├── benchmark_results.json     <- Master combined benchmark outputs
│   ├── vpcr_microbenchmarks.json  <- O(L) vs O(L^2) runtime benchmarks across L in [10, 500]
│   ├── vpcr_exceedance_results.json <- 5,000 synthetic harvest exceedance simulation
│   ├── concurrency_benchmark.json <- Concurrency comparison (Strict OCC vs OCC+Retry vs Slippage)
│   └── esrr_multi_scenario.json   <- Multi-scenario evaluation (Coimbatore, Pune, Ludhiana)
└── processed_results/             <- Structured tables and statistical analysis
    ├── summary_table.md           <- Markdown comparison tables
    └── empirical_analysis.md      <- In-depth technical effect and statistical analysis
```

---

## Reproduction Commands

To reproduce all unit tests, adversarial security tests, and empirical benchmarks from a clean repository clone:

1. **Activate Environment:**
   ```powershell
   .venv\Scripts\activate
   ```

2. **Run Comprehensive Test Suite:**
   ```powershell
   python -m pytest tests/test_novelties.py -v
   python -m pytest tests/ -v
   ```

3. **Execute Benchmark Suite and Regenerate Raw Evidence:**
   ```powershell
   python -m modules.novelty.benchmarks
   ```

All raw outputs will be re-generated and verified in `patent_evidence/raw_results/`.
