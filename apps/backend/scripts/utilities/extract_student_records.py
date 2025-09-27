#!/usr/bin/env python3
"""Extract Student Records functionality files for review.

This script copies all files involved in the "Student Records" sidebar functionality,
generating one .txt file that can be reviewed. It includes the complete file chain
from sidebar link through to the final table rendering.

Usage:
    python scripts/extract_student_records.py

Files included:
- HTML Templates: sidebar, base templates, CRUD templates, student-specific templates
- Python Files: URLs, views, and related logic
- CSS Files: Project styles, layout, and main stylesheets
- JavaScript: Embedded functionality for table management

The output contains the complete implementation of the Student Records feature.
"""

from datetime import datetime
from pathlib import Path


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


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


def create_file_separator(file_path: Path, section_type: str = "") -> str:
    """Create a clear separator line for each file."""
    separator = "=" * 80

    # Determine file type and description
    file_type = ""
    description = ""

    if file_path.suffix == ".py":
        if "urls.py" in str(file_path):
            file_type = "🔗 URLS"
            description = "URL routing configuration"
        elif "views" in str(file_path):
            file_type = "🌐 VIEWS"
            description = "View logic and request handling"
        else:
            file_type = "🐍 PYTHON"
            description = "Python module"
    elif file_path.suffix == ".html":
        if "sidebar" in str(file_path):
            file_type = "📋 SIDEBAR"
            description = "Navigation sidebar template"
        elif "base" in str(file_path):
            file_type = "🏗️  BASE TEMPLATE"
            description = "Base layout template"
        elif "crud" in str(file_path):
            file_type = "📊 CRUD TEMPLATE"
            description = "CRUD framework template"
        elif "student_profile" in str(file_path):
            file_type = "👥 STUDENT TEMPLATE"
            description = "Student-specific template"
        else:
            file_type = "🌐 TEMPLATE"
            description = "HTML template"
    elif file_path.suffix == ".css":
        file_type = "🎨 STYLES"
        description = "CSS stylesheet"

    # Add section type if provided
    section_prefix = f"[{section_type}] " if section_type else ""

    return f"\n{separator}\n{section_prefix}{file_type}: {file_path}\n{description}\n{separator}\n"


