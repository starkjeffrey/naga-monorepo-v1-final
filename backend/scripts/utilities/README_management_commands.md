# Management Command Organization Tools

This directory contains tools for organizing Django management commands into three categories with appropriate quality standards.

## Quick Start

1. **Validate current structure**:
   ```bash
   python scripts/utilities/validate_command_structure.py --verbose
   ```

2. **Move commands to categories** (dry run first):
   ```bash
   python scripts/utilities/move_management_commands.py --dry-run
   python scripts/utilities/move_management_commands.py  # Actually move
   ```

3. **Check quality by category**:
   ```bash
   python scripts/utilities/report_command_quality.py --detailed
   ```

## Tool Overview

### 1. validate_command_structure.py
**Purpose**: Validates the directory structure and identifies issues.

**Usage**:
```bash
# Check all apps
python scripts/utilities/validate_command_structure.py

# Check specific app
python scripts/utilities/validate_command_structure.py --app finance

# Fix simple issues automatically
python scripts/utilities/validate_command_structure.py --fix --verbose
```

**What it checks**:
- ✅ Directory structure exists
- ✅ __init__.py files are present and documented
- ✅ No uncategorized commands remain
- ✅ No unexpected directories

### 2. move_management_commands.py
**Purpose**: Analyzes and moves commands to appropriate categories.

**Usage**:
```bash
# Dry run to see what would be moved
python scripts/utilities/move_management_commands.py --dry-run

# Move with interactive confirmation
python scripts/utilities/move_management_commands.py --interactive

# Auto-move with high confidence only
python scripts/utilities/move_management_commands.py --confidence-threshold 0.7

# Move specific app
python scripts/utilities/move_management_commands.py --app finance
```

**Categorization logic**:
- **Production**: Regular operations, reports, maintenance
- **Transitional**: Migrations, setup, data conversion
- **Ephemeral**: Analysis, debugging, one-off scripts

### 3. report_command_quality.py
**Purpose**: Runs quality checks and reports issues by category.

**Usage**:
```bash
# Quality overview
python scripts/utilities/report_command_quality.py

# Detailed report for specific category
python scripts/utilities/report_command_quality.py --category ephemeral --detailed

# Export results to JSON
python scripts/utilities/report_command_quality.py --export quality_report.json
```

**Quality standards by category**:
- **Production**: Full mypy + ruff compliance
- **Transitional**: Good standards, some flexibility
- **Ephemeral**: Relaxed standards, focus on functionality

## Directory Structure

After organization, each app will have:

```
apps/[app_name]/management/commands/
├── production/         # Full quality standards
│   ├── __init__.py
│   └── operational_command.py
├── transitional/       # Good quality standards
│   ├── __init__.py
│   └── setup_command.py
└── ephemeral/         # Relaxed quality standards
    ├── __init__.py
    └── debug_command.py
```

## Configuration Changes

The tools automatically configured:

**mypy** (`pyproject.toml`):
```toml
[[tool.mypy.overrides]]
module = "*.management.commands.ephemeral.*"
ignore_errors = true
```

**ruff** (`pyproject.toml`):
```toml
"*/management/commands/ephemeral/*" = ["T201", "T203", "C901", "PLR", "B", "S", "E501", "F401", "F841", "UP"]
```

## Example Workflow

1. **Start with validation**:
   ```bash
   python scripts/utilities/validate_command_structure.py
   ```

2. **Move commands** (safe with dry-run):
   ```bash
   python scripts/utilities/move_management_commands.py --dry-run
   python scripts/utilities/move_management_commands.py --interactive
   ```

3. **Verify the move**:
   ```bash
   python scripts/utilities/validate_command_structure.py --fix
   ```

4. **Check quality impact**:
   ```bash
   python scripts/utilities/report_command_quality.py --detailed
   ```

5. **Focus improvements**:
   ```bash
   # Fix production issues first
   uv run ruff check apps/*/management/commands/production/ --fix

   # Then transitional
   uv run mypy apps/*/management/commands/transitional/
   ```

## Benefits

- **Development Speed**: Quick scripts in ephemeral/ without quality burden
- **Production Safety**: High standards for operational commands
- **Technical Debt**: Clear separation of temporary vs. permanent code
- **CI/CD**: Reduced false positives, focused quality checks

## Troubleshooting

**Q: Command moved to wrong category?**
A: Just move the file manually to the correct directory

**Q: Quality checks still failing after move?**
A: Check the category-specific quality rules in pyproject.toml

**Q: Want to promote ephemeral to production?**
A: Move file + apply quality standards (type hints, error handling, docs)

**Q: Mass changes needed?**
A: Use the --app flag to process one app at a time

## Integration with CI/CD

Add to your CI pipeline:
```bash
# Validate structure
python scripts/utilities/validate_command_structure.py

# Quality gates by category
python scripts/utilities/report_command_quality.py --category production
```

For more details, see: `project-docs/management-command-categorization.md`
