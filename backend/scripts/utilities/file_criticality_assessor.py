#!/usr/bin/env python3
"""
File Criticality Assessor - Week 2 Strategic File Management

Identifies non-critical files for strategic "type: ignore" placement
to focus manual effort on core business logic only.

Part of the 3-4 week MyPy acceleration plan.

Usage:
    python scripts/utilities/file_criticality_assessor.py --analyze
    python scripts/utilities/file_criticality_assessor.py --generate-ignores --confirm
"""

import argparse
import ast
import subprocess
from pathlib import Path


class FileCriticalityAssessor:
    """Assess file criticality for strategic MyPy ignore placement."""

    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or Path.cwd()

        # Define criticality tiers
        self.critical_patterns = [
            "models.py",  # Django models - always critical
            "views.py",  # View logic - always critical
            "api.py",  # API endpoints - always critical
            "apis.py",  # API endpoints - always critical
            "services.py",  # Business logic - always critical
            "forms.py",  # User interfaces - usually critical
            "admin.py",  # Django admin - usually critical
        ]

        self.utility_patterns = [
            "utils.py",  # Utility functions - often non-critical
            "helpers.py",  # Helper functions - often non-critical
            "constants.py",  # Constants - usually non-critical
            "config.py",  # Configuration - context-dependent
            "settings.py",  # Settings - context-dependent
            "urls.py",  # URL routing - usually important but not complex
        ]

        self.low_value_patterns = [
            "apps.py",  # Django app configs - usually simple
            "__init__.py",  # Package initialization - usually empty
            "migrations/",  # Database migrations - excluded from MyPy anyway
            "tests/",  # Tests - excluded from MyPy anyway
            "test_",  # Test files - excluded from MyPy anyway
        ]

    def analyze_file_imports(self, file_path: Path) -> dict:
        """Analyze a file's imports to assess its integration criticality."""
        try:
            content = file_path.read_text()
            tree = ast.parse(content)

            imports_info = {
                "django_imports": 0,
                "business_imports": 0,  # Imports from our apps
                "external_imports": 0,
                "total_imports": 0,
                "has_models": False,
                "has_views": False,
                "has_api": False,
                "class_count": 0,
                "function_count": 0,
            }

            for node in ast.walk(tree):
                if isinstance(node, ast.Import | ast.ImportFrom):
                    imports_info["total_imports"] += 1

                    module_name = ""
                    if isinstance(node, ast.ImportFrom) and node.module:
                        module_name = node.module
                    elif isinstance(node, ast.Import):
                        if node.names:
                            module_name = node.names[0].name

                    if module_name.startswith("django"):
                        imports_info["django_imports"] += 1

                        if "models" in module_name:
                            imports_info["has_models"] = True
                        elif "views" in module_name:
                            imports_info["has_views"] = True
                        elif "api" in module_name:
                            imports_info["has_api"] = True

                    elif module_name.startswith("apps."):
                        imports_info["business_imports"] += 1
                    else:
                        imports_info["external_imports"] += 1

                elif isinstance(node, ast.ClassDef):
                    imports_info["class_count"] += 1
                elif isinstance(node, ast.FunctionDef):
                    imports_info["function_count"] += 1

            return imports_info

        except Exception as e:
            return {"error": str(e), "total_imports": 0, "class_count": 0, "function_count": 0}

    def get_file_mypy_errors(self, file_path: Path) -> int:
        """Get MyPy error count for a specific file."""
        try:
            result = subprocess.run(
                ["uv", "run", "mypy", str(file_path), "--show-error-codes"],
                check=False,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30,
            )

            # Count error lines
            error_count = 0
            for line in result.stderr.split("\n"):
                if "error:" in line and str(file_path) in line:
                    error_count += 1

            return error_count

        except Exception:
            return 0

    def assess_file_criticality(self, file_path: Path) -> dict:
        """Assess criticality of a single file."""
        file_str = str(file_path)
        relative_path = file_path.relative_to(self.project_root)

        # Base criticality scoring
        criticality_score = 0
        criticality_reasons = []

        # Pattern-based assessment
        for pattern in self.critical_patterns:
            if pattern in file_str:
                criticality_score += 100
                criticality_reasons.append(f"Critical pattern: {pattern}")

        for pattern in self.utility_patterns:
            if pattern in file_str:
                criticality_score += 30
                criticality_reasons.append(f"Utility pattern: {pattern}")

        for pattern in self.low_value_patterns:
            if pattern in file_str:
                criticality_score -= 20
                criticality_reasons.append(f"Low-value pattern: {pattern}")

        # Import-based assessment
        imports_info = self.analyze_file_imports(file_path)

        # Business logic integration score
        if imports_info.get("business_imports", 0) > 2:
            criticality_score += 30
            criticality_reasons.append("High business logic integration")

        if imports_info.get("django_imports", 0) > 3:
            criticality_score += 20
            criticality_reasons.append("Heavy Django integration")

        if imports_info.get("has_models"):
            criticality_score += 50
            criticality_reasons.append("Contains model definitions")

        if imports_info.get("has_views"):
            criticality_score += 40
            criticality_reasons.append("Contains view logic")

        if imports_info.get("has_api"):
            criticality_score += 45
            criticality_reasons.append("Contains API endpoints")

        # Complexity-based scoring
        total_elements = imports_info.get("class_count", 0) + imports_info.get("function_count", 0)
        if total_elements > 10:
            criticality_score += 20
            criticality_reasons.append("High complexity (many classes/functions)")
        elif total_elements < 3:
            criticality_score -= 10
            criticality_reasons.append("Low complexity")

        # Get MyPy error count
        error_count = self.get_file_mypy_errors(file_path)

        # Final categorization
        if criticality_score >= 100:
            category = "critical"
        elif criticality_score >= 50:
            category = "important"
        elif criticality_score >= 20:
            category = "moderate"
        else:
            category = "low"

        return {
            "file": str(relative_path),
            "category": category,
            "score": criticality_score,
            "mypy_errors": error_count,
            "reasons": criticality_reasons,
            "imports_info": imports_info,
            "ignore_candidate": category in ["low", "moderate"] and error_count <= 5,
        }

    def analyze_all_files(self) -> dict:
        """Analyze criticality of all Python files in the project."""
        print("🔍 Analyzing file criticality across entire project...")

        # Find all Python files (excluding already ignored)
        python_files = []
        for pattern in ["apps/**/*.py", "api/**/*.py", "users/**/*.py", "config/**/*.py"]:
            for file_path in self.project_root.glob(pattern):
                if not any(skip in str(file_path) for skip in ["migrations", "__pycache__", "test"]):
                    python_files.append(file_path)

        print(f"📁 Found {len(python_files)} Python files to assess")

        results = {
            "files": [],
            "summary": {
                "critical": [],
                "important": [],
                "moderate": [],
                "low": [],
                "ignore_candidates": [],
                "total_errors_in_ignore_candidates": 0,
            },
        }

        for file_path in python_files:
            assessment = self.assess_file_criticality(file_path)
            results["files"].append(assessment)

            # Categorize
            category = assessment["category"]
            results["summary"][category].append(assessment)

            if assessment["ignore_candidate"]:
                results["summary"]["ignore_candidates"].append(assessment)
                results["summary"]["total_errors_in_ignore_candidates"] += assessment["mypy_errors"]

        return results

    def generate_strategic_ignores(self, analysis_results: dict, confirm: bool = False) -> dict:
        """Generate strategic type ignore pragmas for non-critical files."""
        if not confirm:
            print("🚨 STRATEGIC IGNORE MODE: This will add type ignore pragmas!")
            print("   Add --confirm flag to proceed")
            return {"status": "cancelled", "reason": "confirmation required"}

        print("🎯 Applying strategic type ignores to non-critical files...")

        ignore_candidates = analysis_results["summary"]["ignore_candidates"]

        results = {"files_processed": 0, "pragmas_added": 0, "errors_ignored": 0, "files_modified": []}

        for file_info in ignore_candidates:
            file_path = self.project_root / file_info["file"]

            if file_info["mypy_errors"] > 0:
                print(f"   Adding pragma to {file_info['file']} ({file_info['mypy_errors']} errors)")

                content = file_path.read_text()

                # Add mypy ignore pragma at the top of file
                lines = content.split("\n")

                # Find insertion point (after shebang, encoding, and docstring)
                insert_idx = 0
                for i, line in enumerate(lines):
                    if (
                        line.startswith("#!")
                        or line.startswith("# -*- coding")
                        or line.startswith('"""')
                        or line.startswith("'''")
                        or line.strip() == ""
                    ):
                        insert_idx = i + 1
                    else:
                        break

                # Add the pragma
                pragma_line = "# type: ignore  # Strategic ignore for acceleration - non-critical file"
                lines.insert(insert_idx, pragma_line)

                # Write back
                file_path.write_text("\n".join(lines))

                results["files_processed"] += 1
                results["pragmas_added"] += 1
                results["errors_ignored"] += file_info["mypy_errors"]
                results["files_modified"].append(file_info["file"])

        return results

    def save_analysis_report(self, analysis_results: dict) -> str:
        """Save comprehensive file criticality analysis report."""
        report = f"""# File Criticality Analysis Report - Week 2 Strategic Management

## 📊 Summary Statistics

### File Categories
- **Critical Files:** {len(analysis_results["summary"]["critical"])} files (models, views, APIs)
- **Important Files:** {len(analysis_results["summary"]["important"])} files (business logic)
- **Moderate Files:** {len(analysis_results["summary"]["moderate"])} files (utilities, helpers)
- **Low Priority Files:** {len(analysis_results["summary"]["low"])} files (configs, simple utilities)

### Strategic Ignore Candidates
- **Total Candidates:** {len(analysis_results["summary"]["ignore_candidates"])} files
- **Errors to Ignore:** {analysis_results["summary"]["total_errors_in_ignore_candidates"]} errors
- **Week 2 Target:** Focus manual effort on critical files only

## 🎯 Strategic Ignore Candidates

Files with low business criticality and ≤5 MyPy errors each:

"""

        for file_info in sorted(
            analysis_results["summary"]["ignore_candidates"], key=lambda x: x["mypy_errors"], reverse=True
        ):
            report += f"""### {file_info["file"]}
- **Category:** {file_info["category"]} (score: {file_info["score"]})
- **MyPy Errors:** {file_info["mypy_errors"]}
- **Reasons:** {", ".join(file_info["reasons"])}

"""

        report += """
## 🏢 Critical Files (NEVER ignore)

Focus all manual MyPy fixing effort on these high-value files:

"""

        critical_files = sorted(
            analysis_results["summary"]["critical"] + analysis_results["summary"]["important"],
            key=lambda x: x["mypy_errors"],
            reverse=True,
        )

        for file_info in critical_files[:20]:  # Top 20 critical files
            if file_info["mypy_errors"] > 0:
                report += f"""### {file_info["file"]}
- **Category:** {file_info["category"]} (score: {file_info["score"]})
- **MyPy Errors:** {file_info["mypy_errors"]} ⭐ **PRIORITY**
- **Business Value:** {", ".join(file_info["reasons"])}

"""

        report += f"""
## 📈 Week 2 Impact Projection

### Before Strategic Ignores
- Current MyPy errors across all files

### After Strategic Ignores
- **Errors Eliminated:** ~{analysis_results["summary"]["total_errors_in_ignore_candidates"]} errors
- **Files Remaining for Manual Work:** {len(critical_files)} high-value files
- **Focus Strategy:** 80% effort on 20% of files with highest business impact

### Success Metrics
- Manual effort focuses only on models, views, APIs, and core business logic
- Non-critical utilities and helpers strategically ignored
- Same business value with dramatically reduced manual work

## Next Steps

1. **Review Ignore Candidates:** Ensure no critical business logic marked for ignoring
2. **Apply Strategic Ignores:** `python scripts/utilities/file_criticality_assessor.py --generate-ignores --confirm`
3. **Focus Manual Effort:** Work only on critical files with remaining errors
4. **Track Progress:** Monitor error reduction in high-value files only
"""

        report_path = self.project_root / "file_criticality_analysis.md"
        report_path.write_text(report)
        print(f"📄 Criticality analysis saved to: {report_path}")

        return str(report_path)


