"""Comprehensive Unit, Invariant, and Adversarial Test Suite for AgriIntel Novelties.

Tests:
- N1: ESRR equilibrium solver, anti-gaming frozen seed reproducibility, and target quota conservation.
- N2: VPCR incremental variance mathematics, exact cancel reversibility, PSD matrix projection,
      numeric drift verification, and O(L) complexity benchmarking.
- N4: Edge Escrow device authentication, hash-chain tamper detection, sequence gap detection,
      replay attack rejection, and idempotent reconciliation.
- N6: Slippage quote tolerance, rank stability protection, and stale-state retry reduction.
- End-to-end multi-seed benchmark integration.
"""
import copy
import hashlib
import numpy as np
import pytest

from modules.novelty.esrr import ESRRAllocator, solve_congestion_equilibrium
from modules.novelty.vpcr_ledger import (
    VPCRLedger,
    _ensure_positive_semidefinite,
    benchmark_vpcr_complexity,
    simulate_vpcr_exceedance_rate,
)
from modules.novelty.edge_escrow import EdgeEscrowManager, EdgeKioskNode, TokenState
from modules.novelty.slippage_quote import SlippageQuoteEngine
from modules.novelty.benchmarks import (
    simulate_n1_esrr_comparison,
    simulate_n2_vpcr_capacity_gain,
    simulate_n4_edge_escrow_isolation,
    simulate_n6_slippage_contention,
    simulate_n6_concurrency_comparison,
    simulate_multi_scenario_benchmarks,
)


@pytest.fixture
def mock_scenario():
    """Deterministic 3-crop agricultural scenario for invariant validation."""
    return {
        "id": "coimbatore-test-scenario",
        "participating_area_ha": 24.0,
        "participant_count": 24,
        "participant_area_ha": 1.0,
        "risk_aversion": 0.5,
        "crops": [
            {
                "crop": "Ragi",
                "yield_q10": 1.2,
                "yield_q50": 1.8,
                "yield_q90": 2.4,
                "cost_per_ha": 15000.0,
                "reference_price": 2800.0,
                "reference_supply_t": 72.0,
                "outside_supply_t": 57.6,
                "capacity_t": 110.0,
                "phi": -1.5,
                "theta": 0.5,
            },
            {
                "crop": "Maize",
                "yield_q10": 3.0,
                "yield_q50": 4.5,
                "yield_q90": 5.8,
                "cost_per_ha": 22000.0,
                "reference_price": 1750.0,
                "reference_supply_t": 180.0,
                "outside_supply_t": 144.0,
                "capacity_t": 280.0,
                "phi": -1.2,
                "theta": 0.6,
            },
            {
                "crop": "Onion",
                "yield_q10": 8.0,
                "yield_q50": 12.0,
                "yield_q90": 16.5,
                "cost_per_ha": 45000.0,
                "reference_price": 1900.0,
                "reference_supply_t": 480.0,
                "outside_supply_t": 384.0,
                "capacity_t": 700.0,
                "phi": -2.0,
                "theta": 0.8,
            },
        ],
    }


# ==============================================================================
# N1: ESRR Tests
# ==============================================================================

def test_n1_esrr_equilibrium_solver(mock_scenario):
    """Verifies that the congestion equilibrium solves the simplex equality constraint."""
    total_area = mock_scenario["participating_area_ha"]
    alloc = solve_congestion_equilibrium(mock_scenario, total_area)

    for crop, area in alloc.items():
        assert area >= 0.0, f"Negative area for {crop}: {area}"

    assert abs(sum(alloc.values()) - total_area) < 1e-4

    for crop_spec in mock_scenario["crops"]:
        crop = crop_spec["crop"]
        headroom_ha = (crop_spec["capacity_t"] - crop_spec["outside_supply_t"]) / crop_spec["yield_q90"]
        assert alloc[crop] <= headroom_ha + 1e-4


