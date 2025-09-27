#!/usr/bin/env python3
"""
Download student photos with admit dates from PUC ID Card Maker database
Uses the same connection parameters as the working tsql connection
"""

import os
import subprocess
import sys
import tempfile
from datetime import datetime


def download_photos(output_dir):
    """Download all photos from both tables with admit dates in filenames"""

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Tables to process
    tables = ["AcadStudentCards", "EngStudentCards"]

    total_success = 0
    total_failed = 0

    print(f"Starting photo download to: {output_dir}")
    print("Student IDs will be formatted as left-zero-padded 5 digits")
    print("Using same connection parameters as working tsql")
    print("=" * 50)

    for table in tables:
        print(f"\nProcessing {table}...")

        # First get count
        count_query = f"SELECT COUNT(*) FROM {table} WHERE photo IS NOT NULL"
        count_result = run_tsql_query(count_query)

        if count_result:
            photo_count = int(count_result.strip())
            print(f"✓ Found {photo_count} photos in {table}")

            if photo_count == 0:
                continue
        else:
            print(f"✗ Could not get count for {table}")
            continue

        # Get list of students with photos (without the actual photo data first)
        list_query = (
            "SELECT IDNo, CONVERT(varchar, AdmitDate, 112) as AdmitDate "
            f"FROM {table} "
            "WHERE photo IS NOT NULL "
            "ORDER BY IDNo"
        )

        # Get the student list
        student_list = run_tsql_query_with_results(list_query)

        if not student_list:
            print(f"✗ Could not get student list from {table}")
            continue

        # Process each student individually to get their photo
        success_count = 0
        failed_count = 0

        for line in student_list.strip().split("\n"):
            if not line.strip():
                continue

            parts = line.split("\t")
            if len(parts) < 2:
                continue

            student_id = parts[0].strip()
            admit_date = parts[1].strip()

            # Download individual photo
            if download_single_photo(table, student_id, admit_date, output_dir):
                success_count += 1
                total_success += 1
            else:
                failed_count += 1
                total_failed += 1

        print(f"✓ {table} processing completed")
        print(f"  Success: {success_count}, Failed: {failed_count}")
        print("-" * 30)

    # Final summary
    print("\nPhoto download completed!")
    print(f"Success: {total_success} photos | Failed: {total_failed} photos")
    print(f"Photos saved to: {output_dir}")

    if total_success > 0:
        # Show some results
        files = os.listdir(output_dir)
        image_files = [f for f in files if f.lower().endswith(".jpg")]
        print("\nFirst few downloaded photos:")
        for filename in sorted(image_files)[:5]:
            filepath = os.path.join(output_dir, filename)
            size = os.path.getsize(filepath)
            print(f"  {filename} ({size:,} bytes)")

        if len(image_files) > 5:
            print(f"  ... and {len(image_files) - 5} more photos")

        # Create summary
        create_summary_report(output_dir, total_success, total_failed)
        print("✓ Photo download completed successfully!")
        return True
    else:
        print("✗ No photos were downloaded successfully")
        return False


def download_single_photo(table, student_id, admit_date, output_dir):
    """Download a single photo using bcp or similar method"""

    try:
        # Format student ID as 5-digit padded
        clean_id = student_id.lstrip("0")
        if clean_id.isdigit():
            formatted_id = f"{int(clean_id):05d}"
        else:
            formatted_id = "".join(c for c in student_id if c.isalnum())[:5].zfill(5)

        # Create filename
        filename = f"{formatted_id}_{admit_date}.jpg"
        filepath = os.path.join(output_dir, filename)

        # Handle duplicates
        counter = 1
        while os.path.exists(filepath):
            filename = f"{formatted_id}_{admit_date}_{counter:02d}.jpg"
            filepath = os.path.join(output_dir, filename)
            counter += 1

        # Use bcp to extract the photo binary data
        bcp_query = f"SELECT photo FROM {table} WHERE IDNo = '{student_id}'"

        # Create temp file for bcp output
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            # Use bcp to export binary data
            bcp_cmd = [
                "bcp",
                bcp_query,
                "queryout",
                temp_path,
                "-S",
                "OLDSIS2",
                "-d",
                "PUCIDCardMaker",
                "-U",
                "sa",
                "-P",
                "123456",
                "-f",
                create_bcp_format_file(),  # Need format file for image data
                "-T",  # Trusted connection flag might not be needed
            ]

            result = subprocess.run(bcp_cmd, check=False, capture_output=True, text=True)

            if result.returncode == 0 and os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                # Copy the binary data to final location
                os.rename(temp_path, filepath)
                size = os.path.getsize(filepath)
                print(f"  ✓ {filename} ({size:,} bytes)")
                return True
            else:
                print(f"  ✗ {formatted_id}_{admit_date} - bcp failed: {result.stderr}")
                return False

        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    except Exception as e:
        print(f"  ✗ {student_id}_{admit_date} - Error: {e}")
        return False


