"""Django management command to migrate both databases in sync."""

import subprocess
import sys

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run migrations on both default and migration databases"

    def add_arguments(self, parser):
        parser.add_argument("app_label", nargs="?", help="App label of migrations to run")
        parser.add_argument(
            "--fake",
            action="store_true",
            help="Mark migrations as run without actually running them",
        )

    def handle(self, *args, **options):
        app_label = options.get("app_label", "")
        fake_flag = "--fake" if options.get("fake") else ""

        self.stdout.write("🔄 Running migrations on both databases...")

        # Migration database first (most critical)
        self.stdout.write("📊 Migrating MIGRATION database...")
        cmd = [
            "docker",
            "compose",
            "-f",
            "docker-compose.local.yml",
            "run",
            "--rm",
            "-e",
            "DJANGO_SETTINGS_MODULE=config.settings.migration",
            "django",
            "python",
            "manage.py",
            "migrate",
        ]
        if app_label:
            cmd.append(app_label)
        if fake_flag:
            cmd.append(fake_flag)

        result = subprocess.run(cmd, check=False, capture_output=False)
        if result.returncode != 0:
            self.stdout.write(self.style.ERROR("❌ Migration database failed - stopping"))
            sys.exit(1)

        self.stdout.write(self.style.SUCCESS("✅ Migration database updated successfully"))

        # Default database
        self.stdout.write("🧪 Migrating DEFAULT database...")
        cmd = [
            "docker",
            "compose",
            "-f",
            "docker-compose.local.yml",
            "run",
            "--rm",
            "django",
            "python",
            "manage.py",
            "migrate",
        ]
        if app_label:
            cmd.append(app_label)
        if fake_flag:
            cmd.append(fake_flag)

        result = subprocess.run(cmd, check=False, capture_output=False)
        if result.returncode != 0:
            self.stdout.write(self.style.ERROR("❌ Default database failed"))
            sys.exit(1)

        self.stdout.write(self.style.SUCCESS("✅ Default database updated successfully"))
        self.stdout.write(self.style.SUCCESS("🎉 Both databases are now in sync!"))
