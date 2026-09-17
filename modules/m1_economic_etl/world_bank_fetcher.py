import os
import requests
import pandas as pd
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
INFLATION_OUT_PATH = PROCESSED_DATA_DIR / "inflation_index.csv"

# World Bank API for India Consumer Price Index (FP.CPI.TOTL)
# We fetch 1999 to 2021 to ensure we cover the 2000-2020 range cleanly
WB_API_URL = "http://api.worldbank.org/v2/country/IND/indicator/FP.CPI.TOTL?date=1999:2021&format=json&per_page=100"

def fetch_and_rebase_inflation():
    print("[FETCH] Connecting to World Bank API...")
    try:
        response = requests.get(WB_API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # World Bank JSON format: [ {page_info}, [ {record}, {record}... ] ]
        records = data[1]
        
        # Parse into DataFrame
        df = pd.DataFrame([{
            'Year': int(r['date']),
            'WB_CPI': float(r['value']) if r['value'] is not None else None
        } for r in records])
        
        df = df.sort_values('Year').reset_index(drop=True)
        
        # Interpolate missing values just in case
        df['WB_CPI'] = df['WB_CPI'].interpolate(method='linear')
        
        # Rebase to 2011=100 to match RBI agricultural standards
        base_2011_value = df.loc[df['Year'] == 2011, 'WB_CPI'].values[0]
        df['Deflator_Index'] = (df['WB_CPI'] / base_2011_value) * 100
        
        # Keep only necessary columns
        final_df = df[['Year', 'Deflator_Index']]
        
        # Save to processed directory
        final_df.to_csv(INFLATION_OUT_PATH, index=False)
        print(f"[SUCCESS] Successfully fetched and rebased inflation data.")
        print(f"[INFO] Saved to {INFLATION_OUT_PATH}")
        print(final_df.head(5))
        print("...")
        print(final_df.tail(5))
        
    except Exception as e:
        print(f"[ERROR] Failed to fetch or process World Bank data: {str(e)}")
        raise e

if __name__ == "__main__":
    fetch_and_rebase_inflation()
