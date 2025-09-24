#!/usr/bin/env python
"""
Generate comprehensive Django fixtures including users and staff profiles.
This version includes more tables but still respects the 500 record limit.
"""

import os
import sys
from datetime import datetime

import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from django.core.management import call_command
from django.db import connection

# Define the tables to export with their record limits
TABLES_TO_EXPORT = {
    # Core curriculum and academic structure
    "curriculum.term": 500,
    "curriculum.cycle": 10,
    "curriculum.division": 10,
    "curriculum.major": 50,
    "curriculum.course": 500,
    "curriculum.courseparttemplate": 500,
    "curriculum.textbook": 100,
    # Accounts and roles
    "accounts.department": 50,
    "accounts.role": 20,
    "accounts.position": 50,
    "accounts.userrole": 100,
    # Users and profiles (limited)
    "users.user": 100,  # Include some users
    "people.staffprofile": 50,
    "people.teacherprofile": 50,
    # Common data
    "common.room": 100,
    "common.holiday": 50,
    # Finance configuration
    "finance.discountrule": 50,
    "finance.defaultpricing": 20,
    "finance.administrativefeeconfig": 20,
    "finance.documentexcessfee": 20,
    "finance.glaccount": 100,
    "finance.readingclasspricing": 50,
    "finance.seniorprojectpricing": 50,
    # Academic records configuration
    "academic_records.documenttypeconfig": 20,
    "academic_records.documentquota": 50,
    # Grading configuration
    "grading.gradingscale": 20,
    # Level testing
    "level_testing.placementtest": 50,
    # Scheduling (limited samples)
    "scheduling.combinedcoursetemplate": 50,
    "scheduling.readingclass": 50,
    # System configuration
    "constance.constance": 50,
    # Django core (needed for proper functioning)
    "contenttypes.contenttype": 200,
    "auth.group": 20,
    "auth.permission": 500,
    # Note: We're still excluding tables with large amounts of data:
    # - people.person (18K+)
    # - people.studentprofile (18K+)
    # - enrollment.classheaderenrollment (261K+)
    # - scheduling.classheader (9K+)
    # - scheduling.classpart (9K+)
    # - enrollment.programenrollment (8K+)
    # - legacy_* tables (all have massive amounts of data)
}

# Table name mappings for Django's inconsistent naming
TABLE_NAME_MAPPINGS = {
    "contenttypes.contenttype": "django_content_type",
    "finance.discountrule": "finance_discount_rule",
    "finance.defaultpricing": "finance_default_pricing",
    "finance.administrativefeeconfig": "finance_administrative_fee_config",
    "finance.documentexcessfee": "finance_document_excess_fee",
    "finance.glaccount": "finance_gl_account",
    "finance.readingclasspricing": "finance_reading_class_pricing",
    "finance.seniorprojectpricing": "finance_senior_project_pricing",
    "academic_records.documentquota": "academic_records_document_quota",
}


def get_record_count(app_label, model_name):
    """Get the current record count for a model."""
    with connection.cursor() as cursor:
        # Check if we have a custom mapping
        model_path = f"{app_label}.{model_name}"
        if model_path in TABLE_NAME_MAPPINGS:
            table_name = TABLE_NAME_MAPPINGS[model_path]
        else:
            table_name = f"{app_label}_{model_name}"

        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            return cursor.fetchone()[0]
        except Exception as e:
            # If table doesn't exist, return 0
            if "does not exist" in str(e):
                return 0
            raise


