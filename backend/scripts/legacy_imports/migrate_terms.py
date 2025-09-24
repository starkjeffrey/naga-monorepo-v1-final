#!/usr/bin/env python3
"""Migrate legacy terms to MIGRATION database.
Run with: DJANGO_SETTINGS_MODULE=config.settings.migration python scripts/legacy_imports/migrate_terms.py
"""

import os
import sys
from datetime import datetime
from pathlib import Path

import django

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.migration")
django.setup()

from django.core.exceptions import ValidationError
from django.db import connection, transaction

from apps.curriculum.models import Term


def parse_date(date_str: str) -> datetime.date:
    """Parse legacy date format to Python date."""
    if not date_str or date_str == "NULL":
        return None

    try:
        # Handle format: '2025-12-15 00:00:00.000'
        if " " in date_str:
            date_str = date_str.split(" ")[0]
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def normalize_term_type(legacy_type: str) -> str:
    """Normalize legacy term types to match current model choices."""
    if not legacy_type or legacy_type == "NULL":
        return "BA"  # Default to BA

    legacy_type = legacy_type.upper().strip()

    # Map legacy types to current choices
    type_mapping = {
        "BA": "BA",
        "MA": "MA",
        "ENG A": "ENG_A",
        "ENG B": "ENG_B",
        "X": "SPECIAL",  # X means special/inactive terms
    }

    return type_mapping.get(legacy_type, "BA")  # Default to BA


def extract_cohort_numbers(term_id: str, term_type: str) -> tuple[int, int]:
    """Extract BA and MA cohort numbers from term ID pattern."""
    ba_cohort = 0
    ma_cohort = 0

    if not term_id or term_id == "NULL":
        return ba_cohort, ma_cohort

    # Parse patterns like "251215B-T4", "251122M-T4", etc.
    try:
        # Extract year part (first 2 digits = year, next 4 = date info)
        if len(term_id) >= 6:
            year_part = term_id[:2]  # e.g., "25" for 2025
            year = 2000 + int(year_part)

            # Extract term number from the end (e.g., "T4" -> 4)
            if "T" in term_id:
                term_part = term_id.split("T")[-1]
                term_num = int("".join(filter(str.isdigit, term_part)))

                # Calculate cohort based on year and term
                base_cohort = (year - 2009) * 4 + term_num  # Assuming 2009 as base year

                if "B" in term_id:  # Bachelor's term
                    ba_cohort = base_cohort
                elif "M" in term_id:  # Master's term
                    ma_cohort = base_cohort
                elif term_type in ["ENG A", "ENG B"]:  # English terms
                    ba_cohort = base_cohort  # English programs count as BA

    except (ValueError, IndexError):
        pass  # Keep defaults of 0

    return ba_cohort, ma_cohort


def migrate_terms():
    """Migrate all legacy terms to the current Term model."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT "TermID", "TermName", "StartDate", "EndDate", "TermType",
                   "Desp", "AddDate", "DropDate", "PmtPeriod", "LDPDate"
            FROM legacy_terms
            ORDER BY "StartDate", "TermID"
        """
        )

        legacy_terms = cursor.fetchall()

    migrated_count = 0
    skipped_count = 0
    error_count = 0

    with transaction.atomic():
        # Clear existing terms first
        existing_count = Term.objects.count()
        if existing_count > 0:
            Term.objects.all().delete()

        for legacy_term in legacy_terms:
            try:
                (
                    term_id,
                    term_name,
                    start_date,
                    end_date,
                    term_type,
                    description,
                    add_date,
                    drop_date,
                    pmt_period,
                    ldp_date,
                ) = legacy_term

                # Parse dates
                start_date_parsed = parse_date(start_date)
                end_date_parsed = parse_date(end_date)
                add_date_parsed = parse_date(add_date)
                drop_date_parsed = parse_date(drop_date)
                ldp_date_parsed = parse_date(ldp_date)  # Last Day to Pay

                # Skip terms without essential dates
                if not start_date_parsed or not end_date_parsed:
                    skipped_count += 1
                    continue

                # Normalize data
                normalized_type = normalize_term_type(term_type)
                ba_cohort, ma_cohort = extract_cohort_numbers(term_id, term_type)

                # Ensure add_date is not before start_date
                safe_add_date = add_date_parsed
                if safe_add_date and start_date_parsed and safe_add_date < start_date_parsed:
                    safe_add_date = start_date_parsed

                # Ensure drop_date is not before start_date
                safe_drop_date = drop_date_parsed
                if safe_drop_date and start_date_parsed and safe_drop_date < start_date_parsed:
                    safe_drop_date = start_date_parsed

                # Create Term instance
                term = Term(
                    code=term_id if term_id and term_id != "NULL" else term_name[:200],
                    description=(
                        term_name
                        if term_name and term_name != "NULL"
                        else (description if description and description != "NULL" else "")
                    ),
                    term_type=normalized_type,
                    ba_cohort_number=ba_cohort,
                    ma_cohort_number=ma_cohort,
                    start_date=start_date_parsed,
                    end_date=end_date_parsed,
                    add_date=safe_add_date or start_date_parsed,
                    drop_date=safe_drop_date or start_date_parsed,
                    payment_deadline_date=ldp_date_parsed or start_date_parsed,
                    discount_end_date=start_date_parsed,  # Default to start date
                    is_active=normalized_type != "SPECIAL",
                )

                # Validate and save
                term.full_clean()
                term.save()

                migrated_count += 1

            except ValidationError:
                error_count += 1
            except Exception:
                error_count += 1

    # Verify results
    Term.objects.count()

    # Show term type distribution
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT term_type, COUNT(*), MIN(start_date), MAX(start_date)
            FROM curriculum_term
            GROUP BY term_type
            ORDER BY term_type
        """
        )
        for _row in cursor.fetchall():
            pass

    return migrated_count


if __name__ == "__main__":
    migrate_terms()
