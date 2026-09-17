import pandas as pd
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CROSSWALKS_DIR = PROJECT_ROOT / "crosswalks"
ECONOMIC_FACT_PATH = PROCESSED_DIR / "fact_economic_seasonal.parquet"

def calculate_profits():
    print("[ETL] Loading agronomic, inflation, and MSP datasets...")
    df_agro = pd.read_parquet(PROCESSED_DIR / "agronomic_cleaned_v4.parquet")
    df_inflation = pd.read_csv(PROCESSED_DIR / "inflation_index.csv")
    df_msp = pd.read_csv(CROSSWALKS_DIR / "historical_msp_registry.csv")
    
    initial_rows = len(df_agro)
    
    # Standardize data types for merge keys
    df_agro['Year_start'] = df_agro['Year_start'].astype(int)
    df_msp['Year'] = df_msp['Year'].astype(int)
    df_inflation['Year'] = df_inflation['Year'].astype(int)
    
    print("[ETL] Merging datasets...")
    # Merge MSP (on Crop and Year_start)
    df_merged = pd.merge(df_agro, df_msp, left_on=['Crop', 'Year_start'], right_on=['Crop', 'Year'], how='left')
    
    # Merge Inflation (on Year_start)
    df_merged = pd.merge(df_merged, df_inflation, left_on='Year_start', right_on='Year', how='left')
    
    # Verify merge
    if df_merged['Nominal_MSP'].isna().any() or df_merged['Deflator_Index'].isna().any():
        missing_crops = df_merged[df_merged['Nominal_MSP'].isna()]['Crop'].unique()
        error_msg = f"Merge introduced NAs for crops: {missing_crops}. Data integrity compromised."
        print(f"[ERROR] {error_msg}")
        raise ValueError(error_msg)
    else:
        print("[SUCCESS] 100% merge rate achieved.")
        
    print("[ETL] Calculating Real Economics...")
    # 1. Deflation: Convert Nominal to Real Base 2011
    df_merged['Real_MSP_per_Quintal'] = (df_merged['Nominal_MSP'] / df_merged['Deflator_Index']) * 100
    
    # 2. Swaminathan Proxy: Cost = MSP / 1.5
    df_merged['Real_Cost_per_Quintal'] = df_merged['Real_MSP_per_Quintal'] / 1.5
    
    # 3. Profit Margins
    df_merged['Real_Profit_per_Quintal'] = df_merged['Real_MSP_per_Quintal'] - df_merged['Real_Cost_per_Quintal']
    
    # 4. Hectare Aggregations (Yield is Tonnes/Ha. 1 Tonne = 10 Quintals)
    df_merged['Real_Profit_per_Hectare'] = df_merged['Yield'] * 10 * df_merged['Real_Profit_per_Quintal']
    df_merged['Real_Revenue_per_Hectare'] = df_merged['Yield'] * 10 * df_merged['Real_MSP_per_Quintal']
    df_merged['Real_Cost_per_Hectare'] = df_merged['Yield'] * 10 * df_merged['Real_Cost_per_Quintal']
    
    # Ensure no massive row explosion or loss
    assert len(df_merged) == initial_rows, f"Row count mismatch after merge! Expected {initial_rows}, got {len(df_merged)}"
    
    # Defensive checks on economic logic
    assert (df_merged['Real_Revenue_per_Hectare'] >= 0).all(), "Found negative revenues."
    assert (df_merged['Real_Cost_per_Hectare'] >= 0).all(), "Found negative costs."    
    print("[ETL] Saving economic fact table...")
    df_merged.to_parquet(ECONOMIC_FACT_PATH, index=False)
    
    # Sanity Checks
    mean_profit = df_merged['Real_Profit_per_Hectare'].mean()
    print(f"[SUCCESS] Pipeline complete. Generated fact_economic_seasonal.parquet")
    print(f"[STATS] Average Real Profit / Hectare (Base 2011 INR): {mean_profit:.2f}")

if __name__ == "__main__":
    calculate_profits()
