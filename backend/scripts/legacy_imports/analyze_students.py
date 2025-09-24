#!/usr/bin/env python3
"""Analyze legacy students data structure.
Run with: DJANGO_SETTINGS_MODULE=config.settings.migration python scripts/legacy_imports/analyze_students.py
"""

import os
import sys
from pathlib import Path

import django

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.migration")
django.setup()

from django.db import connection


def analyze_legacy_students():
    """Analyze the legacy students data."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM legacy_students")
        cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT "CurrentProgram", COUNT(*)
            FROM legacy_students
            WHERE "CurrentProgram" IS NOT NULL
            GROUP BY "CurrentProgram"
            ORDER BY COUNT(*) DESC
            LIMIT 10;
        """
        )
        programs = cursor.fetchall()
        for prog in programs:
            if prog[0] and prog[0] != "NULL":
                pass

        cursor.execute(
            """
            SELECT "Gender", COUNT(*)
            FROM legacy_students
            WHERE "Gender" IS NOT NULL
            GROUP BY "Gender";
        """
        )
        genders = cursor.fetchall()
        for gender in genders:
            if gender[0] and gender[0] != "NULL":
                pass

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM legacy_students
            WHERE "Email" IS NOT NULL
                AND "Email" != 'NULL'
                AND "Email" != ''
                AND "Email" LIKE '%@%';
        """
        )
        cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM legacy_students
            WHERE "MobilePhone" IS NOT NULL
                AND "MobilePhone" != 'NULL'
                AND "MobilePhone" != ''
                AND LENGTH("MobilePhone") > 5;
        """
        )
        cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT MIN("AdmissionDate"), MAX("AdmissionDate")
            FROM legacy_students
            WHERE "AdmissionDate" IS NOT NULL
                AND "AdmissionDate" != 'NULL'
                AND "AdmissionDate" != '';
        """
        )
        date_range = cursor.fetchone()
        if date_range[0] and date_range[1]:
            pass

        cursor.execute(
            """
            SELECT "ID", "Name", "KName", "BirthDate", "Gender", "Email",
                   "MobilePhone", "CurrentProgram", "AdmissionDate"
            FROM legacy_students
            WHERE "Name" IS NOT NULL
                AND "Name" != 'NULL'
            LIMIT 5;
        """
        )
        rows = cursor.fetchall()
        for _i, _row in enumerate(rows, 1):
            pass


if __name__ == "__main__":
    analyze_legacy_students()
