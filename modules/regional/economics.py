"""Shared scenario arithmetic. Prices and costs are proxies, not income guarantees.

Yield is tonnes/ha, price is base-2011 INR/quintal and cost is INR/ha.
The three scenarios are combinations of assumptions, not profit quantiles.
"""
from __future__ import annotations

import math
from typing import Any


def finite_number(value: Any, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite number")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(result) or (positive and result <= 0):
        raise ValueError(f"{name} must be {'positive and ' if positive else ''}finite")
    return result


def profit(area_ha: float, yield_t_ha: float, price_per_quintal: float, cost_per_ha: float) -> float:
    area = finite_number(area_ha, 'area', positive=True)
    y = finite_number(yield_t_ha, 'yield')
    p = finite_number(price_per_quintal, 'price')
    cost = finite_number(cost_per_ha, 'cost')
    if min(y, p, cost) < 0:
        raise ValueError('Yield, price and cost must be nonnegative')
    result = area * (10.0 * y * p - cost)
    if not math.isfinite(result):
        raise ValueError('Scenario profit overflows finite arithmetic')
    return result


def project_price(crop_spec: dict, total_supply_t: float) -> float:
    reference = finite_number(crop_spec['reference_price'], 'reference_price', positive=True)
    reference_supply = finite_number(crop_spec['reference_supply_t'], 'reference_supply_t', positive=True)
    supply = finite_number(total_supply_t, 'total_supply_t')
    phi = finite_number(crop_spec['phi'], 'phi')
    theta = finite_number(crop_spec['theta'], 'theta')
    if supply < 0 or phi >= 0 or not 0 < theta <= 1:
        raise ValueError('Supply must be nonnegative; phi negative; theta in (0, 1]')
    price = reference * (1 + phi * theta * (supply / reference_supply - 1))
    # Numerical bounds belong to the simulation, not to statutory procurement.
    return max(reference * .1, min(reference * 5, price))


def scenario_row(spec: dict, area_ha: float, central_price: float, pessimistic_price: float,
                 optimistic_price: float, *, risk_aversion: float = .5,
                 remaining_area_ha: float | None = None, eligible: bool = True,
                 reason: str | None = None) -> dict:
    area = finite_number(area_ha, 'area', positive=True)
    q10, q50, q90 = [finite_number(spec[key], key) for key in ('yield_q10', 'yield_q50', 'yield_q90')]
    if not 0 <= q10 <= q50 <= q90:
        raise ValueError('Yield estimates must be nonnegative and ordered')
    cost = finite_number(spec['cost_per_ha'], 'cost_per_ha')
    central = profit(area, q50, central_price, cost)
    pessimistic = profit(area, q10, pessimistic_price, cost)
    gap = max(0.0, central - pessimistic)
    return {
        'Crop': spec['crop'], 'Score': central - risk_aversion * gap,
        'Central_Profit': central, 'Pessimistic_Profit': pessimistic, 'Downside_Gap': gap,
        'Cost_per_ha': cost, 'Yield_q10': q10, 'Yield_q50': q50, 'Yield_q90': q90,
        'Price_pessimistic': pessimistic_price, 'Price_central': central_price,
        'Price_optimistic': optimistic_price, 'Remaining_Area_ha': remaining_area_ha,
        'Eligible': eligible, 'Ineligibility_Reason': reason,
    }


def recommend(scenario: dict, state: dict, area_ha: float) -> list[dict]:
    """Evaluate an additional planting against one coherent ledger snapshot."""
    area = finite_number(area_ha, 'area', positive=True)
    crop_states = {row['crop']: row for row in state.get('crops', [])}
    remaining_total = float(state.get('remaining_area_ha', scenario['participating_area_ha']))
    rows = []
    for spec in scenario['crops']:
        cs = crop_states.get(spec['crop'], {})
        expected = float(cs.get('expected_committed_t', 0))
        conservative = float(cs.get('conservative_committed_t', 0))
        remaining_quantity = spec['capacity_t'] - spec['outside_supply_t'] - conservative
        crop_headroom = max(0.0, remaining_quantity / spec['yield_q90']) if spec['yield_q90'] > 0 else 0.0
        headroom = max(0.0, min(remaining_total, crop_headroom))
        eligible = area <= headroom + 1e-9
        reason = None if eligible else 'Requested area exceeds remaining scenario or crop capacity'
        central = project_price(spec, spec['outside_supply_t'] + expected + area * spec['yield_q50'])
        pessimistic = project_price(spec, spec['outside_supply_t'] + conservative + area * spec['yield_q90'])
        optimistic = project_price(spec, spec['outside_supply_t'] + expected + area * spec['yield_q10'])
        rows.append(scenario_row(spec, area, central, pessimistic, optimistic,
                                 risk_aversion=scenario.get('risk_aversion', .5),
                                 remaining_area_ha=headroom, eligible=eligible, reason=reason))
    # Crop name makes ties reproducible across run order and database query plans.
    return sorted(rows, key=lambda row: (not row['Eligible'], -row['Score'], row['Crop']))


def evaluate_final(scenario: dict, state: dict) -> dict:
    """Price every participant at the same final market-clearing scenario price."""
    specs = {row['crop']: row for row in scenario['crops']}
    crop_states = {row['crop']: row for row in state.get('crops', [])}
    final_prices = {crop: project_price(spec, spec['outside_supply_t'] +
                    float(crop_states.get(crop, {}).get('expected_committed_t', 0)))
                    for crop, spec in specs.items()}
    participant_profits = []
    for commitment in state.get('commitments', []):
        spec = specs[commitment['crop']]
        area = float(commitment['area_ha'])
        y = float(commitment.get('yield_q50', spec['yield_q50']))
        cost = float(commitment.get('cost_per_ha', spec['cost_per_ha']))
        participant_profits.append({
            'participant_id': commitment['participant_id'], 'crop': spec['crop'],
            'area_ha': area, 'profit': profit(area, y, final_prices[spec['crop']], cost),
        })
    participant_profits.sort(key=lambda row: row['participant_id'])
    values = sorted(row['profit'] for row in participant_profits)
    tail_count = max(1, math.ceil(len(values) * .1))
    return {
        'total_profit': sum(values),
        'lower_tail_mean_profit': sum(values[:tail_count]) / tail_count if values else None,
        'participants_allocated': len(values),
        'lower_tail_population': 'allocated participants only; rejected participants reported separately',
        'unallocated_area_ha': max(0.0, float(state.get('remaining_area_ha', scenario['participating_area_ha']))),
        'final_prices': final_prices,
        'crop_allocation': {crop: float(crop_states.get(crop, {}).get('committed_area_ha', 0)) for crop in specs},
        'participant_profits': participant_profits,
        'currency_basis': '2011-base INR',
        'interpretation': 'Simulated outcomes under shared final prices; not observed farmer income',
    }
