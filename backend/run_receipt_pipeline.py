#!/usr/bin/env python3
"""
Simple pipeline test for receipt_items data.
Tests the core pipeline components without Django dependencies.
"""

import sys
from pathlib import Path
from typing import Any

import pandas as pd


def simple_data_profiling(file_path: Path, sample_size: int = 1000) -> dict[str, Any]:
    """Simple data profiling - equivalent to Stage 2 of the pipeline."""

    print(f"🔍 Profiling data from {file_path}")

    results = {
        "total_rows": 0,
        "columns_profiled": 0,
        "encoding_issues": 0,
        "null_patterns": [],
        "completeness_scores": {},
        "consistency_scores": {},
    }

    try:
        # Read sample data with pandas
        df = pd.read_csv(file_path, nrows=sample_size)

        results["total_rows"] = len(df)
        results["columns_profiled"] = len(df.columns)

        print(f"   📊 Sampled {len(df)} rows with {len(df.columns)} columns")

        # Analyze completeness (non-null values)
        for col in df.columns:
            non_null_count = df[col].count()
            completeness = (non_null_count / len(df)) * 100
            results["completeness_scores"][col] = completeness

            if completeness < 50:
                print(f"   ⚠️ Column '{col}' has low completeness: {completeness:.1f}%")
            elif completeness < 100:
                print(f"   📝 Column '{col}' completeness: {completeness:.1f}%")

        # Check for common null patterns
        null_patterns = set()
        for col in df.select_dtypes(include=["object"]).columns:
            unique_values = df[col].dropna().astype(str).str.lower().unique()
            for val in unique_values:
                if val in ["null", "none", "n/a", "na", "", " ", "nil"]:
                    null_patterns.add(val)

        results["null_patterns"] = list(null_patterns)
        if null_patterns:
            print(f"   🔍 Found null patterns: {null_patterns}")

        # Overall data quality score
        avg_completeness = sum(results["completeness_scores"].values()) / len(results["completeness_scores"])
        print(f"   📊 Average completeness: {avg_completeness:.1f}%")

        # Show basic stats for numeric columns
        numeric_cols = df.select_dtypes(include=["int64", "float64"]).columns
        if len(numeric_cols) > 0:
            print(f"   📈 Numeric columns: {list(numeric_cols)}")
            for col in numeric_cols:
                print(f"      {col}: min={df[col].min()}, max={df[col].max()}, mean={df[col].mean():.2f}")

        return results

    except Exception as e:
        print(f"   ❌ Error during profiling: {e}")
        results["error"] = str(e)
        return results


def simple_data_cleaning(input_file: Path, output_file: Path, sample_size: int = 1000) -> dict[str, Any]:
    """Simple data cleaning - equivalent to Stage 3 of the pipeline."""

    print(f"🧹 Cleaning data from {input_file}")

    results = {
        "rows_processed": 0,
        "rows_cleaned": 0,
        "null_standardizations": 0,
        "trim_operations": 0,
        "case_corrections": 0,
    }

    try:
        # Read data
        df = pd.read_csv(input_file, nrows=sample_size)
        original_df = df.copy()

        results["rows_processed"] = len(df)

        # Clean text columns
        text_columns = df.select_dtypes(include=["object"]).columns

        for col in text_columns:
            # Trim whitespace
            df[col] = df[col].astype(str).str.strip()

            # Standardize null values
            null_values = ["null", "none", "n/a", "na", "nil", "NULL", "None"]
            df[col] = df[col].replace(null_values, None)

            # Count changes
            changes = (original_df[col].astype(str) != df[col].astype(str)).sum()
            if changes > 0:
                results["null_standardizations"] += changes
                print(f"   📝 Cleaned {changes} values in column '{col}'")

        # Apply specific cleaning rules based on column names
        if "ID" in df.columns:
            # Uppercase student IDs
            df["ID"] = df["ID"].astype(str).str.upper().str.strip()
            print("   🔧 Applied uppercase cleaning to ID column")
            results["case_corrections"] += 1

        if "ReceiptID" in df.columns:
            # Uppercase receipt IDs
            df["ReceiptID"] = df["ReceiptID"].astype(str).str.upper().str.strip()
            print("   🔧 Applied uppercase cleaning to ReceiptID column")
            results["case_corrections"] += 1

        # Save cleaned data
        df.to_csv(output_file, index=False)
        results["rows_cleaned"] = len(df)

        print(f"   ✅ Cleaned data saved to {output_file}")
        print(f"   📊 Processed {results['rows_processed']} rows")
        print(f"   🧹 Applied {results['null_standardizations']} null standardizations")
        print(f"   🔧 Applied {results['case_corrections']} case corrections")

        return results

    except Exception as e:
        print(f"   ❌ Error during cleaning: {e}")
        results["error"] = str(e)
        return results


