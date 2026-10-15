"""Adversarial historical-isolation tests; all inputs are local synthetic frames."""
import numpy as np
import pandas as pd
import pytest

from modules.m3_yield.baselines import generate_baseline
from modules.m3_yield.features import build_ex_ante_features
from modules.regional_data.data import KEY, attach_prior_economics, structural_clean


def raw_frame():
    rows = []
    for state, district, multiplier in [("A", "Same", 1), ("B", "Same", 100), ("A", "Other", 10)]:
        for year in range(2010, 2020):
            rows.append(dict(State=state, District=district, Crop="Ragi", Season="Kharif", Year_start=year,
                             Area=10., Production=10. * multiplier * (year - 2009),
                             Rainfall_mm=float(year - 2000), Nitrogen_index=float(year - 2009),
                             irrigation_intensity=.4, canal_share=.2))
    return pd.DataFrame(rows)


def prepared(raw):
    return generate_baseline(build_ex_ante_features(structural_clean(raw)[0]))


def test_future_perturbation_cannot_change_past_lags_or_baseline():
    raw = raw_frame()
    before = prepared(raw)
    changed = raw.copy()
    changed.loc[changed.Year_start >= 2017, ["Production", "Rainfall_mm", "Nitrogen_index", "irrigation_intensity"]] = 1e9
    after = prepared(changed)
    cols = KEY + [c for c in before if "_lag3_" in c or c.startswith("Baseline_")]
    pd.testing.assert_frame_equal(before.loc[before.Year_start <= 2017, cols].reset_index(drop=True),
                                  after.loc[after.Year_start <= 2017, cols].reset_index(drop=True))


def test_same_named_districts_and_group_boundaries_do_not_cross():
    rows = prepared(raw_frame())
    a = rows[(rows.State == "A") & (rows.District == "Same") & (rows.Year_start == 2013)].iloc[0]
    b = rows[(rows.State == "B") & (rows.District == "Same") & (rows.Year_start == 2013)].iloc[0]
    assert a.Yield_lag3_mean == 2
    assert b.Yield_lag3_mean == 200
    assert a.Baseline_Yield == 2
    assert b.Baseline_Yield == 200
    assert rows.loc[rows.Year_start == 2010, "Yield_lag3_mean"].isna().all()
    assert rows.loc[rows.Year_start == 2010, "Baseline_Yield"].isna().all()


def test_missing_calendar_years_never_admit_old_observations():
    raw = raw_frame().query("State == 'A' and District == 'Same'").copy()
    raw = raw[raw.Year_start.isin([2010, 2011, 2018, 2019])]
    rows = prepared(raw)
    assert pd.isna(rows.loc[rows.Year_start == 2018, "Yield_lag3_mean"].iloc[0])
    assert pd.isna(rows.loc[rows.Year_start == 2018, "Baseline_Yield"].iloc[0])
    assert rows.loc[rows.Year_start == 2019, "Yield_lag3_count"].iloc[0] == 1
    assert rows.loc[rows.Year_start == 2019, "Yield_lag3_mean"].iloc[0] == 9


def test_shuffled_and_duplicate_raw_rows_have_stable_keys_and_yields():
    raw = raw_frame()
    # Exact duplicate is removed; conflicting same-key record adds its Area/Production.
    extra = raw.iloc[[0]].copy()
    extra["Area"], extra["Production"] = 20., 60.
    duplicate_input = pd.concat([raw, raw.iloc[[0]], extra], ignore_index=True)
    clean, _, audit = structural_clean(duplicate_input)
    assert audit["exact_duplicates_removed"] == 1
    assert audit["collision_keys_aggregated"] == 1
    assert len(clean) == len(raw)
    row = clean[(clean.State == "A") & (clean.District == "Same") & (clean.Year_start == 2010)].iloc[0]
    assert row.Area == 30
    assert row.Production == 70
    assert row.Yield == pytest.approx(70 / 30)
    shuffled = structural_clean(duplicate_input.sample(frac=1, random_state=8))[0]
    pd.testing.assert_frame_equal(clean, shuffled)
    assert not clean.duplicated(KEY).any()


def test_invalid_irrigation_and_soil_remain_missing_until_fold_imputation():
    raw = raw_frame()
    raw.loc[raw.Year_start == 2011, "Nitrogen_index"] = np.nan
    raw.loc[raw.Year_start == 2011, "irrigation_intensity"] = 200
    clean, _, _ = structural_clean(raw)
    assert clean.loc[clean.Year_start == 2011, "Nitrogen_index"].isna().all()
    assert clean.loc[clean.Year_start == 2011, "irrigation_intensity"].isna().all()


def test_baseline_does_not_read_model_lag_features():
    data = build_ex_ante_features(structural_clean(raw_frame())[0])
    expected = generate_baseline(data).Baseline_Yield
    data["Yield_lag3_mean"] = 1e12
    pd.testing.assert_series_equal(expected, generate_baseline(data).Baseline_Yield)


def test_hierarchical_fallback_uses_only_prior_same_crop_season():
    raw = raw_frame()
    first = raw[(raw.State == "A") & (raw.District == "Same") & (raw.Year_start == 2017)].copy()
    first["District"] = "New district"
    data = prepared(pd.concat([raw, first], ignore_index=True))
    new = data[data.District.eq("New district")].iloc[0]
    assert new.Baseline_Level == "state"
    assert new.Baseline_Yield == pytest.approx(np.mean([5, 6, 7]) * 5.5)
    assert not new.Feature_Supported  # Hierarchical baseline doesn't justify local model advice.


def test_prior_economics_has_no_target_year_price_cpi_or_realized_yield_dependency():
    frame = prepared(raw_frame())
    registry = pd.DataFrame({"Crop": ["Ragi"] * 10, "Year": range(2010, 2020), "Nominal_MSP": np.arange(10) * 100 + 1200.})
    cpi = pd.DataFrame({"Year": range(2010, 2020), "Deflator_Index": np.arange(10) + 100.})
    base = attach_prior_economics(frame, registry, cpi)
    perturbed = frame.copy()
    perturbed.loc[perturbed.Year_start >= 2017, "Yield"] = 1e12
    registry.loc[registry.Year >= 2017, "Nominal_MSP"] = 1e12
    cpi.loc[cpi.Year >= 2017, "Deflator_Index"] = 1e12
    other = attach_prior_economics(perturbed, registry, cpi)
    cols = ["Price_Reference_per_Quintal", "Cost_Proxy_per_Hectare", "Price_Reference_Year", "CPI_Reference_Year"]
    pd.testing.assert_frame_equal(base.loc[base.Year_start <= 2017, cols], other.loc[other.Year_start <= 2017, cols])
    assert (base.Price_Reference_Year.dropna() < base.loc[base.Price_Reference_Year.notna(), "Year_start"]).all()
    assert (base.CPI_Reference_Year.dropna() < base.loc[base.CPI_Reference_Year.notna(), "Year_start"]).all()
    row = base[(base.State == "A") & (base.District == "Same") & (base.Year_start == 2017)].iloc[0]
    assert row.Price_Reference_per_Quintal == pytest.approx(1800 / 106 * 100)
    assert row.Cost_Proxy_per_Hectare == pytest.approx(10 * 6 * 1800 / 106 * 100 / 1.5)


def test_duplicate_feature_keys_are_rejected_instead_of_exploding_join():
    clean = structural_clean(raw_frame())[0]
    with pytest.raises(ValueError, match="duplicate"):
        build_ex_ante_features(pd.concat([clean, clean.iloc[[0]]]))
