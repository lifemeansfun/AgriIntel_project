# AgriIntel Patent Disclosure — Pre-Filing Fixes

**Scope:** Fixes identified in the review of the Invention Disclosure dated October 28, 2026.
**Caveat:** This is a working checklist, not legal advice. Review with a registered patent agent or attorney. No prior-art search has been run.

---

## 0. Strategy Summary

| Novelty | 3(k) / §101 risk | Recommended role |
|---|---|---|
| N4 Escrow tokens | Low | Lead independent claim (narrowed) |
| N2 VPCR | Medium | Independent claim, if O(L) benefit is demonstrated |
| N2 + N4 combined | Low-Medium | Strongest single system claim |
| N6 Slippage quotes | Medium-high | Dependent claim |
| N1 ESRR | High | Dependent claim, or keep as trade secret |
| N5 DP guard band, N9 NDVI discounting | Unassessed | Candidates to promote if mechanisms are specified concretely |

Key legal frame: Section 3(k) excludes mathematical methods, business methods, algorithms and programs *per se*. The 2025 CRI Guidelines require a concrete, measurable **technical effect** (e.g., speed, security, real-time control) and enabling disclosure. Business methods are treated as an absolute bar.

---

## 1. Remove Overclaiming

- [ ] **N4 "mathematically guaranteed zero overflow"**
  - Problem: Holds only relative to the modelled y90 bound. Real yields can exceed it.
  - Fix: Claim "zero overflow of committed capacity relative to the modelled capacity ceiling."
- [ ] **N2 "exactly reverses" the gradient and variance on cancellation**
  - Problem: Floating-point arithmetic makes reversal numerically approximate.
  - Fix: Use "restores" or "reverses within numerical tolerance." Optionally add periodic recomputation to bound drift.
- [ ] **N1 / Claim 3 "invariant to the arrival sequence"**
  - Problem: Probabilities depend on `committed_c`, which depends on arrival order.
  - Fix: Replace with "reduces sensitivity to arrival order." Back it with a measured order-sensitivity metric (variance of outcome across permutations).
- [ ] **N1 "cryptographically verifiable"**
  - Problem: Verifiability only holds if all seed inputs are logged. A 32-bit seed is for auditability, not security.
  - Fix: Say "deterministically reproducible for audit" and specify what is logged.
- [ ] **N1 gaming risk**
  - Problem: Seed includes area `a_i` and revision, so a farmer can vary inputs to resample.
  - Fix: Document a mitigation (e.g., fix the seed per farmer per scenario window, or rate-limit re-queries) and consider claiming it.

---

## 2. Strengthen the Technical Effect

### N4 — Escrow tokens
- [ ] **Hash chain is tamper-evident but not forgery-resistant.** H₀ = SHA256(token_id) is derivable by anyone, so a compromised kiosk can rewrite its whole chain.
  - Fix: Add a per-entry signature or MAC under a device key, and/or anchor the chain head periodically.
- [ ] Specify token format, expiry handling, replay protection, and idempotency keys.
- [ ] Specify how unused escrow is reclaimed and how expired tokens are treated at settlement.
- [ ] Add a metric table: overflow rate, reconciliation success, tamper-detection rate, settlement latency.

### N2 — VPCR
- [ ] **Prove the O(L) benefit.** Full recomputation of wᵀRw is O(L²).
  - Fix: Add microbenchmarks (latency and CPU vs. full recomputation across L = 10, 50, 100, 500).
  - If real L is small, lead with correctness and exact reversibility rather than speed.
- [ ] State how **R is kept positive semi-definite** (estimation, shrinkage, projection).
- [ ] State the **distributional assumption** behind the z-quantile approximation and its limits.
- [ ] Reframe the +4.6% to +15% acreage gain as *supporting* evidence, not the technical effect. Report how the range was obtained.

### N6 — Slippage quotes
- [ ] Reframe the problem as a **stale-state / retry-storm problem in concurrent ledger commits** (measurable: retries per commit, commit success rate, p95 latency), not as farmer utility.
- [ ] Rename "livelock" only if you can show a livelock; otherwise say "repeated stale-quote rejection."
- [ ] Add a benchmark of rejection and retry rates under concurrency, with and without tolerance.

### N1 — ESRR
- [ ] Decide: dependent claim, or trade secret (infringement is hard to detect from outside, and the output is randomized).
- [ ] If kept, separate economic outcomes from system metrics and avoid profit as the headline effect.

---

## 3. Claim Drafting Fixes

