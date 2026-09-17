"""
Unit & Validation Tests for Module 2: Spatial Graph & Ablation
-------------------------------------------------------------
Validates:
1. District coordinates registry completeness, bounding box, and 1-to-1 match.
2. Spatial graph edge weights, distance bounds, degree constraints, and global connectivity.
3. 16D spectral graph embeddings orthogonality and variance.
4. Ablation test metrics integrity and decision gate schema.
"""

import json
import pytest
import numpy as np
import pandas as pd
import networkx as nx
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

def test_district_coordinates_integrity():
    coords_path = BASE_DIR / "crosswalks" / "district_coordinates.csv"
    assert coords_path.exists(), f"Coordinates file missing: {coords_path}"

    df_coords = pd.read_csv(coords_path)
    assert len(df_coords) == 212, f"Expected 212 districts, got {len(df_coords)}"
    
    # Null checks
    assert df_coords["state"].isna().sum() == 0, "Null states found"
    assert df_coords["district"].isna().sum() == 0, "Null districts found"
    assert df_coords["latitude"].isna().sum() == 0, "Null latitudes found"
    assert df_coords["longitude"].isna().sum() == 0, "Null longitudes found"

    # Physical bounds for India
    assert (df_coords["latitude"] >= 6.0).all() and (df_coords["latitude"] <= 38.0).all(), "Latitudes outside India bounds"
    assert (df_coords["longitude"] >= 68.0).all() and (df_coords["longitude"] <= 98.0).all(), "Longitudes outside India bounds"

    # Match with primary agronomic dataset
    parquet_path = BASE_DIR / "data" / "processed" / "agronomic_cleaned_v4.parquet"
    df_raw = pd.read_parquet(parquet_path, columns=["State", "District"])
    raw_districts = df_raw[["State", "District"]].drop_duplicates()
    assert len(raw_districts) == 212, f"Expected 212 raw districts, got {len(raw_districts)}"

    merged = pd.merge(
        raw_districts,
        df_coords,
        left_on=["State", "District"],
        right_on=["state", "district"],
        how="inner"
    )
    assert len(merged) == 212, f"Coordinates mismatch with raw dataset: merged only {len(merged)}/212"

def test_spatial_graph_topology():
    edges_path = BASE_DIR / "data" / "processed" / "district_graph_edges.csv"
    assert edges_path.exists(), f"Graph edges file missing: {edges_path}"

    df_edges = pd.read_csv(edges_path)
    assert len(df_edges) > 0, "Edges file is empty"

    # Edge weight and distance validity
    assert (df_edges["distance_km"] > 0).all(), "Zero or negative distance found in edges"
    assert (df_edges["similarity_weight"] > 0).all(), "Zero or negative weight found in edges"
    assert (df_edges["similarity_weight"] <= 1.0).all(), "Weight exceeds 1.0"

    # Construct graph and verify topological properties
    G = nx.Graph()
    for _, row in df_edges.iterrows():
        u = (row["source_state"], row["source_district"])
        v = (row["target_state"], row["target_district"])
        G.add_edge(u, v, weight=row["similarity_weight"], distance_km=row["distance_km"])

    assert G.number_of_nodes() == 212, f"Graph node count {G.number_of_nodes()} != 212"
    
    # Verify no orphan nodes and minimum degree constraint
    degrees = [d for _, d in G.degree()]
    assert min(degrees) >= 5, f"Found node with degree {min(degrees)} < 5"

    # Verify global connectivity guaranteed by KNN + MST
    assert nx.number_connected_components(G) == 1, (
        f"Graph has {nx.number_connected_components(G)} disconnected components! Must be 1."
    )

def test_spectral_embeddings_validity():
    emb_path = BASE_DIR / "data" / "processed" / "district_spatial_embeddings.csv"
    assert emb_path.exists(), f"Spatial embeddings missing: {emb_path}"

    df_emb = pd.read_csv(emb_path)
    assert len(df_emb) == 212, f"Embeddings rows {len(df_emb)} != 212"
    assert df_emb.shape[1] == 18, f"Expected 18 columns (State, District + 16 dims), got {df_emb.shape[1]}"

    spatial_cols = [c for c in df_emb.columns if c.startswith("spatial_dim_")]
    assert len(spatial_cols) == 16, f"Expected 16 spatial dimensions, got {len(spatial_cols)}"
    assert not df_emb[spatial_cols].isna().any().any(), "Found NaNs in spatial embeddings"

    # Check non-trivial variance across dimensions (no collapsed representations)
    variances = df_emb[spatial_cols].var()
    assert (variances > 1e-7).all(), f"Detected collapsed/constant embedding dimension: {variances.min()}"

def test_ablation_results_and_gate_schema():
    json_path = BASE_DIR / "data" / "processed" / "m2_spatial_ablation_results.json"
    assert json_path.exists(), f"Ablation results JSON missing: {json_path}"

    with open(json_path) as f:
        results = json.load(f)

    assert "model_a_baseline" in results
    assert "model_b_spatial_graph" in results
    assert "ablation_gate" in results

    gate = results["ablation_gate"]
    assert "threshold_pct" in gate and gate["threshold_pct"] == 3.0
    assert "delta_rmse_pct" in gate
    assert "passed_gate" in gate
    assert "decision" in gate
    assert gate["decision"] in ["RETAIN_SPATIAL_GRAPH", "DROP_SPATIAL_GRAPH"]

    # Metric bounds
    assert results["model_a_baseline"]["test_rmse"] > 0
    assert results["model_b_spatial_graph"]["test_rmse"] > 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
