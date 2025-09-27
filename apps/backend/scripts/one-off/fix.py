import csv

# Path to your large CSV
csv_file = "/Users/jeffreystark/PycharmProjects/naga-monorepo/backend/data/migrate/all_academiccoursetakers_250706.csv"  # update with your actual path
output_sql_file = "bulk_updates.sql"

with (
    open(csv_file, newline="", encoding="utf-8") as csvfile,
    open(output_sql_file, "w", encoding="utf-8") as outfile,
):
    reader = csv.DictReader(csvfile)

    for row in reader:
        # Clean/prepare values and handle NULLs
        course = row["NormalizedLangCourse"] or "NULL"
        part = row["NormalizedLangPart"] or "NULL"
        section = row["NormalizedSection"] or "NULL"
        tod = row["NormalizedTOD"] or "NULL"
        classid = row["ClassID"]

        # Wrap non-NULL values in quotes
        course = f"'{course}'" if course != "NULL" else "NULL"
        part = f"'{part}'" if part != "NULL" else "NULL"
        section = f"'{section}'" if section != "NULL" else "NULL"
        tod = f"'{tod}'" if tod != "NULL" else "NULL"

        sql = (
            f"UPDATE academiccoursetakers SET "
            f"NormalizedCourse = {course}, "
            f"NormalizedPart = {part}, "
            f"NormalizedSection = {section}, "
            f"NormalizedTOD = {tod} "
            f"WHERE classid = '{classid}';\n"
        )
        outfile.write(sql)

print(f"✅ Done. SQL update statements written to {output_sql_file}")
