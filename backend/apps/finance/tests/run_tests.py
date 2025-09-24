#!/usr/bin/env python3
"""
Finance app test runner for isolated test suite execution.

This script allows running different categories of tests independently:
- Unit tests: Test individual components in isolation
- Integration tests: Test component interactions and workflows
- Transaction safety tests: Test concurrency and atomicity
- All tests: Run the complete test suite

Usage:
    python run_tests.py unit                    # Run only unit tests
    python run_tests.py integration             # Run only integration tests
    python run_tests.py transaction_safety      # Run only transaction safety tests
    python run_tests.py all                     # Run all tests
    python run_tests.py --coverage              # Run with coverage report
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Ensure we're in the correct directory
BACKEND_DIR = Path(__file__).parent.parent.parent.parent
FINANCE_TESTS_DIR = Path(__file__).parent


def run_command(command, description):
    """Run a command and handle output."""
    print(f"\n{'=' * 60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(command)}")
    print(f"{'=' * 60}")

    result = subprocess.run(command, check=False, cwd=BACKEND_DIR, capture_output=False)

    if result.returncode != 0:
        print(f"\n❌ {description} failed with exit code {result.returncode}")
        return False
    else:
        print(f"\n✅ {description} completed successfully")
        return True


def run_unit_tests(coverage=False):
    """Run unit tests only."""
    cmd = [
        "python",
        "-m",
        "pytest",
        "apps/finance/tests/test_unit_services.py",
        "--verbose",
        "--tb=short",
        "-m",
        "not integration",
    ]

    if coverage:
        cmd.extend(
            [
                "--cov=apps.finance",
                "--cov-report=term-missing",
                "--cov-report=html:htmlcov/unit",
            ]
        )

    # Set environment for SQLite testing
    env = os.environ.copy()
    env["DJANGO_SETTINGS_MODULE"] = "config.settings.test_sqlite"

    return subprocess.run(cmd, check=False, cwd=BACKEND_DIR, env=env).returncode == 0


def run_integration_tests(coverage=False):
    """Run integration tests only."""
    cmd = [
        "python",
        "-m",
        "pytest",
        "apps/finance/tests/test_integration_workflows.py",
        "--verbose",
        "--tb=short",
    ]

    if coverage:
        cmd.extend(
            [
                "--cov=apps.finance",
                "--cov-report=term-missing",
                "--cov-report=html:htmlcov/integration",
            ]
        )

    # Set environment for SQLite testing
    env = os.environ.copy()
    env["DJANGO_SETTINGS_MODULE"] = "config.settings.test_sqlite"

    return subprocess.run(cmd, check=False, cwd=BACKEND_DIR, env=env).returncode == 0


def run_transaction_safety_tests(coverage=False):
    """Run transaction safety and concurrency tests."""
    cmd = [
        "python",
        "-m",
        "pytest",
        "apps/finance/tests/test_transaction_safety_comprehensive.py",
        "--verbose",
        "--tb=short",
    ]

    if coverage:
        cmd.extend(
            [
                "--cov=apps.finance",
                "--cov-report=term-missing",
                "--cov-report=html:htmlcov/transaction_safety",
            ]
        )

    # Set environment for SQLite testing
    env = os.environ.copy()
    env["DJANGO_SETTINGS_MODULE"] = "config.settings.test_sqlite"

    return subprocess.run(cmd, check=False, cwd=BACKEND_DIR, env=env).returncode == 0


def run_all_tests(coverage=False):
    """Run all finance tests."""
    cmd = [
        "python",
        "-m",
        "pytest",
        "apps/finance/tests/",
        "--verbose",
        "--tb=short",
        "--ignore=apps/finance/tests/factories.py",  # Ignore old broken factories
    ]

    if coverage:
        cmd.extend(
            [
                "--cov=apps.finance",
                "--cov-report=term-missing",
                "--cov-report=html:htmlcov/all",
                "--cov-fail-under=85",  # Require at least 85% coverage
            ]
        )

    # Set environment for SQLite testing
    env = os.environ.copy()
    env["DJANGO_SETTINGS_MODULE"] = "config.settings.test_sqlite"

    return subprocess.run(cmd, check=False, cwd=BACKEND_DIR, env=env).returncode == 0


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description="Finance app test runner")
    parser.add_argument(
        "suite", choices=["unit", "integration", "transaction_safety", "all"], help="Test suite to run"
    )
    parser.add_argument("--coverage", action="store_true", help="Run tests with coverage reporting")
    parser.add_argument("--fast", action="store_true", help="Run tests in fast mode (skip slow tests)")

    args = parser.parse_args()

    print(f"🧪 Running Finance App Tests - {args.suite.upper()} Suite")
    print(f"Backend Directory: {BACKEND_DIR}")
    print("Test Environment: SQLite (fast)")

    if args.coverage:
        print("📊 Coverage reporting enabled")

    success = False

    if args.suite == "unit":
        success = run_unit_tests(coverage=args.coverage)
    elif args.suite == "integration":
        success = run_integration_tests(coverage=args.coverage)
    elif args.suite == "transaction_safety":
        success = run_transaction_safety_tests(coverage=args.coverage)
    elif args.suite == "all":
        success = run_all_tests(coverage=args.coverage)

    if success:
        print(f"\n🎉 All {args.suite} tests passed!")
        return 0
    else:
        print(f"\n💥 Some {args.suite} tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
