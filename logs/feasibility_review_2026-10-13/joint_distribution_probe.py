"""Mathematical joint-distribution counterexample; no training or field data."""
import json
from pathlib import Path
import numpy as np

y = np.array([1.0, 2.0, 4.0])  # tonnes/ha
p = np.array([1.0, 2.0, 4.0])  # rupees/quintal, abstract example
same = y * 10.0 * p
opposite = y * 10.0 * p[::-1]
out = {
    "scope": "Hand-enumerated constructed samples, not empirical price/yield dependence",
    "shared_yield_marginals": y.tolist(),
    "shared_price_marginals": p.tolist(),
    "median_product_revenue_both": float(np.median(y) * 10.0 * np.median(p)),
    "same_order_revenues": same.tolist(),
    "opposite_order_revenues": opposite.tolist(),
    "same_order_mean_revenue": float(np.mean(same)),
    "opposite_order_mean_revenue": float(np.mean(opposite)),
    "constant_crop_comparison_revenue": 50.0,
    "interpretation": "Identical marginal forecasts do not determine expected revenue or its distribution; numerical M5 output cannot distinguish these constructed scenarios.",
}
Path(__file__).with_suffix(".json").write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps(out, indent=2))

