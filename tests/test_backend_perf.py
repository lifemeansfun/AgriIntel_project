"""Historical compatibility and measured TestClient throughput, without a machine-specific latency gate."""
import time

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from test_regional_api import FixtureCatalog
from test_regional_ledger import scenario


@pytest.fixture
def client(tmp_path, scenario):
    with TestClient(create_app(db_path=tmp_path / "perf.db", catalog=FixtureCatalog(scenario))) as http:
        yield http


def test_historical_compatibility_and_scaling(client):
    params = {"state": "Tamil Nadu", "district": "Coimbatore", "season": "Kharif", "area_hectares": 1.0}
    first = client.get("/api/recommendations", params=params)
    larger = client.post("/api/recommendations", json={**params, "area_hectares": 3.0})
    assert first.status_code == larger.status_code == 200
    assert first.headers["Cache-Control"] == "no-store"
    assert first.json()["mode"] == "historical"
    one = {r["Crop"]: r for r in first.json()["recommendations"]}
    three = {r["Crop"]: r for r in larger.json()["recommendations"]}
    for crop in one:
        for field in ("Central_Profit", "Pessimistic_Profit", "Downside_Gap", "Score"):
            assert three[crop][field] == pytest.approx(3 * one[crop][field])
    assert client.get("/api/recommendations", params={**params, "district": "unknown"}).status_code == 404


def test_record_testclient_throughput(client, capsys):
    start = time.perf_counter()
    for _ in range(100):
        assert client.get("/api/locations").status_code == 200
    elapsed = time.perf_counter() - start
    print(f"100 fixture-backed HTTP requests: {elapsed:.4f}s; {elapsed * 10:.3f}ms/request (not production capacity)")
    assert elapsed > 0
