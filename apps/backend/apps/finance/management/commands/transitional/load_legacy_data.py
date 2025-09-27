"""Load legacy CSV data into PostgreSQL for AR reconstruction analysis."""

import csv
import io
from pathlib import Path

from django.db import connection

from apps.common.management.base_migration import BaseMigrationCommand


class Command(BaseMigrationCommand):
    """Load legacy data files into PostgreSQL for comprehensive analysis."""

    help = "Load legacy CSV data (students, terms, receipts, enrollments) into PostgreSQL"

    def execute_migration(self, *args, **options):
        """Execute the actual migration work."""
        return self.handle(*args, **options)

    def get_rejection_categories(self):
        """Return rejection categories for failed loads."""
        return {
            "MISSING_FILE": "Required CSV file not found",
            "INVALID_FORMAT": "CSV format or encoding error",
            "DATABASE_ERROR": "PostgreSQL connection or query error",
            "DATA_VALIDATION": "Data validation failure",
        }

    def add_arguments(self, parser):
        """Add command line arguments."""
        super().add_arguments(parser)

        parser.add_argument(
            "--data-dir",
            type=str,
            default="data/legacy",
            help="Directory containing legacy CSV files",
        )

        parser.add_argument(
            "--drop-existing",
            action="store_true",
            help="Drop existing legacy tables before loading",
        )

        parser.add_argument(
            "--analyze-only",
            action="store_true",
            help="Only analyze file structure, do not load data",
        )

        parser.add_argument(
            "--use-insert",
            action="store_true",
            help="Use INSERT statements instead of COPY (slower but more compatible)",
        )

    def handle(self, *args, **options):
        """Main command handler."""
        try:
            data_dir = Path(options["data_dir"])
            if not data_dir.exists():
                self.stdout.write(self.style.ERROR(f"Data directory not found: {data_dir}"))
                return

            # Define the files we need to load - CRITICAL: includes NormalizedSection for Reading Class pricing
            files_to_load = {
                # Core data for analysis
                "all_students_250802.csv": "legacy_students",
                "all_receipt_headers_250802.csv": "legacy_receipt_headers",
                "all_academiccoursetakers_250802.csv": "legacy_course_takers",  # Contains NormalizedSection
                # Additional files if needed later:
                # 'all_terms_250802.csv': 'legacy_terms',
                # 'all_academicclasses_250802.csv': 'legacy_academic_classes',  # NormalizedSection for size
            }

            # Check all files exist
            missing_files = []
            for filename in files_to_load.keys():
                file_path = data_dir / filename
                if not file_path.exists():
                    missing_files.append(filename)

            if missing_files:
                self.stdout.write(self.style.ERROR(f"Missing files: {missing_files}"))
                return

            if options["analyze_only"]:
                self._analyze_files(data_dir, files_to_load)
                return

            # Drop existing tables if requested
            if options["drop_existing"]:
                self._drop_legacy_tables(list(files_to_load.values()))

            # Load each file
            for filename, table_name in files_to_load.items():
                file_path = data_dir / filename
                self.stdout.write(f"Loading {filename} -> {table_name}")
                self._load_csv_to_table(file_path, table_name, options)

            # Create indexes for performance
            self._create_indexes()

            # Generate summary statistics
            self._generate_summary()

            self.stdout.write(self.style.SUCCESS("Legacy data loading completed successfully"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Legacy data loading failed: {e!s}"))
            raise

    def _analyze_files(self, data_dir: Path, files_to_load: dict[str, str]):
        """Analyze file structure without loading data."""
        self.stdout.write("=== FILE STRUCTURE ANALYSIS ===")

        for filename, _table_name in files_to_load.items():
            file_path = data_dir / filename
            self.stdout.write(f"\n--- {filename} ---")

            try:
                with open(file_path, encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    headers = reader.fieldnames

                    # Count rows
                    row_count = sum(1 for _ in reader)

                    self.stdout.write(f"Columns ({len(headers)}): {', '.join(headers)}")
                    self.stdout.write(f"Row count: {row_count:,}")

                    # Sample first few rows
                    f.seek(0)
                    reader = csv.DictReader(f)
                    sample_rows = []
                    for i, row in enumerate(reader):
                        if i >= 3:  # First 3 rows
                            break
                        sample_rows.append(row)

                    self.stdout.write("Sample data:")
                    for i, row in enumerate(sample_rows, 1):
                        self.stdout.write(f"  Row {i}: {dict(list(row.items())[:5])}...")  # First 5 columns

                    # Note about ID vs IPK distinction
                    if "ID" in headers and "IPK" in headers:
                        self.stdout.write("  📝 Note: ID = student number (NOT record ID), IPK = internal primary key")

                    # Special analysis for files with NormalizedSection (crucial for Reading Class pricing)
                    if "NormalizedSection" in headers:
                        f.seek(0)
                        reader = csv.DictReader(f)
                        section_values = []
                        for i, row in enumerate(reader):
                            if i >= 100:  # Sample first 100 rows
                                break
                            if row.get("NormalizedSection"):
                                section_values.append(row["NormalizedSection"])

                        unique_sections = set(section_values)
                        self.stdout.write("  🔍 NormalizedSection analysis (CRITICAL for Reading Class pricing):")
                        self.stdout.write(f"     Unique sections: {len(unique_sections)}")
                        self.stdout.write(f"     Sample sections: {list(unique_sections)[:10]}")
                        self.stdout.write(f"     Total section values: {len(section_values)}")

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error analyzing {filename}: {e!s}"))

    def _drop_legacy_tables(self, table_names: list[str]):
        """Drop existing legacy tables."""
        self.stdout.write("Dropping existing legacy tables...")

        with connection.cursor() as cursor:
            for table_name in table_names:
                try:
                    cursor.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")
                    self.stdout.write(f"Dropped table: {table_name}")
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Error dropping {table_name}: {e!s}"))

    def _load_csv_to_table(self, file_path: Path, table_name: str, options: dict):
        """Load CSV file into PostgreSQL table."""
        self.stdout.write(f"Loading {file_path.name} -> {table_name}")

        try:
            # First, analyze the CSV structure
            with open(file_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames

                if not headers:
                    self.stdout.write(self.style.ERROR(f"No headers found in {file_path}"))
                    return

                # Sample first 100 rows to determine column types
                sample_data = []
                for i, row in enumerate(reader):
                    if i >= 100:  # Sample first 100 rows
                        break
                    sample_data.append(row)

                if not sample_data:
                    self.stdout.write(self.style.WARNING(f"No data rows found in {file_path}"))
                    return

            # Create table with appropriate column types
            self._create_table_from_csv(table_name, list(headers), sample_data)

            # Load data using COPY command for performance
            # This now uses PostgreSQL's native COPY command which is significantly
            # faster than INSERT statements for large datasets (100,000+ records)
            if options.get("use_insert"):
                self._copy_csv_data_fallback(file_path, table_name, list(headers))
            else:
                self._copy_csv_data(file_path, table_name, list(headers))

            # Get final row count
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = cursor.fetchone()[0]
                self.stdout.write(self.style.SUCCESS(f"Loaded {row_count:,} rows into {table_name}"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error loading {file_path}: {e!s}"))
            raise

    def _create_table_from_csv(self, table_name: str, headers: list[str], sample_data: list[dict]):
        """Create PostgreSQL table based on CSV structure."""
        # Analyze column types based on sample data
        column_definitions = []

        for header in headers:
            # Clean column name for PostgreSQL
            clean_header = self._clean_column_name(header)

            # Determine column type based on sample data
            col_type = self._determine_column_type(header, sample_data)

            column_definitions.append(f"{clean_header} {col_type}")

        # Create table (no primary key column since data already has unique IDs)
        create_sql = f"""
        CREATE TABLE {table_name} (
            {",".join(column_definitions)},
            loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """

        with connection.cursor() as cursor:
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
            cursor.execute(create_sql)
            self.stdout.write(f"Created table {table_name} with {len(headers)} columns")

    def _clean_column_name(self, name: str) -> str:
        """Clean column name for PostgreSQL compatibility."""
        # Convert to lowercase, replace spaces/special chars with underscores
        clean = name.lower().replace(" ", "_").replace("-", "_").replace(".", "_")
        # Remove any remaining non-alphanumeric characters except underscores
        clean = "".join(c if c.isalnum() or c == "_" else "" for c in clean)
        # Ensure it starts with a letter
        if clean and not clean[0].isalpha():
            clean = "col_" + clean
        # Don't rename ID column since we're not adding a primary key
        # if clean == 'id':
        #     clean = 'legacy_id'
        return clean or "unnamed_column"

    def _determine_column_type(self, header: str, sample_data: list[dict]) -> str:
        """Determine PostgreSQL column type based on sample data."""
        values = [row.get(header, "").strip() for row in sample_data if row.get(header, "").strip()]

        if not values:
            return "TEXT"  # Default for empty columns

        # Force certain columns to be text (IDs, codes, etc.)
        if header.upper() in [
            "ID",
            "STUDENTID",
            "STUDENT_ID",
            "TERMID",
            "TERM_ID",
            "CLASSID",
            "CLASS_ID",
            "RECEIPTNO",
            "RECEIPTID",
            "CHECKNO",
            "RECID",
            "IPK",
            "GROUPID",
            "INTGROUPID",
            "BATCHID",
            "BATCHIDFORUNDER",
            "BATCHIDFORMASTER",
            "BATCHIDFORDOCTOR",
            "UI",
            "PW",
            "COLOR",
        ]:
            return "VARCHAR(255)"

        # Force date columns to be TIMESTAMP
        if any(date_word in header.upper() for date_word in ["DATE", "TIME", "CREATED", "MODIFIED", "UPDATED"]):
            return "TIMESTAMP"

        # Check for numeric patterns
        all_integers = True
        all_decimals = True
        all_dates = True

        for value in values[:20]:  # Check first 20 non-empty values
            if value.lower() in ("null", "none", ""):
                continue

            # Check integer
            try:
                int(value)
            except ValueError:
                all_integers = False

            # Check decimal
            try:
                float(value)
            except ValueError:
                all_decimals = False

            # Check date patterns
            if not (len(value) >= 8 and any(sep in value for sep in ["-", "/", "."])):
                all_dates = False

        # Determine type based on patterns
        if all_integers and len(max(values, key=len)) <= 10:
            return "INTEGER"
        elif all_decimals:
            return "DECIMAL(15,4)"
        elif all_dates and "date" in header.lower():
            return "TIMESTAMP"
        else:
            # Use VARCHAR with length based on max content
            max_length = max(len(v) for v in values) if values else 50
            # Increase buffer significantly for safety
            return f"VARCHAR({min(max(max_length * 3, 100), 1000)})"  # Increased buffer for safety

    def _copy_csv_data(self, file_path: Path, table_name: str, headers: list[str]):
        """Load CSV data using PostgreSQL's high-performance COPY command."""
        self.stdout.write(f"Using high-performance COPY for {file_path.name}")
        clean_headers = [self._clean_column_name(h) for h in headers]

        with connection.cursor() as cursor:
            try:
                with open(file_path, encoding="utf-8") as f:
                    # Skip header row
                    next(f)

                    # Create a StringIO buffer for processing the data
                    f_buffer = io.StringIO()

                    # Process the file and write to buffer
                    row_count = 0
                    skipped_count = 0
                    for line in f:
                        # Skip malformed records with backslashes in IDs
                        if "\\" in line.split(",")[0] or "00316\\" in line:
                            skipped_count += 1
                            continue
                        # Replace null bytes which can cause COPY to fail
                        clean_line = line.replace("\x00", "")
                        f_buffer.write(clean_line)
                        row_count += 1

                        # Show progress every 10,000 rows
                        if row_count % 10000 == 0:
                            self.stdout.write(f"  Processing row {row_count:,}...")

                    # Reset buffer position
                    f_buffer.seek(0)

                    # Use COPY command for high-performance loading
                    cursor.copy_expert(
                        f"COPY {table_name} ({','.join(clean_headers)}) "
                        f"FROM STDIN WITH (FORMAT CSV, DELIMITER ',', NULL '')",
                        f_buffer,
                    )
                    self.stdout.write(self.style.SUCCESS(f"COPY successful: {row_count:,} rows loaded"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"COPY failed, falling back to INSERT: {e}"))
                # Fall back to the original INSERT method if COPY fails
                self._copy_csv_data_fallback(file_path, table_name, headers)

    def _copy_csv_data_fallback(self, file_path: Path, table_name: str, headers: list[str]):
        """Fallback method using INSERT statements if COPY fails."""
        self.stdout.write("Using fallback INSERT method...")
        # Clean headers for column names
        clean_headers = [self._clean_column_name(h) for h in headers]

        # Prepare INSERT statement
        placeholders = ",".join(["%s"] * len(clean_headers))
        insert_sql = f"INSERT INTO {table_name} ({','.join(clean_headers)}) VALUES ({placeholders})"

        batch_size = 1000
        batch_data = []
        rows_inserted = 0

        with connection.cursor() as cursor:
            with open(file_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)

                for row in reader:
                    # Skip malformed records
                    student_id = row.get("ID", "").strip()
                    if "\\" in student_id or '"' in student_id:
                        self.stdout.write(self.style.WARNING(f"  Skipping malformed record with ID: {student_id}"))
                        continue

                    # Extract values in the same order as clean_headers
                    values: list[str | None] = []
                    for header in headers:
                        value = row.get(header, "").strip()
                        # Convert "NULL" strings to actual NULL values
                        if value.upper() == "NULL" or value == "":
                            values.append(None)
                        else:
                            values.append(value)
                    batch_data.append(values)

                    # Insert in batches for better performance
                    if len(batch_data) >= batch_size:
                        cursor.executemany(insert_sql, batch_data)
                        rows_inserted += len(batch_data)
                        self.stdout.write(f"  Inserted {rows_inserted:,} rows...")
                        batch_data = []

                # Insert remaining data
                if batch_data:
                    cursor.executemany(insert_sql, batch_data)
                    rows_inserted += len(batch_data)

        self.stdout.write(f"  Total rows inserted: {rows_inserted:,}")

    def _create_indexes(self):
        """Create indexes on legacy tables for performance."""
        indexes = [
            # Students table
            ("legacy_students", "id", "student number lookup (NOT record ID)"),
            ("legacy_students", "name", "student name search"),
            # Terms table
            ("legacy_terms", "termid", "term ID lookup"),
            ("legacy_terms", "termname", "term description search"),
            # Receipt headers table
            ("legacy_receipt_headers", "id", "student number lookup (NOT record ID)"),
            ("legacy_receipt_headers", "termid", "term ID lookup"),
            ("legacy_receipt_headers", "receiptno", "receipt number lookup"),
            ("legacy_receipt_headers", "pmtdate", "payment date range queries"),
            # Academic classes table
            ("legacy_academic_classes", "termid", "term ID lookup"),
            ("legacy_academic_classes", "coursecode", "course lookup"),
            (
                "legacy_academic_classes",
                "normalizedsection",
                "CRITICAL: class size for Reading Class pricing",
            ),
            ("legacy_academic_classes", "normalizedcourse", "normalized course lookup"),
            # Course takers table
            ("legacy_course_takers", "id", "student number lookup (NOT record ID)"),
            ("legacy_course_takers", "classid", "class ID lookup"),
            (
                "legacy_course_takers",
                "normalizedsection",
                "CRITICAL: enrollment size for Reading Class pricing",
            ),
            ("legacy_course_takers", "normalizedcourse", "normalized course lookup"),
        ]

        self.stdout.write("Creating indexes for performance...")

        with connection.cursor() as cursor:
            for table_name, column, description in indexes:
                try:
                    index_name = f"idx_{table_name}_{column}"
                    cursor.execute(f"CREATE INDEX {index_name} ON {table_name} ({column})")
                    self.stdout.write(f"Created index: {index_name} ({description})")
                except Exception as e:
                    # Index might already exist, continue
                    if "already exists" not in str(e):
                        self.stdout.write(self.style.WARNING(f"Error creating index {index_name}: {e!s}"))

    def _generate_summary(self):
        """Generate summary statistics for loaded data."""
        self.stdout.write("\n=== LEGACY DATA SUMMARY ===")

        tables = [
            "legacy_students",
            "legacy_terms",
            "legacy_receipt_headers",
            "legacy_academic_classes",
            "legacy_course_takers",
        ]

        with connection.cursor() as cursor:
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    self.stdout.write(f"{table}: {count:,} records")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error getting count for {table}: {e!s}"))

        # Additional analysis for receipt_headers (our main focus)
        try:
            with connection.cursor() as cursor:
                # Date range
                cursor.execute(
                    """
                    SELECT MIN(pmtdate), MAX(pmtdate)
                    FROM legacy_receipt_headers
                    WHERE pmtdate IS NOT NULL
                """
                )
                date_range = cursor.fetchone()
                if date_range[0]:
                    self.stdout.write(f"Receipt date range: {date_range[0]} to {date_range[1]}")

                # Unique students
                cursor.execute("SELECT COUNT(DISTINCT id) FROM legacy_receipt_headers")
                unique_students = cursor.fetchone()[0]
                self.stdout.write(f"Unique students in receipts: {unique_students:,}")

                # Unique terms
                cursor.execute("SELECT COUNT(DISTINCT termid) FROM legacy_receipt_headers WHERE termid IS NOT NULL")
                unique_terms = cursor.fetchone()[0]
                self.stdout.write(f"Unique terms in receipts: {unique_terms:,}")

        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Error generating receipt summary: {e!s}"))

        # CRITICAL ANALYSIS: Reading Class pricing - count students with Attendance='Normal' per CLASSID
        self.stdout.write("\n=== READING CLASS PRICING ANALYSIS ===")
        try:
            with connection.cursor() as cursor:
                # Count of normal attendance students per CLASSID (this determines Reading Class price)
                cursor.execute(
                    """
                    SELECT
                        classid,
                        COUNT(*) as normal_attendance_count,
                        COUNT(DISTINCT id) as unique_students,
                        normalizedsection,
                        normalizedcourse
                    FROM legacy_course_takers
                    WHERE attendance = 'Normal'
                        AND classid IS NOT NULL
                        AND classid != ''
                    GROUP BY classid, normalizedsection, normalizedcourse
                    ORDER BY normal_attendance_count DESC
                    LIMIT 20
                """
                )

                classes = cursor.fetchall()
                if classes:
                    self.stdout.write("Top 20 classes by normal attendance count (determines Reading Class pricing):")
                    for classid, count, unique_count, section, course in classes:
                        self.stdout.write(
                            f"  ClassID {classid}: {count:,} normal attendance "
                            f"({unique_count:,} unique students) - {course}/{section}"
                        )

                # Overall statistics
                cursor.execute(
                    """
                    SELECT
                        COUNT(DISTINCT classid) as unique_classes,
                        COUNT(*) as total_normal_attendance,
                        AVG(class_counts.normal_count) as avg_class_size,
                        MIN(class_counts.normal_count) as min_class_size,
                        MAX(class_counts.normal_count) as max_class_size
                    FROM (
                        SELECT
                            classid,
                            COUNT(*) as normal_count
                        FROM legacy_course_takers
                        WHERE attendance = 'Normal'
                            AND classid IS NOT NULL
                            AND classid != ''
                        GROUP BY classid
                    ) class_counts
                """
                )

                overall_stats = cursor.fetchone()
                if overall_stats:
                    unique_classes, total, avg_size, min_size, max_size = overall_stats
                    self.stdout.write(
                        f"Overall: {unique_classes:,} unique classes with {total:,} normal attendance records"
                    )
                    self.stdout.write(f"Class size range: {min_size} - {max_size} normal attendance students")
                    self.stdout.write(f"Average class size: {avg_size:.1f} normal attendance students")

                # Distribution analysis for Reading Class pricing tiers
                cursor.execute(
                    """
                    SELECT
                        CASE
                            WHEN normal_count <= 10 THEN '1-10 students'
                            WHEN normal_count <= 15 THEN '11-15 students'
                            WHEN normal_count <= 20 THEN '16-20 students'
                            WHEN normal_count <= 25 THEN '21-25 students'
                            ELSE '25+ students'
                        END as size_category,
                        COUNT(*) as class_count
                    FROM (
                        SELECT
                            classid,
                            COUNT(*) as normal_count
                        FROM legacy_course_takers
                        WHERE attendance = 'Normal'
                            AND classid IS NOT NULL
                            AND classid != ''
                        GROUP BY classid
                    ) class_counts
                    GROUP BY size_category
                    ORDER BY MIN(normal_count)
                """
                )

                distribution = cursor.fetchall()
                if distribution:
                    self.stdout.write("Class size distribution (for Reading Class pricing tiers):")
                    for category, count in distribution:
                        self.stdout.write(f"  {category}: {count:,} classes")

        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Error generating Reading Class pricing analysis: {e!s}"))
