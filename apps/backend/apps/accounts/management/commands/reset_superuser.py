"""
Management command to reset superuser account.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Reset superuser account with specific credentials"

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            type=str,
            default="stark.jeffrey@pucsr.edu.kh",
            help="Email for the superuser account",
        )
        parser.add_argument(
            "--password",
            type=str,
            required=True,
            help="Password for the superuser account",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force reset even if user exists",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        email = options["email"]
        password = options["password"]
        force = options["force"]

        try:
            with transaction.atomic():
                # Try to get existing user
                try:
                    user = User.objects.get(email=email)
                    if force:
                        self.stdout.write(self.style.WARNING(f"Updating existing superuser: {email}"))
                    else:
                        self.stdout.write(self.style.ERROR(f"User {email} already exists. Use --force to update."))
                        return
                except User.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"Creating new superuser: {email}"))
                    user = User()
                    user.email = email

                # Set user properties
                user.is_active = True
                user.is_staff = True
                user.is_superuser = True
                user.set_password(password)

                # Set username (if your model uses it)
                if hasattr(user, "username"):
                    user.username = email.split("@")[0]  # Use email prefix as username

                # Save the user
                user.save()

                self.stdout.write(self.style.SUCCESS(f"Successfully reset superuser account: {email}"))
                self.stdout.write(self.style.SUCCESS("You can now log in with these credentials."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error resetting superuser: {e!s}"))
            raise
