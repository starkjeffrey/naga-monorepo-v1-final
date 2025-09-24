#!/usr/bin/env python3
"""
Import legacy students data with dynamic field detection.

Automatically detects CSV field names and creates legacy_students table
with fields matching the CSV structure (lowercase, no underscores).

Usage:
    # Drop existing table and import
    docker compose -f docker-compose.local.yml run --rm django \
        python scripts/legacy_imports/import_legacy_students_dynamic.py --drop-table

    # Import with validation only (dry run)
    docker compose -f docker-compose.local.yml run --rm django \
        python scripts/legacy_imports/import_legacy_students_dynamic.py --dry-run

    # Import specific file
    docker compose -f docker-compose.local.yml run --rm django \
        python scripts/legacy_imports/import_legacy_students_dynamic.py \
        --file data/legacy/all_students_250811.csv
"""

import csv
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import django
from pydantic import BaseModel, Field, ValidationError, create_model, field_validator

# Setup Django
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from django.db import connection, transaction


def clean_field_name(csv_field: str) -> str:
    """Convert CSV field name to database field name (lowercase, no changes to structure)."""
    return csv_field.lower()


def detect_csv_fields(csv_file_path: str) -> list[str]:
    """Read CSV header to detect all field names."""
    with open(csv_file_path, encoding="utf-8") as file:
        reader = csv.reader(file)
        headers = next(reader)
        return headers


def infer_field_type(field_name: str, sample_values: list[str]) -> str:
    """Infer PostgreSQL field type from field name and sample values."""
    # Remove None/empty values for analysis
    non_empty_values = [v for v in sample_values if v and v.strip() and v.lower() not in ["null", "na"]]

    if not non_empty_values:
        return "VARCHAR(255)"

    # Special handling for specific fields
    field_lower = field_name.lower()

    # IPK should be primary key integer
    if field_lower == "ipk":
        return "INTEGER PRIMARY KEY"

    # ID should be integer (convert from padded string)
    if field_lower == "id":
        return "INTEGER"

    # Check for integers
    try:
        for val in non_empty_values[:10]:  # Check first 10 non-empty values
            int(float(val))  # Handle "1.0" format
        return "INTEGER"
    except (ValueError, TypeError):
        pass

    # Check for floats
    try:
        for val in non_empty_values[:10]:
            float(val)
        return "FLOAT"
    except (ValueError, TypeError):
        pass

    # Check for dates
    date_formats = ["%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"]

    for val in non_empty_values[:5]:
        for fmt in date_formats:
            try:
                datetime.strptime(val, fmt)
                return "TIMESTAMP"
            except ValueError:
                continue

    # Determine VARCHAR length based on max length
    max_length = max(len(str(v)) for v in non_empty_values) if non_empty_values else 50

    # Round up to generous increments to avoid truncation errors
    if max_length <= 10:
        length = 50  # More generous default
    elif max_length <= 50:
        length = 100  # Double the detected size
    elif max_length <= 100:
        length = 255  # Jump to 255 for safety
    elif max_length <= 255:
        length = 500  # Large fields get 500
    else:
        length = 1000  # Very large fields get 1000

    return f"VARCHAR({length})"


def analyze_csv_structure(csv_file_path: str, sample_size: int = 5000) -> dict[str, dict[str, Any]]:
    """Analyze CSV structure to determine field types."""
    print(f"🔍 Analyzing CSV structure: {csv_file_path}")

    fields_info = {}

    with open(csv_file_path, encoding="utf-8") as file:
        reader = csv.DictReader(file)

        # Initialize field tracking
        for field in reader.fieldnames:
            fields_info[field] = {"db_name": clean_field_name(field), "sample_values": [], "type": "VARCHAR(255)"}

        # Sample values for type inference
        for i, row in enumerate(reader):
            if i >= sample_size:
                break

            for field in reader.fieldnames:
                value = row.get(field, "").strip()
                if value and len(fields_info[field]["sample_values"]) < 200:
                    fields_info[field]["sample_values"].append(value)

    # Infer types
    for field, info in fields_info.items():
        info["type"] = infer_field_type(field, info["sample_values"])

    return fields_info


