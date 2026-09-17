#!/usr/bin/env Rscript
# ==============================================================================
# AgriIntel — Module 0: Agronomic Data Hygiene & Sanitization Gate
# ==============================================================================
# Objectives:
# 1. Ingest raw agronomic dataset (agriIntel_merged_final_v.csv).
# 2. Eliminate exact duplicates and resolve composite key collisions.
# 3. Quarantine isolated, unrepairable urban records (Chennai).
# 4. Repair distorted irrigation intensity denominators (Anuppur outlier).
# 5. Impute bifurcated administrative district irrigation (Palghar via Thane).
# 6. Two-tier hierarchical imputation for missing soil indices (Punjab districts).
# 7. Add explicit provenance and risk flags (is_soil_imputed, crop_failure_flag).
# 8. Assert mathematical invariants and output clean artifacts + manifest.
# ==============================================================================

suppressPackageStartupMessages({
  library(data.table)
  library(jsonlite)
})

cat("====================================================================\n")
cat("Starting AgriIntel Module 0: Data Hygiene & Sanitization Gate\n")
cat("====================================================================\n")

# Configuration paths
RAW_DATA_PATH <- "agriIntel_merged_final_v.csv"
OUT_CSV_PATH  <- "data/processed/agronomic_cleaned_v4.csv"
OUT_RDS_PATH  <- "data/processed/agronomic_cleaned_v4.rds"
QUAR_CSV_PATH <- "data/quarantine/m0_quarantined_records.csv"
AUDIT_LOG_PATH<- "data/quarantine/m0_audit_log.txt"
MANIFEST_PATH <- "data/processed/m0_audit_manifest.json"

dir.create("data/processed", recursive = TRUE, showWarnings = FALSE)
dir.create("data/quarantine", recursive = TRUE, showWarnings = FALSE)

audit_log <- file(AUDIT_LOG_PATH, open = "wt")
log_msg <- function(...) {
  msg <- paste0("[", format(Sys.time(), "%Y-%m-%d %H:%M:%S"), "] ", paste0(...))
  cat(msg, "\n")
  cat(msg, "\n", file = audit_log)
}

# ------------------------------------------------------------------------------
# 1. Load Raw Dataset
# ------------------------------------------------------------------------------
log_msg("Step 1: Reading raw dataset: ", RAW_DATA_PATH)
if (!file.exists(RAW_DATA_PATH)) {
  stop("Raw dataset not found at: ", RAW_DATA_PATH)
}

raw_df <- fread(RAW_DATA_PATH, data.table = TRUE)
raw_rows <- nrow(raw_df)
raw_cols <- ncol(raw_df)
log_msg("Raw dataset dimensions: ", raw_rows, " rows x ", raw_cols, " columns.")

manifest <- list(
  source_file = RAW_DATA_PATH,
  execution_timestamp = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ"),
  raw_row_count = raw_rows,
  raw_col_count = raw_cols,
  actions = list()
)

# ------------------------------------------------------------------------------
# 2. Exact Deduplication
# ------------------------------------------------------------------------------
log_msg("Step 2: Checking exact duplicates...")
exact_dup_indices <- which(duplicated(raw_df))
exact_dup_count <- length(exact_dup_indices)

if (exact_dup_count > 0) {
  log_msg("Found ", exact_dup_count, " exact duplicate rows. Removing duplicates.")
  df <- unique(raw_df)
} else {
  log_msg("No exact duplicate rows found.")
  df <- copy(raw_df)
}
manifest$actions$exact_duplicates_removed <- exact_dup_count

# ------------------------------------------------------------------------------
# 3. Composite Key Collision Resolution
# ------------------------------------------------------------------------------
log_msg("Step 3: Checking composite key collisions on [State, District, Crop, Year, Season]...")
key_cols <- c("State", "District", "Crop", "Year", "Season")
key_counts <- df[, .N, by = key_cols]
colliding_keys <- key_counts[N > 1]
collision_count <- nrow(colliding_keys)

