#!/usr/bin/env python3
"""
Simple test script to analyze receipt_items data structure.
This tests basic file reading and analysis without Django dependencies.
"""

import csv
import sys
from pathlib import Path


def test_receipt_items_analysis():
    """Analyze receipt_items data structure and quality."""

    print("🚀 Analyzing receipt_items data")
    print("=" * 60)

    # Input file
    input_file = Path(
        "/Users/jeffreystark/NagaProjects/naga-monorepo/backend/data/legacy/data_pipeline/inputs/receipt_items.csv"
    )

    if not input_file.exists():
        print(f"❌ Input file not found: {input_file}")
        return False

    # Check file size
    file_size = input_file.stat().st_size
    print(f"📁 Input file: {input_file}")
    print(f"📊 File size: {file_size:,} bytes ({file_size / (1024 * 1024):.1f} MB)")

    try:
        # Read and analyze the CSV
        with open(input_file, encoding="utf-8") as f:
            # Try to detect encoding issues
            first_line = f.readline()
            print(f"📋 Header: {first_line.strip()}")

            # Reset and use CSV reader
            f.seek(0)
            reader = csv.reader(f)
            headers = next(reader)

            print(f"📊 Number of columns: {len(headers)}")
            print(f"📝 Columns: {headers}")

            # Analyze sample data
            sample_rows = []
            row_count = 0

            for i, row in enumerate(reader):
                row_count += 1
                if i < 5:  # Keep first 5 rows for analysis
                    sample_rows.append(row)
                if i >= 99:  # Stop after 100 rows total
                    break

            print(f"\n🔍 Analysis of first {min(row_count, 100)} rows:")
            print(f"   Rows processed: {row_count}")

            # Analyze column lengths
            if sample_rows:
                print(f"   Sample row lengths: {[len(row) for row in sample_rows[:3]]}")
                print(f"   Expected length: {len(headers)}")

                # Check for inconsistent row lengths
                inconsistent = [i for i, row in enumerate(sample_rows) if len(row) != len(headers)]
                if inconsistent:
                    print(f"   ⚠️ Rows with wrong length: {inconsistent}")
                else:
                    print("   ✅ All sample rows have correct number of columns")

                # Show sample data
                print("\n📄 Sample rows:")
                for i, row in enumerate(sample_rows[:3]):
                    print(f"   Row {i + 1}: {row[:5]}...")  # First 5 columns

            # Count remaining rows to get total
            remaining_count = sum(1 for _ in reader)
            total_rows = row_count + remaining_count
            print(f"\n📊 Total data rows: {total_rows:,}")
            print(f"   Processing time estimate: {total_rows / 1000:.1f}s at 1K rows/sec")

            return True

    except UnicodeDecodeError as e:
        print(f"❌ Encoding error: {e}")
        print("   Try detecting encoding with chardet")
        return False
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        return False


def analyze_config():
    """Analyze the pipeline configuration for receipt_items."""
    print("\n🔧 Pipeline Configuration Analysis")
    print("-" * 40)

    config_file = Path(
        "/Users/jeffreystark/NagaProjects/naga-monorepo/backend/apps/data_pipeline/configs/receipt_items.py"
    )

    if not config_file.exists():
        print(f"❌ Config file not found: {config_file}")
        return False

    try:
        # Read the config file content
        with open(config_file) as f:
            content = f.read()

        print(f"📋 Configuration file: {config_file}")
        print(f"📊 File size: {len(content)} characters")

        # Extract key information
        if "table_name" in content:
            print("✅ Table name configuration found")
        if "column_mappings" in content:
            print("✅ Column mappings found")
        if "cleaning_rules" in content:
            print("✅ Cleaning rules found")
        if "validator_class" in content:
            print("✅ Validator class found")

        # Show first few lines
        lines = content.split("\n")[:10]
        print("\n📄 Configuration preview:")
        for i, line in enumerate(lines, 1):
            if line.strip():
                print(f"   {i:2d}: {line}")

        return True

    except Exception as e:
        print(f"❌ Error reading config: {e}")
        return False


if __name__ == "__main__":
    success1 = test_receipt_items_analysis()
    success2 = analyze_config()

    print("\n" + "=" * 60)
    if success1 and success2:
        print("✅ Analysis completed successfully!")
        print("💡 Ready to run data pipeline on this file")
    else:
        print("❌ Analysis had issues")

    sys.exit(0 if (success1 and success2) else 1)
