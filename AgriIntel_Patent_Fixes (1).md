# AgriIntel — Patent Disclosure Fixes and Technical Remediation Plan

**Purpose:** Convert the current AgriIntel invention disclosure into a technically defensible, evidence-backed document for review by a qualified patent professional.

**Status:** Working remediation plan — not a legal opinion, patentability guarantee, or substitute for a formal prior-art search.

**Date:** 28 October 2026

---

## 1. Executive priorities

Do not file the current disclosure unchanged. First correct technical claims, validate the implementation, and narrow the proposed inventions to specific mechanisms that can be distinguished from prior art.

### Priority order

1. **N2 — Variance-Pooled Correlated Capacity Reservation (VPCR):** repair the yield-quantile assumptions and validate the aggregate risk estimate.
2. **N4 — Offline Edge Capacity Escrow:** replace the unconditional “zero physical overflow” claim with a precisely scoped capacity-budget guarantee; specify token security and reconciliation.
3. **N1 — Equilibrium-Sampled Randomised Recommendation (ESRR):** remove unsupported arrival-order-invariance claims and define exactly what is invariant.
4. **N6 — Slippage-Tolerant Advisory Quotes:** specify its concurrency-control contribution and demonstrate an advantage over standard stale-version checks and retry policies.
5. **N3/N5/N7/N8/N9:** keep as research candidates until their mechanisms and experimental evidence are complete.

A name, formula, combination of known methods, passing unit tests, or positive benchmark result does not by itself establish novelty, inventive step, or patent eligibility.

---

## 2. Required global changes to the disclosure

### 2.1 Separate facts, hypotheses, and legal conclusions

For every novelty, use separate headings:

- **Implemented:** code exists and its version/commit can be identified.
- **Tested:** tests and test conditions are documented.
- **Measured:** results come from reproducible experiments.
- **Hypothesized:** expected benefit not yet demonstrated.
- **Prior-art status:** unknown until a documented search and claim comparison are complete.

Replace “patentable novelty,” “solves,” “guarantees,” “exact,” and similar absolute wording wherever evidence does not support it.

### 2.2 Add an implementation traceability table

For each claimed feature, record:

| Field | Required content |
|---|---|
| Novelty ID | N1, N2, etc. |
| Source files | Exact repository-relative paths |
| Version | Git commit hash or release tag |
| Inputs/outputs | Data types, units, and validation rules |
| Algorithm | Pseudocode plus equations with defined variables |
| Tests | Test names, test data, expected outcomes |
| Benchmarks | Script, configuration, random seeds, raw results |
| Assumptions | Statistical, network, security, and operational assumptions |
| Known limitations | Cases not covered by the claimed guarantee |

Do not state that “9/9 tests passed” as evidence of correctness unless the test report, test names, environment, and commit are retained.

### 2.3 Correct filing language

Keep legal assessment separate from technical results. In particular:

- Do not state that a technical effect automatically avoids Section 3(k) of the Indian Patents Act.
- Do not assume that Indian eligibility conclusions transfer to US law.
- Do not describe proposed or unimplemented architecture as an implemented invention.
- Do not state that benchmark results prove novelty or non-obviousness.
- Have a qualified patent professional review the current law, claim scope, filing sequence, and all priority deadlines.

---

## 3. N1 — Equilibrium-Sampled Randomised Recommendation (ESRR)

### 3.1 Main defect to resolve

The disclosure calls ESRR “arrival-order-invariant,” but its stated per-farmer probability depends on `committed_c`, and its seed includes a ledger `revision`. Both may change when commitments arrive in a different order. An order-independent aggregate target vector does **not** establish order-independent recommendation probabilities or individual outcomes.

### 3.2 Define the invariance claim precisely

Choose and test one of these claims; do not use them interchangeably:

1. **Target-quota invariance:** the target aggregate allocation vector is identical for the same scenario inputs, regardless of request order.
2. **Expected aggregate invariance:** expected aggregate crop allocations remain the same across request orders under a stated probability model.
3. **Individual outcome invariance:** a given farmer receives the same recommendation under different request orders.
4. **Welfare robustness:** aggregate utility changes by no more than a defined tolerance across request orders.

