#!/usr/bin/env python3
"""Code Packet Generator for LLM Review.

This script extracts app code and creates a single output file containing
the LLM preamble plus all code with proper file separators. It supports
multiple apps and generates output ready for LLM consumption.

Usage:
    python scripts/gemini_code_review.py <app1> [app2] [app3] ...
    python scripts/gemini_code_review.py academic
    python scripts/gemini_code_review.py academic finance scheduling

The script will:
1. Extract code from apps/common (base models) and specified apps
2. Prepend LLM preamble with senior Python engineer persona
3. Add file separators and organize code by app
4. Save complete packet to backend/scratchpad/temp_code_packet/
"""

import sys
from datetime import datetime
from pathlib import Path


def get_project_root() -> Path:
    """Get the project root directory."""
    # The script is in backend/scripts/development/, so go up two levels to get to backend/
    return Path(__file__).parent.parent.parent


def find_files_to_include(directory: Path) -> list[Path]:
    """Find all .py, .html, and .css files in a directory recursively."""
    extensions = {".py", ".html", ".css"}
    files: list[Path] = []

    if not directory.exists():
        return files

    for file_path in directory.rglob("*"):
        if file_path.is_file() and file_path.suffix in extensions:
            # Skip __pycache__ directories, .pyc files, migrations, and tests
            path_str = str(file_path)
            if (
                "__pycache__" not in path_str
                and "migrations/" not in path_str
                and not path_str.endswith("test.py")
                and "/tests/" not in path_str
                and "factories.py" not in path_str
            ):
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
        elif "services.py" in str(file_path):
            file_type = "🔧 SERVICES"
            description = "Business logic and service layer"
        elif "serializers.py" in str(file_path):
            file_type = "📊 SERIALIZERS"
            description = "API serialization logic"
        elif "constants.py" in str(file_path):
            file_type = "🔢 CONSTANTS"
            description = "Application constants and configuration"
        elif "enums.py" in str(file_path):
            file_type = "📋 ENUMS"
            description = "Enumeration definitions"
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

    # Add section type if provided
    section_prefix = f"[{section_type}] " if section_type else ""

    return f"\n{separator}\n{section_prefix}{file_type}: {relative_path}\n{description}\n{separator}\n"


def extract_base_models(project_root: Path) -> list[tuple[Path, Path]]:
    """Extract essential files from apps/common."""
    base_files: list[tuple[Path, Path]] = []

    # Essential common files to include
    common_files_to_include = [
        "models.py",
        "constants.py",
        "enums.py",
        "__init__.py",
    ]

    common_dir = project_root / "apps" / "common"
    for filename in common_files_to_include:
        file_path = common_dir / filename
        if file_path.exists():
            relative_path = file_path.relative_to(project_root)
            base_files.append((file_path, relative_path))

    return base_files


def create_gemini_preamble() -> str:
    """Create the Gemini CLI preamble for senior Python engineer review."""
    return (
        "You are a senior Python engineer reviewing code from a junior developer. "
        "Your goal is to provide a constructive, mentoring code review that helps "
        "them improve their skills. Your tone must be helpful and educational, not critical.\n\n"
        "Please analyze the following Django application code. Structure your review "
        "as a list of actionable suggestions. For each suggestion, you must provide:\n"
        "1. A clear explanation of the issue (the 'why').\n"
        "2. A 'before' and 'after' code snippet to illustrate the improvement (the 'how').\n\n"
        "Focus your review on these key aspects:\n"
        "* **Performance:** Identify any bottlenecks or opportunities for optimization, "
        "especially Django ORM N+1 queries, inefficient database operations, and slow loops.\n"
        "* **Django Best Practices:** Recommend Django-specific patterns (model managers, "
        "custom querysets, proper use of select_related/prefetch_related, admin customizations).\n"
        "* **Pythonic Style:** Recommend more idiomatic and elegant Python patterns "
        "(list comprehensions, context managers, generator expressions, proper exception handling).\n"
        "* **Security:** Identify potential security vulnerabilities (SQL injection, XSS, "
        "CSRF, permission bypasses, data exposure).\n"
        "* **Architecture:** Evaluate separation of concerns, service layer usage, model design, "
        "and overall code organization.\n"
        "* **Simplicity & Readability:** Suggest improvements to make the code easier to understand "
        "and maintain.\n\n"
        "Pay special attention to:\n"
        "- Django model design and relationships\n"
        "- Database query optimization\n"
        "- Admin interface customizations\n"
        "- Service layer implementation\n"
        "- Error handling and validation\n"
        "- Code organization and modularity\n\n"
        "Conclude your review with some brief, encouraging words about the developer's progress.\n\n"
        "Here is the code to review:"
    )


