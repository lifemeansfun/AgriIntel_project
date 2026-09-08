# AgriIntel — Project Plan (v3, Final)
### AI-Powered Crop Profit Forecasting & Recommendation System

**Status:** Build-ready specification. This plan assumes the fixes identified during review are already incorporated — it is written as the plan to execute, not as a critique of an earlier draft.

**Starting assumption:** an existing, cleaned agronomic feature store already exists at `[State, District, Crop, Year, Season]` grain (29 columns: rainfall statistics, soil N/P/K/organic carbon/pH-class shares, irrigation source shares and intensity, area/production/yield). This table is treated as **frozen** — no module in this plan re-derives it. If any column in that table is not actually final, flag it before Module 1 begins; everything downstream assumes it's audited and stable.

---

## 0. Executive Summary

AgriIntel predicts district-crop-season yield, forecasts the price a farmer is likely to realize at harvest, and combines the two into a profit-ranked crop recommendation — with every stage validated against a naive baseline and an explicit, leak-safe train/test protocol. The only new data-engineering work is the economic layer (mandi prices, cultivation cost, WPI, MSP); everything else is modeling, validation, and a lightweight demonstrator.

The project is split into two phases so scope matches a single-student academic timeline:
- **Phase 1 (Modules 1–5):** the actual thesis — data, models, validation. Full rigor.
- **Phase 2 (Modules 6–7):** a minimal TRL3 demonstrator. Deliberately lightweight; production infrastructure (Airflow/Redis/Docker/React PWA) is documented as future work, not built.

---

## 1. Project Scope & Objectives

**Primary objective:** given district, crop, season, and year, produce (a) a yield forecast with uncertainty, (b) a price forecast with calibrated intervals, and (c) a profit-ranked list of candidate crops for that district-season — each validated against a defined baseline on held-out years and held-out districts.

**Explicit non-objectives (state these in the report so no reviewer expects them):**
- Not a causal model. Framed throughout as *predictive decision support*, not a claim that any input (e.g., irrigation intensity) causally drives yield at the margin — it may simply proxy for better-managed districts.
- Not a market-equilibrium model. The plan does not attempt to model the feedback loop where AgriIntel's own recommendations, if adopted at scale, shift supply and therefore price (a Lucas-critique-style self-defeating prediction). This is named explicitly as a stated limitation in the final report, not silently ignored.
- Not a production system. Phase 2 proves deployability at TRL3; it does not build for scale, uptime, or concurrent users.

**Success criteria (thesis-level):** every model in Modules 3–5 beats its assigned baseline, out-of-sample, on the metric specified in §4.4, using the validation protocol in §4.2.

---

## 2. Data Architecture

### 2.1 Existing agronomic feature store (frozen)
Treated as immutable input. No pipeline in this plan touches its source (IMD rainfall, Soil Health Card, irrigation records) beyond reading the final table. Its schema is the join key for everything new: `[State, District, Crop, Season, Year]`.

### 2.2 Economic data layer (the new work)

| Source | Acquisition method | Update cadence | Stored as |
|---|---|---|---|
| AGMARKNET mandi prices & arrivals | Programmatic — data.gov.in resource API, paginated JSON | Daily (source updates continuously) | Raw fact table keyed `[market, commodity, date]` — **not** forced to district/year grain at ingestion |
| DES Cost of Cultivation (A2+FL, C2) | Static, versioned download | Annual | Reference table `[state, crop, year, cost_type, value]` |
| RBI DBIE Wholesale Price Index | Static, versioned bulk download | Monthly | Reference table `[month, commodity_group, wpi]` |
| MSP (Minimum Support Price) | Static, versioned download | 1–2x/year per crop | Reference table `[crop, marketing_year, msp_value]` |

Only AGMARKNET justifies live API access — it's the one source that actually updates and needs refreshing for a demo. The other three are small, slow-moving, and pulled once per project cycle as static files; building scraping infrastructure for them buys nothing.

