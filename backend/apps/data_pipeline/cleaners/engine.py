"""
Data Cleaning Engine

Implements Stage 3 cleaning rules and transformations.
Applies standardization, encoding fixes, date parsing, and format normalization.
"""

import json
import logging
import re
from collections.abc import Callable
from typing import Any

from django.db import connection

from apps.people.utils.name_parser import parse_student_name


class CleaningEngine:
    """Main engine for applying cleaning rules to data"""

    def __init__(self, config_rules: dict[str, Any]):
        self.config_rules = config_rules
        self.logger = logging.getLogger(__name__)
        # Context for per-row parsing results (e.g., name parsing metadata)
        self._current_row_context: dict[str, Any] = {}

        # Register built-in cleaning functions
        self.cleaning_functions = {
            "trim": self._trim,
            "null_standardize": self._null_standardize,
            "uppercase": self._uppercase,
            "lowercase": self._lowercase,
            "title_case": self._title_case,
            "fix_encoding": self._fix_encoding,
            "fix_khmer_encoding": self._fix_khmer_encoding,
            "parse_mssql_datetime": self._parse_mssql_datetime,
            "parse_float": self._parse_float,
            "parse_int": self._parse_int,
            "parse_boolean": self._parse_boolean,
            "parse_decimal": self._parse_decimal,
            "standardize_phone": self._standardize_phone,
            "normalize_phone": self._standardize_phone,  # Alias for compatibility
            "standardize_gender": self._standardize_gender,
            "normalize_gender": self._standardize_gender,  # Alias for compatibility
            "standardize_marital": self._standardize_marital_status,
            "validate_email": self._validate_email,
            "pad_zeros": self._pad_zeros,
            "parse_student_name": self._parse_student_name,
            "parse_emergency_contact": self._parse_emergency_contact,
            "normalize_birth_date": self._normalize_birth_date,
            "normalize_class_id": self._normalize_class_id,
        }

    def apply_cleaning_rules(self, column_name: str, value: Any, rules: list[str]) -> Any:
        """Apply a list of cleaning rules to a value"""
        if value is None:
            return None

        # Convert to string for processing
        current_value: str | float | None = str(value) if value is not None else ""

        # Apply each rule in sequence
        for rule in rules:
            if rule in self.cleaning_functions:
                try:
                    current_value = self.cleaning_functions[rule](
                        str(current_value) if current_value is not None else "", column_name
                    )
                except Exception as e:
                    self.logger.warning(
                        f"Cleaning rule '{rule}' failed for column '{column_name}', value '{value}': {e}"
                    )
                    # Continue with original value on error
                    pass
            else:
                self.logger.warning(f"Unknown cleaning rule: {rule}")

        return current_value

    # Built-in cleaning functions

    def _trim(self, value: str, column_name: str | None = None) -> str:
        """Remove leading/trailing whitespace"""
        return value.strip() if value else ""

    def _null_standardize(self, value: str, column_name: str | None = None) -> str | None:
        """Standardize NULL representations to actual NULL"""
        if not value:
            return None

        null_patterns = self.config_rules.get("null_patterns", ["NULL", "NA", "", " "])
        value_cleaned = value.strip().upper()

        if value_cleaned in [p.upper() for p in null_patterns]:
            return None

        return value

    def _uppercase(self, value: str, column_name: str | None = None) -> str:
        """Convert to uppercase"""
        return value.upper() if value else ""

    def _lowercase(self, value: str, column_name: str | None = None) -> str:
        """Convert to lowercase"""
        return value.lower() if value else ""

    def _title_case(self, value: str, column_name: str | None = None) -> str:
        """Convert to title case"""
        return value.title() if value else ""

    def _fix_encoding(self, value: str, column_name: str | None = None) -> str:
        """Fix common encoding issues"""
        if not value:
            return value

        # Common encoding fix mappings
        encoding_fixes = {
            "â€™": "'",  # Smart quote
            "â€œ": '"',  # Smart quote open
            "â€": '"',  # Smart quote close
            'â€"': "-",  # En dash
            "Ã¡": "á",  # Latin-1 to UTF-8 issues
            "Ã©": "é",
            "Ã­": "í",
            "Ã³": "ó",
            "Ãº": "ú",
            "Ã±": "ñ",
        }

        result = value
        for bad, good in encoding_fixes.items():
            result = result.replace(bad, good)

        return result

    def _fix_khmer_encoding(self, value: str, column_name: str | None = None) -> str:
        """Attempt to fix Khmer character encoding issues"""
        if not value:
            return value

        # This is a simplified approach - in practice, you might need more sophisticated
        # Unicode normalization and Khmer-specific encoding fixes
        try:
            # Try to detect and fix common Khmer encoding issues
            # Remove replacement characters
            result = value.replace("\ufffd", "")

            # Basic cleanup of garbled Khmer text
            # In a real implementation, you might use a Khmer text library
            return result.strip()

        except Exception:
            return value

    def _parse_mssql_datetime(self, value: str, column_name: str | None = None) -> str | None:
        """Parse MSSQL datetime format to ISO format"""
        if not value or value.strip().upper() in ["NULL", "NA", ""]:
            return None

        value = value.strip()

        # MSSQL format: "Apr 27 2009 12:00AM"
        mssql_patterns = [
            r"([A-Za-z]{3})\s+(\d{1,2})\s+(\d{4})\s+\d{1,2}:\d{2}[AP]M",  # Apr 27 2009 12:00AM
            r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})",  # MM/DD/YYYY or MM-DD-YYYY
            r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})",  # YYYY-MM-DD or YYYY/MM/DD
        ]

        # Try MSSQL format first
        match = re.match(mssql_patterns[0], value)
        if match:
            month_name, day, year = match.groups()
            month_map = {
                "Jan": "01",
                "Feb": "02",
                "Mar": "03",
                "Apr": "04",
                "May": "05",
                "Jun": "06",
                "Jul": "07",
                "Aug": "08",
                "Sep": "09",
                "Oct": "10",
                "Nov": "11",
                "Dec": "12",
            }
            month = month_map.get(month_name, "01")
            return f"{year}-{month}-{day.zfill(2)}"

        # Try other common formats
        try:
            # Use dateutil parser as fallback
            from dateutil import parser

            parsed_date = parser.parse(value, fuzzy=True)
            return parsed_date.strftime("%Y-%m-%d")
        except Exception:
            # If all else fails, return original value
            return value

    def _parse_float(self, value: str, column_name: str | None = None) -> float | None:
        """Parse string to float"""
        if not value or value.strip().upper() in ["NULL", "NA", ""]:
            return None

        try:
            # Remove common formatting
            cleaned = value.strip().replace(",", "").replace("$", "")
            return float(cleaned)
        except (ValueError, TypeError):
            return None

    def _parse_int(self, value: str, column_name: str | None = None) -> int | None:
        """Parse string to integer"""
        if not value or value.strip().upper() in ["NULL", "NA", ""]:
            return None

        try:
            # Remove common formatting
            cleaned = value.strip().replace(",", "").replace("$", "")
            return int(float(cleaned))  # Handle "123.0" cases
        except (ValueError, TypeError):
            return None

    def _standardize_phone(self, value: str, column_name: str | None = None) -> str:
        """Standardize phone number format"""
        if not value:
            return value

        # Remove all non-digits
        digits = re.sub(r"\D", "", value)

        # Cambodian phone numbers
        if digits.startswith("855"):  # Country code
            return f"+{digits}"
        elif digits.startswith("0") and len(digits) >= 9:  # Local format
            return f"+855{digits[1:]}"
        elif len(digits) >= 8:  # Without leading zero
            return f"+855{digits}"

        return value  # Return original if can't standardize

    def _standardize_gender(self, value: str, column_name: str | None = None) -> str:
        """Standardize gender values"""
        if not value:
            return value

        value_clean = value.strip().upper()

        gender_mappings = {
            "M": "Male",
            "MALE": "Male",
            "F": "Female",
            "FEMALE": "Female",
        }

        return gender_mappings.get(value_clean, value)

    def _standardize_marital_status(self, value: str, column_name: str | None = None) -> str:
        """Standardize marital status values"""
        if not value:
            return value

        value_clean = value.strip().title()

        marital_mappings = {
            "Single": "Single",
            "Married": "Married",
            "Divorced": "Divorced",
            "Widowed": "Widowed",
        }

        return marital_mappings.get(value_clean, value)

    def _validate_email(self, value: str, column_name: str | None = None) -> str:
        """Enhanced email validation and cleanup with common fixes"""
        if not value or not value.strip():
            return value

        # Initial cleanup
        email = value.strip().lower()

        # Fix common typos and issues
        fixes = {
            # Common domain typos
            "@gmai.com": "@gmail.com",
            "@gmail.co": "@gmail.com",
            "@yahooo.com": "@yahoo.com",
            "@hotmial.com": "@hotmail.com",
            "@outlookm.com": "@outlook.com",
            # Double @ symbols
            "@@": "@",
            # Spaces in email (sometimes from data entry errors)
            " @": "@",
            "@ ": "@",
        }

        for bad, good in fixes.items():
            email = email.replace(bad, good)

        # Remove extra whitespace that might have been introduced
        email = email.strip()

        # Enhanced email regex with better validation
        # Allows international domains, common special characters
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

        # Additional validation checks
        if re.match(email_pattern, email):
            # Check for some obvious invalid patterns
            invalid_patterns = [
                r"\.{2,}",  # Multiple consecutive dots
                r"^[.-]",  # Starting with dot or dash
                r"[.-]@",  # Dot or dash immediately before @
                r"@[.-]",  # Dot or dash immediately after @
                r"[.-]$",  # Ending with dot or dash
            ]

            if not any(re.search(pattern, email) for pattern in invalid_patterns):
                # Basic length check (most email providers have limits)
                if len(email) <= 254 and "@" in email:
                    local, domain = email.split("@", 1)
                    if len(local) <= 64 and len(domain) <= 253:
                        return email

        # Log invalid emails for review (but return original for downstream validation)
        if email != value.strip().lower():
            self.logger.warning(f"Email cleaning attempted for {column_name}: '{value}' -> '{email}' (still invalid)")
        else:
            self.logger.warning(f"Invalid email format in {column_name}: '{value}'")

        # Return original value so validation stage can handle it appropriately
        return value

    def _pad_zeros(self, value: str, column_name: str | None = None) -> str:
        """Pad numeric strings with leading zeros"""
        if not value or not value.strip():
            return value

        value = value.strip()

        # Only pad if it's all digits
        if value.isdigit():
            # Determine target length based on column name or use default
            target_length = 5  # Default

            if column_name and "id" in column_name.lower():
                target_length = 10  # Student IDs are typically 10 digits

            return value.zfill(target_length)

        return value

    def _parse_boolean(self, value: str, column_name: str | None = None) -> str:
        """Convert various boolean representations to 1/0"""
        if not value or value.strip() == "":
            return ""

        value = value.strip().lower()

        # Map various boolean representations
        true_values = ["true", "1", "yes", "y", "t", "on", "enabled"]
        false_values = ["false", "0", "no", "n", "f", "off", "disabled"]

        if value in true_values:
            return "1"
        elif value in false_values:
            return "0"
        else:
            return value  # Return original if not recognized

    def _parse_decimal(self, value: str, column_name: str | None = None) -> str:
        """Parse decimal values, handling currency symbols and formatting"""
        if not value or value.strip() == "":
            return ""

        # Remove currency symbols and formatting
        cleaned = value.strip().replace("$", "").replace(",", "").replace(" ", "")

        try:
            # Try to parse as float first
            float_val = float(cleaned)
            return str(float_val)
        except (ValueError, TypeError):
            # Return original if can't parse
            return value

    def _parse_student_name(self, value: str, column_name: str | None = None) -> str:
        """Parse legacy student names with embedded status indicators"""
        if not value or not value.strip():
            return value

        try:
            # Use the name parser to extract clean name and status
            parsed_result = parse_student_name(value)

            # Store parsed data in a way the cleaning engine can track
            # The main name field gets the clean name
            if hasattr(self, "_current_row_context"):
                # Store status indicators for later processing
                self._current_row_context["_name_parse_result"] = {
                    "is_sponsored": parsed_result.is_sponsored,
                    "sponsor_name": parsed_result.sponsor_name,
                    "is_frozen": parsed_result.is_frozen,
                    "has_admin_fees": parsed_result.has_admin_fees,
                    "raw_indicators": parsed_result.raw_indicators,
                    "parsing_warnings": parsed_result.parsing_warnings,
                }

            # Return the clean name
            return parsed_result.clean_name

        except Exception as e:
            self.logger.warning(f"Name parsing failed for {column_name}: '{value}' - {e}")
            # Fall back to basic trim if parsing fails
            return value.strip()

    def _parse_emergency_contact(self, value: str, column_name: str | None = None) -> str:
        """Parse and normalize emergency contact information"""
        if not value or not value.strip():
            return value

        try:
            # Clean up common formatting issues in emergency contact data
            cleaned = value.strip()

            # Remove excessive whitespace
            cleaned = " ".join(cleaned.split())

            # Handle common legacy formatting issues
            # Remove parentheses around entire name
            if cleaned.startswith("(") and cleaned.endswith(")"):
                cleaned = cleaned[1:-1].strip()

            # Standardize relationship indicators
            relationship_mappings = {
                "father": "Father",
                "mother": "Mother",
                "parent": "Parent",
                "spouse": "Spouse",
                "wife": "Spouse",
                "husband": "Spouse",
                "brother": "Brother",
                "sister": "Sister",
                "son": "Son",
                "daughter": "Daughter",
                "friend": "Friend",
                "relative": "Relative",
            }

            # If this is a relationship field, normalize it
            if column_name and "relationship" in column_name.lower():
                cleaned_lower = cleaned.lower()
                for key, standardized in relationship_mappings.items():
                    if key in cleaned_lower:
                        return standardized

            # Title case for names
            if column_name and "name" in column_name.lower():
                # Split on spaces and title case each part
                name_parts = cleaned.split()
                cleaned = " ".join(part.title() for part in name_parts)

            return cleaned

        except Exception as e:
            self.logger.warning(f"Emergency contact parsing failed for {column_name}: '{value}' - {e}")
            return value.strip()

    def _normalize_birth_date(self, value: str, column_name: str | None = None) -> str:
        """Normalize birth date with additional validation"""
        if not value or not value.strip():
            return value

        try:
            # First apply the standard MSSQL datetime parsing
            parsed_date = self._parse_mssql_datetime(value, column_name)

            if parsed_date and parsed_date != value:
                # Additional validation for birth dates
                from datetime import datetime

                try:
                    # Parse the ISO formatted date for validation
                    birth_dt = datetime.fromisoformat(parsed_date)
                    current_dt = datetime.now()

                    # Calculate age
                    age_years = (current_dt - birth_dt).days / 365.25

                    # Reasonable age range for students (5-120 years)
                    if age_years < 5:
                        self.logger.warning(
                            f"Birth date {parsed_date} indicates very young age ({age_years:.1f} years)"
                        )
                    elif age_years > 120:
                        self.logger.warning(f"Birth date {parsed_date} indicates very old age ({age_years:.1f} years)")
                    elif age_years < 15 or age_years > 65:
                        # Unusual but not invalid for higher education
                        self.logger.info(
                            f"Birth date {parsed_date} indicates unusual student age ({age_years:.1f} years)"
                        )

                    return parsed_date

                except (ValueError, TypeError):
                    # If ISO parsing fails, return the original parsed result
                    return parsed_date

            return parsed_date

        except Exception as e:
            self.logger.warning(f"Birth date normalization failed for {column_name}: '{value}' - {e}")
            return value

    def _normalize_class_id(self, value: str, column_name: str | None = None) -> str:
        """Normalize class ID format for cross-table consistency"""
        if not value or not value.strip():
            return value

        try:
            # Clean up class ID format
            cleaned = value.strip().upper()

            # Remove excessive whitespace
            cleaned = " ".join(cleaned.split())

            # Standardize separators - use dash as standard separator
            # Replace various separators with dash
            separators = [" - ", " _ ", "_", " / ", "/", ".", " "]
            for sep in separators:
                if sep in cleaned and sep != "-":
                    cleaned = cleaned.replace(sep, "-")

            # Remove multiple consecutive dashes
            while "--" in cleaned:
                cleaned = cleaned.replace("--", "-")

            # Remove leading/trailing dashes
            cleaned = cleaned.strip("-")

            # Validate basic class ID pattern
            # Expected format: COURSECODE-SECTION-TERMID
            # Examples: ENG101-001-2009T1, MATH200-A-2009T2
            parts = cleaned.split("-")

            if len(parts) >= 2:
                # Basic validation of parts
                course_part = parts[0]
                section_part = parts[1]

                # Course code should be alphanumeric (letters + numbers)
                if re.match(r"^[A-Z]{2,8}[0-9]{2,4}[A-Z]?$", course_part):
                    # Valid course code format
                    pass
                elif re.match(r"^[A-Z]+[0-9]*$", course_part):
                    # Less strict - just letters optionally followed by numbers
                    pass
                else:
                    self.logger.info(f"Unusual course code format in class ID: {course_part}")

                # Section should be short alphanumeric
                if len(section_part) > 10:
                    self.logger.warning(f"Unusually long section in class ID: {section_part}")

                # Term validation (if present)
                if len(parts) >= 3:
                    term_part = parts[2]
                    # Basic term validation (e.g., 2009T1, 2009T2, FALL2009)
                    if not (
                        re.match(r"^\d{4}T[1-4]$", term_part)
                        or re.match(r"^(FALL|SPRING|SUMMER)\d{4}$", term_part)
                        or re.match(r"^\d{4}(FALL|SPRING|SUMMER)$", term_part)
                    ):
                        self.logger.info(f"Non-standard term format in class ID: {term_part}")

            return cleaned

        except Exception as e:
            self.logger.warning(f"Class ID normalization failed for {column_name}: '{value}' - {e}")
            return value.strip().upper()

    def add_custom_rule(self, name: str, function: Callable) -> None:
        """Add a custom cleaning rule function"""
        self.cleaning_functions[name] = function

    def get_available_rules(self) -> list[str]:
        """Get list of available cleaning rule names"""
        return list(self.cleaning_functions.keys())


