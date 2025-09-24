#!/usr/bin/env python3
"""
Management Command Mover Script

This script helps move Django management commands to the appropriate categorized directories:
- production/: Regular operational commands
- transitional/: Migration and setup commands
- ephemeral/: Quick analysis and debugging commands

Usage:
    python scripts/utilities/move_management_commands.py [--dry-run] [--app APP_NAME]

Options:
    --dry-run: Show what would be moved without actually moving files
    --app: Process only specific app (default: all apps)
"""

import argparse
import re
import shutil
from pathlib import Path


class CommandCategorizer:
    """Analyzes management commands to suggest appropriate categorization."""

    # Keywords that suggest different categories
    PRODUCTION_KEYWORDS = [
        "report",
        "export",
        "import",
        "process",
        "cleanup",
        "maintenance",
        "sync",
        "update",
        "check",
        "validate",
        "backup",
        "restore",
        "notify",
        "send",
        "generate",
        "calculate",
        "aggregate",
    ]

    TRANSITIONAL_KEYWORDS = [
        "migrate",
        "setup",
        "init",
        "install",
        "configure",
        "create_fixtures",
        "load_data",
        "populate",
        "seed",
        "convert",
        "transform",
        "fix_data",
        "upgrade",
        "install",
        "deploy",
        "create_schema",
    ]

    EPHEMERAL_KEYWORDS = [
        "test",
        "debug",
        "analyze",
        "explore",
        "investigate",
        "check_data",
        "temp",
        "quick",
        "scratch",
        "experimental",
        "prototype",
        "one_off",
        "audit",
        "inspect",
        "query",
        "search",
        "find",
        "count",
        "list",
    ]

    def __init__(self):
        self.backend_path = Path(__file__).parent.parent.parent

    def analyze_command(self, command_path: Path) -> tuple[str, str, float]:
        """
        Analyze a command file to suggest categorization.

        Returns:
            Tuple of (suggested_category, reason, confidence)
        """
        try:
            content = command_path.read_text(encoding="utf-8")
            filename = command_path.stem.lower()

            # Score each category based on keywords
            scores = {
                "production": self._score_keywords(content, filename, self.PRODUCTION_KEYWORDS),
                "transitional": self._score_keywords(content, filename, self.TRANSITIONAL_KEYWORDS),
                "ephemeral": self._score_keywords(content, filename, self.EPHEMERAL_KEYWORDS),
            }

            # Additional heuristics
            scores = self._apply_heuristics(content, filename, scores)

            # Find best category
            best_category = max(scores, key=scores.get)
            confidence = scores[best_category]

            # Generate reason
            reason = self._generate_reason(content, filename, best_category, confidence)

            return best_category, reason, confidence

        except Exception as e:
            return "ephemeral", f"Error analyzing file: {e}", 0.1

    def _score_keywords(self, content: str, filename: str, keywords: list[str]) -> float:
        """Score content based on keyword matches."""
        score = 0.0
        content_lower = content.lower()

        # Check filename
        for keyword in keywords:
            if keyword in filename:
                score += 0.3

        # Check docstring/comments
        for keyword in keywords:
            if keyword in content_lower:
                score += 0.1

        return score

    def _apply_heuristics(self, content: str, filename: str, scores: dict[str, float]) -> dict[str, float]:
        """Apply additional heuristics to improve categorization."""

        # Import patterns
        if re.search(r"from apps\.\w+\.management\.base_migration import", content):
            scores["transitional"] += 0.5  # Uses migration base class

        if "BaseMigrationCommand" in content:
            scores["transitional"] += 0.5

        # Usage patterns
        if re.search(r"print\([^)]*debug", content, re.IGNORECASE):
            scores["ephemeral"] += 0.3

        if "import pdb" in content or "breakpoint()" in content:
            scores["ephemeral"] += 0.4

        # File characteristics
        if "TODO" in content or "FIXME" in content or "HACK" in content:
            scores["ephemeral"] += 0.2

        # Complex error handling suggests production
        if re.search(r"try:.*except.*:", content, re.DOTALL) and "logger" in content:
            scores["production"] += 0.3

        # Command help text analysis
        help_text = re.search(r'help\s*=\s*["\']([^"\']+)["\']', content)
        if help_text:
            help_content = help_text.group(1).lower()
            if any(word in help_content for word in ["migrate", "setup", "convert"]):
                scores["transitional"] += 0.2
            elif any(word in help_content for word in ["analyze", "debug", "test"]):
                scores["ephemeral"] += 0.2

        return scores

    def _generate_reason(self, content: str, filename: str, category: str, confidence: float) -> str:
        """Generate human-readable reason for categorization."""
        reasons = []

        # Filename analysis
        category_keywords = getattr(self, f"{category.upper()}_KEYWORDS")
        filename_matches = [kw for kw in category_keywords if kw in filename]
        if filename_matches:
            reasons.append(f"Filename contains: {', '.join(filename_matches)}")

        # Special patterns
        if "BaseMigrationCommand" in content:
            reasons.append("Uses BaseMigrationCommand (migration pattern)")
        if re.search(r"print\([^)]*debug", content, re.IGNORECASE):
            reasons.append("Contains debug print statements")
        if "import pdb" in content:
            reasons.append("Contains debugging imports")

        # Confidence indicator
        confidence_desc = "high" if confidence > 0.7 else "medium" if confidence > 0.4 else "low"

        reason_text = "; ".join(reasons) if reasons else "General content analysis"
        return f"{reason_text} (confidence: {confidence_desc})"

    def get_all_commands(self, app_name: str | None = None) -> list[Path]:
        """Get all management command files, optionally filtered by app."""
        commands = []
        apps_dir = self.backend_path / "apps"

        for app_dir in apps_dir.iterdir():
            if not app_dir.is_dir():
                continue
            if app_name and app_dir.name != app_name:
                continue

            commands_dir = app_dir / "management" / "commands"
            if not commands_dir.exists():
                continue

            # Get all .py files that aren't __init__.py and aren't in subdirectories
            for py_file in commands_dir.glob("*.py"):
                if py_file.name != "__init__.py":
                    commands.append(py_file)

        return commands

    def create_directory_structure(self, app_path: Path):
        """Create the categorized directory structure for an app."""
        commands_dir = app_path / "management" / "commands"

        for category in ["production", "transitional", "ephemeral"]:
            category_dir = commands_dir / category
            category_dir.mkdir(exist_ok=True)

            # Create __init__.py with documentation
            init_file = category_dir / "__init__.py"
            if not init_file.exists():
                init_content = self._get_init_content(category)
                init_file.write_text(init_content, encoding="utf-8")

    def _get_init_content(self, category: str) -> str:
        """Get the content for __init__.py files."""
        contents = {
            "production": '''"""
Production management commands.

Commands in this directory are for ongoing operational needs:
- User-facing operations
- Regular maintenance tasks
- Data processing workflows
- Reporting and analytics

All commands here must meet full code quality standards.
"""''',
            "transitional": '''"""
Transitional management commands.

Commands in this directory are for setup and migration tasks:
- Data migration scripts
- System initialization
- One-time setup operations
- Schema transformations

These commands are temporary but important, requiring good quality standards.
"""''',
            "ephemeral": '''"""
Ephemeral management commands.

Commands in this directory are for quick analysis and fixes:
- One-off debugging scripts
- Data exploration tools
- Experimental analysis
- Quick fixes and patches

Quality standards are relaxed for these commands to allow for rapid development.
They are excluded from type checking and strict linting.
"""''',
        }
        return contents[category]

    def move_command(self, command_path: Path, category: str, dry_run: bool = False) -> bool:
        """Move a command to the appropriate category directory."""
        app_path = command_path.parents[2]  # Go up from commands/ to app/

        # Create directory structure if needed
        if not dry_run:
            self.create_directory_structure(app_path)

        # Determine target path
        target_dir = app_path / "management" / "commands" / category
        target_path = target_dir / command_path.name

        if dry_run:
            print(f"Would move: {command_path} -> {target_path}")
            return True

        try:
            shutil.move(str(command_path), str(target_path))
            print(f"Moved: {command_path.name} -> {category}/")
            return True
        except Exception as e:
            print(f"Error moving {command_path}: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description="Move management commands to categorized directories")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be moved without actually moving")
    parser.add_argument("--app", type=str, help="Process only specific app (default: all apps)")
    parser.add_argument("--interactive", action="store_true", help="Ask for confirmation before moving each command")
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.3,
        help="Minimum confidence threshold for automatic moves (default: 0.3)",
    )

    args = parser.parse_args()

    categorizer = CommandCategorizer()

    # Get all commands
    commands = categorizer.get_all_commands(args.app)

    if not commands:
        print("No management commands found.")
        return

    print(f"Found {len(commands)} management commands")
    if args.dry_run:
        print("DRY RUN MODE - No files will be moved")
    print("-" * 60)

    # Process each command
    moved_count = 0
    skipped_count = 0

    for command_path in commands:
        app_name = command_path.parents[2].name
        category, reason, confidence = categorizer.analyze_command(command_path)

        print(f"\\n{app_name}/{command_path.name}")
        print(f"  Suggested category: {category}")
        print(f"  Reason: {reason}")
        print(f"  Confidence: {confidence:.2f}")

        should_move = confidence >= args.confidence_threshold

        if args.interactive:
            if confidence < args.confidence_threshold:
                print(f"  ⚠️  Low confidence ({confidence:.2f})")

            try:
                response = (
                    input(f"  Move to {category}/? [y/N] or change category [P/T/E/s(skip)/q(quit)]: ").strip().upper()
                )
                if response == "Q":
                    break
                elif response == "S":
                    should_move = False
                elif response == "P":
                    category = "production"
                    should_move = True
                elif response == "T":
                    category = "transitional"
                    should_move = True
                elif response == "E":
                    category = "ephemeral"
                    should_move = True
                elif response in ["Y", "YES"]:
                    should_move = True
                else:
                    should_move = False
            except (EOFError, KeyboardInterrupt):
                print("\nInteractive mode interrupted. Using automatic categorization.")
                should_move = confidence >= args.confidence_threshold

        if should_move:
            if categorizer.move_command(command_path, category, args.dry_run):
                moved_count += 1
            else:
                skipped_count += 1
        else:
            print("  Skipped (confidence too low or user choice)")
            skipped_count += 1

    print(f"\\n{'DRY RUN ' if args.dry_run else ''}Summary:")
    print(f"  Commands that would be moved: {moved_count}")
    print(f"  Commands skipped: {skipped_count}")

    if not args.dry_run and moved_count > 0:
        print(f"\\n✅ Successfully moved {moved_count} commands!")
        print("Next steps:")
        print("1. Run the validation script to verify structure")
        print("2. Run quality checks to see the effect on linting")
        print("3. Update any import statements if needed")


if __name__ == "__main__":
    main()
