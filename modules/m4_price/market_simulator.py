"""
Module 4: Market Price Simulator
Synthesizes a realistic `Real_Market_Price_per_Quintal` to enable downside risk tracking,
using an economic elasticity model around the MSP based on yield shocks.
"""

import pandas as pd
import numpy as np

def synthesize_market_prices(df: pd.DataFrame, random_seed: int = 42) -> pd.DataFrame:
    """
    Simulates real market prices based on yield shocks.
    Market Price = Real MSP * (1.0 - Elasticity * Yield Shock) * (1.0 + Noise)
    """
    np.random.seed(random_seed)
    df = df.copy()
    
    # Calculate Yield Shock
    # If Yield_lag3_mean is missing or 0, shock is 0
    lag_yield = df.get('Yield_lag3_mean', pd.Series([np.nan]*len(df)))
    
    # We must ensure Yield_lag3_mean exists. If it doesn't, we should compute it or handle it.
    # In the main script we will call M3's feature builder first if needed.
    
    # To be safe, let's calculate a simple lag if not present
    if lag_yield.isna().all():
        # Quick computation
        df = df.sort_values(by=['District', 'Crop', 'Season', 'Year_start'])
        lag_yield = df.groupby(['District', 'Crop', 'Season'])['Yield'].shift(1).rolling(3, min_periods=1).mean()
        
    lag_yield = lag_yield.replace(0, np.nan)
    yield_shock = (df['Yield'] - lag_yield) / lag_yield
    yield_shock = yield_shock.fillna(0.0)
    
    # Economic Elasticity (e.g., 0.2 means 10% increase in yield -> 2% drop in price)
    elasticity = 0.20
    
    # Base Price Anchor is Real MSP
    anchor_price = df['Real_MSP_per_Quintal']
    
    # Add random volatility (std dev = 0.05 => 5% random shock)
    noise = np.random.normal(0, 0.05, size=len(df))
    
    # Simulated Market Price
    sim_price = anchor_price * (1.0 - elasticity * yield_shock) * (1.0 + noise)
    
    # Ensure it doesn't go below 0 or crazy high (clip to 0.1x to 5.0x of MSP)
    sim_price = np.clip(sim_price, anchor_price * 0.1, anchor_price * 5.0)
    
    df['Real_Market_Price_per_Quintal'] = sim_price
    
    return df
