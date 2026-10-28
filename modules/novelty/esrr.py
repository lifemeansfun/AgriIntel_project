"""N1: Equilibrium-Sampled Randomised Recommendation (ESRR).

Mitigates the arrival-order penalty and myopia of sequential greedy allocation
by precomputing the target congestion-game equilibrium (social optimum under
downward-sloping market demand) and sampling recommendations from residual quotas
weighted by individual comparative advantage and marginal profit.

Invariance Scope & Methodological Clarification:
1. Target-Quota Invariance: The aggregate equilibrium target vector x* is strictly
   invariant to the arrival order of farmers for a given scenario snapshot.
2. Welfare Robustness: Guides aggregate commitments toward the target equilibrium,
   significantly reducing outcome variance across request order permutations compared
   to sequential greedy selection.
3. Individual Outcome Invariance is NOT claimed: A farmer's recommendation probability
   vector necessarily responds to residual headroom as preceding commitments accumulate.
4. Deterministic Seed Audit: PRNG seeds are derived from scenario and farmer identifiers,
   ensuring deterministic reproducibility for independent regulatory audits while
   preventing input-gaming.
"""
from __future__ import annotations

import hashlib
import math
from typing import Any, Dict, List, Optional
import numpy as np
from scipy.optimize import minimize

from modules.regional.economics import finite_number, project_price, profit


def solve_congestion_equilibrium(
    scenario: dict,
    total_area_ha: float,
) -> Dict[str, float]:
    """Computes the target area allocation x* that maximizes the social potential function.

    Objective:
        max_x sum_{c=1}^C integral_0^{x_c} [ 10 * y_50_c * P_c(outside_c + s * y_50_c) - cost_c ] ds
    subject to:
        sum_{c=1}^C x_c = total_area_ha
        0 <= x_c <= max_headroom_c
    """
    crops = scenario["crops"]
    n_crops = len(crops)
    total_area = finite_number(total_area_ha, "total_area_ha", positive=True)

    alphas = []
    betas = []
    bounds = []

    for c in crops:
        y50 = finite_number(c["yield_q50"], "yield_q50", positive=True)
        y90 = finite_number(c["yield_q90"], "yield_q90", positive=True)
        p_ref = finite_number(c["reference_price"], "reference_price", positive=True)
        s_ref = finite_number(c["reference_supply_t"], "reference_supply_t", positive=True)
        outside = finite_number(c["outside_supply_t"], "outside_supply_t")
        capacity = finite_number(c["capacity_t"], "capacity_t", positive=True)
        cost = finite_number(c["cost_per_ha"], "cost_per_ha")
        phi = finite_number(c["phi"], "phi")
        theta = finite_number(c["theta"], "theta")

        if phi >= 0 or not (0 < theta <= 1):
            raise ValueError("Supply response requires negative phi and theta in (0, 1]")

        k0 = p_ref * (1.0 - phi * theta + (phi * theta * outside / s_ref))
        k1 = p_ref * (phi * theta * y50 / s_ref)  # Note: phi < 0, so k1 < 0

        alpha = 10.0 * y50 * k0 - cost
        beta = -10.0 * y50 * k1  # beta > 0

        alphas.append(alpha)
        betas.append(beta)

        crop_headroom = max(0.0, (capacity - outside) / y90)
        bounds.append((0.0, min(total_area, crop_headroom)))

    alphas = np.array(alphas, dtype=np.float64)
    betas = np.array(betas, dtype=np.float64)

    def objective(x: np.ndarray) -> float:
        return float(0.5 * np.sum(betas * (x ** 2)) - np.sum(alphas * x))

    def objective_grad(x: np.ndarray) -> np.ndarray:
        return betas * x - alphas

    max_possible_sum = sum(b[1] for b in bounds)
    effective_target_sum = min(total_area, max_possible_sum)

    constraints = [
        {
            "type": "eq",
            "fun": lambda x: float(np.sum(x) - effective_target_sum),
            "jac": lambda x: np.ones_like(x),
        }
    ]

    x0 = np.array([b[1] for b in bounds], dtype=np.float64)
    if np.sum(x0) > 0:
        x0 = x0 * (effective_target_sum / np.sum(x0))
    else:
        x0 = np.full(n_crops, effective_target_sum / n_crops)

    res = minimize(
        objective,
        x0,
        jac=objective_grad,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"ftol": 1e-12, "maxiter": 200},
    )

    if not res.success:
        x_sol = np.clip(x0, [b[0] for b in bounds], [b[1] for b in bounds])
        if np.sum(x_sol) > 0:
            x_sol = x_sol * (effective_target_sum / np.sum(x_sol))
    else:
        x_sol = res.x

    return {crops[i]["crop"]: float(max(0.0, x_sol[i])) for i in range(n_crops)}


