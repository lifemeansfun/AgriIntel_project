from copy import deepcopy

from modules.regional.economics import evaluate_final
from modules.regional.ledger import RegionalLedger
from modules.regional.replay import ReplayService
from test_regional_ledger import scenario, ledger
from test_regional_api import client


def complete(service, replay):
    for _ in range(replay["total_steps"]):
        replay = service.step(replay["id"])
    return replay


def comparable(body):
    result = deepcopy(body)
    result.pop("id")
    return result


def test_seed_reproduction_persistence_and_isolation(ledger, scenario):
    service = ReplayService(ledger)
    first = complete(service, service.create(scenario, 42))
    second = complete(service, service.create(scenario, 42))
    assert comparable(first) == comparable(second)
    assert first["status"] == "completed" and first["step"] == 24
    assert RegionalLedger(ledger.path).state(scenario["id"])["total_committed_area_ha"] == 0
    restarted = ReplayService(RegionalLedger(ledger.path))
    assert restarted.get(first["id"]) == first
    assert restarted.step(first["id"]) == first
    for policy in ("static", "dynamic"):
        state = first[f"{policy}_state"]
        assert state["total_committed_area_ha"] <= scenario["participating_area_ha"]
        for row in state["crops"]:
            assert row["outside_supply_t"] + row["conservative_committed_t"] <= row["capacity_t"] + 1e-9
        assert {k: v for k, v in first["summary"][policy].items() if k != "rejected_count"} == evaluate_final(scenario, state)
        assert sum(r["profit"] for r in first["summary"][policy]["participant_profits"]) == first["summary"][policy]["total_profit"]


def test_replay_config_participant_count_and_area(ledger, scenario):
    configured = deepcopy(scenario)
    configured.update(participant_count=3, participant_area_ha=2.0)
    body = complete(ReplayService(ledger), ReplayService(ledger).create(configured))
    assert body["total_steps"] == 3
    assert body["static_state"]["total_committed_area_ha"] == 6
    assert body["dynamic_state"]["total_committed_area_ha"] == 6


def test_api_replay_routes(client):
    created = client.post("/api/v2/replays", json={"seed": 42})
    assert created.status_code == 200
    body = created.json()
    assert body["status"] == "ready"
    assert client.get(f'/api/v2/replays/{body["id"]}').json() == body
    stepped = client.post(f'/api/v2/replays/{body["id"]}/step').json()
    assert stepped["step"] == 1
    assert len(stepped["decisions"]) == 1
