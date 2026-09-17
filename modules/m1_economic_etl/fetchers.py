import os
import time
import json
import urllib.request
import urllib.error
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw_snapshots"
MANUAL_INSTRUCTIONS_PATH = RAW_DATA_DIR / "MANUAL_DOWNLOAD_INSTRUCTIONS.md"

# Ensure data dir exists
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Target Endpoints (Data.gov.in and RBI DBIE are notoriously protected)
# Using placeholder/public endpoints that require API keys or session state to demonstrate defensive fallback
ENDPOINTS = {
    "AGMARKNET_PRICES": "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070?format=json&limit=10", # Requires API Key
    "RBI_WPI": "https://rbi.org.in/Scripts/WPI_Base2011_12.aspx", # Requires ASP.NET Session/Viewstate navigation
    "DES_COSTS": "https://eands.dacnet.nic.in/Cost_of_Cultivation.htm" # Requires PDF/Excel manual extraction
}

def attempt_fetch(name, url, retries=2, timeout=5):
    """
    Defensively attempt to fetch data.
    Implements timeout and basic retry logic.
    """
    print(f"[FETCH] Attempting to acquire {name} from {url}...")
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status == 200:
                    print(f"  -> [SUCCESS] Acquired {name} on attempt {attempt}.")
                    return True
                else:
                    print(f"  -> [WARN] Attempt {attempt} failed with status: {response.status}")
        except urllib.error.HTTPError as e:
            print(f"  -> [ERROR] HTTP Error {e.code}: {e.reason} for {name}.")
            break # No point retrying 401/403 immediately without auth changes
        except urllib.error.URLError as e:
            print(f"  -> [ERROR] URL Error/Timeout: {e.reason}")
        except Exception as e:
            print(f"  -> [ERROR] Unexpected Error: {str(e)}")
        
        if attempt < retries:
            print(f"  -> Retrying in 2 seconds...")
            time.sleep(2)
            
    print(f"  -> [FAIL] Exhausted attempts for {name}. Fallback required.")
    return False

def generate_manual_fallback():
    """
    Generates the markdown instructions if programmatic fetch is blocked.
    """
    content = """# 🚨 Manual Data Download Required

The automated fetchers were blocked (e.g., via IP Rate Limiting, CAPTCHA, or missing API Keys).
To ensure data reproducibility and maintain the integrity of our pipeline, please manually download the following datasets and place them in the `data/raw_snapshots/` folder.

## 1. AGMARKNET Mandi Prices
1. Visit: [AGMARKNET Portal](https://agmarknet.gov.in/)
2. Navigate to: **Price & Arrivals -> Daily/Monthly**
3. Select the 5 States (MH, MP, UP, PB, TN) and 45 Crops spanning 2000-2020.
4. Export as Excel/CSV and save as: `data/raw_snapshots/agmarknet_prices.csv`

## 2. RBI Wholesale Price Index (WPI)
1. Visit: [RBI DBIE WPI Series](https://dbie.rbi.org.in/DBIE/dbie.rbi?site=statistics)
2. Download the historical WPI series (Base 2011-12=100) for Agricultural Commodities.
3. Save as: `data/raw_snapshots/rbi_wpi_2011_base.csv`

## 3. DES Cost of Cultivation
1. Visit: [DACNET Cost of Cultivation](https://eands.dacnet.nic.in/Cost_of_Cultivation.htm)
2. Download the State-wise C2 and A2+FL costs for our relevant crops.
3. Save as: `data/raw_snapshots/des_cost_of_cultivation.csv`

*Once these files are placed in this directory, the ETL pipeline will automatically parse them, build crosswalks, and perform MAD clipping and WPI deflation.*
"""
    with open(MANUAL_INSTRUCTIONS_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"\n[SYSTEM] Programmatic fetch blocked by external servers. Generated manual instructions at: {MANUAL_INSTRUCTIONS_PATH}")

def main():
    print("==================================================")
    print(" MODULE 1: DEFENSIVE ECONOMIC DATA ACQUISITION    ")
    print("==================================================")
    
    all_success = True
    for name, url in ENDPOINTS.items():
        success = attempt_fetch(name, url)
        if not success:
            all_success = False
            
    if not all_success:
        generate_manual_fallback()
    else:
        print("\n[SYSTEM] All data fetched successfully!")

if __name__ == "__main__":
    main()