Individual outcome invariance is substantially stronger and is not currently supported by the described state-dependent sampling rule.

### 3.3 Implementation fixes

- Compute the aggregate equilibrium target from a frozen scenario snapshot with a documented version identifier.
- Separate the equilibrium calculation from the online commit/validation transaction.
- Define whether recommendations are generated independently, in a batch, or sequentially against residual quotas.
- If a seed is intended to be stable for a farmer and scenario, do not include a mutable ledger revision in that seed. If revision changes are intended to change the result, state that this is **not** strict order invariance.
- Document deterministic tie-breaking, quota exhaustion, farmer cancellation, and retries.
- Verify that `pi_i` (probability vector) is normalized, non-negative, and has a defined fallback when every crop has zero weight.
- Define the units and meaning of `Profit`, `headroom`, `committed`, and `CA`; guard against negative or non-finite values.

### 3.4 Experimental fixes

Run at least the following comparisons using the same generated farmer cohorts and scenario inputs:

- Static baseline.
- Existing sequential greedy baseline.
- ESRR as implemented.
- A batch/centralized allocation baseline, where feasible.

Across each cohort, vary arrival order, cohort size, area distribution, agronomic suitability, crop prices, and capacity tightness. Report the number of trials, mean, standard deviation, confidence interval, worst-case result, and compute time. Keep random seeds and raw outcomes.

Report separately:

- change in aggregate profit;
- variation in crop allocation totals across order permutations;
- per-farmer outcome changes;
- rejection rate and unused capacity;
- inequality or dispersion in farmer outcomes, if fairness is claimed.

### 3.5 Safer wording until validated

> “The system computes an aggregate crop-allocation target from a scenario-level objective and generates farmer recommendations using residual capacity and farmer-specific agronomic inputs. The extent to which aggregate allocations or individual recommendations are invariant to request ordering is evaluated under the stated experimental protocol.”

Do not state that recommendations “converge to the social equilibrium invariant to arrival sequence” unless a proof or appropriately scoped formal result supports that statement.

---

## 4. N2 — Variance-Pooled Correlated Capacity Reservation (VPCR)

### 4.1 Correct the quantile conversion

The current equation

```text
sigma_upper = (y90 - y50) / 1.28155
```

uses a normal-distribution relationship between the median and the 90th percentile. It is not a distribution-free estimator of standard deviation and does not generally preserve bounds for skewed yields.

**Action:** remove claims that this conversion is exact for skewed distributions. Treat it as a normal-approximation assumption only if that assumption is tested and documented.

### 4.2 Define the aggregate uncertainty model

If location-level yield errors have standard deviations `sigma_l`, areas `a_i`, and a valid correlation matrix `R`, define a clearly dimensioned weight vector, for example:

```text
W[l] = sum over commitments i in location l of area_i * sigma_i
variance = W.T @ R @ W
```

Then define the aggregate-production estimate and the capacity threshold separately. The exact formula depends on the chosen statistical model; document whether the result is a normal approximation, an empirically calibrated quantile, or a different bound.

Required checks:

- `R` is symmetric within tolerance.
- `R` has unit diagonal when it represents a correlation matrix.
- `R` is positive semidefinite, or a documented repair/estimation method is used.
- All units are consistent (e.g. tonnes, hectares, tonnes/hectare).
- Location aggregation does not double-count commitments.
- Missing correlations, sparse regions, new locations, and uncertain correlation estimates have defined handling.

Do not describe an estimated `z_0.90 * standard_deviation` threshold as a guaranteed upper bound without assumptions that justify that guarantee.

### 4.3 Verify incremental updates

For `V = W.T @ R @ W`, adding `delta` to coordinate `l` gives:

```text
V_new = V_old + 2 * delta * (R @ W_old)[l] + delta**2 * R[l, l]
```

For a cancellation, apply the same update with the negative delta against the **current** state, or restore a recorded pre-commit state using a validated transaction log. Be careful not to use an incorrectly signed inverse expression.

The gradient update is:

```text
G_new = G_old + delta * R[:, l]
```

and the maintained invariant should be:

```text
G == R @ W
V == W.T @ R @ W
```

