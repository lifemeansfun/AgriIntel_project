import pandas as pd
import numpy as np
import lightgbm as lgb
import yaml
import json
from sklearn.metrics import mean_squared_error
from pathlib import Path
from modules.m3_yield.features import build_ex_ante_features
from modules.m3_yield.baselines import generate_baseline

def load_config(path: str) -> dict:
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def run_ensemble():
    # Setup paths
    base_dir = Path('/Users/manishharigovind/Desktop/VIT Vellore/5th semester/Data science proogramming/DSP_project')
    data_path = base_dir / 'data/processed/fact_economic_seasonal.parquet'
    pipe_cfg_path = base_dir / 'config/pipeline.yaml'
    caps_cfg_path = base_dir / 'config/biological_yield_caps.yaml'
    family_reg_path = base_dir / 'crosswalks/crop_family_registry.csv'
    
    # Load configs
    pipe_cfg = load_config(pipe_cfg_path)
    caps_cfg = load_config(caps_cfg_path)
    
    # Load data
    df = pd.read_parquet(data_path)
    
    # Check if 'Yield' exists, if not, maybe use 'Production' / 'Area'
    if 'Yield' not in df.columns:
        df['Yield'] = df['Production'] / df['Area']
        
    df = df.dropna(subset=['Yield', 'Year_start'])
    df['Year_start'] = df['Year_start'].astype(int)
    
    # Calculate Lag Depth for stratification
    df['first_year'] = df.groupby(['District', 'Crop', 'Season'])['Year_start'].transform('min')
    df['lag_depth'] = (df['Year_start'] - df['first_year']).clip(upper=3)
    
    # Feature Engineering
    print("Building Ex-Ante Features...")
    df = build_ex_ante_features(df)
    
    print("Generating Baselines...")
    df = generate_baseline(df)
    
    # Encode categoricals
    cat_cols = ['State', 'District', 'Crop', 'Season']
    for c in cat_cols:
        df[c] = df[c].astype('category')
        
    features = [
        'State', 'District', 'Crop', 'Season',
        'Yield_lag3_mean', 'Yield_lag3_std',
        'Rainfall_mm_lag3_mean', 'Rainy_Days_lag3_mean',
        'Mean_Daily_Rainfall_mm_lag3_mean', 'Max_Daily_Rainfall_mm_lag3_mean',
        'irrigation_intensity_lag3_mean', 'canal_share_lag3_mean',
        'Nitrogen_index_lag3_mean', 'Phosphorus_index_lag3_mean', 
        'Potassium_index_lag3_mean', 'Organic_Carbon_index_lag3_mean',
        'pct_acidic_lag3_mean', 'pct_alkaline_lag3_mean', 'pct_saline_lag3_mean',
        'dist_Rainfall_mm_lag3_mean', 'dist_Rainy_Days_lag3_mean',
        'dist_Mean_Daily_Rainfall_mm_lag3_mean', 'dist_Max_Daily_Rainfall_mm_lag3_mean',
        'dist_irrigation_intensity_lag3_mean', 'dist_canal_share_lag3_mean',
        'dist_Nitrogen_index_lag3_mean', 'dist_Phosphorus_index_lag3_mean',
        'dist_Potassium_index_lag3_mean', 'dist_Organic_Carbon_index_lag3_mean',
        'dist_pct_acidic_lag3_mean', 'dist_pct_alkaline_lag3_mean', 'dist_pct_saline_lag3_mean'
    ]
    
    target = 'Yield'
    
    # Walk forward CV with Conformalized Quantile Regression
    test_years = pipe_cfg['temporal_cv']['test_years']
    lgb_params = pipe_cfg['lightgbm']['params']
    quantiles = pipe_cfg['quantiles']
    
    oof_predictions = []
    
    for test_year in test_years:
        print(f"Running Fold for Test Year: {test_year}")
        train_mask = df['Year_start'] < test_year
        test_mask = df['Year_start'] == test_year
        
        full_train_df = df[train_mask]
        test_df = df[test_mask]
        
        if len(test_df) == 0 or len(full_train_df) == 0:
            continue
            
        # Conformal Prediction Split: use most recent year in training as calibration set
        calib_year = full_train_df['Year_start'].max()
        proper_train_mask = full_train_df['Year_start'] < calib_year
        calib_mask = full_train_df['Year_start'] == calib_year
        
        proper_train_df = full_train_df[proper_train_mask]
        calib_df = full_train_df[calib_mask]
        
        if len(proper_train_df) == 0 or len(calib_df) == 0:
             proper_train_df = full_train_df
             calib_df = full_train_df.sample(frac=0.2, random_state=42)
             proper_train_df = proper_train_df.drop(calib_df.index)
             if len(proper_train_df) == 0:
                 proper_train_df = full_train_df
                 calib_df = full_train_df
        
        X_train, y_train = proper_train_df[features], proper_train_df[target]
        X_calib, y_calib = calib_df[features], calib_df[target]
        X_test = test_df[features]
        
        preds_q_calib = {}
        preds_q_test = {}
        
        for q in quantiles:
            params = lgb_params.copy()
            params['alpha'] = q
            
            model = lgb.LGBMRegressor(**params, n_estimators=pipe_cfg['lightgbm']['num_boost_round'])
            model.fit(X_train, y_train, categorical_feature=cat_cols)
            
            preds_q_calib[q] = model.predict(X_calib)
            preds_q_test[q] = model.predict(X_test)
            
        # Chernozhukov rearrangement on test
        raw_preds_test = np.vstack([preds_q_test[0.10], preds_q_test[0.50], preds_q_test[0.90]]).T
        rearranged_preds_test = np.sort(raw_preds_test, axis=1)
        
        # Chernozhukov rearrangement on calib
        raw_preds_calib = np.vstack([preds_q_calib[0.10], preds_q_calib[0.50], preds_q_calib[0.90]]).T
        rearranged_preds_calib = np.sort(raw_preds_calib, axis=1)
        
        # Conformal Score computation (target coverage = 80%)
        errors = np.maximum(rearranged_preds_calib[:, 0] - y_calib.values, y_calib.values - rearranged_preds_calib[:, 2])
        n_calib = len(errors)
        target_alpha = 0.20
        q_val = min(1.0, (1.0 - target_alpha) * (1.0 + 1.0 / n_calib))
        q_hat = np.quantile(errors, q_val)
        
        test_df = test_df.copy()
        # Apply conformal bounds
        test_df['q10'] = rearranged_preds_test[:, 0] - q_hat
        test_df['q50'] = rearranged_preds_test[:, 1]
        test_df['q90'] = rearranged_preds_test[:, 2] + q_hat
        
        # Defensive Clipping
        default_cap = caps_cfg['default_cap']
        crop_caps = caps_cfg['crops']
        
        def cap_yield(row, col):
            val = row[col]
            crop = row['Crop']
            cap = crop_caps.get(crop, default_cap)
            return np.clip(val, 0.0, cap)
            
        test_df['q10'] = test_df.apply(lambda row: cap_yield(row, 'q10'), axis=1)
        test_df['q50'] = test_df.apply(lambda row: cap_yield(row, 'q50'), axis=1)
        test_df['q90'] = test_df.apply(lambda row: cap_yield(row, 'q90'), axis=1)
        
        # Ensure non-crossing after clipping
        test_df['q10'] = np.minimum(test_df['q10'], test_df['q50'])
        test_df['q90'] = np.maximum(test_df['q90'], test_df['q50'])
        
        oof_predictions.append(test_df)
        
    final_oof_df = pd.concat(oof_predictions, ignore_index=True)
    
    # Save OOF
    out_dir = base_dir / 'data/processed'
    final_oof_df.to_parquet(out_dir / 'fact_yield_predictions_oof.parquet')
    
    # Evaluate
    family_df = pd.read_csv(family_reg_path)
    eval_df = final_oof_df.merge(family_df, on='Crop', how='left')
    
    results = {}
    for family in eval_df['Family'].unique():
        if pd.isna(family):
            continue
        sub = eval_df[eval_df['Family'] == family]
        
        baseline_rmse = np.sqrt(mean_squared_error(sub['Yield'], sub['Baseline_Yield']))
        model_rmse = np.sqrt(mean_squared_error(sub['Yield'], sub['q50']))
        
        # RMSE Improvement
        improvement = (baseline_rmse - model_rmse) / baseline_rmse * 100
        
        # Coverage
        coverage = np.mean((sub['Yield'] >= sub['q10']) & (sub['Yield'] <= sub['q90'])) * 100
        
        results[family] = {
            'Baseline_RMSE': float(baseline_rmse),
            'Model_RMSE': float(model_rmse),
            'Improvement_Pct': float(improvement),
            'Coverage_Pct': float(coverage)
        }
        
    overall_baseline = np.sqrt(mean_squared_error(eval_df['Yield'], eval_df['Baseline_Yield']))
    overall_model = np.sqrt(mean_squared_error(eval_df['Yield'], eval_df['q50']))
    overall_coverage = np.mean((eval_df['Yield'] >= eval_df['q10']) & (eval_df['Yield'] <= eval_df['q90'])) * 100
    
    results['Overall'] = {
        'Baseline_RMSE': float(overall_baseline),
        'Model_RMSE': float(overall_model),
        'Improvement_Pct': float((overall_baseline - overall_model) / overall_baseline * 100),
        'Coverage_Pct': float(overall_coverage)
    }
    
    with open(out_dir / 'm3_yield_evaluation_manifest.json', 'w') as f:
        json.dump(results, f, indent=4)
        
    # Generate Report
    report = ["# Module 3 Yield Forecasting Evaluation Report\n"]
    report.append("## Overall Metrics")
    report.append(f"- **Baseline RMSE:** {results['Overall']['Baseline_RMSE']:.4f}")
    report.append(f"- **Model RMSE (q50):** {results['Overall']['Model_RMSE']:.4f}")
    report.append(f"- **Improvement over Baseline:** {results['Overall']['Improvement_Pct']:.2f}%")
    report.append(f"- **80% Prediction Interval Coverage ([q10, q90]):** {results['Overall']['Coverage_Pct']:.2f}%\n")
    
    report.append("## Crop Family Breakdown\n")
    for k, v in results.items():
        if k == 'Overall': continue
        report.append(f"### {k}")
        report.append(f"- Baseline RMSE: {v['Baseline_RMSE']:.4f}")
        report.append(f"- Model RMSE: {v['Model_RMSE']:.4f}")
        report.append(f"- Improvement: {v['Improvement_Pct']:.2f}%")
        report.append(f"- Coverage: {v['Coverage_Pct']:.2f}%\n")
        
    report.append("## Stratification by Lag Depth\n")
    for depth in [1, 2, 3]:
        sub = eval_df[eval_df['lag_depth'] == depth]
        if len(sub) == 0: continue
        model_rmse = np.sqrt(mean_squared_error(sub['Yield'], sub['q50']))
        coverage = np.mean((sub['Yield'] >= sub['q10']) & (sub['Yield'] <= sub['q90'])) * 100
        report.append(f"### Lag Depth {depth}")
        report.append(f"- Count: {len(sub)}")
        report.append(f"- Model RMSE: {model_rmse:.4f}")
        report.append(f"- Coverage: {coverage:.2f}%\n")
        
    with open(out_dir / 'm3_yield_report.md', 'w') as f:
        f.write('\n'.join(report))
        
    print("Done. Saved OOF, manifest, and report.")

if __name__ == "__main__":
    run_ensemble()
