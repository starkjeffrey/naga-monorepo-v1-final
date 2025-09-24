"""
Django management command to list migration dependencies.

This command helps identify potential circular dependencies by listing
what each migration depends on in a simple format.
"""

from django.core.management.base import BaseCommand
from django.db.migrations.loader import MigrationLoader


class Command(BaseCommand):
    """List all migration dependencies in the project."""

    help = "List migration dependencies to help identify circular dependencies"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument("--app", type=str, help="Only show dependencies for specific app")
        parser.add_argument(
            "--sort", choices=["app", "migration"], default="app", help="Sort output by app name or migration name"
        )
        parser.add_argument("--circular-only", action="store_true", help="Only show potential circular dependencies")

    def handle(self, *args, **options):
        """Execute the command."""
        loader = MigrationLoader(None, ignore_no_migrations=True)

        # Get all migration dependencies
        dependencies = self._get_migration_dependencies(loader, options.get("app"))

        # Sort dependencies
        if options["sort"] == "migration":
            dependencies = sorted(dependencies, key=lambda x: x[0].split(".")[1])
        else:
            dependencies = sorted(dependencies, key=lambda x: x[0])

        # Filter for circular dependencies if requested
        if options["circular_only"]:
            dependencies = self._filter_circular_dependencies(dependencies)

        # Output results
        if not dependencies:
            if options["circular_only"]:
                self.stdout.write(self.style.SUCCESS("No potential circular dependencies found!"))
            else:
                self.stdout.write("No migration dependencies found.")
            return

        self.stdout.write(f"\nMigration Dependencies ({len(dependencies)} total):")
        self.stdout.write("-" * 60)

        current_app = None
        for migration_key, deps in dependencies:
            app_name = migration_key.split(".")[0]

            # Group by app for better readability
            if app_name != current_app:
                if current_app is not None:
                    self.stdout.write("")  # Empty line between apps
                current_app = app_name
                self.stdout.write(f"\n{app_name.upper()}:")

            if deps:
                for dep in deps:
                    self.stdout.write(f"  {migration_key} -> {dep}")
            else:
                self.stdout.write(f"  {migration_key} -> (no dependencies)")

    def _get_migration_dependencies(
        self, loader: MigrationLoader, target_app: str | None = None
    ) -> list[tuple[str, list[str]]]:
        """Get migration dependencies from the loader."""
        dependencies = []

        for (app_name, migration_name), migration in loader.graph.nodes.items():
            # Filter by app if specified
            if target_app and app_name != target_app:
                continue

            migration_key = f"{app_name}.{migration_name}"

            # Get dependencies for this migration
            deps = []
            for dep_app, dep_migration in migration.dependencies:
                deps.append(f"{dep_app}.{dep_migration}")

            dependencies.append((migration_key, deps))

        return dependencies

    def _filter_circular_dependencies(self, dependencies: list[tuple[str, list[str]]]) -> list[tuple[str, list[str]]]:
        """Filter to show only potential circular dependencies."""
        # Build a dependency graph
        dep_graph: dict[str, set[str]] = {}
        all_migrations: set[str] = set()

        for migration_key, deps in dependencies:
            all_migrations.add(migration_key)
            dep_graph[migration_key] = set(deps)
            for dep in deps:
                all_migrations.add(dep)

        # Find circular dependencies using DFS
        circular_deps = []
        visited = set()
        rec_stack = set()

        def has_cycle(node: str, path: list[str]) -> bool:
            """Check if there's a cycle starting from this node."""
            if node in rec_stack:
                # Found a cycle - add all nodes in the cycle
                cycle_start = path.index(node)
                {*path[cycle_start:], node}
                return True

            if node in visited:
                return False

            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in dep_graph.get(node, []):
                if has_cycle(neighbor, path):
                    return True

            rec_stack.remove(node)
            path.pop()
            return False

        # Check for cycles and collect problematic dependencies
        problematic_migrations = set()
        for migration in all_migrations:
            if migration not in visited:
                if has_cycle(migration, []):
                    problematic_migrations.add(migration)

        # Filter original dependencies to show only circular ones
        for migration_key, deps in dependencies:
            # Show if this migration is part of a circular dependency
            if migration_key in problematic_migrations:
                # Also check if any of its dependencies create cycles
                for dep in deps:
                    if dep in problematic_migrations:
                        circular_deps.append((migration_key, [dep]))
                        break
                else:
                    # Show all deps if the migration itself is problematic
                    if deps:
                        circular_deps.append((migration_key, deps))

        return circular_deps
