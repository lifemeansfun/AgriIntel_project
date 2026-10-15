# Regional course release verification — 15 October 2026

**Story:** A student opens the historical explorer or Coimbatore scenario, requests advice from the repaired model artifact, commits a crop into durable shared state, sees subsequent advice change, cancels that commitment, and compares static versus supply-aware choices through an isolated replay.

## Results

| Boundary | Result | Evidence |
|---|---|---|
| Raw data → forecasts | PASS for historical arithmetic isolation | `tests/test_regional_features.py`, `tests/test_regional_training.py`, fresh immutable run with saved model reload checks |
| Artifact → API | PASS | Full artifact hashes verified; five states and three configured demo crops available; missing/modified forecast fails closed |
| Browser → API → ledger | PASS | Two contexts perform commit/cancel, share revision changes, reprice advice, reject stale quote409 |
| Transaction durability | PASS | Separate-process capacity contention, failed-write rollback, exact retries, restart recovery and cancellation tests |
| Model activation/recovery | PASS after repair | Prior state/retry/cancellation remain accessible with a new or missing active catalog; new effective configuration gets separate state |
| Replay | PASS for deterministic specified simulation | 24 steps, identical policy constraints, common final-price repricing, UI step/play/pause/completion |
| Rendered UI | PASS after visual fixes | Day/night desktop and375px mobile; theme contrast fixed; three scatter points visible immediately; supply explanation wraps outside table scroller |

The full Python suite passed **97 tests in6.10s**, with two existing dependency deprecations from Starlette/httpx/anyio. Frontend lint had zero findings; all **3 Node tests passed**; final Vite production build succeeded in842ms. Retained R sanitization checks passed, but inspect old artifacts and do not validate the replacement pipeline.

The browser workflow report contains **12 passing checks** (five state flows plus arithmetic/shared-state/stale/cancel/replay/mobile/runtime checks). It reports zero page errors, console errors, failed requests or HTTP errors. Stale-quote409 was deliberately exercised through the browser context request client. Focused final visual checks separately passed after the theme/plot fixes; the final mobile caption bounds were301px wide with58.5px wrapped height inside375px viewport.

Browser warnings remain from the installed Three.js Clock dependency and the headless software-GPU screenshot driver. No application error or failed boundary was observed. The screenshot driver warnings are not a real-device performance benchmark.

## Fresh historical results

Run `regional-20261015-v1`, actual training time83.66s. Of26,526 historical test records,25,142 have supported historical/economic inputs and1,384 are unavailable. Original raw/processed/API-event files all match the22-file pre-change hash inventory.

| Metric | LightGBM | Corrected trailing-mean baseline |
|---|---:|---:|
| RMSE (t/ha) | 3.941196 | 4.040788 |
| MAE (t/ha) | 1.354052 | 1.278491 |
| Nominal80% interval coverage | 78.9197% | 80.9283% |
| Mean interval width (t/ha) | 3.375111 | 1.790180 |

Results are mixed. They use a new supported subset and repaired protocol, so the original saved metrics are not a controlled before/after scientific comparison. Crop/state/year counts and errors are in the active run's `metrics.json`.

Default seed42 replay: static modeled total profit **739263.4123368218**, dynamic **735940.4386303208**, in2011-base rupees. Both allocate24 participants. The dynamic policy loses; no simulation improvement claim is made. Lower-tail figures describe allocated participants only, with rejects/unallocated acreage separately reported. Equal-area identical-forecast participants mean seeded arrival changes identity assignment, not aggregate demand.

## Issues found and repaired

- Raw/feature/baseline historical leakage and state/group collisions: replaced active pipeline with structural-only cleaning, true calendar-year historical joins and proper-training imputation.
- Target-year yield entering advice costs: replaced with prior-only modeled cost input.
- Competing utility definitions/monetary scaling: one shared fixed-cost scenario calculation and supply-price engine.
- Process-local mutation followed by background persistence: replaced by atomic durable SQLite acceptance with idempotency and scoped quantities.
- Model activation hiding old acknowledgements: durable recovery routes are independent of active forecast availability.
- Scenario ID omitting effective configuration: ID now fingerprints complete configuration/artifact inputs.
- Infinite recommendation caching and obsolete responses: invalidation, polling, abort/generation guards and pending-request retries.
- Unqualified VaR/MSP/safety claims and incorrect net-profit scaling: active UI uses scenario labels, fixed costs and explicit provenance.
- Theme-controlled cards with OS-controlled Tailwind variants: linked theme class and custom dark variant; contrast verified through computed colors/screenshots.
- Empty chart during initial animation and clipped mobile explanation: disabled point animation and separated explanation from horizontally scrollable table.
- Initial automation locator matched both crop title and candidate title: refined to the unique h2. A visual-check expectation usedRGB despite Tailwind returningOKLCH; corrected the test representation. These were test-script issues, not application defects.

## Reproduction

From repository root:

```sh
./scripts/verify_regional.sh --legacy-r
.venv/bin/python -m modules.regional.cli replay --seed 42 --output-dir output/regional_demo/a-new-run
```

Use an unused output directory. The root README documents clean setup, immutable raw-to-model retraining, API routes, environment variables and local startup. Browser scripts in this folder use the bundled Playwright runtime; they accept a UI/API URL for the main workflow. Final screenshots, DOM snapshots, API bodies, commands and raw logs are retained alongside this report.

## Runtime and limits

The QA API was stopped after verification. A fresh API is running at127.0.0.1:8001 using the normal `data/api_processed/regional.sqlite3`; initial revision0 and zero committed hectares were verified. Frontend runs at127.0.0.1:5174. The pre-existing API on8000 was preserved. No external deployment, Git push, real-farmer study or nationwide expansion occurred.

Original publication vintages and production-unit provenance remain unverified; source-declared units and historical calendar cutoffs are disclosed. Prices/costs and outside supply are assumptions, pooled intervals do not certify each crop/farm, and classroom identities are not authentication. The release demonstrates integrated accounting/advice behavior, not real glut prevention, market equilibrium, patentability or improved farmer income.
