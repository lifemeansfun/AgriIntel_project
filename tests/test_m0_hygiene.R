#!/usr/bin/env Rscript
# ==============================================================================
# AgriIntel — Tests for Module 0 (Data Hygiene & Sanitization Gate)
# ==============================================================================

suppressPackageStartupMessages({
  library(testthat)
  library(data.table)
  library(jsonlite)
})

cat("Running Module 0 Verification & Invariant Tests...\n")

test_that("Sanitized artifacts exist and are non-empty", {
  expect_true(file.exists("data/processed/agronomic_cleaned_v4.csv"))
  expect_true(file.exists("data/processed/agronomic_cleaned_v4.rds"))
  expect_true(file.exists("data/processed/m0_audit_manifest.json"))
  expect_true(file.exists("data/quarantine/m0_quarantined_records.csv"))
})

clean_df <- fread("data/processed/agronomic_cleaned_v4.csv")
manifest <- fromJSON("data/processed/m0_audit_manifest.json")

test_that("Zero missing values in any feature column", {
  na_counts <- sapply(clean_df, function(x) sum(is.na(x)))
  expect_equal(sum(na_counts), 0, info = paste("NAs found in:", names(na_counts[na_counts > 0])))
})

test_that("Zero duplicate composite keys [State, District, Crop, Year, Season]", {
  key_cols <- c("State", "District", "Crop", "Year", "Season")
  dup_count <- anyDuplicated(clean_df, by = key_cols)
  expect_equal(dup_count, 0)
})

test_that("Yield equals Production / Area exactly within numerical tolerance", {
  yield_diff <- max(abs(clean_df$Yield - (clean_df$Production / clean_df$Area)))
  expect_lt(yield_diff, 1e-6)
})

test_that("Area, Production, and Yield are non-negative", {
  expect_true(all(clean_df$Area > 0))
  expect_true(all(clean_df$Production >= 0))
  expect_true(all(clean_df$Yield >= 0))
})

test_that("Irrigation intensity bounded and plausible [0, 2.5]", {
  expect_true(all(clean_df$irrigation_intensity >= 0))
  expect_true(all(clean_df$irrigation_intensity <= 2.5))
})

test_that("Irrigation component sum equals total irrigated area", {
  irr_sum <- clean_df$canal_irrigated_ha + clean_df$well_irrigated_ha + 
             clean_df$tank_irrigated_ha + clean_df$other_irrigated_ha
  expect_equal(clean_df$total_irrigated_ha, irr_sum)
})

test_that("Provenance columns exist with valid boolean/integer types", {
  expect_true("is_soil_imputed" %in% names(clean_df))
  expect_true("soil_imputation_tier" %in% names(clean_df))
  expect_true("is_irrigation_imputed" %in% names(clean_df))
  expect_true("is_multicropped_irrigation" %in% names(clean_df))
  expect_true("crop_failure_flag" %in% names(clean_df))
  
  expect_true(is.logical(clean_df$is_soil_imputed))
  expect_true(is.logical(clean_df$is_irrigation_imputed))
  expect_true(is.logical(clean_df$is_multicropped_irrigation))
  expect_true(is.logical(clean_df$crop_failure_flag))
  expect_true(all(clean_df$soil_imputation_tier %in% c(0L, 1L, 2L)))
})

test_that("Chennai isolated urban record was quarantined", {
  quar_df <- fread("data/quarantine/m0_quarantined_records.csv")
  expect_equal(nrow(quar_df), 1)
  expect_equal(quar_df$District[1], "Chennai")
  expect_equal(quar_df$quarantine_reason[1], "ISOLATED_URBAN_INSUFFICIENT_AGRONOMY")
})

test_that("Manifest metadata matches file dimensions and actions", {
  expect_equal(manifest$final_row_count, nrow(clean_df))
  expect_equal(manifest$final_col_count, ncol(clean_df))
  expect_true(manifest$validation_gate$zero_missing_values)
  expect_true(manifest$validation_gate$unique_composite_keys)
})

cat("\nAll Module 0 unit & property tests passed successfully!\n")
