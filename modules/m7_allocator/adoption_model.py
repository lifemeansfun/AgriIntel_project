import numpy as np
from typing import Dict, List, Any
import logging

from modules.m6_market.supply_ledger import DistrictSupplyLedger
from modules.m7_allocator.online_allocator import OnlineAllocator

logger = logging.getLogger(__name__)

class PartialAdoptionSimulator:
    """
    Evaluates system robustness under partial adoption rate \alpha.
    """
    def __init__(self, ledger: DistrictSupplyLedger, online_allocator: OnlineAllocator):
        self.ledger = ledger
        self.online_allocator = online_allocator

    def simulate_season(
        self, 
        alpha: float, 
        farmers: List[Dict[str, Any]], 
        district_mean_q50: Dict[str, float],
        historical_baseline: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Simulate a season where fraction \alpha of farmers adopt the system,
        and (1-\alpha) stick to their historical behavior.
        farmers: list of dicts. We randomly sample \alpha * N to be adopters.
        historical_baseline: {crop: area} for the entire district.
        Returns the welfare of adopters and non-adopters.
        """
        N = len(farmers)
        np.random.seed(int(alpha * 100)) # reproducible
        
        # Determine adopters
        n_adopters = int(alpha * N)
        shuffled_indices = np.random.permutation(N)
        adopter_indices = set(shuffled_indices[:n_adopters])
        
        # Phase 1: Adopters use the allocator
        adopter_allocations = {}
        for i in adopter_indices:
            f = farmers[i]
            # allocate_and_commit updates the ledger's committed_area
            crop = self.online_allocator.allocate_and_commit(f['id'], f['area'], f['q50'], district_mean_q50)
            if crop:
                adopter_allocations[f['id']] = crop
                
        # Phase 2: Compute Actual Aggregate Supply X_c
        # Actual supply = committed_area (adopters) + (1 - \alpha) * historical_baseline
        # Note: In real life, non-adopters plant exactly what they planted last year.
        # Here we approximate by adding the proportional historical baseline.
        
        actual_supply = {}
        for crop in self.ledger.crop_context.keys():
            adopter_area = self.ledger.committed_area.get(crop, 0.0)
            non_adopter_area = (1.0 - alpha) * historical_baseline.get(crop, 0.0)
            actual_supply[crop] = adopter_area + non_adopter_area
            
        # Phase 3: Compute Realized Prices
        realized_prices = {}
        for crop, ctx in self.ledger.crop_context.items():
            q_current = actual_supply[crop] * ctx['yield_hat']
            realized_prices[crop] = self.ledger.price_simulator.project_price(
                crop, ctx['msp_real'], q_current, ctx['q_lag3'], eta=0.0
            )
            
        # Phase 4: Compute Welfares
        adopter_welfare = 0.0
        for i in adopter_indices:
            f = farmers[i]
            crop = adopter_allocations.get(f['id'])
            if crop:
                # Realized welfare is purely Price * Yield * Area
                adopter_welfare += realized_prices[crop] * f['q50'].get(crop, 0.0) * f['area']
                
        # Non-adopters planted according to historical distribution.
        # We assume they got proportional historical yields and faced the same realized prices.
        non_adopter_welfare = 0.0
        if alpha < 1.0:
            for crop, baseline_area in historical_baseline.items():
                non_adopter_crop_area = (1.0 - alpha) * baseline_area
                # average utility per hectare for non-adopters
                avg_q50 = district_mean_q50.get(crop, 1.0)
                # CA averages to 1.0
                non_adopter_welfare += realized_prices[crop] * avg_q50 * non_adopter_crop_area
                
        # Normalize to average per farmer (or per hectare) for comparison
        total_adopter_area = sum(farmers[i]['area'] for i in adopter_indices)
        total_non_adopter_area = sum(farmers[i]['area'] for i in range(N) if i not in adopter_indices)
        
        avg_adopter_welfare_per_ha = adopter_welfare / total_adopter_area if total_adopter_area > 0 else 0.0
        avg_non_adopter_welfare_per_ha = non_adopter_welfare / total_non_adopter_area if total_non_adopter_area > 0 else 0.0
        
        # Clean up ledger for next run
        for i in adopter_indices:
            self.ledger.release(farmers[i]['id'])
            
        return {
            "adopter_welfare_per_ha": avg_adopter_welfare_per_ha,
            "non_adopter_welfare_per_ha": avg_non_adopter_welfare_per_ha,
            "realized_prices": realized_prices
        }

class AlphaEstimator:
    """
    Cross-season adaptive estimation of adoption rate \alpha.
    """
    def __init__(self, initial_prior: float = 0.1, learning_rate: float = 0.7):
        self.alpha_hat = initial_prior
        self.lr = learning_rate
        
    def update(self, recommended_area: Dict[str, float], historical_area: Dict[str, float], observed_actual_area: Dict[str, float]):
        """
        X_actual = alpha * X_rec + (1 - alpha) * X_hist
        X_actual = alpha * (X_rec - X_hist) + X_hist
        alpha = (X_actual - X_hist) / (X_rec - X_hist)
        """
        alphas = []
        weights = []
        for crop in recommended_area.keys():
            x_rec = recommended_area.get(crop, 0.0)
            x_hist = historical_area.get(crop, 0.0)
            x_act = observed_actual_area.get(crop, 0.0)
            
            diff = x_rec - x_hist
            if abs(diff) > 10.0: # Only use crops where recommendation significantly diverged from history
                alpha_c = (x_act - x_hist) / diff
                alpha_c = np.clip(alpha_c, 0.0, 1.0)
                alphas.append(alpha_c)
                weights.append(abs(diff))
                
        if alphas:
            estimated_alpha = np.average(alphas, weights=weights)
            # exponential moving average
            self.alpha_hat = (1 - self.lr) * self.alpha_hat + self.lr * estimated_alpha
            
        return self.alpha_hat
