"""
Spatial Graph Construction Pipeline
-----------------------------------
Builds a Haversine distance matrix across all 212 Indian districts and constructs
a K-Nearest Neighbors (KNN) spatial adjacency graph with RBF similarity weights.
Exports graph topology to `data/processed/district_graph_edges.csv`.
"""

import sys
import logging
from pathlib import Path
import numpy as np
import pandas as pd
import networkx as nx
from sklearn.metrics.pairwise import haversine_distances

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("graph_builder")

EARTH_RADIUS_KM = 6371.0088
DEFAULT_K = 5

def validate_input_data(df: pd.DataFrame) -> None:
    """Defensive assertions on input coordinates dataset."""
    required_cols = {"state", "district", "latitude", "longitude"}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"Missing required columns in coordinates: {required_cols - set(df.columns)}")
    if len(df) != 212:
        logger.warning(f"Expected 212 districts, found {len(df)}.")
    if df[["latitude", "longitude"]].isna().any().any():
        raise ValueError("Null values detected in coordinates!")
    if (df["latitude"] < 6.0).any() or (df["latitude"] > 38.0).any():
        raise ValueError("Latitude values outside India bounds [6.0, 38.0]!")
    if (df["longitude"] < 68.0).any() or (df["longitude"] > 98.0).any():
        raise ValueError("Longitude values outside India bounds [68.0, 98.0]!")

def compute_haversine_distance_matrix(df: pd.DataFrame) -> np.ndarray:
    """
    Computes pairwise great-circle Haversine distances in kilometers.
    Requires coordinates in (latitude, longitude) order converted to radians.
    """
    coords_rad = np.radians(df[["latitude", "longitude"]].values)
    dist_matrix_rad = haversine_distances(coords_rad, coords_rad)
    dist_matrix_km = dist_matrix_rad * EARTH_RADIUS_KM
    return dist_matrix_km

def build_knn_graph(
    df: pd.DataFrame,
    dist_matrix_km: np.ndarray,
    k: int = DEFAULT_K
) -> tuple[nx.Graph, pd.DataFrame]:
    """
    Constructs an undirected graph combining K-Nearest Neighbors (local clusters)
    and a Minimum Spanning Tree (MST backbone) to guarantee 100% global connectivity.
    Edges are weighted using an RBF Gaussian kernel: W_ij = exp(-d_ij^2 / (2 * sigma^2)).
    """
    from scipy.sparse.csgraph import minimum_spanning_tree

    n_nodes = len(df)
    G = nx.Graph()

    # Add nodes with attributes
    for idx, row in df.iterrows():
        G.add_node(idx, district=row["district"], state=row["state"], lat=row["latitude"], lon=row["longitude"])

    # 1. Extract K-nearest neighbor edges
    knn_edges = set()
    all_knn_distances = []
    for i in range(n_nodes):
        sorted_indices = np.argsort(dist_matrix_km[i])
        knn_indices = sorted_indices[1 : k + 1]
        for j in knn_indices:
            edge = tuple(sorted((i, j)))
            knn_edges.add(edge)
            all_knn_distances.append(dist_matrix_km[i, j])

    # 2. Extract Minimum Spanning Tree (MST) edges to guarantee global graph connectivity
    mst = minimum_spanning_tree(dist_matrix_km)
    mst_edges = set()
    mst_coo = mst.tocoo()
    for i, j in zip(mst_coo.row, mst_coo.col):
        mst_edges.add(tuple(sorted((int(i), int(j)))))

    # Union of KNN and MST
    all_edges = knn_edges.union(mst_edges)
    logger.info(f"Graph edges: {len(knn_edges)} KNN + {len(mst_edges)} MST -> {len(all_edges)} unique edges.")

    # Compute characteristic scale sigma for Gaussian RBF weighting
    sigma = float(np.median(all_knn_distances))
    if sigma <= 0:
        sigma = 1.0
    logger.info(f"RBF Kernel sigma (median KNN distance): {sigma:.2f} km")

    edge_records = []
    for u, v in all_edges:
        dist_km = float(dist_matrix_km[u, v])
        raw_weight = float(np.exp(-(dist_km ** 2) / (2 * (sigma ** 2))))
        weight = max(raw_weight, 1e-6)  # Defensive positive floor to prevent disconnected components
        G.add_edge(u, v, distance_km=dist_km, weight=weight)
        
        edge_records.append({
            "source_idx": u,
            "source_district": df.loc[u, "district"],
            "source_state": df.loc[u, "state"],
            "target_idx": v,
            "target_district": df.loc[v, "district"],
            "target_state": df.loc[v, "state"],
            "distance_km": round(dist_km, 2),
            "similarity_weight": round(weight, 8)
        })

    edges_df = pd.DataFrame(edge_records).sort_values("distance_km").reset_index(drop=True)
    return G, edges_df

def validate_graph_topology(G: nx.Graph, n_expected_nodes: int, k: int) -> dict:
    """Defensive assertions on graph topology."""
    if G.number_of_nodes() != n_expected_nodes:
        raise ValueError(f"Graph node count mismatch: {G.number_of_nodes()} vs {n_expected_nodes}")

    degrees = [d for _, d in G.degree()]
    min_deg = min(degrees)
    max_deg = max(degrees)
    avg_deg = sum(degrees) / len(degrees)

    if min_deg < k:
        raise ValueError(f"Found node with degree {min_deg} < K ({k})! Isolated or insufficiently connected node.")

    num_components = nx.number_connected_components(G)
    component_sizes = [len(c) for c in nx.connected_components(G)]

    stats = {
        "num_nodes": G.number_of_nodes(),
        "num_edges": G.number_of_edges(),
        "min_degree": min_deg,
        "max_degree": max_deg,
        "avg_degree": round(avg_deg, 2),
        "num_connected_components": num_components,
        "component_sizes": component_sizes
    }
    logger.info(f"Graph topology validated: {stats}")
    return stats

def run_graph_construction(
    coords_csv: str = "crosswalks/district_coordinates.csv",
    output_edges_csv: str = "data/processed/district_graph_edges.csv",
    k: int = DEFAULT_K
) -> tuple[nx.Graph, pd.DataFrame, np.ndarray]:
    coords_path = Path(coords_csv)
    if not coords_path.exists():
        raise FileNotFoundError(f"District coordinates not found at {coords_path}")

    df_coords = pd.read_csv(coords_path)
    validate_input_data(df_coords)
    logger.info(f"Loaded {len(df_coords)} verified district coordinates.")

    logger.info("Computing pairwise Haversine distance matrix (km)...")
    dist_matrix = compute_haversine_distance_matrix(df_coords)

    logger.info(f"Building K-Nearest Neighbors (K={k}) spatial graph...")
    G, edges_df = build_knn_graph(df_coords, dist_matrix, k=k)

    validate_graph_topology(G, len(df_coords), k)

    output_path = Path(output_edges_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    edges_df.to_csv(output_path, index=False)
    logger.info(f"Successfully saved {len(edges_df)} graph edges to {output_path}.")

    return G, edges_df, dist_matrix

if __name__ == "__main__":
    run_graph_construction()
