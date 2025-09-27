#!/usr/bin/env python3
"""
Refresh all fixtures for Naga SIS apps.

This script dumps current database data to fixtures in each app's fixtures/ directory.
It organizes fixtures by app and model type for easy loading.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
import django

django.setup()

from django.apps import apps
from django.core.management import call_command

# Define which apps and models to dump fixtures for
FIXTURE_CONFIG = {
    "common": {"models": ["Holiday", "Room", "Sponsor"], "filename": "common_data.json"},
    "accounts": {
        "models": ["User", "Group"],
        "filename": "user_data.json",
        "exclude": True,  # Skip user data for security
    },
    "people": {
        "models": ["Person", "StudentProfile", "TeacherProfile"],
        "filename": "people_data.json",
        "exclude": True,  # Skip personal data for privacy
    },
    "curriculum": {
        "models": ["Division", "Major", "Cycle", "Term", "Course", "CoursePrerequisite"],
        "filename": "curriculum_data.json",
    },
    "academic": {
        "models": ["CanonicalRequirement", "RequirementSet", "StudentRequirement"],
        "filename": "academic_requirements.json",
    },
    "enrollment": {
        "models": ["ClassHeader", "ClassHeaderEnrollment"],
        "filename": "enrollment_data.json",
        "exclude": True,  # Skip enrollment data as it's specific to students
    },
    "finance": {
        "models": [
            "DefaultPricing",
            "CourseFixedPricing",
            "SeniorProjectPricing",
            "ReadingClassPricing",
            "FeePricing",
            "FeeType",
            "GLAccount",
            "FeeGLMapping",
            "DiscountRule",
        ],
        "filename": "finance_config.json",
    },
    "scholarships": {"models": ["Sponsor", "ScholarshipType"], "filename": "scholarship_config.json"},
    "scheduling": {"models": ["TimeSlot", "ClassSchedule"], "filename": "scheduling_config.json"},
    "grading": {"models": ["GradeScale", "GradeMapping"], "filename": "grading_config.json"},
}


def ensure_fixtures_directory(app_name):
    """Ensure the fixtures directory exists for an app."""
    app_path = project_root / "apps" / app_name
    fixtures_path = app_path / "fixtures"

    if not fixtures_path.exists():
        fixtures_path.mkdir(parents=True)
        print(f"✅ Created fixtures directory: {fixtures_path}")

    return fixtures_path


def dump_app_fixtures(app_name, config):
    """Dump fixtures for a specific app."""
    if config.get("exclude", False):
        print(f"⏭️  Skipping {app_name} (marked as excluded)")
        return

    try:
        # Get the app
        app = apps.get_app_config(app_name)

        # Ensure fixtures directory exists
        fixtures_path = ensure_fixtures_directory(app_name)

        # Build model list
        model_args = []
        for model_name in config["models"]:
            try:
                app.get_model(model_name)
                model_args.append(f"{app_name}.{model_name}")
            except LookupError:
                print(f"⚠️  Model {app_name}.{model_name} not found, skipping")

        if not model_args:
            print(f"⚠️  No valid models found for {app_name}, skipping")
            return

        # Create backup of existing fixture if it exists
        fixture_file = fixtures_path / config["filename"]
        if fixture_file.exists():
            backup_name = f"{fixture_file.stem}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            backup_file = fixtures_path / backup_name
            fixture_file.rename(backup_file)
            print(f"📁 Backed up existing fixture to: {backup_name}")

        # Dump the fixtures
        print(f"\n🔄 Dumping fixtures for {app_name}...")
        print(f"   Models: {', '.join(config['models'])}")
        print(f"   Output: {fixture_file}")

        with open(fixture_file, "w") as f:
            call_command("dumpdata", *model_args, format="json", indent=2, stdout=f, verbosity=0)

        # Check file size
        file_size = fixture_file.stat().st_size
        if file_size > 0:
            print(f"✅ Successfully created {config['filename']} ({file_size:,} bytes)")
        else:
            print(f"⚠️  Warning: {config['filename']} is empty")

    except Exception as e:
        print(f"❌ Error dumping fixtures for {app_name}: {e}")


def dump_special_fixtures():
    """Dump special fixtures that need custom handling."""
    print("\n📋 Creating special fixtures...")

    # Dump Terms with specific ordering
    try:
        fixtures_path = ensure_fixtures_directory("curriculum")
        terms_file = fixtures_path / "terms.json"

        print("🔄 Dumping Term fixtures...")
        with open(terms_file, "w") as f:
            call_command("dumpdata", "curriculum.Term", format="json", indent=2, stdout=f, verbosity=0)
        print("✅ Created terms.json")
    except Exception as e:
        print(f"❌ Error creating terms fixture: {e}")

    # Dump Divisions and Majors separately for clarity
    try:
        print("🔄 Dumping Division and Major fixtures...")

        divisions_file = fixtures_path / "divisions.json"
        with open(divisions_file, "w") as f:
            call_command("dumpdata", "curriculum.Division", format="json", indent=2, stdout=f, verbosity=0)

        majors_file = fixtures_path / "majors.json"
        with open(majors_file, "w") as f:
            call_command("dumpdata", "curriculum.Major", format="json", indent=2, stdout=f, verbosity=0)

        print("✅ Created divisions.json and majors.json")
    except Exception as e:
        print(f"❌ Error creating division/major fixtures: {e}")


def main():
    """Main function to refresh all fixtures."""
    print("🚀 Starting fixture refresh process...")
    print(f"📅 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 Project root: {project_root}")

    # Process each app
    for app_name, config in FIXTURE_CONFIG.items():
        dump_app_fixtures(app_name, config)

    # Handle special fixtures
    dump_special_fixtures()

    print("\n✨ Fixture refresh complete!")
    print("\nTo load fixtures, use:")
    print("  python manage.py loaddata <fixture_file>")
    print("\nOr load all fixtures for an app:")
    print("  python manage.py loaddata apps/<app_name>/fixtures/*.json")


if __name__ == "__main__":
    main()
