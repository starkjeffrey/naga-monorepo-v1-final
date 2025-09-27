#!/usr/bin/env python3
"""
Import all legacy CSV files to PostgreSQL as legacy_ tables.

This script drops existing legacy tables and recreates them from the current CSV files:
- all_students_250811.csv -> legacy_students
- all_academicclasses_250811.csv -> legacy_academic_classes
- all_academiccoursetakers_250811.csv -> legacy_course_takers
- all_receipt_headers_250811.csv -> legacy_receipt_headers
- all_et_results_250811.csv -> legacy_et_results

Usage:
    # Import all tables with fresh data
    docker compose -f docker-compose.local.yml run --rm django \
        python scripts/legacy_imports/import_all_legacy_csv_current.py

    # Import specific table only
    docker compose -f docker-compose.local.yml run --rm django \
        python scripts/legacy_imports/import_all_legacy_csv_current.py --table students

    # Dry run to see what would be imported
    docker compose -f docker-compose.local.yml run --rm django \
        python scripts/legacy_imports/import_all_legacy_csv_current.py --dry-run
"""

import os
import sys
from pathlib import Path

import django
import pandas as pd

# Setup Django
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from django.db import connection


def drop_all_legacy_tables():
    """Drop all existing legacy tables."""
    tables_to_drop = [
        "legacy_students",
        "legacy_academic_classes",
        "legacy_course_takers",
        "legacy_receipt_headers",
        "legacy_et_results",
    ]

    drop_sql = f"DROP TABLE IF EXISTS {', '.join(tables_to_drop)} CASCADE;"

    with connection.cursor() as cursor:
        cursor.execute(drop_sql)

    print(f"✅ Dropped legacy tables: {', '.join(tables_to_drop)}")


def create_legacy_table_from_csv(csv_path: Path, table_name: str) -> None:
    """Create a legacy table from a CSV file with all TEXT columns."""
    print(f"📄 Processing {csv_path.name} -> {table_name}")

    # Read CSV to get column info
    df = pd.read_csv(csv_path, nrows=0)  # Just get headers
    columns = df.columns.tolist()

    print(f"   Found {len(columns)} columns")

    # Create table DDL - all columns as TEXT for simplicity in legacy data
    column_defs = [f'"{col}" TEXT' for col in columns]
    column_defs.append('"csv_row_number" INTEGER')  # Add row tracking
    column_defs.append('"imported_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP')  # Add import timestamp

    create_table_sql = f"""
    DROP TABLE IF EXISTS {table_name};
    CREATE TABLE {table_name} (
        {", ".join(column_defs)}
    );
    """

    with connection.cursor() as cursor:
        cursor.execute(create_table_sql)

    print(f"✅ Created table: {table_name}")

    # Load data using INSERT statements (safer for Docker environment)
    # Read full CSV and add row numbers
    full_df = pd.read_csv(csv_path, low_memory=False)
    full_df["csv_row_number"] = range(1, len(full_df) + 1)

    # Convert all data to strings to handle mixed types and NULL values
    for col in full_df.columns:
        if col != "csv_row_number":  # Don't convert row number to string
            full_df[col] = full_df[col].fillna("NULL").astype(str)

    # Insert data in batches
    batch_size = 1000
    total_rows = len(full_df)

    print(f"   Importing {total_rows:,} rows in batches of {batch_size}")

    try:
        with connection.cursor() as cursor:
            for i in range(0, total_rows, batch_size):
                batch = full_df.iloc[i : i + batch_size]

                # Create parameterized insert
                all_columns = [*columns, "csv_row_number"]
                placeholders = ", ".join(["%s"] * len(all_columns))
                insert_sql = f"""
                INSERT INTO {table_name} ("{('", "'.join(all_columns))}")
                VALUES ({placeholders})
                """

                # Prepare batch data
                batch_data = []
                for _, row in batch.iterrows():
                    row_data = [row[col] for col in all_columns]
                    batch_data.append(row_data)

                # Execute batch insert
                cursor.executemany(insert_sql, batch_data)

                if i + batch_size < total_rows:
                    print(f"   ⏳ Imported {i + batch_size:,} / {total_rows:,} rows...")

        print(f"✅ Successfully imported {total_rows:,} rows into {table_name}")

        # Create some basic indexes for common queries
        create_indexes(table_name, columns)

    except Exception as e:
        print(f"❌ Error importing data: {e!s}")
        raise