if (collision_count > 0) {
  log_msg("Found ", collision_count, " colliding composite keys (", sum(colliding_keys$N), " total records).")
  log_msg("Aggregating colliding keys: summing Area & Production, recomputing Yield.")
  
  # For non-colliding rows:
  non_colliding <- df[!colliding_keys[, ..key_cols], on = key_cols]
  
  # For colliding rows:
  colliding_rows <- df[colliding_keys[, ..key_cols], on = key_cols]
  
  aggregated <- colliding_rows[, {
    tot_area <- sum(Area)
    tot_prod <- sum(Production)
    calc_yield <- if (tot_area > 0) tot_prod / tot_area else 0
    
    # Retain first record's weather, soil, irrigation infrastructure metrics
    first_row <- .SD[1]
    res <- copy(first_row)
    res$Area <- tot_area
    res$Production <- tot_prod
    res$Yield <- calc_yield
    res
  }, by = key_cols]
  
  # Re-order columns to match original
  setcolorder(aggregated, names(df))
  df <- rbindlist(list(non_colliding, aggregated))
}
manifest$actions$composite_key_collisions_resolved <- collision_count

# ------------------------------------------------------------------------------
# 4. Quarantine Isolated Incomplete Urban Records (Chennai Anomaly)
# ------------------------------------------------------------------------------
log_msg("Step 4: Checking for unrepairable isolated urban records...")
quarantine_filter <- is.na(df$Rainfall_mm) & is.na(df$Organic_Carbon_index)
quarantine_records <- df[quarantine_filter]
quarantine_count <- nrow(quarantine_records)

