"""Management command to generate OpenAPI schema from django-ninja API."""

import json
from pathlib import Path

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Generate OpenAPI schema JSON file from django-ninja API"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default="openapi-schema.json",
            help="Output file path for the OpenAPI schema",
        )

    def handle(self, *args, **options):
        output_file = options["file"]

        # Import API only when command is actually run to avoid startup conflicts
        from config.api import api

        # Get the OpenAPI schema from django-ninja
        schema = api.get_openapi_schema()

        # Write to file
        output_path = Path(output_file)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2, ensure_ascii=False)

        self.stdout.write(self.style.SUCCESS(f"OpenAPI schema generated successfully: {output_path.absolute()}"))
