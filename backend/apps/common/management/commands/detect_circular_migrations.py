"""
Django management command to detect circular migration dependencies.

This command analyzes migration dependencies across all Django apps and identifies
circular dependencies that could cause migration issues.

Algorithm:
1. Collect all migration files from all installed apps
2. Parse each migration file to extract its dependencies
3. Build a directed graph of migration dependencies
4. Use depth-first search to detect cycles in the graph
5. Report any circular dependencies found
"""

import ast
from collections import defaultdict
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand


class MigrationDependencyExtractor(ast.NodeVisitor):
    """AST visitor to extract dependencies from migration files."""

    def __init__(self):
        self.dependencies = []

    def visit_Assign(self, node):
        """Extract dependencies from migration file assignments."""
        # Look for: dependencies = [(...), ...]
        if isinstance(node.targets[0], ast.Name) and node.targets[0].id == "dependencies":
            self._extract_dependencies_list(node.value)
        self.generic_visit(node)

    def _extract_dependencies_list(self, node):
        """Extract individual dependencies from the dependencies list."""
        if isinstance(node, ast.List):
            for item in node.elts:
                if isinstance(item, ast.Tuple | ast.List) and len(item.elts) >= 2:
                    # Extract (app_name, migration_name) tuple
                    if isinstance(item.elts[0], ast.Constant) and isinstance(item.elts[1], ast.Constant):
                        app_name = item.elts[0].value
                        migration_name = item.elts[1].value
                        self.dependencies.append((app_name, migration_name))


