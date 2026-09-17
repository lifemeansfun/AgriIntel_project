import pytest
import pandas as pd
import numpy as np
import json
from pathlib import Path

base_dir = Path('/Users/manishharigovind/Desktop/VIT Vellore/5th semester/Data science proogramming/DSP_project')

@pytest.fixture
def recommendations_data():
    path = base_dir / 'data/processed/fact_recommendations.parquet'
    assert path.exists(), f"Recommendations missing at {path}"
    return pd.read_parquet(path)

@pytest.fixture
def ranking_manifest():
    path = base_dir / 'data/processed/m5_ranking_manifest.json'
    assert path.exists(), f"Ranking manifest missing at {path}"
    with open(path, 'r') as f:
        return json.load(f)

def test_invariant_1_risk_positive(recommendations_data):
    """Invariant 1: Downside Risk must always be >= 0."""
    # Since q50 >= q10 and p50 >= p10, expected profit is always >= pessimistic profit.
    # Allowing for tiny floating point variations, we check >= -1e-4
    assert (recommendations_data['Downside_Risk'] >= -1e-4).all(), "Found negative downside risk."

def test_invariant_2_monotonic_ranking(recommendations_data):
    """Invariant 2: Recommendation Score for Rank 1 >= Rank 2."""
    df = recommendations_data
    
    for _, group in df.groupby(['District', 'Season', 'Year_start']):
        if len(group) < 2:
            continue
            
        group = group.sort_values('Recommended_Rank')
        scores = group['Recommendation_Score'].values
        
        # Check monotonic decreasing
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i+1] - 1e-5, f"Ranking inversion detected. Rank {i+1} score {scores[i]} < Rank {i+2} score {scores[i+1]}"

def test_invariant_3_ndcg_target(ranking_manifest):
    """Invariant 3: System must beat NDCG@3 >= 0.70."""
    ndcg = ranking_manifest['Model']['NDCG_3']
    assert ndcg >= 0.70, f"NDCG@3 target missed. Achieved {ndcg:.4f}, expected >= 0.70."

def test_invariant_4_cost_fallback_integrity(recommendations_data):
    """Invariant 4: Ensure no crop has a NaN cost after hierarchical fallback."""
    assert not recommendations_data['Real_Cost_per_Hectare'].isna().any(), "NaN costs present in final dataset."
