"""Management command to create the system user for automated enrollment operations.

This command creates the system@naga-sis.local user with appropriate permissions
for audit trails and automated enrollment operations.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.enrollment.constants import (
    SYSTEM_USER_EMAIL,
    SYSTEM_USER_FIRST_NAME,
    SYSTEM_USER_LAST_NAME,
)

User = get_user_model()


class Command(BaseCommand):
    """Create system user for automated enrollment operations."""

    help = "Create system user for automated enrollment operations and audit trails"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--update",
            action="store_true",
            help="Update existing system user if it exists",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        """Create or update the system user."""
        try:
            # Check if system user already exists
            try:
                system_user = User.objects.get(email=SYSTEM_USER_EMAIL)
                if not options["update"]:
                    self.stdout.write(
                        self.style.WARNING(
                            f"System user {SYSTEM_USER_EMAIL} already exists. Use --update to update permissions.",
                        ),
                    )
                    return
                self.stdout.write(f"Updating existing system user: {SYSTEM_USER_EMAIL}")
            except User.DoesNotExist:
                # Create new system user
                # Note: User model uses 'name' field instead of first_name/last_name
                system_user = User.objects.create_user(
                    email=SYSTEM_USER_EMAIL,
                    name=f"{SYSTEM_USER_FIRST_NAME} {SYSTEM_USER_LAST_NAME}",
                    is_staff=True,
                    is_active=True,
                )
                self.stdout.write(f"Created system user: {SYSTEM_USER_EMAIL}")

            # Ensure system user has staff status
            if not system_user.is_staff:
                system_user.is_staff = True
                system_user.save()

            # Get or create staff group
            staff_group, created = Group.objects.get_or_create(name="Staff")
            if created:
                self.stdout.write("Created Staff group")

            # Add system user to staff group
            system_user.groups.add(staff_group)

            # Grant enrollment permissions to system user
            enrollment_permissions = [
                "enrollment.can_manage_enrollments",
                "enrollment.add_classheaderenrollment",
                "enrollment.change_classheaderenrollment",
                "enrollment.view_classheaderenrollment",
                "enrollment.add_programenrollment",
                "enrollment.change_programenrollment",
                "enrollment.view_programenrollment",
            ]

            permissions_granted = []
            for perm_codename in enrollment_permissions:
                try:
                    app_label, codename = perm_codename.split(".", 1)
                    permission = Permission.objects.get(
                        content_type__app_label=app_label,
                        codename=codename,
                    )
                    system_user.user_permissions.add(permission)
                    permissions_granted.append(perm_codename)
                except Permission.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"Permission {perm_codename} not found"))
                except ValueError:
                    self.stdout.write(self.style.ERROR(f"Invalid permission format: {perm_codename}"))

            self.stdout.write(self.style.SUCCESS(f"System user {SYSTEM_USER_EMAIL} configured successfully!"))
            self.stdout.write(f"Granted permissions: {', '.join(permissions_granted)}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to create system user: {e}"))
            raise
