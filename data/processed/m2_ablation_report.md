# Module 2: Spatial Graph Construction & Ablation Report

## Executive Summary
This ablation study empirically evaluates whether incorporating spatial graph topology (via 16D Laplacian Eigenmaps from a geographic KNN+MST adjacency graph across 212 Indian districts) provides a statistically and practically significant improvement in out-of-sample crop yield forecasting.

- **Gate Rule:** Spatial graph embeddings must improve out-of-sample Test RMSE by $\ge 3.0\%$ over a pure tabular baseline model.
- **Decision:** `DROP_SPATIAL_GRAPH`
- **Test RMSE Improvement:** `+1.02%`

---

## Experimental Setup
- **Dataset:** `fact_economic_seasonal.parquet` (95,667 observations spanning 2000–2019)
- **Temporal Holdout:**
  - **Train Set (2000–2015):** 74,205 samples
  - **Out-of-Sample Test Set (2016–2019):** 21,462 samples
- **Graph Topology:** 212 districts, KNN ($K=5$) + Minimum Spanning Tree backbone, RBF Gaussian similarity weights.
- **Embedding Formulation:** 16D Normalized Graph Laplacian Eigenmaps ($L_{sym} = I - D^{-1/2} W D^{-1/2}$).

---

## Comparative Performance

| Metric | Model A (Baseline Tabular) | Model B (Spatial Graph) | Relative Delta |
| :--- | :---: | :---: | :---: |
| **Test RMSE** | **4.8526** | **4.8030** | **+1.02%** |
| **Test MAE** | 1.8603 | 1.8410 | +1.04% |
| **Test $R^2$** | 0.8932 | 0.8954 | +0.0022 |
| **Features** | 19 | 35 | +16 dims |

---

## Gate Verdict & Scientific Rationale
> [!NOTE]
> **Decision: DROP_SPATIAL_GRAPH**
> Spatial embeddings yielded a 1.02% improvement in test RMSE, failing to clear the empirical 3.0% gate. In accordance with Occam's razor, the spatial graph topology is formally dropped.

### Top Baseline Features
```
Crop                     1186
Area                     1127
Rainy_Days                738
irrigation_intensity      619
canal_share               582
total_irrigated_ha        571
Max_Daily_Rainfall_mm     562
Rainfall_mm               422
```

### Top Spatial Dimension Importances
```
spatial_dim_0     397
spatial_dim_14    147
spatial_dim_7     121
spatial_dim_8     121
spatial_dim_5     119
spatial_dim_10    118
```
