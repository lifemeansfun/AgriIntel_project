Recommend repairing forecasting and economics before integrating a bounded regional simulation. Credible national deployment is presently unsupported. The strongest reason is that the validation inputs violate the claimed historical information boundary: features.py:43 rolls across the concatenated shifted series, while lines 62–66 calculate fallback means using all supplied years. Grouping also omits State, risking collisions when district names repeat nationally.

Verified by inspection: the advisory serves cached records from the global latest dataset year; feedback uses one hardcoded district context (backend/main.py:25). Ledger commits check total hectares but never crop headroom; recommendation and commit occur separately (supply_ledger.py:112, online_allocator.py:67–75). Thus its lock does not establish the advertised crop-cap invariant.

Reported evidence: the packet’s worse-than-baseline yield/profit-ranking results and recorded probes strengthen this rejection; I did not rerun them. Unknown: corrected prospective accuracy, nationwide joined coverage, empirical price response, nonadopter supply, and actual farmer benefits.

The strongest alternative is a geographically qualified service that abstains where evidence is missing, using historical-yield baselines, independently grounded costs/prices, and simple acreage caps before introducing comparative-advantage allocation.

The most consequential failure is presenting fictitious coordination safety: the allocator can accept acreage beyond its own modeled threshold, and those thresholds themselves depend on unvalidated market assumptions.

The cheapest falsifying check is a tiny synthetic prefix-invariance test: alter future observations, reorder unrelated groups, and introduce identical district names in different states. Earlier features must remain unchanged. Any violation stops forecasting claims and national expansion until repaired. A separate stale-recommendation test must reject over-cap commits atomically; passing either check establishes engineering correctness only.