def create_dynamic_pydantic_model(fields_info: dict[str, dict[str, Any]]) -> type:
    """Create Pydantic model dynamically based on CSV fields."""

    field_definitions = {}
    validators = {}

    for csv_field, info in fields_info.items():
        db_field = info["db_name"]
        field_type = info["type"]

        # Determine Python type for Pydantic
        if field_type.startswith("VARCHAR"):
            python_type = str | None
        elif field_type == "INTEGER":
            python_type = int | None
        elif field_type == "FLOAT":
            python_type = float | None
        elif field_type == "TIMESTAMP":
            python_type = datetime | None
        else:
            python_type = str | None

        field_definitions[db_field] = (python_type, Field(None, description=f"From CSV field: {csv_field}"))

    # Add audit fields
    field_definitions["csv_row_number"] = (int | None, Field(None, description="CSV row number"))
    field_definitions["imported_at"] = (datetime | None, Field(None, description="Import timestamp"))

    # Create validators for datetime and numeric fields
    datetime_fields = [name for name, info in fields_info.items() if info["type"] == "TIMESTAMP"]
    int_fields = [name for name, info in fields_info.items() if info["type"] == "INTEGER"]
    float_fields = [name for name, info in fields_info.items() if info["type"] == "FLOAT"]

    if datetime_fields:
        db_datetime_fields = [clean_field_name(f) for f in datetime_fields]

        @field_validator(*db_datetime_fields, mode="before")
        @classmethod
        def parse_datetime(cls, v):
            """Parse datetime fields, handling various formats and NULL values."""
            if v is None or v == "" or v == "NULL" or v == "null":
                return None

            if isinstance(v, str):
                # Handle common datetime formats
                for fmt in [
                    "%Y-%m-%d %H:%M:%S.%f",
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%d",
                    "%m/%d/%Y",
                    "%d/%m/%Y",
                ]:
                    try:
                        return datetime.strptime(v, fmt)
                    except ValueError:
                        continue

            if isinstance(v, datetime):
                return v

            return None

        validators["parse_datetime"] = parse_datetime

    if int_fields:
        db_int_fields = [clean_field_name(f) for f in int_fields]

        @field_validator(*db_int_fields, mode="before")
        @classmethod
        def parse_int(cls, v):
            """Parse integer fields, handling NULL and empty values."""
            if v is None or v == "" or v == "NULL" or v == "null":
                return None

            if isinstance(v, str):
                try:
                    # Handle padded strings (e.g., "00123" -> 123)
                    return int(float(v.strip()))
                except (ValueError, TypeError):
                    return None

            return v

        validators["parse_int"] = parse_int

    if float_fields:
        db_float_fields = [clean_field_name(f) for f in float_fields]

        @field_validator(*db_float_fields, mode="before")
        @classmethod
        def parse_float(cls, v):
            """Parse float fields, handling NULL and empty values."""
            if v is None or v == "" or v == "NULL" or v == "null":
                return None

            if isinstance(v, str):
                try:
                    return float(v)
                except (ValueError, TypeError):
                    return None

            return v

        validators["parse_float"] = parse_float

    # String fields validator
    string_fields = [
        clean_field_name(name) for name, info in fields_info.items() if info["type"].startswith("VARCHAR")
    ]

    if string_fields:

        @field_validator(*string_fields, mode="before")
        @classmethod
        def parse_string(cls, v):
            """Parse string fields, handling NULL values and trimming whitespace."""
            if v is None or v == "NULL" or v == "null":
                return None

            if isinstance(v, str):
                v = v.strip()
                if v == "" or v == "NA" or v == "NULL":
                    return None
                return v

            return str(v) if v is not None else None

        validators["parse_string"] = parse_string

    # Create the dynamic model
    DynamicLegacyStudent = create_model("DynamicLegacyStudent", **field_definitions, __validators__=validators)

    return DynamicLegacyStudent


