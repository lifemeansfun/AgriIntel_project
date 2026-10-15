"""Structural cleaning only: never estimate statistics across historical cutoffs.

The input's production convention is project-declared tonnes. The original
publication vintages are unavailable; this is an arithmetic historical simulation,
not a vintage-correct evaluation of what a farmer actually knew at sowing time.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

KEY = ["State", "District", "Crop", "Season", "Year_start"]
CONTEXT_COLUMNS = [
    "Rainfall_mm", "Rainy_Days", "Mean_Daily_Rainfall_mm", "Max_Daily_Rainfall_mm",
    "irrigation_intensity", "canal_share", "Nitrogen_index", "Phosphorus_index",
    "Potassium_index", "Organic_Carbon_index", "pct_acidic", "pct_alkaline", "pct_saline",
]


def structural_clean(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Resolve keys/units using each record only; preserve missing covariates.

    Same-key Area and Production are summed after exact deduplication. Context
    duplicates are reduced by median within the same key/year. Invalid irrigation
    is marked missing rather than repaired with a future district median.
    """
    required = set(KEY + ["Area", "Production"])
    if not required.issubset(raw.columns):
        raise ValueError(f"Missing raw columns: {sorted(required - set(raw.columns))}")
    df = raw.copy().drop_duplicates()
    exact = len(raw) - len(df)
    for col in KEY[:-1]:
        df[col] = df[col].astype("string").str.strip()
    for col in ["Year_start", "Area", "Production"] + CONTEXT_COLUMNS:
        if col not in df:
            df[col] = np.nan
        df[col] = pd.to_numeric(df[col], errors="coerce").replace([np.inf, -np.inf], np.nan)
    invalid = (df[KEY[:-1]].isna().any(axis=1) | df[KEY[:-1]].eq("").any(axis=1)
               | df["Year_start"].isna() | df["Year_start"].mod(1).ne(0)
               | df["Area"].isna() | df["Production"].isna()
               | df["Area"].le(0) | df["Production"].lt(0))
    quarantined = df[invalid].copy()
    quarantined["Quarantine_Reason"] = "INVALID_KEY_YEAR_AREA_OR_PRODUCTION"
    df = df[~invalid].copy()
    df["Year_start"] = df["Year_start"].astype(int)
    # No inference about missing weather/soil is needed to structurally retain a row.
    collision_keys = int(df.loc[df.duplicated(KEY, keep=False), KEY].drop_duplicates().shape[0])
    aggregation = {"Area": "sum", "Production": "sum", **{c: "median" for c in CONTEXT_COLUMNS}}
    df = df.groupby(KEY, dropna=False, observed=True, sort=True).agg(aggregation).reset_index()
    df["Yield"] = df["Production"] / df["Area"]
    bad_irrigation = df["irrigation_intensity"].notna() & ~df["irrigation_intensity"].between(0, 2.5)
    df["irrigation_invalid"] = bad_irrigation
    df.loc[bad_irrigation, "irrigation_intensity"] = np.nan
    bad_canal = df["canal_share"].notna() & ~df["canal_share"].between(0, 1)
    df.loc[bad_canal, "canal_share"] = np.nan
    # Binary failure is a target-side descriptor and never a model feature.
    df["crop_failure_flag"] = df["Production"].eq(0)
    if df.duplicated(KEY).any() or not np.isfinite(df["Yield"]).all():
        raise AssertionError("Structural cleaning failed key/yield validation")
    audit = {
        "raw_rows": len(raw), "exact_duplicates_removed": exact,
        "collision_keys_aggregated": collision_keys, "quarantined_rows": len(quarantined),
        "structural_rows": len(df), "irrigation_rows_marked_missing": int(bad_irrigation.sum()),
        "statistical_imputation": "none; per-fold historical training medians applied to lag features only",
        "context_collision_rule": "same-key same-year median; Area/Production sum after exact deduplication",
        "yield_unit_contract": "project-declared tonnes/hectare; original source unit/vintage unverified",
    }
    return df, quarantined, audit


def attach_prior_economics(df: pd.DataFrame, registry: pd.DataFrame, cpi: pd.DataFrame) -> pd.DataFrame:
    """Use latest strictly prior-year registry/CPI observations, never target yield.

    The registry is generated category-price proxies, not observed MSP/market prices.
    This data has calendar year labels, not verified release timestamps.
    """
    reg = registry[["Crop", "Year", "Nominal_MSP"]].copy()
    inf = cpi[["Year", "Deflator_Index"]].copy()
    if reg.duplicated(["Crop", "Year"]).any() or inf.duplicated("Year").any():
        raise ValueError("Economic registries must have unique keys")
    for frame, cols in [(reg, ["Year", "Nominal_MSP"]), (inf, ["Year", "Deflator_Index"])]:
        for col in cols:
            frame[col] = pd.to_numeric(frame[col], errors="raise")
        if not np.isfinite(frame[cols].to_numpy()).all():
            raise ValueError("Nonfinite economic inputs")
    if (reg.Nominal_MSP <= 0).any() or (inf.Deflator_Index <= 0).any():
        raise ValueError("Economic reference prices and CPI must be positive")
    result = df.copy()
    result["Price_Reference_per_Quintal"] = np.nan
    result["Price_Reference_Year"] = np.nan
    result["CPI_Reference_Year"] = np.nan
    for year in sorted(result.Year_start.unique()):
        available_prices = reg[reg.Year < year].sort_values("Year").drop_duplicates("Crop", keep="last").set_index("Crop")
        available_cpi = inf[inf.Year < year].sort_values("Year")
        if available_cpi.empty:
            continue
        last_cpi = available_cpi.iloc[-1]
        mask = result.Year_start.eq(year)
        result.loc[mask, "Price_Reference_per_Quintal"] = result.loc[mask, "Crop"].map(available_prices.Nominal_MSP).to_numpy() / last_cpi.Deflator_Index * 100
        result.loc[mask, "Price_Reference_Year"] = result.loc[mask, "Crop"].map(available_prices.Year).to_numpy()
        result.loc[mask, "CPI_Reference_Year"] = last_cpi.Year
    result["Cost_Proxy_per_Hectare"] = 10 * result["Yield_lag3_mean"] * result["Price_Reference_per_Quintal"] / 1.5
    result["Economics_Basis"] = "generated_price_and_cost_proxies_2011_INR"
    return result
