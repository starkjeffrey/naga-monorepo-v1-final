"""
Management command to set up read-only user groups and accounts.

This command creates two read-only groups and associated user accounts:
1. Read-Only Staff: Can view everything EXCEPT finance
2. Read-Only Admin: Can view everything INCLUDING finance

Usage:
    python manage.py setup_readonly_users
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import transaction

User = get_user_model()


class Command(BaseCommand):
    help = "Set up read-only groups and create read-only user accounts"

    def handle(self, *args, **options):
        """Main command execution."""
        with transaction.atomic():
            # Create groups
            staff_group = self.create_readonly_staff_group()
            admin_group = self.create_readonly_admin_group()

            # Create users
            self.create_staff_user(staff_group)
            self.create_finance_admin_user(admin_group)

            self.stdout.write(
                self.style.SUCCESS(
                    "\n✅ Successfully created read-only groups and users!\n"
                    "Users created:\n"
                    "1. staff@pucsr.edu.kh (password: staff123) - Can view everything EXCEPT finance\n"
                    "2. finadmin@pucsr.edu.kh (password: finadmin123) - Can view everything INCLUDING finance"
                )
            )

    def create_readonly_staff_group(self):
        """Create Read-Only Staff group with all view permissions except finance."""
        # Create the read-only group
        readonly_group, created = Group.objects.get_or_create(name="Read-Only Staff")

        if created:
            self.stdout.write("Created group: Read-Only Staff")
        else:
            self.stdout.write("Group already exists: Read-Only Staff")
            # Clear existing permissions to reset
            readonly_group.permissions.clear()

        # Get all view permissions EXCEPT finance
        view_permissions = Permission.objects.filter(codename__startswith="view_").exclude(
            content_type__app_label="finance"
        )

        # Add permissions to group
        readonly_group.permissions.add(*view_permissions)

        self.stdout.write(f"Added {view_permissions.count()} view permissions to Read-Only Staff (excluding finance)")

        return readonly_group

    def create_readonly_admin_group(self):
        """Create Read-Only Admin group with all view permissions including finance."""
        readonly_group, created = Group.objects.get_or_create(name="Read-Only Admin")

        if created:
            self.stdout.write("Created group: Read-Only Admin")
        else:
            self.stdout.write("Group already exists: Read-Only Admin")
            # Clear existing permissions to reset
            readonly_group.permissions.clear()

        # Get ALL view permissions
        view_permissions = Permission.objects.filter(codename__startswith="view_")

        # Add permissions to group
        readonly_group.permissions.add(*view_permissions)

        self.stdout.write(f"Added {view_permissions.count()} view permissions to Read-Only Admin (including finance)")

        return readonly_group

    def create_staff_user(self, group):
        """Create the staff@pucsr.edu.kh user."""
        email = "staff@pucsr.edu.kh"
        password = "staff123"

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "name": "Read-Only Staff",
                "is_staff": True,  # Required to access admin
                "is_active": True,
            },
        )

        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(f"Created user: {email}")
        else:
            # Update existing user
            user.email = email
            user.is_staff = True
            user.is_active = True
            user.set_password(password)
            user.save()
            self.stdout.write(f"Updated existing user: {email}")

        # Clear existing groups and add both Read-Only Staff and admin groups
        user.groups.clear()
        user.groups.add(group)

        # Add to admin group for web interface access
        admin_group, _ = Group.objects.get_or_create(name="admin")
        user.groups.add(admin_group)

        return user

    def create_finance_admin_user(self, group):
        """Create the finadmin@pucsr.edu.kh user."""
        email = "finadmin@pucsr.edu.kh"
        password = "finadmin123"

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "name": "Finance Admin",
                "is_staff": True,  # Required to access admin
                "is_active": True,
            },
        )

        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(f"Created user: {email}")
        else:
            # Update existing user
            user.email = email
            user.is_staff = True
            user.is_active = True
            user.set_password(password)
            user.save()
            self.stdout.write(f"Updated existing user: {email}")

        # Clear existing groups and add both Read-Only Admin and admin groups
        user.groups.clear()
        user.groups.add(group)

        # Add to admin group for web interface access
        admin_group, _ = Group.objects.get_or_create(name="admin")
        user.groups.add(admin_group)

        return user