def create_legacy_students_table(fields_info: dict[str, dict[str, Any]], drop_existing: bool = False) -> None:
    """Create the legacy_students table with dynamic schema."""

    drop_sql = "DROP TABLE IF EXISTS legacy_students;" if drop_existing else ""

    # Build CREATE TABLE statement
    field_definitions = []

    # Process all fields, ensuring IPK comes first if it exists
    ipk_field = None
    other_fields = []

    for _csv_field, info in fields_info.items():
        db_field = info["db_name"]
        field_type = info["type"]

        if db_field.lower() == "ipk":
            ipk_field = f'    "{db_field}" {field_type}'
        else:
            other_fields.append(f'    "{db_field}" {field_type}')

    # Add IPK first if it exists
    if ipk_field:
        field_definitions.append(ipk_field)
        field_definitions.extend(other_fields)
    else:
        field_definitions = other_fields
        print("⚠️  No 'IPK' field found in CSV - table will not have a primary key")

    # Add audit fields
    field_definitions.append('    "csv_row_number" INTEGER')
    field_definitions.append('    "imported_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP')

    create_sql = f"""
    CREATE TABLE legacy_students (
{",".join(field_definitions)}
    );
    """

    print("📝 Generated SQL:")
    print(create_sql[:500] + "..." if len(create_sql) > 500 else create_sql)

    # Add indexes for common fields
    indexes = []
    for _csv_field, info in fields_info.items():
        db_field = info["db_name"]
        if db_field.lower() in ["name", "status", "schoolemail", "email"]:
            indexes.append(f'CREATE INDEX idx_legacy_students_{db_field} ON legacy_students("{db_field}");')

    with connection.cursor() as cursor:
        if drop_sql:
            cursor.execute(drop_sql)
            print("✅ Dropped existing legacy_students table")

        cursor.execute(create_sql)
        print(f"✅ Created legacy_students table with {len(fields_info)} fields")

        # Create indexes
        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
            except Exception as e:
                print(f"⚠️  Could not create index: {e}")


def import_students_csv(csv_file_path: str, dry_run: bool = False, limit: int | None = None) -> dict:
    """Import students from CSV using dynamic Pydantic validation."""

    csv_file = Path(csv_file_path)
    if not csv_file.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_file_path}")

    print(f"📄 Processing: {csv_file_path}")
    if dry_run:
        print("🔍 DRY RUN MODE - No data will be modified")
    if limit:
        print(f"🔢 Limiting to {limit} records")

    # Analyze CSV structure
    fields_info = analyze_csv_structure(csv_file_path)

    print(f"📋 Detected {len(fields_info)} fields:")
    for csv_field, info in fields_info.items():
        print(f"  {csv_field} → {info['db_name']} ({info['type']})")

    # Create dynamic Pydantic model
    LegacyStudent = create_dynamic_pydantic_model(fields_info)

    # Create table if not dry run
    if not dry_run:
        create_legacy_students_table(fields_info, drop_existing=True)

    # Statistics tracking
    stats = {
        "total_rows": 0,
        "valid_rows": 0,
        "invalid_rows": 0,
        "inserted_rows": 0,
        "errors": [],
        "validation_errors": [],
    }

    # Process CSV file
    with open(csv_file, encoding="utf-8") as file:
        reader = csv.DictReader(file)

        if not dry_run:
            # Use transaction for data consistency
            with transaction.atomic():
                for row_num, row in enumerate(reader, start=2):
                    stats["total_rows"] += 1

                    if limit and stats["total_rows"] > limit:
                        break

                    try:
                        # Map CSV fields to database fields
                        mapped_data = {}
                        skip_row = False

                        for csv_field, value in row.items():
                            if csv_field in fields_info:
                                db_field = fields_info[csv_field]["db_name"]

                                # Special handling for ID field - must be convertible to integer
                                if db_field.lower() == "id":
                                    try:
                                        # Convert padded string to integer
                                        if value and value.strip():
                                            int(value.strip())
                                        mapped_data[db_field] = value
                                    except (ValueError, TypeError):
                                        # Skip this row if ID cannot be converted to integer
                                        skip_row = True
                                        break
                                else:
                                    mapped_data[db_field] = value

                        if skip_row:
                            stats["invalid_rows"] += 1
                            continue

                        # Add audit data
                        mapped_data["csv_row_number"] = row_num - 1
                        mapped_data["imported_at"] = datetime.now()

                        # Validate with Pydantic
                        validated_student = LegacyStudent(**mapped_data)
                        stats["valid_rows"] += 1

                        # Insert into database
                        insert_student_record(validated_student, fields_info)
                        stats["inserted_rows"] += 1

                        if row_num % 1000 == 0:
                            print(f"⏳ Processed {row_num} rows...")

                    except ValidationError as e:
                        stats["invalid_rows"] += 1
                        error_msg = f"Row {row_num} (ID: {row.get('ID', 'N/A')}): Validation error"
                        stats["validation_errors"].append(
                            {"row": row_num, "id": row.get("ID", "N/A"), "error": str(e)}
                        )

                        if len(stats["validation_errors"]) <= 10:
                            print(f"❌ {error_msg}: {e}")

                    except Exception as e:
                        stats["invalid_rows"] += 1
                        error_msg = f"Row {row_num} (ID: {row.get('ID', 'N/A')}): {e!s}"
                        stats["errors"].append(error_msg)

                        if len(stats["errors"]) <= 10:
                            print(f"❌ {error_msg}")

                        if len(stats["errors"]) > 50:
                            print(f"❌ Too many errors ({len(stats['errors'])}), stopping import")
                            break

        else:
            # Dry run - just validate
            for row_num, row in enumerate(reader, start=2):
                stats["total_rows"] += 1

                if limit and stats["total_rows"] > limit:
                    break

                try:
                    # Map and validate
                    mapped_data = {}
                    for csv_field, value in row.items():
                        if csv_field in fields_info:
                            db_field = fields_info[csv_field]["db_name"]
                            mapped_data[db_field] = value

                    LegacyStudent(**mapped_data)
                    stats["valid_rows"] += 1

                except ValidationError as e:
                    stats["invalid_rows"] += 1
                    if len(stats["validation_errors"]) < 10:
                        print(f"❌ Row {row_num} validation error: {e}")
                    stats["validation_errors"].append({"row": row_num, "id": row.get("ID", "N/A"), "error": str(e)})

                except Exception as e:
                    stats["invalid_rows"] += 1
                    if len(stats["errors"]) < 10:
                        print(f"❌ Row {row_num} error: {e!s}")
                    stats["errors"].append(f"Row {row_num}: {e!s}")

                if row_num % 1000 == 0:
                    print(f"⏳ Validated {row_num} rows...")

    return stats


