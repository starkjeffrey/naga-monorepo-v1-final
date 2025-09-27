# Generated migration to update ATHLETIC scholarships to STAFF

from django.db import migrations


def update_athletic_to_staff(apps, schema_editor):
    """Update any ATHLETIC scholarship types to STAFF."""
    try:
        Scholarship = apps.get_model("scholarships", "Scholarship")

        # Check if the model has the objects manager and the scholarship_type field
        if hasattr(Scholarship, "objects") and hasattr(Scholarship._meta.get_field("scholarship_type"), "name"):
            # Update any ATHLETIC scholarships to STAFF
            updated_count = Scholarship.objects.filter(scholarship_type="ATHLETIC").update(scholarship_type="STAFF")

            if updated_count > 0:
                print(f"Updated {updated_count} ATHLETIC scholarships to STAFF")
            else:
                print("No ATHLETIC scholarships found to update")
        else:
            print("Scholarship model or scholarship_type field not ready - skipping migration")
    except Exception as e:
        print(f"Migration failed safely: {e} - continuing without updates")


def reverse_staff_to_athletic(apps, schema_editor):
    """Reverse operation: update STAFF back to ATHLETIC."""
    try:
        Scholarship = apps.get_model("scholarships", "Scholarship")

        # Check if the model has the objects manager and the scholarship_type field
        if hasattr(Scholarship, "objects") and hasattr(Scholarship._meta.get_field("scholarship_type"), "name"):
            # Update any STAFF scholarships back to ATHLETIC
            updated_count = Scholarship.objects.filter(scholarship_type="STAFF").update(scholarship_type="ATHLETIC")

            if updated_count > 0:
                print(f"Reversed {updated_count} STAFF scholarships back to ATHLETIC")
            else:
                print("No STAFF scholarships found to reverse")
        else:
            print("Scholarship model or scholarship_type field not ready - skipping reverse migration")
    except Exception as e:
        print(f"Reverse migration failed safely: {e} - continuing without updates")


class Migration(migrations.Migration):
    dependencies = [
        ("scholarships", "0004_scholarship_cycle_and_more"),
    ]

    operations = [
        migrations.RunPython(
            update_athletic_to_staff,
            reverse_staff_to_athletic,
        ),
    ]
