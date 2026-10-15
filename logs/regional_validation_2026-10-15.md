# Regional forecasting implementation verification — 15 October 2026

Executed from the repository root using `.venv/bin/python`.

## Commands and observed outcomes

1. `-m pytest tests/test_regional_features.py tests/test_regional_training.py -q`
   - 12 passed in 1.73 seconds. One pandas future-category warning was subsequently fixed by mapping unseen categories to missing before constructing the categorical.
2. `-m pytest tests/test_regional_features.py tests/test_regional_training.py tests/test_m3_yield.py -q`
   - 17 passed in 2.45 seconds, no warnings.
3. `-u -m modules.regional_data.train --run-id regional-20261015-v1`
   - Exit 0; raw stdout/stderr in `logs/regional_training_2026-10-15.log`.
   - Full five-fold run completed in 83.66 seconds. The active pointer was promoted after validation.
   - Pandas performance warnings describe fragmented construction of the feature matrix. They do not affect values. The exact implementation used by training is preserved and its hashes match the source registry.
4. Independent read-only verification of the active run:
   - All 9 input/config/implementation source hashes matched current files.
   - All 38 manifest-listed artifact hashes matched their files.
   - Forecast SHA256: `3f8f10cb4b96dd38623746438d0134d9e7f74de55aa11eaf82440911811362a6`.
   - 26,526 historical test rows, 25,142 supported, 1,384 unavailable because local three-calendar-year history/economic references were absent.
   - Supported records cover all five source states. Coimbatore Kharif 2019 Maize, Onion and Ragi all have three prior-year yield observations.
   - Every fold's saved raw and calibrated inference representations reproduced the generated predictions.

## Fresh findings

| Metric | Quantile model | Independent trailing baseline |
|---|---:|---:|
| RMSE (t/ha under project unit convention) | 3.941196 | 4.040788 |
| Nominal 80% interval coverage | 78.9197% | 80.9283% |

See `data/runs/regional-20261015-v1/metrics.json` for MAE, interval widths,
quantile losses and counts by crop, state and year. No accuracy-improvement test
was imposed. These fresh historical results do not validate real farmer income,
current-season forecasting, original source release vintages or original unit
provenance. Monetary quantities use generated prior-year category-price proxies
and a historical yield-based cost proxy in base-2011 rupees.

Legacy inputs, processed metrics and presentation files were not changed. The
structural cleaner deliberately retains the isolated incomplete weather/soil row,
which becomes unsupported if no local history exists; it does not fabricate
covariates to enforce a zero-missing invariant.
