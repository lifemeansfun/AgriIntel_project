import os
import time
import pytest
import threading
import json
import tempfile

from modules.m6_market.supply_ledger import DistrictSupplyLedger, CapacityExceededError
from backend.ledger import LedgerPersistenceManager

class MockPriceSimulator:
    def get_coefficients(self, crop):
        if crop == "Tomato":
            return (-2.0, 1.0)
        return (-1.5, 0.5)
        
    def project_price(self, crop, msp_real, q_current, q_lag3, eta=0.0):
        # mock linear logic
        phi, theta = self.get_coefficients(crop)
        s_c = (q_current - q_lag3) / q_lag3
        p = msp_real * (1.0 + phi * theta * s_c)
        return p

@pytest.fixture
def mock_crop_context():
    return {
        "Tomato": {"msp_real": 1500.0, "q_lag3": 10000.0, "yield_hat": 20.0},
        "Wheat": {"msp_real": 2000.0, "q_lag3": 50000.0, "yield_hat": 3.0}
    }

def test_analytic_glut_threshold(mock_crop_context):
    simulator = MockPriceSimulator()
    ledger = DistrictSupplyLedger(
        district_id="test_d1",
        total_arable_ha=10000.0,
        crop_context=mock_crop_context,
        price_simulator=simulator
    )
    
    # For tomato: phi=-2.0, theta=1.0. target_sc = -0.1 / (-2.0) = 0.05
    # q_curr_max = 10000 * 1.05 = 10500
    # thresh = 10500 / 20.0 = 525.0 hectares
    assert abs(ledger.glut_thresholds["Tomato"] - 525.0) < 1e-5

def test_commit_and_headroom(mock_crop_context):
    simulator = MockPriceSimulator()
    ledger = DistrictSupplyLedger("test_d1", 10000.0, mock_crop_context, simulator)
    
    # Commit 100 ha to Tomato
    ledger.commit("farmer_1", "Tomato", 100.0)
    
    assert ledger.committed_area["Tomato"] == 100.0
    assert abs(ledger.headroom("Tomato") - 425.0) < 1e-5
    
    # Release
    ledger.release("farmer_1")
    assert ledger.committed_area["Tomato"] == 0.0
    assert abs(ledger.headroom("Tomato") - 525.0) < 1e-5

def test_capacity_exceeded(mock_crop_context):
    simulator = MockPriceSimulator()
    ledger = DistrictSupplyLedger("test_d1", 100.0, mock_crop_context, simulator)
    
    with pytest.raises(CapacityExceededError):
        ledger.commit("farmer_1", "Tomato", 101.0)

def test_concurrent_commits(mock_crop_context):
    simulator = MockPriceSimulator()
    ledger = DistrictSupplyLedger("test_d1", 10000.0, mock_crop_context, simulator)
    
    def worker(farmer_id):
        try:
            ledger.commit(f"farmer_{farmer_id}", "Tomato", 1.0)
        except CapacityExceededError:
            pass
            
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(100)]
    for t in threads: t.start()
    for t in threads: t.join()
    
    assert ledger.committed_area["Tomato"] == 100.0

def test_persistence_hydration(mock_crop_context):
    with tempfile.TemporaryDirectory() as tmpdir:
        simulator = MockPriceSimulator()
        ledger = DistrictSupplyLedger("test_d1", 10000.0, mock_crop_context, simulator)
        
        pm = LedgerPersistenceManager(data_dir=tmpdir, event_file="test_events.jsonl")
        
        v1 = ledger.commit("farmer_1", "Tomato", 100.0)
        pm.log_commit("test_d1", "farmer_1", "Tomato", 100.0, v1)
        
        v2 = ledger.commit("farmer_2", "Wheat", 50.0)
        pm.log_commit("test_d1", "farmer_2", "Wheat", 50.0, v2)
        
        # Hydrate a new empty ledger
        new_ledger = DistrictSupplyLedger("test_d1", 10000.0, mock_crop_context, simulator)
        pm.hydrate_ledger(new_ledger)
        
        assert new_ledger.committed_area["Tomato"] == 100.0
        assert new_ledger.committed_area["Wheat"] == 50.0
        assert new_ledger.version == ledger.version
