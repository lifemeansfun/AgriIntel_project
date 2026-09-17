"""
Module 5: Ranker
Scores and ranks crops based on risk-adjusted profit.
"""

import pandas as pd

def rank_crops(df: pd.DataFrame, lmbda: float) -> pd.DataFrame:
    # Calculate Recommendation Score
    df['Recommendation_Score'] = df['Expected_Profit'] - (lmbda * df['Downside_Risk'])
    
    # Rank recommended crops (descending score)
    df['Recommended_Rank'] = df.groupby(['District', 'Season', 'Year_start'])['Recommendation_Score'].rank(method='first', ascending=False)
    
    # Rank realized crops (descending true profit)
    df['Realized_Rank'] = df.groupby(['District', 'Season', 'Year_start'])['Realized_Profit'].rank(method='first', ascending=False)
    
    # Sort
    df = df.sort_values(by=['Year_start', 'District', 'Season', 'Recommended_Rank'])
    
    return df

def apply_baseline_strategy(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agricultural Baseline: Plant whatever was most profitable here last year.
    We just carry forward the Realized_Rank from T-1 as the Baseline_Rank for T.
    """
    df = df.copy()
    
    df_lag = df[['District', 'Crop', 'Season', 'Year_start', 'Realized_Profit']].copy()
    df_lag['Year_start'] = df_lag['Year_start'] + 1
    df_lag = df_lag.rename(columns={'Realized_Profit': 'Lag1_Realized_Profit'})
    
    df = df.merge(df_lag, on=['District', 'Crop', 'Season', 'Year_start'], how='left')
    
    # If a crop wasn't planted last year, assume -infinity profit for ranking purposes (don't plant it)
    df['Lag1_Realized_Profit'] = df['Lag1_Realized_Profit'].fillna(-1e9)
    
    df['Baseline_Rank'] = df.groupby(['District', 'Season', 'Year_start'])['Lag1_Realized_Profit'].rank(method='first', ascending=False)
    
    return df
