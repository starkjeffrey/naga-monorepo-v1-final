#!/usr/bin/env python
"""
Analyze the impact of recreating specific database tables.
Shows what data would be lost and what operations would be blocked.
"""

import os
import sys

import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from django.apps import apps
from django.db import connection, models


def analyze_table_recreation_impact(model_labels: list[str]):
    """
    Analyze what happens if we recreate (drop and create) specified tables.

    Args:
        model_labels: List of model labels in format "app_label.ModelName"
    """

    # Get model classes
    target_models = []
    for label in model_labels:
        try:
            app_label, model_name = label.split(".")
            model = apps.get_model(app_label, model_name)
            target_models.append(model)
        except (ValueError, LookupError) as e:
            print(f"❌ Error finding model {label}: {e}")
            return

    print("🔍 IMPACT ANALYSIS: Table Recreation")
    print("=" * 80)
    print("Target tables to recreate:")
    for model in target_models:
        table_name = model._meta.db_table
        print(f"  - {model._meta.label} → {table_name}")
    print()

    # Analyze for each target model
    for target_model in target_models:
        print(f"\n{'=' * 80}")
        print(f"📊 Analyzing: {target_model._meta.label} ({target_model._meta.db_table})")
        print(f"{'=' * 80}")

        # Get current record count
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM {target_model._meta.db_table}")
            count = cursor.fetchone()[0]
            print(f"\n📈 Current records in table: {count:,}")

        # Find all relationships pointing TO this model
        cascade_relationships = []
        protect_relationships = []
        set_null_relationships = []
        other_relationships = []

        for model in apps.get_models():
            for field in model._meta.get_fields():
                if isinstance(field, models.ForeignKey | models.OneToOneField):
                    if field.related_model == target_model:
                        rel_info = {
                            "source_model": model._meta.label,
                            "field_name": field.name,
                            "field_type": field.__class__.__name__,
                            "on_delete": field.remote_field.on_delete,
                            "null": field.null,
                            "source_table": model._meta.db_table,
                        }

                        if field.remote_field.on_delete == models.CASCADE:
                            cascade_relationships.append(rel_info)
                        elif field.remote_field.on_delete == models.PROTECT:
                            protect_relationships.append(rel_info)
                        elif field.remote_field.on_delete == models.SET_NULL:
                            set_null_relationships.append(rel_info)
                        else:
                            other_relationships.append(rel_info)

                # Check ManyToMany relationships
                elif isinstance(field, models.ManyToManyField):
                    if field.related_model == target_model:
                        print("\n🔗 ManyToMany relationship:")
                        print(f"   {model._meta.label}.{field.name} ↔ {target_model._meta.label}")
                        print(f"   Through table: {field.remote_field.through._meta.db_table}")

        # Report findings
        if cascade_relationships:
            print(f"\n🗑️  CASCADE Relationships ({len(cascade_relationships)})")
            print("   These tables will LOSE DATA when target is dropped:")
            print("-" * 60)
            for rel in cascade_relationships:
                # Count affected records
                source_model = apps.get_model(*rel["source_model"].split("."))
                try:
                    affected_count = source_model.objects.filter(**{f"{rel['field_name']}__isnull": False}).count()
                    print(f"   ❌ {rel['source_model']}.{rel['field_name']}")
                    print(f"      → Will DELETE {affected_count:,} records from {rel['source_table']}")
                except Exception as e:
                    print(f"   ❌ {rel['source_model']}.{rel['field_name']}")
                    print(f"      → Error counting records: {e}")

        if protect_relationships:
            print(f"\n🛡️  PROTECT Relationships ({len(protect_relationships)})")
            print("   These will BLOCK deletion if they have data:")
            print("-" * 60)
            for rel in protect_relationships:
                # Check if any records exist
                source_model = apps.get_model(*rel["source_model"].split("."))
                try:
                    has_data = source_model.objects.filter(**{f"{rel['field_name']}__isnull": False}).exists()
                    if has_data:
                        count = source_model.objects.filter(**{f"{rel['field_name']}__isnull": False}).count()
                        print(f"   🚫 {rel['source_model']}.{rel['field_name']}")
                        print(f"      → WILL BLOCK: {count:,} records in {rel['source_table']}")
                    else:
                        print(f"   ✅ {rel['source_model']}.{rel['field_name']}")
                        print("      → No data, won't block")
                except Exception as e:
                    print(f"   ⚠️  {rel['source_model']}.{rel['field_name']}")
                    print(f"      → Error checking: {e}")

        if set_null_relationships:
            print(f"\n🔄 SET_NULL Relationships ({len(set_null_relationships)})")
            print("   These fields will be set to NULL:")
            print("-" * 60)
            for rel in set_null_relationships:
                source_model = apps.get_model(*rel["source_model"].split("."))
                try:
                    affected_count = source_model.objects.filter(**{f"{rel['field_name']}__isnull": False}).count()
                    print(f"   ⚠️  {rel['source_model']}.{rel['field_name']}")
                    print(f"      → Will NULL {affected_count:,} records in {rel['source_table']}")
                except Exception as e:
                    print(f"   ⚠️  {rel['source_model']}.{rel['field_name']}")
                    print(f"      → Error counting: {e}")

        # Find indirect CASCADE chains
        print("\n🔗 CASCADE Chain Analysis")
        print("-" * 60)
        cascade_chains = find_cascade_chains_from_model(target_model)
        if cascade_chains:
            for i, chain in enumerate(cascade_chains[:10], 1):  # Show top 10
                print(f"   Chain {i}: {' → '.join(chain)}")
                # Estimate total impact
                try:
                    final_model = apps.get_model(*chain[-1].split("."))
                    impact_count = final_model.objects.count()
                    print(f"           Potential impact: up to {impact_count:,} records")
                except Exception:
                    pass
        else:
            print("   No CASCADE chains found")

        # Summary
        print(f"\n📊 SUMMARY for {target_model._meta.label}")
        print("-" * 60)
        print(f"   Direct data loss: {count:,} records")
        print(f"   CASCADE deletions: {len(cascade_relationships)} relationships")
        print(f"   PROTECT blocks: {len(protect_relationships)} relationships")
        print(f"   SET_NULL impacts: {len(set_null_relationships)} relationships")


