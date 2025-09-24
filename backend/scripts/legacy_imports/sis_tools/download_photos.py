#!/usr/bin/env python3
"""
Photo Download Script for SIS Database
Downloads student photos from AcadStudentCards and EngStudentCards tables
Student IDs are formatted as left-zero-padded 5 digits for filenames
"""

import argparse
import os
import sys
from pathlib import Path

import pymssql

print("pymssql version:", pymssql.__version__)
print("get_dbversion:", pymssql.get_dbversion())
print("version_info:", pymssql.version_info())


class PhotoDownloader:
    def __init__(
        self,
        server: str = "192.168.36.250",
        user: str = "sa",
        password: str | None = None,
        database: str = "PUCIDCardMaker",
    ):
        """Initialize the photo downloader with database connection parameters."""
        self.server = server
        self.user = user
        # Prefer env var when password not provided to avoid hardcoding secrets
        self.password = password or os.environ.get("SIS_DB_PASSWORD", "")
        self.database = database
        self.conn = None

    def connect(self) -> bool:
        """Establish database connection."""
        try:
            self.conn = pymssql.connect(
                server=self.server,
                user=self.user,
                password=self.password,
                database=self.database,
                tds_version="7.0",
            )
            print(f"✓ Connected to {self.database} database")
            return True
        except Exception as e:
            print(f"✗ Database connection failed: {e}")
            return False

    def disconnect(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            print("✓ Database connection closed")

    def get_photo_count(self, table_name: str) -> int:
        """Get count of photos in the specified table."""
        if not self.conn:
            return 0

        cursor = self.conn.cursor()
        try:
            query = f"SELECT COUNT(*) FROM {table_name} WHERE photo IS NOT NULL"
            cursor.execute(query)
            count = cursor.fetchone()[0]
            return count
        except Exception as e:
            print(f"✗ Error getting photo count from {table_name}: {e}")
            return 0
        finally:
            cursor.close()

    def check_for_duplicates(self, table_name: str) -> list[tuple[str, int]]:
        """Check for student IDs with multiple photos."""
        if not self.conn:
            return []

        cursor = self.conn.cursor()
        try:
            query = (
                "SELECT IDNo, COUNT(*) as photo_count "
                f"FROM {table_name} "
                "WHERE photo IS NOT NULL "
                "GROUP BY IDNo "
                "HAVING COUNT(*) > 1 "
                "ORDER BY COUNT(*) DESC, IDNo"
            )
            cursor.execute(query)
            duplicates = cursor.fetchall()
            return duplicates
        except Exception as e:
            print(f"✗ Error checking duplicates in {table_name}: {e}")
            return []
        finally:
            cursor.close()

    def download_photos(self, table_name: str, output_dir: str) -> tuple[int, int, int]:
        """
        Download photos from specified table.
        Returns: (success_count, fail_count, duplicate_count)
        """
        if not self.conn:
            print("✗ No database connection")
            return 0, 0, 0

        # Ensure output directory exists
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        cursor = self.conn.cursor()
        success_count = 0
        fail_count = 0
        duplicate_count = 0

        try:
            # Get photos with ID numbers
            query = f"SELECT photo, IDNo FROM {table_name} WHERE photo IS NOT NULL ORDER BY IDNo"
            cursor.execute(query)

            print(f"Downloading photos from {table_name}...")

            # Track IDs we've seen to handle duplicates
            seen_ids = {}

            for row in cursor:
                image_data = row[0]
                student_id = row[1]

                if image_data is None:
                    print(f"  Skipping {student_id}: No image data")
                    fail_count += 1
                    continue

                # Format student ID as left-zero-padded 5 digits
                try:
                    id_num = int(student_id)
                    formatted_id = f"{id_num:05d}"
                except (ValueError, TypeError):
                    # If ID is not numeric, use as-is but clean it
                    formatted_id = str(student_id).strip()

                # Handle duplicates by adding suffix
                if formatted_id in seen_ids:
                    seen_ids[formatted_id] += 1
                    filename = f"{formatted_id}_{seen_ids[formatted_id]:02d}.jpg"
                    duplicate_count += 1
                    print(f"  Duplicate ID {formatted_id}, saving as {filename}")
                else:
                    seen_ids[formatted_id] = 0
                    filename = f"{formatted_id}.jpg"

                # Full path for the image
                image_path = os.path.join(output_dir, filename)

                try:
                    # Write the image data to file
                    with open(image_path, "wb") as file:
                        file.write(image_data)

                    # Verify file was written
                    if os.path.exists(image_path) and os.path.getsize(image_path) > 0:
                        print(f"  ✓ {filename} ({len(image_data)} bytes)")
                        success_count += 1
                    else:
                        print(f"  ✗ {filename} - File not created or empty")
                        fail_count += 1

                except Exception as e:
                    print(f"  ✗ {filename} - Write error: {e}")
                    fail_count += 1

        except Exception as e:
            print(f"✗ Query execution error: {e}")
            return success_count, fail_count, duplicate_count
        finally:
            cursor.close()

        return success_count, fail_count, duplicate_count


def main():
    parser = argparse.ArgumentParser(
        description="Download student photos from SIS database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --table AcadStudentCards --output /Users/jeffreystark/Photos/acad
  %(prog)s --table EngStudentCards --output /Users/jeffreystark/Photos/eng
  %(prog)s --table both --output /Users/jeffreystark/Photos
        """,
    )

    parser.add_argument(
        "--table",
        choices=["AcadStudentCards", "EngStudentCards", "both"],
        default="both",
        help="Table to download photos from (default: both)",
    )

    parser.add_argument("--output", "-o", default="./photos", help="Output directory for photos (default: ./photos)")

    parser.add_argument(
        "--check-duplicates", action="store_true", help="Check for duplicate student IDs before downloading"
    )

    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be downloaded without actually downloading"
    )

    args = parser.parse_args()

    # Initialize downloader
    downloader = PhotoDownloader()

    if not downloader.connect():
        sys.exit(1)

    try:
        # Determine which tables to process
        if args.table == "both":
            tables = ["AcadStudentCards", "EngStudentCards"]
        else:
            tables = [args.table]

        total_success = 0
        total_fail = 0
        total_duplicates = 0

        for table in tables:
            print(f"\n=== Processing {table} ===")

            # Get photo count
            photo_count = downloader.get_photo_count(table)
            print(f"Found {photo_count} photos in {table}")

            if photo_count == 0:
                print(f"No photos found in {table}, skipping...")
                continue

            # Check for duplicates if requested
            if args.check_duplicates:
                duplicates = downloader.check_for_duplicates(table)
                if duplicates:
                    print(f"\nDuplicate student IDs found in {table}:")
                    for student_id, count in duplicates:
                        print(f"  ID {student_id}: {count} photos")
                else:
                    print(f"No duplicate student IDs found in {table}")

            if args.dry_run:
                print(f"[DRY RUN] Would download {photo_count} photos from {table}")
                continue

            # All photos go to the same output directory
            table_output_dir = args.output

            # Download photos
            success, fail, duplicates = downloader.download_photos(table, table_output_dir)

            print(f"\n✓ {table} Results:")
            print(f"  Successfully downloaded: {success}")
            print(f"  Failed downloads: {fail}")
            print(f"  Duplicate IDs handled: {duplicates}")
            print(f"  Output directory: {table_output_dir}")

            total_success += success
            total_fail += fail
            total_duplicates += duplicates

        # Final summary
        print("\n=== DOWNLOAD SUMMARY ===")
        print(f"Total photos downloaded: {total_success}")
        print(f"Total failures: {total_fail}")
        print(f"Total duplicates handled: {total_duplicates}")

        print(f"Photos saved to: {args.output}")

        if total_success > 0:
            print("✓ Photo download completed successfully!")
        else:
            print("✗ No photos were downloaded.")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n✗ Download interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        sys.exit(1)
    finally:
        downloader.disconnect()


if __name__ == "__main__":
    main()
