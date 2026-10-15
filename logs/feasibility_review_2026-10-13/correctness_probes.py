"""Isolated feasibility probes. Run from repository root:
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python logs/feasibility_review_2026-10-13/correctness_probes.py
Does not modify production datasets or ledger events.
"""
import json
import platform
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import pandas as pd
from modules.m4_price.market_simulator import PriceSimulator
from modules.m6_market.supply_ledger import DistrictSupplyLedger
from modules.m7_allocator.online_allocator import OnlineAllocator
from modules.m3_yield.features import build_ex_ante_features
from modules.m8_edge.aggregator import DPAggregator

ctx = {
    "Tomato": {"msp_real": 1500.0, "q_lag3": 10000.0, "yield_hat": 20.0},
    "Onion": {"msp_real": 1200.0, "q_lag3": 12000.0, "yield_hat": 18.0},
}
sim = PriceSimulator()
ledger = DistrictSupplyLedger("probe_only", 1000.0, ctx, sim)
threshold = ledger.glut_thresholds["Tomato"]
ledger.commit("one", "Tomato", 600.0)
direct = {
    "threshold_ha": threshold,
    "committed_ha": ledger.committed_area["Tomato"],
    "headroom_ha": ledger.headroom("Tomato"),
    "price_ratio_to_reference": ledger.project_price("Tomato", 0.0) / 1500.0,
}
negative = DistrictSupplyLedger("probe_only", 1000.0, ctx, sim)
negative.commit("negative", "Tomato", -5.0)
neg = {"accepted_negative_area": negative.committed_area["Tomato"]}
race = DistrictSupplyLedger("probe_only", 1000.0, ctx, sim)
alloc = OnlineAllocator(race)
barrier = Barrier(2)

def worker(i):
    yields = {"Tomato": 20.0, "Onion": 18.0}
    rec = alloc.recommend(str(i), 300.0, yields, yields)
    crop = rec[0]["crop"]
    barrier.wait()
    race.commit(str(i), crop, 300.0)
    return crop

with ThreadPoolExecutor(max_workers=2) as pool:
    choices = list(pool.map(worker, range(2)))
quoted = {
    "choices": choices,
    "committed_ha": race.committed_area,
    "threshold_ha": race.glut_thresholds,
}
climate = [
    "Rainfall_mm", "Rainy_Days", "Mean_Daily_Rainfall_mm", "Max_Daily_Rainfall_mm",
    "irrigation_intensity", "canal_share", "Nitrogen_index", "Phosphorus_index",
    "Potassium_index", "Organic_Carbon_index", "pct_acidic", "pct_alkaline", "pct_saline",
]
rows = []
for dist, values in [("A", [1.0, 2.0, 3.0]), ("B", [100.0, 200.0, 300.0])]:
    for year, value in zip([2000, 2001, 2002], values):
        row = {
            "State": "S", "District": dist, "Crop": "C", "Season": "K",
            "Year_start": year, "Yield": value,
        }
        row.update({col: 1.0 for col in climate})
        rows.append(row)
features = build_ex_ante_features(pd.DataFrame(rows))
lag = features.loc[
    features.District.eq("B"), ["Year_start", "Yield_lag3_mean"]
].to_dict("records")
future_input = pd.DataFrame([row for row in rows if row["District"] == "A"])
f1 = build_ex_ante_features(future_input)
future_input.loc[future_input.Year_start.eq(2001), "Yield"] = 200.0
f2 = build_ex_ante_features(future_input)
future = {
    "earliest_year_lag_before": float(f1.iloc[0].Yield_lag3_mean),
    "earliest_year_lag_after_future_change": float(f2.iloc[0].Yield_lag3_mean),
}
dp = DPAggregator()
a = dp.aggregate_commitments([{"crop": "Tomato", "area": 100.0}])
b = dp.aggregate_commitments([{"crop": "Tomato", "area": 101.0}])
privacy = {"released_difference_for_one_ha_change": b["Tomato"] - a["Tomato"]}
out = {
    "scope": "Isolated in-memory correctness probes; no saved dataset or event log modified",
    "environment": {"python": platform.python_version(), "platform": platform.platform()},
    "direct_crop_threshold_bypass": direct,
    "negative_area": neg,
    "stale_recommendation_then_commit": quoted,
    "group_boundary_lags": lag,
    "future_value_affects_past_fallback": future,
    "repeat_seed_privacy": privacy,
}
Path(__file__).with_suffix(".json").write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps(out, indent=2))