def find_cascade_chains_from_model(start_model, max_depth=5):
    """Find all CASCADE chains starting from a model."""
    chains = []

    def trace_cascades(model, path=None, depth=0):
        if path is None:
            path = []
        if depth > max_depth:
            return

        model_label = model._meta.label
        path.append(model_label)

        # Find all models that CASCADE from this one
        for other_model in apps.get_models():
            for field in other_model._meta.get_fields():
                if isinstance(field, models.ForeignKey | models.OneToOneField):
                    if field.related_model == model and field.remote_field.on_delete == models.CASCADE:
                        if other_model._meta.label not in path:  # Avoid cycles
                            sub_chains = trace_cascades(other_model, path.copy(), depth + 1)
                            if not sub_chains:
                                chains.append([*path, other_model._meta.label])

        return chains

    trace_cascades(start_model)
    return chains


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Analyze impact of recreating database tables",
        epilog="Example: python analyze_table_recreation_impact.py people.StudentProfile enrollment.ProgramEnrollment",
    )
    parser.add_argument("models", nargs="+", help="Model labels to analyze (format: app_label.ModelName)")

    args = parser.parse_args()

    # Run analysis
    analyze_table_recreation_impact(args.models)

    print("\n" + "=" * 80)
    print("⚠️  IMPORTANT NOTES:")
    print("=" * 80)
    print("1. PROTECT relationships will prevent table deletion if they contain data")
    print("2. CASCADE relationships will delete all related records automatically")
    print("3. SET_NULL relationships will set foreign keys to NULL (data loss)")
    print("4. Always backup before recreating tables!")
    print("5. Consider using migrations instead of recreating tables")


if __name__ == "__main__":
    main()