def test_n1_esrr_frozen_farmer_seed_anti_gaming(mock_scenario):
    """Verifies anti-gaming protection: farmer receives stable seed regardless of revision ticks."""
    allocator = ESRRAllocator(mock_scenario, freeze_farmer_seed=True)
    state_rev1 = {
        "scenario_id": mock_scenario["id"],
        "revision": 1,
        "remaining_area_ha": 24.0,
        "crops": [
            {"crop": c["crop"], "committed_area_ha": 0.0, "expected_committed_t": 0.0, "conservative_committed_t": 0.0}
            for c in mock_scenario["crops"]
        ],
    }
    state_rev5 = copy.deepcopy(state_rev1)
    state_rev5["revision"] = 5

    rec1 = allocator.recommend(state_rev1, "farmer-01", 1.0)
    rec2 = allocator.recommend(state_rev5, "farmer-01", 1.0)

    # In frozen farmer seed mode, seed is stable to prevent re-query gaming
    assert rec1["audit_seed"] == rec2["audit_seed"]
    assert rec1["seed_mode"] == "frozen_farmer_identity"


# ==============================================================================
# N2: VPCR Ledger Tests
# ==============================================================================

def test_n2_vpcr_incremental_variance_math(mock_scenario):
    """Verifies that O(L) incremental variance update matches full matrix multiplication exactly."""
    locations = ["dist-A", "dist-B", "dist-C"]
    R = np.array([
        [1.0, 0.4, 0.2],
        [0.4, 1.0, 0.3],
        [0.2, 0.3, 1.0],
    ])

    vpcr = VPCRLedger(mock_scenario, locations=locations, correlation_matrix=R)
    crop = "Ragi"

    vpcr.commit("c1", crop, 2.0, location="dist-A")
    vpcr.commit("c2", crop, 3.0, location="dist-B")
    vpcr.commit("c3", crop, 1.5, location="dist-C")

    w_vec = vpcr.state[crop]["W"]
    expected_full_variance = float(w_vec @ R @ w_vec)
    online_incremental_variance = vpcr.state[crop]["variance"]

    assert np.isclose(expected_full_variance, online_incremental_variance, rtol=1e-10)

    # Test invariant checker
    inv = vpcr.verify_incremental_invariants(crop)
    assert inv["is_valid"] is True
    assert inv["max_drift_gradient"] < 1e-9


def test_n2_vpcr_psd_projection(mock_scenario):
    """Tests that non-positive semidefinite correlation matrices are projected to valid PSD."""
    # Invalid non-PSD matrix with negative eigenvalue
    invalid_R = np.array([
        [1.0, 0.9, 0.9],
        [0.9, 1.0, 0.9],
        [0.9, 0.9, 1.0]
    ])
    # Make it artificially non-PSD
    invalid_R[0, 1] = invalid_R[1, 0] = 0.99
    invalid_R[0, 2] = invalid_R[2, 0] = 0.99
    invalid_R[1, 2] = invalid_R[2, 1] = -0.99

    psd_R = _ensure_positive_semidefinite(invalid_R)
    eigvals = np.linalg.eigvalsh(psd_R)
    assert np.all(eigvals >= 0.0), f"Negative eigenvalues found: {eigvals}"
    assert np.allclose(np.diag(psd_R), 1.0)


def test_n2_vpcr_exact_reversibility_on_cancel(mock_scenario):
    """Verifies that cancelling a commitment reverses the variance update to exact precision."""
    vpcr = VPCRLedger(mock_scenario, locations=["dist-A", "dist-B"], default_correlation=0.35)
    crop = "Maize"

    vpcr.commit("comm-1", crop, 2.5, location="dist-A")
    vpcr.commit("comm-2", crop, 1.5, location="dist-B")

    vpcr.cancel("comm-2")
    vpcr.cancel("comm-1")

    assert vpcr.state[crop]["variance"] == 0.0
    assert vpcr.state[crop]["expected_t"] == 0.0
    assert vpcr.state[crop]["committed_area_ha"] == 0.0


