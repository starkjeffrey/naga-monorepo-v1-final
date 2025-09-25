#!/usr/bin/env python3
"""
Simple Load and Explode Script for 2025 Academic Course Takers
Direct approach - no Django, just raw data analysis to see what explodes
"""

import csv
import sqlite3
from pathlib import Path


def load_and_explode_2025():
    """Load 2025 data into SQLite and see what blows up"""

    csv_path = Path(
        "/Volumes/Projects/naga-monorepo-v1-final/backend/data/recent_terms/recent_academiccoursetakers.csv"
    )
    db_path = Path("/Volumes/Projects/naga-monorepo-v1-final/backend/explosion_test.db")

    print("🚀 LOAD AND EXPLODE: 2025 Academic Course Takers")
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

    # Create simple table - everything as TEXT
    cursor.execute("""
        CREATE TABLE explosion_test (
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

    # Load CSV data
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

                # Insert record
                cursor.execute(
                    """
                    INSERT INTO explosion_test VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    values,
                )

                success_count += 1

            except Exception as e:
                explosion_count += 1
                explosions.append({"row": row_num, "error": str(e), "data": dict(row)})

                if explosion_count <= 5:  # Show first 5 explosions
                    print(f"💥 Row {row_num} EXPLODED: {e}")
                    print(f"   Data: {row}")

    conn.commit()

    # Report results
    print("\n🎯 EXPLOSION RESULTS:")
    print(f"   ✅ Successfully loaded: {success_count:,} records")
    print(f"   💥 Explosions: {explosion_count}")

    if explosions:
        print("\n🔬 EXPLOSION ANALYSIS:")

        # Analyze explosion patterns
        error_types = {}
        for exp in explosions:
            error_msg = exp["error"].lower()
            if "unique constraint" in error_msg:
                error_types.setdefault("duplicate_keys", []).append(exp)
            elif "null" in error_msg:
                error_types.setdefault("null_violations", []).append(exp)
            else:
                error_types.setdefault("other_errors", []).append(exp)

        for error_type, error_list in error_types.items():
            print(f"\n💥 {error_type.replace('_', ' ').title()}: {len(error_list)} occurrences")
            if error_list:
                sample = error_list[0]
                print(f"   Example: Row {sample['row']} - {sample['error']}")
                print(f"   Sample Data: ID={sample['data'].get('ID')}, IPK={sample['data'].get('IPK')}")

    # Analyze loaded data
    print("\n📊 DATA ANALYSIS:")

    # Count records
    cursor.execute("SELECT COUNT(*) FROM explosion_test")
    total_count = cursor.fetchone()[0]
    print(f"   Total loaded records: {total_count:,}")

    # Analyze grades
    cursor.execute(
        "SELECT grade, COUNT(*) as count FROM explosion_test WHERE grade IS NOT NULL GROUP BY grade ORDER BY count DESC LIMIT 10"
    )
    grades = cursor.fetchall()
    print("\n📈 TOP GRADES:")
    for grade, count in grades:
        print(f"   {grade.strip() if grade else 'NULL'}: {count:,}")

    # Analyze attendance
    cursor.execute(
        "SELECT attendance, COUNT(*) as count FROM explosion_test WHERE attendance IS NOT NULL GROUP BY attendance ORDER BY count DESC"
    )
    attendance = cursor.fetchall()
    print("\n🎓 ATTENDANCE TYPES:")
    for att, count in attendance:
        print(f"   {att.strip() if att else 'NULL'}: {count:,}")

    # Analyze terms from ClassID
    cursor.execute("""
        SELECT SUBSTR(class_id, 1, 6) as term_prefix, COUNT(*) as count
        FROM explosion_test
        WHERE class_id IS NOT NULL
        GROUP BY term_prefix
        ORDER BY count DESC
        LIMIT 10
    """)
    terms = cursor.fetchall()
    print("\n📅 TERM PREFIXES:")
    for term, count in terms:
        print(f"   {term}: {count:,}")

    # Sample data
    cursor.execute("SELECT id, class_id, grade, attendance FROM explosion_test LIMIT 5")
    samples = cursor.fetchall()
    print("\n📋 SAMPLE RECORDS:")
    for sample in samples:
        print(f"   ID: {sample[0]}, Class: {sample[1][:30]}..., Grade: {sample[2]}, Attendance: {sample[3]}")

    conn.close()

    print("\n🎉 Load and Explode Complete!")
    print(f"💾 Results saved to: {db_path}")
    print(f"🔍 Use SQLite to explore: sqlite3 {db_path}")


if __name__ == "__main__":
    load_and_explode_2025()
