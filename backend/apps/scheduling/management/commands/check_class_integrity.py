"""Management command for checking and fixing class scheduling data integrity.

This command validates that all classes follow the proper ClassHeader → ClassSession → ClassPart
structure and can automatically fix common integrity issues.

Usage:
    python manage.py check_class_integrity                    # Check integrity only
    python manage.py check_class_integrity --fix              # Check and fix issues
    python manage.py check_class_integrity --term 123         # Check specific term
    python manage.py check_class_integrity --fix --term 123   # Fix issues in specific term
"""

from django.core.management.base import BaseCommand

from apps.scheduling.models import ClassHeader, ClassPart, ClassSession


class Command(BaseCommand):
    """Check and fix class scheduling data integrity."""

    help = "Check and fix class scheduling data integrity"

    def add_arguments(self, parser):
        parser.add_argument(
            "--fix",
            action="store_true",
            help="Attempt to fix integrity issues",
        )
        parser.add_argument(
            "--term",
            type=int,
            help="Check only classes in specific term ID",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Verbose output with detailed information",
        )

    def handle(self, *args, **options):
        fix_mode = options.get("fix", False)
        term_id = options.get("term")
        verbose = options.get("verbose", False)

        # Get classes to check
        classes = ClassHeader.objects.all()
        if term_id:
            classes = classes.filter(term_id=term_id)

        issues = {"no_sessions": [], "wrong_session_count": [], "no_parts": [], "weight_issues": [], "fixed": []}

        self.stdout.write("Checking class integrity...\n")

        for class_header in classes:
            if verbose:
                self.stdout.write(f"Checking {class_header}...")

            # Check sessions
            session_count = class_header.class_sessions.count()

            if session_count == 0:
                issues["no_sessions"].append(class_header)
                if fix_mode:
                    created, _sessions = class_header.ensure_sessions_exist()
                    if created > 0:
                        issues["fixed"].append(f"Created {created} sessions for {class_header}")

            elif class_header.is_ieap_class() and session_count != 2:
                issues["wrong_session_count"].append(f"{class_header}: IEAP with {session_count} sessions")
                if fix_mode:
                    created, _sessions = class_header.ensure_sessions_exist()
                    if created > 0:
                        issues["fixed"].append(f"Fixed sessions for {class_header}")

            elif not class_header.is_ieap_class() and session_count != 1:
                issues["wrong_session_count"].append(f"{class_header}: Regular with {session_count} sessions")

            # Check parts in each session
            for session in class_header.class_sessions.all():
                if not session.class_parts.exists():
                    issues["no_parts"].append(f"{session}")
                    if fix_mode:
                        created = session.ensure_parts_exist()
                        if created > 0:
                            issues["fixed"].append(f"Created {created} parts for {session}")

                # Check grade weights
                validation = session.validate_parts_structure()
                if validation["warnings"]:
                    issues["weight_issues"].extend([f"{session}: {w}" for w in validation["warnings"]])

        # Report results
        self.stdout.write("\n=== Integrity Check Results ===\n")

        if issues["no_sessions"]:
            self.stdout.write(self.style.ERROR(f"Classes with no sessions: {len(issues['no_sessions'])}"))
            if verbose:
                for cls in issues["no_sessions"][:10]:
                    self.stdout.write(f"  - {cls}")
            elif len(issues["no_sessions"]) > 5:
                for cls in issues["no_sessions"][:5]:
                    self.stdout.write(f"  - {cls}")
                self.stdout.write(f"  ... and {len(issues['no_sessions']) - 5} more")

        if issues["wrong_session_count"]:
            self.stdout.write(
                self.style.ERROR(f"Classes with wrong session count: {len(issues['wrong_session_count'])}")
            )
            if verbose:
                for msg in issues["wrong_session_count"][:10]:
                    self.stdout.write(f"  - {msg}")
            elif len(issues["wrong_session_count"]) > 5:
                for msg in issues["wrong_session_count"][:5]:
                    self.stdout.write(f"  - {msg}")
                self.stdout.write(f"  ... and {len(issues['wrong_session_count']) - 5} more")

        if issues["no_parts"]:
            self.stdout.write(self.style.ERROR(f"Sessions with no parts: {len(issues['no_parts'])}"))
            if verbose:
                for msg in issues["no_parts"][:10]:
                    self.stdout.write(f"  - {msg}")
            elif len(issues["no_parts"]) > 5:
                for msg in issues["no_parts"][:5]:
                    self.stdout.write(f"  - {msg}")
                self.stdout.write(f"  ... and {len(issues['no_parts']) - 5} more")

        if issues["weight_issues"]:
            self.stdout.write(self.style.WARNING(f"Grade weight issues: {len(issues['weight_issues'])}"))
            if verbose:
                for msg in issues["weight_issues"][:10]:
                    self.stdout.write(f"  - {msg}")
            elif len(issues["weight_issues"]) > 5:
                for msg in issues["weight_issues"][:5]:
                    self.stdout.write(f"  - {msg}")
                self.stdout.write(f"  ... and {len(issues['weight_issues']) - 5} more")

        if fix_mode and issues["fixed"]:
            self.stdout.write(self.style.SUCCESS(f"\nFixed {len(issues['fixed'])} issues:"))
            for msg in issues["fixed"]:
                self.stdout.write(f"  ✓ {msg}")

        # Summary
        total_issues = len(issues["no_sessions"]) + len(issues["wrong_session_count"]) + len(issues["no_parts"])

        if total_issues == 0:
            self.stdout.write(self.style.SUCCESS("\n✓ All classes have valid structure!"))
        else:
            self.stdout.write(self.style.WARNING(f"\n⚠ Found {total_issues} structural issues"))
            if not fix_mode:
                self.stdout.write("Run with --fix flag to attempt automatic fixes")

        # Additional statistics
        if verbose:
            self.stdout.write("\n=== Statistics ===")
            total_classes = classes.count()
            ieap_classes = sum(1 for c in classes if c.is_ieap_class())
            regular_classes = total_classes - ieap_classes

            self.stdout.write(f"Total classes checked: {total_classes}")
            self.stdout.write(f"IEAP classes: {ieap_classes}")
            self.stdout.write(f"Regular classes: {regular_classes}")

            # Session statistics
            total_sessions = ClassSession.objects.filter(class_header__in=classes).count()
            self.stdout.write(f"Total sessions: {total_sessions}")

            # Part statistics
            total_parts = ClassPart.objects.filter(class_session__class_header__in=classes).count()
            self.stdout.write(f"Total parts: {total_parts}")
