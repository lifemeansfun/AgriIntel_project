import pytest
import asyncio
from fastapi.testclient import TestClient
from backend.main import app, ledger, pm
import threading
import os

client = TestClient(app)

def test_api_state():
    response = client.get("/api/state")
    assert response.status_code == 200
    data = response.json()
    assert "headroom" in data
    assert "Tomato" in data["headroom"]

def test_api_commit_concurrent_stress():
    # IV&V Stress Test 8.1: Load Testing & Race Conditions
    # 500 concurrent requests simulating a planting day spike
    
    # Reset ledger and event log
    ledger.committed_area = {c: 0.0 for c in ledger.crop_context.keys()}
    ledger.commitments = {}
    ledger.version = 0
    if os.path.exists(pm.event_file):
        os.remove(pm.event_file)
        
    initial_headroom = ledger.headroom("Tomato")
    
    def worker(i):
        # We use TestClient synchronously in threads for the stress test
        res = client.post("/api/commit", json={
            "farmer_id": f"farmer_{i}",
            "crop": "Tomato",
            "area_ha": 1.0
        })
        return res.status_code
        
    threads = []
    results = []
    
    def thread_task(i):
        status = worker(i)
        results.append(status)
        
    for i in range(500):
        t = threading.Thread(target=thread_task, args=(i,))
        threads.append(t)
        
    for t in threads: t.start()
    for t in threads: t.join()
    
    # Check that exactly 500 succeeded (since total_arable is 1000.0, it should fit)
    successes = sum(1 for r in results if r == 200)
    assert successes == 500, f"Expected 500 successful commits, got {successes}"
    
    # Check Race Conditions: Ledger state must exactly reflect 500 ha
    final_headroom = ledger.headroom("Tomato")
    assert abs(initial_headroom - final_headroom - 500.0) < 1e-5, f"Race condition detected! Headroom dropped by {initial_headroom - final_headroom} instead of 500.0"
    
    # Check no negative headroom
    assert final_headroom >= 0.0, "Ledger state corrupted (negative headroom)"
    assert ledger.version == 500, f"Version mismatch: {ledger.version} != 500"