class Stage3DataCleaner:
    """Stage 3: Apply cleaning rules to create cleaned tables"""

    def __init__(self, config, logger, run_id: int):
        self.config = config
        self.logger = logger
        self.run_id = run_id
        self.cleaning_engine = CleaningEngine(config.cleaning_rules)

    def execute(self, stage2_result: dict[str, Any], dry_run: bool = False) -> dict[str, Any]:
        """Execute Stage 3: Clean raw data based on profiling and configuration"""
        import time

        start_time = time.time()

        try:
            self.logger.info("Starting Stage 3 - Data Cleaning")

            # Create cleaned table schema
            if not dry_run:
                self._create_cleaned_table()

            # Process data in chunks for memory efficiency
            chunk_size = self.config.chunk_size
            total_processed = 0
            total_cleaned = 0
            cleaning_stats = {}

            with connection.cursor() as cursor:
                # Get total row count
                cursor.execute(f'SELECT COUNT(*) FROM "{self.config.raw_table_name}"')
                total_rows = cursor.fetchone()[0]

                # Process in chunks
                offset = 0
                while offset < total_rows:
                    chunk_result = self._process_chunk(cursor, offset, chunk_size, dry_run)

                    total_processed += chunk_result["rows_processed"]
                    total_cleaned += chunk_result["rows_cleaned"]

                    # Merge cleaning stats
                    for col, stats in chunk_result["cleaning_stats"].items():
                        if col not in cleaning_stats:
                            cleaning_stats[col] = {"null_conversions": 0, "encoding_fixes": 0, "format_changes": 0}

                        for stat_type, count in stats.items():
                            cleaning_stats[col][stat_type] += count

                    offset += chunk_size

                    if offset % (chunk_size * 10) == 0:  # Log progress every 10 chunks
                        self.logger.info(f"Processed {offset}/{total_rows} rows")

            execution_time = time.time() - start_time

            result = {
                "total_rows_processed": total_processed,
                "total_rows_cleaned": total_cleaned,
                "cleaning_stats": cleaning_stats,
                "execution_time_seconds": execution_time,
                "quality_improvements": self._calculate_quality_improvements(cleaning_stats),
            }

            self.logger.info(
                f"Stage 3 completed in {execution_time:.2f}s - {total_cleaned}/{total_processed} rows cleaned"
            )
            return result

        except Exception as e:
            self.logger.error(f"Stage 3 failed: {e!s}")
            raise

    def _create_cleaned_table(self):
        """Create cleaned table with proper data types"""
        with connection.cursor() as cursor:
            # Drop existing table
            cursor.execute(f'DROP TABLE IF EXISTS "{self.config.cleaned_table_name}" CASCADE;')

            # Create column definitions based on mappings
            column_defs = ["id SERIAL PRIMARY KEY"]

            # Add cleaned columns with appropriate types
            for mapping in self.config.column_mappings:
                target_name = mapping.target_name
                sql_type = self._map_to_postgres_type(mapping.data_type)
                nullable = "NULL" if mapping.nullable else "NOT NULL"

                column_defs.append(f'"{target_name}" {sql_type} {nullable}')

            # Add metadata columns
            metadata_columns = [
                '"_original_row_id" INTEGER',
                '"_cleaning_applied" JSONB',
                '"_quality_score" NUMERIC(5,2)',
                '"_processed_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                # Name parsing metadata columns
                '"_is_sponsored" BOOLEAN',
                '"_sponsor_name" VARCHAR(100)',
                '"_is_frozen" BOOLEAN',
                '"_has_admin_fees" BOOLEAN',
                '"_name_raw_indicators" TEXT',
                '"_name_parsing_warnings" TEXT',
            ]
            column_defs.extend(metadata_columns)

            create_sql = f'''
                CREATE TABLE "{self.config.cleaned_table_name}" (
                    {", ".join(column_defs)}
                );

                -- Add indexes for performance
                CREATE INDEX IF NOT EXISTS "idx_{self.config.cleaned_table_name}_original_row"
                ON "{self.config.cleaned_table_name}" ("_original_row_id");
            '''

            cursor.execute(create_sql)
            self.logger.info(f"Created cleaned table: {self.config.cleaned_table_name}")

    def _map_to_postgres_type(self, mssql_type: str) -> str:
        """Map MSSQL data types to PostgreSQL types"""
        type_mapping = {
            "nvarchar": "VARCHAR",
            "varchar": "VARCHAR",
            "char": "CHAR",
            "text": "TEXT",
            "int": "INTEGER",
            "float": "NUMERIC",
            "datetime": "TIMESTAMP",
            "bit": "BOOLEAN",
        }

        # Extract base type (e.g., 'nvarchar(100)' -> 'nvarchar')
        base_type = mssql_type.split("(")[0].lower()

        if base_type in type_mapping:
            postgres_type = type_mapping[base_type]

            # Preserve length specifications for VARCHAR/CHAR
            if "(" in mssql_type and postgres_type in ["VARCHAR", "CHAR"]:
                length_part = mssql_type[mssql_type.find("(") :]
                return f"{postgres_type}{length_part}"

            return postgres_type

        # Default to TEXT for unknown types
        return "TEXT"

    def _process_chunk(self, cursor, offset: int, chunk_size: int, dry_run: bool) -> dict[str, Any]:
        """Process a chunk of raw data"""
        # Fetch chunk from raw table
        cursor.execute(
            f'''
            SELECT * FROM "{self.config.raw_table_name}"
            ORDER BY "_csv_row_number"
            LIMIT %s OFFSET %s
        ''',
            [chunk_size, offset],
        )

        rows = cursor.fetchall()
        if not rows:
            return {"rows_processed": 0, "rows_cleaned": 0, "cleaning_stats": {}}

        # Get column names
        column_names = [desc[0] for desc in cursor.description]

        cleaned_rows = []
        cleaning_stats = {}

        for row in rows:
            row_dict = dict(zip(column_names, row, strict=False))
            cleaned_row, row_stats = self._clean_row(row_dict)

            if cleaned_row:
                cleaned_rows.append(cleaned_row)

                # Accumulate stats
                for col, stats in row_stats.items():
                    if col not in cleaning_stats:
                        cleaning_stats[col] = {"null_conversions": 0, "encoding_fixes": 0, "format_changes": 0}

                    for stat_type, count in stats.items():
                        cleaning_stats[col][stat_type] += count

        # Insert cleaned rows
        if not dry_run and cleaned_rows:
            self._insert_cleaned_rows(cursor, cleaned_rows)

        return {"rows_processed": len(rows), "rows_cleaned": len(cleaned_rows), "cleaning_stats": cleaning_stats}

    def _clean_row(self, row_dict: dict[str, Any]) -> tuple[dict | None, dict]:
        """Clean a single row of data"""
        cleaned_row = {}
        row_cleaning_stats = {}
        cleaning_applied = {}

        # Set up row context for name parsing
        self.cleaning_engine._current_row_context = {}

        # Process each mapped column
        for mapping in self.config.column_mappings:
            source_name = mapping.source_name
            target_name = mapping.target_name

            if source_name not in row_dict:
                continue  # Skip missing columns

            original_value = row_dict[source_name]

            # Apply cleaning rules
            cleaned_value = self.cleaning_engine.apply_cleaning_rules(
                source_name, original_value, mapping.cleaning_rules
            )

            # Track changes
            stats = {"null_conversions": 0, "encoding_fixes": 0, "format_changes": 0}
            changes = []

            if original_value != cleaned_value:
                if original_value and not cleaned_value:
                    stats["null_conversions"] = 1
                    changes.append("null_standardization")
                elif self._has_encoding_changes(str(original_value), str(cleaned_value)):
                    stats["encoding_fixes"] = 1
                    changes.append("encoding_fix")
                else:
                    stats["format_changes"] = 1
                    changes.append("format_change")

            cleaned_row[target_name] = cleaned_value
            row_cleaning_stats[source_name] = stats

            if changes:
                cleaning_applied[target_name] = changes

        # Handle parsed name results if available
        name_parse_result = getattr(self.cleaning_engine, "_current_row_context", {}).get("_name_parse_result")
        if name_parse_result:
            # Add parsed status fields to the row_dict for processing by column mappings
            virtual_columns = {
                "_is_sponsored": name_parse_result["is_sponsored"],
                "_sponsor_name": name_parse_result["sponsor_name"],
                "_is_frozen": name_parse_result["is_frozen"],
                "_has_admin_fees": name_parse_result["has_admin_fees"],
                "_name_raw_indicators": name_parse_result["raw_indicators"],
                "_name_parsing_warnings": json.dumps(name_parse_result["parsing_warnings"])
                if name_parse_result["parsing_warnings"]
                else None,
            }

            # Process virtual columns through the column mapping system
            for mapping in self.config.column_mappings:
                source_name = mapping.source_name
                target_name = mapping.target_name

                if source_name in virtual_columns:
                    original_value = virtual_columns[source_name]

                    # Apply cleaning rules (though most virtual columns won't need much cleaning)
                    cleaned_value = self.cleaning_engine.apply_cleaning_rules(
                        source_name, original_value, mapping.cleaning_rules
                    )

                    # Track changes (minimal for virtual columns)
                    stats = {"null_conversions": 0, "encoding_fixes": 0, "format_changes": 0}
                    changes = []

                    if original_value != cleaned_value:
                        stats["format_changes"] = 1
                        changes.append("format_change")

                    cleaned_row[target_name] = cleaned_value
                    row_cleaning_stats[source_name] = stats

                    if changes:
                        cleaning_applied[target_name] = changes

        # Add metadata
        cleaned_row["_original_row_id"] = row_dict.get("id")
        cleaned_row["_cleaning_applied"] = json.dumps(cleaning_applied)
        cleaned_row["_quality_score"] = self._calculate_row_quality_score(cleaned_row, row_cleaning_stats)

        return cleaned_row, row_cleaning_stats

    def _has_encoding_changes(self, original: str, cleaned: str) -> bool:
        """Check if cleaning involved encoding fixes"""
        encoding_indicators = ["â€™", "Ã¡", "Ã©", "\ufffd"]
        return any(indicator in original for indicator in encoding_indicators) and original != cleaned

    def _calculate_row_quality_score(self, cleaned_row: dict, stats: dict) -> float:
        """Calculate quality score for a row (0-100)"""
        total_fields = len([v for v in cleaned_row.values() if not str(v).startswith("_")])

        if total_fields == 0:
            return 0.0

        # Count non-null fields
        non_null_fields = len(
            [v for k, v in cleaned_row.items() if not k.startswith("_") and v is not None and str(v).strip()]
        )

        # Base score from completeness
        base_score = (non_null_fields / total_fields) * 100

        # Bonus for successful cleaning
        cleaning_bonus = min(sum(sum(stat.values()) for stat in stats.values()) * 2, 10)

        return min(base_score + cleaning_bonus, 100.0)

    def _insert_cleaned_rows(self, cursor, cleaned_rows: list[dict]):
        """Bulk insert cleaned rows"""
        if not cleaned_rows:
            return

        # Get column names (excluding id which is auto-generated)
        columns = [k for k in cleaned_rows[0].keys() if k != "id"]

        # Prepare insert statement
        placeholders = ", ".join(["%s"] * len(columns))
        column_names = ", ".join([f'"{col}"' for col in columns])

        insert_sql = f'''
            INSERT INTO "{self.config.cleaned_table_name}"
            ({column_names})
            VALUES ({placeholders})
        '''

        # Prepare data tuples
        data_tuples = []
        for row in cleaned_rows:
            tuple_data = tuple(row[col] for col in columns)
            data_tuples.append(tuple_data)

        # Bulk insert
        cursor.executemany(insert_sql, data_tuples)

    def _calculate_quality_improvements(self, cleaning_stats: dict) -> dict[str, Any]:
        """Calculate quality improvement metrics"""
        total_null_conversions = sum(stats.get("null_conversions", 0) for stats in cleaning_stats.values())
        total_encoding_fixes = sum(stats.get("encoding_fixes", 0) for stats in cleaning_stats.values())
        total_format_changes = sum(stats.get("format_changes", 0) for stats in cleaning_stats.values())

        return {
            "null_standardizations": total_null_conversions,
            "encoding_fixes": total_encoding_fixes,
            "format_normalizations": total_format_changes,
            "total_improvements": total_null_conversions + total_encoding_fixes + total_format_changes,
        }
