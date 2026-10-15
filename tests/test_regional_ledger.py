"""Durability, identity, concurrency and quote contracts use temporary SQLite only."""
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
import sqlite3

import pytest

from modules.regional.economics import recommend
from modules.regional.ledger import LedgerError, RegionalLedger


@pytest.fixture
def scenario():
    return {"id": "test-region", "name": "Test", "state": "Tamil Nadu", "district": "Coimbatore",
            "season": "Kharif", "year": 2019, "artifact_id": "test-artifact", "participating_area_ha": 24.0,
            "risk_aversion": .5, "crops": [
                {"crop": name, "yield_q10": y * .7, "yield_q50": y, "yield_q90": y * 1.2,
                 "reference_price": p, "cost_per_ha": 1000.0, "reference_supply_t": 40 * y,
                 "outside_supply_t": 32 * y, "capacity_t": 44 * y, "phi": -1.0, "theta": 1.0}
                for name, y, p in [("Ragi", 2.0, 1000.0), ("Maize", 3.0, 900.0), ("Onion", 5.0, 600.0)]]}


@pytest.fixture
def ledger(tmp_path, scenario):
    instance = RegionalLedger(tmp_path / "ledger.db")
    instance.ensure_scenario(scenario)
    return instance


def quote(ledger, scenario, participant="farmer", area=1.0):
    state = ledger.state(scenario["id"], participant)
    rows = recommend(scenario, state, area)
    return ledger.issue_quote(scenario["id"], participant, area, state["revision"], rows)


def commit_one(ledger, scenario, participant="farmer", crop="Ragi", area=1.0, key="once"):
    q = quote(ledger, scenario, participant, area)
    return ledger.commit(scenario["id"], participant, q["quote_id"], crop, key)


def test_browsing_and_quotes_never_reserve(ledger, scenario):
    before = ledger.state(scenario["id"])
    for _ in range(10):
        quote(ledger, scenario)
    assert ledger.state(scenario["id"]) == before


def test_retry_restart_and_exact_cancel(ledger, scenario):
    q = quote(ledger, scenario, area=.7)
    result = ledger.commit(scenario["id"], "farmer", q["quote_id"], "Ragi", "same")
    restarted = RegionalLedger(ledger.path)
    assert restarted.commit(scenario["id"], "farmer", q["quote_id"], "Ragi", "same") == result
    with pytest.raises(LedgerError, match="different input"):
        restarted.commit(scenario["id"], "farmer", q["quote_id"], "Onion", "same")
    with pytest.raises(LedgerError, match="another participant"):
        restarted.cancel(result["commitment_id"], "other", "cancel")
    cancelled = restarted.cancel(result["commitment_id"], "farmer", "cancel")
    assert cancelled["revision"] == 2
    assert cancelled["state"]["total_committed_area_ha"] == 0
    assert all(c["conservative_committed_t"] == 0 for c in cancelled["state"]["crops"])
    assert restarted.cancel(result["commitment_id"], "farmer", "cancel") == cancelled
    assert restarted.cancel(result["commitment_id"], "farmer", "another-cancel")["revision"] == 2
    with restarted.connect() as db:
        assert db.execute("SELECT count(*) FROM events").fetchone()[0] == 2
        assert db.execute("PRAGMA synchronous").fetchone()[0] == 2


def test_quote_expiry_binding_and_one_active(ledger, scenario):
    ledger.clock = lambda: 10.0
    q = quote(ledger, scenario)
    ledger.clock = lambda: 310.0
    with pytest.raises(LedgerError, match="expired"):
        ledger.commit(scenario["id"], "farmer", q["quote_id"], "Ragi", "expired")
    ledger.clock = lambda: 20.0
    q = quote(ledger, scenario)
    with pytest.raises(LedgerError, match="not valid"):
        ledger.commit(scenario["id"], "other", q["quote_id"], "Ragi", "wrong")
    ledger.commit(scenario["id"], "farmer", q["quote_id"], "Ragi", "valid")
    q2 = quote(ledger, scenario)
    with pytest.raises(LedgerError, match="already has"):
        ledger.commit(scenario["id"], "farmer", q2["quote_id"], "Onion", "duplicate")


