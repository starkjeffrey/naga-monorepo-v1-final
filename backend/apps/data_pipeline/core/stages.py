"""
Pipeline Stage Implementations

Defines all 6 stages of the data processing pipeline.
"""

import json
import re
import time
from pathlib import Path
from typing import Any

import chardet
import pandas as pd
from django.conf import settings
from django.db import connection
from django.utils import timezone
from sqlalchemy import create_engine

from ..configs.base import PipelineLogger, TableConfig
from ..models import DataProfile


def get_sqlalchemy_engine():
    """Get SQLAlchemy engine for pandas operations"""
    db_config = settings.DATABASES["default"]
    database_url = f"postgresql+psycopg://{db_config['USER']}:{db_config['PASSWORD']}@{db_config['HOST']}:{db_config['PORT']}/{db_config['NAME']}"
    return create_engine(database_url)


class Stage1Import:
    """Stage 1: Import CSV data preserving all original values"""

    def __init__(self, config: TableConfig, logger: PipelineLogger):
        self.config = config
        self.logger = logger

    def execute(self, source_file: Path, dry_run: bool = False) -> dict[str, Any]:
        """Import raw CSV data into staging table"""
        start_time = time.time()

        try:
            if not source_file.exists():
                raise FileNotFoundError(f"Source file not found: {source_file}")

            self.logger.info(f"Starting Stage 1 - Import: {source_file}")

            # Detect encoding
            encoding = self._detect_encoding(source_file)
            self.logger.info(f"Detected encoding: {encoding}")

            # Read CSV
            df = self._read_csv_safely(source_file, encoding)

            # Add audit columns
            df = self._add_audit_columns(df, source_file)

            if not dry_run:
                # Create and populate staging table
                self._create_staging_table(df.columns.tolist())
                rows_inserted = self._bulk_insert(df)
                self.logger.info(f"Inserted {rows_inserted} rows")

            execution_time = time.time() - start_time

            return {
                "total_rows": len(df),
                "total_columns": len(df.columns),
                "encoding": encoding,
                "file_size_bytes": source_file.stat().st_size,
                "execution_time_seconds": execution_time,
                "column_list": df.columns.tolist(),
                "dataframe": df if not dry_run else None,
            }

        except Exception as e:
            self.logger.error(f"Stage 1 failed: {e!s}")
            raise

    def _detect_encoding(self, file_path: Path) -> str:
        """Detect file encoding"""
        with open(file_path, "rb") as f:
            raw_data = f.read(min(100000, file_path.stat().st_size))

        result = chardet.detect(raw_data)
        return result["encoding"] or "utf-8"

    def _read_csv_safely(self, file_path: Path, encoding: str) -> pd.DataFrame:
        """Read CSV with error handling"""
        try:
            df = pd.read_csv(
                file_path,
                encoding=encoding,
                dtype=str,  # Everything as string
                keep_default_na=False,
                na_filter=False,
                on_bad_lines="warn",
            )
        except UnicodeDecodeError:
            # Fallback to UTF-8 with error replacement
            df = pd.read_csv(
                file_path,
                encoding="utf-8",
                encoding_errors="replace",
                dtype=str,
                keep_default_na=False,
                na_filter=False,
            )

        return df

    def _add_audit_columns(self, df: pd.DataFrame, source_file: Path) -> pd.DataFrame:
        """Add metadata columns for tracking"""
        import uuid

        df["_import_id"] = str(uuid.uuid4())
        df["_import_timestamp"] = timezone.now().isoformat()
        df["_row_number"] = range(1, len(df) + 1)
        df["_source_file"] = source_file.name
        df["_stage"] = 1
        df["_transformation_path"] = "stage1_import"

        return df

    def _create_staging_table(self, columns: list[str]):
        """Create staging table with all TEXT columns"""
        table_name = f"{self.config.table_name}_stage1_raw"

        with connection.cursor() as cursor:
            cursor.execute(f'DROP TABLE IF EXISTS "{table_name}" CASCADE;')

            column_defs = [f'"{col}" TEXT' for col in columns]

            create_sql = f'''
                CREATE TABLE "{table_name}" (
                    {", ".join(column_defs)},
                    PRIMARY KEY ("_row_number")
                );
            '''
            cursor.execute(create_sql)
            self.logger.info(f"Created staging table: {table_name}")

    def _bulk_insert(self, df: pd.DataFrame) -> int:
        """Bulk insert dataframe into staging table"""
        table_name = f"{self.config.table_name}_stage1_raw"

        if df.empty:
            return 0

        columns = [f'"{col}"' for col in df.columns]
        placeholders = ", ".join(["%s"] * len(columns))

        insert_sql = f'''
            INSERT INTO "{table_name}" ({", ".join(columns)})
            VALUES ({placeholders})
        '''

        with connection.cursor() as cursor:
            data_tuples = [tuple(row) for row in df.values]
            cursor.executemany(insert_sql, data_tuples)
            return cursor.rowcount


