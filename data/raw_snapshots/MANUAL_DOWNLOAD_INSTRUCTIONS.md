# 🚨 Manual Data Download Required

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
