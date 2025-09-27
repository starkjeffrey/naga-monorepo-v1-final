#!/usr/bin/env python3
"""Import legacy CSV files to MIGRATION database as legacy_ tables.
Run with: DJANGO_SETTINGS_MODULE=config.settings.migration python scripts/legacy_imports/import_csv_to_legacy_tables.py
"""

import os
import sys
from pathlib import Path

import django
import pandas as pd

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.migration")
django.setup()

from django.db import connection


def create_legacy_table_from_csv(csv_path: Path, table_name: str) -> None:
    """Create a legacy table from a CSV file."""
    # Read CSV to get column info
    df = pd.read_csv(csv_path, nrows=0)  # Just get headers
    columns = df.columns.tolist()

    # Create table DDL - all columns as TEXT for simplicity in legacy data
    column_defs = [f'"{col}" TEXT' for col in columns]
    column_defs.append('"csv_row_number" INTEGER')  # Add row tracking

    create_table_sql = f"""
    DROP TABLE IF EXISTS {table_name};
    CREATE TABLE {table_name} (
        {", ".join(column_defs)}
    );
    """

    with connection.cursor() as cursor:
        cursor.execute(create_table_sql)

    # Load data using INSERT statements (safer for Docker environment)
    # Read full CSV and add row numbers
    full_df = pd.read_csv(csv_path, low_memory=False)
    full_df["csv_row_number"] = range(1, len(full_df) + 1)

    # Convert all data to strings to handle mixed types and NULL values
    for col in full_df.columns:
        full_df[col] = full_df[col].fillna("NULL").astype(str)

    # Insert data in batches
    batch_size = 1000
    total_rows = len(full_df)

    try:
        with connection.cursor() as cursor:
            for i in range(0, total_rows, batch_size):
                batch = full_df.iloc[i : i + batch_size]

                # Create parameterized insert
                placeholders = ", ".join(["%s"] * len(columns) + ["%s"])  # +1 for csv_row_number
                insert_sql = f"""
                INSERT INTO {table_name}
                VALUES ({placeholders})
                """

                # Prepare batch data
                batch_data = []
                for _, row in batch.iterrows():
                    row_data = [row[col] for col in columns] + [row["csv_row_number"]]
                    batch_data.append(row_data)

                # Execute batch insert
                cursor.executemany(insert_sql, batch_data)

    except Exception:
        raise


def main():
    """Import all legacy CSV files to legacy_ tables."""
    # Map CSV files to table names
    csv_mappings = {
        "all_students_250624.csv": "legacy_students",
        "all_terms_250624.csv": "legacy_terms",
        "all_academiccoursetakrers_250624.csv": "legacy_academiccoursetakers",
        "all_receipt_headers_250624.csv": "legacy_receipt_headers",
        "all_moo_250624.csv": "legacy_moodle_classes",
    }

    data_dir = Path(__file__).parent.parent.parent / "data" / "migrate"

    for csv_file, table_name in csv_mappings.items():
        csv_path = data_dir / csv_file
        if csv_path.exists():
            create_legacy_table_from_csv(csv_path, table_name)
        else:
            pass


if __name__ == "__main__":
    main()
