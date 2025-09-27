#!/usr/bin/env python3
"""
Script to find potentially unused Django models.
Usage: python find_unused_models.py
"""

import ast
import os
import re
from collections import defaultdict
from pathlib import Path

import django
from django.apps import apps
from django.conf import settings


class ModelUsageFinder:
    def __init__(self, project_root="."):
        self.project_root = Path(project_root)
        self.model_references = defaultdict(set)
        self.all_models = set()

    def setup_django(self):
        """Setup Django environment"""
        if not settings.configured:
            # You might need to adjust this path
            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
            django.setup()

    def get_all_models(self):
        """Get all Django models from installed apps"""
        self.setup_django()

        for model in apps.get_models():
            model_name = f"{model._meta.app_label}.{model.__name__}"
            self.all_models.add(model_name)
            # Also add just the class name for simpler references
            self.all_models.add(model.__name__)

    def find_model_references_in_file(self, file_path):
        """Find model references in a Python file using AST parsing"""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Parse with AST for more accurate results
            try:
                tree = ast.parse(content)
                self.visit_ast_nodes(tree, file_path)
            except SyntaxError:
                # Fallback to regex if AST parsing fails
                self.find_references_with_regex(content, file_path)

        except Exception as e:
            print(f"Error processing {file_path}: {e}")

    def visit_ast_nodes(self, node, file_path):
        """Visit AST nodes to find model references"""
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                # Direct model name reference
                if child.id in self.all_models:
                    self.model_references[child.id].add(file_path)

            elif isinstance(child, ast.Attribute):
                # Model references like MyModel.objects
                if hasattr(child, "attr") and hasattr(child.value, "id"):
                    model_ref = child.value.id
                    if model_ref in self.all_models:
                        self.model_references[model_ref].add(file_path)

            elif isinstance(child, ast.Call):
                # Function calls that might reference models
                if hasattr(child.func, "id"):
                    if child.func.id in ["get_model", "apps.get_model"]:
                        # Handle apps.get_model('app', 'Model') calls
                        if len(child.args) >= 2:
                            if isinstance(child.args[1], ast.Str):
                                model_name = child.args[1].s
                                if model_name in self.all_models:
                                    self.model_references[model_name].add(file_path)

    def find_references_with_regex(self, content, file_path):
        """Fallback method using regex to find model references"""
        for model_name in self.all_models:
            # Look for various patterns
            patterns = [
                rf"\b{re.escape(model_name)}\b",  # Direct name
                rf"{re.escape(model_name)}\.objects",  # Model.objects
                rf"from\s+\w+\.models\s+import\s+.*{re.escape(model_name)}",  # imports
                rf"class.*\({re.escape(model_name)}\)",  # inheritance
            ]

            for pattern in patterns:
                if re.search(pattern, content):
                    self.model_references[model_name].add(file_path)
                    break

    def scan_project_files(self):
        """Scan all Python files in the project"""
        python_files = list(self.project_root.rglob("*.py"))

        # Filter out virtual environments and other irrelevant directories
        exclude_patterns = [
            "venv",
            "env",
            ".env",
            "node_modules",
            "__pycache__",
            ".git",
            "migrations",
            ".pytest_cache",
        ]

        filtered_files = []
        for file_path in python_files:
            if not any(pattern in str(file_path) for pattern in exclude_patterns):
                filtered_files.append(file_path)

        print(f"Scanning {len(filtered_files)} Python files...")

        for file_path in filtered_files:
            self.find_model_references_in_file(file_path)

    def find_unused_models(self):
        """Find models that appear to be unused"""
        self.get_all_models()
        self.scan_project_files()

        unused_models = []
        potentially_unused = []

        for model in self.all_models:
            references = self.model_references[model]

            if not references:
                unused_models.append(model)
            elif len(references) == 1:
                # Only referenced in one file - might be just the model definition
                ref_file = next(iter(references))
                if "models.py" in str(ref_file):
                    potentially_unused.append((model, ref_file))

        return unused_models, potentially_unused

    def generate_report(self):
        """Generate a report of unused models"""
        unused, potentially_unused = self.find_unused_models()

        print("\n" + "=" * 60)
        print("UNUSED MODELS REPORT")
        print("=" * 60)

        if unused:
            print(f"\n🔴 DEFINITELY UNUSED MODELS ({len(unused)}):")
            for model in sorted(unused):
                print(f"  - {model}")

        if potentially_unused:
            print(f"\n🟡 POTENTIALLY UNUSED MODELS ({len(potentially_unused)}):")
            print("   (Only referenced in models.py files)")
            for model, file_path in sorted(potentially_unused):
                print(f"  - {model} (in {file_path})")

        if not unused and not potentially_unused:
            print("\n✅ All models appear to be in use!")

        print("\n📊 SUMMARY:")
        print(f"  Total models found: {len(self.all_models)}")
        print(f"  Definitely unused: {len(unused)}")
        print(f"  Potentially unused: {len(potentially_unused)}")

        return unused, potentially_unused


if __name__ == "__main__":
    finder = ModelUsageFinder()
    finder.generate_report()
