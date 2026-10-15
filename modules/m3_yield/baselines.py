"""Independent hierarchical baseline using only the prior three calendar years."""
from __future__ import annotations

import numpy as np
import pandas as pd
from modules.regional_data.data import KEY


def generate_baseline(df: pd.DataFrame) -> pd.DataFrame:
    """Compute local -> state -> crop-season means from Yield, not model features.

    No-history rows remain unavailable. State is part of every district key.
    """
    if df.duplicated(KEY).any():
        raise ValueError("Resolve duplicate keys before calculating baseline")
    result = df.copy()
    for level, groups in enumerate([KEY[:-1], ["State", "Crop", "Season"], ["Crop", "Season"]]):
        keys = groups + ["Year_start"]
        annual = df.groupby(keys, observed=True, sort=True)["Yield"].mean().reset_index()
        # Deliberately independent implementation from feature calendar_lags.
        history = []
        for offset in (1, 2, 3):
            shifted = annual.rename(columns={"Yield": f"past_{offset}"}).copy()
            shifted["Year_start"] += offset
            history.append(annual[keys].merge(shifted, on=keys, how="left", validate="one_to_one")[f"past_{offset}"])
        annual[f"Baseline_L{level}"] = pd.concat(history, axis=1).mean(axis=1)
        result = result.merge(annual[keys + [f"Baseline_L{level}"]], on=keys, how="left", validate="many_to_one", sort=False)
    result["Baseline_Yield"] = result["Baseline_L0"].combine_first(result["Baseline_L1"]).combine_first(result["Baseline_L2"])
    result["Baseline_Supported"] = result["Baseline_Yield"].notna()
    result["Baseline_Level"] = np.select([result.Baseline_L0.notna(), result.Baseline_L1.notna(), result.Baseline_L2.notna()], ["district", "state", "crop_season"], default="unsupported")
    return result
