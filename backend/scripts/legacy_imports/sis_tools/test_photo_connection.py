#!/usr/bin/env python3
"""
Test script to verify connection to PUCIDCardMaker database and check photo availability
"""

import sys

import pymssql


def test_connection():
    """Test database connection and show photo statistics."""
    print("Testing connection to PUCIDCardMaker database...")
    print(f"pymssql version: {pymssql.__version__}")

    try:
        # Connect to database
        conn = pymssql.connect(
            server="192.168.36.250",
            user="sa",
            password="123456",
            database="PUCIDCardMaker",
            tds_version="7.0",
        )
        print("✓ Database connection successful!")

        cursor = conn.cursor()

        # Test both tables
        tables = ["AcadStudentCards", "EngStudentCards"]

        for table in tables:
            print(f"\n=== Testing {table} ===")

            try:
                # Check if table exists
                cursor.execute(f"SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = '{table}'")
                table_exists = cursor.fetchone()[0]

                if table_exists == 0:
                    print(f"✗ Table {table} does not exist")
                    continue

                print(f"✓ Table {table} exists")

                # Get total record count
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                total_records = cursor.fetchone()[0]
                print(f"  Total records: {total_records}")

                # Get photo count
                cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE photo IS NOT NULL")
                photo_count = cursor.fetchone()[0]
                print(f"  Records with photos: {photo_count}")

                # Get sample of photo sizes
                if photo_count > 0:
                    cursor.execute(
                        f"SELECT TOP 5 IDNo, DATALENGTH(photo) as photo_size FROM {table} WHERE photo IS NOT NULL ORDER BY IDNo"
                    )
                    samples = cursor.fetchall()
                    print("  Sample photo sizes:")
                    for student_id, size in samples:
                        print(f"    ID {student_id}: {size:,} bytes")

                # Check for duplicates
                query = (
                    "SELECT COUNT(*) FROM ("
                    "SELECT IDNo "
                    f"FROM {table} "
                    "WHERE photo IS NOT NULL "
                    "GROUP BY IDNo "
                    "HAVING COUNT(*) > 1"
                    ") as duplicates"
                )
                cursor.execute(query)
                duplicate_count = cursor.fetchone()[0]
                if duplicate_count > 0:
                    print(f"  ⚠️  Warning: {duplicate_count} student IDs have multiple photos")
                else:
                    print("  ✓ No duplicate student IDs found")

            except Exception as e:
                print(f"✗ Error testing {table}: {e}")

        cursor.close()
        conn.close()
        print("\n✓ Connection test completed successfully!")

        return True

    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False


def main():
    """Main function to run connection test."""
    success = test_connection()

    if success:
        print("\n=== READY TO DOWNLOAD ===")
        print("The database connection is working correctly.")
        print("You can now run:")
        print("  ./bulk_photo_download.sh [output_directory]")
        print("or")
        print("  python3 download_photos.py --help")
        sys.exit(0)
    else:
        print("\n✗ Connection test failed. Please check:")
        print("  - Database server is running and accessible")
        print("  - Network connectivity to 192.168.36.250")
        print("  - Database credentials are correct")
        print("  - pymssql is properly installed (pip3 install pymssql)")
        sys.exit(1)


if __name__ == "__main__":
    main()
