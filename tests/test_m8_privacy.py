import pytest
import numpy as np

from modules.m8_edge.aggregator import DPAggregator, QuantizedEdgeNode

def test_dp_utility_loss():
    # IV&V Stress Test 6.1: Utility loss <= 5%
    # We will simulate the aggregator receiving 1000 farmer commitments.
    
    np.random.seed(42)
    raw_commitments = []
    
    # Simulate 1000 farmers committing between 1 to 5 hectares each
    for i in range(1000):
        raw_commitments.append({
            'crop': 'Tomato',
            'area': np.random.uniform(1.0, 5.0)
        })
        raw_commitments.append({
            'crop': 'Onion',
            'area': np.random.uniform(1.0, 5.0)
        })
        
    # True aggregate
    true_agg = sum(c['area'] for c in raw_commitments if c['crop'] == 'Tomato')
    
    # DP Aggregate with epsilon=1.0, sensitivity=5.0
    aggregator = DPAggregator(epsilon=1.0, sensitivity=5.0)
    dp_agg = aggregator.aggregate_commitments(raw_commitments)
    
    # Calculate utility loss as absolute percentage error
    error = abs(true_agg - dp_agg['Tomato']) / true_agg
    
    # Since n=1000, total area is ~3000. Laplace noise scale = 5.0 / 1.0 = 5.0. 
    # Expected noise is ~ 5.0, which is < 1% of 3000.
    assert error <= 0.05, f"DP Utility Loss {error * 100:.2f}% exceeds 5% threshold."

def test_edge_quantization_precision():
    # IV&V Stress Test 6.2: Pearson correlation >= 0.98
    
    np.random.seed(42)
    # Simulate 10,000 model weights from a normal distribution
    fp32_weights = np.random.normal(loc=1.5, scale=2.5, size=10000)
    
    node = QuantizedEdgeNode()
    node.train_and_quantize(fp32_weights)
    
    reconstructed_weights = node.dequantize()
    
    # Calculate Pearson correlation coefficient
    corr = np.corrcoef(fp32_weights, reconstructed_weights)[0, 1]
    
    assert corr >= 0.98, f"Quantization correlation {corr:.4f} is below 0.98 threshold."
