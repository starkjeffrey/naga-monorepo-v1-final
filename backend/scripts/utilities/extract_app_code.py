#!/usr/bin/env python3
"""Extract all app code for review.

This script walks through all apps/ directories and extracts Python code
with clear file separators for easy navigation and analysis.

Usage:
    python scripts/extract_app_code.py              # Extract all apps
    python scripts/extract_app_code.py <app_name>   # Extract specific app

Example:
    python scripts/extract_app_code.py
    python scripts/extract_app_code.py attendance
"""

import os
import sys
from datetime import datetime
from pathlib import Path


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def find_files_to_include(directory: Path) -> list[Path]:
    """Find all .py, .html, and .css files in a directory recursively."""
    extensions = {".py", ".html", ".css"}
    files: list[Path] = []

    if not directory.exists():
        return files

    for file_path in directory.rglob("*"):
        if file_path.is_file() and file_path.suffix in extensions:
            # Skip __pycache__ directories, .pyc files, and migrations
            if "__pycache__" not in str(file_path) and "migrations/" not in str(file_path):
                files.append(file_path)

    return sorted(files)


def read_file_content(file_path: Path) -> str:
    """Read file content safely."""
    try:
        with open(file_path, encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, encoding="latin-1") as f:
                return f.read()
        except Exception as e:
            return f"[ERROR: Could not read file - {e}]"
    except Exception as e:
        return f"[ERROR: Could not read file - {e}]"


def create_file_separator(file_path: Path, relative_path: Path, section_type: str = "") -> str:
    """Create a clear separator line for each file."""
    separator = "=" * 80

    # Determine file type and description
    file_type = ""
    description = ""

    if file_path.suffix == ".py":
        if "models.py" in str(file_path):
            file_type = "🏗️  MODELS"
            description = "Data models and database schema"
        elif "views.py" in str(file_path):
            file_type = "🌐 VIEWS"
            description = "View logic and request handling"
        elif "forms.py" in str(file_path):
            file_type = "📝 FORMS"
            description = "Form definitions and validation"
        elif "admin.py" in str(file_path):
            file_type = "⚙️  ADMIN"
            description = "Django admin configuration"
        elif "urls.py" in str(file_path):
            file_type = "🔗 URLS"
            description = "URL routing configuration"
        elif "apps.py" in str(file_path):
            file_type = "📦 APP CONFIG"
            description = "Django app configuration"
        elif "tests.py" in str(file_path) or "/tests/" in str(file_path):
            file_type = "🧪 TESTS"
            description = "Test cases and test utilities"
        elif "services.py" in str(file_path):
            file_type = "🔧 SERVICES"
            description = "Business logic and service layer"
        elif "serializers.py" in str(file_path):
            file_type = "📊 SERIALIZERS"
            description = "API serialization logic"
        elif "migrations/" in str(file_path):
            file_type = "🔄 MIGRATION"
            description = "Database migration"
        elif "__init__.py" in str(file_path):
            file_type = "📋 INIT"
            description = "Python package initialization"
        else:
            file_type = "🐍 PYTHON"
            description = "Python module"
    elif file_path.suffix == ".html":
        file_type = "🌐 TEMPLATE"
        description = "HTML template"
    elif file_path.suffix == ".css":
        file_type = "🎨 STYLES"
        description = "CSS stylesheet"

    # Add section type if provided (for base models vs app files)
    section_prefix = f"[{section_type}] " if section_type else ""

    return f"\n{separator}\n{section_prefix}{file_type}: {relative_path}\n{description}\n{separator}\n"


def extract_base_models(project_root: Path) -> list[tuple[Path, Path]]:
    """Extract base models from apps/common/models.py."""
    base_models_files: list[tuple[Path, Path]] = []

    # Look for common base models
    common_models = project_root / "apps" / "common" / "models.py"
    if common_models.exists():
        relative_path = common_models.relative_to(project_root)
        base_models_files.append((common_models, relative_path))

    # Also include common __init__.py if it exists
    common_init = project_root / "apps" / "common" / "__init__.py"
    if common_init.exists():
        relative_path = common_init.relative_to(project_root)
        base_models_files.append((common_init, relative_path))

    return base_models_files