Add property-based tests that compare every incremental add/remove sequence to a full recomputation within a numeric tolerance. Include repeated cancellation, duplicate operations, concurrent commits, and floating-point drift.

### 4.4 Validate the risk target empirically

On held-out historical or simulated harvests:

1. Fit or calibrate the location yield distributions and spatial dependence model using training data only.
2. Compute the proposed reservation ceiling.
3. Measure how often realized aggregate harvest exceeds the ceiling.
4. Compare observed exceedance frequency against the chosen risk level, with uncertainty intervals.
5. Compare against the sum-of-individual-quantiles baseline and simpler aggregate models.
6. Report capacity utilization and overflow risk jointly; capacity gained is not a benefit if it materially increases the measured risk.

Do not generalize one Ragi/Coimbatore example to all crops and regions.

### 4.5 Safer claim language

> “The system maintains an incremental estimate of aggregate production variance using a configured spatial dependence model and uses the estimate in a capacity-admission rule. The calibration assumptions and observed exceedance rate are specified for the applicable crop and region.”

Only claim a specific risk level when the mathematical assumptions and validation support it.

---

## 5. N4 — Escrowed Capacity Tokens for Offline Edge Kiosks

### 5.1 Narrow the guarantee

Replace:

> “Mathematically guaranteed zero overflow” / “Global overflow observed: 0.00%” as an unconditional physical-harvest guarantee.

With a scoped statement such as:

> “Under the assumptions that each capacity token has a unique, non-reusable identifier, token ceilings are disjoint and collectively do not exceed the centrally allocated budget, each kiosk enforces its ceiling, and all admitted commitments are included exactly once, the protocol prevents admitted commitments from exceeding the sum of the issued token budgets. This is a budget-enforcement guarantee; it does not guarantee that realized harvest remains below the market-capacity estimate.”

A probabilistic yield forecast cannot guarantee that actual harvest never exceeds its estimate.

### 5.2 Specify the threat model and protocol

The disclosure must state whether the threat model includes accidental duplication, malicious kiosk software, stolen device credentials, clock manipulation, disk rollback, replay, a compromised central server, or a compromised signing key. Do not imply protection against threats that are not addressed.

Define the token fields and their semantics, including at least:

- globally unique token identifier;
- crop and geographic scope;
- allocated budget and unit;
- authorized device/kiosk identity;
- issue time and expiry semantics;
- issuer key identifier and signature/MAC scheme;
- protocol version;
- revocation or reallocation rules;
- server-side status to prevent reuse.

Use a cryptographically appropriate authenticated token format. Explain whether the server and kiosks share a secret or use public-key signatures; do not refer to HMAC as a public-verifiable signature.

### 5.3 Hash-chain corrections

A hash chain can reveal changes only when the chain is compared to a trusted state or a trusted checkpoint. Specify how a chain head is anchored, for example through signed checkpoints or a protected monotonic state where available. State clearly what happens if the device is compromised before synchronization.

Define canonical serialization, timestamp handling, sequence numbers, device identity, authentication tags/signatures, and how server-side deduplication works. A hash alone is not proof that a commitment was authorized by the correct device.

### 5.4 Reconciliation state machine

Specify the state transitions for each token, such as:

```text
ISSUED -> ACTIVE_OFFLINE -> SUBMITTED -> VALIDATED -> SETTLED
                             |-> REJECTED
```

The exact states may differ, but every transition must be idempotent. Include explicit outcomes for expired tokens, duplicated logs, partial uploads, sequence gaps, invalid signatures, conflicting commitment IDs, and capacity-budget inconsistencies.

Never release unused escrow until the server has established which commitments were accepted and the token can no longer be used offline. Explain how token expiry and an offline device with an incorrect clock are handled.

### 5.5 Required adversarial tests

- Duplicate-token reuse by two kiosks.
- Replay of an already settled commitment.
- Modified, reordered, deleted, and duplicated records.
- Full chain reconstruction from a modified local database.
- Lost acknowledgement and retried synchronization.
- Expired token used while disconnected.
- Compromised or cloned kiosk identity.
- Two kiosks attempting to spend overlapping budget.
- Partial server failure during settlement.

Report **commitment-budget oversubscription** separately from **physical harvest exceeding forecast**. They are different metrics.

