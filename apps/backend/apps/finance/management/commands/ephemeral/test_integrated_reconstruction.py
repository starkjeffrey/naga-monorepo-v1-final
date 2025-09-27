#!/usr/bin/env python
"""Quick test script to verify the integrated reconstruction command works."""

import os
import sys

import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")
django.setup()

from django.core.management import call_command  # noqa: E402


def test_integrated_reconstruction():
    """Test the integrated reconstruction command."""
    print("Testing integrated AR reconstruction command...")

    try:
        # Test with a small limit to avoid processing too much data
        call_command(
            "reconstruct_ar_integrated", "--limit=5", "--mode=supervised", "--confidence-threshold=80.0", verbosity=2
        )
        print("✅ Command executed successfully!")

    except Exception as e:
        print(f"❌ Command failed: {e!s}")
        import traceback

        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = test_integrated_reconstruction()
    sys.exit(0 if success else 1)
