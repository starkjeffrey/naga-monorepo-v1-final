"""Database routers for migration environment."""


class MigrationRouter:
    """Database router for migration environment.

    Routes models to appropriate databases:
    - Migration-specific models go to 'migration_data' database
    - Regular models go to 'default' database
    """

    # Apps that should use migration database
    migration_apps = {"migration_testing"}

    def db_for_read(self, model, **hints) -> str | None:
        """Suggest the database to read from."""
        if model._meta.app_label in self.migration_apps:
            return "migration_data"
        return "default"

    def db_for_write(self, model, **hints) -> str | None:
        """Suggest the database to write to."""
        if model._meta.app_label in self.migration_apps:
            return "migration_data"
        return "default"

    def allow_relation(self, obj1, obj2, **hints) -> bool | None:
        """Allow relations if models are in the same app."""
        db_set = {"default", "migration_data"}
        if obj1._state.db in db_set and obj2._state.db in db_set:
            return True
        return None

    def allow_migrate(self, db: str, app_label: str, model_name=None, **hints) -> bool | None:
        """Ensure that certain apps' models get created on the appropriate database."""
        if app_label in self.migration_apps:
            return db == "migration_data"
        if db == "migration_data":
            return False
        return db == "default"
