# Corrected historical forecasting pipeline

Run from the repository root using the project Python environment:

```sh
.venv/bin/python -m pytest tests/test_regional_features.py tests/test_regional_training.py -q
.venv/bin/python -m modules.regional_data.train --run-id regional-YYYYMMDD-unique
```

A run identifier is immutable: existing directories cause an error. A failure leaves a
`status.json` failure record and never promotes the active pointer. Successful runs
write `data/runs/active.json` only after all folds, finite/ordered forecast invariants,
five-state coverage, classroom-crop support, and saved-model reload checks pass.
Use `--no-promote` to evaluate without changing the active run, or `--output-root`
for temporary evaluation directories.

The new pipeline never reads or overwrites the legacy cleaned agronomic/economic
fact tables. It starts with `agriIntel_merged_final_v.csv`, removes exact duplicates,
sums same-key area/production, and retains missing covariates. Invalid irrigation
intensity becomes missing rather than being repaired with a full-period median.
There is no all-years statistical imputation and no current-yield-derived cost.

Feature and baseline keys include state, district, crop, season and calendar year.
Only years t-1, t-2 and t-3 enter trailing values; calendar gaps remain gaps. Each
2015–2019 fold fits through t-2, calibrates on t-1, and tests t. A missing calibration
year is an error, never a random or overlapping split. Numeric imputation and category
vocabularies are fit to proper-training rows only and persisted. Numeric missingness
is retained through indicators; all-missing training features are dropped. The
independent baseline uses local, then state, then crop-season history. Local model
advice requires at least one local observation in the prior three calendar years.

Each fold saves three LightGBM text models, preprocessing/joblib state, historical
structural records, interval calibration, and prediction-cap configuration. The
`predict_calibrated_bundle(bundle_dir, feature_rows)` API in `train.py` restores the
calibrated quantile and independent-baseline intervals. It expects rows engineered
from the saved history and query keys; current-year target observations are not
needed for inference. It rejects absent local yield history rather than supplying a
zero forecast. All five folds are checked against both raw and calibrated saved
inference representations.

Prices are generated category-price proxies, using the latest registry calendar
year strictly before the target, deflated by the latest prior-year saved CPI. Costs
are `10 × trailing local yield × reference price / 1.5`, in base-2011 rupees per
hectare. They are simulation inputs, not official price observations or guarantees.

`metrics.json` reports model and baseline RMSE, MAE, quantile loss, interval coverage
and width, with counts by crop, state and test year. Worse model results are valid
findings. Coverage is pooled temporal calibration; it is not a guarantee for each
crop, region, individual farm or future season. Metrics are conditional on crop
records actually observed in the historical file.

The source registry hashes raw/economic/config files and the implementation files.
Original source publication timestamps and crop-unit documentation are unavailable.
The input's production/hectare arithmetic follows the project's declared tonnes
convention and is labeled accordingly. Arithmetic historical isolation is tested;
this does not establish what was operationally available before sowing, current
forecast accuracy, or improved real farmer income. Existing cap values are inherited
project safeguards, not independently verified biological limits.
