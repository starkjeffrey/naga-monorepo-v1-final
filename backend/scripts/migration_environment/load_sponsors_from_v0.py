"""Load sponsor data from version 0 fixture into the V1 system.

This script imports the sponsor data from the V0 fixture file into our
current V1 scholarships.Sponsor model.
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date

from apps.scholarships.models import Sponsor


class Command(BaseCommand):
    """Load sponsors from V0 fixture data."""

    help = "Load sponsors from version 0 fixture into V1 system"

    def handle(self, *args, **options):
        """Load sponsors from V0 fixture file."""
        # Path to V0 sponsor fixture
        v0_fixture_path = Path(
            "/Users/jeffreystark/PycharmProjects/naga-backend_version_0/apps/core/fixtures/production/fixture_sponsor_c.json",
        )

        if not v0_fixture_path.exists():
            self.stdout.write(self.style.ERROR(f"❌ V0 sponsor fixture not found at: {v0_fixture_path}"))
            return

        self.stdout.write(f"📋 Loading sponsors from: {v0_fixture_path}")

        with Path(v0_fixture_path).open() as f:
            sponsor_data = json.load(f)

        created_count = 0
        updated_count = 0

        for item in sponsor_data:
            if item["model"] != "core.sponsor":
                continue

            fields = item["fields"]

            # Parse dates
            start_date = parse_date(fields["start_date"]) if fields["start_date"] else None
            end_date = parse_date(fields["end_date"]) if fields["end_date"] else None

            # Map V0 fields to V1 Sponsor model
            sponsor_data_v1 = {
                "code": fields["code"],
                "name": fields["name"],
                "contact_name": fields.get("contact_name", "") or "",
                "contact_email": fields.get("contact_email", "") or "",
                "contact_phone": fields.get("contact_phone", "") or "",
                "billing_email": fields.get("billing_email", "") or "",
                "is_active": fields.get("is_active", True),
                "notes": fields.get("notes", "") or "",
                "start_date": start_date,
                "end_date": end_date,
            }

            # Create or update sponsor
            sponsor, created = Sponsor.objects.get_or_create(code=fields["code"], defaults=sponsor_data_v1)

            if created:
                created_count += 1
                self.stdout.write(f"   ✅ Created sponsor: {sponsor.code} - {sponsor.name}")
            else:
                # Update existing sponsor
                for field, value in sponsor_data_v1.items():
                    setattr(sponsor, field, value)
                sponsor.save()
                updated_count += 1
                self.stdout.write(f"   🔄 Updated sponsor: {sponsor.code} - {sponsor.name}")

        self.stdout.write("\n📊 SPONSOR LOAD SUMMARY:")
        self.stdout.write(f"   Created: {created_count}")
        self.stdout.write(f"   Updated: {updated_count}")
        self.stdout.write(f"   Total processed: {len(sponsor_data)}")

        # Verify loaded sponsors
        all_sponsors = Sponsor.objects.all()
        self.stdout.write("\n📋 Current sponsors in system:")
        for sponsor in all_sponsors:
            self.stdout.write(f"   {sponsor.code}: {sponsor.name}")

        self.stdout.write(self.style.SUCCESS("\n✅ Sponsor loading completed!"))
