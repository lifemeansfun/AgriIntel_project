"""
GNN Spatial Embedding & Tabular Ablation Pipeline
------------------------------------------------
1. Computes 16D Spectral Graph Embeddings (Laplacian Eigenmaps) from spatial adjacency.
2. Appends spatial embeddings to the economic seasonal fact table.
3. Performs temporal out-of-sample holdout ablation test comparing:
   - Model A: Baseline Tabular LightGBM (Agronomic + Environmental features)
   - Model B: Spatial Graph LightGBM (Baseline + 16D Spatial Embeddings)
4. Evaluates the strict >3% RMSE improvement gate to determine whether to retain
   or drop the spatial graph topology.
"""

import sys
import json
import logging
from pathlib import Path
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.manifold import SpectralEmbedding
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("gnn_ablation")

ABLATION_THRESHOLD_PCT = 3.0
EMBEDDING_DIM = 16
SPLIT_YEAR = 2016

def compute_spectral_embeddings(
    coords_csv: str = "crosswalks/district_coordinates.csv",
    edges_csv: str = "data/processed/district_graph_edges.csv",
    n_dim: int = EMBEDDING_DIM
) -> pd.DataFrame:
    """
    Computes 16D continuous Laplacian Eigenmaps from the spatial graph.
    Constructs symmetric adjacency matrix with Gaussian RBF similarity weights.
    """
    df_coords = pd.read_csv(coords_csv)
    df_edges = pd.read_csv(edges_csv)

    n_nodes = len(df_coords)
    logger.info(f"Generating {n_dim}D Spectral Embeddings for {n_nodes} districts...")

    # Create index mapping
    node_to_idx = {
        (row["state"], row["district"]): idx for idx, row in df_coords.iterrows()
    }

    # Build weighted adjacency matrix
    adj_matrix = np.zeros((n_nodes, n_nodes), dtype=np.float64)
    for _, edge in df_edges.iterrows():
        u = node_to_idx[(edge["source_state"], edge["source_district"])]
        v = node_to_idx[(edge["target_state"], edge["target_district"])]
        w = float(edge["similarity_weight"])
        adj_matrix[u, v] = w
        adj_matrix[v, u] = w

    # Spectral embedding using precomputed affinity
    spectral = SpectralEmbedding(
        n_components=n_dim,
        affinity="precomputed",
        random_state=42
    )
    embeddings = spectral.fit_transform(adj_matrix)

    # Defensive check: no NaNs
    assert not np.isnan(embeddings).any(), "NaN values found in spectral embeddings!"

    emb_cols = [f"spatial_dim_{i}" for i in range(n_dim)]
    emb_df = pd.DataFrame(embeddings, columns=emb_cols)
    emb_df["State"] = df_coords["state"]
    emb_df["District"] = df_coords["district"]

    # Reorder columns
    ordered_cols = ["State", "District"] + emb_cols
    emb_df = emb_df[ordered_cols]
    logger.info(f"Generated {len(emb_df)} district spatial embeddings with shape {embeddings.shape}.")
    return emb_df

def prepare_ablation_dataset(
    fact_parquet: str = "data/processed/fact_economic_seasonal.parquet",
    emb_df: pd.DataFrame = None
) -> tuple[pd.DataFrame, pd.DataFrame, list[str], list[str]]:
    """
    Merges economic seasonal table with district embeddings and splits into
    out-of-sample temporal train (Year_start < 2016) and test (Year_start >= 2016).
    """
    logger.info(f"Loading economic seasonal dataset from {fact_parquet}...")
    df_fact = pd.read_parquet(fact_parquet)

    # Defensive merge with spatial embeddings
    merged_df = pd.merge(df_fact, emb_df, on=["State", "District"], how="left")
    
    spatial_cols = [c for c in emb_df.columns if c.startswith("spatial_dim_")]
    missing_spatial = merged_df[spatial_cols].isna().any(axis=1).sum()
    if missing_spatial > 0:
        raise ValueError(f"FATAL: {missing_spatial} observations missing spatial embeddings after merge!")
    
    logger.info(f"Successfully merged spatial embeddings. Total dataset size: {len(merged_df)} rows.")

    # Define feature sets
    cat_cols = ["State", "Crop", "Season"]
    num_cols = [
        "Area",
        "Rainfall_mm",
        "Mean_Daily_Rainfall_mm",
        "Rainy_Days",
        "Heavy_Rain_Days",
        "Max_Daily_Rainfall_mm",
        "total_irrigated_ha",
        "canal_share",
        "irrigation_intensity",
        "Nitrogen_index",
        "Phosphorus_index",
        "Potassium_index",
        "Organic_Carbon_index",
        "pct_acidic",
        "pct_alkaline",
        "pct_saline"
    ]

    base_features = cat_cols + num_cols
    spatial_features = base_features + spatial_cols

    # Cast categoricals to category dtype for LightGBM
    for c in cat_cols:
        merged_df[c] = merged_df[c].astype("category")

    # Defensive filter: Drop observations with non-positive or NaN target
    valid_mask = merged_df["Yield"].notna() & (merged_df["Yield"] >= 0)
    merged_df = merged_df[valid_mask].copy()

    # Temporal split
    train_df = merged_df[merged_df["Year_start"] < SPLIT_YEAR].copy()
    test_df = merged_df[merged_df["Year_start"] >= SPLIT_YEAR].copy()

    logger.info(f"Temporal Split: Train (2000-{SPLIT_YEAR-1}): {len(train_df)} rows | Test ({SPLIT_YEAR}-2019): {len(test_df)} rows.")
    return train_df, test_df, base_features, spatial_features

