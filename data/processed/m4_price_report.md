# Module 4 Structural Price Simulation Report

> **Methodological Note:** Due to the absence of historical mandi transaction data, market prices are modeled structurally rather than empirically forecasted. The model propagates yield shocks via an assumed price elasticity.

## Structural Assumptions
- **Price Anchor:** Government Minimum Support Price (Real MSP)
- **Yield-Price Elasticity:** $\epsilon = 0.2$ (A 10% yield surplus causes a 2% price drop)
- **Uncertainty Propagation:** $P_{bound} = MSP \times (1 - \epsilon \times Yield\_Shock_{bound})$

*Note: Pinball loss and empirical coverage metrics are intentionally omitted as the price target is a structural simulation, not an observed ground truth.*