def extract_app_code(app_name: str) -> None:
    """Extract code from base models and specified app."""
    project_root = get_project_root()

    # Validate app name
    app_dir = project_root / "apps" / app_name
    if not app_dir.exists():
        apps_dir = project_root / "apps"
        if apps_dir.exists():
            for item in sorted(apps_dir.iterdir()):
                if item.is_dir() and not item.name.startswith("."):
                    pass
        sys.exit(1)

    # Create output directory if it doesn't exist
    output_dir = project_root / "project-docs" / "working-folder"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create output filename
    output_file = output_dir / f"{app_name}_code_review.txt"

    # Collect all files
    all_files: list[tuple[Path, Path]] = []

    # 1. Add base models first
    base_model_files = extract_base_models(project_root)
    all_files.extend(base_model_files)

    # 2. Add app files
    app_files = find_files_to_include(app_dir)
    for file_path in app_files:
        relative_path = file_path.relative_to(project_root)
        all_files.append((file_path, relative_path))

    # 3. Write everything to output file

    with open(output_file, "w", encoding="utf-8") as output:
        # Write code review preamble
        preamble = """Act as a senior Python/Django software engineer conducting a code review. Your feedback should be direct, concise, and targeted at a junior developer for improvement. Do not offer compliments.

Analyze the following code and provide a critique focused on actionable feedback. Structure your response with these specific markdown headings:

## Architectural & Design Flaws
Point out high-level weaknesses, incorrect design patterns, poor separation of concerns, or fundamental issues with the code's structure.

## Performance & Optimization
Identify performance bottlenecks, inefficient database queries (N+1 problems), slow loops, and other areas that would perform poorly under load.

## Security Vulnerabilities
Highlight any potential security risks, such as SQL injection, XSS, CSRF vulnerabilities, insecure handling of secrets, or other common web application security flaws.

## Code Refinements & Best Practices
Provide suggestions for more "Pythonic" or "Django-like" code, violations of the DRY (Don't Repeat Yourself) principle, unclear variable names, and areas where readability or maintainability could be improved.

"""
        output.write(preamble)

        # Write header
        header = f"""
{"=" * 80}
🚀 CODE REVIEW EXTRACT
{"=" * 80}
App: {app_name}
Generated: {Path.cwd()}
Date: $(date)

This file contains all Python (.py), HTML (.html), and CSS (.css) files
from the base models and the {app_name} app for code review purposes.

Total files included: {len(all_files)}
{"=" * 80}

📋 TABLE OF CONTENTS:
1. BASE MODELS - Common models and utilities
2. APP CODE - {app_name.upper()} app implementation

{"=" * 80}
"""
        output.write(header)

        # Separate base models from app files
        base_files: list[tuple[Path, Path]] = [(f, r) for f, r in all_files if "apps/common" in str(r)]
        app_filtered_files: list[tuple[Path, Path]] = [(f, r) for f, r in all_files if "apps/common" not in str(r)]

        # Write base models section
        if base_files:
            section_header = f"""
{"#" * 80}
📦 SECTION 1: BASE MODELS & COMMON UTILITIES
{"#" * 80}
This section contains the foundational models and utilities used across
the entire application. These provide common functionality like
timestamps, soft deletes, and audit trails.
{"#" * 80}
"""
            output.write(section_header)

            for file_path, relative_path in base_files:
                # Write file separator with BASE MODELS section type
                separator = create_file_separator(file_path, relative_path, "BASE MODELS")
                output.write(separator)

                # Write file content
                content = read_file_content(file_path)
                output.write(content)
                output.write("\n\n")

        # Write app files section
        if app_filtered_files:
            section_header = f"""
{"#" * 80}
📱 SECTION 2: {app_name.upper()} APP IMPLEMENTATION
{"#" * 80}
This section contains all the implementation files for the {app_name} app,
including models, views, forms, tests, and other components.
{"#" * 80}
"""
            output.write(section_header)

            for file_path, relative_path in app_filtered_files:
                # Write file separator with APP section type
                separator = create_file_separator(file_path, relative_path, f"{app_name.upper()} APP")
                output.write(separator)

                # Write file content
                content = read_file_content(file_path)
                output.write(content)
                output.write("\n\n")

    # Show file breakdown
    len([f for f, _ in all_files if f.suffix == ".py"])
    len([f for f, _ in all_files if f.suffix == ".html"])
    len([f for f, _ in all_files if f.suffix == ".css"])


