# Module 5 Risk-Adjusted Profit Ranking Evaluation

**Risk Aversion Lambda:** 0.5

> **Methodological Note on Baseline Comparison:** Agricultural returns exhibit extremely high year-to-year autocorrelation. Consequently, a naive baseline that simply replicates last year's plantings will frequently achieve very high ranking metrics (NDCG). The primary contribution of this system is not to 'beat' the baseline on expected ranking, but to provide a **calibrated quantification of downside risk** which the naive baseline cannot offer.

## System Performance (Risk-Adjusted)
- **NDCG@3:** 0.7582
- **Top-1 in True Top-3 Rate:** 68.73%

## Naive Agricultural Baseline (T-1 Plantings, No Risk Awareness)
- **NDCG@3:** 0.8805
- **Top-1 in True Top-3 Rate:** 85.24%