class ESRRAllocator:
    """Equilibrium-Sampled Randomised Recommendation Allocator."""

    def __init__(self, scenario: dict, freeze_farmer_seed: bool = True):
        self.scenario = scenario
        self.freeze_farmer_seed = freeze_farmer_seed
        self.crops_by_name = {c["crop"]: c for c in scenario["crops"]}
        self.participating_area_ha = finite_number(
            scenario["participating_area_ha"], "participating_area_ha", positive=True
        )
        self.equilibrium_targets = solve_congestion_equilibrium(
            scenario, self.participating_area_ha
        )

    def compute_selection_probabilities(
        self,
        state: dict,
        farmer_id: str,
        area_ha: float,
        comparative_advantage: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        """Calculates the probability vector pi_i for farmer i against residual targets."""
        area = finite_number(area_ha, "area_ha", positive=True)
        ca = comparative_advantage or {c: 1.0 for c in self.crops_by_name}

        crop_states = {row["crop"]: row for row in state.get("crops", [])}
        remaining_total_area = float(
            state.get("remaining_area_ha", self.participating_area_ha)
        )

        unnormalized_weights: Dict[str, float] = {}

        for crop_name, spec in self.crops_by_name.items():
            cs = crop_states.get(crop_name, {})
            conservative = float(cs.get("conservative_committed_t", 0.0))
            expected = float(cs.get("expected_committed_t", 0.0))
            committed_area = float(cs.get("committed_area_ha", 0.0))

            remaining_quantity = (
                spec["capacity_t"] - spec["outside_supply_t"] - conservative
            )
            crop_headroom_ha = (
                max(0.0, remaining_quantity / spec["yield_q90"])
                if spec["yield_q90"] > 0
                else 0.0
            )
            available_headroom = min(remaining_total_area, crop_headroom_ha)

            # Strict physical eligibility filter
            if area > available_headroom + 1e-9:
                continue

            target_area = self.equilibrium_targets.get(crop_name, 0.0)
            residual_target = max(0.0, target_area - committed_area)

            # Marginal price projection if committed
            p_proj = project_price(
                spec, spec["outside_supply_t"] + expected + area * spec["yield_q50"]
            )
            est_profit = profit(area, spec["yield_q50"], p_proj, spec["cost_per_ha"])
            est_profit_per_ha = max(0.1, est_profit / area)

            farmer_ca = max(0.1, ca.get(crop_name, 1.0))

            # Weight = (residual target + baseline exploration) * comparative advantage * sqrt(profit density)
            weight = (residual_target + 0.05 * available_headroom) * farmer_ca * math.sqrt(est_profit_per_ha)
            unnormalized_weights[crop_name] = max(0.0, weight)

        total_weight = sum(unnormalized_weights.values())
        if total_weight <= 1e-9:
            eligible_crops = list(unnormalized_weights.keys())
            if not eligible_crops:
                return {}
            prob = 1.0 / len(eligible_crops)
            return {c: prob for c in eligible_crops}

        return {c: w / total_weight for c, w in unnormalized_weights.items()}

    def recommend(
        self,
        state: dict,
        farmer_id: str,
        area_ha: float,
        comparative_advantage: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Issues an auditable, deterministically seeded recommendation."""
        probs = self.compute_selection_probabilities(
            state, farmer_id, area_ha, comparative_advantage
        )

        if not probs:
            return {
                "farmer_id": farmer_id,
                "recommended_crop": None,
                "probabilities": {},
                "eligible": False,
                "audit_seed": None,
                "reason": "No crops have remaining capacity for requested area",
            }

        scenario_id = state.get("scenario_id", self.scenario.get("id", "scenario"))
        revision = state.get("revision", 0)

        # Seed construction:
        # If freeze_farmer_seed is True: seed depends only on scenario_id and farmer_id.
        # This prevents gaming where a farmer tries varying input area or waiting for revision ticks.
        if self.freeze_farmer_seed:
            seed_material = f"{scenario_id}:{farmer_id}"
        else:
            seed_material = f"{scenario_id}:{farmer_id}:{revision}:{area_ha}"

        seed_hash = hashlib.sha256(seed_material.encode("utf-8")).hexdigest()
        seed_int = int(seed_hash[:8], 16)

        rng = np.random.RandomState(seed_int)
        sorted_crops = sorted(probs.keys())
        prob_values = [probs[c] for c in sorted_crops]

        chosen_crop = rng.choice(sorted_crops, p=prob_values)

        return {
            "farmer_id": farmer_id,
            "recommended_crop": chosen_crop,
            "probabilities": probs,
            "eligible": True,
            "audit_seed": seed_hash,
            "seed_mode": "frozen_farmer_identity" if self.freeze_farmer_seed else "dynamic_revision",
            "equilibrium_targets": self.equilibrium_targets,
        }
