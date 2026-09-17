"""
Module 5: Economic Engine
Convolutes M3 and M4 predictions into Expected Profit and Downside Risk.
"""

import pandas as pd
import numpy as np

def calculate_economics(df_yield: pd.DataFrame, df_price: pd.DataFrame, df_cost: pd.DataFrame) -> pd.DataFrame:
    keys = ['State', 'District', 'Crop', 'Season', 'Year_start']
    
    # Select needed columns
    y_cols = keys + ['q10', 'q50', 'q90', 'Yield']
    p_cols = keys + ['p10', 'p50', 'p90', 'Real_Market_Price_per_Quintal']
    c_cols = keys + ['Real_Cost_per_Hectare']
    
    # Merge
    df = df_yield[y_cols].merge(df_price[p_cols], on=keys, how='inner')
    df = df.merge(df_cost[c_cols], on=keys, how='left')
    
    initial_len = len(df)
    
    # 1. Fallback for missing costs (Hierarchical)
    # If a cost is missing, fill with District Mean -> State Mean -> National Mean
    dist_cost = df_cost.groupby(['District', 'Crop', 'Season'])['Real_Cost_per_Hectare'].transform('mean')
    state_cost = df_cost.groupby(['State', 'Crop', 'Season'])['Real_Cost_per_Hectare'].transform('mean')
    nat_cost = df_cost.groupby(['Crop', 'Season'])['Real_Cost_per_Hectare'].transform('mean')
    
    # Re-apply to df based on its rows
    # It's safer to just compute aggregations and merge them
    agg_dist = df_cost.groupby(['District', 'Crop', 'Season'])['Real_Cost_per_Hectare'].mean().reset_index().rename(columns={'Real_Cost_per_Hectare': 'cost_d'})
    agg_state = df_cost.groupby(['State', 'Crop', 'Season'])['Real_Cost_per_Hectare'].mean().reset_index().rename(columns={'Real_Cost_per_Hectare': 'cost_s'})
    agg_nat = df_cost.groupby(['Crop', 'Season'])['Real_Cost_per_Hectare'].mean().reset_index().rename(columns={'Real_Cost_per_Hectare': 'cost_n'})
    
    df = df.merge(agg_dist, on=['District', 'Crop', 'Season'], how='left')
    df = df.merge(agg_state, on=['State', 'Crop', 'Season'], how='left')
    df = df.merge(agg_nat, on=['Crop', 'Season'], how='left')
    
    df['Real_Cost_per_Hectare'] = df['Real_Cost_per_Hectare'].fillna(df['cost_d'])
    df['Real_Cost_per_Hectare'] = df['Real_Cost_per_Hectare'].fillna(df['cost_s'])
    df['Real_Cost_per_Hectare'] = df['Real_Cost_per_Hectare'].fillna(df['cost_n'])
    df['Real_Cost_per_Hectare'] = df['Real_Cost_per_Hectare'].fillna(df['Real_Cost_per_Hectare'].mean())
    
    df = df.drop(columns=['cost_d', 'cost_s', 'cost_n'])
    
    if df['Real_Cost_per_Hectare'].isna().any():
        raise ValueError("Cost missingness still present after hierarchical fallback. Data integrity failure.")
        
    if len(df) != initial_len:
        raise ValueError(f"Row explosion during merge: {initial_len} -> {len(df)}")
        
    # 2. Economic Formulations
    # Strict scaling: 1 Tonne = 10 Quintals. Yield is t/ha, Price is per quintal.
    
    # Expected Profit
    df['Expected_Revenue'] = df['q50'] * 10.0 * df['p50']
    df['Expected_Profit'] = df['Expected_Revenue'] - df['Real_Cost_per_Hectare']
    
    # Pessimistic Profit
    df['Pessimistic_Revenue'] = df['q10'] * 10.0 * df['p10']
    df['Pessimistic_Profit'] = df['Pessimistic_Revenue'] - df['Real_Cost_per_Hectare']
    
    # Downside Risk (Always >= 0 since q50>=q10 and p50>=p10)
    df['Downside_Risk'] = df['Expected_Profit'] - df['Pessimistic_Profit']
    
    # True Realized Profit (for evaluation)
    df['Realized_Profit'] = (df['Yield'] * 10.0 * df['Real_Market_Price_per_Quintal']) - df['Real_Cost_per_Hectare']
    
    return df
