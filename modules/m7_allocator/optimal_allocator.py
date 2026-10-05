import numpy as np
from scipy.optimize import minimize, Bounds, LinearConstraint
from typing import Dict, List, Any
import logging

from modules.m6_market.supply_ledger import DistrictSupplyLedger

logger = logging.getLogger(__name__)

class OfflineOptimalAllocator:
    """
    Offline Quadratic Programming allocator.
    Serves as the theoretical upper bound for the IV&V competitive ratio stress test.
    Maximizes sum of utilities exactly aligned with the Online Allocator.
    """
    def __init__(self, ledger: DistrictSupplyLedger):
        self.ledger = ledger

    def solve(self, farmers: List[Dict[str, Any]], district_mean_q50: Dict[str, float]) -> Dict[str, float]:
        """
        farmers is a list of dicts: [{'id': str, 'area': float, 'q50': {'Tomato': 20, ...}}, ...]
        Returns a dictionary of farmer_id -> crop
        """
        N = len(farmers)
        crops = list(self.ledger.crop_context.keys())
        C = len(crops)
        
        # Flattened variable array: x = [x_{1,1}, x_{1,2}, ..., x_{1,C}, x_{2,1}, ..., x_{N,C}]
        # x_{i,c} is the area allocated to farmer i for crop c.
        
        # Compute CA_{i,c} matrix
        ca_matrix = np.ones((N, C))
        q50_matrix = np.zeros((N, C))
        area_array = np.zeros(N)
        
        for i, f in enumerate(farmers):
            area_array[i] = f['area']
            for j, c in enumerate(crops):
                q50 = f['q50'].get(c, 0.0)
                q50_matrix[i, j] = q50
                mean_q50 = district_mean_q50.get(c, 1.0)
                ca_matrix[i, j] = (q50 / mean_q50) if mean_q50 > 0 else 1.0

        # Objective function (Negative to minimize)
        # sum_c P_c(X_c) * sum_i (x_{i,c} * q50_{i,c} * ca_{i,c})
        
        def objective(x_flat):
            x = x_flat.reshape((N, C))
            X_c = np.sum(x, axis=0) # Aggregate area per crop
            
            total_utility = 0.0
            for j, crop in enumerate(crops):
                ctx = self.ledger.crop_context[crop]
                q_current = X_c[j] * ctx['yield_hat']
                
                # We need the exact price formula from the simulator
                p_c = self.ledger.price_simulator.project_price(
                    crop, ctx['msp_real'], q_current, ctx['q_lag3'], eta=0.0
                )
                
                # sum_i (x_{i,c} * q50_{i,c} * ca_{i,c})
                crop_utility_sum = np.sum(x[:, j] * q50_matrix[:, j] * ca_matrix[:, j])
                
                total_utility += p_c * crop_utility_sum
                
            return -total_utility

        # Constraints
        # 1. sum_c x_{i,c} = area_i (Farmer uses exactly their land)
        A_eq = np.zeros((N, N * C))
        for i in range(N):
            A_eq[i, i*C:(i+1)*C] = 1.0
        
        linear_constraint = LinearConstraint(A_eq, area_array, area_array)
        
        # Bounds: 0 <= x_{i,c}
        # Technically also X_c <= glut_threshold, but the utility should naturally prevent gluts.
        # We can add an upper bound to X_c but it requires an inequality constraint.
        A_ub = np.zeros((C, N * C))
        for j in range(C):
            for i in range(N):
                A_ub[j, i*C + j] = 1.0
                
        # upper bounds are the glut thresholds
        ub_array = np.array([self.ledger.glut_thresholds.get(c, float('inf')) for c in crops])
        # Replace inf with a very large number for scipy
        ub_array[ub_array == float('inf')] = 1e9
        
        ineq_constraint = LinearConstraint(A_ub, -np.inf, ub_array)
        
        bounds = Bounds(0, np.inf)
        
        # Initial guess (even distribution)
        x0 = np.zeros((N, C))
        for i in range(N):
            x0[i, :] = area_array[i] / C
        x0_flat = x0.flatten()
        
        res = minimize(
            objective, 
            x0_flat, 
            method='SLSQP', 
            bounds=bounds,
            constraints=[linear_constraint, ineq_constraint],
            options={'maxiter': 1000, 'ftol': 1e-4}
        )
        
        if not res.success:
            logger.warning(f"Offline optimizer did not converge: {res.message}")
            
        x_opt = res.x.reshape((N, C))
        
        # Assignment: Fractional areas are technically allowed in the QP, 
        # but farmers usually plant a single dominant crop in our simplified model.
        # For benchmarking, we assign the crop with the max fractional area.
        assignment = {}
        for i, f in enumerate(farmers):
            best_crop_idx = np.argmax(x_opt[i, :])
            assignment[f['id']] = crops[best_crop_idx]
            
        return assignment, -res.fun
