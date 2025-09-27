#!/usr/bin/env python3
"""Quick verification script for local testing setup.

This script verifies that the local test environment can run basic tests
without Docker dependencies. Run this to verify your local testing setup.

Usage:
    cd backend
    python scripts/verify_local_testing.py
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and return success status."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
            check=False,  # backend directory
        )

        if result.returncode == 0:
            return True
        if result.stderr.strip():
            pass
        if result.stdout.strip():
            pass
        return False

    except Exception:
        return False


def main():
    """Main verification function."""
    # Set minimal environment for testing
    test_env = os.environ.copy()
    test_env.update(
        {
            "DATABASE_URL": "sqlite:///test_naga.db",
            "DEBUG": "1",
            "SECRET_KEY": "test-secret-key-for-verification",
        },
    )

    # Update environment
    os.environ.update(test_env)

    tests = [
        (
            "python manage.py check --settings=config.settings.local_test",
            "Django configuration check",
        ),
        (
            "python -c \"import apps.curriculum.models; print('Models import successfully')\"",
            "Model imports verification",
        ),
        (
            "python manage.py test apps.curriculum.tests.DivisionModelTest.test_division_creation --settings=config.settings.local_test -v 0",
            "Sample curriculum test execution",
        ),
    ]

    success_count = 0

    for cmd, description in tests:
        if run_command(cmd, description):
            success_count += 1

    return success_count == len(tests)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