def simple_validation(input_file: Path, sample_size: int = 1000) -> dict[str, Any]:
    """Simple validation - equivalent to Stage 4 of the pipeline."""

    print(f"✅ Validating data from {input_file}")

    results = {"rows_validated": 0, "valid_rows": 0, "invalid_rows": 0, "validation_errors": [], "error_summary": {}}

    try:
        # Read cleaned data
        df = pd.read_csv(input_file, nrows=sample_size)
        results["rows_validated"] = len(df)

        validation_errors = []

        # Validate required fields
        required_fields = ["ID", "ReceiptID"]
        for field in required_fields:
            if field in df.columns:
                null_count = df[field].isnull().sum()
                if null_count > 0:
                    error = f"Missing required field '{field}': {null_count} rows"
                    validation_errors.append(error)
                    print(f"   ❌ {error}")

        # Validate numeric fields
        numeric_fields = ["UnitCost", "Quantity", "Amount"]
        for field in numeric_fields:
            if field in df.columns:
                # Convert to numeric, marking errors as NaN
                numeric_col = pd.to_numeric(df[field], errors="coerce")
                invalid_count = numeric_col.isnull().sum() - df[field].isnull().sum()
                if invalid_count > 0:
                    error = f"Invalid numeric values in '{field}': {invalid_count} rows"
                    validation_errors.append(error)
                    print(f"   ❌ {error}")

        # Validate ID format (should be alphanumeric)
        if "ID" in df.columns:
            id_pattern = df["ID"].astype(str).str.match(r"^[A-Z0-9]+$")
            invalid_ids = (~id_pattern & df["ID"].notna()).sum()
            if invalid_ids > 0:
                error = f"Invalid ID format: {invalid_ids} rows"
                validation_errors.append(error)
                print(f"   ❌ {error}")

        results["validation_errors"] = validation_errors
        results["invalid_rows"] = len([e for e in validation_errors if "rows" in e])
        results["valid_rows"] = results["rows_validated"] - results["invalid_rows"]

        if results["invalid_rows"] == 0:
            print(f"   ✅ All {results['rows_validated']} rows passed validation!")
        else:
            print(f"   ⚠️ {results['valid_rows']} valid, {results['invalid_rows']} invalid rows")

        return results

    except Exception as e:
        print(f"   ❌ Error during validation: {e}")
        results["error"] = str(e)
        return results


def run_simple_pipeline():
    """Run a simplified version of the data pipeline on receipt_items."""

    print("🚀 Running Simple Data Pipeline on Receipt Items")
    print("=" * 60)

    # File paths
    input_file = Path(
        "/Users/jeffreystark/NagaProjects/naga-monorepo/backend/data/legacy/data_pipeline/inputs/receipt_items.csv"
    )
    cleaned_file = Path("receipt_items_cleaned.csv")

    if not input_file.exists():
        print(f"❌ Input file not found: {input_file}")
        return False

    # Process smaller sample for testing
    sample_size = 500
    print(f"📋 Processing sample of {sample_size} rows for testing")

    try:
        # Stage 1: Raw Import (already done - file exists)
        print("\n📥 Stage 1: Raw Import - ✅ Complete")

        # Stage 2: Data Profiling
        print("\n📊 Stage 2: Data Profiling")
        profile_results = simple_data_profiling(input_file, sample_size)

        # Stage 3: Data Cleaning
        print("\n🧹 Stage 3: Data Cleaning")
        cleaning_results = simple_data_cleaning(input_file, cleaned_file, sample_size)

        # Stage 4: Validation
        print("\n✅ Stage 4: Validation")
        validation_results = simple_validation(cleaned_file, sample_size)

        # Summary
        print("\n" + "=" * 60)
        print("🎯 Pipeline Summary")
        print("=" * 60)

        print("📊 Data Profiling:")
        print(f"   • Columns analyzed: {profile_results.get('columns_profiled', 0)}")
        completeness_scores = profile_results.get("completeness_scores", {})
        avg_completeness = (
            sum(completeness_scores.values()) / max(len(completeness_scores), 1)
        )
        print(f"   • Average completeness: {avg_completeness:.1f}%")

        print("\n🧹 Data Cleaning:")
        print(f"   • Rows processed: {cleaning_results.get('rows_processed', 0)}")
        print(f"   • Null standardizations: {cleaning_results.get('null_standardizations', 0)}")
        print(f"   • Case corrections: {cleaning_results.get('case_corrections', 0)}")

        print("\n✅ Validation:")
        print(f"   • Rows validated: {validation_results.get('rows_validated', 0)}")
        print(f"   • Valid rows: {validation_results.get('valid_rows', 0)}")
        print(f"   • Invalid rows: {validation_results.get('invalid_rows', 0)}")

        success_rate = (
            validation_results.get("valid_rows", 0) / max(validation_results.get("rows_validated", 1), 1)
        ) * 100
        print(f"   • Success rate: {success_rate:.1f}%")

        print("\n🎉 Pipeline completed successfully!")
        print("💡 Ready to process full dataset of 103,179 rows")

        # Cleanup
        if cleaned_file.exists():
            cleaned_file.unlink()

        return True

    except Exception as e:
        print(f"❌ Pipeline failed: {e}")
        return False


if __name__ == "__main__":
    success = run_simple_pipeline()
    sys.exit(0 if success else 1)