### 5.6 Safer claim language

> “A central system partitions an allocated commitment budget into device-scoped quotas, and disconnected edge devices admit authenticated commitments subject to their local quota. During reconciliation, the central system verifies token status and commitment identifiers, rejects duplicate or unauthorized entries, and settles accepted commitments idempotently.”

Use “prevents quota oversubscription under the stated protocol assumptions” only after the design and tests establish that property.

---

## 6. N6 — Slippage-Tolerant Advisory Quotes

### 6.1 Define the technical problem

Avoid asserting that ordinary stale quotes necessarily cause “livelock.” Define the failure pattern, such as repeated rejection and retry under concurrent updates, and measure its frequency and cost.

### 6.2 Define exact execution semantics

Document:

- what data is frozen in the quote snapshot;
- which version/revision is recorded;
- how `slippage` is calculated for positive, negative, zero, or near-zero quoted profits;
- how profit-sign changes are treated;
- how the ranking metric and tie-breaks are defined;
- when capacity is checked and atomically reserved;
- whether quote acceptance is idempotent;
- the precise meaning of `tau_slippage` and rank tolerance;
- what happens when the crop remains within the score tolerance but no longer has capacity.

A percentage rule alone may be unreliable for quoted profits near zero. Use a documented absolute/relative tolerance policy if appropriate, and test its behaviour rather than choosing thresholds only from a successful example.

### 6.3 Compare with credible baselines

Compare strict version rejection, ordinary retry/backoff, refresh-on-conflict, and the proposed tolerance method under the same workload. Measure successful transaction rate, median and tail latency, retry count, rejected commitments, capacity violations, and change in realized utility.

Do not claim that an 8.41% observed slippage proves livelock is “completely eliminated.” Report the number of trials and workload conditions.

---

## 7. N3, N5, N7, N8, and N9 — Minimum work before claims

| Candidate | Required technical completion |
|---|---|
| N3 — Batch-window min-cost flow | Give the graph definition, nodes/edges, costs, constraints, objective, tie-breaking and complexity. Compare its result and latency to established min-cost-flow implementations. Explain what is technically distinctive beyond using the known algorithm. |
| N5 — Differential-privacy guard band | Specify the privacy mechanism, sensitivity, noise distribution, privacy parameters, threshold formula and assumptions. Derive and test the probability of exceeding the capacity threshold after noise is added. |
| N7 — Copula downside score | Specify marginal distributions, dependence estimation, calibration, tail-risk statistic, fallback for sparse data and comparative results against simpler risk metrics. State what is new in the actual computation. |
| N8 — Mondrian conformal abstention | Define the nonconformity score, calibration split, grouping rule, exchangeability assumptions, coverage target, abstention threshold and fallback. Do not claim formal coverage outside the assumptions of the method. |
| N9 — Reliability-weighted ledger | Specify the update equation, evidence source, observation lag, treatment of missing or noisy satellite measurements, commitment feedback loop and safeguards against biased or manipulated observations. Compare with conventional Bayesian updating and remote-sensing workflows. |

Until this work is completed, label these sections **“proposed research directions — not yet implementation-verified”** and do not present them as established patentable inventions.

---

## 8. Revised claim-development approach

The current claim skeletons should be treated as drafting notes, not filing-ready claims. Do not expand the independent claims to cover generic optimization, cryptographic ledgers, or offline token systems.

### Candidate A — Capacity estimation and admission

Potential claim focus, subject to prior-art search and validation:

- specific agricultural commitment records with explicit units and locations;
- a defined spatial-dependence representation;
- a particular incremental state update tied to a validated aggregate production estimator;
- a concrete admission transaction that compares the calibrated estimate with a configured regional budget;
- defined handling of cancellation and concurrent updates.

The core claim must say more than “compute variance, calculate a quantile, and admit a booking.”

### Candidate B — Offline quota reconciliation

Potential claim focus, subject to prior-art search and security testing:

- centrally partitioned, device-scoped agricultural commitment quotas;
- authenticated offline records linked to a trusted state/checkpoint;
- explicit replay prevention and idempotent settlement;
- safe reclamation of unused quota without allowing a disconnected token to be reused;
- interaction with the regional capacity ledger.

