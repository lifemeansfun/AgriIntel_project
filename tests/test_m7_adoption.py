import pytest
import numpy as np

from modules.m6_market.supply_ledger import DistrictSupplyLedger
from modules.m7_allocator.online_allocator import OnlineAllocator
from modules.m7_allocator.adoption_model import PartialAdoptionSimulator, AlphaEstimator

class MockPriceSimulator:
    def get_coefficients(self, crop):
        return (-2.0, 1.0)
        
    def project_price(self, crop, msp_real, q_current, q_lag3, eta=0.0):
        s_c = (q_current - q_lag3) / q_lag3
        p = msp_real * (1.0 + (-2.0) * (1.0) * s_c)
        return max(p, msp_real * 0.1)

@pytest.fixture
def adoption_context():
    base_context = {
        "Tomato": {"msp_real": 1500.0, "q_lag3": 10000.0, "yield_hat": 20.0},
        "Onion": {"msp_real": 1200.0, "q_lag3": 12000.0, "yield_hat": 18.0}
    }
    simulator = MockPriceSimulator()
    ledger = DistrictSupplyLedger("d1", 50000.0, base_context, simulator)
    online_allocator = OnlineAllocator(ledger)
    return ledger, online_allocator, base_context

def test_adopter_advantage(adoption_context):
    ledger, online_allocator, base_context = adoption_context
    simulator = PartialAdoptionSimulator(ledger, online_allocator)
    
    # Generate 100 synthetic farmers
    np.random.seed(42)
    farmers = []
    for i in range(100):
        farmers.append({
            "id": f"f_{i}",
            "area": np.random.uniform(1.0, 5.0),
            "q50": {
                "Tomato": np.random.normal(20.0, 2.0),
                "Onion": np.random.normal(18.0, 1.5)
            }
        })
        
    total_synthetic_area = sum(f['area'] for f in farmers)
    district_mean_q50 = {"Tomato": 20.0, "Onion": 18.0}
    
    # Scale historical baseline to match exactly the synthetic population's area
    # Let's say Tomato was 40% and Onion was 60% of history
    historical_baseline = {
        "Tomato": total_synthetic_area * 0.4, 
        "Onion": total_synthetic_area * 0.6
    }
    
    # Sweep alpha
    for alpha in [0.1, 0.3, 0.6, 0.9]:
        results = simulator.simulate_season(alpha, farmers, district_mean_q50, historical_baseline)
        
        adopter_welfare = results['adopter_welfare_per_ha']
        non_adopter_welfare = results['non_adopter_welfare_per_ha']
        
        # IV&V Stress Test 5.1: Adopter welfare must be >= non-adopter welfare
        # Add a tiny epsilon for float precision
        assert adopter_welfare + 1e-5 >= non_adopter_welfare, f"Alpha {alpha} failed: Adopter {adopter_welfare} < Non-Adopter {non_adopter_welfare}"

def test_estimator_convergence():
    np.random.seed(42)
    estimator = AlphaEstimator(initial_prior=0.1, learning_rate=0.75)
    
    true_alpha = 0.6
    
    recommended = {"Tomato": 800.0, "Onion": 400.0}
    historical = {"Tomato": 400.0, "Onion": 600.0}
    
    # Simulate 3 seasons
    for season in range(3):
        # Add 15% observation noise to true actual
        actual = {}
        for crop in recommended.keys():
            exact = true_alpha * recommended[crop] + (1 - true_alpha) * historical[crop]
            noise = np.random.normal(0, 0.15 * exact)
            actual[crop] = exact + noise
            
        estimator.update(recommended, historical, actual)
        
    # IV&V Stress Test 5.2: Convergence within 3 seasons
    # Since learning rate is 0.5 and noise is 15%, we expect it to be reasonably close.
    assert abs(estimator.alpha_hat - true_alpha) < 0.15, f"Estimator failed to converge: {estimator.alpha_hat} != {true_alpha}"
