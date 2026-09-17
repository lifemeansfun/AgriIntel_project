"""
Module 4: Naive Seasonal Trailing Mean Baseline for Price
"""

import pandas as pd
import numpy as np

def generate_baseline(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generates the hierarchical trailing 3-year mean baseline real price.
    Level 0: (District, Crop, Season)
    Level 1: (State, Crop, Season)
    Level 2: (Crop, Season)
    """
    df = df.copy()
    
    # L0
    df_l0 = df.groupby(['District', 'Crop', 'Season', 'Year_start'])['Real_Market_Price_per_Quintal'].mean().reset_index()
    df_l0 = df_l0.sort_values(by=['District', 'Crop', 'Season', 'Year_start'])
    df_l0['Baseline_L0'] = df_l0.groupby(['District', 'Crop', 'Season'])['Real_Market_Price_per_Quintal'].shift(1).rolling(3, min_periods=1).mean()
    
    # L1
    df_l1 = df.groupby(['State', 'Crop', 'Season', 'Year_start'])['Real_Market_Price_per_Quintal'].mean().reset_index()
    df_l1 = df_l1.sort_values(by=['State', 'Crop', 'Season', 'Year_start'])
    df_l1['Baseline_L1'] = df_l1.groupby(['State', 'Crop', 'Season'])['Real_Market_Price_per_Quintal'].shift(1).rolling(3, min_periods=1).mean()
    
    # L2
    df_l2 = df.groupby(['Crop', 'Season', 'Year_start'])['Real_Market_Price_per_Quintal'].mean().reset_index()
    df_l2 = df_l2.sort_values(by=['Crop', 'Season', 'Year_start'])
    df_l2['Baseline_L2'] = df_l2.groupby(['Crop', 'Season'])['Real_Market_Price_per_Quintal'].shift(1).rolling(3, min_periods=1).mean()
    
    df = df.merge(df_l0[['District', 'Crop', 'Season', 'Year_start', 'Baseline_L0']], 
                  on=['District', 'Crop', 'Season', 'Year_start'], how='left')
    df = df.merge(df_l1[['State', 'Crop', 'Season', 'Year_start', 'Baseline_L1']], 
                  on=['State', 'Crop', 'Season', 'Year_start'], how='left')
    df = df.merge(df_l2[['Crop', 'Season', 'Year_start', 'Baseline_L2']], 
                  on=['Crop', 'Season', 'Year_start'], how='left')
                  
    df['Baseline_Price'] = df['Baseline_L0']
    df['Baseline_Price'] = df['Baseline_Price'].fillna(df['Baseline_L1'])
    df['Baseline_Price'] = df['Baseline_Price'].fillna(df['Baseline_L2'])
    df['Baseline_Price'] = df['Baseline_Price'].fillna(df['Real_Market_Price_per_Quintal'].mean())
    
    return df