@pytest.mark.parametrize("area", [0, -1, float("nan"), float("inf"), True, None])
def test_invalid_area(ledger, scenario, area):
    with pytest.raises((LedgerError, ValueError)):
        ledger.issue_quote(scenario["id"], "bad", area, 0, [])


def test_stale_quote_and_scenario_isolation(ledger, scenario):
    stale = quote(ledger, scenario, "late")
    commit_one(ledger, scenario)
    with pytest.raises(LedgerError, match="stale"):
        ledger.commit(scenario["id"], "late", stale["quote_id"], "Ragi", "stale")
    isolated = deepcopy(scenario)
    isolated["id"] = "isolated"
    ledger.ensure_scenario(isolated)
    assert ledger.state("isolated")["total_committed_area_ha"] == 0
    changed = deepcopy(scenario)
    changed["participating_area_ha"] = 99
    with pytest.raises(LedgerError, match="configuration changed"):
        ledger.ensure_scenario(changed)


def _process_worker(args):
    path, scenario, i = args
    ledger = RegionalLedger(path)
    # Refresh on legitimate optimistic-concurrency conflicts, as the client must.
    for attempt in range(50):
        try:
            return commit_one(ledger, scenario, f"farmer-{i}", area=1, key=f"k-{i}")["commitment_id"]
        except LedgerError as err:
            if "stale" in str(err) or "while quoting" in str(err):
                continue
            return None
    raise AssertionError("Concurrency retry budget exhausted")


def test_cross_process_capacity_and_area(ledger, scenario):
    # Two independent OS processes share one durable capacity constraint.
    with ProcessPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(_process_worker, [(ledger.path, scenario, i) for i in range(20)]))
    state = ledger.state(scenario["id"])
    # Ragi capacity: (44*2 - 32*2)/(2*1.2) = 10 hectares.
    assert sum(r is not None for r in results) == 10
    assert state["total_committed_area_ha"] == 10
    ragi = next(c for c in state["crops"] if c["crop"] == "Ragi")
    assert ragi["conservative_committed_t"] + ragi["outside_supply_t"] <= ragi["capacity_t"] + 1e-9
    with ledger.connect() as db:
        assert db.execute("SELECT count(*) FROM events").fetchone()[0] == 10


def test_failed_transaction_has_no_acknowledged_or_partial_commit(ledger, scenario):
    with ledger.connect() as db:
        db.execute("CREATE TRIGGER reject_event BEFORE INSERT ON events BEGIN SELECT RAISE(ABORT, 'simulated write failure'); END")
    with pytest.raises(sqlite3.IntegrityError):
        commit_one(ledger, scenario)
    assert ledger.state(scenario["id"])["revision"] == 0
    assert ledger.state(scenario["id"])["total_committed_area_ha"] == 0
    with ledger.connect() as db:
        assert db.execute("SELECT count(*) FROM requests").fetchone()[0] == 0


@pytest.mark.parametrize("field,bad", [("yield_q90", 0), ("yield_q90", float("inf")),
    ("yield_q10", -1), ("outside_supply_t", -1), ("outside_supply_t", 99999),
    ("reference_supply_t", 0), ("reference_price", float("nan")), ("phi", 0), ("theta", 1.1)])
def test_reject_invalid_scenario_before_persistence(tmp_path, scenario, field, bad):
    scenario["crops"][0][field] = bad
    ledger = RegionalLedger(tmp_path / "invalid.db")
    with pytest.raises(LedgerError, match="Invalid scenario"):
        ledger.ensure_scenario(scenario)
    with ledger.connect() as db:
        assert db.execute("SELECT count(*) FROM scenarios").fetchone()[0] == 0


def test_total_area_budget_is_independent_of_crop_headroom(tmp_path, scenario):
    scenario["participating_area_ha"] = 2.0
    ledger = RegionalLedger(tmp_path / "global-limit.db")
    ledger.ensure_scenario(scenario)
    commit_one(ledger, scenario, "first", "Ragi")
    commit_one(ledger, scenario, "second", "Maize")
    q = quote(ledger, scenario, "third")
    with pytest.raises(LedgerError, match="exceeds remaining"):
        ledger.commit(scenario["id"], "third", q["quote_id"], "Onion", "third")
    assert ledger.state(scenario["id"])["total_committed_area_ha"] == 2.0
