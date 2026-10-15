"""HTTP feedback tests inject fixtures and temporary storage, never application logs."""
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from modules.regional.economics import scenario_row
from test_regional_ledger import scenario  # pytest registers the shared fixture


class FixtureCatalog:
    def __init__(self, config):
        self.config = deepcopy(config)
        self.metadata = {"data_year": 2019, "artifact_id": "test-artifact", "mode": "historical_simulation",
                         "currency_basis": "2011-base INR"}
        self.locations = {"Tamil Nadu": {"Coimbatore": ["Kharif"]}}

    def scenarios(self):
        return [deepcopy(self.config)]

    def scenario(self, scenario_id):
        if scenario_id != self.config["id"]:
            raise KeyError(scenario_id)
        return deepcopy(self.config)

    def historical_rows(self, state, district, season, area):
        if (state, district, season) != ("Tamil Nadu", "Coimbatore", "Kharif"):
            return []
        rows = [scenario_row(c, area, c["reference_price"], c["reference_price"] * .9, c["reference_price"] * 1.1)
                for c in self.config["crops"]]
        return sorted(rows, key=lambda row: -row["Score"])


@pytest.fixture
def client(tmp_path, scenario):
    with TestClient(create_app(db_path=tmp_path / "api.db", catalog=FixtureCatalog(scenario))) as http:
        yield http


def advise(client, scenario, participant="farmer", area=1.0):
    return client.post("/api/v2/recommendations", json={"state": scenario["state"], "district": scenario["district"],
                       "season": scenario["season"], "area_hectares": area,
                       "scenario_id": scenario["id"], "participant_id": participant})


def test_full_feedback_cancel_and_legacy_retirement(client, scenario):
    initial = client.get("/api/v2/state", params={"scenario_id": scenario["id"], "participant_id": "farmer"}).json()
    quote = advise(client, scenario).json()
    assert quote["mode"] == "feedback"
    assert quote["revision"] == 0 and quote["quote_id"]
    assert client.get("/api/v2/state", params={"scenario_id": scenario["id"]}).json()["revision"] == 0
    payload = {"scenario_id": scenario["id"], "participant_id": "farmer", "quote_id": quote["quote_id"],
               "crop": "Ragi", "idempotency_key": "commit-once"}
    result = client.post("/api/v2/commitments", json=payload)
    assert result.status_code == 200
    assert result.json()["state"]["total_committed_area_ha"] == 1
    assert client.post("/api/v2/commitments", json=payload).json() == result.json()
    later = advise(client, scenario, "another").json()
    ragi_before = next(r for r in quote["recommendations"] if r["Crop"] == "Ragi")
    ragi_after = next(r for r in later["recommendations"] if r["Crop"] == "Ragi")
    assert ragi_after["Price_central"] < ragi_before["Price_central"]
    assert ragi_after["Score"] < ragi_before["Score"]
    own = advise(client, scenario).json()
    assert all(not r["Eligible"] for r in own["recommendations"])
    cancelled = client.post(f'/api/v2/commitments/{result.json()["commitment_id"]}/cancel',
                            json={"participant_id": "farmer", "idempotency_key": "cancel-once"})
    assert cancelled.status_code == 200
    assert cancelled.json()["state"]["total_committed_area_ha"] == initial["total_committed_area_ha"]
    assert client.post("/api/commit", json={"farmer_id": "x", "crop": "Tomato", "area_ha": 1}).status_code == 410
    assert client.get("/api/state").status_code == 410


def test_historical_missing_invalid_and_contract(client, scenario):
    location = client.get("/api/v2/locations")
    assert location.status_code == 200 and location.headers["Cache-Control"] == "no-store"
    assert location.json()["locations"]["Tamil Nadu"]["Coimbatore"] == ["Kharif"]
    payload = {"state": "Tamil Nadu", "district": "Coimbatore", "season": "Kharif", "area_hectares": 1}
    historic = client.post("/api/v2/recommendations", json=payload).json()
    assert historic["mode"] == "historical" and historic["quote_id"] is None
    assert historic["recommendations"][0]["Remaining_Area_ha"] is None
    for bad_area in [0, -1, True, "Infinity", 1_000_001]:
        assert client.post("/api/v2/recommendations", json={**payload, "area_hectares": bad_area}).status_code == 422
    assert client.post("/api/v2/recommendations", json={**payload, "district": "unknown"}).status_code == 404
    assert client.post("/api/v2/recommendations", json={**payload, "scenario_id": scenario["id"]}).status_code == 422
    assert client.get("/api/v2/state", params={"scenario_id": "unknown"}).status_code == 404
    assert client.post("/api/v2/commitments", json={"scenario_id": scenario["id"], "participant_id": "x", "quote_id": "x", "crop": "Ragi", "idempotency_key": "k", "area_ha": 900}).status_code == 422


