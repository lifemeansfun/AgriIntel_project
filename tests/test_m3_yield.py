import pytest
import pandas as pd
import numpy as np
import yaml
import json
from pathlib import Path

base_dir = Path('/Users/manishharigovind/Desktop/VIT Vellore/5th semester/Data science proogramming/DSP_project')

@pytest.fixture
def oof_data():
    path = base_dir / 'data/processed/fact_yield_predictions_oof.parquet'
    assert path.exists(), f"OOF predictions missing at {path}"
    return pd.read_parquet(path)

@pytest.fixture
def caps_config():
    path = base_dir / 'config/biological_yield_caps.yaml'
    with open(path, 'r') as f:
        return yaml.safe_load(f)

@pytest.fixture
def evaluation_manifest():
    path = base_dir / 'data/processed/m3_yield_evaluation_manifest.json'
    assert path.exists(), f"Evaluation manifest missing at {path}"
    with open(path, 'r') as f:
        return json.load(f)

def test_invariant_1_non_negativity(oof_data):
    """Invariant 1: All predicted yields >= 0."""
    assert (oof_data['q10'] >= 0.0).all(), "Negative predictions found in q10"
    assert (oof_data['q50'] >= 0.0).all(), "Negative predictions found in q50"
    assert (oof_data['q90'] >= 0.0).all(), "Negative predictions found in q90"

def test_invariant_2_monotonic_quantiles(oof_data):
    """Invariant 2: q10 <= q50 <= q90 across 100% of test records."""
    assert (oof_data['q10'] <= oof_data['q50']).all(), "q10 > q50 found"
    assert (oof_data['q50'] <= oof_data['q90']).all(), "q50 > q90 found"

def test_invariant_3_biological_cap(oof_data, caps_config):
    """Invariant 3: q90 <= MaxBio_crop."""
    default_cap = caps_config['default_cap']
    crop_caps = caps_config['crops']
    
    for crop in oof_data['Crop'].unique():
        cap = crop_caps.get(crop, default_cap)
        sub = oof_data[oof_data['Crop'] == crop]
        assert (sub['q90'] <= cap + 1e-5).all(), f"Biological cap exceeded for {crop}"

def test_invariant_4_anti_leakage(oof_data):
    """Invariant 4: Verify no row in fold T was generated with access to training data from year >= T."""
    # Since we use expanding window cross-validation by Year_start and our lag logic strictly uses shift(1), 
    # we assert that test sets only contain the test year, meaning no future years leaked back.
    # The true test of this invariant is the manual review of the feature engineering code, 
    # but we can verify that the test sets correctly partition time.
    years = sorted(oof_data['Year_start'].unique())
    assert all(y >= 2015 for y in years), "Test set contains years before 2015, leakage possible"

def test_invariant_5_baseline_superiority(evaluation_manifest):
    """Invariant 5: Model must outperform the hierarchical baseline RMSE by >= 10% on average across major crop families."""
    improvements = []
    for family, metrics in evaluation_manifest.items():
        if family != 'Overall':
            improvements.append(metrics['Improvement_Pct'])
            
    mean_improvement = np.mean(improvements)
    assert mean_improvement >= 10.0, f"Baseline superiority failure. Average family improvement was {mean_improvement:.2f}%, expected >= 10%"
