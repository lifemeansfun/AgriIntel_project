import pytest
from fastapi.testclient import TestClient
from backend.main import app, _initialize_caches, CACHED_LOCATIONS, RECOMMENDATION_CACHE
import time

@pytest.fixture(scope="module", autouse=True)
def init_server():
    _initialize_caches()
    with TestClient(app) as client:
        yield client

def test_root_endpoint(init_server):
    response = init_server.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "AgriIntel API is running"
    assert data["cached_locations"] > 0
    assert data["cached_tuples"] > 0

def test_locations_endpoint(init_server):
    response = init_server.get("/api/locations")
    assert response.status_code == 200
    assert "public, max-age=86400" in response.headers.get("Cache-Control", "")
    data = response.json()
    assert isinstance(data, dict)
    assert "Punjab" in data
    assert "Ludhiana" in data["Punjab"]
    assert "Kharif" in data["Punjab"]["Ludhiana"]

def test_recommendations_post(init_server):
    payload = {
        "state": "Punjab",
        "district": "Ludhiana",
        "season": "Kharif",
        "area_hectares": 2.5
    }
    response = init_server.post("/api/recommendations", json=payload)
    assert response.status_code == 200
    recs = response.json().get("recommendations", [])
    assert len(recs) > 0
    
    # Verify descending sort by Score
    scores = [r["Score"] for r in recs]
    assert scores == sorted(scores, reverse=True)
    
    first = recs[0]
    assert "Crop" in first
    assert "Expected_Profit" in first
    assert "Downside_Risk" in first
    assert "Safety_Rating" in first
    assert first["Safety_Rating"] in ["Safe", "Moderate Risk", "High Risk"]

def test_recommendations_get_and_cache_header(init_server):
    params = {
        "state": "Punjab",
        "district": "Ludhiana",
        "season": "Kharif",
        "area_hectares": 2.5
    }
    response = init_server.get("/api/recommendations", params=params)
    assert response.status_code == 200
    assert "public, max-age=3600" in response.headers.get("Cache-Control", "")
    recs = response.json().get("recommendations", [])
    assert len(recs) > 0

def test_recommendations_area_scaling(init_server):
    # Base 1.0 ha vs 3.0 ha
    resp_1 = init_server.get("/api/recommendations?state=Punjab&district=Ludhiana&season=Kharif&area_hectares=1.0").json()
    resp_3 = init_server.get("/api/recommendations?state=Punjab&district=Ludhiana&season=Kharif&area_hectares=3.0").json()
    
    recs_1 = resp_1["recommendations"]
    recs_3 = resp_3["recommendations"]
    
    assert len(recs_1) == len(recs_3)
    for r1, r3 in zip(recs_1, recs_3):
        assert r1["Crop"] == r3["Crop"]
        assert abs(r3["Expected_Profit"] - (r1["Expected_Profit"] * 3.0)) < 1e-4
        assert abs(r3["Downside_Risk"] - (r1["Downside_Risk"] * 3.0)) < 1e-4
        assert abs(r3["Score"] - (r1["Score"] * 3.0)) < 1e-4

def test_recommendations_unknown_location(init_server):
    payload = {
        "state": "NonExistentState",
        "district": "Nowhere",
        "season": "Kharif",
        "area_hectares": 1.0
    }
    response = init_server.post("/api/recommendations", json=payload)
    assert response.status_code == 404

def test_benchmark_throughput(init_server):
    # Benchmark 500 requests through TestClient
    params = {"state": "Punjab", "district": "Ludhiana", "season": "Kharif", "area_hectares": 1.5}
    start = time.perf_counter()
    for _ in range(500):
        resp = init_server.get("/api/recommendations", params=params)
        assert resp.status_code == 200
    elapsed = time.perf_counter() - start
    
    latency_per_req_ms = (elapsed / 500) * 1000
    print(f"\n[TestClient Benchmark] 500 full HTTP requests completed in {elapsed:.4f}s ({latency_per_req_ms:.3f} ms/req)")
    # Must comfortably be sub-millisecond per request even with TestClient overhead
    assert latency_per_req_ms < 2.0
