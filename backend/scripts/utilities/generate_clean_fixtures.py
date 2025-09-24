#!/usr/bin/env python3
"""
Generate clean fixtures for all Naga SIS apps.

This script dumps essential configuration data from the database to fixture files.
It only exports non-sensitive, configuration-type data that should be preserved.
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

from django.core.management import call_command


def ensure_fixtures_dir(app_name):
    """Ensure fixtures directory exists for an app."""
    fixtures_path = project_root / "apps" / app_name / "fixtures"
    fixtures_path.mkdir(exist_ok=True)
    return fixtures_path


def dump_fixture(app_name, models, filename, description):
    """Dump specific models to a fixture file."""
    try:
        fixtures_path = ensure_fixtures_dir(app_name)
        fixture_file = fixtures_path / filename

        # Build model list with app prefix
        model_args = []
        for model in models:
            model_args.append(f"{app_name}.{model}")

        print(f"\n📝 Dumping {description}...")
        print(f"   Models: {', '.join(models)}")
        print(f"   File: {fixture_file.relative_to(project_root)}")

        with open(fixture_file, "w") as f:
            call_command("dumpdata", *model_args, format="json", indent=2, stdout=f, verbosity=0)

        size = fixture_file.stat().st_size
        print(f"   ✅ Created: {size:,} bytes")

    except Exception as e:
        print(f"   ❌ Error: {e}")


def main():
    """Generate all fixtures."""
    print("🚀 Generating Clean Fixtures")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    # Common app - foundational data
    dump_fixture("common", ["Holiday", "Room"], "common_foundation.json", "holidays and rooms")

    # People app - profile data
    dump_fixture("people", ["StaffProfile"], "staff_profiles.json", "staff profiles")

    # Curriculum app - academic structure
    dump_fixture("curriculum", ["Division"], "divisions.json", "academic divisions")

    dump_fixture("curriculum", ["Major"], "majors.json", "academic majors")

    dump_fixture("curriculum", ["Cycle"], "cycles.json", "academic cycles")

    dump_fixture("curriculum", ["Term"], "terms.json", "academic terms")

    dump_fixture("curriculum", ["Course", "CoursePrerequisite"], "courses.json", "courses and prerequisites")

    # Academic app - requirements
    dump_fixture("academic", ["CanonicalRequirement"], "canonical_requirements.json", "canonical requirements")

    # Finance app - pricing configuration
    dump_fixture("finance", ["DefaultPricing"], "default_pricing.json", "default pricing tiers")

    dump_fixture("finance", ["CourseFixedPricing"], "course_fixed_pricing.json", "fixed course prices")

    dump_fixture(
        "finance",
        ["SeniorProjectPricing", "SeniorProjectCourse"],
        "senior_project_pricing.json",
        "senior project pricing",
    )

    dump_fixture("finance", ["ReadingClassPricing"], "reading_class_pricing.json", "reading class prices")

    dump_fixture("finance", ["DiscountRule"], "discount_rules.json", "discount rules configuration")

    dump_fixture("finance", ["GLAccount", "FeeGLMapping"], "gl_accounts.json", "GL accounts and mappings")

    dump_fixture("finance", ["FeePricing"], "fee_pricing.json", "fee pricing configuration")

    # Scholarships app - sponsors
    dump_fixture("scholarships", ["Sponsor"], "sponsors.json", "scholarship sponsors")

    # Create a master fixture list
    print("\n📋 Creating master fixture list...")
    fixture_list = []

    for app_dir in (project_root / "apps").iterdir():
        if app_dir.is_dir():
            fixtures_dir = app_dir / "fixtures"
            if fixtures_dir.exists():
                for fixture_file in fixtures_dir.glob("*.json"):
                    if fixture_file.stat().st_size > 0:
                        rel_path = fixture_file.relative_to(project_root)
                        fixture_list.append(str(rel_path))

    # Write fixture load order
    load_order_file = project_root / "scripts" / "utilities" / "fixture_load_order.txt"
    with open(load_order_file, "w") as f:
        f.write("# Naga SIS Fixture Load Order\n")
        f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("# Load fixtures in this order to avoid dependency issues\n\n")

        # Define load order
        load_order = [
            "# Foundation",
            "apps/common/fixtures/common_foundation.json",
            "",
            "# People",
            "apps/people/fixtures/staff_profiles.json",
            "",
            "# Academic Structure",
            "apps/curriculum/fixtures/divisions.json",
            "apps/curriculum/fixtures/majors.json",
            "apps/curriculum/fixtures/cycles.json",
            "apps/curriculum/fixtures/terms.json",
            "apps/curriculum/fixtures/courses.json",
            "",
            "# Academic Requirements",
            "apps/academic/fixtures/canonical_requirements.json",
            "",
            "# Finance Configuration",
            "apps/finance/fixtures/default_pricing.json",
            "apps/finance/fixtures/course_fixed_pricing.json",
            "apps/finance/fixtures/senior_project_pricing.json",
            "apps/finance/fixtures/reading_class_pricing.json",
            "apps/finance/fixtures/gl_accounts.json",
            "apps/finance/fixtures/fee_pricing.json",
            "apps/finance/fixtures/discount_rules.json",
            "",
            "# Scholarships",
            "apps/scholarships/fixtures/sponsors.json",
        ]

        f.write("\n".join(load_order))

    print(f"✅ Created fixture load order: {load_order_file.relative_to(project_root)}")

    print("\n✨ Fixture generation complete!")
    print("\nTo load all fixtures in order:")
    print("  docker compose -f docker-compose.local.yml run --rm django python manage.py loaddata \\")
    print("    apps/common/fixtures/common_foundation.json \\")
    print("    apps/people/fixtures/staff_profiles.json \\")
    print("    apps/curriculum/fixtures/*.json \\")
    print("    apps/academic/fixtures/*.json \\")
    print("    apps/finance/fixtures/*.json \\")
    print("    apps/scholarships/fixtures/*.json")


if __name__ == "__main__":
    main()