### 2.3 Storage design: star schema, not a mega-flat-file
One fact table at the existing `[state, district, crop, season, year]` grain, joined **at query time** to three small reference tables (WPI, MSP, cultivation cost) — never baked in at storage time. Rationale: WPI/MSP values repeat across thousands of district-crop rows if flattened; a star schema keeps corrections (e.g., fixing one WPI figure) to a single reference-table edit instead of a full re-join, and makes debugging additive ("is the error in the fact table or the WPI lookup?").

```
fact_agri_economic        (state, district, crop, season, year, mandi_price_agg, arrivals, ...)
dim_wpi                   (month, commodity_group, wpi)
dim_msp                   (crop, marketing_year, msp_value)
dim_cultivation_cost      (state, crop, year, cost_type, value)
```

### 2.4 Crosswalk tables (built once, reused everywhere)

**Mandi → District crosswalk.** AGMARKNET reports by market (mandi), not by administrative district; a district can map to zero, one, or several mandis, and farmers sell across district lines. Build an explicit crosswalk (GADM/gazetteer matching, hand-curated where automated matching fails) plus a documented aggregation rule — area-weighted average across all mandis whose catchment is that district. This crosswalk gets its own validation gate (§7), not a one-line "standardize strings" step.

**Crop-name canonicalization.** AGMARKNET commodity names ("Arhar (Tur/Red Gram)") won't string-match the agronomic table's `Crop` column ("Arhar/Tur") or DES/MSP naming. One canonical crop-name lookup table is built and used by *every* join in the pipeline — mismatches here fail silently (dropped rows, not errors), so match rate is logged and gated explicitly.

### 2.5 Reproducibility & snapshot policy
Every external pull is frozen as a timestamped, hash-stamped Parquet snapshot with an accompanying `manifest.json` (fetch date, source URL, row count). No module hits a live API during training or demo — acquisition happens once, is versioned, and everything downstream trains against the frozen snapshot. This protects both the published result (must be reproducible from a fixed dataset) and the demo (must not break because a government API is down during a viva).

---

## 3. System Design

### 3.1 Standard module interface
Every module — regardless of what it does internally — implements the same contract, so any stage can be tested, swapped, or debugged alone:

```python
class PipelineModule:
    def validate_input(self, df) -> None:
        """Raise on schema/range violation before any processing."""

    def run(self, df) -> pd.DataFrame | dict:
        """Core logic."""

    def validate_output(self, result) -> None:
        """Raise before handing downstream — no module trusts its own output blindly."""

    def run_from_disk(self, in_path: str, out_path: str) -> None:
        """CLI-runnable in isolation, no upstream module needs to have run first."""
```

Every module reads and writes a **versioned artifact to disk** (Parquet for tabular, JSON for scalars/config) rather than passing in-memory objects — this is what lets you re-run Module 4 against yesterday's Module 3 output while debugging Module 4 alone, without re-running the yield ensemble.

### 3.2 Configuration
All hyperparameters, file paths, and thresholds live in a single YAML config, never hardcoded. An ablation (e.g., "with vs. without GNN embeddings") becomes a one-line config diff, not a code change.

```yaml
module: M3_yield
model: xgboost
folds:
  temporal: rolling_origin
  spatial: leave_one_district_out
hyperparam_search: optuna
baseline: trailing_3yr_mean
acceptance_margin_pct: 10
```

### 3.3 Logging
Structured, module-tagged logs for every run: `[M3-yield] fold=3 rmse=0.41 crop=wheat`. A failed pipeline run should point to the exact module and fold, never just a bare stack trace.

### 3.4 Phase 1 / Phase 2 split
Stated explicitly in the proposal as scoping discipline, not corner-cutting:

