"""
Django management command to detect circular import dependencies between apps.

This command analyzes import dependencies across Django apps and identifies
potential circular dependencies that could cause import issues.
"""

import ast
from collections import defaultdict
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class ImportVisitor(ast.NodeVisitor):
    """AST visitor to extract import statements from Python files."""

    def __init__(self):
        self.imports = []

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(alias.name)

    def visit_ImportFrom(self, node):
        if node.module:
            self.imports.append(node.module)


class Command(BaseCommand):
    """Management command to detect circular imports between Django apps."""

    help = "Detect circular import dependencies between Django apps"

    def add_arguments(self, parser):
        parser.add_argument(
            "--show-details", action="store_true", help="Show detailed import paths for each circular dependency"
        )
        parser.add_argument("--exclude-tests", action="store_true", help="Exclude test files from analysis")

    def handle(self, *args, **options):
        """Main command handler."""
        self.show_details = options["show_details"]
        self.exclude_tests = options["exclude_tests"]

        # Build dependency graph
        app_dependencies = self._build_dependency_graph()

        # Find circular dependencies
        circular_deps = self._find_circular_dependencies(app_dependencies)

        if circular_deps:
            self.stdout.write(self.style.ERROR(f"Found {len(circular_deps)} circular dependency chains:"))
            for i, cycle in enumerate(circular_deps, 1):
                self.stdout.write(f"\n{i}. {' -> '.join([*cycle, cycle[0]])}")

                if self.show_details:
                    self._show_cycle_details(cycle, app_dependencies)
        else:
            self.stdout.write(self.style.SUCCESS("No circular dependencies detected!"))

        # Show summary statistics
        self._show_summary(app_dependencies)

    def _build_dependency_graph(self) -> dict[str, set[str]]:
        """Build a graph of app dependencies based on import statements."""
        dependencies = defaultdict(set)
        apps_dir = Path(settings.BASE_DIR) / "apps"

        # Get all Django app names
        app_names = set()
        for app_path in apps_dir.iterdir():
            if app_path.is_dir() and (app_path / "__init__.py").exists():
                app_names.add(app_path.name)

        # Analyze imports in each app
        for app_name in app_names:
            app_path = apps_dir / app_name
            app_imports = self._get_app_imports(app_path, app_names)
            dependencies[app_name] = app_imports

        return dependencies

    def _get_app_imports(self, app_path: Path, app_names: set[str]) -> set[str]:
        """Extract imports to other Django apps from an app directory."""
        imports = set()

        for py_file in app_path.rglob("*.py"):
            # Skip test files if requested
            if self.exclude_tests and "test" in py_file.name:
                continue

            try:
                with open(py_file, encoding="utf-8") as f:
                    tree = ast.parse(f.read())

                visitor = ImportVisitor()
                visitor.visit(tree)

                # Check which imports reference other Django apps
                for import_name in visitor.imports:
                    # Look for patterns like "apps.other_app" or "other_app"
                    if import_name.startswith("apps."):
                        parts = import_name.split(".")
                        if len(parts) >= 2 and parts[1] in app_names:
                            imports.add(parts[1])
                    elif import_name in app_names:
                        imports.add(import_name)

            except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
                # Skip files that can't be parsed
                continue

        return imports

    def _find_circular_dependencies(self, dependencies: dict[str, set[str]]) -> list[list[str]]:
        """Find all circular dependencies using DFS."""
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: list[str]) -> None:
            if node in rec_stack:
                # Found a cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:]
                if len(cycle) > 1:  # Only report cycles with more than 1 node
                    cycles.append(cycle)
                return

            if node in visited:
                return

            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in dependencies.get(node, set()):
                dfs(neighbor, path[:])

            rec_stack.remove(node)
            path.pop()

        for app in dependencies:
            if app not in visited:
                dfs(app, [])

        # Remove duplicate cycles (same cycle in different order)
        unique_cycles = []
        for cycle in cycles:
            # Normalize cycle to start with lexicographically smallest element
            min_idx = cycle.index(min(cycle))
            normalized = cycle[min_idx:] + cycle[:min_idx]

            # Check if we already have this cycle
            if normalized not in unique_cycles:
                unique_cycles.append(normalized)

        return unique_cycles

    def _show_cycle_details(self, cycle: list[str], dependencies: dict[str, set[str]]):
        """Show detailed information about a circular dependency."""
        self.stdout.write("   Details:")
        for i in range(len(cycle)):
            current = cycle[i]
            next_app = cycle[(i + 1) % len(cycle)]

            if next_app in dependencies.get(current, set()):
                self.stdout.write(f"     {current} imports from {next_app}")

    def _show_summary(self, dependencies: dict[str, set[str]]):
        """Show summary statistics about app dependencies."""
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("DEPENDENCY SUMMARY")
        self.stdout.write("=" * 50)

        total_deps = sum(len(deps) for deps in dependencies.values())
        self.stdout.write(f"Total apps analyzed: {len(dependencies)}")
        self.stdout.write(f"Total dependencies: {total_deps}")

        # Show apps with most dependencies
        sorted_apps = sorted(dependencies.items(), key=lambda x: len(x[1]), reverse=True)

        self.stdout.write("\nApps with most dependencies:")
        for app, deps in sorted_apps[:5]:
            self.stdout.write(f"  {app}: {len(deps)} dependencies")
            if deps:
                self.stdout.write(f"    -> {', '.join(sorted(deps))}")
