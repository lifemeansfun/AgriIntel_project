import copy
import math

import pytest

from modules.regional.economics import evaluate_final, profit, project_price, recommend, scenario_row


@pytest.fixture
def scenario():
    return {
        'participating_area_ha': 24, 'risk_aversion': .5,
        'crops': [{'crop': 'Maize', 'yield_q10': 2, 'yield_q50': 4, 'yield_q90': 6,
                   'reference_price': 2000, 'cost_per_ha': 10000,
                   'reference_supply_t': 160, 'outside_supply_t': 128,
                   'capacity_t': 160 * (1 + .1 / .6), 'phi': -2, 'theta': .3}],
    }


def test_units_and_fixed_cost_under_yield_change():
    assert profit(2, 3, 2000, 10000) == 100000
    assert profit(2, 1, 2000, 10000) == 20000
    # Scaling already net profit would give 33333.33, which is incorrect.
    assert profit(2, 1, 2000, 10000) != profit(2, 3, 2000, 10000) / 3


@pytest.mark.parametrize('bad', [0, -1, float('nan'), float('inf'), True])
def test_invalid_area_rejected(bad):
    with pytest.raises(ValueError):
        profit(bad, 3, 2000, 10000)


def test_capacity_means_minimum_scenario_price(scenario):
    spec = scenario['crops'][0]
    assert project_price(spec, spec['reference_supply_t']) == spec['reference_price']
    assert project_price(spec, spec['capacity_t']) == pytest.approx(.9 * spec['reference_price'])
    assert project_price(spec, 170) < project_price(spec, 150)


def test_quantity_reservation_and_area_limit(scenario):
    state = {'remaining_area_ha': 24, 'crops': [
        {'crop': 'Maize', 'expected_committed_t': 20, 'conservative_committed_t': 30}]}
    row = recommend(scenario, state, 1)[0]
    spec = scenario['crops'][0]
    assert row['Price_central'] == project_price(spec, 128 + 20 + 4)
    assert row['Price_pessimistic'] == project_price(spec, 128 + 30 + 6)
    assert row['Remaining_Area_ha'] == pytest.approx((spec['capacity_t'] - 128 - 30) / 6)
    assert row['Central_Profit'] == profit(1, 4, row['Price_central'], 10000)
    assert row['Score'] == row['Central_Profit'] - .5 * row['Downside_Gap']
    assert not recommend(scenario, state, 10)[0]['Eligible']
    state['remaining_area_ha'] = .5
    assert not recommend(scenario, state, 1)[0]['Eligible']


def test_browsing_has_no_supply_side_effects(scenario):
    state = {'remaining_area_ha': 24, 'crops': []}
    before = copy.deepcopy((scenario, state))
    recommend(scenario, state, 1)
    assert (scenario, state) == before


def test_final_repricing_uses_same_price_for_all_farmers(scenario):
    state = {
        'remaining_area_ha': 21,
        'crops': [{'crop': 'Maize', 'expected_committed_t': 12, 'committed_area_ha': 3}],
        'commitments': [{'participant_id': 'later', 'crop': 'Maize', 'area_ha': 1},
                        {'participant_id': 'earlier', 'crop': 'Maize', 'area_ha': 2}],
    }
    result = evaluate_final(scenario, state)
    p = project_price(scenario['crops'][0], 128 + 12)
    assert result['total_profit'] == pytest.approx(profit(3, 4, p, 10000))
    assert result['participant_profits'][0]['participant_id'] == 'earlier'
    assert result['participant_profits'][0]['profit'] == 2 * result['participant_profits'][1]['profit']
    assert result['unallocated_area_ha'] == 21


def test_scenario_is_not_a_probability_quantile(scenario):
    spec = scenario['crops'][0]
    row = scenario_row(spec, 1, 2000, 1800, 2200)
    assert row['Central_Profit'] == 70000
    assert row['Pessimistic_Profit'] == 26000
    assert row['Downside_Gap'] == 44000
    assert 'Expected_Profit' not in row
    assert 'VaR95' not in row


@pytest.mark.parametrize('changes', [{'reference_supply_t': 0}, {'theta': 0}, {'phi': 1}])
def test_bad_price_configuration(scenario, changes):
    spec = dict(scenario['crops'][0], **changes)
    with pytest.raises(ValueError):
        project_price(spec, 100)
