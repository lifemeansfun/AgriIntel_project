"""
District Geocoding Pipeline
---------------------------
Extracts unique (State, District) pairs from the agronomic dataset, queries
coordinates via OpenStreetMap's Nominatim API with rate limiting and checkpointing,
and generates a verified, frozen registry in `crosswalks/district_coordinates.csv`.
"""

import os
import sys
import time
import logging
from pathlib import Path
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("district_geocoder")

# India Bounding Box Constraints
MIN_LAT, MAX_LAT = 6.0, 38.0
MIN_LON, MAX_LON = 68.0, 98.0

# Alternate names / historical aliases to guarantee 100% resolution
DISTRICT_ALIASES = {
    ("Madhya Pradesh", "East Nimar"): "Khandwa",
    ("Madhya Pradesh", "West Nimar"): "Khargone",
    ("Uttar Pradesh", "Sant Ravi Das Nagar"): "Bhadohi",
    ("Uttar Pradesh", "Allahabad"): "Prayagraj",
    ("Uttar Pradesh", "Faizabad"): "Ayodhya",
    ("Uttar Pradesh", "Amroha"): "Jyotiba Phule Nagar",
    ("Uttar Pradesh", "Hathras"): "Mahamaya Nagar",
    ("Uttar Pradesh", "Kasganj"): "Kanshiram Nagar",
    ("Maharashtra", "Bid"): "Beed",
    ("Maharashtra", "Osmanabad"): "Dharashiv",
    ("Maharashtra", "Aurangabad"): "Chhatrapati Sambhajinagar",
    ("Maharashtra", "Ahmadnagar"): "Ahilyanagar",
    ("Maharashtra", "Garhchiroli"): "Gadchiroli",
    ("Maharashtra", "Raigarh"): "Raigad",
    ("Tamil Nadu", "The Nilgiris"): "Nilgiris",
    ("Tamil Nadu", "Kancheepuram"): "Kanchipuram",
    ("Tamil Nadu", "Viluppuram"): "Villupuram",
    ("Tamil Nadu", "Kanniyakumari"): "Kanyakumari",
    ("Tamil Nadu", "Thoothukkudi"): "Tuticorin",
    ("Tamil Nadu", "Thiruvarur"): "Tiruvarur",
    ("Tamil Nadu", "Virudunagar"): "Virudhunagar",
    ("Punjab", "Shahid Bhagat Singh Nagar"): "Nawanshahr",
    ("Punjab", "Muktsar"): "Sri Muktsar Sahib",
}

def validate_coordinates(lat: float, lon: float, district: str, state: str) -> None:
    """Validate that coordinates fall inside the physical boundary of India."""
    if not (MIN_LAT <= lat <= MAX_LAT and MIN_LON <= lon <= MAX_LON):
        raise ValueError(
            f"Invalid coordinates for {district}, {state}: ({lat}, {lon}) outside India bounding box."
        )

def fetch_coordinates_with_retry(geolocator: Nominatim, query: str, max_retries: int = 4) -> tuple[float, float] | None:
    """Execute geocoding lookup with exponential backoff on timeouts."""
    delay = 1.5
    for attempt in range(max_retries):
        try:
            loc = geolocator.geocode(query, timeout=12)
            if loc is not None:
                return loc.latitude, loc.longitude
            return None
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            logger.warning(f"Geocoding attempt {attempt + 1} failed for '{query}': {e}. Retrying in {delay}s...")
            time.sleep(delay)
            delay *= 2
    return None

def resolve_district(geolocator: Nominatim, state: str, district: str) -> tuple[float, float]:
    """Resolve coordinates for a district using multi-tier fallback strategies."""
    alias = DISTRICT_ALIASES.get((state, district))

    candidate_queries = [
        f"{district} district, {state}, India",
        f"{district}, {state}, India",
    ]
    if alias:
        candidate_queries.insert(1, f"{alias} district, {state}, India")
        candidate_queries.insert(2, f"{alias}, {state}, India")
    candidate_queries.append(f"{district}, India")

    for query in candidate_queries:
        time.sleep(1.1)  # Strict adherence to Nominatim 1 req/sec policy
        coords = fetch_coordinates_with_retry(geolocator, query)
        if coords is not None:
            lat, lon = coords
            try:
                validate_coordinates(lat, lon, district, state)
                return lat, lon
            except ValueError as ve:
                logger.warning(f"Discarding result for '{query}': {ve}")
                continue

    raise RuntimeError(f"FATAL: Failed to resolve coordinates for district: '{district}', state: '{state}'.")

def run_geocoding(
    input_parquet: str = "data/processed/agronomic_cleaned_v4.parquet",
    output_csv: str = "crosswalks/district_coordinates.csv"
) -> pd.DataFrame:
    input_path = Path(input_parquet)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    logger.info(f"Loading agronomic dataset from {input_path}...")
    df_raw = pd.read_parquet(input_path, columns=["State", "District"])
    unique_pairs = (
        df_raw[["State", "District"]]
        .drop_duplicates()
        .sort_values(["State", "District"])
        .reset_index(drop=True)
    )
    total_districts = len(unique_pairs)
    logger.info(f"Found {total_districts} unique (State, District) pairs.")

    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Checkpoint recovery
    cached_df = pd.DataFrame(columns=["state", "district", "latitude", "longitude"])
    resolved_map = {}
    if output_path.exists():
        cached_df = pd.read_csv(output_path)
        logger.info(f"Found existing registry with {len(cached_df)} records. Resuming...")
        for _, row in cached_df.iterrows():
            resolved_map[(row["state"], row["district"])] = (float(row["latitude"]), float(row["longitude"]))

    geolocator = Nominatim(user_agent="agri_intel_dsp_project_spatial_v4")
    new_resolutions = 0

    results = []
    for idx, row in unique_pairs.iterrows():
        state = str(row["State"]).strip()
        district = str(row["District"]).strip()

        if (state, district) in resolved_map:
            lat, lon = resolved_map[(state, district)]
            results.append({"state": state, "district": district, "latitude": lat, "longitude": lon})
            continue

        logger.info(f"[{idx + 1}/{total_districts}] Geocoding: {district}, {state}...")
        lat, lon = resolve_district(geolocator, state, district)
        results.append({"state": state, "district": district, "latitude": lat, "longitude": lon})
        resolved_map[(state, district)] = (lat, lon)
        new_resolutions += 1

        # Checkpoint every 5 new lookups
        if new_resolutions % 5 == 0:
            temp_df = pd.DataFrame(results)
            temp_df.to_csv(output_path, index=False)
            logger.info(f"Checkpoint saved: {len(temp_df)} records.")

    final_df = pd.DataFrame(results)
    
    # Defensive validations
    assert len(final_df) == total_districts, f"Mismatch: expected {total_districts} districts, got {len(final_df)}"
    assert final_df["latitude"].isna().sum() == 0, "Found null latitude values!"
    assert final_df["longitude"].isna().sum() == 0, "Found null longitude values!"
    assert (final_df["latitude"] >= MIN_LAT).all() and (final_df["latitude"] <= MAX_LAT).all(), "Latitude out of bounds!"
    assert (final_df["longitude"] >= MIN_LON).all() and (final_df["longitude"] <= MAX_LON).all(), "Longitude out of bounds!"

    final_df.sort_values(["state", "district"]).to_csv(output_path, index=False)
    logger.info(f"Successfully verified and saved all {len(final_df)} district coordinates to {output_path}.")
    return final_df

if __name__ == "__main__":
    run_geocoding()
