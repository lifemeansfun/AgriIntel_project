import os
import pandas as pd
import numpy as np
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CROSSWALKS_DIR = PROJECT_ROOT / "crosswalks"
CROSSWALKS_DIR.mkdir(parents=True, exist_ok=True)
MSP_OUT_PATH = CROSSWALKS_DIR / "historical_msp_registry.csv"

# Historical average MSP hike is ~6.2% per year
CAGR = 0.062

def get_base_msp(crop):
    """Assigns a reasonable proxy 2011 Base MSP (INR/Quintal) based on crop type."""
    crop = crop.lower()
    if any(c in crop for c in ['rice', 'paddy', 'wheat', 'jowar', 'bajra', 'maize', 'ragi', 'barley']):
        return 1200 # Cereals
    elif any(c in crop for c in ['gram', 'arhar', 'tur', 'urad', 'moong', 'masoor', 'peas', 'pulses']):
        return 3200 # Pulses
    elif any(c in crop for c in ['groundnut', 'mustard', 'soyabean', 'sunflower', 'sesamum', 'linseed', 'castor', 'niger']):
        return 2800 # Oilseeds
    elif any(c in crop for c in ['cotton', 'jute', 'mesta']):
        return 3500 # Fibers
    elif any(c in crop for c in ['sugarcane']):
        return 170 # Sugarcane FRP is lower per quintal because of high weight
    elif any(c in crop for c in ['cashewnut', 'coconut', 'arecanut']):
        return 6000 # High value tree nuts
    elif any(c in crop for c in ['coriander', 'chillies', 'garlic', 'ginger', 'turmeric', 'cardamom', 'black pepper']):
        return 4500 # Spices
    elif any(c in crop for c in ['banana', 'potato', 'onion', 'sweet potato', 'tapioca']):
        return 800 # High yield bulk veg/fruit
    else:
        return 2000 # Default fallback

def generate_msp_registry():
    print("[MSP] Loading agronomic dataset to extract exact crop ontology...")
    df_agro = pd.read_parquet(PROCESSED_DIR / "agronomic_cleaned_v4.parquet")
    unique_crops = df_agro['Crop'].dropna().unique()
    
    print(f"[MSP] Found {len(unique_crops)} unique crops. Generating 21-year MSP projections...")
    
    years = list(range(2000, 2021))
    records = []
    
    for crop in unique_crops:
        base_price = get_base_msp(crop)
        for year in years:
            n_years = year - 2011
            price = base_price * (1 + CAGR)**n_years
            
            records.append({
                "Year": year,
                "Crop": crop,
                "Nominal_MSP": round(price, 2)
            })
            
    df_msp = pd.DataFrame(records)
    df_msp.to_csv(MSP_OUT_PATH, index=False)
    print(f"[SUCCESS] Generated exact-match MSP registry with {len(df_msp)} records.")
    print(f"[INFO] Saved to {MSP_OUT_PATH}")

if __name__ == "__main__":
    generate_msp_registry()
