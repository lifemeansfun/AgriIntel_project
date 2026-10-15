"""Legacy unscoped mutation is deliberately retired; all storage is temporary."""
from fastapi.testclient import TestClient
from backend.main import create_app
from test_regional_api import FixtureCatalog
from test_regional_ledger import scenario


def test_retired_unscoped_endpoints(tmp_path, scenario):
    with TestClient(create_app(db_path=tmp_path / "legacy.db", catalog=FixtureCatalog(scenario))) as client:
        assert client.get("/api/state").status_code == 410
        assert client.post("/api/commit", json={"farmer_id": "test", "crop": "Tomato", "area_ha": 1}).status_code == 410
        assert client.get("/api/v2/state", params={"scenario_id": scenario["id"]}).json()["total_committed_area_ha"] == 0