- **Phase 1 — Modules 1–5.** The thesis. Full rigor, full validation, all novel contribution.
- **Phase 2 — Modules 6–7.** TRL3 demonstrator only: Airflow → single scheduled script; Redis → local SQLite/JSON cache; React PWA → Streamlit/Plotly Dash. TRL3 ("experimental proof of concept") does not require production-grade orchestration or caching, and building it anyway spends effort on the part of the project no reviewer is grading. The full production stack is retained in the write-up only as a labeled "Future Work / Scaling Path" section.

---

## 4. Methodology

### 4.1 Mandatory baselines (every stage compares against one)

| Stage | Baseline |
|---|---|
| Yield | District's own 3-year trailing mean; state-crop-season mean yield |
| Price | Naive persistence (last season's realized price); seasonal-naive (same season, prior year) |
| Recommendation | "Recommend whatever crop had the highest realized profit last year in that district" — i.e., what a farmer using only public knowledge and no model would do |

Every acceptance gate is phrased as *"beats baseline by X% on metric Y, out-of-sample"* — never as an absolute score.

### 4.2 Train/test protocol: nested, dual-axis validation
Fixed **before** any model is touched, because a chained pipeline (yield → price → profit) leaks information across every seam if the split isn't fixed first.

- **Temporal axis:** rolling-origin / walk-forward — train on years ≤ T, evaluate on year T+1. Never train on a year and test on an earlier one.
- **Spatial axis:** leave-one-district-out (or leave-region-out) folds, run *within* each temporal fold — checks the model isn't just memorizing district identity rather than learning transferable structure.

### 4.3 Chain-safety rule (the leak that actually matters)
The `Predicted_Yield` fed into Module 5's training set must be Module 3's **out-of-fold prediction for that row's specific temporal fold** — never from a model that has seen that year, even indirectly. Internal M3 hyperparameter tuning can use ordinary K-fold OOF; the yield values that flow into the price/profit chain must be temporal-OOF specifically. This rule is enforced in code (`validate_input` on Module 4 checks a `fold_id` column matches the temporal fold being scored) rather than left as a convention.

### 4.4 Metrics, per module

| Module | Metrics |
|---|---|
| M3 (yield) | RMSE, MAE, R² — **computed per crop**, never pooled (yields vary by orders of magnitude across crops, so one pooled RMSE is uninformative) |
| M4 (price) | Pinball/quantile loss at P10/P50/P90; **interval coverage** — does the 80% interval actually contain the true price ~80% of the time, checked explicitly rather than assumed |
| M5 (profit) | Direction/hit-rate accuracy — did the top-ranked crop actually land in the top-3 by realized profit? This is closer to what a farmer or policymaker cares about than raw regression error |

### 4.5 Limitations stated explicitly in the write-up
- **Endogeneity / feedback loop:** naming the Lucas-critique-style self-defeating-prediction risk up front is a stated limitation, not a gap to be caught by a reviewer.
- **Correlational, not causal:** Modules 2–4 are predictive ML; the report frames outputs as decision support, not causal claims about e.g. irrigation's marginal effect on yield.

### 4.6 Uncertainty propagation
Module 3 produces `predicted_yield_variance`. It is not allowed to be computed and discarded. Two acceptable outcomes, either is fine as long as it's a deliberate choice recorded in the design doc:
1. **Propagate:** sample from the M3 yield distribution when forming M4's price quantiles, or at minimum widen M4's interval as a function of M3's variance.
2. **Drop it and say so:** if propagation proves impractical, remove the output and state explicitly in the methods section why it isn't used. An unused, unexplained output is treated as a defect during review.

---

## 5. Detailed Module Specifications

### Module 1 — Economic Data Layer
**Objective:** produce the fact table + reference tables described in §2.2–2.4, joined to the frozen agronomic table.
**Inputs:** AGMARKNET API, DES/WPI/MSP static downloads, existing agronomic table.
**Processing:** frozen snapshot pull → mandi→district crosswalk applied → crop-name canonicalization applied → fact table assembled at `[state, district, crop, season, year]` → reference tables joined at query time only.
**Outputs:** `fact_agri_economic.parquet`, `dim_wpi.parquet`, `dim_msp.parquet`, `dim_cultivation_cost.parquet`, `manifest.json`.
**Validation:** Pydantic/pandera schema checks; crosswalk match-rate report (logged, never silently dropped); null-rate report per column.
**Acceptance gate:** ≥98% of price rows successfully matched to a district; zero unresolved crosswalk entries above the documented threshold; zero silent nulls.

### Module 2 — Spatial Embeddings *(conditional)*
**Objective:** test whether graph-based district embeddings (GAT/GraphSAGE, built over a district-adjacency or climate-similarity graph) improve yield prediction.
**Inputs:** frozen agronomic table, district adjacency/similarity graph.
**Processing:** build embeddings; run as an **ablation**, not a one-off sanity check — train Module 3 with vs. without embeddings, identical folds.
**Outputs:** embeddings artifact (only retained if it clears the gate); ablation report either way.
**Validation:** graph connectivity check (no orphan nodes); embedding variance non-degenerate; t-SNE/UMAP plot to visually confirm climatically similar districts cluster.
**Acceptance gate:** GNN embeddings must measurably improve M3's out-of-sample RMSE vs. a tabular-only baseline. If they don't, drop the GNN — at this data scale (tens of districts), unjustified complexity is a liability, and a documented negative result is legitimate thesis content on its own.

### Module 3 — Yield Ensemble
**Objective:** predict yield per district-crop-season with calibrated uncertainty.
**Inputs:** M1 fact table (or M1+M2 if embeddings pass the gate).
**Processing:** RF/XGBoost with Optuna hyperparameter search; temporally-OOF predictions generated specifically for downstream chaining (§4.3).
**Outputs:** `predicted_yield`, `predicted_yield_variance` (with a documented consumer per §4.6), per-crop metrics report.
**Validation:** range assertions (yield ≥ 0, ≤ documented crop-specific biological max); feature importance stability checked across folds.
**Acceptance gate:** beats the trailing-3-year-mean baseline RMSE by a pre-registered margin, evaluated per crop, under both leave-one-year-out and leave-one-district-out backtests.

### Module 4 — Price Forecasting
**Objective:** forecast realized price at harvest with calibrated quantile intervals.
**Inputs:** M1 economic fact table, M3's temporally-OOF yield predictions, WPI/MSP reference tables.
**Processing:** quantile regression via XGBoost/LightGBM quantile objective as the primary model (more tractable and better-calibrated than LSTM at this data size); ARIMA retained as an interpretable baseline, not a co-equal model. MSP handled as a **soft constraint** during training (loss-shaping) with explicit post-hoc clipping applied afterward if a hard floor is genuinely required — a soft-constraint loss function alone should never be described as guaranteeing a hard floor.
**Outputs:** P10/P50/P90 price forecasts.
**Validation:** quantile monotonicity check (P10 < P50 < P90); MSP floor never violated post-clip.
**Acceptance gate:** beats naive seasonal persistence on pinball loss; interval coverage within ±5 percentage points of the nominal 80%, checked under rolling-origin walk-forward.

### Module 5 — Profit Ranking
**Objective:** rank candidate crops per district-season by predicted profit.
**Inputs:** M3 yield forecast, M4 price forecast, M1 cultivation cost table.
**Processing:** deterministic profit = (predicted yield × predicted price) − cultivation cost, per crop candidate; ranked descending.
**Outputs:** ranked crop list per district-season with profit estimate and confidence band (inherited from M4's interval, itself informed by M3's variance per §4.6).
**Validation:** golden-master tests (hand-computed profit for fixed inputs must match exactly); property-based tests (e.g., via Hypothesis — profit strictly increasing in price, strictly decreasing in cost).
**Acceptance gate:** beats the "prior year's best performer" baseline on realized-outcome hit-rate — for held-out years, does the top-ranked crop actually land in the top-3 by realized profit?

### Module 6/7 — Phase 2 Demonstrator
**Objective:** minimal end-to-end proof that a district/crop/season query returns a recommendation, satisfying TRL3.
**Inputs:** trained M3–M5 artifacts.
**Processing:** FastAPI endpoint → local SQLite/JSON cache → Streamlit or Plotly Dash front end. No Airflow, no Redis, no React PWA, no offline caching — these are documented as future work only.
**Outputs:** a running local demo.
**Validation:** schema/contract tests on the API response; basic UI smoke test.
**Acceptance gate:** end-to-end request → recommendation round-trip works for at least 3 representative district/crop queries; manual walkthrough is sufficient — automated load testing is explicitly out of scope for TRL3.

---

## 6. Defensive Coding Standards (apply at every module boundary)

- **Schema-first everywhere:** `pandera` for DataFrame validation (a better fit than raw Pydantic for tabular data) enforcing dtypes, ranges, non-null constraints — at *every* module seam, not just M1→M2.
- **Unit sanity checks:** assert `Yield ≈ Production / Area` within tolerance on load; quarantine rows where it doesn't hold (a known issue in this public crop-production dataset is a small number of unit-mismatched rows).
- **Divide-by-zero guards:** any row with `Area == 0` is caught and excluded/flagged before reaching a yield calculation — never allowed to silently produce `inf`/`NaN` downstream.
- **No silent imputation:** any imputation logs the count of imputed cells per column; the build fails if the imputation rate exceeds a documented threshold.
- **Specific exceptions + backoff for AGMARKNET calls:** catch `requests.HTTPError` / `Timeout` distinctly, exponential backoff, respect data.gov.in's documented rate limits — never a bare `except:`.
- **Idempotent ETL:** re-running Module 1 against the same frozen snapshot produces a byte-identical (or hash-identical) output.
- **Provenance tagging:** every fact-table row carries `source_snapshot_date` — needed both for reproducibility and for explaining any anomaly a reviewer flags.

---

## 7. Consolidated Verification & Validation Matrix

| Module | Unit / statistical checks | Backtest protocol | Acceptance gate |
|---|---|---|---|
| M1 ETL | Schema validation; crosswalk coverage report; null-rate report | N/A (deterministic) | ≥98% crosswalk match rate; schema-validated; zero silent nulls |
| M2 GNN | Graph connectivity; embedding variance; t-SNE/UMAP cluster check | Ablation vs. tabular-only baseline | Must measurably beat tabular-only RMSE, or is dropped |
| M3 Yield | Range assertions; feature-importance stability | Leave-one-year-out + leave-one-district-out, vs. trailing-mean baseline | Beats trailing-3yr-mean RMSE by pre-registered margin, per crop |
| M4 Price | Quantile monotonicity; MSP floor check post-clip | Rolling-origin walk-forward; interval coverage check | Beats naive seasonal persistence on pinball loss; coverage within ±5pp of nominal |
| M5 Profit | Golden-master tests; property-based tests | Realized-outcome backtest on held-out years | Beats "last year's best performer" baseline on hit-rate |
| M6/M7 | API contract tests; UI smoke test | Manual walkthrough | Round-trip works for ≥3 representative queries |

---

## 8. Timeline / Work Breakdown Structure

*Assumption: a single-semester academic execution window of ~20 weeks. Adjust proportionally if your actual timeline differs — the sequencing and dependencies below don't change even if the durations do.*

| Weeks | Phase | Activity |
|---|---|---|
| 1–2 | Setup | Freeze agronomic table audit; set up repo, YAML config skeleton, module interface scaffolding, logging |
| 3–5 | M1 | AGMARKNET API integration, static pulls (DES/WPI/MSP), crosswalk construction, star-schema fact table, snapshot/versioning |
| 6 | M1 gate | Crosswalk match-rate validation; schema gate sign-off before any modeling begins |
| 7–8 | M3 (core) | Baseline yield models (trailing mean), then RF/XGBoost + Optuna, temporal + spatial folds |
| 9 | M2 (conditional) | GNN embedding ablation; keep or drop based on gate result |
| 10–11 | M4 | Quantile regression price model, ARIMA baseline, calibration checks |
| 12 | M5 | Profit ranking logic, golden-master + property-based tests, realized-outcome backtest |
| 13 | Integration | Full M1→M5 pipeline run on frozen snapshot; chain-safety audit (temporal-OOF check at every seam) |
| 14–15 | M6/M7 | FastAPI + SQLite cache + Streamlit demo; contract tests; smoke test |
| 16–17 | Write-up | Methods, limitations (endogeneity, correlational framing), results, ablation reporting |
| 18–20 | Buffer / defense prep | Slack for API downtime, re-runs, viva rehearsal with the frozen snapshot |

---

## 9. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| AGMARKNET API downtime or rate-limit changes | Medium | Medium | Frozen snapshot policy (§2.5) means training/demo never depend on live access |
| Mandi↔district crosswalk has low match rate for sparse districts | Medium | High | Explicit gate (§7) surfaces this in Week 6, before modeling time is spent on an incomplete join |
| GNN adds complexity without benefit at this data scale | Medium | Low (if gated correctly) | Mandatory ablation (M2) makes this a documented decision, not a sunk-cost inclusion |
| Chain leak between M3 and M5 | Low if enforced in code | High if it happens | `fold_id` validation in Module 5's `validate_input` makes the chain-safety rule (§4.3) unbypassable rather than a convention |
| Scope creep into Phase 2 production infrastructure | Medium | High to timeline | Phase 1/Phase 2 split stated explicitly in proposal; Phase 2 stack fixed to FastAPI+SQLite+Streamlit only |
| Reviewer challenges causal framing | Medium | Medium | §4.5 limitations are pre-written into the methods section, not left for the defense |

---

## 10. Thesis / Report Chapter Mapping

| Chapter | Maps to |
|---|---|
| Data & Methods | §2 (data architecture), §4 (methodology, baselines, validation protocol) |
| System Design | §3 (module contract, config, phase split) |
| Experiments & Results | §5 module specs + §7 V&V matrix, reported per crop |
| Ablations | Module 2 GNN ablation, reported regardless of outcome |
| Limitations | §4.5 (endogeneity, correlational framing) — written proactively, not reactively |
| Deployment / TRL Justification | §5 Module 6/7, explicitly scoped to TRL3 |
| Future Work | Full production stack (Airflow/Redis/Docker/React PWA), labeled as such |

---

## Appendix A — Repository Structure

```
agriintel/
├── config/
│   └── pipeline.yaml
├── data/
│   ├── raw_snapshots/        # frozen, hash-stamped pulls + manifest.json
│   └── processed/             # versioned Parquet outputs per module
├── modules/
│   ├── m1_economic_etl.py
│   ├── m2_spatial_embeddings.py
│   ├── m3_yield_ensemble.py
│   ├── m4_price_forecast.py
│   ├── m5_profit_ranking.py
│   └── m6_m7_demo/
├── tests/
│   ├── test_golden_master.py
│   ├── test_property_based.py
│   └── test_schema_gates.py
└── logs/
```

## Appendix B — Config Schema (illustrative)

```yaml
project: agriintel
snapshot_date: "2026-09-08"

module_m1:
  crosswalk_match_threshold_pct: 98
  sources: [agmarknet, des_cultivation_cost, rbi_wpi, msp]

module_m3:
  model: xgboost
  hpo: optuna
  folds: {temporal: rolling_origin, spatial: leave_one_district_out}
  baseline: trailing_3yr_mean
  acceptance_margin_pct: 10

module_m4:
  model: lightgbm_quantile
  quantiles: [0.1, 0.5, 0.9]
  baseline: seasonal_naive
  coverage_tolerance_pp: 5
  msp_floor: soft_then_clip

module_m5:
  baseline: prior_year_best_performer
```
