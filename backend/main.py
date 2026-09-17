from fastapi import FastAPI, HTTPException, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import ORJSONResponse
import pandas as pd
import numpy as np
from pydantic import BaseModel, Field
import os
from typing import List, Dict, Any, Tuple, Optional
from contextlib import asynccontextmanager

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'processed', 'fact_recommendations.parquet')

# Global high-performance caches
CACHED_LOCATIONS: Dict[str, Dict[str, List[str]]] = {}
RECOMMENDATION_CACHE: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = {}

def _initialize_caches():
    """Defensive pre-computation of locations and latest-year recommendations for sub-millisecond retrieval."""
    global CACHED_LOCATIONS, RECOMMENDATION_CACHE
    if not os.path.exists(DATA_PATH):
        print(f"[AgriIntel Startup Warning] Parquet file not found at {DATA_PATH}")
        return

    try:
        df = pd.read_parquet(DATA_PATH)
    except Exception as err:
        print(f"[AgriIntel Startup Error] Failed to read {DATA_PATH}: {err}")
        return

    if df.empty:
        print("[AgriIntel Startup Warning] Empty DataFrame loaded.")
        return

    # 1. Precompute nested State -> District -> Seasons hierarchy
    try:
        if {'State', 'District', 'Season'}.issubset(df.columns):
            grouped = df[['State', 'District', 'Season']].drop_duplicates()
            locs: Dict[str, Dict[str, List[str]]] = {}
            for state, s_group in grouped.groupby('State'):
                locs[str(state)] = {}
                for district, d_group in s_group.groupby('District'):
                    locs[str(state)][str(district)] = sorted(d_group['Season'].unique().tolist())
            CACHED_LOCATIONS = locs
            print(f"[AgriIntel Startup] Precomputed locations cache for {len(CACHED_LOCATIONS)} states.")
    except Exception as err:
        print(f"[AgriIntel Startup Error] Failed to precompute locations: {err}")

    # 2. Precompute recommendation records for the latest available year
    try:
        max_year = df['Year_start'].max()
        df_latest = df[df['Year_start'] == max_year].copy()
        
        cache: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = {}
        grouped_recs = df_latest.groupby(['State', 'District', 'Season'])
        
        for (st, dist, seas), grp in grouped_recs:
            records: List[Dict[str, Any]] = []
            for _, row in grp.iterrows():
                records.append({
                    'Crop': str(row['Crop']),
                    'Base_Expected_Profit': float(row['Expected_Profit']),
                    'Base_Downside_Risk': float(row['Downside_Risk']),
                    'Base_Pessimistic_Profit': float(row['Pessimistic_Profit']),
                    'Yield_q10': float(row['q10']),
                    'Yield_q50': float(row['q50']),
                    'Yield_q90': float(row['q90']),
                    'Price_p10': float(row['p10']),
                    'Price_p50': float(row['p50']),
                    'Price_p90': float(row['p90']),
                    'Cost_per_ha': float(row['Real_Cost_per_Hectare']),
                })
            cache[(str(st), str(dist), str(seas))] = records

        RECOMMENDATION_CACHE = cache
        print(f"[AgriIntel Startup] Precomputed O(1) recommendations cache for {len(RECOMMENDATION_CACHE)} location-season tuples (Year {max_year}).")
    except Exception as err:
        print(f"[AgriIntel Startup Error] Failed to precompute recommendations cache: {err}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Precompute caches
    _initialize_caches()
    yield
    # Shutdown: Clean references
    CACHED_LOCATIONS.clear()
    RECOMMENDATION_CACHE.clear()

# Initialize FastAPI with native orjson response serializer for 5-10x faster serialization
app = FastAPI(
    title="AgriIntel API",
    default_response_class=ORJSONResponse,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

@app.get("/")
def read_root():
    return {"status": "AgriIntel API is running", "cached_locations": len(CACHED_LOCATIONS), "cached_tuples": len(RECOMMENDATION_CACHE)}

@app.get("/api/locations")
def get_locations(response: Response):
    """Returns a nested structure of available States -> Districts -> Seasons from startup cache."""
    response.headers["Cache-Control"] = "public, max-age=86400, stale-while-revalidate=3600"
    return CACHED_LOCATIONS

class RecommendationRequest(BaseModel):
    state: str
    district: str
    season: str
    area_hectares: float = Field(default=1.0, gt=0)

def _compute_recommendations(state: str, district: str, season: str, area: float) -> List[Dict[str, Any]]:
    """Ultra-fast O(1) in-memory recommendation computation with zero DataFrame allocation."""
    raw = RECOMMENDATION_CACHE.get((state, district, season))
    if not raw:
        return []

    lmbda = 0.5
    results: List[Dict[str, Any]] = []
    for item in raw:
        exp_prof = item['Base_Expected_Profit'] * area
        down_risk = item['Base_Downside_Risk'] * area
        pess_prof = item['Base_Pessimistic_Profit'] * area
        score = exp_prof - (lmbda * down_risk)

        # Vectorized / branchless safety rating equivalent
        safety = "Safe" if pess_prof > 0 else ("Moderate Risk" if pess_prof > -5000 else "High Risk")

        results.append({
            'Crop': item['Crop'],
            'Score': score,
            'Expected_Profit': exp_prof,
            'Pessimistic_Profit': pess_prof,
            'Downside_Risk': down_risk,
            'Safety_Rating': safety,
            'Yield_q10': item['Yield_q10'],
            'Yield_q50': item['Yield_q50'],
            'Yield_q90': item['Yield_q90'],
            'Price_p10': item['Price_p10'],
            'Price_p50': item['Price_p50'],
            'Price_p90': item['Price_p90'],
            'Cost_per_ha': item['Cost_per_ha'],
        })

    results.sort(key=lambda x: x['Score'], reverse=True)
    return results

@app.post("/api/recommendations")
def get_recommendations(req: RecommendationRequest):
    """POST endpoint for crop recommendations (backwards compatible)."""
    if not RECOMMENDATION_CACHE:
        raise HTTPException(status_code=500, detail="Data not loaded")

    results = _compute_recommendations(req.state, req.district, req.season, req.area_hectares)
    if not results:
        raise HTTPException(status_code=404, detail="No data found for this location/season combination")

    return {"recommendations": results}

@app.get("/api/recommendations")
def get_recommendations_get(
    response: Response,
    state: str = Query(..., description="State name"),
    district: str = Query(..., description="District name"),
    season: str = Query(..., description="Season name"),
    area_hectares: float = Query(1.0, gt=0, description="Cultivation area in hectares")
):
    """Idempotent GET endpoint for crop recommendations supporting HTTP caching."""
    if not RECOMMENDATION_CACHE:
        raise HTTPException(status_code=500, detail="Data not loaded")

    results = _compute_recommendations(state, district, season, area_hectares)
    if not results:
        raise HTTPException(status_code=404, detail="No data found for this location/season combination")

    # Set cache header for browser/CDN edge caching
    response.headers["Cache-Control"] = "public, max-age=3600, stale-while-revalidate=86400"
    return {"recommendations": results}
