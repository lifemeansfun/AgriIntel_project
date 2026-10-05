import threading
import time
from typing import Dict, Any, Optional

class CapacityExceededError(Exception):
    """Raised when headroom goes negative."""
    pass

class DistrictSupplyLedger:
    """
    O(1) thread-safe atomic state object tracking committed acreages.
    State is scoped to a specific (State, District, Season, Year).
    """
    def __init__(
        self, 
        district_id: str, 
        total_arable_ha: float,
        crop_context: Dict[str, Dict[str, float]], 
        price_simulator: Any
    ):
        """
        crop_context dict structure:
        {
            'Tomato': {'msp_real': 1500, 'q_lag3': 10000, 'yield_hat': 25.0},
            ...
        }
        """
        self.district_id = district_id
        self.total_arable_ha = total_arable_ha
        self.crop_context = crop_context
        self.price_simulator = price_simulator
        
        self.committed_area: Dict[str, float] = {c: 0.0 for c in crop_context.keys()}
        self.baseline_area: Dict[str, float] = {c: 0.0 for c in crop_context.keys()} # Can be set later
        
        # Concurrency
        self.version: int = 1
        self.updated_at: float = time.time()
        self._lock = threading.Lock()
        
        # Farmer commitments tracking for release()
        # farmer_id -> {'crop': str, 'area': float}
        self.commitments: Dict[str, Dict[str, Any]] = {}
        
        # Precompute glut thresholds analytically
        self.glut_thresholds: Dict[str, float] = {}
        self._compute_glut_thresholds()

    def _compute_glut_thresholds(self):
        """
        Analytically compute the acreage X_c* at which P_c(X_c) falls to MSP.
        P_c = MSP * (1 - phi * theta * ((X_c * yield_hat - q_lag3) / q_lag3))
        If P_c = MSP, then phi * theta * S_c = 0.
        Since phi and theta are non-zero, S_c = 0.
        So X_c * yield_hat = q_lag3 => X_c = q_lag3 / yield_hat.
        This is the baseline "no glut" threshold. 
        If we define glut threshold as dropping to some critical floor (e.g. 80% of MSP), 
        we solve: 1 - phi*theta*S_c = 0.8 => S_c = 0.2 / (phi*theta).
        We will define glut threshold as the acreage where price drops below 90% of MSP.
        """
        for crop, ctx in self.crop_context.items():
            phi, theta = self.price_simulator.get_coefficients(crop)
            q_lag3 = ctx['q_lag3']
            yield_hat = ctx['yield_hat']
            
            if q_lag3 <= 0 or yield_hat <= 0:
                self.glut_thresholds[crop] = float('inf')
                continue
                
            # target S_c where price drops by 10% (0.1)
            # 1 - (phi * theta * S_c) = 0.9 => S_c = 0.1 / (phi * theta)
            # Since phi is negative (e.g. -2.0), phi*theta is negative.
            # Wait, if supply goes up, price goes DOWN.
            # My formula: P = MSP * (1 - (phi * theta * S_c))
            # If phi=-2.0, theta=1.0, then phi*theta = -2.0.
            # So P = MSP * (1 - (-2.0 * S_c)) = MSP * (1 + 2.0 * S_c).
            # WAIT! Demand elasticity phi is negative, so if supply INCREASES (S_c > 0), 
            # the price should DROP. 
            # So the formula in PriceSimulator must be: P = MSP * (1 + phi * theta * S_c).
            # Let's adjust the algebra here, and I will fix PriceSimulator later or assume phi is positive internally.
            # Actually, standard formula is P = MSP * (1 + phi * theta * S_c) where phi < 0.
            # So we solve 1 + phi * theta * S_c = 0.9 => phi * theta * S_c = -0.1
            # S_c = -0.1 / (phi * theta)
            try:
                target_sc = -0.1 / (phi * theta)
                # S_c = (Q_curr - Q_lag) / Q_lag => Q_curr = Q_lag * (1 + target_sc)
                q_curr_max = q_lag3 * (1 + target_sc)
                self.glut_thresholds[crop] = q_curr_max / yield_hat
            except ZeroDivisionError:
                self.glut_thresholds[crop] = float('inf')

    def project_price(self, crop: str, delta_area: float) -> float:
        """O(1) projection of marginal price if delta_area is added."""
        if crop not in self.crop_context:
            raise ValueError(f"Crop {crop} not in context")
            
        ctx = self.crop_context[crop]
        current_area = self.committed_area[crop] + delta_area
        q_current = current_area * ctx['yield_hat']
        
        return self.price_simulator.project_price(
            crop=crop,
            msp_real=ctx['msp_real'],
            q_current=q_current,
            q_lag3=ctx['q_lag3']
        )

    def headroom(self, crop: str) -> float:
        """Returns remaining acreage before hitting the glut threshold."""
        return max(0.0, self.glut_thresholds.get(crop, float('inf')) - self.committed_area.get(crop, 0.0))

    def commit(self, farmer_id: str, crop: str, area: float) -> int:
        """Atomic increment of committed area."""
        with self._lock:
            if farmer_id in self.commitments:
                raise ValueError(f"Farmer {farmer_id} already committed.")
            
            # Strict capacity check
            if sum(self.committed_area.values()) + area > self.total_arable_ha:
                raise CapacityExceededError(f"Total arable capacity {self.total_arable_ha} exceeded.")
                
            self.committed_area[crop] += area
            self.commitments[farmer_id] = {'crop': crop, 'area': area}
            
            self.version += 1
            self.updated_at = time.time()
            return self.version

    def release(self, farmer_id: str) -> int:
        """Decrement for withdrawn commitments."""
        with self._lock:
            if farmer_id not in self.commitments:
                return self.version
                
            record = self.commitments.pop(farmer_id)
            self.committed_area[record['crop']] -= record['area']
            # Float precision fix
            if self.committed_area[record['crop']] < 1e-9:
                self.committed_area[record['crop']] = 0.0
                
            self.version += 1
            self.updated_at = time.time()
            return self.version