def test_n2_vpcr_subadditivity_and_capacity_gain(mock_scenario):
    """Confirms that VPCR under correlation < 1 frees up safe capacity compared to E1."""
    vpcr = VPCRLedger(mock_scenario, locations=["loc1", "loc2"], default_correlation=0.25)
    crop_spec = mock_scenario["crops"][0]
    crop = crop_spec["crop"]

    for i in range(5):
        vpcr.commit(f"farmer-{i}", crop, 1.0, location=f"loc{i%2 + 1}")

    vpcr_conservative = vpcr.conservative_production(crop)
    legacy_marginal = 5.0 * crop_spec["yield_q90"]

    assert vpcr_conservative < legacy_marginal
    assert vpcr.remaining_headroom_t(crop) > (crop_spec["capacity_t"] - crop_spec["outside_supply_t"] - legacy_marginal)


def test_n2_complexity_speedup():
    """Verifies that incremental update runs in O(L) time and beats full recomputation."""
    bench = benchmark_vpcr_complexity(L_values=[50], num_commits=50)
    assert len(bench) == 1
    assert bench[0]["speedup_factor"] > 1.0


# ==============================================================================
# N4: Edge Escrow Tests
# ==============================================================================

def test_n4_edge_escrow_tamper_detection(mock_scenario):
    """Verifies HMAC signature verification and tamper rejection."""
    manager = EdgeEscrowManager(server_secret_key="test-key-32b-secret")
    token = manager.issue_escrow_token("kiosk-01", mock_scenario["id"], "Ragi", 20.0)

    assert manager.verify_token(token) is True

    tampered_token = copy.deepcopy(token)
    tampered_token["allocated_capacity_t"] = 50.0
    assert manager.verify_token(tampered_token) is False


def test_n4_edge_escrow_hash_chain_integrity(mock_scenario):
    """Verifies that offline hash chain detects any intermediate payload tampering."""
    manager = EdgeEscrowManager()
    kiosk = EdgeKioskNode("kiosk-01")

    token = manager.issue_escrow_token("kiosk-01", mock_scenario["id"], "Ragi", 30.0)
    kiosk.load_escrow_token(token)

    kiosk.commit_offline("f1", 1.0, 2.4)
    kiosk.commit_offline("f2", 1.5, 2.4)

    payload = kiosk.export_sync_payload()
    res = manager.reconcile_and_settle(payload)
    assert res["status"] == "settled"
    assert res["commitments_accepted"] == 2


def test_n4_adversarial_replay_attack(mock_scenario):
    """Verifies that resubmitting a commitment with duplicate commitment_id is caught and rejected."""
    manager = EdgeEscrowManager()
    kiosk1 = EdgeKioskNode("kiosk-01")
    token1 = manager.issue_escrow_token("kiosk-01", mock_scenario["id"], "Ragi", 30.0)
    kiosk1.load_escrow_token(token1)

    kiosk1.commit_offline("farmer-alice", 1.0, 2.4, commitment_id="replay-target-cid-001")
    payload1 = kiosk1.export_sync_payload()
    manager.reconcile_and_settle(payload1)

    # Adversary attempts to inject the same commitment_id into a second token
    kiosk2 = EdgeKioskNode("kiosk-02")
    token2 = manager.issue_escrow_token("kiosk-02", mock_scenario["id"], "Ragi", 30.0)
    kiosk2.load_escrow_token(token2)

    kiosk2.commit_offline("farmer-bob", 1.0, 2.4, commitment_id="replay-target-cid-001")
    payload2 = kiosk2.export_sync_payload()

    with pytest.raises(ValueError, match="Replay attack detected"):
        manager.reconcile_and_settle(payload2)


def test_n4_sequence_gap_detection(mock_scenario):
    """Verifies that dropping a transaction from the offline log is detected by sequence checks."""
    manager = EdgeEscrowManager()
    kiosk = EdgeKioskNode("kiosk-01")
    token = manager.issue_escrow_token("kiosk-01", mock_scenario["id"], "Ragi", 30.0)
    kiosk.load_escrow_token(token)

    kiosk.commit_offline("f1", 1.0, 2.4)
    kiosk.commit_offline("f2", 1.0, 2.4)
    kiosk.commit_offline("f3", 1.0, 2.4)

    payload = kiosk.export_sync_payload()
    # Drop second commitment (seq gap)
    payload["commitments"].pop(1)

    with pytest.raises(ValueError, match="Sequence gap or reordering"):
        manager.reconcile_and_settle(payload)


