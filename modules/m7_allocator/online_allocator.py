import numpy as np
from typing import Dict, List, Any
import logging

from modules.m6_market.supply_ledger import DistrictSupplyLedger

logger = logging.getLogger(__name__)

class OnlineAllocator:
    """
    Capacity-aware greedy allocator that routes farmers to the highest 
    utility crop based on real-time marginal prices and comparative advantage.
    """
    def __init__(self, ledger: DistrictSupplyLedger):
        self.ledger = ledger

    def _compute_comparative_advantage(self, farmer_q50: Dict[str, float], district_mean_q50: Dict[str, float]) -> Dict[str, float]:
        """
        CA_{i,c} = q_50_{i,c} / mean(q_50_{.,c})
        """
        ca = {}
        for crop, q50 in farmer_q50.items():
            mean_q50 = district_mean_q50.get(crop, 1.0)
            if mean_q50 <= 0:
                ca[crop] = 1.0
            else:
                ca[crop] = q50 / mean_q50
        return ca

    def recommend(self, farmer_id: str, area_ha: float, farmer_q50: Dict[str, float], district_mean_q50: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        Returns a ranked list of crops based on the marginal utility.
        """
        ca = self._compute_comparative_advantage(farmer_q50, district_mean_q50)
        
        candidates = []
        for crop, ctx in self.ledger.crop_context.items():
            # Hard filter on capacity
            headroom = self.ledger.headroom(crop)
            if headroom < area_ha:
                continue
                
            # Project marginal price if this farmer commits
            p_marg = self.ledger.project_price(crop, area_ha)
            
            # Simple Utility = P_marg * q50 * CA_{i,c}
            # For exact potential game alignment, Utility must exactly match the derivative of the offline QP.
            # Revenue = P(X) * q50 * Area. 
            utility = p_marg * farmer_q50.get(crop, 0.0) * ca.get(crop, 1.0)
            
            candidates.append({
                "crop": crop,
                "marginal_price": p_marg,
                "utility": utility,
                "comparative_advantage": ca.get(crop, 1.0),
                "headroom": headroom
            })
            
        # Rank by utility descending
        candidates.sort(key=lambda x: x['utility'], reverse=True)
        return candidates

    def allocate_and_commit(self, farmer_id: str, area_ha: float, farmer_q50: Dict[str, float], district_mean_q50: Dict[str, float]) -> Optional[str]:
        """
        Gets the best crop, commits it to the ledger, and returns the crop name.
        """
        recs = self.recommend(farmer_id, area_ha, farmer_q50, district_mean_q50)
        if not recs:
            logger.warning(f"No valid crops with sufficient headroom for farmer {farmer_id} ({area_ha} ha)")
            return None
            
        best_crop = recs[0]['crop']
        
        # Commit to ledger (this locks internally)
        self.ledger.commit(farmer_id, best_crop, area_ha)
        
        return best_crop
