# AgriIntel — Documented Boundary Conditions and Known Limitations

**Document Purpose:** In accordance with Section 2.2 and Section 4 of the AgriIntel Patent Remediation Plan (`AgriIntel_Patent_Fixes (1).md`), this document records explicit operational boundaries, statistical approximations, and non-claims for each novelty.

---

## 1. N4 — Offline Edge Capacity Escrow Tokens

### What Is Guaranteed:
- **Zero Commitment-Budget Oversubscription:** Under the cryptographic protocol assumptions (unforgeable server signature $K_s$, per-device HMAC key $K_d$, non-reusable token IDs, sequence continuity, and global commitment deduplication), the sum of admitted commitments across all kiosks is guaranteed not to exceed the centrally issued capacity budget.
- **Tamper Evidence:** Any modification, deletion, reordering, or insertion of entries in a kiosk's offline hash chain is detected during reconciliation.
- **Replay Protection:** Resubmitting an already-settled commitment ID or attempting to settle the same token across multiple kiosks is caught and rejected.
- **Idempotency:** Retried reconciliation requests for an already settled token safely return the cached settlement response without double-counting capacity.

### What Is NOT Guaranteed:
- **Physical Harvest vs. Market Capacity:** A cryptographic capacity token cannot guarantee that real-world physical harvest never exceeds mandi processing capacity. Unmodeled weather shocks, catastrophic pests, or extreme yield surges can cause physical volume to exceed forecasts.
- **Compromised Device Key Before Sync:** If an adversary compromises both the device software and the local symmetric key $K_d$ before any sync has occurred, the adversary can forge offline commitments up to the token's budget ceiling (though not beyond it). Hardware secure enclaves (TEE / TPM) are recommended for high-risk deployments.
- **Clock Skew on Disconnected Nodes:** Kiosks with untrusted or drifting hardware real-time clocks could record inaccurate timestamps. The central ledger mitigates this by rejecting commitments timestamped past `token.expires_at`, but subtle drift within the active window cannot be eliminated without trusted hardware RTCs.

---

## 2. N2 — Variance-Pooled Correlated Capacity Reservation (VPCR)

### What Is Guaranteed:
- **$O(L)$ Streaming Computational Complexity:** Incremental commitment and cancellation updates execute in $O(L)$ operations by maintaining an active gradient vector $\mathbf{G} = \mathbf{R} \mathbf{W}$, achieving a measured $2.6\times$ to $7.4\times$ speedup over $O(L^2)$ matrix recalculation across $L \in [10, 500]$.
- **Numerical Reversibility:** Cancelling an admitted commitment restores expected volume and portfolio variance to exact values within 64-bit IEEE 754 floating point tolerance, with drift eliminated via periodic full recomputations every 500 operations.
- **Upper Bound Recovery at $\rho = 1$:** When all spatial locations are perfectly correlated ($\rho = 1$), conservative production mathematically recovers the legacy sum-of-marginals upper quantile $\sum a_i y_{90}$ as an exact physical ceiling.

### What Is NOT Guaranteed:
- **Distribution-Free Quantile Invariance:** The conversion $\sigma_{\text{upper}} = (y_{90} - y_{50}) / 1.28155$ relies on a normal-approximation assumption for aggregate spatial harvest. For individual locations with extreme right-skew (e.g. onion yields with heavy tails), this is an engineering approximation. While empirical tests on 5,000 synthetic harvests demonstrated an exceedance rate of $11.88\%$ (close to the nominal $10.0\%$ target), it is not a formal distribution-free quantile bound.
- **Missing or Non-Stationary Spatial Correlation:** If historical spatial correlation $\mathbf{R}$ changes abruptly due to localized micro-climate disruptions or extreme climate change, the estimated portfolio variance will reflect historical rather than realized co-movements. The ledger enforces positive semi-definiteness via eigenvalue clipping, but accurate estimation requires sufficient historical observations.

---

## 3. N1 — Equilibrium-Sampled Randomised Recommendation (ESRR)

### What Is Guaranteed:
- **Target-Quota Invariance:** The aggregate target allocation vector $\mathbf{x}^* = \arg\min \Psi(\mathbf{x})$ is invariant to farmer arrival order for a given frozen scenario configuration.
- **Anti-Gaming Seed Reproducibility:** When `freeze_farmer_seed = True`, a farmer's pseudo-random seed is derived strictly from $\text{SHA256}(\text{scenario\_id} \,\|\, \text{farmer\_id})$. Farmers cannot alter recommendations by re-querying or varying transient inputs.

### What Is NOT Guaranteed:
- **Individual Outcome Invariance:** Individual farmer recommendations are **not** strictly invariant to arrival order. As prior farmers make commitments, residual quotas decrease, altering the conditional sampling distribution $\boldsymbol{\pi}_i$. The mechanism provides aggregate welfare robustness and reduced order sensitivity, not deterministic individual invariance across permutations.
- **Universal Profit Dominance:** ESRR optimizes social congestion potential to prevent market crashes; it does not guarantee higher individual farmer profit in all market conditions compared to unconstrained cash-crop concentration.

---

## 4. N6 — Slippage-Tolerant Advisory Quotes

### What Is Guaranteed:
- **Mitigation of Stale-Quote Retry Storms:** Under high concurrent contention, clients can commit quotes across revision increments without aborting, provided profit drift is within $\tau_{\text{rel}} = 5\%$ (or $\tau_{\text{abs}} = \text{INR } 500$) and crop rank does not drop.
- **Zero Retries for Tolerant Commits:** Tolerant commits execute in a single round-trip (1.0 RTT) with 0 retries, whereas standard optimistic concurrency control experiences severe retry storms (averaging 7.6 retries per commit under contention).

### What Is NOT Guaranteed:
- **Elimination of Aborts when Capacity Is Fully Exhausted:** If competing transactions completely exhaust available capacity for a crop, the transaction must fail closed (`CAPACITY_EXHAUSTED`). Slippage tolerance absorbs price and congestion drift, but never allows physical capacity violations.