The core claim must say more than “issue token, hash records, and synchronize later.”

### Candidate C — Recommendation mechanism

Do not use “arrival-order-invariant” in an independent claim until the defined invariance property is proved or experimentally established under clearly stated assumptions. If the actual mechanism is sequential, acknowledge its state dependence and identify a narrower technical contribution.

### Claim drafting checklist

Before drafting a final independent claim, answer:

1. What concrete technical problem is solved?
2. Which exact steps or structures solve it?
3. Which step distinguishes the claim from each closest reference?
4. What technical effect follows from those steps, and how is it measured?
5. Are the details enabled by the written description and implemented or at least fully specified?
6. Does the claim depend on assumptions that are absent from the disclosure?
7. Is the claim too broad, or does it only recite a desired result?
8. Could the claim be excluded as a mathematical method, algorithm, business method, computer programme per se, or method of agriculture under the applicable law?

Have a qualified patent professional resolve the legal questions and final claim scope.

---

## 9. Reproducible evidence packet

Create a versioned folder with the following artefacts before the next patent review:

```text
patent_evidence/
  README.md
  implementation_manifest.csv
  environment.txt
  test_report.txt
  benchmark_config.json
  raw_results/
  processed_results/
  plots/
  prior_art_matrix.csv
  known_limitations.md
```

### Benchmark report requirements

For every claimed improvement, include:

- exact source commit and command used to run it;
- hardware, software environment, and dependency versions;
- source dataset and train/validation/test separation, where relevant;
- baseline implementation details;
- number of repetitions and random seeds;
- mean, median, standard deviation, confidence intervals, and worst-case results where appropriate;
- runtime and memory measurements for claimed computational improvements;
- failure cases and negative results;
- raw machine-readable output.

Do not write “proved faster,” “zero risk,” or “guaranteed” based solely on a small simulation. Use formal proofs only for properties whose assumptions and scope are explicitly stated; use empirical language for measured outcomes.

---

## 10. Prior-art and filing workflow

1. Search patent publications and non-patent literature for each proposed independent claim, not just each novelty name.
2. Build a claim chart with one row per required claim limitation and one column per relevant reference. Record whether each limitation is explicitly disclosed, implicitly disclosed, or absent; have the patent professional assess the legal significance.
3. Search priority dates, publication dates, family members, citations and relevant classifications. Verify references from official patent-office or publisher sources before relying on them.
4. Separate the proposed inventions if they lack a single inventive concept. Do not assume all nine concepts should be filed together.
5. Keep details confidential until an appropriate filing strategy has been selected. Check public repositories, presentations, demonstrations, competition submissions and any other disclosures that may affect rights.
6. Get jurisdiction-specific advice for India and any intended overseas filing. A provisional filing only supports subject matter sufficiently disclosed in it; later-added technical matter may not receive the earlier priority date.

This plan does not determine whether AgriIntel is patentable. A formal legal assessment requires a current prior-art search, a review of the actual implementation and a claim-by-claim analysis.

---

## 11. Immediate action checklist

- [ ] Remove the unconditional “zero physical overflow” guarantee from N4.
- [ ] Correct N2's unsupported normal-quantile and skewed-distribution statements.
- [ ] Verify VPCR incremental add/remove updates against full recomputation.
- [ ] Define the exact order-invariance property claimed by N1.
- [ ] Remove mutable revision from the ESRR seed if strict seed stability is a requirement, or narrow the claim accordingly.
- [ ] Add adversarial token/replay/reconciliation tests for N4.
- [ ] Benchmark N6 against standard optimistic concurrency and retry baselines.
- [ ] Mark N3/N5/N7/N8/N9 as unverified until specifications and tests exist.
- [ ] Add implementation versions, raw results, configs, and limitations.
- [ ] Obtain a documented claim-by-claim prior-art search.
- [ ] Ask a qualified patent professional to review claim eligibility, unity, support and filing sequence.

## 12. Recommended next milestone

Produce a **corrected technical disclosure** for N2 and N4 only, supported by code, formula validation, adversarial tests and a claim chart against the closest references. Reassess whether the two form one inventive concept or should be developed separately. Revisit N1 only after its invariance property is defined precisely and verified.