- [ ] **Claim 1 (VPCR)**
  - Replace "regional market carrying capacity" with a physical or computational resource (storage / mandi throughput) enforced by an admission-control mechanism.
  - Frame the claim around ledger state, incremental update, and atomic admission.
  - Put quantile and economic details into dependent claims.
- [ ] **Claim 2 (Escrow)**
  - Remove "thereby guaranteeing zero aggregate capacity overflow." Use the narrowed wording from Section 1.
  - Add the signature/MAC element from Section 2.
- [ ] **Claim 3 (ESRR)**
  - Remove "social congestion potential function" from the independent claim.
  - Remove "invariant to the arrival sequence."
  - Consider demoting to a dependent claim.
- [ ] **New combined claim:** escrow tranches sized from VPCR correlation-aware headroom, with token issuance, offline admission against the tranche, and hash-chained settlement.
- [ ] Add dependent claims: slippage-tolerant execution (N6), seeded audit sampling (N1), reversal on cancellation (N2).
- [ ] Add a tie to concrete hardware/system elements (edge device, central ledger server, network link, memory) rather than a generic "computer."

---

## 4. Enablement Gaps to Fill

- [ ] **Forecasting model:** how y50 and y90 are produced (model type, features, training data sources, calibration, quantile method).
- [ ] **Price model parameters:** how φ, θ, S_ref, P_ref are calibrated; data sources.
- [ ] **Data structures:** ledger schema, gradient vector layout, token schema, hash-chain payload canonicalization.
- [ ] **Protocols:** settlement protocol, conflict resolution, failure and retry handling.
- [ ] **Worked examples** with actual numbers for each claimed novelty.
- [ ] Include pseudocode for each independent claim.

---

## 5. Strengthen the Evidence

- [ ] Replace the single-seed, 20-permutation, single-scenario N1 benchmark with multiple scenarios, multiple seeds, and confidence intervals.
- [ ] Note that the current simulation uses the same price model the algorithm optimizes. Add at least one evaluation on independent or held-out data.
- [ ] Report the N1 gain honestly: about ₹5.2k on about ₹740k (roughly 0.7%).
- [ ] Add system metrics for every novelty: latency, memory, overflow rate, rejection rate, retries.
- [ ] Record benchmark environment, code version, and seeds so results are reproducible for an examiner.

---

## 6. Prior-Art Search (before final claims)

- [ ] Distributed **escrow transactions, demarcation protocols, bounded counters / CRDTs, token buckets**
- [ ] **Hash-chained logs, signed capability tokens, offline-first settlement**
- [ ] **Incremental portfolio variance / marginal VaR** computation
- [ ] **Optimistic concurrency control with validation tolerance; AMM / DEX slippage**
- [ ] **Congestion / potential games, capacity-aware or herding-aware recommender systems, randomized routing recommendations**
- [ ] Agricultural advisory and crop-allocation patents (India, US, EP, CN)

---

## 7. Process and Compliance

- [ ] **Section 39, Indian Patents Act:** an Indian resident generally must file first in India (and wait the required period) or obtain Controller permission before filing abroad. Confirm with counsel before any US filing.
- [ ] **No public disclosure** (GitHub, talks, papers, demos, social posts) before the provisional is filed.
- [ ] **Strip local file paths** (`file:///c:/Users/...`) and internal references from anything filed.
- [ ] Confirm **ownership** (employer, institution, or personal) and list correct **inventors**.
- [ ] Note the **12-month window** to convert a provisional to a complete specification; set a calendar reminder.
- [ ] For the US, plan for **Alice/Mayo** arguments: lead with N4 and N2+N4 as improvements to computer functionality.

---

## 8. Housekeeping in the Disclosure

- [ ] Fix the Master Novelty Inventory priority labels (e.g., N6 listed as "Tier 1 (★★)").
- [ ] Clarify "9/9 passed" tests and map each test to a claimed feature.
- [ ] Reassess N5 (DP guard band) and N9 (NDVI/remote-sensing discounting) for promotion: privacy-preserving bounds and signal processing fit recognized technical-effect categories if specified concretely.
- [ ] Keep unimplemented specs (N3, N7, N8) out of the first filing unless they are fully enabled.

---

## Suggested Order of Work

1. Prior-art search (Section 6)
2. Fix overclaiming and add the signature mechanism (Sections 1 and 2)
3. Run the extra benchmarks (Section 5)
4. Fill the enablement gaps (Section 4)
5. Redraft the claims (Section 3)
6. Complete the process checks and file the provisional (Section 7)