def insert_student_record(student: BaseModel, fields_info: dict[str, dict[str, Any]]) -> None:
    """Insert a validated student record into the database."""

    # Get all database field names
    db_fields = [info["db_name"] for info in fields_info.values()]
    db_fields.extend(["csv_row_number", "imported_at"])

    # Build INSERT statement with quoted field names
    field_list = ", ".join(f'"{field}"' for field in db_fields)
    placeholder_list = ", ".join(f"%({field})s" for field in db_fields)

    insert_sql = f"""
    INSERT INTO legacy_students ({field_list})
    VALUES ({placeholder_list})
    """

    # Convert Pydantic model to dict for database insertion
    data = student.model_dump()

    with connection.cursor() as cursor:
        cursor.execute(insert_sql, data)


def main():
    """Main execution function."""
    import argparse

    parser = argparse.ArgumentParser(description="Import legacy students with dynamic field detection")
    parser.add_argument(
        "--file",
        default="data/legacy/all_students_250816.csv",
        help="Path to CSV file (default: data/legacy/all_students_250816.csv)",
    )
    parser.add_argument("--drop-table", action="store_true", help="Drop existing table before import")
    parser.add_argument("--dry-run", action="store_true", help="Validate only, do not import data")
    parser.add_argument("--limit", type=int, help="Limit number of records to process (for testing)")

    args = parser.parse_args()

    print("🎓 Dynamic Legacy Students Import")
    print("=" * 60)

    try:
        # Import data
        stats = import_students_csv(args.file, dry_run=args.dry_run, limit=args.limit)

        # Print results
        print("\n📊 IMPORT SUMMARY")
        print("=" * 60)
        print(f"📄 Total rows processed: {stats['total_rows']:,}")
        print(f"✅ Valid rows: {stats['valid_rows']:,}")
        print(f"❌ Invalid rows: {stats['invalid_rows']:,}")

        if not args.dry_run:
            print(f"💾 Successfully inserted: {stats['inserted_rows']:,}")
        else:
            print("🔍 DRY RUN - No data was inserted")

        if stats["validation_errors"]:
            print(f"⚠️  Validation errors: {len(stats['validation_errors'])}")

        if stats["errors"]:
            print(f"🚨 General errors: {len(stats['errors'])}")

        if stats["invalid_rows"] == 0:
            print("🎉 All records processed successfully!")

        print("=" * 60)

    except Exception as e:
        print(f"❌ Fatal error: {e!s}")
        sys.exit(1)


if __name__ == "__main__":
    main()
