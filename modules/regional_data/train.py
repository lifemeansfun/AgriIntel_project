"""Immutable raw-to-model historical training run.

Run from the project root:
    .venv/bin/python -m modules.regional_data.train --run-id regional-20261015

No existing processed table is consumed or overwritten. An active pointer is
atomically replaced only after the run and saved model reload checks succeed.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import re
import time

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
import yaml

from modules.m3_yield.baselines import generate_baseline
from modules.m3_yield.features import build_ex_ante_features
from modules.regional_data.data import KEY, attach_prior_economics, structural_clean

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CATEGORICAL = ["State", "District", "Crop", "Season"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")


def fit_preprocessor(training: pd.DataFrame) -> dict:
    """Fit numeric medians and categorical vocabulary on proper-training data."""
    numeric = [c for c in training.columns if "_lag3_" in c] + ["Year_start"]
    medians = {}
    dropped = []
    for col in numeric:
        value = training[col].replace([np.inf, -np.inf], np.nan).median()
        if pd.isna(value):
            dropped.append(col)
        else:
            medians[col] = float(value)
    return {
        "numeric_medians": medians,
        "dropped_all_missing_features": dropped,
        "categories": {c: sorted(training[c].dropna().astype(str).unique().tolist()) for c in CATEGORICAL},
        "feature_names": CATEGORICAL + list(medians) + [f"{c}__missing" for c in medians],
        "missing_policy": "proper-training median plus missing indicator; drop all-missing feature; unknown category -> missing",
        "fit_max_year": int(training.Year_start.max()),
    }


def transform(frame: pd.DataFrame, preprocessor: dict) -> pd.DataFrame:
    result = pd.DataFrame(index=frame.index)
    for col, vocabulary in preprocessor["categories"].items():
        values = frame[col].astype(str)
        result[col] = pd.Categorical(values.where(values.isin(vocabulary)), categories=vocabulary)
    for col, median in preprocessor["numeric_medians"].items():
        raw = pd.to_numeric(frame[col], errors="coerce").replace([np.inf, -np.inf], np.nan)
        result[col] = raw.fillna(median)
        result[f"{col}__missing"] = raw.isna().astype(np.int8)
    return result[preprocessor["feature_names"]]


def finite_sample_quantile(scores: np.ndarray, coverage: float = 0.8) -> float:
    scores = np.asarray(scores, dtype=float)
    scores = scores[np.isfinite(scores)]
    if len(scores) < 5:
        raise ValueError("Fewer than five finite calibration observations; no overlapping fallback is permitted")
    rank = math.ceil((len(scores) + 1) * coverage)
    if rank > len(scores):
        raise ValueError("Calibration set is too small for the requested finite-sample quantile")
    return float(np.sort(scores)[rank - 1])


def metric_set(frame: pd.DataFrame) -> dict:
    if frame.empty:
        return {"count": 0}
    target = frame.Yield.to_numpy()
    result = {"count": len(frame)}
    for label, lower, central, upper in [("model", "q10", "q50", "q90"),
                                          ("baseline", "Baseline_q10", "Baseline_Yield", "Baseline_q90")]:
        point = frame[central].to_numpy()
        errors = target - point
        metrics = {
            "RMSE": float(np.sqrt(np.mean(errors ** 2))), "MAE": float(np.mean(np.abs(errors))),
            "coverage_80": float(np.mean((target >= frame[lower]) & (target <= frame[upper]))),
            "mean_interval_width": float(np.mean(frame[upper] - frame[lower])),
        }
        for q, col in [(0.1, lower), (0.5, central), (0.9, upper)]:
            error = target - frame[col].to_numpy()
            metrics[f"pinball_{q:.1f}"] = float(np.mean(np.maximum(q * error, (q - 1) * error)))
        result[label] = metrics
    return result


def evaluate(frame: pd.DataFrame) -> dict:
    supported = frame[frame.Supported].copy()
    return {
        "evidence_status": "fresh historical rerun; source publication vintages and original units not independently verified",
        "overall": metric_set(supported),
        "by_crop": {str(key): metric_set(part) for key, part in supported.groupby("Crop", observed=True)},
        "by_state": {str(key): metric_set(part) for key, part in supported.groupby("State", observed=True)},
        "by_year": {str(key): metric_set(part) for key, part in supported.groupby("Year_start", observed=True)},
        "unsupported_rows": int((~frame.Supported).sum()),
        "interpretation": "Engineering historical isolation is tested; these metrics do not establish present-day performance or realized income improvement.",
    }


def predict_saved_bundle(bundle_dir: Path, feature_rows: pd.DataFrame) -> np.ndarray:
    state = joblib.load(bundle_dir / "preprocessing.joblib")
    matrix = transform(feature_rows, state)
    predictions = np.column_stack([lgb.Booster(model_file=str(bundle_dir / f"q{q}.txt")).predict(matrix, num_threads=2) for q in (10, 50, 90)])
    return np.sort(predictions, axis=1)


def predict_calibrated_bundle(bundle_dir: Path, feature_rows: pd.DataFrame) -> pd.DataFrame:
    """Deploy saved calibrated forecasts for already-engineered historical rows.

    Build lags from bundle history + query keys using build_ex_ante_features and
    independently generate_baseline first. No target-year Yield is needed for
    inference. This helper deliberately does not invent a forecast for missing
    local history. The baseline is supplied as a historical feature, not a label.
    """
    calibration = json.loads((bundle_dir / "calibration.json").read_text())
    if not {"Yield_lag3_mean", "Baseline_Yield"}.issubset(feature_rows.columns):
        raise ValueError("Inference requires calendar-lag features and independent Baseline_Yield")
    if feature_rows[["Yield_lag3_mean", "Baseline_Yield"]].isna().any().any():
        raise ValueError("Inference is unsupported without historical local yield and baseline")
    raw = predict_saved_bundle(bundle_dir, feature_rows)
    caps = feature_rows.Crop.map(calibration["prediction_caps"]).fillna(calibration["default_prediction_cap"]).to_numpy()
    raw[:, 0] -= calibration["model_interval_expansion"]
    raw[:, 2] += calibration["model_interval_expansion"]
    raw = np.clip(raw, 0, caps[:, None])
    result = feature_rows[KEY].copy()
    result[["q10", "q50", "q90"]] = raw
    baseline = np.clip(feature_rows.Baseline_Yield.to_numpy(), 0, caps)
    radius = calibration["baseline_absolute_residual_radius"]
    result["Baseline_Yield"] = baseline
    result["Baseline_q10"] = np.clip(feature_rows.Baseline_Yield.to_numpy() - radius, 0, caps)
    result["Baseline_q90"] = np.clip(feature_rows.Baseline_Yield.to_numpy() + radius, 0, caps)
    return result


def train_run(run_id: str, project_root: Path = PROJECT_ROOT, output_root: Path | None = None,
              promote: bool = True) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}", run_id):
        raise ValueError("run_id must be a safe unique identifier, at most 96 characters")
    start = time.perf_counter()
    sources = {
        "raw_agronomy": project_root / "agriIntel_merged_final_v.csv",
        "generated_price_registry": project_root / "crosswalks/historical_msp_registry.csv",
        "cpi_index": project_root / "data/processed/inflation_index.csv",
        "pipeline_config": project_root / "config/pipeline.yaml",
        "prediction_caps": project_root / "config/biological_yield_caps.yaml",
        "code_features": project_root / "modules/m3_yield/features.py",
        "code_baselines": project_root / "modules/m3_yield/baselines.py",
        "code_data": project_root / "modules/regional_data/data.py",
        "code_training": project_root / "modules/regional_data/train.py",
    }
    for path in sources.values():
        if not path.is_file():
            raise FileNotFoundError(path)
    output_root = output_root or project_root / "data/runs"
    output_root.mkdir(parents=True, exist_ok=True)
    run_dir = output_root / run_id
    run_dir.mkdir(exist_ok=False)  # Never overwrite earlier runs, including failed runs.
    write_json(run_dir / "status.json", {"status": "running", "run_id": run_id})
    try:
        config = yaml.safe_load(sources["pipeline_config"].read_text())
        caps_config = yaml.safe_load(sources["prediction_caps"].read_text())
        cfg = {
            "test_years": config["temporal_cv"]["test_years"],
            "fit_rule": "Year_start <= test_year-2", "calibration_rule": "Year_start == test_year-1",
            "lag_calendar_years": [1, 2, 3], "num_boost_round": 500,
            "quantiles": [0.1, 0.5, 0.9], "seed": 42, "n_jobs": 2,
            "unit_contract": "project-declared tonnes per hectare; original crop-source units unverified",
            "money_basis": "2011 INR; generated prior-year price registry, no statutory-price guarantee",
            "cap_provenance": "legacy project configuration; not independently verified biological limits",
        }
        params = dict(config["lightgbm"]["params"])
        params.update(objective="quantile", n_jobs=2, random_state=42,
                      deterministic=True, force_col_wise=True, verbosity=-1)
        params.pop("verbose", None)
        cfg["lightgbm_params"] = params
        write_json(run_dir / "config.json", cfg)
        print(f"[{run_id}] Reading raw source and applying structural-only cleaning", flush=True)
        cleaned, quarantine, audit = structural_clean(pd.read_csv(sources["raw_agronomy"]))
        cleaned.to_parquet(run_dir / "structural_clean.parquet", index=False)
        quarantine.to_parquet(run_dir / "quarantined_records.parquet", index=False)
        write_json(run_dir / "structural_audit.json", audit)
        data = generate_baseline(build_ex_ante_features(cleaned))
        data = attach_prior_economics(data, pd.read_csv(sources["generated_price_registry"]), pd.read_csv(sources["cpi_index"]))
        data.to_parquet(run_dir / "historical_features.parquet", index=False)
        print(f"[{run_id}] {len(data)} unique records; ex-ante calendar features ready", flush=True)
        all_folds, fold_metadata = [], []
        for test_year in cfg["test_years"]:
            fold_start = time.perf_counter()
            supported = data.Feature_Supported & data.Baseline_Supported & data.Cost_Proxy_per_Hectare.notna() & data.Price_Reference_per_Quintal.notna()
            proper = data[(data.Year_start <= test_year - 2) & supported].copy()
            calibration = data[(data.Year_start == test_year - 1) & supported].copy()
            test = data[data.Year_start == test_year].copy()
            eligible = test.Feature_Supported & test.Baseline_Supported & test.Cost_Proxy_per_Hectare.notna() & test.Price_Reference_per_Quintal.notna()
            test["Supported"] = eligible
            test["Support_Reason"] = np.where(eligible, "historical_local_yield_and_prior_economic_references", "insufficient_prior_three_calendar_year_local_yield_or_economic_reference")
            if proper.empty or len(calibration) < 5 or not eligible.any():
                raise ValueError(f"Fold {test_year} lacks disjoint training/calibration/test support; no random fallback")
            bundle_dir = run_dir / "models" / str(test_year)
            bundle_dir.mkdir(parents=True)
            preprocessor = fit_preprocessor(proper)
            joblib.dump(preprocessor, bundle_dir / "preprocessing.joblib")
            # Persist raw, structurally cleaned observations through the latest
            # eligible historical year for reproducible feature/baseline inference.
            cleaned[cleaned.Year_start < test_year].to_parquet(bundle_dir / "history.parquet", index=False)
            x_train, x_calibration = transform(proper, preprocessor), transform(calibration, preprocessor)
            x_test = transform(test[eligible], preprocessor)
            cal_predictions, predictions = [], []
            print(f"[{run_id}] Fold {test_year}: train<= {test_year-2} n={len(proper)}, cal={test_year-1} n={len(calibration)}, test n={int(eligible.sum())}", flush=True)
            for quantile in (0.1, 0.5, 0.9):
                model = lgb.LGBMRegressor(**params, alpha=quantile, n_estimators=500)
                model.fit(x_train, proper.Yield, categorical_feature=CATEGORICAL)
                cal_predictions.append(model.predict(x_calibration))
                predictions.append(model.predict(x_test))
                model.booster_.save_model(str(bundle_dir / f"q{int(quantile*100)}.txt"))
            cal_array = np.sort(np.column_stack(cal_predictions), axis=1)
            test_array = np.sort(np.column_stack(predictions), axis=1)
            scores = np.maximum(cal_array[:, 0] - calibration.Yield.to_numpy(), calibration.Yield.to_numpy() - cal_array[:, 2])
            qhat = max(0.0, finite_sample_quantile(scores))
            baseline_qhat = finite_sample_quantile(np.abs(calibration.Yield.to_numpy() - calibration.Baseline_Yield.to_numpy()))
            # Save/load check against the actual inference representation.
            reload_array = predict_saved_bundle(bundle_dir, test[eligible].head(5))
            if not np.allclose(reload_array, test_array[:5], rtol=1e-10, atol=1e-10):
                raise AssertionError(f"Saved model predictions do not reproduce fold {test_year}")
            cap = test.loc[eligible, "Crop"].map(caps_config["crops"]).fillna(caps_config["default_cap"]).to_numpy()
            test_array[:, 0] -= qhat
            test_array[:, 2] += qhat
            test_array = np.minimum(np.maximum(test_array, 0), cap[:, None])
            for index, col in enumerate(["q10", "q50", "q90"]):
                test[col] = np.nan
                test.loc[eligible, col] = test_array[:, index]
            test["Baseline_q10"] = np.nan
            test["Baseline_q90"] = np.nan
            test.loc[eligible, "Baseline_q10"] = np.clip(test.loc[eligible, "Baseline_Yield"].to_numpy() - baseline_qhat, 0, cap)
            test.loc[eligible, "Baseline_q90"] = np.clip(test.loc[eligible, "Baseline_Yield"].to_numpy() + baseline_qhat, 0, cap)
            test.loc[eligible, "Baseline_Yield"] = np.clip(test.loc[eligible, "Baseline_Yield"], 0, cap)
            test["Run_ID"] = run_id
            test["Model_Train_Through"] = test_year - 2
            test["Calibration_Year"] = test_year - 1
            test["Unit_Status"] = "project_declared_tonnes_per_hectare_source_vintage_unverified"
            metadata = {
                "test_year": int(test_year), "train_through": int(proper.Year_start.max()),
                "calibration_year": int(test_year-1), "train_rows": len(proper),
                "calibration_rows": len(calibration), "test_rows": len(test),
                "supported_test_rows": int(eligible.sum()), "model_interval_expansion": qhat,
                "baseline_absolute_residual_radius": baseline_qhat, "target_coverage": 0.8,
                "coverage_caveat": "pooled temporal calibration does not guarantee per-crop or future coverage",
                "prediction_caps": caps_config["crops"], "default_prediction_cap": caps_config["default_cap"],
                "seconds": time.perf_counter() - fold_start, "saved_model_reload": "pass",
            }
            write_json(bundle_dir / "calibration.json", metadata)
            deployed = predict_calibrated_bundle(bundle_dir, test[eligible].head(5))
            deployed_columns = ["q10", "q50", "q90", "Baseline_Yield", "Baseline_q10", "Baseline_q90"]
            if not np.allclose(deployed[deployed_columns], test.loc[eligible, deployed_columns].head(5), rtol=1e-10, atol=1e-10):
                raise AssertionError(f"Calibrated deployment reload failed for fold {test_year}")
            metadata["saved_calibrated_reload"] = "pass"
            write_json(bundle_dir / "calibration.json", metadata)
            fold_metadata.append(metadata)
            all_folds.append(test)
            print(f"[{run_id}] Fold {test_year} saved, {metadata['seconds']:.2f}s", flush=True)
        forecasts = pd.concat(all_folds, ignore_index=True)
        required = ["q10", "q50", "q90", "Baseline_Yield", "Baseline_q10", "Baseline_q90", "Yield", "Price_Reference_per_Quintal", "Cost_Proxy_per_Hectare"]
        usable = forecasts[forecasts.Supported]
        if forecasts.duplicated(KEY).any() or not np.isfinite(usable[required].to_numpy()).all():
            raise AssertionError("Forecasts contain invalid duplicate/nonfinite supported rows")
        for lower, median, upper in [("q10", "q50", "q90"), ("Baseline_q10", "Baseline_Yield", "Baseline_q90")]:
            if not ((usable[lower] >= 0) & (usable[lower] <= usable[median]) & (usable[median] <= usable[upper])).all():
                raise AssertionError("Nonnegative ordered forecast invariant failed")
        if set(usable.State.unique()) != set(cleaned.State.unique()):
            raise AssertionError("Supported forecasts do not cover all five source states")
        demonstration = usable[(usable.State == "Tamil Nadu") & (usable.District == "Coimbatore") & (usable.Season == "Kharif") & (usable.Year_start == 2019) & usable.Crop.isin(["Ragi", "Maize", "Onion"])]
        if set(demonstration.Crop) != {"Ragi", "Maize", "Onion"}:
            raise AssertionError("Classroom demonstration crops lack supported history")
        forecasts.to_parquet(run_dir / "historical_forecasts.parquet", index=False)
        metrics = evaluate(forecasts)
        write_json(run_dir / "metrics.json", metrics)
        source_registry = {
            label: {"path": str(path.relative_to(project_root)), "sha256": sha256(path)}
            for label, path in sources.items()
        }
        source_registry["interpretation"] = {
            "agronomy": "raw project merge; annual reporting/release vintages and original unit provenance unavailable",
            "price": "generated category base prices with 6.2% growth, not observed market or guaranteed MSP",
            "cpi": "saved annual index; use only latest calendar year preceding each target, release dates unavailable",
            "soil_irrigation": "raw values only; invalid irrigation -> missing; historical lag then proper-training imputation",
            "statistical_scope": "historical arithmetic isolation, not a claim of operational pre-sowing information availability",
        }
        write_json(run_dir / "source_registry.json", source_registry)
        manifest = {
            "schema_version": 1, "run_id": run_id, "status": "complete",
            "created_at_utc": datetime.now(timezone.utc).isoformat(), "elapsed_seconds": time.perf_counter()-start,
            "forecast_file": "historical_forecasts.parquet", "forecast_rows": len(forecasts),
            "supported_rows": len(usable), "folds": fold_metadata,
            "validation": {"unique_keys": True, "finite_supported_forecasts": True, "nonnegative_ordered_intervals": True,
                           "all_five_states": True, "demo_three_crops_2019": True, "saved_model_reload_all_folds": True},
            "environment": {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__, "lightgbm": lgb.__version__, "platform": platform.platform()},
            "claim_boundary": "Course/historical simulation only; price/cost proxy assumptions, unverified original unit/release vintages, no demonstrated real income gain.",
        }
        manifest["artifact_sha256"] = {str(p.relative_to(run_dir)): sha256(p) for p in sorted(run_dir.rglob("*")) if p.is_file() and p.name != "status.json"}
        write_json(run_dir / "manifest.json", manifest)
        write_json(run_dir / "status.json", {"status": "complete", "run_id": run_id})
        overall = metrics["overall"]
        (run_dir / "REPORT.md").write_text(
            f"# Corrected historical run {run_id}\n\n"
            f"{len(usable):,} supported rows / {len(forecasts):,} test rows. Train through t-2, calibrate t-1, test t.\n\n"
            f"Model RMSE {overall['model']['RMSE']:.6f}; baseline RMSE {overall['baseline']['RMSE']:.6f}. "
            f"Model 80% interval coverage {overall['model']['coverage_80']:.2%}; baseline coverage {overall['baseline']['coverage_80']:.2%}.\n\n"
            "Metrics are a new historical run. No improvement threshold is imposed. Original source release vintages/units remain unverified. "
            "Generated economic proxies are simulation inputs; no farm-income benefit is established. See metrics.json for state, crop, and year counts.\n")
        if promote:
            pointer = {"run_id": run_id, "run_dir": str(run_dir.relative_to(project_root)) if run_dir.is_relative_to(project_root) else str(run_dir),
                       "forecast_file": "historical_forecasts.parquet", "manifest_sha256": sha256(run_dir / "manifest.json")}
            temp_pointer = output_root / f".active-{run_id}.json"
            write_json(temp_pointer, pointer)
            temp_pointer.replace(output_root / "active.json")
        print(json.dumps({"run_dir": str(run_dir), "seconds": time.perf_counter()-start, "metrics": overall, "promoted": promote}, indent=2), flush=True)
        return run_dir
    except Exception as exc:
        write_json(run_dir / "status.json", {"status": "failed", "run_id": run_id, "error_type": type(exc).__name__, "error": str(exc)})
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--no-promote", action="store_true")
    args = parser.parse_args()
    train_run(args.run_id, args.project_root.resolve(), args.output_root, not args.no_promote)


if __name__ == "__main__":
    main()
