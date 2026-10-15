"""Small, synthetic tests for proper-training state and calibration; no runtime data."""
import numpy as np
import pandas as pd
import pytest
from modules.regional_data.train import fit_preprocessor, transform, finite_sample_quantile, metric_set


def feature_frame():
    return pd.DataFrame({"State": ["A", "A"], "District": ["D", "D"], "Crop": ["Ragi", "Ragi"],
                         "Season": ["Kharif", "Kharif"], "Year_start": [2010, 2011],
                         "Yield_lag3_mean": [2., np.nan], "Rainfall_mm_lag3_mean": [np.nan, np.nan]})


def test_imputation_is_fit_only_on_proper_training_and_preserves_missingness():
    training = feature_frame()
    state = fit_preprocessor(training)
    future = training.iloc[[0]].copy()
    future["State"] = "Never seen"
    future["Yield_lag3_mean"] = np.nan
    transformed = transform(future, state)
    assert transformed.Yield_lag3_mean.iloc[0] == 2
    assert transformed.Yield_lag3_mean__missing.iloc[0] == 1
    assert transformed.State.isna().all()
    assert "Rainfall_mm_lag3_mean" in state["dropped_all_missing_features"]
    assert "Rainfall_mm_lag3_mean" not in transformed
    assert state["fit_max_year"] == 2011
    future["Yield_lag3_mean"] = 1e9
    assert fit_preprocessor(training) == state


def test_finite_sample_calibration_uses_order_statistic_not_interpolation():
    assert finite_sample_quantile(np.arange(10)) == 8
    with pytest.raises(ValueError, match="Fewer than five"):
        finite_sample_quantile(np.arange(3))


def test_bad_model_results_are_reported_not_rejected_for_failing_improvement():
    frame = pd.DataFrame({"Yield": [1., 2.], "q10": [0., 0.], "q50": [10., 10.], "q90": [12., 12.],
                          "Baseline_q10": [0., 0.], "Baseline_Yield": [1., 2.], "Baseline_q90": [3., 3.]})
    metrics = metric_set(frame)
    assert metrics["model"]["RMSE"] > metrics["baseline"]["RMSE"]
    assert metrics["baseline"]["RMSE"] == 0
    assert metrics["model"]["coverage_80"] == 1
    assert metrics["count"] == 2
