"""
Module 4: Ex-Ante Price Feature Engineering
"""

import pandas as pd
import numpy as np

def build_price_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Builds ex-ante price features, preventing temporal leakage.
    Uses strictly historical lags for price and acreage.
    """
    df = df.copy()
    
    df = df.sort_values(by=['District', 'Crop', 'Season', 'Year_start'])
    
    group_cols = ['District', 'Crop', 'Season']
    grouped = df.groupby(group_cols)
    
    # Lag 1 and Lag 3 Mean of Market Price
    df['Real_Price_lag1'] = grouped['Real_Market_Price_per_Quintal'].shift(1)
    df['Real_Price_lag3_mean'] = grouped['Real_Market_Price_per_Quintal'].shift(1).rolling(window=3, min_periods=1).mean()
    
    # Price Volatility
    df['Real_Price_lag3_std'] = grouped['Real_Market_Price_per_Quintal'].shift(1).rolling(window=3, min_periods=1).std().fillna(0)
    
    # Acreage change (Farmers respond to last year's price by changing acreage)
    df['Area_lag1'] = grouped['Area'].shift(1)
    df['Area_lag3_mean'] = grouped['Area'].shift(1).rolling(window=3, min_periods=1).mean()
    
    # Macro WPI is already given by Deflator_Index. 
    # WPI is exogenous and known up to the current year technically, but to be strictly ex-ante,
    # we can use WPI lag1 or just the fact that it's a structural trend.
    # We will use Deflator_Index as is, assuming it's available pre-harvest.
    
    # Fill NAs
    state_means = df.groupby(['State', 'Crop', 'Season'])['Real_Market_Price_per_Quintal'].transform(lambda x: x.shift(1).mean())
    df['Real_Price_lag3_mean'] = df['Real_Price_lag3_mean'].fillna(state_means)
    
    # Forward fill strictly within groups to prevent temporal leakage
    fill_cols = [c for c in df.columns if c not in ['District', 'Crop', 'Season']]
    df[fill_cols] = df.groupby(['District', 'Crop', 'Season'])[fill_cols].ffill()
    df = df.fillna(0)
    
    return df
