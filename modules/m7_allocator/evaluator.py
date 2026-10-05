import numpy as np
from typing import Dict, List, Any
import logging

from modules.m6_market.supply_ledger import DistrictSupplyLedger
from modules.m7_allocator.online_allocator import OnlineAllocator

logger = logging.getLogger(__name__)

class FourArmEvaluator:
    """
    Evaluates the final system across four conceptual arms:
    Arm A: Historical Naive Replant (Static)
    Arm B: Uncoordinated Static ML Recommendations (Causes gluts)
    Arm C: Capacity-aware Closed-loop Allocator (Our invention)
    Arm D: Theoretical Offline Optimal (QP upper bound)
    """
    def __init__(self, ledger: DistrictSupplyLedger, online_allocator: OnlineAllocator):
        # We only really need to evaluate Arm A vs Arm C for the No-Harm Invariant.
        self.ledger = ledger
        self.online_allocator = online_allocator

    def evaluate_arms(self, farmers: List[Dict[str, Any]], historical_baseline: Dict[str, float], district_mean_q50: Dict[str, float]) -> Dict[str, Any]:
        """
        Runs a simulated season comparing Arm A (Historical) and Arm C (Allocator).
        """
        N = len(farmers)
        
        # --- Arm A: Historical Naive Replant ---
        # We assume total historical baseline area is distributed among farmers.
        # To calculate farmer-level income, we simulate prices under historical baseline.
        arm_a_prices = {}
        for crop, ctx in self.ledger.crop_context.items():
            q_current = historical_baseline.get(crop, 0.0) * ctx['yield_hat']
            arm_a_prices[crop] = self.ledger.price_simulator.project_price(
                crop, ctx['msp_real'], q_current, ctx['q_lag3'], eta=0.0
            )
            
        arm_a_incomes = []
        # Assign farmers proportional income assuming they roughly grew what history did
        # For simplicity, we just randomly assign them a crop with probability proportional to history
        total_hist_area = sum(historical_baseline.values())
        if total_hist_area == 0: total_hist_area = 1.0
        
        np.random.seed(42)
        for f in farmers:
            # simple proportional lottery
            r = np.random.uniform(0, total_hist_area)
            assigned_crop = list(historical_baseline.keys())[0]
            accum = 0
            for c, a in historical_baseline.items():
                accum += a
                if r <= accum:
                    assigned_crop = c
                    break
                    
            income = arm_a_prices[assigned_crop] * f['q50'].get(assigned_crop, 0.0) * f['area']
            arm_a_incomes.append(income)
            
        # --- Arm C: Closed-loop Allocator ---
        # reset ledger
        self.ledger.committed_area = {c: 0.0 for c in self.ledger.crop_context.keys()}
        
        arm_c_allocations = {}
        for f in farmers:
            crop = self.online_allocator.allocate_and_commit(f['id'], f['area'], f['q50'], district_mean_q50)
            arm_c_allocations[f['id']] = crop
            
        arm_c_prices = {}
        for crop, ctx in self.ledger.crop_context.items():
            area = self.ledger.committed_area.get(crop, 0.0)
            q_current = area * ctx['yield_hat']
            arm_c_prices[crop] = self.ledger.price_simulator.project_price(
                crop, ctx['msp_real'], q_current, ctx['q_lag3'], eta=0.0
            )
            
        arm_c_incomes = []
        for f in farmers:
            crop = arm_c_allocations.get(f['id'])
            if crop:
                income = arm_c_prices[crop] * f['q50'].get(crop, 0.0) * f['area']
                arm_c_incomes.append(income)
            else:
                arm_c_incomes.append(0.0)
                
        return {
            "arm_a_incomes": arm_a_incomes,
            "arm_c_incomes": arm_c_incomes,
            "arm_a_prices": arm_a_prices,
            "arm_c_prices": arm_c_prices
        }
