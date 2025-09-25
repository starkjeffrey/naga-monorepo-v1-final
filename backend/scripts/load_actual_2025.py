#!/usr/bin/env python3
"""Load ACTUAL 2025 data with 250106 term codes"""

import csv
import sqlite3
from pathlib import Path


def load_actual_2025():
    """Load the real 2025 data and see what blows up"""

    csv_path = Path(
        "/Volumes/Projects/naga-monorepo-v1-final/backend/data/legacy/data_pipeline/inputs/academiccoursetakers_2025_subset.csv"
    )
    db_path = Path("/Volumes/Projects/naga-monorepo-v1-final/backend/actual_2025_explosion_test.db")

    print("🚀 LOAD ACTUAL 2025: Academic Course Takers")
    print(f"📂 CSV: {csv_path}")
    print(f"💾 SQLite DB: {db_path}")

    if not csv_path.exists():
        print(f"❌ CSV file not found: {csv_path}")
        return

    # Remove old DB
    if db_path.exists():
        db_path.unlink()

    # Connect to SQLite
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create table
    cursor.execute("""
        CREATE TABLE actual_2025_test (
            id TEXT,
            class_id TEXT,
            credit TEXT,
            grade_point TEXT,
            total_point TEXT,
            grade TEXT,
            passed TEXT,
            remarks TEXT,
            attendance TEXT,
            add_time TEXT,
            last_update TEXT,
            ipk TEXT PRIMARY KEY,
            created_date TEXT,
            modified_date TEXT
        )
    """)

    print("✅ Created SQLite table")

    # Load data
    explosion_count = 0
    success_count = 0
    explosions = []

    with csv_path.open() as f:
        reader = csv.DictReader(f)

        for row_num, row in enumerate(reader, 1):
            try:
                # Clean values
                values = []
                for field in [
                    "ID",
                    "ClassID",
                    "Credit",
                    "GradePoint",
                    "TotalPoint",
                    "Grade",
                    "Passed",
                    "Remarks",
                    "Attendance",
                    "AddTime",
                    "LastUpdate",
                    "IPK",
                    "CreatedDate",
                    "ModifiedDate",
                ]:
                    value = row.get(field, "")
                    if value in ("NULL", ""):
                        values.append(None)
                    else:
                        values.append(str(value).strip())

                cursor.execute(
                    """
                    INSERT INTO actual_2025_test VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    values,
                )

                success_count += 1

            except Exception as e:
                explosion_count += 1
                explosions.append({"row": row_num, "error": str(e), "data": dict(row)})

                if explosion_count <= 5:
                    print(f"💥 Row {row_num} EXPLODED: {e}")

    conn.commit()

    print("\n🎯 ACTUAL 2025 RESULTS:")
    print(f"   ✅ Successfully loaded: {success_count:,} records")
    print(f"   💥 Explosions: {explosion_count}")

    # Analyze the data
    print("\n📊 2025 DATA ANALYSIS:")

    cursor.execute("SELECT COUNT(*) FROM actual_2025_test")
    total_count = cursor.fetchone()[0]
    print(f"   Total records: {total_count:,}")

    # Term analysis
    cursor.execute("""
        SELECT SUBSTR(class_id, 1, 6) as term_prefix, COUNT(*) as count
        FROM actual_2025_test
        WHERE class_id IS NOT NULL
        GROUP BY term_prefix
        ORDER BY count DESC
    """)
    terms = cursor.fetchall()
    print("\n📅 2025 TERM CODES:")
    for term, count in terms:
        print(f"   {term}: {count:,}")

    # Grade distribution
    cursor.execute(
        "SELECT grade, COUNT(*) FROM actual_2025_test WHERE grade IS NOT NULL GROUP BY grade ORDER BY COUNT(*) DESC LIMIT 10"
    )
    grades = cursor.fetchall()
    print("\n📈 GRADE DISTRIBUTION:")
    for grade, count in grades:
        print(f"   {grade.strip() if grade else 'NULL'}: {count:,}")

    # Attendance analysis
    cursor.execute(
        "SELECT attendance, COUNT(*) FROM actual_2025_test WHERE attendance IS NOT NULL GROUP BY attendance ORDER BY COUNT(*) DESC"
    )
    attendance = cursor.fetchall()
    print("\n🎓 ATTENDANCE PATTERNS:")
    for att, count in attendance:
        print(f"   {att.strip() if att else 'NULL'}: {count:,}")

    # Course analysis from ClassID
    cursor.execute("""
        SELECT SUBSTR(class_id, INSTR(class_id, '!$') + 2) as course_part, COUNT(*) as count
        FROM actual_2025_test
        WHERE class_id LIKE '%!$%'
        GROUP BY course_part
        ORDER BY count DESC
        LIMIT 10
    """)
    courses = cursor.fetchall()
    print("\n📚 TOP COURSE PATTERNS:")
    for course, count in courses:
        if course:
            print(f"   {course[:50]}{'...' if len(course) > 50 else ''}: {count:,}")

    # Program type detection
    cursor.execute("""
        SELECT
            CASE
                WHEN class_id LIKE '%EHSS%' OR class_id LIKE '%IEAP%' OR class_id LIKE '%PRE-%' THEN 'Language'
                WHEN class_id LIKE '%BA%' THEN 'BA Program'
                WHEN class_id LIKE '%MA%' THEN 'MA Program'
                ELSE 'Other'
            END as program_type,
            COUNT(*) as count
        FROM actual_2025_test
        GROUP BY program_type
        ORDER BY count DESC
    """)
    programs = cursor.fetchall()
    print("\n🎓 PROGRAM TYPE DISTRIBUTION:")
    for prog, count in programs:
        print(f"   {prog}: {count:,}")

    conn.close()

    print("\n🎉 ACTUAL 2025 Load Complete!")
    print(f"💾 Results saved to: {db_path}")


if __name__ == "__main__":
    load_actual_2025()