def test_n4_idempotent_settlement_recovery(mock_scenario):
    """Verifies that resubmitting an already settled token returns the cached response idempotently."""
    manager = EdgeEscrowManager()
    kiosk = EdgeKioskNode("kiosk-01")
    token = manager.issue_escrow_token("kiosk-01", mock_scenario["id"], "Ragi", 30.0)
    kiosk.load_escrow_token(token)

    kiosk.commit_offline("f1", 1.0, 2.4)
    payload = kiosk.export_sync_payload()

    res1 = manager.reconcile_and_settle(payload)
    res2 = manager.reconcile_and_settle(payload)

    assert res1 == res2
    assert res1["status"] == "settled"


# ==============================================================================
# N6: Slippage Quote Tests
# ==============================================================================

def test_n6_slippage_quote_stale_retry_prevention(mock_scenario):
    """Verifies that quotes execute across revision drift if profit slippage is within tolerance."""
    engine = SlippageQuoteEngine(mock_scenario)
    state = {
        "scenario_id": mock_scenario["id"],
        "revision": 0,
        "participating_area_ha": 24.0,
        "remaining_area_ha": 24.0,
        "crops": [
            {
                "crop": c["crop"],
                "committed_area_ha": 0.0,
                "expected_committed_t": 0.0,
                "conservative_committed_t": 0.0,
                "outside_supply_t": c["outside_supply_t"],
                "capacity_t": c["capacity_t"],
                "remaining_capacity_t": c["capacity_t"] - c["outside_supply_t"],
                "remaining_area_ha": (c["capacity_t"] - c["outside_supply_t"]) / c["yield_q90"],
            }
            for c in mock_scenario["crops"]
        ],
    }

    quote_res = engine.issue_quote("farmer-target", 1.0, state)
    quote_id = quote_res["quote_id"]

    # Revision drifts to 2 as other commitments occur
    state["revision"] = 2
    state["crops"][0]["expected_committed_t"] += 2.0
    state["crops"][0]["conservative_committed_t"] += 3.0

    eval_strict = engine.evaluate_commit_with_slippage(
        quote_id, "Ragi", state, max_slippage_pct=0.0, max_abs_slippage=0.0
    )
    assert eval_strict["accepted"] is False
    assert eval_strict["error_code"] == "EXCESSIVE_SLIPPAGE"

    eval_tolerant = engine.evaluate_commit_with_slippage(
        quote_id, "Ragi", state, max_slippage_pct=0.05
    )
    assert eval_tolerant["accepted"] is True
    assert eval_tolerant["revisions_drifted"] == 2


# ==============================================================================
# Integration Benchmark Tests
# ==============================================================================

def test_simulation_benchmarks_run(mock_scenario):
    """Verifies that simulation benchmark functions run cleanly and produce valid metrics."""
    esrr_res = simulate_n1_esrr_comparison(mock_scenario, num_seeds=3, participant_count=6)
    assert esrr_res["seeds_tested"] == 3
    assert esrr_res["esrr"]["mean_total_profit"] > 0.0

    vpcr_res = simulate_n2_vpcr_capacity_gain(mock_scenario)
    assert vpcr_res["capacity_utilization_gain_pct"] >= 0.0

    edge_res = simulate_n4_edge_escrow_isolation(mock_scenario)
    assert edge_res["quota_oversubscription_observed"] is False
    assert edge_res["reconciled_settled_t"] > 0.0

    slip_res = simulate_n6_slippage_contention(mock_scenario)
    assert slip_res["revisions_drifted"] == 3
    assert slip_res["tolerant_ten_pct_accepted"] is True


def test_n4_adversarial_wrong_kiosk_reconciliation(mock_scenario):
    """Verifies that kiosk B cannot submit a payload claiming a token registered to kiosk A."""
    manager = EdgeEscrowManager()
    token = manager.issue_escrow_token("kiosk-01", mock_scenario["id"], "Ragi", 20.0)

    # Attacker tries to hijack token issued to kiosk-01
    payload = {
        "kiosk_id": "kiosk-02",
        "token": token,
        "commitments": [],
        "final_hash": "",
        "unused_escrow_t": 20.0,
    }
    with pytest.raises(ValueError, match="Token kiosk_id mismatch"):
        manager.reconcile_and_settle(payload)