def generate_fixtures():
    """Generate fixtures for all configured tables."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fixture_dir = f"fixtures_comprehensive_{timestamp}"

    # Create fixture directory
    os.makedirs(fixture_dir, exist_ok=True)

    print(f"🚀 Starting comprehensive fixture generation at {datetime.now()}")
    print(f"📁 Output directory: {fixture_dir}")
    print("-" * 60)

    successful_exports = []
    failed_exports = []
    skipped_empty = []
    skipped_too_large = []

    for model_path, limit in sorted(TABLES_TO_EXPORT.items()):
        app_label, model_name = model_path.split(".")

        try:
            # Check record count
            count = get_record_count(app_label, model_name)

            if count == 0:
                skipped_empty.append(model_path)
                continue

            if count > limit:
                print(f"⚠️  Skipping {model_path}: Too many records ({count} > {limit})")
                skipped_too_large.append((model_path, count))
                continue

            # Generate fixture
            fixture_file = os.path.join(fixture_dir, f"{app_label}_{model_name}.json")
            print(f"📝 Exporting {model_path} ({count} records)...", end=" ")

            call_command(
                "dumpdata",
                model_path,
                "--natural-foreign",
                "--natural-primary",
                indent=2,
                output=fixture_file,
                format="json",
                verbosity=0,
            )

            # Verify file was created
            if os.path.exists(fixture_file):
                file_size = os.path.getsize(fixture_file)
                print(f"✅ Done ({file_size:,} bytes)")
                successful_exports.append((model_path, count, file_size))
            else:
                print("❌ Failed")
                failed_exports.append((model_path, "File not created"))

        except Exception as e:
            print(f"❌ Error: {e!s}")
            failed_exports.append((model_path, str(e)))

    # Generate a summary report
    print("\n" + "=" * 60)
    print("📊 COMPREHENSIVE FIXTURE GENERATION SUMMARY")
    print("=" * 60)

    if successful_exports:
        print(f"\n✅ Successfully exported {len(successful_exports)} fixtures:")
        total_size = 0
        total_records = 0
        for model, count, size in successful_exports:
            print(f"   - {model}: {count} records ({size:,} bytes)")
            total_size += size
            total_records += count
        print(f"\n   Total: {total_records:,} records in {total_size:,} bytes")

    if skipped_empty:
        print(f"\n⚠️  Skipped {len(skipped_empty)} empty tables:")
        for model in skipped_empty:
            print(f"   - {model}")

    if skipped_too_large:
        print(f"\n⚠️  Skipped {len(skipped_too_large)} tables with too many records:")
        for model, count in skipped_too_large:
            print(f"   - {model}: {count:,} records")

    if failed_exports:
        print(f"\n❌ Failed to export {len(failed_exports)} fixtures:")
        for model, error in failed_exports:
            print(f"   - {model}: {error}")

    # Create a combined fixture with all data
    if successful_exports:
        print("\n🔄 Creating combined fixture...")
        combined_file = os.path.join(fixture_dir, "all_fixtures_combined.json")

        # Collect all model paths
        models_to_combine = [export[0] for export in successful_exports]

        call_command(
            "dumpdata",
            *models_to_combine,
            "--natural-foreign",
            "--natural-primary",
            indent=2,
            output=combined_file,
            format="json",
            verbosity=0,
        )

        if os.path.exists(combined_file):
            combined_size = os.path.getsize(combined_file)
            print(f"✅ Combined fixture created: {combined_size:,} bytes")

    # Create grouped fixtures by category
    categories = {
        "curriculum": ["curriculum."],
        "accounts_users": ["accounts.", "users.", "people.staff", "people.teacher"],
        "finance": ["finance."],
        "common": ["common."],
        "system": ["contenttypes.", "auth.", "constance."],
    }

    for category_name, prefixes in categories.items():
        category_models = []
        for model, _, _ in successful_exports:
            if any(model.startswith(prefix) for prefix in prefixes):
                category_models.append(model)

        if category_models:
            category_file = os.path.join(fixture_dir, f"{category_name}_fixtures.json")
            print(f"\n📦 Creating {category_name} category fixture...")

            call_command(
                "dumpdata",
                *category_models,
                "--natural-foreign",
                "--natural-primary",
                indent=2,
                output=category_file,
                format="json",
                verbosity=0,
            )

            if os.path.exists(category_file):
                category_size = os.path.getsize(category_file)
                print(f"✅ {category_name} fixture: {category_size:,} bytes")

    # Create a README file
    readme_path = os.path.join(fixture_dir, "README.md")
    with open(readme_path, "w") as f:
        f.write("# Django Fixtures - Comprehensive Export\n\n")
        f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("## Summary\n\n")
        f.write(f"- Total fixtures: {len(successful_exports)}\n")
        f.write(f"- Total records: {sum(export[1] for export in successful_exports):,}\n")
        f.write(f"- Total size: {sum(export[2] for export in successful_exports):,} bytes\n\n")

        f.write("## Included Models\n\n")

        if successful_exports:
            f.write("| Model | Records | File Size |\n")
            f.write("|-------|---------|----------|\n")
            for model, count, size in sorted(successful_exports):
                f.write(f"| {model} | {count:,} | {size:,} bytes |\n")

        f.write("\n## Usage\n\n")
        f.write("### Load all fixtures at once:\n")
        f.write("```bash\n")
        f.write("python manage.py loaddata all_fixtures_combined.json\n")
        f.write("```\n\n")

        f.write("### Load by category:\n")
        f.write("```bash\n")
        f.write("# Load curriculum data\n")
        f.write("python manage.py loaddata curriculum_fixtures.json\n\n")
        f.write("# Load user and account data\n")
        f.write("python manage.py loaddata accounts_users_fixtures.json\n\n")
        f.write("# Load finance configuration\n")
        f.write("python manage.py loaddata finance_fixtures.json\n\n")
        f.write("# Load common reference data\n")
        f.write("python manage.py loaddata common_fixtures.json\n\n")
        f.write("# Load system configuration\n")
        f.write("python manage.py loaddata system_fixtures.json\n")
        f.write("```\n\n")

        f.write("### Load individual fixtures:\n")
        f.write("```bash\n")
        f.write("python manage.py loaddata <fixture_file>.json\n")
        f.write("```\n\n")

        f.write("## Notes\n\n")
        f.write("- Fixtures use natural keys where possible for better portability\n")
        f.write("- Large tables (>500 records) were excluded\n")
        f.write("- Legacy data tables were excluded\n")
        f.write("- Student data was excluded for privacy\n")

    print(f"\n📄 README created at: {readme_path}")
    print(f"\n✨ Comprehensive fixture generation complete! Check the '{fixture_dir}' directory.")


if __name__ == "__main__":
    generate_fixtures()
