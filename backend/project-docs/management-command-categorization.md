# Management Command Categorization Strategy

## Overview

This document describes the three-tier organizational structure for Django management commands, designed to balance code quality requirements with development efficiency.

## Directory Structure

Each Django app's management/commands directory is organized into three subdirectories:

```
apps/*/management/commands/
├── production/       # Commands for ongoing operations
├── transitional/     # Migration/setup commands (temporary but important)
└── ephemeral/       # One-off analysis/fixes (relaxed quality standards)
```

## Category Definitions

### 1. Production Commands (`production/`)

**Purpose**: Commands for ongoing operational needs that are part of the regular system workflow.

**Characteristics**:
- User-facing operations
- Regular maintenance tasks
- Data processing workflows
- Reporting and analytics
- Commands that may be run in production environments
- Commands that are part of automated processes

**Quality Standards**: **Full compliance** with all code quality standards:
- ✅ Type hints required
- ✅ Comprehensive documentation
- ✅ Error handling
- ✅ Testing encouraged
- ✅ Full mypy type checking
- ✅ All ruff linting rules apply

**Examples**:
- User report generation
- Regular data cleanup
- Batch processing workflows
- System health checks
- Automated maintenance tasks

### 2. Transitional Commands (`transitional/`)

**Purpose**: Commands for setup and migration tasks that are temporary but important for system evolution.

**Characteristics**:
- Data migration scripts
- System initialization
- One-time setup operations
- Schema transformations
- Legacy data imports
- System configuration updates

**Quality Standards**: **Good standards** with some flexibility:
- ✅ Type hints encouraged but not required
- ✅ Basic documentation required
- ✅ Error handling for critical operations
- ✅ Full mypy type checking
- ✅ Most ruff linting rules apply
- ⚠️ Some complexity tolerance for data transformations

**Examples**:
- Database schema migrations
- Legacy data import scripts
- System initialization commands
- Configuration deployment scripts

### 3. Ephemeral Commands (`ephemeral/`)

**Purpose**: Commands for quick analysis and fixes that prioritize speed of development over code quality.

**Characteristics**:
- One-off debugging scripts
- Data exploration tools
- Experimental analysis
- Quick fixes and patches
- Investigative scripts
- Prototype implementations

**Quality Standards**: **Relaxed standards** to allow rapid development:
- ❌ Type checking disabled (mypy ignores)
- ❌ Most linting rules relaxed (ruff ignores)
- ⚠️ Basic functionality required
- ⚠️ Print statements allowed for debugging
- ⚠️ Complex logic acceptable without refactoring
- ⚠️ Minimal documentation acceptable

**Ruff Rules Ignored for Ephemeral Commands**:
- `T201`, `T203` - Print statements allowed
- `C901` - Complex structure allowed
- `PLR` - Pylint refactoring rules ignored
- `B` - Bugbear rules relaxed
- `S` - Security rules relaxed (non-production)
- `E501` - Line length relaxed
- `F401`, `F841` - Unused imports/variables allowed
- `UP` - Upgrade suggestions ignored

## Implementation Details

### Configuration Updates

**mypy Configuration** (`pyproject.toml`):
```toml
[[tool.mypy.overrides]]
module = "*.management.commands.ephemeral.*"
ignore_errors = true
```

**Ruff Configuration** (`pyproject.toml`):
```toml
# Ephemeral management commands - relaxed quality standards
"*/management/commands/ephemeral/*" = ["T201", "T203", "C901", "PLR", "B", "S", "E501", "F401", "F841", "UP"]
```

### Migration Strategy

1. **Assess Existing Commands**: Review all current management commands to understand their purpose and usage patterns.

2. **Categorize Commands**: Sort commands into the three categories based on:
   - **Production**: Regular use, user-facing, operational necessity
   - **Transitional**: Setup, migration, one-time configuration
   - **Ephemeral**: Debugging, analysis, experimental, quick fixes

3. **Move Commands**: Use provided helper scripts to move commands to appropriate directories.

4. **Validate Structure**: Use validation scripts to ensure proper categorization and directory structure.

## Helper Scripts

### 1. Command Mover Script
Located at: `scripts/utilities/move_management_commands.py`
- Analyzes command content to suggest categorization
- Moves commands to appropriate directories
- Updates import paths if needed

### 2. Validation Script
Located at: `scripts/utilities/validate_command_structure.py`
- Verifies directory structure exists
- Checks for proper __init__.py files
- Validates command categorization
- Reports on linting compliance by category

### 3. Quality Reporter Script
Located at: `scripts/utilities/report_command_quality.py`
- Runs quality checks by category
- Shows mypy/ruff issues organized by command type
- Provides quality metrics and trends

## Usage Guidelines

### For Developers

1. **New Commands**: Place new commands in the appropriate directory based on their intended use:
   - **Production**: Commands that will be used regularly or in production
   - **Transitional**: Setup, migration, or temporary configuration commands
   - **Ephemeral**: Quick analysis, debugging, or experimental commands

2. **Quality Expectations**:
   - Follow full quality standards for production commands
   - Apply good practices for transitional commands
   - Focus on functionality over form for ephemeral commands

3. **Movement Between Categories**: Commands can be moved between categories as their purpose evolves:
   - Ephemeral → Transitional: When a quick fix becomes a proper migration
   - Transitional → Production: When a setup command becomes operational
   - Production → Transitional: When a command becomes deprecated

### For Code Reviews

- **Production commands**: Apply full review standards
- **Transitional commands**: Focus on functionality and basic quality
- **Ephemeral commands**: Minimal review, focus on not breaking system

## Benefits

1. **Development Speed**: Developers can create quick debugging scripts without worrying about perfect code quality.

2. **Quality Assurance**: Production commands maintain high standards for reliability and maintainability.

3. **Technical Debt Management**: Clear separation allows for focused quality improvements where they matter most.

4. **CI/CD Efficiency**: Automated tools can apply different standards to different categories, reducing false positives.

5. **Maintenance Clarity**: Easy to identify which commands need ongoing maintenance vs. temporary scripts.

## Monitoring and Maintenance

- **Monthly Review**: Review ephemeral commands to identify candidates for promotion or deletion
- **Quality Metrics**: Track quality improvements in transitional commands over time
- **Documentation Updates**: Keep categorization up-to-date as system evolves
- **Training**: Ensure new developers understand the categorization system

## Migration Timeline

1. **Week 1**: Create directory structure and update configurations
2. **Week 2**: Categorize and move existing commands
3. **Week 3**: Validate structure and fix any issues
4. **Week 4**: Team training and documentation updates

This categorization strategy provides a pragmatic approach to code quality that supports both rapid development and long-term maintainability.