def extract_student_records_files() -> None:
    """Extract all Student Records functionality files."""
    project_root = get_project_root()

    # Define all the files involved in Student Records functionality
    student_records_files = [
        # HTML Templates
        "templates/components/sidebar.html",
        "templates/common/crud/list.html",
        "templates/base_crud.html",
        "templates/common/crud/table.html",
        "templates/people/student_profile_list.html",
        "templates/base.html",
        # Python Files
        "apps/people/urls.py",
        "apps/people/views/student_profile_crud.py",
        # CSS Files
        "static/css/project.css",
        "static/css/layout.css",
        "static/css/main.css",
    ]

    # Create output directory if it doesn't exist
    output_dir = project_root / "project-docs" / "working-folder"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"student_records_functionality_{timestamp}.txt"

    # Collect existing files
    existing_files = []
    missing_files = []

    for file_path_str in student_records_files:
        file_path = project_root / file_path_str
        if file_path.exists():
            existing_files.append((file_path, file_path_str))
        else:
            missing_files.append(file_path_str)

    # Write everything to output file
    with open(output_file, "w", encoding="utf-8") as output:
        # Write code review preamble
        preamble = """Act as a senior Python/Django software engineer conducting a code review. Your feedback should
        be direct, concise, and targeted at a junior developer for improvement. Do not offer compliments.  # noqa: E501

Analyze the following Student Records functionality implementation and provide a critique focused on actionable
feedback. Structure your response with these specific markdown headings:  # noqa: E501

## Architectural & Design Flaws
Point out high-level weaknesses, incorrect design patterns, poor separation of concerns, or fundamental issues with the
code's structure.  # noqa: E501

## Performance & Optimization
Identify performance bottlenecks, inefficient database queries (N+1 problems), slow loops, and other areas that would
perform poorly under load.  # noqa: E501

## Security Vulnerabilities
Highlight any potential security risks, such as SQL injection, XSS, CSRF vulnerabilities, insecure handling of secrets,
or other common web application security flaws.  # noqa: E501

## Code Refinements & Best Practices
Provide suggestions for more "Pythonic" or "Django-like" code, violations of the DRY (Don't Repeat Yourself) principle,
unclear variable names, and areas where readability or maintainability could be improved.  # noqa: E501

## UI/UX & Frontend Issues
Analyze the template structure, HTML semantics, CSS organization, JavaScript implementation, and overall user
experience patterns.  # noqa: E501

"""
        output.write(preamble)

        # Write header
        header = f"""
{"=" * 80}
🚀 STUDENT RECORDS FUNCTIONALITY EXTRACT
{"=" * 80}
Feature: Student Records (Sidebar → List View → Table)
Generated: {project_root}
Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

This file contains all files involved in the "Student Records" functionality
from the sidebar navigation through to the complete student profile list view.

Files included: {len(existing_files)}
Missing files: {len(missing_files)}
{"=" * 80}

📋 FUNCTIONALITY OVERVIEW:
The Student Records feature provides:
- 📋 Sidebar navigation link
- 👥 Comprehensive student profile list with filtering
- 📊 Statistics dashboard (total, active, graduated, monks, transfers)
- 🔍 Advanced search and filtering capabilities
- 📤 Export functionality (CSV/XLSX)
- 🔧 Column management (show/hide, reorder)
- 📱 Responsive design for mobile devices
- ⚡ HTMX-powered real-time interactions

{"=" * 80}

📂 FILE ORGANIZATION:
1. NAVIGATION - Sidebar and base layout
2. CRUD FRAMEWORK - Reusable list/table components
3. STUDENT VIEWS - Student-specific logic and templates
4. STYLING - CSS for visual presentation

{"=" * 80}
"""
        output.write(header)

        # Show missing files if any
        if missing_files:
            missing_section = """
⚠️  MISSING FILES:
The following files were not found:
"""
            for missing_file in missing_files:
                missing_section += f"- {missing_file}\n"
            missing_section += f"\n{'=' * 80}\n"
            output.write(missing_section)

        # Organize files by category
        navigation_files = [(f, p) for f, p in existing_files if any(x in p for x in ["sidebar", "base.html"])]
        crud_files = [(f, p) for f, p in existing_files if "crud" in p]
        student_files = [(f, p) for f, p in existing_files if any(x in p for x in ["people", "student_profile"])]
        css_files = [(f, p) for f, p in existing_files if p.endswith(".css")]

        # Write sections
        sections = [
            (
                "NAVIGATION & BASE LAYOUT",
                navigation_files,
                "Core layout and navigation components",
            ),
            ("CRUD FRAMEWORK", crud_files, "Reusable CRUD list and table components"),
            (
                "STUDENT VIEWS & LOGIC",
                student_files,
                "Student-specific views, URLs, and templates",
            ),
            ("STYLING & CSS", css_files, "Visual styling and layout CSS"),
        ]

        for section_name, section_files, section_description in sections:
            if section_files:
                section_header = f"""
{"#" * 80}
📂 SECTION: {section_name}
{"#" * 80}
{section_description}

Files in this section: {len(section_files)}
{"#" * 80}
"""
                output.write(section_header)

                for file_path, _relative_path in section_files:
                    # Write file separator
                    separator = create_file_separator(file_path, section_name)
                    output.write(separator)

                    # Write file content
                    content = read_file_content(file_path)
                    output.write(content)
                    output.write("\n\n")

        # Write summary footer
        footer = f"""
{"=" * 80}
📊 EXTRACT SUMMARY
{"=" * 80}
Total files processed: {len(existing_files)}
- HTML Templates: {len([f for f, p in existing_files if p.endswith(".html")])}
- Python Files: {len([f for f, p in existing_files if p.endswith(".py")])}
- CSS Files: {len([f for f, p in existing_files if p.endswith(".css")])}

Missing files: {len(missing_files)}

The Student Records functionality represents a complete CRUD implementation
with advanced features like real-time search, export capabilities, and
responsive design. Review focus should be on performance, security, and
maintainability of this user-facing feature.
{"=" * 80}
"""
        output.write(footer)

    print(f"✅ Student Records functionality extracted to: {output_file}")
    print(f"📁 Files processed: {len(existing_files)}")
    if missing_files:
        print(f"⚠️  Missing files: {len(missing_files)}")
        for missing in missing_files:
            print(f"   - {missing}")


def main():
    """Main entry point."""
    extract_student_records_files()


if __name__ == "__main__":
    main()