def extract_all_apps_code() -> None:
    """Extract code from ALL apps into a single file."""
    project_root = get_project_root()
    apps_dir = project_root / "apps"

    if not apps_dir.exists():
        print("❌ Error: Directory 'apps' not found!")
        sys.exit(1)

    # Get all app directories
    app_dirs = []
    for item in sorted(apps_dir.iterdir()):
        if item.is_dir() and not item.name.startswith(".") and not item.name.startswith("__"):
            app_dirs.append(item.name)

    print(f"📁 Found {len(app_dirs)} apps in apps/ directory")

    # Create output directory if it doesn't exist
    output_dir = project_root / "project-docs" / "working-folder"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"all_apps_code_extract_{timestamp}.txt"

    # Collect all files
    all_files: list[tuple[Path, Path]] = []

    # Walk through each app
    for app_name in app_dirs:
        app_dir = apps_dir / app_name
        app_files = find_files_to_include(app_dir)
        for file_path in app_files:
            relative_path = file_path.relative_to(project_root)
            all_files.append((file_path, relative_path))

    print(f"📄 Found {len(all_files)} total files to extract")

    # Write everything to output file
    with open(output_file, "w", encoding="utf-8") as output:
        # Write header
        header = f"""{"#" * 80}
# NAGA SIS - ALL APPS CODE EXTRACT
{"#" * 80}
# Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
# Total apps: {len(app_dirs)}
# Total files: {len(all_files)}
# Apps included: {", ".join(app_dirs)}
{"#" * 80}

"""
        output.write(header)

        # Process files grouped by app
        for app_name in app_dirs:
            app_files = [(f, r) for f, r in all_files if f"apps/{app_name}/" in str(r)]

            if app_files:
                # Write app section header
                app_header = f"""
{"=" * 80}
📦 APP: {app_name.upper()}
{"=" * 80}
Files in this app: {len(app_files)}
{"=" * 80}
"""
                output.write(app_header)

                # Sort files by type (models first, then views, etc.)
                def sort_key(item: tuple[Path, Path]) -> int:
                    path = str(item[1])
                    if "models.py" in path:
                        return 0
                    elif "admin.py" in path:
                        return 1
                    elif "forms.py" in path:
                        return 2
                    elif "views.py" in path:
                        return 3
                    elif "urls.py" in path:
                        return 4
                    elif "services.py" in path:
                        return 5
                    elif "serializers.py" in path:
                        return 6
                    elif "apps.py" in path:
                        return 7
                    elif "__init__.py" in path:
                        return 8
                    elif "tests" in path:
                        return 9
                    else:
                        return 10

                app_files.sort(key=sort_key)

                for file_path, relative_path in app_files:
                    # Write file separator
                    separator = create_file_separator(file_path, relative_path, app_name.upper())
                    output.write(separator)

                    # Write file content with line numbers
                    content = read_file_content(file_path)
                    lines = content.split("\n")
                    for i, line in enumerate(lines, 1):
                        output.write(f"{i:4d}→{line}\n")
                    output.write("\n")

    # Print summary
    print("\n✅ Extraction complete!")
    print(f"📄 Output written to: {output_file}")
    print(f"📊 File size: {os.path.getsize(output_file):,} bytes")

    # Print app summary
    print("\n📋 Files per app:")
    for app_name in app_dirs:
        app_files = [(f, r) for f, r in all_files if f"apps/{app_name}/" in str(r)]
        print(f"   {app_name:20s}: {len(app_files):3d} files")


def main():
    """Main entry point."""
    if len(sys.argv) == 1:
        # No arguments - extract all apps
        extract_all_apps_code()
    elif len(sys.argv) == 2:
        # One argument - extract specific app
        app_name = sys.argv[1]
        extract_app_code(app_name)
    else:
        print("Usage: python scripts/extract_app_code.py [app_name]")
        print("  No arguments: Extract all apps")
        print("  With app_name: Extract specific app")
        sys.exit(1)


if __name__ == "__main__":
    main()
