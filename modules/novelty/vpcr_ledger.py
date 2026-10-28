"""N2: Variance-Pooled Correlated Capacity Reservation (VPCR).

Replaces sum-of-marginals capacity reservation with an aggregate spatial
portfolio variance model (W^T R W), maintaining online state via O(L) incremental
updates with periodic drift bounding.

Statistical & Methodological Assumptions:
1. Aggregate harvest risk uses upper semi-deviation sigma_upper = (y90 - y50) / z_0.90
   under an asymptotic central limit approximation for aggregate correlated harvest volume.
2. When spatial correlation rho = 1, conservative production recovers the legacy
   sum-of-marginals upper quantile sum(a_i * y90) as an upper physical ceiling.
3. The spatial correlation matrix R is enforced to be symmetric and positive semi-definite (PSD).
"""
from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Optional
import numpy as np

from modules.regional.economics import finite_number


def _ensure_positive_semidefinite(matrix: np.ndarray, min_eigenval: float = 1e-6) -> np.ndarray:
    """Projects matrix to the nearest symmetric positive semi-definite correlation matrix."""
    # Symmetrize
    sym = 0.5 * (matrix + matrix.T)
    # Unit diagonal
    np.fill_diagonal(sym, 1.0)

    # Eigenvalue decomposition
    eigvals, eigvecs = np.linalg.eigh(sym)
    if np.all(eigvals >= min_eigenval):
        return sym

    # Clip negative/small eigenvalues
    clipped = np.maximum(eigvals, min_eigenval)
    reconstructed = eigvecs @ np.diag(clipped) @ eigvecs.T

    # Rescale to unit diagonal
    inv_sqrt_diag = 1.0 / np.sqrt(np.maximum(1e-12, np.diag(reconstructed)))
    corr = inv_sqrt_diag[:, None] * reconstructed * inv_sqrt_diag[None, :]
    np.fill_diagonal(corr, 1.0)
    return corr