class Command(BaseCommand):
    """Management command to detect circular migration dependencies."""

    help = "Detect circular dependencies in Django migrations"

    def add_arguments(self, parser):
        parser.add_argument(
            "--show-details", action="store_true", help="Show detailed migration paths for each circular dependency"
        )
        parser.add_argument("--apps", nargs="+", help="Limit analysis to specific apps (default: all installed apps)")
        parser.add_argument(
            "--exclude-third-party", action="store_true", help="Exclude third-party app migrations from analysis"
        )

    def handle(self, *args, **options):
        """Main command handler."""
        self.show_details = options["show_details"]
        self.target_apps = options.get("apps", [])
        self.exclude_third_party = options["exclude_third_party"]

        self.stdout.write("Analyzing migration dependencies...")

        # Step 1: Collect all migration files and their dependencies
        migration_graph = self._build_migration_dependency_graph()

        if not migration_graph:
            self.stdout.write(self.style.WARNING("No migrations found to analyze."))
            return

        # Step 2: Detect circular dependencies
        circular_deps = self._detect_cycles(migration_graph)

        # Step 3: Output results
        self._output_results(circular_deps, migration_graph)

    def _build_migration_dependency_graph(self) -> dict[tuple[str, str], list[tuple[str, str]]]:
        """
        Build a dependency graph of all migrations.

        Returns:
            Dict mapping (app_name, migration_name) -> list of dependencies
        """
        migration_graph = {}

        # Get all installed apps
        installed_apps = self._get_target_apps()

        for app_config in installed_apps:
            app_name = app_config.label
            migrations_path = self._get_migrations_path(app_config)

            if not migrations_path or not migrations_path.exists():
                continue

            # Process each migration file in the app
            for migration_file in migrations_path.glob("*.py"):
                if migration_file.name.startswith("__"):
                    continue

                migration_name = migration_file.stem
                dependencies = self._extract_migration_dependencies(migration_file)

                migration_key = (app_name, migration_name)
                migration_graph[migration_key] = dependencies

                self.stdout.write(f"  {app_name}.{migration_name}: {len(dependencies)} dependencies", ending="\r")

        self.stdout.write("\n")  # Clear the status line
        return migration_graph

    def _get_target_apps(self):
        """Get the list of apps to analyze."""
        all_apps = apps.get_app_configs()

        if self.target_apps:
            # Filter to specific apps
            target_apps = []
            for app_config in all_apps:
                if app_config.label in self.target_apps:
                    target_apps.append(app_config)
            return target_apps

        if self.exclude_third_party:
            # Exclude third-party apps (those not in our project directory)
            project_apps = []
            base_dir = Path(settings.BASE_DIR)

            for app_config in all_apps:
                app_path = Path(app_config.path)
                if str(app_path).startswith(str(base_dir)):
                    project_apps.append(app_config)
            return project_apps

        return all_apps

    def _get_migrations_path(self, app_config) -> Path | None:
        """Get the migrations directory path for an app."""
        try:
            app_path = Path(app_config.path)
            migrations_path = app_path / "migrations"
            return migrations_path if migrations_path.exists() else None
        except (AttributeError, TypeError):
            return None

    def _extract_migration_dependencies(self, migration_file: Path) -> list[tuple[str, str]]:
        """
        Extract dependencies from a migration file.

        Args:
            migration_file: Path to the migration file

        Returns:
            List of (app_name, migration_name) dependencies
        """
        try:
            with open(migration_file, encoding="utf-8") as f:
                content = f.read()

            # Parse the Python AST
            tree = ast.parse(content)
            extractor = MigrationDependencyExtractor()
            extractor.visit(tree)

            return extractor.dependencies

        except (SyntaxError, UnicodeDecodeError, FileNotFoundError) as e:
            self.stdout.write(self.style.WARNING(f"Could not parse {migration_file}: {e}"))
            return []

    def _detect_cycles(self, graph: dict[tuple[str, str], list[tuple[str, str]]]) -> list[list[tuple[str, str]]]:
        """
        Detect cycles in the migration dependency graph using DFS.

        Args:
            graph: Migration dependency graph

        Returns:
            List of cycles, where each cycle is a list of (app_name, migration_name) tuples
        """
        cycles = []
        visited = set()
        recursion_stack = set()

        def dfs(node: tuple[str, str], path: list[tuple[str, str]]) -> None:
            """Depth-first search to detect cycles."""
            if node in recursion_stack:
                # Found a cycle - extract it from the path
                try:
                    cycle_start = path.index(node)
                    cycle = path[cycle_start:]
                    if len(cycle) > 1:  # Only report actual cycles
                        cycles.append(cycle)
                except ValueError:
                    # Node not in path (shouldn't happen, but handle gracefully)
                    pass
                return

            if node in visited:
                return

            visited.add(node)
            recursion_stack.add(node)

            # Visit all dependencies
            for dependency in graph.get(node, []):
                if dependency in graph:  # Only follow dependencies that exist
                    dfs(dependency, [*path, node])

            recursion_stack.remove(node)

        # Start DFS from each unvisited node
        for migration in graph:
            if migration not in visited:
                dfs(migration, [])

        return self._deduplicate_cycles(cycles)

    def _deduplicate_cycles(self, cycles: list[list[tuple[str, str]]]) -> list[list[tuple[str, str]]]:
        """Remove duplicate cycles (same cycle starting at different points)."""
        unique_cycles = []

        for cycle in cycles:
            # Normalize cycle to start with lexicographically smallest element
            if cycle:
                min_idx = cycle.index(min(cycle))
                normalized = cycle[min_idx:] + cycle[:min_idx]

                # Check if we already have this cycle
                if normalized not in unique_cycles:
                    unique_cycles.append(normalized)

        return unique_cycles

    def _output_results(
        self, cycles: list[list[tuple[str, str]]], graph: dict[tuple[str, str], list[tuple[str, str]]]
    ):
        """Output the analysis results in a human-readable format."""

        self.stdout.write("=" * 60)
        self.stdout.write("MIGRATION DEPENDENCY ANALYSIS RESULTS")
        self.stdout.write("=" * 60)

        total_migrations = len(graph)
        total_dependencies = sum(len(deps) for deps in graph.values())

        self.stdout.write(f"Total migrations analyzed: {total_migrations}")
        self.stdout.write(f"Total dependencies: {total_dependencies}")
        self.stdout.write("")

        if cycles:
            self.stdout.write(self.style.ERROR(f"🚨 FOUND {len(cycles)} CIRCULAR DEPENDENCY CHAIN(S):"))
            self.stdout.write("")

            for i, cycle in enumerate(cycles, 1):
                self.stdout.write(f"{i}. Circular dependency chain:")
                self._display_cycle(cycle)

                if self.show_details:
                    self._display_cycle_details(cycle, graph)

                self.stdout.write("")
        else:
            self.stdout.write(self.style.SUCCESS("✅ No circular dependencies detected!"))

        # Show apps with most dependencies
        self._show_dependency_summary(graph)

    def _display_cycle(self, cycle: list[tuple[str, str]]):
        """Display a single cycle in a readable format."""
        cycle_str = " → ".join(f"{app}.{migration}" for app, migration in cycle)
        # Close the cycle by showing it loops back to the first
        first_migration = f"{cycle[0][0]}.{cycle[0][1]}"
        cycle_str += f" → {first_migration}"

        self.stdout.write(f"   {cycle_str}")

    def _display_cycle_details(
        self, cycle: list[tuple[str, str]], graph: dict[tuple[str, str], list[tuple[str, str]]]
    ):
        """Display detailed information about a cycle."""
        self.stdout.write("   Details:")

        for i in range(len(cycle)):
            current = cycle[i]
            next_migration = cycle[(i + 1) % len(cycle)]

            # Check if current migration actually depends on next migration
            dependencies = graph.get(current, [])
            if next_migration in dependencies:
                self.stdout.write(f"     {current[0]}.{current[1]} depends on {next_migration[0]}.{next_migration[1]}")

    def _show_dependency_summary(self, graph: dict[tuple[str, str], list[tuple[str, str]]]):
        """Show summary statistics about migration dependencies."""
        if not graph:
            return

        self.stdout.write("-" * 40)
        self.stdout.write("DEPENDENCY SUMMARY")
        self.stdout.write("-" * 40)

        # Group by app
        app_stats: defaultdict[str, dict[str, int]] = defaultdict(lambda: {"migrations": 0, "dependencies": 0})

        for (app_name, _migration_name), dependencies in graph.items():
            app_stats[app_name]["migrations"] += 1
            app_stats[app_name]["dependencies"] += len(dependencies)

        # Sort by number of dependencies
        sorted_apps = sorted(app_stats.items(), key=lambda x: x[1]["dependencies"], reverse=True)

        self.stdout.write("Apps with most migration dependencies:")
        for app_name, stats in sorted_apps[:10]:  # Show top 10
            self.stdout.write(f"  {app_name}: {stats['migrations']} migrations, {stats['dependencies']} dependencies")

        # Find migrations with most dependencies
        migration_deps = [(migration, len(deps)) for migration, deps in graph.items()]
        migration_deps.sort(key=lambda x: x[1], reverse=True)

        if migration_deps:
            self.stdout.write("\nMigrations with most dependencies:")
            for (app_name, migration_name), dep_count in migration_deps[:5]:
                self.stdout.write(f"  {app_name}.{migration_name}: {dep_count} dependencies")
