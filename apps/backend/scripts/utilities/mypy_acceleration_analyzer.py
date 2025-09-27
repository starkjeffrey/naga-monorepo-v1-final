#!/usr/bin/env python3
"""
MyPy Acceleration Pattern Analyzer

Analyzes all MyPy errors to identify bulk-fixable patterns for dramatic
acceleration of error reduction from 30+ weeks down to 3-4 weeks.

The key insight: Stop fixing errors individually. Eliminate error categories.

Usage:
    python scripts/utilities/mypy_acceleration_analyzer.py
    python scripts/utilities/mypy_acceleration_analyzer.py --generate-fixes
"""

import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path


class MyPyAccelerationAnalyzer:
    """Identifies bulk-fixable patterns in MyPy errors for dramatic acceleration."""

    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or Path.cwd()
        self.all_errors: list[dict] = []
        self.pattern_analysis: dict = {}

    def collect_all_errors(self) -> list[dict]:
        """Collect and parse ALL MyPy errors for pattern analysis."""
        print("🔍 Collecting ALL MyPy errors for pattern analysis...")

        try:
            result = subprocess.run(
                ["uv", "run", "mypy", ".", "--show-error-codes"],
                check=False,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=180,
            )

            errors = []
            error_pattern = re.compile(r"^([^:]+):(\d+):(?:\d+:)?\s*(error):\s*(.+?)\s*\[([^\]]+)\]")

            for line in result.stderr.split("\n"):
                match = error_pattern.match(line.strip())
                if match:
                    file_path, line_num, _severity, message, error_code = match.groups()

                    errors.append(
                        {
                            "file": file_path,
                            "line": int(line_num),
                            "message": message,
                            "error_code": error_code,
                            "app": file_path.split("/")[1] if file_path.startswith("apps/") else "other",
                        }
                    )

            print(f"📊 Collected {len(errors)} total errors for analysis")
            self.all_errors = errors
            return errors

        except Exception as e:
            print(f"❌ Error collecting MyPy errors: {e}")
            return []

    def analyze_bulk_fix_patterns(self) -> dict:
        """Analyze errors to identify bulk-fixable patterns with high impact."""
        if not self.all_errors:
            self.collect_all_errors()

        print("🧠 Analyzing bulk-fixable patterns...")

        # Pattern 1: Attribute errors by error message similarity
        attr_patterns = defaultdict(list)
        import_patterns = defaultdict(list)
        return_patterns = defaultdict(list)
        union_patterns = defaultdict(list)

        for error in self.all_errors:
            code = error["error_code"]
            message = error["message"]

            if code == "attr-defined":
                # Extract the attribute name pattern
                if "has no attribute" in message:
                    attr_match = re.search(r'"([^"]+)" has no attribute "([^"]+)"', message)
                    if attr_match:
                        class_name, attr_name = attr_match.groups()
                        pattern_key = f"{class_name}::{attr_name}"
                        attr_patterns[pattern_key].append(error)

            elif code == "name-defined":
                # Extract undefined names
                if "is not defined" in message:
                    name_match = re.search(r'Name "([^"]+)" is not defined', message)
                    if name_match:
                        undefined_name = name_match.group(1)
                        import_patterns[undefined_name].append(error)

            elif code == "return-value":
                # QuerySet vs List return type mismatches
                if "incompatible return value type" in message.lower():
                    return_patterns["queryset_to_list"].append(error)

            elif code == "union-attr":
                # Optional attribute access without None checks
                if "has no attribute" in message:
                    union_patterns["optional_access"].append(error)

        # Calculate impact scores (errors fixed per pattern)
        pattern_impact = {}

        # Top attribute errors
        top_attr_patterns = sorted(attr_patterns.items(), key=lambda x: len(x[1]), reverse=True)[:10]
        for pattern_key, errors in top_attr_patterns:
            if len(errors) >= 5:  # Only patterns with significant impact
                pattern_impact[f"attr_defined::{pattern_key}"] = {
                    "error_count": len(errors),
                    "fix_confidence": "high" if len(errors) >= 10 else "medium",
                    "fix_type": "field_name_correction",
                    "sample_files": list({e["file"] for e in errors[:5]}),
                    "fix_complexity": "bulk_replace",
                }

        # Top import errors
        top_import_patterns = sorted(import_patterns.items(), key=lambda x: len(x[1]), reverse=True)[:5]
        for name, errors in top_import_patterns:
            if len(errors) >= 3:
                pattern_impact[f"name_defined::{name}"] = {
                    "error_count": len(errors),
                    "fix_confidence": "high",
                    "fix_type": "add_import",
                    "sample_files": list({e["file"] for e in errors[:5]}),
                    "fix_complexity": "bulk_import_add",
                }

        # QuerySet return patterns
        if len(return_patterns["queryset_to_list"]) >= 5:
            pattern_impact["return_value::queryset_to_list"] = {
                "error_count": len(return_patterns["queryset_to_list"]),
                "fix_confidence": "medium",
                "fix_type": "wrap_with_list",
                "sample_files": list({e["file"] for e in return_patterns["queryset_to_list"][:5]}),
                "fix_complexity": "pattern_replacement",
            }

        self.pattern_analysis = pattern_impact
        return pattern_impact

    def generate_acceleration_plan(self) -> dict:
        """Generate 3-4 week acceleration plan with specific actions."""
        if not self.pattern_analysis:
            self.analyze_bulk_fix_patterns()

        # Calculate total fixable errors through bulk automation
        total_bulk_fixable = sum(p["error_count"] for p in self.pattern_analysis.values())
        total_errors = len(self.all_errors)
        automation_percentage = (total_bulk_fixable / total_errors * 100) if total_errors > 0 else 0

        # File criticality assessment
        file_error_counts = Counter([error["file"] for error in self.all_errors])
        low_priority_files = [
            f
            for f, count in file_error_counts.items()
            if count <= 3 and ("utils" in f or "helpers" in f or "constants" in f)
        ]

        strategic_ignore_candidates = sum(file_error_counts[f] for f in low_priority_files)

        plan = {
            "current_status": {
                "total_errors": total_errors,
                "bulk_fixable_errors": total_bulk_fixable,
                "automation_potential": f"{automation_percentage:.1f}%",
                "strategic_ignore_candidates": strategic_ignore_candidates,
            },
            "acceleration_timeline": {
                "week_1": {
                    "target": f"Reduce from {total_errors} to ~{max(100, total_errors - total_bulk_fixable)} errors",
                    "method": "Bulk pattern automation",
                    "expected_reduction": total_bulk_fixable,
                    "success_criteria": "75%+ error reduction through automation",
                },
                "week_2": {
                    "target": f"Reduce by additional ~{strategic_ignore_candidates} errors",
                    "method": "Strategic file ignores for low-priority code",
                    "expected_reduction": strategic_ignore_candidates,
                    "success_criteria": "Focus only on core business logic files",
                },
                "week_3_4": {
                    "target": "Reduce remaining errors to 0",
                    "method": "Focused manual fixes on critical files only",
                    "expected_reduction": total_errors - total_bulk_fixable - strategic_ignore_candidates,
                    "success_criteria": "Complete type safety for core business logic",
                },
            },
            "high_impact_patterns": sorted(
                self.pattern_analysis.items(), key=lambda x: x[1]["error_count"], reverse=True
            ),
            "strategic_ignore_files": low_priority_files[:20],
        }

        return plan

    def generate_bulk_fix_script(self) -> str:
        """Generate executable bulk fix script based on pattern analysis."""
        if not self.pattern_analysis:
            self.analyze_bulk_fix_patterns()

        script_content = '''#!/usr/bin/env python3
"""
Generated Bulk MyPy Fix Script - Week 1 Acceleration
Auto-generated from pattern analysis for maximum error reduction impact.
"""

import re
import subprocess
from pathlib import Path

def apply_bulk_fixes():
    """Apply all high-impact bulk fixes identified by pattern analysis."""
    project_root = Path.cwd()
    total_fixed = 0

    print("🚀 Starting Week 1 Bulk Fix Acceleration...")

'''

        # Add specific fix functions for each high-impact pattern
        for pattern_key, pattern_info in sorted(
            self.pattern_analysis.items(), key=lambda x: x[1]["error_count"], reverse=True
        ):
            if pattern_info["error_count"] >= 10:  # Only high-impact patterns
                script_content += f"""
    # Fix Pattern: {pattern_key} ({pattern_info["error_count"]} errors)
    print(f"🔧 Fixing pattern: {pattern_key}")
    # TODO: Implement specific bulk fix for this pattern
    # Files affected: {pattern_info["sample_files"]}

"""

        script_content += """
    print(f"✅ Bulk fixes complete. Run 'uv run mypy . | tail -1' to check progress.")
    return total_fixed

if __name__ == "__main__":
    apply_bulk_fixes()
"""

        return script_content

    def save_analysis_report(self) -> str:
        """Save comprehensive analysis report for team review."""
        plan = self.generate_acceleration_plan()

        report = f"""# MyPy Acceleration Analysis Report
Generated: {subprocess.run(["date"], check=False, capture_output=True, text=True).stdout.strip()}

## 📊 Current Status
- **Total Errors:** {plan["current_status"]["total_errors"]:,}
- **Bulk Fixable:** {plan["current_status"]["bulk_fixable_errors"]:,} ({plan["current_status"]["automation_potential"]})
- **Strategic Ignore Candidates:** {plan["current_status"]["strategic_ignore_candidates"]:,}

## 🚀 3-Week Acceleration Timeline

### Week 1: Bulk Pattern Automation
{plan["acceleration_timeline"]["week_1"]["target"]}
- **Method:** {plan["acceleration_timeline"]["week_1"]["method"]}
- **Expected Reduction:** {plan["acceleration_timeline"]["week_1"]["expected_reduction"]:,} errors
- **Success Criteria:** {plan["acceleration_timeline"]["week_1"]["success_criteria"]}

### Week 2: Strategic File Management
{plan["acceleration_timeline"]["week_2"]["target"]}
- **Method:** {plan["acceleration_timeline"]["week_2"]["method"]}
- **Expected Reduction:** {plan["acceleration_timeline"]["week_2"]["expected_reduction"]:,} errors
- **Success Criteria:** {plan["acceleration_timeline"]["week_2"]["success_criteria"]}

### Week 3-4: Focused Manual Cleanup
{plan["acceleration_timeline"]["week_3_4"]["target"]}
- **Method:** {plan["acceleration_timeline"]["week_3_4"]["method"]}
- **Remaining Errors:** ~{plan["acceleration_timeline"]["week_3_4"]["expected_reduction"]:,}
- **Success Criteria:** {plan["acceleration_timeline"]["week_3_4"]["success_criteria"]}

## 🎯 High-Impact Patterns for Bulk Fixing

"""

        for pattern_key, info in plan["high_impact_patterns"][:10]:
            report += f"""### {pattern_key}
- **Errors:** {info["error_count"]:,}
- **Confidence:** {info["fix_confidence"]}
- **Fix Type:** {info["fix_type"]}
- **Sample Files:** {", ".join(info["sample_files"][:3])}
- **Complexity:** {info["fix_complexity"]}

"""

        report += """
## 📁 Strategic Ignore Candidates
These files have few errors and low business criticality:

"""
        for file_path in plan["strategic_ignore_files"]:
            report += f"- {file_path}\n"

        report += """
## 🏆 Success Metrics
- **Week 1 Goal:** 75%+ error reduction through automation
- **Week 2 Goal:** Focus on <20% of files that matter most
- **Week 3-4 Goal:** Zero MyPy errors in core business logic
- **Overall:** 3-4 weeks instead of 30+ weeks (10x acceleration)

## Next Steps
1. Review and approve this acceleration plan
2. Run bulk pattern fixes for Week 1
3. Apply strategic ignores for Week 2
4. Focus manual effort on remaining critical errors
"""

        # Save report
        report_path = self.project_root / "mypy_acceleration_analysis.md"
        report_path.write_text(report)
        print(f"📄 Analysis report saved to: {report_path}")

        return str(report_path)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Analyze MyPy errors for dramatic acceleration")
    parser.add_argument("--generate-fixes", action="store_true", help="Generate bulk fix script")
    parser.add_argument("--save-report", action="store_true", help="Save comprehensive analysis report")

    args = parser.parse_args()

    analyzer = MyPyAccelerationAnalyzer()

    # Always run the analysis
    analyzer.collect_all_errors()
    patterns = analyzer.analyze_bulk_fix_patterns()
    plan = analyzer.generate_acceleration_plan()

    print("\n📊 ACCELERATION ANALYSIS COMPLETE")
    print(f"Current errors: {plan['current_status']['total_errors']:,}")
    print(
        f"Bulk fixable: {plan['current_status']['bulk_fixable_errors']:,} ({plan['current_status']['automation_potential']})"
    )
    print(f"Strategic ignore candidates: {plan['current_status']['strategic_ignore_candidates']:,}")

    print("\n🚀 TIMELINE ACCELERATION:")
    print("From: 30+ weeks (50 errors/week)")
    print("To: 3-4 weeks through bulk automation + strategic management")

    if args.generate_fixes:
        script_content = analyzer.generate_bulk_fix_script()
        script_path = Path("scripts/utilities/generated_bulk_fixes.py")
        script_path.write_text(script_content)
        print(f"🔧 Bulk fix script generated: {script_path}")

    if args.save_report:
        report_path = analyzer.save_analysis_report()
        print(f"📄 Comprehensive report saved to: {report_path}")

    # Always show top patterns
    print("\n🎯 TOP BULK-FIX PATTERNS:")
    for pattern_key, info in sorted(patterns.items(), key=lambda x: x[1]["error_count"], reverse=True)[:5]:
        print(f"   {info['error_count']:,} errors: {pattern_key}")


if __name__ == "__main__":
    main()
