"""Read-only hand reconciliation of M5/M7 units and heterogeneous supply."""
import json
from pathlib import Path
from modules.m4_price.market_simulator import PriceSimulator
from modules.m6_market.supply_ledger import DistrictSupplyLedger

sim = PriceSimulator()
ctx = {"Tomato": {"msp_real": 1500.0, "q_lag3": 10000.0, "yield_hat": 20.0}}
ledger = DistrictSupplyLedger("probe_only", 1000.0, ctx, sim)
farmers = [
    {"id": "f1", "area": 200.0, "q50": 20.0},
    {"id": "f2", "area": 200.0, "q50": 40.0},
]
for farmer in farmers:
    ledger.commit(farmer["id"], "Tomato", farmer["area"])
weighted_quantity = sum(farmer["area"] * farmer["q50"] for farmer in farmers)
ledger_quantity = sum(farmer["area"] for farmer in farmers) * ctx["Tomato"]["yield_hat"]
price_ledger = ledger.project_price("Tomato", 0.0)
price_weighted = sim.project_price("Tomato", 1500.0, weighted_quantity, 10000.0)
out = {
    "scope": "Hand-reconciled synthetic example, not actual production or market observations",
    "heterogeneous_supply": {
        "area_ha": ledger.committed_area["Tomato"],
        "threshold_ha": ledger.glut_thresholds["Tomato"],
        "ledger_quantity_tonnes": ledger_quantity,
        "farmer_forecast_weighted_quantity_tonnes": weighted_quantity,
        "ledger_price_per_quintal": price_ledger,
        "consistent_quantity_price_per_quintal": price_weighted,
        "threshold_reference_price_per_quintal": 1350.0,
    },
    "monetary_units": {
        "price_per_quintal": 1500.0, "yield_tonnes_per_ha": 20.0, "area_ha": 1.0,
        "m7_evaluator_formula_revenue": 1500.0 * 20.0 * 1.0,
        "consistent_revenue_rupees": 1500.0 * 20.0 * 10.0 * 1.0,
        "interpretation": "A common missing factor may cancel in revenue ratios, but not when subtracting hectare costs.",
    },
}
Path(__file__).with_suffix(".json").write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps(out, indent=2))