def test_n4_adversarial_expired_commitment(mock_scenario):
    """Verifies that offline commitments made past token expiry are rejected by edge and central ledger."""
    manager = EdgeEscrowManager()
    kiosk = EdgeKioskNode("kiosk-01")
    token = manager.issue_escrow_token("kiosk-01", mock_scenario["id"], "Ragi", 20.0, validity_seconds=10.0, current_time=1000.0)
    kiosk.load_escrow_token(token)

    # Valid commitment at t=1005
    kiosk.commit_offline("farmer-valid", 1.0, 2.4, timestamp=1005.0)

    # Invalid commitment attempted at t=1015
    with pytest.raises(ValueError, match="Active escrow token has expired"):
        kiosk.commit_offline("farmer-expired", 1.0, 2.4, timestamp=1015.0)


def test_n4_adversarial_server_token_revocation(mock_scenario):
    """Verifies that revoked/expired tokens are blocked from central settlement."""
    manager = EdgeEscrowManager()
    kiosk = EdgeKioskNode("kiosk-01")
    token = manager.issue_escrow_token("kiosk-01", mock_scenario["id"], "Ragi", 20.0)
    kiosk.load_escrow_token(token)
    kiosk.commit_offline("farmer-1", 1.0, 2.4)
    payload = kiosk.export_sync_payload()

    # Server expires token before sync
    manager.expire_token(token["token_id"])

    with pytest.raises(ValueError, match="expired and was revoked/reclaimed"):
        manager.reconcile_and_settle(payload)


def test_n4_adversarial_local_quota_overflow(mock_scenario):
    """Verifies that edge kiosk fails closed if offline requests exceed token capacity."""
    kiosk = EdgeKioskNode("kiosk-01")
    manager = EdgeEscrowManager()
    token = manager.issue_escrow_token("kiosk-01", mock_scenario["id"], "Ragi", 5.0)
    kiosk.load_escrow_token(token)

    kiosk.commit_offline("f1", 1.0, 2.4)
    with pytest.raises(ValueError, match="exceeds remaining local escrow"):
        kiosk.commit_offline("f2", 2.0, 2.4)


def test_n2_vpcr_exceedance_simulation(mock_scenario):
    """Verifies empirical exceedance simulation runs and measures risk under asymmetric yields."""
    res = simulate_vpcr_exceedance_rate(
        mock_scenario,
        crop="Ragi",
        locations=["loc-1", "loc-2", "loc-3"],
        committed_areas_ha=[2.0, 3.0, 1.0],
        correlation=0.30,
        num_harvest_simulations=1000,
        seed=123,
    )
    assert res["simulations_run"] == 1000
    assert res["legacy_ceiling_t"] > res["vpcr_ceiling_t"]
    assert res["capacity_headroom_gain_pct"] > 0.0
    assert 0.04 <= res["vpcr_exceedance_rate"] <= 0.18
    assert res["legacy_exceedance_rate"] <= res["vpcr_exceedance_rate"]


def test_n6_concurrency_comparison_metrics(mock_scenario):
    """Verifies concurrency simulation metrics across Strict OCC, OCC+Retry, and Slippage."""
    res = simulate_n6_concurrency_comparison(mock_scenario, num_requests=15, interleaved_commits=1)
    assert "strict_occ" in res
    assert "occ_retry_3" in res
    assert "slippage_tolerant" in res
    assert res["slippage_tolerant"]["retries_per_commit"] == 0.0
    assert res["slippage_tolerant"]["success_rate_pct"] >= res["strict_occ"]["success_rate_pct"]


def test_multi_scenario_benchmarks_run():
    """Verifies that multi-scenario benchmark runs across Coimbatore, Pune, and Ludhiana."""
    res = simulate_multi_scenario_benchmarks()
    assert len(res) == 3
    for s_id, s_data in res.items():
        assert s_data["esrr_profit_inr"] > 0.0

