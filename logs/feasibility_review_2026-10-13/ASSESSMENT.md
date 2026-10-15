**AgriIntel feasibility assessment — 13 October 2026**

The feedback architecture is not integrated into the active advisory flow. Connecting it is feasible engineering work, but current components need correctness and economic-contract repairs. Nationwide selected-crop forecasting is plausible conditional on audited data and fresh evaluation; uniform reliable profit forecasts and glut prevention for every jurisdiction are unsupported.

Evidence status: code inspected at v3-invention / 9881127; saved metrics were recomputed earlier in this chat. Current work ran isolated correctness examples and six existing tests. Five fresh-context advisors and five fresh reviewers completed the coding-research-council workflow in waves, sharing the configured model and filesystem. Their agreement is not independent empirical validation. No model retrained, countrywide data acquired, field outcomes collected, deployment performed or application code changed.

**Integration scope and verified blockers**

The active backend serves saved 2019 recommendations; React calls location/recommendation endpoints. The demonstration ledger is one fixed Tomato/Onion district. Tomato is absent from the main cleaned and recommendation data. M3 saves historical out-of-fold predictions, rather than a deployable model and current feature/inference service. See backend/main.py:19–41,74–101,150–183; frontend/src/services/api.js:4–23; modules/m3_yield/ensemble.py:166–168.

Parent probes verified: direct 600 ha Tomato commit despite a 525 ha modeled cap; negative acreage accepted; two near-cap recommendations both commit beyond cap. Crop headroom must be checked within the transaction accepting a commitment, with finite positive input validation, identity/idempotency and scoped land/quantity contracts. A process-local lock does not provide cross-worker state. Current persistence occurs after in-memory mutation, so crash/retry/replay semantics need redesign. See supply_ledger.py:108–127, online_allocator.py:63–75, backend/main.py:222–226 and backend/ledger.py:23–32.

M7 scores price × farmer yield × relative yield while M5 uses profit minus a downside penalty. M7 must not silently replace the product objective. Reconcile cultivation costs known at sowing, rupee/quintal and tonne/hectare conversions, and meaningful profit uncertainty. M7 evaluator lacks M5's factor of ten; a common factor can cancel in revenue ratios but fails when mixing hectare costs.

A verified synthetic reconciliation uses two 200 ha farmers at 20 and 40 tonnes/ha. The ledger assumes 8000 tonnes, while summed farmer forecasts imply 12000 tonnes. The same simulator yields reference prices of 2100 versus 900 rupees/quintal. This is an internal consistency example, not observed market performance. Capacity must account for forecast production and uncertainty, not fixed average yield alone.

The visible application supplies district-level yields, not farmer-specific crop response estimates. Copying district forecasts gives comparative advantage approximately one; authentic personalization needs a separate validated source. A district-only coordination demo is possible without pretending to have personalized evidence.

Current price references and crop costs are proxies. Government MSP covers 22 mandated crops, excluding Tomato/Onion; for those crops use empirical market price references with explicit uncertainty, rather than statutory-MSP language. Annual crop supply differs from market arrivals, and selling catchments need not follow administrative boundaries. App commitments omit other farmers, storage, traders and other-region supply. The code stores baseline_area but does not include it in project_price. A real service needs outside-supply estimates without double counting and observed planting, withdrawal and harvest events.

A sensible architecture is crop eligibility → versioned yield/cost forecasts → estimated total marketed supply → harvest-price scenarios → common profit/risk scoring → advisory → optional planting commitment → atomic durable state update → refreshed subsequent advice. Quotes are not commitments; browsing must not consume acreage. Expiry, amendment, cancellation and fairness for late arrivals need explicit policy. M8 edge/privacy helpers are optional separate research work and are not deployment-ready.

**Forecasting/economic foundations**

Current features fail historical-prefix invariance. Changing a future yield from 2 to 200 changes the first year's fallback input from 1.25 to 50.75. Grouped shifts followed by ungrouped rolling mix districts/crops; full-period fallback and soil-imputation statistics use future data. Existing anti-leakage test merely checks test-year labels and passed. Existing saved model/baseline metrics reproduce, but do not establish leakage-free prospective performance. Correct all preprocessing and the comparison baseline, then evaluate anew.

Median yield × median price is generally neither mean revenue nor a profit quantile. Identical marginals [1,2,4] paired together produce mean revenue 70 after tonne/quintal conversion; reversing price order produces 40. M5 returns central revenue 40 for both. This synthetic example establishes an uncertainty-contract problem, not its real-data magnitude. A simpler risk-aware/cap baseline also needs corrected economic semantics.

**National expansion**

Official LGD currently lists 28 states and 8 UTs and offers unique location codes and historical modifications. DES provides district crop/season/year statistics; IMD lists 0.25-degree daily rainfall; DES cost studies and AGMARKNET prices offer economic sources. Catalog presence is not proof of a complete retrievable longitudinal panel. Some direct web fetches failed, and no national coverage audit was completed.

A national registry must retain state/district identifiers, effective boundaries, source units, crop aliases, season/harvest calendars and publication cutoff dates. Older Telangana/AP boundaries, J&K/Ladakh and district splits require verified historical mapping. Crop statistics may use different unit conventions (official cotton publications use 170 kg bales); never convert every production field to tonnes by assumption.

