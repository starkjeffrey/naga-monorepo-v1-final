"""Database router for directing migration and legacy data to separate database.

This router directs:
- Legacy tables (legacy_*) to the migration database
- All other models to the default database
"""


class MigrationDatabaseRouter:
    """Router to direct legacy/migration data to separate database."""

    # Models that should use the migration database
    migration_models = {
        # Legacy data tables (raw CSV imports)
        "legacy_students",
        "legacy_academiccoursetakers",
        "legacy_terms",
        "legacy_receipt_headers",
        "legacy_receipt_items",
    }

    def db_for_read(self, model, **hints):
        """Suggest the database to read from."""
        # Check if this is a legacy table by table name
        if hasattr(model, "_meta") and model._meta.db_table in self.migration_models:
            return "migration"
        # Also check by model name for raw queries
        if hasattr(model, "__name__") and model.__name__.startswith("legacy_"):
            return "migration"
        return "default"

    def db_for_write(self, model, **hints):
        """Suggest the database to write to."""
        # Check if this is a legacy table by table name
        if hasattr(model, "_meta") and model._meta.db_table in self.migration_models:
            return "migration"
        # Also check by model name for raw queries
        if hasattr(model, "__name__") and model.__name__.startswith("legacy_"):
            return "migration"
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        """Allow relations if models are in the same database."""
        db_set = {"default", "migration"}
        if obj1._state.db in db_set and obj2._state.db in db_set:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Ensure that certain apps' models get created on the right database."""
        # Legacy models should only be in migration database
        if model_name and f"legacy_{model_name}" in self.migration_models:
            return db == "migration"

        # All Django app models should be in default database
        if app_label in [
            "admin",
            "auth",
            "contenttypes",
            "sessions",
            "sites",
            "messages",
            "staticfiles",
            "accounts",
            "common",
            "people",
            "curriculum",
            "academic",
            "language",
            "enrollment",
            "scheduling",
            "attendance",
            "grading",
            "finance",
            "scholarships",
            "academic_records",
            "level_testing",
            "users",
        ]:
            return db == "default"

        # For unmanaged models (like raw SQL tables), allow in migration db
        if hints.get("model") and not hints["model"]._meta.managed:
            return db == "migration"

        return None