def create_bcp_format_file():
    """Create a format file for bcp to handle image data"""
    format_content = """13.0
1
1   SQLIMAGE   0   0   ""  1   photo   ""
"""
    format_file = tempfile.NamedTemporaryFile(encoding="utf-8", mode="w", suffix=".fmt", delete=False)
    format_file.write(format_content)
    format_file.close()
    return format_file.name


def run_tsql_query(query):
    """Run a simple query and return the first result"""
    try:
        cmd = ["tsql", "-S", "OLDSIS2", "-D", "PUCIDCardMaker", "-U", "sa", "-P", "123456"]

        full_query = f"{query}\ngo\nquit\n"

        result = subprocess.run(cmd, check=False, input=full_query, capture_output=True, text=True)

        if result.returncode == 0:
            # Parse output to extract just the result
            lines = result.stdout.split("\n")
            for line in lines:
                line = line.strip()
                if line and not any(x in line.lower() for x in ["locale", "charset", "setting", "affected", "%"]):
                    if line.isdigit():
                        return line
            return None
        else:
            print(f"tsql error: {result.stderr}")
            return None
    except Exception as e:
        print(f"Query error: {e}")
        return None


def run_tsql_query_with_results(query):
    """Run a query and return all results"""
    try:
        cmd = ["tsql", "-S", "OLDSIS2", "-D", "PUCIDCardMaker", "-U", "sa", "-P", "123456", "-t", "\t"]

        full_query = f"{query}\ngo\nquit\n"

        result = subprocess.run(cmd, check=False, input=full_query, capture_output=True, text=True)

        if result.returncode == 0:
            # Filter out system messages
            lines = result.stdout.split("\n")
            data_lines = []
            for line in lines:
                if line and not any(x in line.lower() for x in ["locale", "charset", "setting", "affected", "%"]):
                    # Skip header line (contains column names)
                    if "IDNo" not in line and "AdmitDate" not in line:
                        data_lines.append(line)
            return "\n".join(data_lines)
        else:
            print(f"tsql error: {result.stderr}")
            return None
    except Exception as e:
        print(f"Query error: {e}")
        return None


def create_summary_report(output_dir, success_count, fail_count):
    """Create a summary report"""
    summary_file = os.path.join(output_dir, "download_summary.txt")

    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(f"Photo Download Summary - {datetime.now()}\n")
        f.write("=" * 50 + "\n")
        f.write(f"Successfully downloaded: {success_count} photos\n")
        f.write(f"Failed downloads: {fail_count} photos\n")
        f.write(f"Total photos: {success_count + fail_count}\n")
        f.write("\n")
        f.write("Directory Structure:\n")
        f.write("-" * 20 + "\n")

        try:
            files = os.listdir(output_dir)
            for filename in sorted(files):
                filepath = os.path.join(output_dir, filename)
                if os.path.isfile(filepath):
                    size = os.path.getsize(filepath)
                    f.write(f"{filename} ({size:,} bytes)\n")
        except Exception as e:
            f.write(f"Error listing files: {e}\n")

    print(f"Summary report created: {summary_file}")


if __name__ == "__main__":
    output_dir = sys.argv[1] if len(sys.argv) > 1 else f"student_photos_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    success = download_photos(output_dir)
    sys.exit(0 if success else 1)
