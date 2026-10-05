import pytest
import numpy as np

from modules.m6_market.supply_ledger import DistrictSupplyLedger
from modules.m7_allocator.online_allocator import OnlineAllocator
from modules.m7_allocator.evaluator import FourArmEvaluator

class MockPriceSimulator:
    def get_coefficients(self, crop):
        return (-2.0, 1.0)
        
    def project_price(self, crop, msp_real, q_current, q_lag3, eta=0.0):
        s_c = (q_current - q_lag3) / q_lag3
        p = msp_real * (1.0 + (-2.0) * (1.0) * s_c)
        return max(p, msp_real * 0.1)

@pytest.fixture
def eval_context():
    base_context = {
        "Tomato": {"msp_real": 1500.0, "q_lag3": 10000.0, "yield_hat": 20.0},
        "Onion": {"msp_real": 1200.0, "q_lag3": 12000.0, "yield_hat": 18.0}
    }
    simulator = MockPriceSimulator()
    ledger = DistrictSupplyLedger("d1", 50000.0, base_context, simulator)
    online_allocator = OnlineAllocator(ledger)
    return ledger, online_allocator, base_context

def test_no_harm_invariant(eval_context):
    ledger, online_allocator, base_context = eval_context
    evaluator = FourArmEvaluator(ledger, online_allocator)
    
    np.random.seed(42)
    farmers = []
    for i in range(200):
        farmers.append({
            "id": f"f_{i}",
            "area": np.random.uniform(1.0, 3.0),
            "q50": {
                "Tomato": max(0.1, np.random.normal(20.0, 5.0)),
                "Onion": max(0.1, np.random.normal(18.0, 4.0))
            }
        })
        
    total_area = sum(f['area'] for f in farmers)
    # Simulate a historically bad glut in Tomato
    historical_baseline = {
        "Tomato": total_area * 0.8,
        "Onion": total_area * 0.2
    }
    district_mean_q50 = {"Tomato": 20.0, "Onion": 18.0}
    
    res = evaluator.evaluate_arms(farmers, historical_baseline, district_mean_q50)
    
    arm_a_incomes = res['arm_a_incomes']
    arm_c_incomes = res['arm_c_incomes']
    
    # Calculate 10th percentile income per hectare
    arm_a_per_ha = [arm_a_incomes[i] / farmers[i]['area'] for i in range(len(farmers))]
    arm_c_per_ha = [arm_c_incomes[i] / farmers[i]['area'] for i in range(len(farmers))]
    
    p10_a = np.percentile(arm_a_per_ha, 10)
    p10_c = np.percentile(arm_c_per_ha, 10)
    
    # IV&V Stress Test 7.1: The lowest 10% of farmers should not be worse off
    # under the allocator than they were under the historical glut.
    assert p10_c >= p10_a * 0.95, f"No-Harm invariant violated: Allocator P10 {p10_c} < Hist P10 {p10_a}"
