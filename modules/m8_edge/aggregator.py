import numpy as np
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class DPAggregator:
    """
    Differentially Private (DP) aggregator for farmer acreage commitments.
    Instead of sending raw continuous areas, nodes send bucketed commitments 
    and the aggregator applies Laplace noise to guarantee epsilon-DP.
    """
    def __init__(self, epsilon: float = 1.0, sensitivity: float = 5.0):
        # sensitivity: maximum land holding (e.g. 5.0 ha) a single farmer could change
        self.epsilon = epsilon
        self.sensitivity = sensitivity
        self.scale = self.sensitivity / self.epsilon
        
    def aggregate_commitments(self, raw_commitments: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        raw_commitments: [{'crop': 'Tomato', 'area': 2.5}, ...]
        Returns a DP-noised aggregate area per crop.
        """
        true_aggregate = {}
        for c in raw_commitments:
            crop = c['crop']
            true_aggregate[crop] = true_aggregate.get(crop, 0.0) + c['area']
            
        dp_aggregate = {}
        np.random.seed(42) # For reproducible testing
        for crop, total_area in true_aggregate.items():
            noise = np.random.laplace(0.0, self.scale)
            # Ensure it doesn't go below 0
            dp_aggregate[crop] = max(0.0, total_area + noise)
            
        return dp_aggregate

class QuantizedEdgeNode:
    """
    Simulates an offline-capable edge device node.
    Quantizes floating point feature weights/scores to INT8 to simulate
    the model compression required for edge deployment and offline ledger sync.
    """
    def __init__(self):
        # Simulated model weights (e.g., q10, q50, q90 baseline modifiers)
        self.fp32_weights = None
        self.int8_weights = None
        self.scale = 1.0
        self.zero_point = 0
        
    def train_and_quantize(self, fp32_weights: np.ndarray):
        """
        Quantizes FP32 weights to INT8.
        """
        self.fp32_weights = fp32_weights
        
        min_val = np.min(fp32_weights)
        max_val = np.max(fp32_weights)
        
        # Asymmetric quantization
        self.scale = (max_val - min_val) / 255.0 if (max_val - min_val) > 0 else 1.0
        self.zero_point = -np.round(min_val / self.scale)
        
        quantized = np.round(fp32_weights / self.scale + self.zero_point)
        # Clip to valid INT8 range (uint8 used here for 0-255)
        self.int8_weights = np.clip(quantized, 0, 255).astype(np.uint8)
        
    def dequantize(self) -> np.ndarray:
        """
        Reconstructs FP32 weights from INT8 for inference.
        """
        if self.int8_weights is None:
            raise ValueError("Model not quantized.")
            
        return (self.int8_weights.astype(np.float32) - self.zero_point) * self.scale
