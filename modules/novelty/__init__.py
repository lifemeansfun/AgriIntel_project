"""AgriIntel Novelty Modules — Core Patentable Algorithmic Implementations.

This package provides:
- N1: Equilibrium-Sampled Randomised Recommendation (ESRR) (esrr.py)
- N2: Variance-Pooled Correlated Capacity Reservation (VPCR) (vpcr_ledger.py)
- N4: Escrowed Capacity Tokens for Offline Edge Commitment (edge_escrow.py)
- N6: Slippage-Tolerant Advisory Quotes (slippage_quote.py)
- Simulation and benchmarking suite (benchmarks.py)
"""

from .esrr import ESRRAllocator
from .vpcr_ledger import VPCRLedger
from .edge_escrow import EdgeEscrowManager, EdgeKioskNode
from .slippage_quote import SlippageQuoteEngine

__all__ = [
    "ESRRAllocator",
    "VPCRLedger",
    "EdgeEscrowManager",
    "EdgeKioskNode",
    "SlippageQuoteEngine",
]
