import pandas as pd
from pathlib import Path
import sys

def validate_m1():
    print("[VALIDATION] Starting Module 1 Validation...")
    
    # Paths
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
    PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
    ECONOMIC_FACT_PATH = PROCESSED_DIR / "fact_economic_seasonal.parquet"
    
    if not ECONOMIC_FACT_PATH.exists():
        print(f"[ERROR] Fact table not found at {ECONOMIC_FACT_PATH}")
        sys.exit(1)
        
    df = pd.read_parquet(ECONOMIC_FACT_PATH)
    
    print(f"[INFO] Loaded fact table with {len(df)} records.")
    
    # 1. No Missing Values Check
    required_cols = [
        'State', 'District', 'Crop', 'Year_start', 'Season',
        'Area', 'Production', 'Yield',
        'Nominal_MSP', 'Deflator_Index',
        'Real_MSP_per_Quintal', 'Real_Cost_per_Quintal', 'Real_Profit_per_Quintal',
        'Real_Profit_per_Hectare', 'Real_Revenue_per_Hectare', 'Real_Cost_per_Hectare'
    ]
    
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"[ERROR] Missing columns: {missing_cols}")
        sys.exit(1)
        
    na_counts = df[required_cols].isna().sum()
    if na_counts.any():
        print("[ERROR] Found missing values in essential columns:")
        print(na_counts[na_counts > 0])
        sys.exit(1)
    
    # 2. Logic Check (Revenue = Profit + Cost)
    # Using a small tolerance for floating point errors
    calc_revenue = df['Real_Profit_per_Hectare'] + df['Real_Cost_per_Hectare']
    diff = (df['Real_Revenue_per_Hectare'] - calc_revenue).abs()
    
    if (diff > 0.01).any():
        print(f"[ERROR] Economic invariant failed: Revenue != Profit + Cost for {(diff > 0.01).sum()} rows.")
        sys.exit(1)
        
    # 3. Non-Negative Constraints
    negative_checks = {
        'Area': df['Area'] < 0,
        'Production': df['Production'] < 0,
        'Yield': df['Yield'] < 0,
        'Real_Cost_per_Hectare': df['Real_Cost_per_Hectare'] < 0,
        'Real_Revenue_per_Hectare': df['Real_Revenue_per_Hectare'] < 0
    }
    
    failed = False
    for name, mask in negative_checks.items():
        if mask.any():
            print(f"[ERROR] Found {mask.sum()} negative values in {name}.")
            failed = True
            
    if failed:
        sys.exit(1)
        
    # 4. Outlier/Statistical Check (Just to log and ensure reasonability)
    print("\n[STATS] Summary of Real Profit per Hectare:")
    print(df['Real_Profit_per_Hectare'].describe())
    
    print("\n[SUCCESS] Module 1 data passed all validation checks! Data is clean, complete, and economically sound.")

if __name__ == "__main__":
    validate_m1()