def train_and_evaluate(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    feature_cols: list[str],
    model_name: str
) -> tuple[float, float, float, np.ndarray, pd.Series]:
    """Train LightGBM Regressor and evaluate out-of-sample metrics."""
    X_train = train_df[feature_cols]
    y_train = train_df["Yield"]

    X_test = test_df[feature_cols]
    y_test = test_df["Yield"]

    model = lgb.LGBMRegressor(
        objective="regression",
        metric="rmse",
        n_estimators=300,
        learning_rate=0.05,
        num_leaves=31,
        random_state=42,
        n_jobs=-1,
        verbose=-1
    )

    logger.info(f"Training {model_name} on {len(X_train)} samples with {len(feature_cols)} features...")
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    preds = np.clip(preds, 0, None)  # Defensive clip to non-negative yield

    rmse = float(np.sqrt(mean_squared_error(y_test, preds)))
    mae = float(mean_absolute_error(y_test, preds))
    r2 = float(r2_score(y_test, preds))

    importances = pd.Series(model.feature_importances_, index=feature_cols).sort_values(ascending=False)
    logger.info(f"{model_name} Results -> RMSE: {rmse:.4f} | MAE: {mae:.4f} | R2: {r2:.4f}")
    return rmse, mae, r2, preds, importances

def run_ablation(
    coords_csv: str = "crosswalks/district_coordinates.csv",
    edges_csv: str = "data/processed/district_graph_edges.csv",
    fact_parquet: str = "data/processed/fact_economic_seasonal.parquet",
    output_emb_csv: str = "data/processed/district_spatial_embeddings.csv",
    output_json: str = "data/processed/m2_spatial_ablation_results.json",
    output_report: str = "data/processed/m2_ablation_report.md"
) -> dict:
    """Execute complete GNN Spatial Ablation study."""
    # 1. Generate & Save Spatial Embeddings
    emb_df = compute_spectral_embeddings(coords_csv, edges_csv, EMBEDDING_DIM)
    Path(output_emb_csv).parent.mkdir(parents=True, exist_ok=True)
    emb_df.to_csv(output_emb_csv, index=False)
    logger.info(f"Saved district spatial embeddings to {output_emb_csv}.")

    # 2. Prepare Data
    train_df, test_df, base_features, spatial_features = prepare_ablation_dataset(fact_parquet, emb_df)

    # 3. Train Model A (Baseline)
    rmse_a, mae_a, r2_a, _, imp_a = train_and_evaluate(train_df, test_df, base_features, "Model A (Tabular Baseline)")

    # 4. Train Model B (Spatial Graph)
    rmse_b, mae_b, r2_b, _, imp_b = train_and_evaluate(train_df, test_df, spatial_features, "Model B (Spatial Graph)")

    # 5. Calculate Delta and Gate Decision
    improvement_pct = ((rmse_a - rmse_b) / rmse_a) * 100.0
    passed_gate = improvement_pct >= ABLATION_THRESHOLD_PCT

    if passed_gate:
        decision = "RETAIN_SPATIAL_GRAPH"
        rationale = (
            f"Spatial embeddings improved test RMSE by {improvement_pct:.2f}%, "
            f"which exceeds the academic threshold of {ABLATION_THRESHOLD_PCT}%. Retaining graph topology."
        )
    else:
        decision = "DROP_SPATIAL_GRAPH"
        rationale = (
            f"Spatial embeddings yielded a {improvement_pct:.2f}% improvement in test RMSE, "
            f"failing to clear the empirical {ABLATION_THRESHOLD_PCT}% gate. "
            f"In accordance with Occam's razor, the spatial graph topology is formally dropped."
        )

    logger.info(f"\n================ ABLATION GATE RESULTS ================\n"
                f"Model A (Baseline Tabular) RMSE : {rmse_a:.4f}\n"
                f"Model B (Spatial Graph)    RMSE : {rmse_b:.4f}\n"
                f"Delta Improvement              : {improvement_pct:+.2f}%\n"
                f"Gate Threshold Required        : >={ABLATION_THRESHOLD_PCT:.1f}%\n"
                f"Decision                       : {decision}\n"
                f"Rationale                      : {rationale}\n"
                f"=======================================================")

    # Top spatial feature importances
    spatial_cols = [c for c in spatial_features if c.startswith("spatial_dim_")]
    spatial_imp = imp_b[spatial_cols].sort_values(ascending=False)

    results = {
        "evaluation_split": {
            "strategy": "Temporal Out-of-Sample Holdout",
            "train_years": f"2000-{SPLIT_YEAR-1}",
            "train_samples": len(train_df),
            "test_years": f"{SPLIT_YEAR}-2019",
            "test_samples": len(test_df)
        },
        "model_a_baseline": {
            "features_count": len(base_features),
            "test_rmse": round(rmse_a, 4),
            "test_mae": round(mae_a, 4),
            "test_r2": round(r2_a, 4),
            "top_features": imp_a.head(5).to_dict()
        },
        "model_b_spatial_graph": {
            "features_count": len(spatial_features),
            "spatial_embedding_dim": EMBEDDING_DIM,
            "test_rmse": round(rmse_b, 4),
            "test_mae": round(mae_b, 4),
            "test_r2": round(r2_b, 4),
            "top_features": imp_b.head(5).to_dict(),
            "spatial_feature_importances": spatial_imp.to_dict()
        },
        "ablation_gate": {
            "threshold_pct": ABLATION_THRESHOLD_PCT,
            "delta_rmse_pct": round(improvement_pct, 4),
            "passed_gate": bool(passed_gate),
            "decision": decision,
            "rationale": rationale
        }
    }

    # Save JSON manifest
    with open(output_json, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"Saved ablation manifest to {output_json}.")

    # Generate Markdown Report
    report_md = f"""# Module 2: Spatial Graph Construction & Ablation Report

## Executive Summary
This ablation study empirically evaluates whether incorporating spatial graph topology (via 16D Laplacian Eigenmaps from a geographic KNN+MST adjacency graph across 212 Indian districts) provides a statistically and practically significant improvement in out-of-sample crop yield forecasting.

- **Gate Rule:** Spatial graph embeddings must improve out-of-sample Test RMSE by $\\ge {ABLATION_THRESHOLD_PCT}\\%$ over a pure tabular baseline model.
- **Decision:** `{decision}`
- **Test RMSE Improvement:** `{improvement_pct:+.2f}%`

---

## Experimental Setup
- **Dataset:** `fact_economic_seasonal.parquet` (95,667 observations spanning 2000–2019)
- **Temporal Holdout:**
  - **Train Set (2000–{SPLIT_YEAR-1}):** {len(train_df):,} samples
  - **Out-of-Sample Test Set ({SPLIT_YEAR}–2019):** {len(test_df):,} samples
- **Graph Topology:** 212 districts, KNN ($K=5$) + Minimum Spanning Tree backbone, RBF Gaussian similarity weights.
- **Embedding Formulation:** 16D Normalized Graph Laplacian Eigenmaps ($L_{{sym}} = I - D^{{-1/2}} W D^{{-1/2}}$).

---

## Comparative Performance

| Metric | Model A (Baseline Tabular) | Model B (Spatial Graph) | Relative Delta |
| :--- | :---: | :---: | :---: |
| **Test RMSE** | **{rmse_a:.4f}** | **{rmse_b:.4f}** | **{improvement_pct:+.2f}%** |
| **Test MAE** | {mae_a:.4f} | {mae_b:.4f} | {((mae_a - mae_b)/mae_a)*100:+.2f}% |
| **Test $R^2$** | {r2_a:.4f} | {r2_b:.4f} | {r2_b - r2_a:+.4f} |
| **Features** | {len(base_features)} | {len(spatial_features)} | +{EMBEDDING_DIM} dims |

---

## Gate Verdict & Scientific Rationale
> [!NOTE]
> **Decision: {decision}**
> {rationale}

### Top Baseline Features
```
{imp_a.head(8).to_string()}
```

### Top Spatial Dimension Importances
```
{spatial_imp.head(6).to_string()}
```
"""
    with open(output_report, "w") as f:
        f.write(report_md)
    logger.info(f"Saved ablation report to {output_report}.")

    return results

if __name__ == "__main__":
    run_ablation()
