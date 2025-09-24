#!/usr/bin/env python
"""
Analyze Django model relationships and their deletion behaviors (CASCADE, PROTECT, etc.)
"""

import os
import sys
from collections import defaultdict

import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from django.apps import apps
from django.db import models


def get_deletion_behavior_name(deletion_func):
    """Convert deletion function to readable name."""
    if deletion_func == models.CASCADE:
        return "CASCADE"
    elif deletion_func == models.PROTECT:
        return "PROTECT"
    elif deletion_func == models.SET_NULL:
        return "SET_NULL"
    elif deletion_func == models.SET_DEFAULT:
        return "SET_DEFAULT"
    elif deletion_func == models.DO_NOTHING:
        return "DO_NOTHING"
    elif deletion_func == models.RESTRICT:
        return "RESTRICT"
    else:
        return f"CUSTOM ({deletion_func.__name__ if hasattr(deletion_func, '__name__') else str(deletion_func)})"


def analyze_model_relationships(app_label=None, model_name=None):
    """Analyze all model relationships and their deletion behaviors."""

    # Get models to analyze
    if app_label and model_name:
        try:
            model = apps.get_model(app_label, model_name)
            models_to_analyze = [model]
        except LookupError:
            print(f"❌ Model {app_label}.{model_name} not found")
            return
    elif app_label:
        app_config = apps.get_app_config(app_label)
        models_to_analyze = app_config.get_models()
    else:
        models_to_analyze = apps.get_models()

    # Categorize relationships by deletion behavior
    relationships_by_behavior = defaultdict(list)

    # Analyze each model
    for model in models_to_analyze:
        model_label = f"{model._meta.app_label}.{model._meta.model_name}"

        # Check all fields
        for field in model._meta.get_fields():
            if isinstance(field, models.ForeignKey | models.OneToOneField):
                behavior = get_deletion_behavior_name(field.remote_field.on_delete)
                related_model = f"{field.related_model._meta.app_label}.{field.related_model._meta.model_name}"

                relationships_by_behavior[behavior].append(
                    {
                        "source_model": model_label,
                        "field_name": field.name,
                        "field_type": field.__class__.__name__,
                        "related_model": related_model,
                        "null": field.null,
                        "blank": field.blank,
                    }
                )

    # Display results
    print("🔍 Django Model Relationship Analysis")
    print("=" * 80)

    for behavior, relationships in sorted(relationships_by_behavior.items()):
        print(f"\n📌 {behavior} ({len(relationships)} relationships)")
        print("-" * 80)

        for rel in sorted(relationships, key=lambda x: (x["source_model"], x["field_name"])):
            null_info = " (nullable)" if rel["null"] else ""
            print(f"  {rel['source_model']}.{rel['field_name']} → {rel['related_model']}{null_info}")

    # Summary statistics
    print("\n📊 Summary Statistics")
    print("-" * 80)
    total_relationships = sum(len(rels) for rels in relationships_by_behavior.values())
    print(f"Total relationships analyzed: {total_relationships}")

    for behavior, relationships in sorted(relationships_by_behavior.items()):
        percentage = (len(relationships) / total_relationships * 100) if total_relationships > 0 else 0
        print(f"  {behavior}: {len(relationships)} ({percentage:.1f}%)")


def find_cascade_chains(start_model=None):
    """Find potential cascade deletion chains."""
    print("\n🔗 CASCADE Deletion Chains Analysis")
    print("=" * 80)

    # Build a graph of CASCADE relationships
    cascade_graph = defaultdict(list)
    all_models = apps.get_models()

    for model in all_models:
        model_label = f"{model._meta.app_label}.{model._meta.model_name}"

        for field in model._meta.get_fields():
            if isinstance(field, models.ForeignKey | models.OneToOneField):
                if field.remote_field.on_delete == models.CASCADE:
                    related_label = f"{field.related_model._meta.app_label}.{field.related_model._meta.model_name}"
                    cascade_graph[related_label].append({"to_model": model_label, "via_field": field.name})

    # Find chains starting from specified model or all models
    if start_model:
        start_points = [start_model]
    else:
        # Find models that have CASCADE relationships but aren't CASCADE targets
        all_targets = set()
        for targets in cascade_graph.values():
            for target in targets:
                all_targets.add(target["to_model"])

        start_points = [model for model in cascade_graph.keys() if model not in all_targets]

    # Trace CASCADE chains
    def trace_chain(model, path=None, visited=None):
        if path is None:
            path = []
        if visited is None:
            visited = set()

        if model in visited:
            return []  # Circular reference

        visited.add(model)
        path.append(model)

        chains = []
        if model in cascade_graph:
            for target in cascade_graph[model]:
                sub_chains = trace_chain(target["to_model"], path.copy(), visited.copy())
                if sub_chains:
                    chains.extend(sub_chains)
                else:
                    chains.append([*path, target["to_model"]])
        else:
            if len(path) > 1:
                chains.append(path)

        return chains

    # Display CASCADE chains
    all_chains = []
    for start in start_points:
        chains = trace_chain(start)
        all_chains.extend(chains)

    # Sort by chain length
    all_chains.sort(key=len, reverse=True)

    if all_chains:
        print(f"\nFound {len(all_chains)} CASCADE chains:")
        for i, chain in enumerate(all_chains[:20], 1):  # Show top 20 longest chains
            print(f"\n{i}. Chain length: {len(chain)}")
            print("   " + " → ".join(chain))
    else:
        print("\nNo CASCADE chains found.")


def analyze_protection_conflicts():
    """Find potential conflicts between PROTECT and CASCADE."""
    print("\n⚠️  Potential Protection Conflicts")
    print("=" * 80)

    protect_models = set()
    cascade_sources = defaultdict(set)

    for model in apps.get_models():
        model_label = f"{model._meta.app_label}.{model._meta.model_name}"

        for field in model._meta.get_fields():
            if isinstance(field, models.ForeignKey | models.OneToOneField):
                related_label = f"{field.related_model._meta.app_label}.{field.related_model._meta.model_name}"

                if field.remote_field.on_delete == models.PROTECT:
                    protect_models.add(related_label)
                elif field.remote_field.on_delete == models.CASCADE:
                    cascade_sources[model_label].add(related_label)

    # Find conflicts
    conflicts = []
    for cascade_model, targets in cascade_sources.items():
        protected_targets = targets.intersection(protect_models)
        if protected_targets:
            conflicts.append({"cascade_source": cascade_model, "protected_targets": list(protected_targets)})

    if conflicts:
        print(f"\nFound {len(conflicts)} potential conflicts:")
        for conflict in conflicts:
            print(f"\n  Model {conflict['cascade_source']} has CASCADE relationships to:")
            for target in conflict["protected_targets"]:
                print(f"    - {target} (which is also PROTECTED elsewhere)")
    else:
        print("\nNo protection conflicts found.")


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="Analyze Django model relationships and deletion behaviors")
    parser.add_argument("--app", help="Specific app to analyze")
    parser.add_argument("--model", help="Specific model to analyze (requires --app)")
    parser.add_argument("--chains", action="store_true", help="Show CASCADE deletion chains")
    parser.add_argument("--conflicts", action="store_true", help="Show potential protection conflicts")
    parser.add_argument("--start-model", help="Starting model for chain analysis (format: app.model)")

    args = parser.parse_args()

    # Basic analysis
    analyze_model_relationships(args.app, args.model)

    # Additional analyses
    if args.chains:
        find_cascade_chains(args.start_model)

    if args.conflicts:
        analyze_protection_conflicts()


if __name__ == "__main__":
    main()