def test_expired_quote_http(tmp_path, scenario):
    now = [10.0]
    with TestClient(create_app(db_path=tmp_path / "clock.db", catalog=FixtureCatalog(scenario), clock=lambda: now[0])) as client:
        quoted = advise(client, scenario).json()
        now[0] = 310.0
        res = client.post("/api/v2/commitments", json={"scenario_id": scenario["id"], "participant_id": "farmer",
                          "quote_id": quoted["quote_id"], "crop": "Ragi", "idempotency_key": "expired"})
        assert res.status_code == 409 and "expired" in res.json()["detail"]


def test_missing_artifact_fails_closed_without_legacy_fallback(tmp_path):
    with TestClient(create_app(db_path=tmp_path / "empty.db", active_path=tmp_path / "missing.json")) as client:
        response = client.get("/api/v2/locations")
        assert response.status_code == 503
        assert "validated" in response.json()["detail"].lower()


@pytest.mark.parametrize("missing_current_artifact", [False, True])
def test_persisted_acknowledgement_recovery_survives_active_artifact_retirement(tmp_path, scenario, missing_current_artifact):
    """Successful writes outlive catalog membership and quote expiry, without a second allocation."""
    path = tmp_path / "lifecycle.db"
    with TestClient(create_app(db_path=path, catalog=FixtureCatalog(scenario), clock=lambda: 10.0)) as first:
        quoted = advise(first, scenario).json()
        uncommitted = advise(first, scenario, "other").json()
        payload = {"scenario_id": scenario["id"], "participant_id": "farmer", "quote_id": quoted["quote_id"],
                   "crop": "Ragi", "idempotency_key": "original-request"}
        acknowledged = first.post("/api/v2/commitments", json=payload)
        assert acknowledged.status_code == 200
        original = acknowledged.json()
    replacement = deepcopy(scenario)
    replacement.update(id="new-artifact-scenario", artifact_id="revised-artifact")
    startup = {"active_path": tmp_path / "missing.json"} if missing_current_artifact else {
        "catalog": FixtureCatalog(replacement)}
    with TestClient(create_app(db_path=path, clock=lambda: 1000.0, **startup)) as restarted:
        retry = restarted.post("/api/v2/commitments", json=payload)
        assert retry.status_code == 200 and retry.json() == original
        persisted = restarted.get("/api/v2/state", params={"scenario_id": scenario["id"], "participant_id": "farmer"})
        assert persisted.status_code == 200
        assert persisted.json()["revision"] == 1
        assert persisted.json()["total_committed_area_ha"] == 1
        assert persisted.json()["commitment"]["id"] == original["commitment_id"]
        # Persisted recovery does not bypass ordinary validation for new writes.
        expired = restarted.post("/api/v2/commitments", json={**payload, "participant_id": "other",
                                 "quote_id": uncommitted["quote_id"], "idempotency_key": "not-committed-before"})
        assert expired.status_code == 409 and "expired" in expired.json()["detail"]
        assert restarted.get("/api/v2/state", params={"scenario_id": "unknown"}).status_code == 404
        assert restarted.post("/api/v2/commitments", json={**payload, "scenario_id": "unknown"}).status_code == 404
        if missing_current_artifact:
            assert restarted.get("/api/v2/locations").status_code == 503
            assert restarted.get("/api/v2/scenarios").status_code == 503
            assert advise(restarted, scenario).status_code == 503
        else:
            assert restarted.get("/api/v2/state", params={"scenario_id": replacement["id"]}).json()["total_committed_area_ha"] == 0
        cancelled = restarted.post(f'/api/v2/commitments/{original["commitment_id"]}/cancel',
                                   json={"participant_id": "farmer", "idempotency_key": "recover-cancel"})
        assert cancelled.status_code == 200
        assert cancelled.json()["state"]["total_committed_area_ha"] == 0
        assert cancelled.json()["revision"] == 2
        retry_cancel = restarted.post(f'/api/v2/commitments/{original["commitment_id"]}/cancel',
                                      json={"participant_id": "farmer", "idempotency_key": "recover-cancel"})
        assert retry_cancel.json() == cancelled.json()
