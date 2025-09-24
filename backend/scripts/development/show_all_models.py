#!/usr/bin/env python
"""
Show all Django models in the project with useful information.
Similar to PyCharm's Django service window.
"""

import os
import sys
from collections import defaultdict

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")
os.environ.setdefault("USE_DOCKER", "no")
import django

django.setup()

from django.apps import apps


def show_all_models():
    """Display all Django models organized by app."""

    print("\n" + "=" * 80)
    print(" DJANGO MODELS OVERVIEW (PyCharm-style)")
    print("=" * 80)

    # Group models by app
    app_models = defaultdict(list)
    for model in apps.get_models():
        app_models[model._meta.app_label].append(model)

    # Display by app
    for app_label in sorted(app_models.keys()):
        models_list = app_models[app_label]
        print(f"\n📦 {app_label.upper()} ({len(models_list)} models)")
        print("-" * 40)

        for model in sorted(models_list, key=lambda x: x.__name__):
            # Count fields
            fields = model._meta.get_fields()
            field_count = len([f for f in fields if not f.many_to_many and not f.one_to_many])
            relation_count = len([f for f in fields if f.many_to_many or f.one_to_many])

            # Check for important model attributes
            markers = []
            if hasattr(model, "Meta"):
                if getattr(model.Meta, "abstract", False):
                    markers.append("abstract")
                if getattr(model.Meta, "proxy", False):
                    markers.append("proxy")

            # Display model info
            marker_str = f" [{', '.join(markers)}]" if markers else ""
            print(f"  • {model.__name__:30} - {field_count} fields, {relation_count} relations{marker_str}")

            # Show database table if different from default
            if model._meta.db_table != f"{app_label}_{model.__name__.lower()}":
                print(f"    └─ Table: {model._meta.db_table}")

    # Summary statistics
    total_models = sum(len(models) for models in app_models.values())
    print(f"\n{'=' * 80}")
    print(f"SUMMARY: {len(app_models)} apps, {total_models} models total")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    show_all_models()