def extract_multiple_apps_code(app_names: list[str]) -> str:
    """Extract code from base models and specified apps."""
    project_root = get_project_root()

    # Validate all app names
    valid_apps = []
    for app_name in app_names:
        app_dir = project_root / "apps" / app_name
        if not app_dir.exists():
            print(f"❌ App '{app_name}' not found in apps/ directory")
            continue
        valid_apps.append(app_name)

    if not valid_apps:
        print("❌ No valid apps provided")
        sys.exit(1)

    # Create output directory
    output_dir = project_root / "scratchpad" / "temp_code_packet"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate distinctive output filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    apps_suffix = "_".join(valid_apps)
    output_file = output_dir / f"code_packet_{apps_suffix}_{timestamp}.txt"

    # Collect all files
    all_files: list[tuple[Path, Path]] = []

    # 1. Add base models first (always include common)
    base_model_files = extract_base_models(project_root)
    all_files.extend(base_model_files)

    # 2. Add files from each app
    for app_name in valid_apps:
        app_dir = project_root / "apps" / app_name
        app_files = find_files_to_include(app_dir)
        for file_path in app_files:
            relative_path = file_path.relative_to(project_root)
            all_files.append((file_path, relative_path))

    # 3. Write LLM preamble + code to file
    with open(output_file, "w", encoding="utf-8") as output:
        # Write LLM preamble first
        preamble = create_gemini_preamble()
        output.write(preamble)
        output.write("\n\n")

        # Write header
        header = f"""{"=" * 80}
🚀 DJANGO CODE EXTRACT
{"=" * 80}
Apps: {", ".join(valid_apps)}
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Total files: {len(all_files)}

This file contains all Python (.py), HTML (.html), and CSS (.css) files
from apps/common and the specified apps.

Apps included:
{chr(10).join(f"  • {app}" for app in valid_apps)}
{"=" * 80}

📋 CONTENTS:
1. BASE MODELS & UTILITIES (apps/common)
2. APP IMPLEMENTATIONS ({", ".join(valid_apps)})

{"=" * 80}
"""
        output.write(header)

        # Separate base files from app files
        base_files: list[tuple[Path, Path]] = [(f, r) for f, r in all_files if "apps/common" in str(r)]
        app_filtered_files: list[tuple[Path, Path]] = [(f, r) for f, r in all_files if "apps/common" not in str(r)]

        # Write base models section
        if base_files:
            section_header = f"""
{"#" * 80}
📦 SECTION 1: BASE MODELS & COMMON UTILITIES
{"#" * 80}
This section contains foundational models and utilities used across
the application. These provide common functionality like timestamps,
soft deletes, audit trails, and shared constants.
{"#" * 80}
"""
            output.write(section_header)

            for file_path, relative_path in base_files:
                separator = create_file_separator(file_path, relative_path, "COMMON")
                output.write(separator)
                content = read_file_content(file_path)
                output.write(content)
                output.write("\n\n")

        # Write app files section
        if app_filtered_files:
            section_header = f"""
{"#" * 80}
📱 SECTION 2: APPLICATION IMPLEMENTATIONS
{"#" * 80}
This section contains all implementation files for the specified apps:
{", ".join(valid_apps)}
{"#" * 80}
"""
            output.write(section_header)

            current_app = None
            for file_path, relative_path in app_filtered_files:
                # Detect app changes for better organization
                app_from_path = str(relative_path).split("/")[1] if "/" in str(relative_path) else "unknown"
                if app_from_path != current_app:
                    current_app = app_from_path
                    app_divider = f"""
{"~" * 60}
📂 {current_app.upper()} APP
{"~" * 60}
"""
                    output.write(app_divider)

                separator = create_file_separator(file_path, relative_path, f"{app_from_path.upper()}")
                output.write(separator)
                content = read_file_content(file_path)
                output.write(content)
                output.write("\n\n")

    # File statistics
    py_files = len([f for f, _ in all_files if f.suffix == ".py"])
    html_files = len([f for f, _ in all_files if f.suffix == ".html"])
    css_files = len([f for f, _ in all_files if f.suffix == ".css"])

    print("✅ Code packet created successfully!")
    print(f"   📂 Output: {output_file}")
    print(f"   📊 Files: {py_files} Python, {html_files} HTML, {css_files} CSS")
    print(f"   🏗️  Apps: {', '.join(valid_apps)} + common")

    return str(output_file)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/gemini_code_review.py <app1> [app2] [app3] ...")
        print("Example: python scripts/gemini_code_review.py academic finance")
        sys.exit(1)

    app_names = sys.argv[1:]

    print("🚀 Code Packet Generator")
    print(f"📂 Apps to extract: {', '.join(app_names)}")
    print("=" * 60)

    try:
        # Extract code from apps and write to temp_code_packet
        output_file = extract_multiple_apps_code(app_names)

        print(f"\n💡 Code packet ready at: {output_file}")
        print("🎯 Contains LLM preamble + code with file separators")

    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