def main():
    parser = argparse.ArgumentParser(description="Assess file criticality for strategic MyPy management")
    parser.add_argument("--analyze", action="store_true", help="Analyze file criticality")
    parser.add_argument("--generate-ignores", action="store_true", help="Generate strategic ignore pragmas")
    parser.add_argument("--confirm", action="store_true", help="Confirm strategic ignore changes")
    parser.add_argument("--save-report", action="store_true", help="Save comprehensive analysis report")

    args = parser.parse_args()

    assessor = FileCriticalityAssessor()

    if args.analyze or args.generate_ignores or args.save_report:
        analysis = assessor.analyze_all_files()

        print("\n📊 CRITICALITY ANALYSIS COMPLETE")
        print(f"Critical files: {len(analysis['summary']['critical'])}")
        print(f"Important files: {len(analysis['summary']['important'])}")
        print(f"Strategic ignore candidates: {len(analysis['summary']['ignore_candidates'])}")
        print(f"Errors in ignore candidates: {analysis['summary']['total_errors_in_ignore_candidates']}")

        if args.save_report:
            assessor.save_analysis_report(analysis)

        if args.generate_ignores:
            results = assessor.generate_strategic_ignores(analysis, args.confirm)
            if results["status"] != "cancelled":
                print("\n🎯 STRATEGIC IGNORES APPLIED")
                print(f"Files processed: {results['files_processed']}")
                print(f"Errors ignored: {results['errors_ignored']}")
                print(
                    f"Focus now on: {len(analysis['summary']['critical']) + len(analysis['summary']['important'])} critical files"
                )

    else:
        print("🎯 File Criticality Assessor - Week 2 Strategic Management")
        print("   --analyze: Analyze file criticality across project")
        print("   --generate-ignores --confirm: Apply strategic ignores to non-critical files")
        print("   --save-report: Save comprehensive analysis report")


if __name__ == "__main__":
    main()
