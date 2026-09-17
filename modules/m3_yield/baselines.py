"""
Module 3: Hierarchical Trailing 3-Year Mean Baseline
"""

import pandas as pd
import numpy as np

def generate_baseline(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generates the hierarchical trailing 3-year mean baseline yield.
    Level 0: (District, Crop, Season)
    Level 1: (State, Crop, Season)
    Level 2: (Crop, Season)
    """
    # df must already have 'Yield_lag3_mean' calculated from features.py, 
    # but let's re-calculate it rigorously hierarchically for the baseline specifically.
    
    df = df.copy()
    
    # L0: District, Crop, Season
    df_l0 = df.groupby(['District', 'Crop', 'Season', 'Year_start'])['Yield'].mean().reset_index()
    df_l0 = df_l0.sort_values(by=['District', 'Crop', 'Season', 'Year_start'])
    df_l0['Baseline_L0'] = df_l0.groupby(['District', 'Crop', 'Season'])['Yield'].shift(1).rolling(window=3, min_periods=1).mean()
    
    # L1: State, Crop, Season
    df_l1 = df.groupby(['State', 'Crop', 'Season', 'Year_start'])['Yield'].mean().reset_index()
    df_l1 = df_l1.sort_values(by=['State', 'Crop', 'Season', 'Year_start'])
    df_l1['Baseline_L1'] = df_l1.groupby(['State', 'Crop', 'Season'])['Yield'].shift(1).rolling(window=3, min_periods=1).mean()
    
    # L2: Crop, Season
    df_l2 = df.groupby(['Crop', 'Season', 'Year_start'])['Yield'].mean().reset_index()
    df_l2 = df_l2.sort_values(by=['Crop', 'Season', 'Year_start'])
    df_l2['Baseline_L2'] = df_l2.groupby(['Crop', 'Season'])['Yield'].shift(1).rolling(window=3, min_periods=1).mean()
    
    # Merge back
    df = df.merge(df_l0[['District', 'Crop', 'Season', 'Year_start', 'Baseline_L0']], 
                  on=['District', 'Crop', 'Season', 'Year_start'], how='left')
    df = df.merge(df_l1[['State', 'Crop', 'Season', 'Year_start', 'Baseline_L1']], 
                  on=['State', 'Crop', 'Season', 'Year_start'], how='left')
    df = df.merge(df_l2[['Crop', 'Season', 'Year_start', 'Baseline_L2']], 
                  on=['Crop', 'Season', 'Year_start'], how='left')
                  
    # Hierarchical fallback
    df['Baseline_Yield'] = df['Baseline_L0']
    df['Baseline_Yield'] = df['Baseline_Yield'].fillna(df['Baseline_L1'])
    df['Baseline_Yield'] = df['Baseline_Yield'].fillna(df['Baseline_L2'])
    
    # Final fallback if still NA
    overall_mean = df['Yield'].mean()
    df['Baseline_Yield'] = df['Baseline_Yield'].fillna(overall_mean)
    
    return df
