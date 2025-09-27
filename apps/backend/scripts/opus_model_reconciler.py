import json
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()


class ModelReconciler:
    def __init__(self):
        with open("integrity_reports/analysis.json") as f:
            self.data = json.load(f)
            self.decisions = self.data["decisions"]

    def update_models(self):
        """Update model files based on decisions"""
        changes = []

        for key, decision in self.decisions.items():
            if decision["action"] == "update_model":
                table, column = key.split(".")
                changes.append(self.modify_model_field(table, column, decision))

        return changes

    def modify_model_field(self, table, column, decision):
        """Modify a specific model field"""
        # Find the model file
        from django.apps import apps

        for model in apps.get_models():
            if model._meta.db_table == table:
                # Get the app and model name
                app_label = model._meta.app_label
                model_name = model.__name__

                # Find the field
                for field in model._meta.fields:
                    if field.column == column:
                        # Generate the change
                        if decision["change"] == "make_nullable":
                            return {
                                "app": app_label,
                                "model": model_name,
                                "field": field.name,
                                "change": "Add null=True, blank=True",
                                "file": f"apps/{app_label}/models.py",
                                "reason": decision.get("reason", "No reason provided"),
                            }
        return None

    def apply_changes(self, changes):
        """Apply changes to model files"""
        for change in changes:
            if change:
                print(f"📝 Updating {change['file']}: {change['model']}.{change['field']}")
                # Here you would actually modify the file
                # For safety, we'll output the changes first


reconciler = ModelReconciler()
changes = reconciler.update_models()

print("\n📋 Required Model Changes:")
print("=" * 50)

if not changes or all(c is None for c in changes):
    print("✅ No model changes required!")
else:
    for change in changes:
        if change:
            print(f"📁 {change['file']}")
            print(f"   Model: {change['model']}")
            print(f"   Field: {change['field']}")
            print(f"   Change: {change['change']}")
            print(f"   Reason: {change['reason']}")
            print()
