"""
Module 4: Market Price Simulator
Synthesizes a realistic `Real_Market_Price_per_Quintal` to enable downside risk tracking,
using an economic elasticity model driven by aggregate supply shocks (Area x Yield) 
and market integration coefficients.

Provides an O(1) PriceSimulator class for real-time marginal price projections in the Allocator.
"""

import pandas as pd
import numpy as np
import yaml
import os
import logging

logger = logging.getLogger(__name__)

class PriceSimulator:
    """
    O(1) stateful price simulator. Loads flexibility and integration coefficients
    from config to compute marginal prices dynamically.
    """
    def __init__(self, config_path: str = None):
        if config_path is None:
            # Default to project config path relative to this file
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            config_path = os.path.join(base_dir, 'config', 'price_flexibility.yaml')
            
        try:
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load price flexibility config at {config_path}: {e}")
            raise

        self.default_phi = self.config.get('default_flexibility', -1.5)
        self.default_theta = self.config.get('default_integration', 0.5)
        self.crops_config = self.config.get('crops', {})

    def get_coefficients(self, crop: str):
        """Returns (phi, theta) for a given crop."""
        crop_conf = self.crops_config.get(crop, {})
        phi = crop_conf.get('phi', self.default_phi)
        theta = crop_conf.get('theta', self.default_theta)
        return phi, theta

    def project_price(self, crop: str, msp_real: float, q_current: float, q_lag3: float, eta: float = 0.0) -> float:
        """
        Computes the realized market price based on supply shock.
        
        P_c = MSP_real * (1 - phi * theta * S_c) * (1 + eta)
        where S_c = (Q_current - Q_lag3) / Q_lag3
        
        Defensive bounds: 0.1 * MSP <= Price <= 5.0 * MSP
        """
        # Defensive check: zero or missing lag supply
        if pd.isna(q_lag3) or q_lag3 <= 0:
            logger.warning(f"Invalid Q_lag3 ({q_lag3}) for {crop}. Assuming zero shock.")
            s_c = 0.0
        else:
            s_c = (q_current - q_lag3) / q_lag3

        phi, theta = self.get_coefficients(crop)
        
        # Calculate price
        sim_price = msp_real * (1.0 + (phi * theta * s_c)) * (1.0 + eta)
        
        # Clip to prevent extreme propagation
        min_price = msp_real * 0.1
        max_price = msp_real * 5.0
        return float(np.clip(sim_price, min_price, max_price))


def synthesize_market_prices(df: pd.DataFrame, random_seed: int = 42) -> pd.DataFrame:
    """
    Simulates real market prices based on Area * Yield shocks (Quantity).
    Maintains backward compatibility with M5 DataFrame pipeline.
    """
    np.random.seed(random_seed)
    df = df.copy()
    
    simulator = PriceSimulator()
    
    # Calculate Quantity (Supply) = Area * Yield
    # Note: If Area is missing, we must fallback to 1.0 just to reflect yield shock
    area = df.get('Area', pd.Series([1.0]*len(df), index=df.index))
    area = area.fillna(1.0)
    
    current_q = area * df['Yield']
    
    # Retrieve Lag3 Quantity (Area_lag3 * Yield_lag3)
    # If not present, we simulate a lag based on rolling mean
    if 'Yield_lag3_mean' not in df.columns or 'Area_lag3_mean' not in df.columns:
        df = df.sort_values(by=['District', 'Crop', 'Season', 'Year_start'])
        if 'Yield_lag3_mean' not in df.columns:
            df['Yield_lag3_mean'] = df.groupby(['District', 'Crop', 'Season'])['Yield'].shift(1).rolling(3, min_periods=1).mean()
        if 'Area_lag3_mean' not in df.columns:
            df['Area_lag3_mean'] = df.groupby(['District', 'Crop', 'Season'])['Area'].shift(1).rolling(3, min_periods=1).mean()
            
    lag_q = df['Area_lag3_mean'].fillna(1.0) * df['Yield_lag3_mean']
    
    sim_prices = []
    
    # Add random volatility (std dev = 0.05 => 5% random shock)
    noise_array = np.random.normal(0, 0.05, size=len(df))
    
    for i, (_, row) in enumerate(df.iterrows()):
        crop = row['Crop']
        msp = row.get('Real_MSP_per_Quintal', 1000.0) # default fallback
        
        q_curr = current_q.iloc[i]
        q_lag3 = lag_q.iloc[i]
        eta = noise_array[i]
        
        p = simulator.project_price(crop, msp, q_curr, q_lag3, eta)
        sim_prices.append(p)
        
    df['Real_Market_Price_per_Quintal'] = sim_prices
    
    return df
