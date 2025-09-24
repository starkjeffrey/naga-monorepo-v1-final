import os

import django
from django.core.management import call_command

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

# After all model changes are done and database is cleaned
print("🔍 Creating perfect state snapshot from current database...")

# Redirect stdout to capture the output
import sys
from io import StringIO

# Capture inspectdb output
old_stdout = sys.stdout
sys.stdout = captured_output = StringIO()

try:
    call_command("inspectdb", "--database=default")
    output = captured_output.getvalue()
finally:
    sys.stdout = old_stdout

# Write to file
with open("integrity_reports/perfect_state.py", "w") as f:
    f.write(output)

print("✅ Created perfect state snapshot at integrity_reports/perfect_state.py")