class Stage2Profile:
    """Stage 2: Profile data to understand patterns and issues"""

    def __init__(self, config: TableConfig, logger: PipelineLogger, run_id: int):
        self.config = config
        self.logger = logger
        self.run_id = run_id

    def execute(self, stage1_result: dict[str, Any], dry_run: bool = False) -> dict[str, Any]:
        """Profile all columns for data quality"""
        start_time = time.time()

        try:
            self.logger.info("Starting Stage 2 - Profile")

            profiles = {}
            table_name = f"{self.config.table_name}_stage1_raw"

            with connection.cursor() as cursor:
                # Get columns to profile (exclude metadata)
                cursor.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = %s
                      AND column_name NOT LIKE '\\_%%' ESCAPE '\'
                    ORDER BY ordinal_position
                    """,
                    [table_name],
                )

                columns = [row[0] for row in cursor.fetchall()]

                # Profile each column
                for column in columns:
                    profile = self._profile_column(cursor, table_name, column)
                    profiles[column] = profile

                    if not dry_run:
                        # Store profile in database
                        DataProfile.objects.create(
                            pipeline_run_id=self.run_id,
                            table_name=self.config.table_name,
                            column_name=column,
                            **profile,
                        )

            execution_time = time.time() - start_time

            return {
                "total_columns_profiled": len(profiles),
                "column_profiles": profiles,
                "execution_time_seconds": execution_time,
                "recommendations": self._generate_recommendations(profiles),
            }

        except Exception as e:
            self.logger.error(f"Stage 2 failed: {e!s}")
            raise

    def _profile_column(self, cursor, table_name: str, column: str) -> dict[str, Any]:
        """Profile a single column"""
        # Get basic stats
        cursor.execute(f"""
            SELECT
                COUNT(*) as total,
                COUNT(DISTINCT "{column}") as unique_count,
                COUNT(CASE WHEN "{column}" IS NULL OR "{column}" = '' THEN 1 END) as null_count
            FROM "{table_name}"
        """)

        stats = cursor.fetchone()

        # Get common values
        cursor.execute(f"""
            SELECT "{column}", COUNT(*) as cnt
            FROM "{table_name}"
            GROUP BY "{column}"
            ORDER BY cnt DESC
            LIMIT 10
        """)

        common_values = [{"value": row[0], "count": row[1]} for row in cursor.fetchall()]

        return {
            "total_rows": stats[0],
            "unique_count": stats[1],
            "null_count": stats[2],
            "completeness_score": ((stats[0] - stats[2]) / stats[0] * 100) if stats[0] > 0 else 0,
            "common_values": common_values,
        }

    def _generate_recommendations(self, profiles: dict) -> list[str]:
        """Generate cleaning recommendations"""
        recommendations = []

        for col_name, profile in profiles.items():
            if profile["completeness_score"] < 50:
                recommendations.append(f"Column '{col_name}' is {profile['completeness_score']:.1f}% complete")

        return recommendations


class Stage3Clean:
    """Stage 3: Clean data and parse complex fields like ClassID"""

    def __init__(self, config: TableConfig, logger: PipelineLogger, run_id: int):
        self.config = config
        self.logger = logger
        self.run_id = run_id

    def execute(self, stage2_result: dict[str, Any], dry_run: bool = False) -> dict[str, Any]:
        """Clean and parse data"""
        start_time = time.time()

        try:
            self.logger.info("Starting Stage 3 - Clean & Parse")

            # Read data from Stage 1
            raw_table = f"{self.config.table_name}_stage1_raw"
            engine = get_sqlalchemy_engine()
            df = pd.read_sql(f'SELECT * FROM "{raw_table}"', engine)

            # Update transformation path
            df["_transformation_path"] = df["_transformation_path"] + "->stage3_clean"

            # Apply cleaning rules
            df = self._standardize_nulls(df)
            df = self._fix_encoding_issues(df)
            df = self._parse_dates(df)

            # Apply table-specific parsing
            if self.config.table_name == "academiccoursetakers":
                df = self._parse_enrollment_fields(df)
            elif self.config.table_name == "receipt_headers":
                df = self._clean_financial_records(df)

            # Create supplemental records if needed
            supplemental_records = self._create_supplemental_records(df)

            if not dry_run:
                # Save cleaned data
                cleaned_table = f"{self.config.table_name}_stage3_cleaned"
                self._save_cleaned_data(df, cleaned_table)

                # Save supplemental records if any
                if not supplemental_records.empty:
                    supp_table = f"{self.config.table_name}_stage3_supplemental"
                    engine = get_sqlalchemy_engine()
                    supplemental_records.to_sql(supp_table, engine, if_exists="replace", index=False)

            execution_time = time.time() - start_time

            return {
                "total_rows_cleaned": len(df),
                "parsed_fields": self._get_parsed_fields(df),
                "supplemental_records_created": len(supplemental_records),
                "execution_time_seconds": execution_time,
                "dataframe": df,
                "supplemental_dataframe": supplemental_records,
            }

        except Exception as e:
            self.logger.error(f"Stage 3 failed: {e!s}")
            raise

    def _standardize_nulls(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize various NULL representations"""
        null_values = ["NULL", "null", "NA", "N/A", "None", "NONE", ""]

        for col in df.columns:
            if not col.startswith("_"):
                df[col] = df[col].replace(null_values, None)

        return df

    def _fix_encoding_issues(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fix common encoding problems"""
        # Implementation would handle character encoding issues
        return df

    def _parse_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Parse date columns"""
        date_columns = [col for col in df.columns if "date" in col.lower() or "time" in col.lower()]

        for col in date_columns:
            if col in df.columns and not col.startswith("_"):
                df[f"{col}_parsed"] = pd.to_datetime(df[col], errors="coerce")

        return df

    def _parse_enrollment_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Parse enrollment-specific fields including ClassID"""
        self.logger.info("Parsing enrollment fields")

        # Parse ClassID
        if "ClassID" in df.columns:
            df = self._parse_classid(df)

        # Mark records that need special handling
        df["needs_class_session"] = df["parsed_program"].isin(["IEAP", "GEP"])
        df["_has_multiple_components"] = df["parsed_component_name"].notna()

        return df

    def _parse_classid(self, df: pd.DataFrame) -> pd.DataFrame:
        """Enhanced ClassID parsing for both academic and language classes"""
        self.logger.info("Parsing ClassID field")

        def parse_single_classid(classid, row_data=None):
            """Parse one ClassID value with context awareness"""
            if pd.isna(classid) or not classid:
                return {}

            parts = str(classid).split("-")
            if len(parts) < 4:
                return {"parse_error": f"Invalid format: only {len(parts)} parts"}

            result = {}

            # Part 1: Termid
            result["parsed_termid"] = parts[0] if len(parts) > 0 else None

            # Part 2: Program code (582 = IEAP, 583 = GEP, etc.)
            program_map = {
                "582": "IEAP",
                "632": "GESL",
                "688": "EHSS",
                "1187": "EXPRESS",
                "87": "BA",
                "147": "MA",
                "832": "ESP",
                "1427": "Japanese",
                "1949": "Korean",
                "2014": "French",
                "2076": "Computer",
            }
            result["parsed_program"] = program_map.get(parts[1], parts[1]) if len(parts) > 1 else None

            # Part 3: Term ID
            result["parsed_time_of_day"] = parts[2] if len(parts) > 2 else None

            # Determine if this is academic or language based on program
            is_language_class = result["parsed_program"] in ["IEAP", "GEP"]

            # Part 4: Complex parsing based on class type
            if len(parts) > 3:
                part4 = parts[3]

                if is_language_class:
                    # Language class: part4 contains course + section
                    parsed_part4 = self._parse_language_part4(part4, result["parsed_program"])
                    result.update(parsed_part4)
                else:
                    # Academic class: part4 is target audience indicator
                    result["parsed_target_audience"] = part4

            # Part 5: Course code (academic) or component name (language)
            if len(parts) > 4:
                if is_language_class:
                    result["parsed_component_name"] = parts[4]  # e.g., "Grammar", "Speaking"
                else:
                    result["parsed_course_code"] = parts[4]

            # Build standardized course code
            if result.get("parsed_program") and result.get("parsed_level"):
                if result.get("parsed_course"):
                    # For language classes with explicit course codes (e.g., GESL-01)
                    result["standardized_course_code"] = f"{result['parsed_course']}-{result['parsed_level']}"
                else:
                    # For classes using program-based codes (e.g., IEAP-01 from A1A)
                    result["standardized_course_code"] = f"{result['parsed_program']}-{result['parsed_level']}"

                # Validate against SIS course catalog
                if result.get("standardized_course_code"):
                    result["course_code_valid"] = self._validate_course_code(result["standardized_course_code"])

            return result

        def _parse_language_part4(self, part4, program=None):
            """Parse language class part4 into course and section"""
            result = {}

            # Common patterns in language class data
            patterns = [
                # Exception: PRE-B1, PRE-B2 standalone course names
                (
                    r"^(PRE-B[12])(?:/([A-D]))?$",
                    lambda m: {
                        "parsed_course": m.group(1),  # PRE-B1 or PRE-B2 as complete course
                        "parsed_level": "01",  # Default level
                        "parsed_section": m.group(2) if m.group(2) else "A",
                    },
                ),
                # Pattern: GESL-1B, GESL-1A (course-section with dash)
                (
                    r"^([A-Z]+)-(\d+)([A-Z])$",
                    lambda m: {
                        "parsed_course": m.group(1),
                        "parsed_level": f"{int(m.group(2)):02d}",
                        "parsed_section": m.group(3) if m.group(3) in ['A', 'B', 'C', 'D'] else "A",
                        "time_confirmation": m.group(3) if m.group(3) not in ['A', 'B', 'C', 'D'] else None,
                    },
                ),
                # Pattern: A1A, E1A (time-level-section format)
                # First letter = time of day, digit = level, last letter = section
                (
                    r"^([A-Z])(\d+)([A-Z])$",
                    lambda m: {
                        "parsed_time": m.group(1),  # A=afternoon, E=evening, etc.
                        "parsed_level": f"{int(m.group(2)):02d}",  # 1 -> 01
                        "parsed_section": m.group(3),  # A, B, C, D
                        # Note: course code comes from program (IEAP, GESL, etc.)
                    } if (1 <= int(m.group(2)) <= self._get_max_level_for_program(program) and
                          m.group(3) in ['A', 'B', 'C', 'D']) else None,
                ),
                # Pattern: E-BEGINNER, M-INTERMEDIATE, A-ADVANCED
                (
                    r"^([EMA])-(\w+)$",
                    lambda m: {
                        "parsed_time": m.group(1),
                        "parsed_level": self._standardize_level(m.group(2).upper()),
                        "parsed_section": "A",  # Default section
                    },
                ),
                # Pattern: E/2A, M/3B, A/1C
                (
                    r"^([EMA])/(\d+)([A-Z])$",
                    lambda m: {
                        "parsed_time": m.group(1),
                        "parsed_level": f"{int(m.group(2)):02d}",
                        "parsed_section": m.group(3),
                    },
                ),
                # Pattern: 2A, 3B (no time indicator)
                (
                    r"^(\d+)([A-Z])$",
                    lambda m: {
                        "parsed_level": f"{int(m.group(1)):02d}",
                        "parsed_section": m.group(2),
                    },
                ),
                # Pattern: BEGINNER-1M, INTERMEDIATE-2E (level with redundant time confirmation)
                (
                    r"^([A-Z-]+)-\d*([EMA])$",
                    lambda m: {
                        "parsed_level": self._shorten_level_name(m.group(1).strip().upper()),
                        "parsed_section": "A",  # Default section for single class
                        "redundant_time_confirmation": m.group(2),
                    },
                ),
                # Pattern: BEGINNER/A, PRE-BEGINNING-B (level/section with delimiter)
                (
                    r"^([^/-]+)[/-]([A-D])$",
                    lambda m: {
                        "parsed_level": self._shorten_level_name(m.group(1).strip().upper()),
                        "parsed_section": m.group(2),
                    },
                ),
                # Pattern: BEGINNER, INTERMEDIATE (no time/section)
                (
                    r"^(\w+)$",
                    lambda m: {
                        "parsed_level": self._standardize_level(m.group(1).upper()),
                        "parsed_section": "A",
                    },
                ),
            ]

            for pattern, parser in patterns:
                match = re.match(pattern, part4, re.IGNORECASE)
                if match:
                    parsed_result = parser(match)
                    if parsed_result is not None:  # Check for constraint violations
                        result.update(parsed_result)
                        break
            else:
                # Couldn't parse - store as-is for manual review
                result["parsed_level"] = part4
                result["parsed_section"] = "U"  # Unknown
                result["parse_warning"] = f"Could not parse part4: {part4}"

            return result

        def _standardize_level(self, level_text):
            """Standardize level names to codes"""
            level_map = {
                "BEGINNER": "01",
                "ELEMENTARY": "02",
                "PRE-INTERMEDIATE": "03",
                "INTERMEDIATE": "04",
                "UPPER-INTERMEDIATE": "05",
                "ADVANCED": "06",
                "PROFICIENCY": "07",
            }
            return level_map.get(level_text, level_text)

        def _shorten_level_name(self, level_text):
            """Shorten level names using convention (BEGINNER→BEG, PRE-BEGINNING→PRE)"""
            # Handle hyphenated levels - take first part
            if "-" in level_text:
                level_text = level_text.split("-")[0]

            # Apply shortening rules
            shortening_map = {
                "BEGINNER": "BEG",
                "BEGINNING": "BEG",
                "ELEMENTARY": "ELEM",
                "INTERMEDIATE": "INT",
                "ADVANCED": "ADV",
                "PROFICIENCY": "PROF",
                "PRE": "PRE",  # Already short
            }
            return shortening_map.get(level_text, level_text[:3])  # Fallback to first 3 chars

        def _get_max_level_for_program(self, program):
            """Get maximum valid level for each program"""
            program_limits = {
                "IEAP": 4,
                "GESL": 12,
                "EHSS": 12,
                # Add other programs as needed
            }
            return program_limits.get(program, 12)  # Default to 12 if unknown

        def _validate_course_code(self, course_code):
            """Validate course code against SIS curriculum table"""
            try:
                from apps.curriculum.models import Course
                return Course.objects.filter(course_code=course_code).exists()
            except Exception as e:
                # Log warning but don't fail parsing
                self.logger.warning(f"Could not validate course code {course_code}: {e}")
                return None  # Unknown validation status

        # Apply parsing to each row
        parsed_data = df.apply(lambda row: parse_single_classid(row.get("ClassID"), row), axis=1)

        # Extract all unique keys from parsed data
        all_keys = set()
        for item in parsed_data:
            all_keys.update(item.keys())

        # Add all parsed columns to dataframe
        for col in all_keys:
            if not col.startswith("parse_"):
                df[col] = parsed_data.apply(lambda x: x.get(col))

        # Add parsing quality flags
        df["_parsing_complete"] = parsed_data.apply(lambda x: "parse_error" not in x and "parse_warning" not in x)
        df["_parsing_warnings"] = parsed_data.apply(
            lambda x: x.get("parse_warning", "") if "parse_warning" in x else ""
        )
        df["_parsing_errors"] = parsed_data.apply(lambda x: x.get("parse_error", "") if "parse_error" in x else "")

        return df

    def _clean_financial_records(self, df: pd.DataFrame) -> pd.DataFrame:
        """Basic cleaning for financial records - complex logic in Stage 6"""
        self.logger.info("Cleaning financial records")

        # Basic field cleaning and standardization
        df["payment_amount"] = pd.to_numeric(df.get("payment_amount", 0), errors="coerce")
        df["payment_date"] = pd.to_datetime(df.get("payment_date"), errors="coerce")

        if "term_id" in df.columns:
            df["term_id"] = df["term_id"].str.strip()

        if "student_id" in df.columns:
            df["student_id"] = df["student_id"].str.strip()

        # Flag records that need complex allocation
        df["_needs_allocation"] = df.get("payment_type", "").str.upper() == "BULK"

        # Flag records with missing critical data
        df["_has_missing_data"] = df[["payment_amount", "student_id", "term_id"]].isnull().any(axis=1)

        return df

    def _create_supplemental_records(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create supplemental records for complex parsing results"""
        supplemental = []

        # Only for enrollment data with multiple components
        if self.config.table_name == "academiccoursetakers":
            for _idx, row in df.iterrows():
                if row.get("_has_multiple_components"):
                    # Create a supplemental record for component tracking
                    supp_record = {
                        "original_ipk": row.get("IPK"),
                        "original_classid": row.get("ClassID"),
                        "original_row_number": row.get("_row_number"),
                        "component_type": row.get("parsed_component_name"),
                        "parsed_course_code": row.get("standardized_course_code"),
                        "parsed_section": row.get("parsed_section"),
                        "parsed_time": row.get("parsed_time"),
                        "_import_id": row.get("_import_id"),
                        "_supplemental_type": "component",
                    }
                    supplemental.append(supp_record)

        return pd.DataFrame(supplemental)

    def _save_cleaned_data(self, df: pd.DataFrame, table_name: str):
        """Save cleaned data to database"""
        engine = get_sqlalchemy_engine()
        df.to_sql(table_name, engine, if_exists="replace", index=False)
        self.logger.info(f"Saved {len(df)} rows to {table_name}")

    def _get_parsed_fields(self, df: pd.DataFrame) -> list[str]:
        """Get list of parsed fields"""
        return [col for col in df.columns if col.startswith("parsed_") or col.startswith("standardized_")]


class Stage4Validate:
    """Stage 4: Validate data against business rules"""

    def __init__(self, config: TableConfig, logger: PipelineLogger, run_id: int):
        self.config = config
        self.logger = logger
        self.run_id = run_id

    def execute(self, stage3_result: dict[str, Any], dry_run: bool = False) -> dict[str, Any]:
        """Validate cleaned data"""
        start_time = time.time()

        try:
            self.logger.info("Starting Stage 4 - Validate")

            # Get cleaned data
            cleaned_table = f"{self.config.table_name}_stage3_cleaned"
            df = pd.read_sql(f'SELECT * FROM "{cleaned_table}"', connection)

            # Update transformation path
            df["_transformation_path"] = df["_transformation_path"] + "->stage4_validate"

            # Apply validation rules
            valid_rows = []
            invalid_rows = []

            for _idx, row in df.iterrows():
                validation_result = self._validate_row(row)

                if validation_result["is_valid"]:
                    valid_rows.append(row)
                else:
                    row["_validation_errors"] = json.dumps(validation_result["errors"])
                    invalid_rows.append(row)

            if not dry_run:
                # Save valid and invalid data separately
                engine = get_sqlalchemy_engine()
                if valid_rows:
                    valid_df = pd.DataFrame(valid_rows)
                    valid_table = f"{self.config.table_name}_stage4_valid"
                    valid_df.to_sql(valid_table, engine, if_exists="replace", index=False)

                if invalid_rows:
                    invalid_df = pd.DataFrame(invalid_rows)
                    invalid_table = f"{self.config.table_name}_stage4_invalid"
                    invalid_df.to_sql(invalid_table, engine, if_exists="replace", index=False)

            execution_time = time.time() - start_time
            success_rate = (len(valid_rows) / len(df) * 100) if len(df) > 0 else 0

            return {
                "total_rows_validated": len(df),
                "total_rows_valid": len(valid_rows),
                "total_rows_invalid": len(invalid_rows),
                "success_rate_percent": success_rate,
                "execution_time_seconds": execution_time,
                "valid_dataframe": pd.DataFrame(valid_rows) if valid_rows else pd.DataFrame(),
                "invalid_dataframe": pd.DataFrame(invalid_rows) if invalid_rows else pd.DataFrame(),
            }

        except Exception as e:
            self.logger.error(f"Stage 4 failed: {e!s}")
            raise

    def _validate_row(self, row: pd.Series) -> dict[str, Any]:
        """Validate a single row using configured validator or custom rules"""
        errors = []

        # If validator class is configured, use it
        if self.config.validator_class:
            errors.extend(self._validate_with_pydantic(row))

        # Apply table-specific validation
        if self.config.table_name == "academiccoursetakers":
            errors.extend(self._validate_enrollment(row))
        elif self.config.table_name == "receipt_headers":
            errors.extend(self._validate_financial(row))

        return {"is_valid": len(errors) == 0, "errors": errors}

    def _validate_with_pydantic(self, row: pd.Series) -> list[dict]:
        """Validate using Pydantic model if configured"""
        errors = []
        try:
            # Convert row to dict for validator
            row_dict = row.to_dict()

            # Remove metadata columns
            row_dict = {k: v for k, v in row_dict.items() if not k.startswith("_")}

            # Try to validate with Pydantic model
            self.config.validator_class(**row_dict)

        except Exception as e:
            if hasattr(e, "errors"):
                for error in e.errors():
                    errors.append(
                        {
                            "field": error.get("loc", ["unknown"])[0],
                            "error": error.get("msg", str(e)),
                            "type": error.get("type", "validation_error"),
                        }
                    )
            else:
                errors.append({"field": "general", "error": str(e), "type": "validation_error"})

        return errors

    def _validate_enrollment(self, row: pd.Series) -> list[dict]:
        """Validate enrollment-specific rules"""
        errors = []

        # Check required fields
        if pd.isna(row.get("IPK")):
            errors.append({"field": "IPK", "error": "Required field missing", "type": "required"})

        # Check parsed fields
        if pd.isna(row.get("parsed_program")):
            errors.append(
                {
                    "field": "parsed_program",
                    "error": "Could not parse program",
                    "type": "parse_error",
                }
            )

        # Validate standardized course code format (but not existence in new DB yet)
        if row.get("standardized_course_code"):
            if not re.match(r"^[A-Z]{3,6}-\d{2}$", str(row["standardized_course_code"])):
                errors.append(
                    {
                        "field": "standardized_course_code",
                        "error": f"Invalid format: {row['standardized_course_code']}",
                        "type": "format_error",
                    }
                )

        # Validate section codes
        if row.get("parsed_section") and row["parsed_section"] not in [
            "A",
            "B",
            "C",
            "D",
            "U",
        ]:
            errors.append(
                {
                    "field": "parsed_section",
                    "error": f"Invalid section: {row['parsed_section']}",
                    "type": "invalid_value",
                }
            )

        # Check parsing completeness
        if row.get("_parsing_errors"):
            errors.append(
                {
                    "field": "ClassID",
                    "error": row["_parsing_errors"],
                    "type": "parse_error",
                }
            )

        return errors

    def _validate_financial(self, row: pd.Series) -> list[dict]:
        """Validate financial record rules"""
        errors = []

        # Check required fields
        required_fields = ["payment_amount", "student_id", "term_id"]
        for field in required_fields:
            if pd.isna(row.get(field)):
                errors.append(
                    {
                        "field": field,
                        "error": "Required field missing",
                        "type": "required",
                    }
                )

        # Validate payment amount
        amount = row.get("payment_amount")
        if amount is not None and not pd.isna(amount):
            if amount <= 0:
                errors.append(
                    {
                        "field": "payment_amount",
                        "error": f"Invalid amount: {amount}",
                        "type": "invalid_value",
                    }
                )

        # Check if allocation is needed but data is missing
        if row.get("_needs_allocation") and row.get("_has_missing_data"):
            errors.append(
                {
                    "field": "general",
                    "error": "Bulk payment missing required data for allocation",
                    "type": "missing_data",
                }
            )

        return errors


class Stage5Transform:
    """Stage 5: Apply domain-specific transformations"""

    def __init__(self, config: TableConfig, logger: PipelineLogger, run_id: int):
        self.config = config
        self.logger = logger
        self.run_id = run_id

    def execute(self, stage4_result: dict[str, Any], dry_run: bool = False) -> dict[str, Any]:
        """Apply transformations like Limon to Unicode"""
        start_time = time.time()

        try:
            self.logger.info("Starting Stage 5 - Transform")

            # Get valid data from Stage 4
            df = stage4_result.get("valid_dataframe")
            if df is None or df.empty:
                valid_table = f"{self.config.table_name}_stage4_valid"
                df = pd.read_sql(f'SELECT * FROM "{valid_table}"', connection)

            # Update transformation path
            df["_transformation_path"] = df["_transformation_path"] + "->stage5_transform"

            # Apply transformations based on configuration
            transformations_applied = []

            for rule in self.config.transformation_rules:
                if rule.transformer == "khmer_unicode":
                    df = self._transform_khmer_text(df, rule)
                    transformations_applied.append("khmer_unicode")
                elif rule.transformer == "date_format":
                    df = self._transform_dates(df, rule)
                    transformations_applied.append("date_format")
                # Add more transformers as needed

            if not dry_run:
                # Save transformed data
                engine = get_sqlalchemy_engine()
                transformed_table = f"{self.config.table_name}_stage5_transformed"
                df.to_sql(transformed_table, engine, if_exists="replace", index=False)

            execution_time = time.time() - start_time

            return {
                "records_transformed": len(df),
                "transformations_applied": transformations_applied,
                "execution_time_seconds": execution_time,
                "transformed_dataframe": df,
            }

        except Exception as e:
            self.logger.error(f"Stage 5 failed: {e!s}")
            raise

    def _transform_khmer_text(self, df: pd.DataFrame, rule) -> pd.DataFrame:
        """Transform Limon to Unicode Khmer"""
        from .transformations import TransformationContext, transformer_registry

        self.logger.info(f"Transforming Khmer text in column: {rule.source_column}")

        # Get the transformer from registry
        transformer = transformer_registry.get_transformer("khmer.limon_to_unicode")
        if not transformer:
            self.logger.warning("Khmer transformer not found in registry")
            return df

        # Apply transformation to each row
        for idx, row in df.iterrows():
            value = row.get(rule.source_column)

            if value and transformer.can_transform(value):
                context = TransformationContext(
                    source_table=self.config.table_name,
                    source_column=rule.source_column,
                    target_column=rule.target_column or rule.source_column,
                    row_number=idx,
                    pipeline_run_id=self.run_id,
                )

                # Transform the value
                transformed = transformer.transform(value, context)

                # Preserve original if requested
                if rule.preserve_original:
                    df.at[idx, f"{rule.source_column}_original"] = value

                # Set transformed value
                target_col = rule.target_column or rule.source_column
                df.at[idx, target_col] = transformed

        return df

    def _transform_dates(self, df: pd.DataFrame, rule) -> pd.DataFrame:
        """Transform date formats"""
        self.logger.info(f"Transforming dates in column: {rule.source_column}")

        # Implementation would handle date format standardization
        return df


class Stage6Split:
    """Stage 6: Split single records into multiple (headers/lines)"""

    def __init__(self, config: TableConfig, logger: PipelineLogger, run_id: int):
        self.config = config
        self.logger = logger
        self.run_id = run_id

    def execute(self, stage5_result: dict[str, Any], dry_run: bool = False) -> dict[str, Any]:
        """Split records into headers and lines based on table type"""
        start_time = time.time()

        try:
            self.logger.info("Starting Stage 6 - Split Records")

            # Get transformed data
            df = stage5_result.get("transformed_dataframe")
            if df is None or df.empty:
                transformed_table = f"{self.config.table_name}_stage5_transformed"
                df = pd.read_sql(f'SELECT * FROM "{transformed_table}"', connection)

            # Update transformation path
            df["_transformation_path"] = df.get("_transformation_path", "") + "->stage6_split"

            # Process based on table type
            if self.config.table_name == "academiccoursetakers":
                result = self._process_enrollments(df, dry_run)
            elif self.config.table_name == "receipt_headers":
                result = self._process_financial_records(df, dry_run)
            else:
                result = {
                    "skipped": True,
                    "reason": f"No splitting logic for {self.config.table_name}",
                }

            execution_time = time.time() - start_time
            result["execution_time_seconds"] = execution_time

            return result

        except Exception as e:
            self.logger.error(f"Stage 6 failed: {e!s}")
            raise

    def _process_enrollments(self, df: pd.DataFrame, dry_run: bool) -> dict[str, Any]:
        """Create ClassHeader, ClassSession, and ClassPart records"""
        self.logger.info("Processing enrollment records")

        # Check dependencies
        if not self._check_dependencies("enrollments"):
            raise ValueError("Missing dependencies for enrollment processing")

        # Step 1: Create unique ClassHeaders (deduplicated)
        headers_df = self._create_class_headers(df)
        self.logger.info(f"Created {len(headers_df)} unique class headers")

        # Step 2: Create ClassSessions for IEAP/GEP only
        sessions_df = self._create_class_sessions(df, headers_df)
        self.logger.info(f"Created {len(sessions_df)} class sessions")

        # Step 3: Create ClassParts (the line records)
        parts_df = self._create_class_parts(df, headers_df, sessions_df)
        self.logger.info(f"Created {len(parts_df)} class parts")

        # Step 4: Create mapping records for traceability
        mappings_df = self._create_enrollment_mappings(df, headers_df, sessions_df, parts_df)

        if not dry_run:
            # Save all tables
            engine = get_sqlalchemy_engine()
            headers_df.to_sql("class_headers", engine, if_exists="replace", index=False)
            sessions_df.to_sql("class_sessions", engine, if_exists="replace", index=False)
            parts_df.to_sql("class_parts", engine, if_exists="replace", index=False)
            mappings_df.to_sql("enrollment_mappings", engine, if_exists="replace", index=False)

        return {
            "headers_created": len(headers_df),
            "sessions_created": len(sessions_df),
            "parts_created": len(parts_df),
            "mappings_created": len(mappings_df),
            "headers_df": headers_df,
            "sessions_df": sessions_df,
            "parts_df": parts_df,
        }

    def _create_class_headers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create unique class headers"""
        # Define columns that make a class unique
        header_cols = [
            "standardized_course_code",
            "parsed_termid",
            "parsed_section",
            "parsed_program",
        ]

        # Filter out rows with missing key fields
        valid_df = df.dropna(subset=["standardized_course_code", "parsed_termid"])

        # Create unique headers
        headers = valid_df[header_cols].drop_duplicates().reset_index(drop=True)

        # Generate unique header IDs
        headers["class_header_id"] = headers.apply(
            lambda x: f"CH_{x['parsed_termid']}_{x['standardized_course_code']}_{x.get('parsed_section', 'A')}",
            axis=1,
        )

        # Add metadata
        headers["_created_at"] = timezone.now().isoformat()
        headers["_source_table"] = "academiccoursetakers"

        return headers

    def _create_class_sessions(self, df: pd.DataFrame, headers_df: pd.DataFrame) -> pd.DataFrame:
        """Create class sessions for language programs"""
        sessions = []

        # Filter for language classes that need sessions
        language_df = df[df["needs_class_session"]]

        if language_df.empty:
            return pd.DataFrame()

        # Group by unique session characteristics
        session_groups = language_df.groupby(
            [
                "standardized_course_code",
                "parsed_termid",
                "parsed_section",
                "parsed_component_name",
            ]
        )

        for group_key, group_df in session_groups:
            # Link to header
            header_match = headers_df[
                (headers_df["standardized_course_code"] == group_key[0])
                & (headers_df["parsed_termid"] == group_key[1])
                & (headers_df["parsed_section"] == group_key[2])
            ]

            if not header_match.empty:
                session = {
                    "class_session_id": f"CS_{group_key[1]}_{group_key[0]}_{group_key[2]}_{group_key[3]}",
                    "class_header_id": header_match.iloc[0]["class_header_id"],
                    "component_name": group_key[3],  # Grammar, Speaking, etc.
                    "parsed_time": group_df.iloc[0].get("parsed_time"),
                    "_created_at": timezone.now().isoformat(),
                }
                sessions.append(session)

        return pd.DataFrame(sessions)

    def _create_class_parts(
        self, df: pd.DataFrame, headers_df: pd.DataFrame, sessions_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Create enrollment line records (parts)"""
        parts = []

        for idx, row in df.iterrows():
            # Find matching header
            header_match = headers_df[
                (headers_df["standardized_course_code"] == row.get("standardized_course_code"))
                & (headers_df["parsed_termid"] == row.get("parsed_termid"))
                & (headers_df["parsed_section"] == row.get("parsed_section", "A"))
            ]

            if header_match.empty:
                self.logger.warning(f"No header found for row {idx}")
                continue

            # Base part record
            part = {
                "class_part_id": f"CP_{row.get('IPK')}_{idx}",
                "class_header_id": header_match.iloc[0]["class_header_id"],
                "original_ipk": row.get("IPK"),
                "student_id": row.get("student_id"),
                "enrollment_date": row.get("enrollment_date_parsed"),
                "status": row.get("status"),
                "_original_classid": row.get("ClassID"),
                "_row_number": row.get("_row_number"),
                "_import_id": row.get("_import_id"),
            }

            # Link to session if applicable
            if row.get("needs_class_session") and row.get("parsed_component_name"):
                session_match = sessions_df[
                    (sessions_df["class_header_id"] == part["class_header_id"])
                    & (sessions_df["component_name"] == row.get("parsed_component_name"))
                ]

                if not session_match.empty:
                    part["class_session_id"] = session_match.iloc[0]["class_session_id"]

            parts.append(part)

        return pd.DataFrame(parts)

    def _create_enrollment_mappings(self, df, headers_df, sessions_df, parts_df) -> pd.DataFrame:
        """Create mapping records for traceability"""
        mappings = []

        for idx, part in parts_df.iterrows():
            mapping = {
                "mapping_id": f"EM_{idx}",
                "original_ipk": part["original_ipk"],
                "original_classid": part["_original_classid"],
                "class_header_id": part["class_header_id"],
                "class_part_id": part["class_part_id"],
                "class_session_id": part.get("class_session_id"),
                "mapping_type": "enrollment",
                "created_at": timezone.now().isoformat(),
            }
            mappings.append(mapping)

        return pd.DataFrame(mappings)

    def _process_financial_records(self, df: pd.DataFrame, dry_run: bool) -> dict[str, Any]:
        """Complex payment allocation and AR record creation"""
        self.logger.info("Processing financial records")

        # Check dependencies
        if not self._check_dependencies("financial"):
            raise ValueError("Cannot process payments without enrollment data")

        ar_headers = []
        ar_lines = []
        allocation_log = []

        for _idx, payment in df.iterrows():
            if payment.get("_needs_allocation"):
                # Complex allocation for bulk payments
                result = self._allocate_bulk_payment(payment)
                ar_headers.append(result["header"])
                ar_lines.extend(result["lines"])
                allocation_log.append(result["log"])
            else:
                # Simple 1:1 transformation
                ar_headers.append(self._create_simple_ar_header(payment))
                ar_lines.append(self._create_simple_ar_line(payment, ar_headers[-1]))

        # Convert to DataFrames
        ar_headers_df = pd.DataFrame(ar_headers)
        ar_lines_df = pd.DataFrame(ar_lines)
        allocation_log_df = pd.DataFrame(allocation_log)

        if not dry_run:
            # Save AR records
            engine = get_sqlalchemy_engine()
            ar_headers_df.to_sql("ar_transaction_headers", engine, if_exists="replace", index=False)
            ar_lines_df.to_sql("ar_transaction_lines", engine, if_exists="replace", index=False)
            allocation_log_df.to_sql("payment_allocation_log", engine, if_exists="replace", index=False)

        return {
            "ar_headers_created": len(ar_headers_df),
            "ar_lines_created": len(ar_lines_df),
            "allocations_processed": len(allocation_log_df),
            "ar_headers_df": ar_headers_df,
            "ar_lines_df": ar_lines_df,
        }

    def _allocate_bulk_payment(self, payment: pd.Series) -> dict[str, Any]:
        """Complex allocation logic for bulk payments"""
        self.logger.info(f"Allocating bulk payment: {payment.get('receipt_id')}")

        # Step 1: Find related enrollments
        enrollments = self._find_student_enrollments(payment.get("student_id"), payment.get("term_id"))

        # Step 2: Impute missing data if needed
        if not enrollments or len(enrollments) == 0:
            enrollments = self._impute_enrollments(payment)

        # Step 3: Calculate allocation
        total_amount = float(payment.get("payment_amount", 0))
        allocations = self._calculate_allocations(enrollments, total_amount)

        # Step 4: Create header
        header = {
            "ar_header_id": f"ARH_{payment.get('receipt_id')}",
            "original_receipt_id": payment.get("receipt_id"),
            "student_id": payment.get("student_id"),
            "term_id": payment.get("term_id"),
            "payment_date": payment.get("payment_date"),
            "total_amount": total_amount,
            "allocation_method": "calculated" if enrollments else "imputed",
            "_import_id": payment.get("_import_id"),
            "_created_at": timezone.now().isoformat(),
        }

        # Step 5: Create lines
        lines = []
        for i, alloc in enumerate(allocations):
            line = {
                "ar_line_id": f"ARL_{payment.get('receipt_id')}_{i}",
                "ar_header_id": header["ar_header_id"],
                "course_code": alloc["course_code"],
                "allocated_amount": alloc["amount"],
                "allocation_percentage": alloc["percentage"],
                "line_number": i + 1,
                "_created_at": timezone.now().isoformat(),
            }
            lines.append(line)

        # Step 6: Create allocation log
        log = {
            "log_id": f"AL_{payment.get('receipt_id')}",
            "ar_header_id": header["ar_header_id"],
            "enrollment_count": len(enrollments),
            "allocation_count": len(allocations),
            "method_used": header["allocation_method"],
            "allocations_detail": json.dumps(allocations),
            "_created_at": timezone.now().isoformat(),
        }

        return {"header": header, "lines": lines, "log": log}

    def _find_student_enrollments(self, student_id: str, term_id: str) -> list[dict]:
        """Find enrollments for a student in a term"""
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                               SELECT DISTINCT
                                   standardized_course_code,
                                   parsed_section
                               FROM academiccoursetakers_stage5_transformed
                               WHERE student_id = %s
                                 AND parsed_termid = %s
                               """,
                    [student_id, term_id],
                )

                results = cursor.fetchall()
                return [{"course_code": row[0], "section": row[1]} for row in results]
        except Exception as e:
            self.logger.warning(f"Could not find enrollments: {e}")
            return []

    def _impute_enrollments(self, payment: pd.Series) -> list[dict]:
        """Impute enrollments when data is missing"""
        self.logger.warning(f"Imputing enrollments for payment {payment.get('receipt_id')}")

        # Default imputation strategy - assume standard course load
        # This would be customized based on your business rules
        return [
            {"course_code": "IEAP-04", "section": "A"},  # Default courses
            {"course_code": "IEAP-04", "section": "B"},
        ]

    def _calculate_allocations(self, enrollments: list[dict], total_amount: float) -> list[dict]:
        """Calculate how to allocate payment across courses"""
        if not enrollments:
            return []

        # Simple equal allocation - customize based on your rules
        per_course = total_amount / len(enrollments)

        allocations = []
        for enrollment in enrollments:
            allocations.append(
                {
                    "course_code": enrollment["course_code"],
                    "amount": round(per_course, 2),
                    "percentage": round(100.0 / len(enrollments), 2),
                }
            )

        # Adjust for rounding
        total_allocated = sum(a["amount"] for a in allocations)
        if total_allocated != total_amount and allocations:
            allocations[-1]["amount"] += total_amount - total_allocated

        return allocations

    def _create_simple_ar_header(self, payment: pd.Series) -> dict:
        """Create simple AR header for non-bulk payments"""
        return {
            "ar_header_id": f"ARH_{payment.get('receipt_id')}",
            "original_receipt_id": payment.get("receipt_id"),
            "student_id": payment.get("student_id"),
            "term_id": payment.get("term_id"),
            "payment_date": payment.get("payment_date"),
            "total_amount": float(payment.get("payment_amount", 0)),
            "allocation_method": "direct",
            "_import_id": payment.get("_import_id"),
            "_created_at": timezone.now().isoformat(),
        }

    def _create_simple_ar_line(self, payment: pd.Series, header: dict) -> dict:
        """Create simple AR line for non-bulk payments"""
        return {
            "ar_line_id": f"ARL_{payment.get('receipt_id')}_0",
            "ar_header_id": header["ar_header_id"],
            "course_code": payment.get("course_code", "UNKNOWN"),
            "allocated_amount": float(payment.get("payment_amount", 0)),
            "allocation_percentage": 100.0,
            "line_number": 1,
            "_created_at": timezone.now().isoformat(),
        }

    def _check_dependencies(self, process_type: str) -> bool:
        """Check if required dependencies exist"""
        if process_type == "financial":
            # Check if enrollment data has been processed
            with connection.cursor() as cursor:
                cursor.execute("""
                               SELECT EXISTS (
                                   SELECT 1 FROM information_schema.tables
                                   WHERE table_name = 'academiccoursetakers_stage5_transformed'
                               )
                               """)
                return cursor.fetchone()[0]

        return True
