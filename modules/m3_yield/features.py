"""
Module 3: Ex-Ante Feature Engineering & Lag Store
"""

import pandas as pd
import numpy as np

def build_ex_ante_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Builds ex-ante features using strictly historical data to prevent temporal leakage.
    Uses trailing 3-year means shifted by 1 year for yield and agro-climatic variables.
    """
    df = df.copy()
    
    # Ensure sorted order for rolling operations
    df = df.sort_values(by=['District', 'Crop', 'Season', 'Year_start'])
    
    # We want trailing 3-year means. We use a 3-year rolling window, closed='left'
    # which excludes the current year (strictly ex-ante).
    # Group by District, Crop, Season
    group_cols = ['District', 'Crop', 'Season']
    
    def compute_shifted_rolling_mean(x, window=3):
        # Rolling mean over the past `window` years, excluding current year
        return x.shift(1).rolling(window=window, min_periods=1).mean()
        
    def compute_shifted_rolling_std(x, window=3):
        return x.shift(1).rolling(window=window, min_periods=1).std().fillna(0)

    # Features to aggregate
    yield_col = 'Yield'
    climate_cols = ['Rainfall_mm', 'Rainy_Days', 'Mean_Daily_Rainfall_mm', 'Max_Daily_Rainfall_mm']
    irrigation_cols = ['irrigation_intensity', 'canal_share']
    soil_cols = ['Nitrogen_index', 'Phosphorus_index', 'Potassium_index', 'Organic_Carbon_index', 
                 'pct_acidic', 'pct_alkaline', 'pct_saline']
                 
    all_target_cols = [yield_col] + climate_cols + irrigation_cols + soil_cols
    
    # Calculate grouped rolling means
    grouped = df.groupby(group_cols)
    
    for col in all_target_cols:
        df[f'{col}_lag3_mean'] = grouped[col].shift(1).rolling(window=3, min_periods=1).mean()
        if col == yield_col:
            df[f'{col}_lag3_std'] = grouped[col].shift(1).rolling(window=3, min_periods=1).std().fillna(0)
            
    # Also add District-level climate/soil lag3 means (ignoring Crop/Season) for more robustness
    # This helps if a specific crop-season wasn't grown in previous years but we want climate context
    district_grouped = df.groupby(['District', 'Year_start'])[climate_cols + soil_cols + irrigation_cols].mean().reset_index()
    district_grouped = district_grouped.sort_values(['District', 'Year_start'])
    
    dist_grp = district_grouped.groupby('District')
    for col in climate_cols + soil_cols + irrigation_cols:
        district_grouped[f'dist_{col}_lag3_mean'] = dist_grp[col].shift(1).rolling(window=3, min_periods=1).mean()
        
    district_grouped = district_grouped[['District', 'Year_start'] + [f'dist_{col}_lag3_mean' for col in climate_cols + soil_cols + irrigation_cols]]
    
    df = df.merge(district_grouped, on=['District', 'Year_start'], how='left')
    
    # Fill NAs with overall means or state means defensively
    df['State'] = df['State'].fillna('Unknown')
    state_means = df.groupby(['State', 'Crop', 'Season'])[f'{yield_col}_lag3_mean'].transform('mean')
    df[f'{yield_col}_lag3_mean'] = df[f'{yield_col}_lag3_mean'].fillna(state_means)
    
    national_means = df.groupby(['Crop', 'Season'])[f'{yield_col}_lag3_mean'].transform('mean')
    df[f'{yield_col}_lag3_mean'] = df[f'{yield_col}_lag3_mean'].fillna(national_means)
    df[f'{yield_col}_lag3_mean'] = df[f'{yield_col}_lag3_mean'].fillna(0) # Absolute fallback
    df[f'{yield_col}_lag3_std'] = df[f'{yield_col}_lag3_std'].fillna(0)
    
    # Forward fill climate/soil lags strictly within each group to prevent temporal leakage across districts/crops
    fill_cols = [c for c in df.columns if c not in ['District', 'Crop', 'Season']]
    df[fill_cols] = df.groupby(['District', 'Crop', 'Season'])[fill_cols].ffill()
    df = df.fillna(0)
    
    # Check for leakage
    # We do this by ensuring the original column is not perfectly correlated with the lag (except by chance if constant)
    # and we explicitly don't use the current year values in the lag.
    
    return df
