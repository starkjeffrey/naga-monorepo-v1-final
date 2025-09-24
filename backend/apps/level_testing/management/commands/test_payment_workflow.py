"""Management command to test the payment-first workflow.

This command creates a test access token to verify the payment-first
workflow is functioning correctly.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.level_testing.models import PaymentMethod, TestAccessToken

User = get_user_model()


class Command(BaseCommand):
    help = "Test the payment-first workflow by creating a sample access token"

    def handle(self, *args, **options):
        self.stdout.write("Testing Payment-First Workflow...")

        # Get or create a test cashier user
        cashier, created = User.objects.get_or_create(
            email="cashier@test.com",
            defaults={
                "name": "Test Cashier",
                "is_staff": True,
            },
        )

        if created:
            cashier.set_password("testpass123")
            cashier.save()
            self.stdout.write(self.style.SUCCESS(f"Created test cashier user: {cashier.email}"))

        # Create a test access token
        token = TestAccessToken.objects.create(
            student_name="John Doe",
            student_phone="+85512345678",
            payment_amount=Decimal("5.00"),
            payment_method=PaymentMethod.CASH,
            payment_received_at=timezone.now(),
            cashier=cashier,
        )

        self.stdout.write(self.style.SUCCESS("\n✅ Access Token Created Successfully!"))
        self.stdout.write(f"   Access Code: {token.access_code}")
        self.stdout.write(f"   Student: {token.student_name}")
        self.stdout.write(f"   Phone: {token.student_phone}")
        self.stdout.write(f"   Amount: ${token.payment_amount}")
        self.stdout.write(f"   Valid Until: {token.expires_at}")

        # Generate QR code URL
        from django.conf import settings

        base_url = getattr(settings, "LEVEL_TESTING_BASE_URL", "http://localhost:8000")
        qr_url = f"{base_url}/level-testing/apply/{token.access_code}/"

        self.stdout.write("\n📱 QR Code URL:")
        self.stdout.write(self.style.WARNING(f"   {qr_url}"))

        self.stdout.write(
            self.style.SUCCESS("\n✨ Workflow test complete! Use the URL above to test the mobile flow.")
        )
