import json
import os

import django
from django.apps import apps
from django.core.management import call_command
from django.db import connection

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()


def generate_fixtures():
    """Generate fixtures from all tables with data, excluding large tables (>2000 records)"""

    print("🔍 Analyzing tables for fixture generation...")

    # Get all model tables and their record counts
    tables_to_include = []
    tables_excluded = []

    with connection.cursor() as cursor:
        for model in apps.get_models():
            if not model._meta.managed:
                continue

            table_name = model._meta.db_table
            app_label = model._meta.app_label
            model_name = model.__name__

            try:
                cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
                count = cursor.fetchone()[0]

                if count == 0:
                    print(f"   ⚪ {app_label}.{model_name}: {count} records (empty, skipping)")
                elif count > 2000:
                    print(f"   🔴 {app_label}.{model_name}: {count} records (too large, excluding)")
                    tables_excluded.append(
                        {"app": app_label, "model": model_name, "table": table_name, "count": count}
                    )
                else:
                    print(f"   ✅ {app_label}.{model_name}: {count} records (including)")
                    tables_to_include.append(
                        {"app": app_label, "model": model_name, "table": table_name, "count": count}
                    )

            except Exception as e:
                print(f"   ❌ {app_label}.{model_name}: Error - {e}")

    print("\n📊 Summary:")
    print(f"   ✅ Tables to include: {len(tables_to_include)}")
    print(f"   🔴 Tables excluded (>2000 records): {len(tables_excluded)}")

    if tables_excluded:
        print("\n📋 Excluded large tables:")
        for table in sorted(tables_excluded, key=lambda x: x["count"], reverse=True):
            print(f"   - {table['app']}.{table['model']}: {table['count']:,} records")

    # Create fixtures directory
    os.makedirs("fixtures", exist_ok=True)

    # Generate fixtures by app
    fixtures_created = []

    # Group by app
    apps_with_data = {}
    for table in tables_to_include:
        app = table["app"]
        if app not in apps_with_data:
            apps_with_data[app] = []
        apps_with_data[app].append(table)

    for app_label, app_tables in apps_with_data.items():
        print(f"\n📦 Generating fixtures for {app_label} app...")

        # Create model list for this app
        model_names = [f"{app_label}.{table['model']}" for table in app_tables]

        fixture_filename = f"fixtures/{app_label}_data.json"

        try:
            # Generate fixture for this app
            with open(fixture_filename, "w") as f:
                call_command("dumpdata", *model_names, indent=2, format="json", stdout=f)

            # Check file size
            file_size = os.path.getsize(fixture_filename)
            total_records = sum(table["count"] for table in app_tables)

            print(f"   ✅ Created {fixture_filename}")
            print(f"      📊 {len(app_tables)} models, {total_records} total records")
            print(f"      📦 File size: {file_size:,} bytes ({file_size / 1024:.1f} KB)")

            fixtures_created.append(
                {
                    "app": app_label,
                    "filename": fixture_filename,
                    "models": len(app_tables),
                    "records": total_records,
                    "size_bytes": file_size,
                }
            )

        except Exception as e:
            print(f"   ❌ Failed to create fixture for {app_label}: {e}")

    # Create summary report
    print("\n📋 Creating fixture summary report...")

    summary = {
        "generation_timestamp": django.utils.timezone.now().isoformat(),
        "total_fixtures_created": len(fixtures_created),
        "fixtures": fixtures_created,
        "excluded_tables": tables_excluded,
        "total_records_exported": sum(f["records"] for f in fixtures_created),
        "total_size_bytes": sum(f["size_bytes"] for f in fixtures_created),
    }

    with open("fixtures/fixture_summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print("✅ Fixture generation complete!")
    print(f"   📦 Created {len(fixtures_created)} fixture files")
    print(f"   📊 Exported {summary['total_records_exported']:,} total records")
    print(
        f"   💾 Total size: {summary['total_size_bytes']:,} bytes ({summary['total_size_bytes'] / 1024 / 1024:.1f} MB)"
    )
    print("   📋 Summary report: fixtures/fixture_summary.json")

    return summary


if __name__ == "__main__":
    try:
        summary = generate_fixtures()
    except Exception as e:
        print(f"❌ Fixture generation failed: {e}")
        import traceback

        traceback.print_exc()