Audit jurisdiction × district × crop × season × year coverage, missingness, source release dates, physical plausibility, price/arrival coverage and available sowing-time features. All 36 jurisdictions can appear in navigation without emitting forecasts in unsupported cells. Small UTs, island systems, hill/perennial crops and sparse histories must be assessed individually; neither assume they are impossible nor assume the current five-state model transfers.

The exact historical soil/irrigation features may not be available everywhere. SHC API documentation describes authentication/registration; an API does not establish open historical nutrient access. A tested reduced-feature national model can be preferable to fictional or zero-filled soil fields. Compare a pooled crop/season model and justified regional variants against corrected historical baselines, using temporal and held-out-region evaluation. Evaluate error and interval coverage separately across crops and regions; countrywide averages cannot certify each.

Forecasting historical outcomes, forecasting a new season and predicting outcomes after recommendations change planting are different tasks. A current service needs pinned trained models, an as-of feature store, scheduled retraining, drift checks, calibrated uncertainty and explicit refusal for missing/stale inputs. At low data support use qualified experimental output or no forecast, not uniform precision.

Yield forecasting is easier than credible profit advice, which needs empirical sale-price and pre-sowing cost information. Nationwide supply coordination additionally needs trusted planting observations, adoption and market-flow estimates, partners, and outcomes. A real-time ledger is fast accounting, not immediate observability of all farms or instantaneous market equilibrium.

**Effort and resources**

Planning estimates, not timings: assuming one experienced full-time engineer, existing regional data and simulated delivery, a coherent regional integration is plausibly 2–4 engineer-weeks after scoping. A pilot-ready service can require 6–12+ weeks if usable data/model contracts are available. A reproducible selected-crop national data/model pipeline is a months-long undertaking, plausibly 2–6+ engineer-months under accessible data. Uniform validated predictions everywhere have no honest finish date before the data audit. Actual coordination benefits need completed planting-to-sale observations, usually multiple seasons for robustness, and partners; engineering speed cannot substitute.

Measured host: Apple M1, 8 GiB RAM, Python 3.14.4. Tabular seasonal forecasting need not use an LLM or a large GPU. A hypothetical 800-district × 40-crop × 2-season × 25-year dense panel contains 1.6 million rows; 40 float32 features take 244 MiB before categorical, dataframe, copy and training overhead. IMD grid dimensions imply about 24 MiB per daily year variable, 606 MiB for 25 years before extra variables/processing. These are arithmetic scenarios, not national-size or runtime benchmarks. Aggregate grids in chunks, train sequentially and measure resource use. Data validity and operations are more serious current barriers than buying compute.

**Recommended order and gates**

1. Repair feature/baseline historical isolation, ledger validation and atomic crop/quantity safeguards. Zero breaches in future-perturbation, group/state collision, stale quote, retry/recovery and hand-unit checks is an engineering gate; any breach stops promotion.
2. Build one region/market catchment, one season and 2–3 supported crops. Existing inputs can support a labeled historical/synthetic demo; current advice needs new cutoff-valid inputs and a deployable model.
3. Compare historical planting, static advice, corrected risk-aware advice with simple quantity caps and the allocator using identical forecasts/costs/constraints. Stress adoption, outside supply, yield–price dependence, arrival order and weather correlations. Judge net profit, lower-tail effects and regret, not the current synthetic revenue benchmark alone. Predefine the practical effect and acceptable downside before looking at new outcomes; reject a complex allocator that cannot justify its additional cost.
4. In parallel build the full national coverage/vintage matrix. Expand validated output crop/region by crop/region. Register all states/UTs while withholding unsupported predictions.
5. Before claiming real glut reduction or welfare benefits, run an appropriately controlled prospective market-level study that accounts for nonadopters and spillovers and measures actual planting and sale proceeds less costs. Historical observed crops do not supply counterfactual profits for every alternative crop on the same farm.

Sources:
- https://lgdirectory.gov.in/
- https://data.desagri.gov.in/website/apy-query-report-web
- https://www.data.gov.in/catalog/district-wise-season-wise-crop-production-statistics-0
- https://imdpune.gov.in/cmpg/Griddata/Rainfall_25_Bin.html
- https://desagri.gov.in/divisions-cell/cost-studies-cs/
- https://www.data.gov.in/catalog/current-daily-price-various-commodities-various-markets-mandi
- https://soilhealth.dac.gov.in/files/SHC_API_Integration_Guidelines.pdf
- https://www.pib.gov.in/PressReleaseIframePage.aspx?PRID=2222802&lang=2&reg=48
- https://proceedings.mlr.press/v119/perdomo20a.html
- https://arxiv.org/abs/2211.01951v1
- https://arxiv.org/abs/2403.07967
The broad idea that predictions change outcomes already has a research literature (e.g. Performative Prediction, ICML 2020). This is not a patentability review; no legal or novelty determination is made.

Audit records: frozen evidence_packet.md, correctness_probes.py/json, supplemental_probes.py/json, joint_distribution_probe.py/json, crop_coverage.json, resource_scenarios.json, targeted_tests.txt, five advisor reports, five fresh peer reviews, randomized council_record.json and source-search snapshots. Scripts reproduce the constructed examples; they do not repair or train the production implementation.