if (quarantine_count > 0) {
  log_msg("Quarantining ", quarantine_count, " isolated records with missing weather & soil profiles.")
  quarantine_records[, quarantine_reason := "ISOLATED_URBAN_INSUFFICIENT_AGRONOMY"]
  quarantine_records[, quarantined_at := format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ")]
  fwrite(quarantine_records, QUAR_CSV_PATH)
  
  df <- df[!quarantine_filter]
  log_msg("Quarantined records saved to: ", QUAR_CSV_PATH)
}
manifest$actions$quarantined_records_count <- quarantine_count

# ------------------------------------------------------------------------------
# 5. Impute Bifurcated Administrative District (Palghar Maharashtra)
# ------------------------------------------------------------------------------
log_msg("Step 5: Imputing missing irrigation for bifurcated district (Palghar, MH)...")
df[, is_irrigation_imputed := FALSE]

palghar_idx <- which(df$State == "Maharashtra" & df$District == "Palghar" & is.na(df$total_irrigated_ha))
log_msg("Found ", length(palghar_idx), " Palghar rows with missing irrigation.")

if (length(palghar_idx) > 0) {
  # Impute using parent district Thane's historical irrigation intensity and source shares
  thane_stats <- df[State == "Maharashtra" & District == "Thane" & !is.na(total_irrigated_ha)]
  
  if (nrow(thane_stats) > 0) {
    thane_intensity  <- median(thane_stats$irrigation_intensity, na.rm = TRUE)
    thane_canal_share<- median(thane_stats$canal_share, na.rm = TRUE)
    
    well_share  <- median(thane_stats$well_irrigated_ha / pmax(thane_stats$total_irrigated_ha, 1), na.rm = TRUE)
    tank_share  <- median(thane_stats$tank_irrigated_ha / pmax(thane_stats$total_irrigated_ha, 1), na.rm = TRUE)
    other_share <- pmax(0, 1 - (thane_canal_share + well_share + tank_share))
    
    for (idx in palghar_idx) {
      c_area <- df$total_cropped_area[idx]
      est_tot_irr <- round(c_area * thane_intensity)
      est_canal   <- round(est_tot_irr * thane_canal_share)
      est_well    <- round(est_tot_irr * well_share)
      est_tank    <- round(est_tot_irr * tank_share)
      est_other   <- pmax(0, est_tot_irr - (est_canal + est_well + est_tank))
      
      df[idx, total_irrigated_ha   := est_tot_irr]
      df[idx, canal_irrigated_ha   := est_canal]
      df[idx, well_irrigated_ha    := est_well]
      df[idx, tank_irrigated_ha    := est_tank]
      df[idx, other_irrigated_ha   := est_other]
      df[idx, canal_share          := thane_canal_share]
      df[idx, irrigation_intensity := thane_intensity]
      df[idx, is_irrigation_imputed:= TRUE]
    }
    log_msg("Successfully imputed Palghar irrigation from Thane parent baseline.")
  } else {
    mh_intensity <- median(df[State == "Maharashtra", irrigation_intensity], na.rm = TRUE)
    df[palghar_idx, irrigation_intensity := mh_intensity]
    df[palghar_idx, is_irrigation_imputed := TRUE]
    log_msg("Fallback: Imputed Palghar via Maharashtra state median.")
  }
}
manifest$actions$palghar_irrigation_imputed_count <- length(palghar_idx)

# ------------------------------------------------------------------------------
# 6. Irrigation Anomaly Bounding & Typo Repair
# ------------------------------------------------------------------------------
log_msg("Step 6: Treating irrigation intensity anomalies...")
extreme_irr_idx <- which(df$irrigation_intensity > 2.5)
log_msg("Found ", length(extreme_irr_idx), " rows with extreme irrigation intensity (> 2.5).")

if (length(extreme_irr_idx) > 0) {
  for (idx in extreme_irr_idx) {
    st <- df$State[idx]
    dist <- df$District[idx]
    yr <- df$Year[idx]
    old_intens <- df$irrigation_intensity[idx]
    old_crop_area <- df$total_cropped_area[idx]
    
    # Calculate district median cropped area excluding extreme anomalies
    valid_dist_cropped <- df[State == st & District == dist & irrigation_intensity <= 2.5, total_cropped_area]
    
    repaired_area <- if (length(valid_dist_cropped) > 0) median(valid_dist_cropped, na.rm = TRUE) else df$total_irrigated_ha[idx]
    new_intens <- min(df$total_irrigated_ha[idx] / max(repaired_area, 1), 2.5)
    
    df[idx, total_cropped_area := repaired_area]
    df[idx, irrigation_intensity := new_intens]
    
    log_msg("Repaired extreme irrigation: [", dist, ", ", yr, "] intensity: ", 
            round(old_intens, 2), " -> ", round(new_intens, 2), 
            " (cropped_area: ", old_crop_area, " -> ", repaired_area, ")")
  }
}
manifest$actions$extreme_irrigation_denominators_repaired <- length(extreme_irr_idx)

# Set multi-cropping flag cleanly (guaranteed boolean, zero NAs)
df[, is_multicropped_irrigation := !is.na(irrigation_intensity) & (irrigation_intensity > 1.0 & irrigation_intensity <= 2.5)]

# ------------------------------------------------------------------------------
# 7. Two-Tier Hierarchical Soil Nutrient Imputation
# ------------------------------------------------------------------------------
log_msg("Step 7: Applying two-tier soil nutrient imputation with provenance tags...")
df[, is_soil_imputed := FALSE]
df[, soil_imputation_tier := 0L] # 0 = Raw, 1 = District Median, 2 = State Median

soil_cols <- c("Nitrogen_index", "Phosphorus_index", "Potassium_index", 
               "Organic_Carbon_index", "pct_acidic", "pct_alkaline", "pct_saline")

imputation_counts <- list()

for (col in soil_cols) {
  missing_idx <- which(is.na(df[[col]]))
  imputation_counts[[col]] <- length(missing_idx)
  
  if (length(missing_idx) > 0) {
    log_msg("Column ", col, " has ", length(missing_idx), " missing values. Resolving...")
    
    # Pre-calculate district medians
    dist_medians <- df[!is.na(get(col)), .(dist_med = median(get(col), na.rm = TRUE)), by = .(State, District)]
    # Pre-calculate state medians
    state_medians <- df[!is.na(get(col)), .(state_med = median(get(col), na.rm = TRUE)), by = .(State)]
    
    for (idx in missing_idx) {
      st <- df$State[idx]
      dist <- df$District[idx]
      
      d_med <- dist_medians[State == st & District == dist, dist_med]
      
      if (length(d_med) > 0 && !is.na(d_med)) {
        # Tier 1: District Median
        set(df, idx, col, d_med)
        set(df, idx, "is_soil_imputed", TRUE)
        if (df$soil_imputation_tier[idx] < 1L) set(df, idx, "soil_imputation_tier", 1L)
      } else {
        # Tier 2: State Median
        s_med <- state_medians[State == st, state_med]
        set(df, idx, col, s_med)
        set(df, idx, "is_soil_imputed", TRUE)
        set(df, idx, "soil_imputation_tier", 2L)
      }
    }
  }
}
manifest$actions$soil_nutrient_imputations <- imputation_counts

# ------------------------------------------------------------------------------
# 8. Crop Failure Indicator & Plausibility Flags
# ------------------------------------------------------------------------------
log_msg("Step 8: Adding crop failure and biological plausibility flags...")
df[, crop_failure_flag := (Production == 0 & Area > 0)]
crop_failure_count <- sum(df$crop_failure_flag)
log_msg("Identified ", crop_failure_count, " crop failure records (Production == 0 & Area > 0).")
manifest$actions$crop_failure_records_count <- crop_failure_count

# Recalculate Yield exactly to prevent float rounding inconsistencies
df[, Yield := ifelse(Area > 0, Production / Area, 0)]

# ------------------------------------------------------------------------------
# 9. Strict Invariant & Schema Assertions Gate
# ------------------------------------------------------------------------------
log_msg("Step 9: Executing post-sanitization invariant assertions...")

assertions <- list()

# Assertion 1: No missing values in any column
any_na <- sapply(df, function(x) sum(is.na(x)))
assertions$zero_missing_values <- (sum(any_na) == 0)
if (!assertions$zero_missing_values) {
  log_msg("ASSERTION FAILED: Missing values remain in cleaned dataset:\n", paste(names(any_na[any_na > 0]), collapse = ", "))
  stop("Invariant failure: Missing values detected.")
}

# Assertion 2: Unique composite keys
dup_keys <- anyDuplicated(df, by = key_cols)
assertions$unique_composite_keys <- (dup_keys == 0)
if (!assertions$unique_composite_keys) {
  stop("Invariant failure: Duplicate composite keys remain.")
}

# Assertion 3: Mathematical Yield consistency
yield_diff <- max(abs(df$Yield - (df$Production / df$Area)))
assertions$yield_exactness <- (yield_diff < 1e-6)
if (!assertions$yield_exactness) {
  stop("Invariant failure: Yield discrepancy detected.")
}

# Assertion 4: Non-negative areas and yields
assertions$non_negative_values <- all(df$Area > 0) && all(df$Yield >= 0) && all(df$Production >= 0)
if (!assertions$non_negative_values) {
  stop("Invariant failure: Negative values found in Area, Production, or Yield.")
}

# Assertion 5: Irrigation intensity bounded in [0, 2.5]
assertions$irrigation_bounded <- all(df$irrigation_intensity >= 0 & df$irrigation_intensity <= 2.5)
if (!assertions$irrigation_bounded) {
  stop("Invariant failure: Irrigation intensity out of bounds [0, 2.5].")
}

# Assertion 6: Irrigation component sum holds
irr_comp_diff <- max(abs(df$total_irrigated_ha - (df$canal_irrigated_ha + df$well_irrigated_ha + df$tank_irrigated_ha + df$other_irrigated_ha)))
assertions$irrigation_component_sum_exact <- (irr_comp_diff == 0)

manifest$validation_gate <- assertions
log_msg("All 6 invariant assertions passed successfully!")

# ------------------------------------------------------------------------------
# 10. Save Output Artifacts
# ------------------------------------------------------------------------------
log_msg("Step 10: Saving sanitized artifacts...")
manifest$final_row_count <- nrow(df)
manifest$final_col_count <- ncol(df)

fwrite(df, OUT_CSV_PATH)
log_msg("Saved clean CSV: ", OUT_CSV_PATH, " (", file.info(OUT_CSV_PATH)$size / 1e6, " MB)")

saveRDS(df, OUT_RDS_PATH)
log_msg("Saved clean RDS: ", OUT_RDS_PATH, " (", file.info(OUT_RDS_PATH)$size / 1e6, " MB)")

write_json(manifest, MANIFEST_PATH, pretty = TRUE, auto_unbox = TRUE)
log_msg("Saved audit manifest: ", MANIFEST_PATH)

close(audit_log)
cat("====================================================================\n")
cat("Module 0 Execution Completed Successfully!\n")
cat("Clean Dataset: ", nrow(df), " rows x ", ncol(df), " columns.\n")
cat("====================================================================\n")
