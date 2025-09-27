#!/usr/bin/env python3
"""
Helper script to convert hex photo data from tsql to actual JPEG files
Works with the same tsql connection as the CSV export scripts
"""

import os
import subprocess
import sys


def convert_hex_to_jpg(student_id, admit_date, hex_data, output_dir):
    """Convert hex string to JPEG file."""
    try:
        # Remove any whitespace and validate hex
        hex_data = hex_data.strip().replace(" ", "").replace("\n", "").replace("\r", "")

        # Skip if no data or invalid hex
        if not hex_data or hex_data == "NULL" or len(hex_data) < 10:
            return False

        # Convert hex to binary
        try:
            binary_data = bytes.fromhex(hex_data)
        except ValueError:
            # If hex conversion fails, try to extract hex from the string
            # Sometimes tsql adds extra formatting
            import re

            hex_matches = re.findall(r"[0-9a-fA-F]+", hex_data)
            if hex_matches:
                hex_clean = "".join(hex_matches)
                binary_data = bytes.fromhex(hex_clean)
            else:
                return False

        # Check if it looks like JPEG data (starts with FF D8)
        if len(binary_data) < 2 or not (binary_data[0] == 0xFF and binary_data[1] == 0xD8):
            print(f"  Warning: {student_id}_{admit_date} - Data doesn't look like JPEG")

        # Create filename
        filename = f"{student_id}_{admit_date}.jpg"
        filepath = os.path.join(output_dir, filename)

        # Write binary data to file
        with open(filepath, "wb") as f:
            f.write(binary_data)

        print(f"  ✓ {filename} ({len(binary_data)} bytes)")
        return True

    except Exception as e:
        print(f"  ✗ {student_id}_{admit_date} - Error: {e}")
        return False


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 process_photo_hex.py <table_name> <output_directory>")
        sys.exit(1)

    table_name = sys.argv[1]
    output_dir = sys.argv[2]

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    print(f"Processing photos from {table_name}...")

    # Use tsql to get photo data - same connection as CSV exports
    query = f"SELECT IDNo, CONVERT(varchar, AdmitDate, 112) as AdmitDateFormatted, CONVERT(varchar(max), photo, 1) as HexPhoto FROM {table_name} WHERE photo IS NOT NULL ORDER BY IDNo"

    cmd = ["tsql", "-S", "OLDSIS2", "-U", "sa", "-P", "123456", "-D", "PUCIDCardMaker"]

    try:
        # Execute tsql command
        process = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        output, error = process.communicate(input=f"{query}\ngo\n")

        if process.returncode != 0:
            print(f"Error executing query: {error}")
            sys.exit(1)

        # Process output
        lines = output.split("\n")
        success_count = 0
        fail_count = 0

        for line in lines:
            line = line.strip()

            # Skip headers, empty lines, and tsql messages
            if (
                not line
                or "locale" in line
                or "charset" in line
                or "Setting" in line
                or "rows affected" in line
                or line.startswith("%")
                or line.startswith("1>")
            ):
                continue

            # Parse tab-separated data
            parts = line.split("\t")
            if len(parts) >= 3:
                student_id = parts[0].strip()
                admit_date = parts[1].strip()
                hex_data = parts[2].strip()

                # Format student ID as left-zero-padded 5 digits
                try:
                    # Remove leading zeros to avoid octal interpretation
                    clean_id = student_id.lstrip("0") or "0"
                    if clean_id.isdigit():
                        formatted_id = f"{int(clean_id):05d}"
                    else:
                        formatted_id = student_id
                except Exception:
                    formatted_id = student_id

                if convert_hex_to_jpg(formatted_id, admit_date, hex_data, output_dir):
                    success_count += 1
                else:
                    fail_count += 1

        print("\n=== RESULTS ===")
        print(f"Successfully converted: {success_count} photos")
        print(f"Failed conversions: {fail_count} photos")
        print(f"Output directory: {output_dir}")

        if success_count > 0:
            print("\n✓ Photo conversion completed!")
        else:
            print("\n✗ No photos were converted successfully")
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
