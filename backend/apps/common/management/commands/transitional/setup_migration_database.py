"""Django management command to set up the migration database.

Creates the migration database and any necessary initial setup.
"""

import psycopg
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Set up the migration database."""

    help = "Create and set up the migration database"

    def handle(self, *args, **options):
        """Create the migration database if it doesn't exist."""
        # Get database connection details
        migration_db_config = settings.DATABASES["migration"]

        # Get connection details from database config
        db_config = migration_db_config

        # Database connection parameters
        conn_params = {
            "host": db_config["HOST"],
            "port": db_config["PORT"] or 5432,
            "user": db_config["USER"],
            "password": db_config["PASSWORD"],
            "dbname": "postgres",  # Connect to default postgres db to create new db
        }

        migration_db_name = db_config["NAME"]

        self.stdout.write(f"Setting up migration database: {migration_db_name}")

        try:
            # Connect to PostgreSQL server
            with psycopg.connect(**conn_params) as conn:
                conn.autocommit = True
                with conn.cursor() as cursor:
                    # Check if database exists
                    cursor.execute(
                        "SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s",
                        (migration_db_name,),
                    )

                    if cursor.fetchone():
                        self.stdout.write(self.style.WARNING(f"Database '{migration_db_name}' already exists"))
                    else:
                        # Create the database
                        cursor.execute(f'CREATE DATABASE "{migration_db_name}"')
                        self.stdout.write(self.style.SUCCESS(f"Created database '{migration_db_name}'"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error setting up migration database: {e}"))
            raise

        # Test connection to migration database
        try:
            from django.db import connections

            migration_db = connections["migration"]
            with migration_db.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                if result:
                    self.stdout.write(self.style.SUCCESS("✅ Migration database connection test successful"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Migration database connection test failed: {e}"))

        self.stdout.write(self.style.SUCCESS("🔧 Migration database setup completed!"))
