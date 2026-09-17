"""
Module 4: Structural Price Propagator
Replaces the ML quantile regressor with a deterministic structural economic model.
It propagates yield uncertainty into price uncertainty via elasticity.
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path

def run_price_ensemble():
    base_dir = Path('/Users/manishharigovind/Desktop/VIT Vellore/5th semester/Data science proogramming/DSP_project')
    
    print("Loading yield predictions and economic data...")
    # Load the OOF yield predictions which contain q10, q50, q90 and true Yield
    df = pd.read_parquet(base_dir / 'data/processed/fact_yield_predictions_oof.parquet')
    
    # Sort for lag computation
    df = df.sort_values(by=['District', 'Crop', 'Season', 'Year_start'])
    
    # 1. Structural Parameters
    elasticity = 0.20  # A 10% increase in yield results in a 2% drop in price
    
    # 2. Compute Yield Baseline (lag 3 mean) for shocks
    df['Yield_lag3_mean'] = df.groupby(['District', 'Crop', 'Season'])['Yield'].shift(1).rolling(3, min_periods=1).mean()
    # Fallback to state means if needed
    state_means = df.groupby(['State', 'Crop', 'Season'])['Yield'].transform(lambda x: x.shift(1).mean())
    df['Yield_lag3_mean'] = df['Yield_lag3_mean'].fillna(state_means)
    df['Yield_lag3_mean'] = df['Yield_lag3_mean'].fillna(df['Yield'].mean())
    
    # 3. Propagate Uncertainty
    anchor_price = df['Real_MSP_per_Quintal']
    lag_yield = df['Yield_lag3_mean']
    
    # p50 corresponds to q50 shock
    shock_q50 = (df['q50'] - lag_yield) / lag_yield
    df['p50'] = anchor_price * (1.0 - elasticity * shock_q50.fillna(0))
    
    # High yield (q90) -> Low price (p10)
    shock_q90 = (df['q90'] - lag_yield) / lag_yield
    df['p10'] = anchor_price * (1.0 - elasticity * shock_q90.fillna(0))
    
    # Low yield (q10) -> High price (p90)
    shock_q10 = (df['q10'] - lag_yield) / lag_yield
    df['p90'] = anchor_price * (1.0 - elasticity * shock_q10.fillna(0))
    
    # 4. Synthesize the "Real_Market_Price_per_Quintal" for downstream metrics
    # using the actual realized Yield shock, so we can evaluate downstream M5 profit
    actual_shock = (df['Yield'] - lag_yield) / lag_yield
    noise = np.random.normal(0, 0.05, size=len(df)) # 5% structural noise
    df['Real_Market_Price_per_Quintal'] = anchor_price * (1.0 - elasticity * actual_shock.fillna(0)) * (1.0 + noise)
    
    # Defensive Clipping
    df['p10'] = np.clip(df['p10'], anchor_price * 0.1, anchor_price * 5.0)
    df['p50'] = np.clip(df['p50'], anchor_price * 0.1, anchor_price * 5.0)
    df['p90'] = np.clip(df['p90'], anchor_price * 0.1, anchor_price * 5.0)
    df['Real_Market_Price_per_Quintal'] = np.clip(df['Real_Market_Price_per_Quintal'], anchor_price * 0.1, anchor_price * 5.0)
    
    # Sort bounds to guarantee p10 <= p50 <= p90
    price_bounds = np.vstack([df['p10'], df['p50'], df['p90']]).T
    price_bounds.sort(axis=1)
    df['p10'] = price_bounds[:, 0]
    df['p50'] = price_bounds[:, 1]
    df['p90'] = price_bounds[:, 2]
    
    out_dir = base_dir / 'data/processed'
    df.to_parquet(out_dir / 'fact_price_predictions_oof.parquet')
    
    # 5. Documentation and Manifest
    results = {
        'Structural_Assumptions': {
            'Elasticity': elasticity,
            'Noise_Std': 0.05,
            'Price_Anchor': 'Real_MSP_per_Quintal'
        }
    }
    
    with open(out_dir / 'm4_price_evaluation_manifest.json', 'w') as f:
        json.dump(results, f, indent=4)
        
    report = ["# Module 4 Structural Price Simulation Report\n"]
    report.append("> **Methodological Note:** Due to the absence of historical mandi transaction data, market prices are modeled structurally rather than empirically forecasted. The model propagates yield shocks via an assumed price elasticity.\n")
    report.append("## Structural Assumptions")
    report.append(f"- **Price Anchor:** Government Minimum Support Price (Real MSP)")
    report.append(f"- **Yield-Price Elasticity:** $\epsilon = {elasticity}$ (A 10% yield surplus causes a 2% price drop)")
    report.append(f"- **Uncertainty Propagation:** $P_{{bound}} = MSP \\times (1 - \epsilon \\times Yield\\_Shock_{{bound}})$")
    report.append("\n*Note: Pinball loss and empirical coverage metrics are intentionally omitted as the price target is a structural simulation, not an observed ground truth.*")
    
    with open(out_dir / 'm4_price_report.md', 'w') as f:
        f.write('\n'.join(report))
        
    print("Done. Saved structural prices, manifest, and report.")

if __name__ == "__main__":
    run_price_ensemble()
