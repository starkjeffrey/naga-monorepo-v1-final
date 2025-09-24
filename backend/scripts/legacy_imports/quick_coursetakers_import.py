#!/usr/bin/env python3
"""Quick import for academiccoursetakers 250816.csv"""

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


def main():
    # Read CSV
    csv_path = Path("data/legacy/all_academiccoursetakers_250816.csv")
    print(f"📄 Loading: {csv_path}")

    df = pd.read_csv(csv_path, low_memory=False)
    df = df.fillna("")  # Replace NaN with empty strings

    print(f"📊 Found {len(df)} records")

    # Drop and recreate table
    with connection.cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS legacy_course_takers;")

        # Create table with all columns as TEXT for simplicity
        columns = df.columns.tolist()
        column_defs = [f'"{col}" TEXT' for col in columns]
        column_defs.append('"imported_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP')

        create_sql = f"""
        CREATE TABLE legacy_course_takers (
            {", ".join(column_defs)}
        );
        """

        cursor.execute(create_sql)
        print("✅ Created legacy_course_takers table")

        # Insert data
        placeholders = ", ".join(["%s"] * len(columns))
        insert_sql = (
            f"INSERT INTO legacy_course_takers ({', '.join(f'"{col}"' for col in columns)}) VALUES ({placeholders})"
        )

        # Convert DataFrame to list of tuples
        data = [tuple(row) for row in df.values]

        cursor.executemany(insert_sql, data)
        print(f"✅ Inserted {len(data)} records")

        # Create index on IPK for easier querying
        cursor.execute('CREATE INDEX idx_legacy_course_takers_ipk ON legacy_course_takers("IPK");')
        print("✅ Created IPK index")


if __name__ == "__main__":
    main()
