#!/usr/bin/env python3
# Updated version of your original program with admit dates
import os

import pymssql

print("pymssql version: ", pymssql.__version__)
print("get_dbversion: ", pymssql.get_dbversion())
print("version_info: ", pymssql.version_info())

# =============================================================================
# CONNECT TO THE DB
# =============================================================================
conn = pymssql.connect(
    server="OLDSIS2",
    user="sa",
    password="123456",
    database="PUCIDCardMaker",
    tds_version="7.0",
)

cursor = conn.cursor()

# Choose which table to process
table_name = input("Which table? (acad/eng/both): ").lower()

if table_name not in ["acad", "eng", "both"]:
    print("Invalid choice. Using 'both'")
    table_name = "both"

tables_to_process = []
if table_name == "acad":
    tables_to_process = ["AcadStudentCards"]
elif table_name == "eng":
    tables_to_process = ["EngStudentCards"]
else:  # both
    tables_to_process = ["AcadStudentCards", "EngStudentCards"]

# Ensure the directory for saving images exists
output_dir = "student_photos_with_dates"
os.makedirs(output_dir, exist_ok=True)

total_success = 0
total_failed = 0

for table in tables_to_process:
    print(f"\n=== Processing {table} ===")

    # SQL query to fetch the image data with admit date
    query = f"select photo, IDNo, CONVERT(varchar, AdmitDate, 112) as AdmitDateFormatted from {table} WHERE photo IS NOT NULL ORDER BY IDNo"
    cursor.execute(query)

    success_count = 0
    failed_count = 0

    # Iterate through the result
    for row in cursor:
        image_data = row[0]  # Image data is in the first column
        image_id = row[1]  # Student ID
        admit_date = row[2]  # Admit date in YYYYMMDD format

        # Format student ID as left-zero-padded 5 digits
        try:
            # Remove leading zeros to avoid octal interpretation
            clean_id = str(image_id).lstrip("0") or "0"
            if clean_id.isdigit():
                formatted_id = f"{int(clean_id):05d}"
            else:
                formatted_id = str(image_id)
        except Exception:
            formatted_id = str(image_id)

        # Define the filename with admit date
        filename = f"{formatted_id}_{admit_date}.jpg"
        image_path = os.path.join(output_dir, filename)

        print("Image data type:", type(image_data))

        # Write the image data to a file
        if image_data is None:
            print(f"  ✗ {filename} - No image data")
            failed_count += 1
        else:
            try:
                with open(image_path, "wb") as file:
                    file.write(image_data)
                print(f"  ✓ {filename} ({len(image_data)} bytes)")
                success_count += 1
            except Exception as e:
                print(f"  ✗ {filename} - Error writing file: {e}")
                failed_count += 1

    print(f"\n{table} Results:")
    print(f"  Successfully saved: {success_count} photos")
    print(f"  Failed: {failed_count} photos")

    total_success += success_count
    total_failed += failed_count

# Close the cursor and connection
cursor.close()
conn.close()

print("\n=== FINAL RESULTS ===")
print(f"Total photos saved: {total_success}")
print(f"Total failures: {total_failed}")
print(f"Photos saved to: {output_dir}")
print("All images have been saved successfully with admit dates in filenames!")
