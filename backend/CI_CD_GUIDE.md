# 🚀 CI/CD Quality Pipeline Guide

## Overview

This CI/CD pipeline is designed for **realistic quality control** in a large Django codebase with existing technical debt. Instead of failing constantly, it **prevents new problems** while allowing gradual improvement.

## 🎯 Philosophy: "Prevent Regression, Enable Progress"

- ✅ **Don't block development** with 1000+ existing mypy errors
- ✅ **Prevent NEW problems** from being introduced  
- ✅ **Fast feedback** (< 15 minutes total runtime)
- ✅ **Incremental improvement** over time

## 🏗️ Pipeline Structure

### 1. 🚀 Smoke Tests (5 min)
**Purpose**: Catch obvious problems immediately
- Django system checks
- Missing migrations detection
- Python syntax validation
- Basic import checks

### 2. 🔍 Code Quality (10 min)  
**Purpose**: Maintain code standards on NEW code
- **MyPy**: Only modified files (no legacy error spam!)
- **Ruff Lint**: Focus on changed files
- **Ruff Format**: Full codebase (fast)
- **Bandit Security**: Modified files only

### 3. 🧪 Tests (15 min)
**Purpose**: Ensure functionality works
- Fast smoke tests first
- Unit tests (excluding slow ones)  
- Coverage reporting
- PostgreSQL + Redis services

### 4. 🔗 Integration Tests (20 min)
**Purpose**: Test component interactions
- Only runs on main branch or with label `run-integration-tests`
- API endpoint testing
- Complex workflow validation

### 5. 🔒 Security (5 min)
**Purpose**: Catch security issues early
- Dependency vulnerability scanning
- Secret scanning with TruffleHog
- Both steps continue-on-error (warn, don't block)

## 🛠️ Key Scripts

### `scripts/mypy-new-files-ci.sh`
Only checks mypy on files changed in your PR:
```bash
# Locally test what CI will check:
./scripts/mypy-new-files-ci.sh
```

### `scripts/mypy-baseline-check.sh`  
Alternative approach - locks in current error count:
```bash
# Create baseline (run once):
./scripts/mypy-baseline-check.sh

# Future runs only fail if errors increase
./scripts/mypy-baseline-check.sh
```

## 🎮 Usage Patterns

### For Daily Development
```bash
# Before committing, check what CI will see:
./scripts/mypy-new-files-ci.sh

# Quick local quality check:
uv run ruff check --diff
uv run ruff format --check .
```

### For Pull Requests
1. **All checks run automatically**
2. **Focus on modified files only**
3. **Integration tests via label**: Add `run-integration-tests` label

### For Releases
- **Main branch** gets full integration tests
- **All quality checks** must pass
- **Security scans** included

## 📊 What Gets Checked vs Ignored

### ✅ Always Checked (Will Fail CI)
- New mypy errors in modified files
- Ruff linting errors in modified files
- Code formatting violations  
- Test failures
- Django system check failures
- Missing migrations

### ⚠️ Warned About (Won't Fail CI)
- Security vulnerabilities in dependencies
- Bandit security warnings
- Coverage decreases
- Integration test failures (on PRs)

### 🤐 Ignored Completely  
- Existing mypy errors in unchanged files
- Legacy code quality issues
- Slow test failures (marked with `@pytest.mark.slow`)

## 🔧 Configuration Files

### Mypy Strategy
- **Modified Files**: `mypy.ini` with lenient settings
- **Baseline Approach**: `mypy-baseline.txt` locks current errors
- **Django Integration**: Handles Django ORM patterns

### Ruff Configuration  
- **Django-aware**: Ignores common Django patterns
- **Security-focused**: Catches real issues, ignores false positives
- **Per-file overrides**: Different rules for tests, migrations, etc.

### Test Configuration
- **Pytest markers**: `smoke`, `slow`, `integration`, `api`
- **Fast defaults**: `--nomigrations`, `--reuse-db`
- **Coverage**: HTML, XML, and terminal reporting

## 🚦 How to Fix Common CI Failures

### ❌ MyPy Errors in Modified Files
```bash
# Check locally first:
./scripts/mypy-new-files-ci.sh

# Add type hints or suppress specific errors:
# type: ignore[attr-defined]
```

### ❌ Ruff Linting Errors  
```bash
# See what needs fixing:
uv run ruff check --diff

# Auto-fix what's possible:
uv run ruff check --fix

# Format code:
uv run ruff format .
```

### ❌ Test Failures
```bash  
# Run the same tests as CI:
uv run pytest -m "not slow and not e2e" --maxfail=5

# Debug specific test:
uv run pytest path/to/test.py::TestClass::test_method -v
```

### ❌ Django System Check Failures
```bash
# Check locally:
uv run python manage.py check --deploy

# Common issues:
# - Missing migrations: python manage.py makemigrations
# - Settings problems: Check config/settings/ci.py
```

## 🎛️ Customization Options

### Skip Integration Tests
Remove the `run-integration-tests` label or don't push to main.

### Change Quality Thresholds
Edit the scripts in `scripts/`:
- Adjust mypy strictness in `mypy-new-files-ci.sh`
- Modify ruff rules in `pyproject.toml`
- Update test markers in `pytest.ini`

### Add New Checks
Add steps to `.github/workflows/quality-check.yml`:
```yaml
- name: Custom check
  run: your-custom-command
  continue-on-error: true  # Don't fail CI
```

## 📈 Gradual Improvement Strategy

### Week 1-2: Establish Baseline
- ✅ Get CI passing consistently  
- ✅ Team adopts "check before push" habit
- ✅ No new mypy/lint errors introduced

### Month 1: Clean Up New Code
- ✅ All new files have proper type hints
- ✅ New tests have good coverage  
- ✅ Security issues caught early

### Month 2+: Tackle Legacy Code
- 🎯 Pick one module per sprint to clean up
- 🎯 Gradually increase mypy strictness
- 🎯 Add integration tests for critical paths

## 🤝 Team Workflow

### Before Push
```bash
# Quick quality check:
./scripts/mypy-new-files-ci.sh
uv run ruff format .
```

### During Code Review
- ✅ **Focus on NEW issues**, not legacy problems
- ✅ **Praise** mypy/lint improvements
- ✅ **Suggest** gradual cleanups, don't demand them

### When CI Fails
1. **Don't bypass** - fix the issue
2. **Ask for help** if mypy errors are confusing  
3. **Temporary ignore** is OK with `# type: ignore[error-code]`

## 📞 Getting Help

### MyPy Confusion
- Check our lenient config in `mypy.ini`
- Use `# type: ignore[error-code]` for now
- Ask in team chat for complex type issues

### CI Taking Too Long
- Most runs should be < 15 minutes
- Check if integration tests are running unnecessarily
- Consider splitting large PRs

### Quality Standards Too Strict
- This pipeline is designed to be realistic
- Discuss any blocking issues with the team
- Remember: we prevent regression, we don't demand perfection

---

🎉 **Happy Coding!** This pipeline lets you ship features while gradually improving code quality.
