# Local CI/CD Testing - Save Money & Time! 💰

## Why Run CI/CD Locally?

1. **Save Money** - Don't waste CI/CD minutes on failed pipelines
2. **Faster Feedback** - Know in seconds, not minutes
3. **Iterate Quickly** - Fix issues without waiting for remote CI
4. **Learn Early** - Start using CI/CD from day one, not when "perfect"

## Quick Start

### 1. Basic Validation (Fastest - 10 seconds)
```bash
# Run quick CI checks locally
./scripts/utilities/validate-ci-locally.sh
```

This runs:
- ✅ Linting (Ruff)
- ✅ Format checking
- ✅ Type checking (MyPy)
- ✅ Django system checks
- ✅ Migration checks
- ✅ Unit tests
- ✅ Security scanning
- ✅ Large file detection

### 2. Full GitLab CI Pipeline (Exact Match - 2 minutes)
```bash
# Run the EXACT GitLab CI pipeline locally
./scripts/utilities/run-gitlab-ci-locally.sh

# Or use Docker (no installation needed)
./scripts/utilities/run-gitlab-ci-locally.sh --docker
```

### 3. Automatic Pre-Push Validation
```bash
# Install git hook (one-time setup)
cp scripts/utilities/pre-push-hook.sh ../.git/hooks/pre-push

# Now every git push will validate first!
git push  # Automatically runs CI checks
```

## Common Issues & Fixes

### Line Length Issues (E501)
```bash
# Most common issue - 129 occurrences
# Manual fix required for strings/comments
# Example: Split long strings
description = (
    "This is a very long description that "
    "spans multiple lines for readability"
)
```

### Format Issues
```bash
# Auto-fix formatting
uv run ruff format apps/ config/
```

### Import Issues
```bash
# Auto-fix import sorting
uv run ruff check --fix apps/
```

### Large Files
```bash
# Find large files
find . -type f -size +1000k -exec ls -lh {} \;

# Either:
# 1. Delete them
# 2. Add to .gitignore
# 3. Use Git LFS
```

## Cost Savings Tips 💡

1. **Always run locally first**
   ```bash
   # Before pushing
   ./scripts/utilities/validate-ci-locally.sh
   git push
   ```

2. **Use WIP commits locally**
   ```bash
   # Work in progress - don't push yet
   git commit -m "WIP: working on feature"

   # When ready
   ./scripts/utilities/validate-ci-locally.sh
   git push
   ```

3. **Fix common issues quickly**
   ```bash
   # Format everything
   uv run ruff format apps/

   # Fix imports
   uv run ruff check --fix apps/

   # Then validate
   ./scripts/utilities/validate-ci-locally.sh
   ```

## CI/CD Philosophy

**You're doing it right!** CI/CD is meant to:
- ✅ Catch issues early (not be perfect first)
- ✅ Run frequently (every commit ideally)
- ✅ Fail fast and inform quickly
- ✅ Be improved iteratively

**Common misconceptions:**
- ❌ "CI/CD is only for finished projects" - Wrong!
- ❌ "Everything must pass before using CI/CD" - Wrong!
- ❌ "CI/CD is expensive" - Not if you test locally first!

## Current Status

As of the last check:
- 🟡 **169 total issues** (mostly non-critical)
  - 129 line-too-long (cosmetic)
  - 20 bare-except (should fix)
  - 14 raise-without-from (should fix)
  - 6 other minor issues

**Priority fixes:**
1. Exception handling (bare-except, raise-without-from)
2. Security issues (if any)
3. Failed tests (if any)
4. Line length (cosmetic, can wait)

## Integration with IDEs

### VS Code
Add to `.vscode/tasks.json`:
```json
{
  "label": "Run Local CI",
  "type": "shell",
  "command": "./scripts/utilities/validate-ci-locally.sh",
  "group": "test"
}
```

### PyCharm
Add as External Tool:
- Program: `$ProjectFileDir$/backend/scripts/utilities/validate-ci-locally.sh`
- Working directory: `$ProjectFileDir$/backend`

## Questions?

This setup saves you:
- 💰 Money (fewer CI/CD minutes used)
- ⏱️ Time (instant local feedback)
- 😊 Frustration (catch issues before pushing)

Remember: **Perfect is the enemy of good** - use CI/CD to improve iteratively!