class VPCRLedger:
    """Variance-Pooled Correlated Capacity Reservation Ledger.

    Maintains online updates of expected production and aggregate portfolio
    variance for each crop across spatially correlated locations in O(L) time.
    """

    def __init__(
        self,
        scenario: dict,
        locations: Optional[List[str]] = None,
        correlation_matrix: Optional[np.ndarray] = None,
        default_correlation: float = 0.35,
        z_score: float = 1.28155,  # 90th percentile of standard normal
    ):
        self.scenario = scenario
        self.crops = {c["crop"]: c for c in scenario["crops"]}
        self.z_score = finite_number(z_score, "z_score", positive=True)

        # Spatial locations setup
        self.locations = list(locations) if locations else ["loc-central"]
        self.loc_to_idx = {loc: i for i, loc in enumerate(self.locations)}
        n_locs = len(self.locations)

        if correlation_matrix is not None:
            if correlation_matrix.shape != (n_locs, n_locs):
                raise ValueError(f"Correlation matrix must be ({n_locs}, {n_locs})")
            self.R = _ensure_positive_semidefinite(np.array(correlation_matrix, dtype=np.float64))
        else:
            # Construct correlation matrix with default inter-location correlation
            R = np.full((n_locs, n_locs), default_correlation, dtype=np.float64)
            np.fill_diagonal(R, 1.0)
            self.R = _ensure_positive_semidefinite(R)

        # Internal state per crop:
        # - expected_t: float
        # - weights W: (n_locs,) float array representing sum of (a_i * sigma_i)
        # - grad G: (n_locs,) float array = R @ W
        # - variance: float = W @ R @ W
        self.state: Dict[str, Dict[str, Any]] = {}
        for crop_name in self.crops:
            self.state[crop_name] = {
                "expected_t": 0.0,
                "W": np.zeros(n_locs, dtype=np.float64),
                "G": np.zeros(n_locs, dtype=np.float64),
                "variance": 0.0,
                "committed_area_ha": 0.0,
                "op_count": 0,
            }

        # Active commitments: id -> dict
        self.commitments: Dict[str, Dict[str, Any]] = {}

    def _get_loc_index(self, location: Optional[str]) -> int:
        if location is None:
            return 0
        if location not in self.loc_to_idx:
            idx = len(self.locations)
            self.locations.append(location)
            self.loc_to_idx[location] = idx
            n = len(self.locations)
            new_R = np.full((n, n), 0.35, dtype=np.float64)
            new_R[: n - 1, : n - 1] = self.R
            np.fill_diagonal(new_R, 1.0)
            self.R = _ensure_positive_semidefinite(new_R)
            for crop_name in self.crops:
                s = self.state[crop_name]
                s["W"] = np.pad(s["W"], (0, 1))
                s["G"] = self.R @ s["W"]
            return idx
        return self.loc_to_idx[location]

    def compute_dispersion(self, crop: str, y10: float, y50: float, y90: float) -> float:
        """Estimates upper-tail semi-deviation from upper quantile spread (q90 - q50).

        Using upper semi-deviation ensures that when correlation rho = 1,
        conservative production recovers sum(y90) as an exact upper physical ceiling.
        """
        upper_spread = max(0.001, y90 - y50)
        sigma = upper_spread / self.z_score
        return float(sigma)

    def conservative_production(self, crop: str) -> float:
        """Returns the conservative portfolio quantile: mu + z * sigma_portfolio."""
        s = self.state[crop]
        std_dev = math.sqrt(max(0.0, s["variance"]))
        return float(s["expected_t"] + self.z_score * std_dev)

    def remaining_headroom_t(self, crop: str) -> float:
        """Headroom in tonnes under VPCR portfolio quantile."""
        spec = self.crops[crop]
        capacity = spec["capacity_t"]
        outside = spec["outside_supply_t"]
        conservative = self.conservative_production(crop)
        return max(0.0, capacity - outside - conservative)

    def remaining_area_ha(self, crop: str) -> float:
        """Remaining capacity converted to eligible hectares based on conservative marginal."""
        spec = self.crops[crop]
        headroom_t = self.remaining_headroom_t(crop)
        return max(0.0, headroom_t / spec["yield_q90"]) if spec["yield_q90"] > 0 else 0.0

    def simulate_commitment(
        self,
        crop: str,
        area_ha: float,
        location: Optional[str] = None,
    ) -> Dict[str, float]:
        """O(L) projection of the resulting conservative production if committed."""
        spec = self.crops[crop]
        s = self.state[crop]
        loc_idx = self._get_loc_index(location)

        area = finite_number(area_ha, "area_ha", positive=True)
        sigma_per_ha = self.compute_dispersion(
            crop, spec["yield_q10"], spec["yield_q50"], spec["yield_q90"]
        )

        delta_w = area * sigma_per_ha
        delta_expected = area * spec["yield_q50"]

        # delta_var = 2 * delta_w * G[loc_idx] + delta_w^2 * R[loc_idx, loc_idx]
        delta_var = 2.0 * delta_w * s["G"][loc_idx] + (delta_w ** 2) * self.R[loc_idx, loc_idx]
        new_var = max(0.0, s["variance"] + delta_var)
        new_expected = s["expected_t"] + delta_expected

        new_conservative = new_expected + self.z_score * math.sqrt(new_var)
        remaining = spec["capacity_t"] - spec["outside_supply_t"] - new_conservative

        return {
            "new_expected_t": new_expected,
            "new_conservative_t": new_conservative,
            "new_headroom_t": remaining,
            "eligible": remaining >= -1e-9,
        }

    def commit(
        self,
        commitment_id: str,
        crop: str,
        area_ha: float,
        location: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Atomically registers a commitment via O(L) incremental variance update."""
        if commitment_id in self.commitments:
            raise ValueError(f"Commitment {commitment_id} already exists")

        sim = self.simulate_commitment(crop, area_ha, location)
        if not sim["eligible"]:
            raise ValueError(f"Commitment exceeds VPCR capacity for {crop}")

        spec = self.crops[crop]
        s = self.state[crop]
        loc_idx = self._get_loc_index(location)
        area = float(area_ha)
        sigma = self.compute_dispersion(
            crop, spec["yield_q10"], spec["yield_q50"], spec["yield_q90"]
        )
        delta_w = area * sigma
        delta_expected = area * spec["yield_q50"]

        # Incremental update: O(L)
        delta_var = 2.0 * delta_w * s["G"][loc_idx] + (delta_w ** 2) * self.R[loc_idx, loc_idx]
        s["variance"] = max(0.0, s["variance"] + delta_var)
        s["expected_t"] += delta_expected
        s["W"][loc_idx] += delta_w
        s["G"] += delta_w * self.R[:, loc_idx]
        s["committed_area_ha"] += area
        s["op_count"] += 1

        record = {
            "commitment_id": commitment_id,
            "crop": crop,
            "area_ha": area,
            "location": self.locations[loc_idx],
            "loc_idx": loc_idx,
            "delta_w": delta_w,
            "delta_expected": delta_expected,
        }
        self.commitments[commitment_id] = record

        # Periodic drift prevention: recompute exactly after every 500 operations
        if s["op_count"] % 500 == 0:
            self.recompute_state(crop)

        return {
            "status": "committed",
            "conservative_t": self.conservative_production(crop),
            "headroom_t": self.remaining_headroom_t(crop),
            "state": record,
        }

    def cancel(self, commitment_id: str) -> Dict[str, Any]:
        """Atomically cancels a commitment, restoring variance and gradient within numeric tolerance."""
        if commitment_id not in self.commitments:
            raise KeyError(f"Commitment {commitment_id} not found")

        record = self.commitments.pop(commitment_id)
        crop = record["crop"]
        s = self.state[crop]
        loc_idx = record["loc_idx"]
        delta_w = record["delta_w"]
        delta_expected = record["delta_expected"]

        # Exact reversal of the gradient and variance update
        s["W"][loc_idx] -= delta_w
        s["G"] -= delta_w * self.R[:, loc_idx]
        delta_var = 2.0 * delta_w * s["G"][loc_idx] + (delta_w ** 2) * self.R[loc_idx, loc_idx]
        s["variance"] = max(0.0, s["variance"] - delta_var)
        s["expected_t"] = max(0.0, s["expected_t"] - delta_expected)
        s["committed_area_ha"] = max(0.0, s["committed_area_ha"] - record["area_ha"])
        s["op_count"] += 1

        # Numerical reset guard when empty or near zero
        active_for_crop = [c for c in self.commitments.values() if c["crop"] == crop]
        if len(active_for_crop) == 0:
            s["variance"] = 0.0
            s["expected_t"] = 0.0
            s["W"].fill(0.0)
            s["G"].fill(0.0)
            s["committed_area_ha"] = 0.0
        elif s["op_count"] % 100 == 0:
            self.recompute_state(crop)

        return {
            "status": "cancelled",
            "cancelled_id": commitment_id,
            "conservative_t": self.conservative_production(crop),
            "headroom_t": self.remaining_headroom_t(crop),
        }

    def recompute_state(self, crop: str) -> None:
        """Full O(L^2) recalculation from active commitments to eliminate accumulated floating point drift."""
        s = self.state[crop]
        n_locs = len(self.locations)
        W_new = np.zeros(n_locs, dtype=np.float64)
        expected_new = 0.0
        area_new = 0.0

        for c in self.commitments.values():
            if c["crop"] == crop:
                loc_idx = c["loc_idx"]
                W_new[loc_idx] += c["delta_w"]
                expected_new += c["delta_expected"]
                area_new += c["area_ha"]

        G_new = self.R @ W_new
        variance_new = float(W_new @ G_new)

        s["W"] = W_new
        s["G"] = G_new
        s["variance"] = max(0.0, variance_new)
        s["expected_t"] = expected_new
        s["committed_area_ha"] = area_new

    def verify_incremental_invariants(self, crop: str) -> Dict[str, float]:
        """Checks agreement between maintained incremental state and ground-truth matrix math."""
        s = self.state[crop]
        expected_G = self.R @ s["W"]
        expected_var = float(s["W"] @ self.R @ s["W"])

        drift_G = float(np.max(np.abs(s["G"] - expected_G)))
        drift_var = float(abs(s["variance"] - expected_var))

        return {
            "max_drift_gradient": drift_G,
            "drift_variance": drift_var,
            "is_valid": bool(drift_G < 1e-9 and drift_var < 1e-9),
        }


def benchmark_vpcr_complexity(
    L_values: Optional[List[int]] = None,
    num_commits: int = 100,
) -> List[Dict[str, Any]]:
    """Microbenchmark comparing O(L) incremental update vs O(L^2) full recomputation."""
    if L_values is None:
        L_values = [10, 50, 100, 250, 500]

    scenario = {
        "crops": [
            {
                "crop": "TestCrop", "yield_q10": 1.0, "yield_q50": 2.0, "yield_q90": 3.0,
                "capacity_t": 1e9, "outside_supply_t": 0.0, "cost_per_ha": 1000.0,
            }
        ]
    }

    results = []
    for L in L_values:
        locations = [f"loc-{i}" for i in range(L)]
        R = np.full((L, L), 0.30, dtype=np.float64)
        np.fill_diagonal(R, 1.0)

        ledger = VPCRLedger(scenario, locations=locations, correlation_matrix=R)

        # Time O(L) incremental commits
        t0 = time.perf_counter()
        for i in range(num_commits):
            loc = locations[i % L]
            ledger.commit(f"comm-{i}", "TestCrop", 1.0, location=loc)
        t_incremental = time.perf_counter() - t0

        # Time O(L^2) full matrix recomputations
        t0 = time.perf_counter()
        for _ in range(num_commits):
            ledger.recompute_state("TestCrop")
        t_full = time.perf_counter() - t0

        speedup = t_full / max(1e-9, t_incremental)
        results.append({
            "locations_L": L,
            "commits_measured": num_commits,
            "time_incremental_sec": t_incremental,
            "time_full_recompute_sec": t_full,
            "speedup_factor": speedup,
        })

    return results


def simulate_vpcr_exceedance_rate(
    scenario: dict,
    crop: str,
    locations: List[str],
    committed_areas_ha: List[float],
    correlation: float = 0.35,
    num_harvest_simulations: int = 5000,
    seed: int = 42,
) -> Dict[str, Any]:
    """Empirically evaluates exceedance risk on simulated harvests with asymmetric yields.

    Validates Section 4.4 of Patent Remediation Plan:
    1. Uses a Gaussian Copula to generate spatially correlated location yields.
    2. Calibrates marginal distributions to the asymmetric quantiles (y10, y50, y90).
    3. Evaluates how frequently realized aggregate harvest exceeds the VPCR ceiling
       vs the legacy sum-of-quantiles ceiling (sum a_i * y90).
    4. Reports exceedance frequency with 95% confidence intervals and capacity gain.
    """
    spec = next(c for c in scenario["crops"] if c["crop"] == crop)
    y10, y50, y90 = float(spec["yield_q10"]), float(spec["yield_q50"]), float(spec["yield_q90"])
    n_locs = len(locations)

    if len(committed_areas_ha) != n_locs:
        raise ValueError("committed_areas_ha length must match locations count")

    areas = np.array(committed_areas_ha, dtype=np.float64)
    total_area = float(np.sum(areas))

    # Construct and project correlation matrix
    R = np.full((n_locs, n_locs), correlation, dtype=np.float64)
    np.fill_diagonal(R, 1.0)
    R = _ensure_positive_semidefinite(R)

    # Instantiate VPCR ledger and commit
    ledger = VPCRLedger(scenario, locations=locations, correlation_matrix=R)
    for loc, a in zip(locations, areas):
        if a > 0:
            ledger.commit(f"eval-{loc}", crop, a, location=loc)

    vpcr_ceiling = ledger.conservative_production(crop)
    legacy_ceiling = float(total_area * y90)

    # Cholesky decomposition of correlation matrix for Gaussian Copula
    L_chol = np.linalg.cholesky(R)

    rng = np.random.RandomState(seed)
    # Generate standard normal vectors Z: (num_sims, n_locs)
    z_uncorr = rng.standard_normal((num_harvest_simulations, n_locs))
    z_corr = z_uncorr @ L_chol.T

    # Map correlated standard normals to uniforms via CDF: U = 0.5 * (1 + erf(Z / sqrt(2)))
    # Then piecewise linear quantile inverse to preserve exact (y10, y50, y90) calibration
    u_corr = 0.5 * (1.0 + np.vectorize(math.erf)(z_corr / math.sqrt(2.0)))

    # Vectorized piecewise inverse CDF matching (0.0->0, 0.10->y10, 0.50->y50, 0.90->y90, 1.0->y90*1.2)
    # This captures realistic agronomic right-skew
    simulated_yields = np.zeros_like(u_corr)
    for i in range(n_locs):
        u = u_corr[:, i]
        y_sim = np.zeros_like(u)

        # Region 0: [0, 0.10) -> [max(0, y10 - (y50-y10)), y10]
        y_min = max(0.1, y10 - (y50 - y10))
        m0 = u < 0.10
        y_sim[m0] = y_min + (u[m0] / 0.10) * (y10 - y_min)

        # Region 1: [0.10, 0.50) -> [y10, y50]
        m1 = (u >= 0.10) & (u < 0.50)
        y_sim[m1] = y10 + ((u[m1] - 0.10) / 0.40) * (y50 - y10)

        # Region 2: [0.50, 0.90) -> [y50, y90]
        m2 = (u >= 0.50) & (u < 0.90)
        y_sim[m2] = y50 + ((u[m2] - 0.50) / 0.40) * (y90 - y50)

        # Region 3: [0.90, 1.00] -> [y90, y90 + 1.25*(y90-y50)]
        y_max = y90 + 1.25 * (y90 - y50)
        m3 = u >= 0.90
        y_sim[m3] = y90 + ((u[m3] - 0.90) / 0.10) * (y_max - y90)

        simulated_yields[:, i] = y_sim

    # Realized harvest per simulation: dot product with areas
    realized_harvests = simulated_yields @ areas

    vpcr_exceedances = int(np.sum(realized_harvests > vpcr_ceiling))
    legacy_exceedances = int(np.sum(realized_harvests > legacy_ceiling))

    p_vpcr = vpcr_exceedances / num_harvest_simulations
    p_legacy = legacy_exceedances / num_harvest_simulations

    # Wilson score 95% confidence interval for p_vpcr
    z_crit = 1.95996
    denom = 1.0 + (z_crit**2) / num_harvest_simulations
    center = (p_vpcr + (z_crit**2) / (2.0 * num_harvest_simulations)) / denom
    margin = (z_crit * math.sqrt((p_vpcr * (1.0 - p_vpcr) + (z_crit**2) / (4.0 * num_harvest_simulations)) / num_harvest_simulations)) / denom
    ci_vpcr = (max(0.0, center - margin), min(1.0, center + margin))

    headroom_gain_pct = ((legacy_ceiling - vpcr_ceiling) / max(1e-9, legacy_ceiling)) * 100.0

    return {
        "crop": crop,
        "locations_evaluated": locations,
        "spatial_correlation_rho": correlation,
        "total_committed_area_ha": total_area,
        "simulations_run": num_harvest_simulations,
        "legacy_ceiling_t": legacy_ceiling,
        "vpcr_ceiling_t": vpcr_ceiling,
        "capacity_headroom_gain_pct": headroom_gain_pct,
        "vpcr_exceedance_count": vpcr_exceedances,
        "vpcr_exceedance_rate": p_vpcr,
        "vpcr_exceedance_ci95": ci_vpcr,
        "legacy_exceedance_count": legacy_exceedances,
        "legacy_exceedance_rate": p_legacy,
        "realized_p90_empirical_t": float(np.percentile(realized_harvests, 90.0)),
        "realized_mean_t": float(np.mean(realized_harvests)),
    }
