"""Cutoff-safe ex-ante features with an actual three-calendar-year window."""
from __future__ import annotations

import numpy as np
import pandas as pd
from modules.regional_data.data import CONTEXT_COLUMNS, KEY


def calendar_lags(frame: pd.DataFrame, groups: list[str], columns: list[str], prefix: str = "") -> pd.DataFrame:
    """Return prior 1..3 calendar-year mean/std/count; never cross groups.

    Input is unique by groups + year. Calendar joins deliberately leave gaps for
    absent years instead of admitting older observations via a three-row roll.
    """
    key = groups + ["Year_start"]
    if frame.duplicated(key).any():
        raise ValueError(f"calendar_lags requires unique keys: {key}")
    out = frame[key].copy()
    values = {c: [] for c in columns}
    for distance in (1, 2, 3):
        prior = frame[key + columns].copy()
        prior["Year_start"] += distance
        merged = frame[key].merge(prior, how="left", on=key, validate="one_to_one", sort=False)
        for col in columns:
            values[col].append(pd.to_numeric(merged[col], errors="coerce").to_numpy(dtype=float))
    for col, arrays in values.items():
        matrix = np.column_stack(arrays)
        count = np.isfinite(matrix).sum(axis=1)
        total = np.nansum(matrix, axis=1)
        mean = np.divide(total, count, out=np.full(len(out), np.nan), where=count > 0)
        out[f"{prefix}{col}_lag3_mean"] = mean
        out[f"{prefix}{col}_lag3_count"] = count
        if col == "Yield":
            centered = np.where(np.isfinite(matrix), matrix - mean[:, None], 0)
            var = np.divide((centered ** 2).sum(axis=1), count - 1,
                            out=np.full(len(out), np.nan), where=count > 1)
            var[count == 1] = 0  # A single historical observation has zero observed variation.
            out[f"{prefix}{col}_lag3_std"] = np.sqrt(var)
    return out


def build_ex_ante_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build historical lags without filling from later years or current labels.

    Call structural_clean first for raw records. Missing numeric model features
    are imputed later from proper-training rows only, with explicit missing flags.
    """
    if df.duplicated(KEY).any():
        raise ValueError("Resolve duplicate State/District/Crop/Season/year keys before features")
    frame = df.copy().sort_values(KEY).reset_index(drop=True)
    for col in CONTEXT_COLUMNS:
        if col not in frame:
            frame[col] = np.nan
    lagged = calendar_lags(frame, KEY[:-1], ["Yield"] + CONTEXT_COLUMNS)
    result = frame.merge(lagged, on=KEY, how="left", validate="one_to_one", sort=False)
    district = frame.groupby(["State", "District", "Year_start"], observed=True)[CONTEXT_COLUMNS].median().reset_index()
    district_lags = calendar_lags(district, ["State", "District"], CONTEXT_COLUMNS, prefix="dist_")
    result = result.merge(district_lags, on=["State", "District", "Year_start"], how="left", validate="many_to_one", sort=False)
    result["Feature_Supported"] = result["Yield_lag3_count"].ge(1)
    return result