def create_indexes(table_name: str, columns: list):
    """Create basic indexes for common query patterns."""
    index_patterns = {
        "legacy_students": ["ID", "Name", "Status", "CurrentProgram", "BatchID"],
        "legacy_academic_classes": ["TermID", "Program", "CourseCode", "ClassID"],
        "legacy_course_takers": ["ID", "ClassID", "parsed_termid", "parsed_coursecode"],
        "legacy_receipt_headers": ["ID", "TermID", "Program", "PmtDate"],
        "legacy_et_results": ["ID", "TermID", "Name", "TestType", "Program"],
    }

    # Get the columns that exist and should be indexed
    columns_to_index = []
    if table_name in index_patterns:
        for idx_col in index_patterns[table_name]:
            if idx_col in columns:
                columns_to_index.append(idx_col)

    # Create indexes
    with connection.cursor() as cursor:
        for col in columns_to_index:
            try:
                index_name = f"idx_{table_name}_{col.lower()}"
                cursor.execute(f'CREATE INDEX {index_name} ON {table_name}("{col}");')
            except Exception:
                # Index might already exist, continue
                pass

    if columns_to_index:
        print(f"✅ Created indexes on: {', '.join(columns_to_index)}")


def main():
    """Main execution function."""
    import argparse

    parser = argparse.ArgumentParser(description="Import all legacy CSV files to PostgreSQL")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be imported without importing")
    parser.add_argument(
        "--table",
        choices=["students", "classes", "coursetakers", "receipts", "etresults"],
        help="Import specific table only",
    )

    args = parser.parse_args()

    print("🗄️  Legacy Data Import - Current CSV Files")
    print("=" * 60)

    # Map table names to CSV files
    csv_mappings = {
        "students": ("all_students_250811.csv", "legacy_students"),
        "classes": ("all_academicclasses_250811.csv", "legacy_academic_classes"),
        "coursetakers": ("all_academiccoursetakers_250811.csv", "legacy_course_takers"),
        "receipts": ("all_receipt_headers_250811.csv", "legacy_receipt_headers"),
        "etresults": ("all_et_results_250811.csv", "legacy_et_results"),
    }

    data_dir = Path(__file__).parent.parent.parent / "data" / "legacy"

    try:
        # Drop all tables first (unless dry run)
        if not args.dry_run:
            drop_all_legacy_tables()

        # Determine which tables to process
        tables_to_process = [args.table] if args.table else csv_mappings.keys()

        total_files = 0
        total_rows = 0

        for table_key in tables_to_process:
            csv_file, table_name = csv_mappings[table_key]
            csv_path = data_dir / csv_file

            if not csv_path.exists():
                print(f"❌ CSV file not found: {csv_file}")
                continue

            if args.dry_run:
                # Just read CSV info for dry run
                df = pd.read_csv(csv_path, nrows=0)
                row_count = len(pd.read_csv(csv_path, low_memory=False))
                print(f"🔍 Would import {csv_file} -> {table_name}")
                print(f"   {len(df.columns)} columns, {row_count:,} rows")
                total_rows += row_count
            else:
                # Actually import the data
                create_legacy_table_from_csv(csv_path, table_name)

                # Count rows for summary
                with connection.cursor() as cursor:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    row_count = cursor.fetchone()[0]
                    total_rows += row_count

            total_files += 1
            print()  # Empty line for readability

        # Print summary
        print("📊 IMPORT SUMMARY")
        print("=" * 60)
        print(f"📄 Files processed: {total_files}")
        print(f"📊 Total rows: {total_rows:,}")

        if args.dry_run:
            print("🔍 DRY RUN - No data was imported")
        else:
            print("✅ Import completed successfully!")

            # Show table sizes
            print("\n📋 Table Sizes:")
            for table_key in tables_to_process:
                _, table_name = csv_mappings[table_key]
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                        count = cursor.fetchone()[0]
                        print(f"   {table_name}: {count:,} rows")
                except Exception:
                    pass

        print("=" * 60)

    except Exception as e:
        print(f"❌ Fatal error: {e!s}")
        sys.exit(1)


if __name__ == "__main__":
    main()
