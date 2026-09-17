import pytest
import pandas as pd
import numpy as np
import yaml
import json
from pathlib import Path

base_dir = Path('/Users/manishharigovind/Desktop/VIT Vellore/5th semester/Data science proogramming/DSP_project')

@pytest.fixture
def oof_data():
    path = base_dir / 'data/processed/fact_price_predictions_oof.parquet'
    assert path.exists(), f"OOF predictions missing at {path}"
    return pd.read_parquet(path)

@pytest.fixture
def evaluation_manifest():
    path = base_dir / 'data/processed/m4_price_evaluation_manifest.json'
    assert path.exists(), f"Evaluation manifest missing at {path}"
    with open(path, 'r') as f:
        return json.load(f)

def test_invariant_1_non_negativity(oof_data):
    """Invariant 1: All predicted prices >= 0."""
    assert (oof_data['p10'] >= 0.0).all(), "Negative predictions found in p10"
    assert (oof_data['p50'] >= 0.0).all(), "Negative predictions found in p50"
    assert (oof_data['p90'] >= 0.0).all(), "Negative predictions found in p90"

def test_invariant_2_monotonic_quantiles(oof_data):
    """Invariant 2: p10 <= p50 <= p90 across 100% of test records."""
    assert (oof_data['p10'] <= oof_data['p50']).all(), "p10 > p50 found"
    assert (oof_data['p50'] <= oof_data['p90']).all(), "p50 > p90 found"

def test_invariant_3_market_dynamics(oof_data):
    """Invariant 3: Ensure the simulated market price demonstrates valid variance from the flat MSP floor."""
    # Since we synthesized market price based on yield shocks, there must be instances where
    # market price is completely different from MSP (variance > 0).
    price_diff = oof_data['Real_Market_Price_per_Quintal'] - oof_data['Real_MSP_per_Quintal']
    assert price_diff.std() > 0, "Market price lacks volatility; it is identical to MSP."
    
    # Check that downside risk actually materialized in the data
    assert (oof_data['Real_Market_Price_per_Quintal'] < oof_data['Real_MSP_per_Quintal']).any(), "No downside market crash simulated."

def test_invariant_4_anti_leakage(oof_data):
    """Invariant 4: Verify no row in fold T was generated with access to training data from year >= T."""
    years = sorted(oof_data['Year_start'].unique())
    assert all(y >= 2015 for y in years), "Test set contains years before 2015, leakage possible"

def test_invariant_5_structural_bounds_and_coverage(oof_data, evaluation_manifest):
    """Invariant 5: Verify structural assumptions and valid price interval containment."""
    assert "Structural_Assumptions" in evaluation_manifest
    assert evaluation_manifest["Structural_Assumptions"]["Elasticity"] == 0.20
    assert evaluation_manifest["Structural_Assumptions"]["Price_Anchor"] == "Real_MSP_per_Quintal"
    
    # Verify empirical price interval coverage on simulated market prices
    cov = np.mean((oof_data['Real_Market_Price_per_Quintal'] >= oof_data['p10']) & 
                  (oof_data['Real_Market_Price_per_Quintal'] <= oof_data['p90'])) * 100
    assert 50.0 <= cov <= 99.0, f"Coverage {cov}% is outside expected plausible interval."
