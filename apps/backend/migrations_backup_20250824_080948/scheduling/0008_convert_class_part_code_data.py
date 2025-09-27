# Generated manually for data conversion
# Converts class_part_code from letters (A, B, C) to integers (1, 2, 3)

from django.db import migrations


def convert_letters_to_numbers(apps, schema_editor):
    """Convert class_part_code from letters to numbers."""
    apps.get_model("scheduling", "ClassPart")
    apps.get_model("scheduling", "ClassPartTemplate")

    # Mapping from letters to numbers
    letter_to_number = {
        "A": 1,
        "B": 2,
        "C": 3,
        "D": 4,
        "E": 5,
        "F": 6,
        "G": 7,
        "H": 8,
        "I": 9,
        "J": 10,
        "K": 11,
        "L": 12,
        "M": 13,
        "N": 14,
        "O": 15,
        "P": 16,
        "Q": 17,
        "R": 18,
        "S": 19,
        "T": 20,
        "U": 21,
        "V": 22,
        "W": 23,
        "X": 24,
        "Y": 25,
        "Z": 26,
    }

    # Use the database operations directly for historical models

    # Convert ClassPart records using raw SQL
    with schema_editor.connection.cursor() as cursor:
        # Get all distinct class_part_codes first
        cursor.execute("SELECT DISTINCT class_part_code FROM scheduling_classpart")
        existing_codes = [row[0] for row in cursor.fetchall()]

        for old_code in existing_codes:
            if old_code and old_code.strip().upper() in letter_to_number:
                new_code = str(letter_to_number[old_code.strip().upper()])
                cursor.execute(
                    "UPDATE scheduling_classpart SET class_part_code = %s WHERE class_part_code = %s",
                    [new_code, old_code],
                )

    # Convert ClassPartTemplate records using raw SQL
    with schema_editor.connection.cursor() as cursor:
        # Get all distinct class_part_codes first
        cursor.execute("SELECT DISTINCT class_part_code FROM scheduling_classparttemplate")
        existing_codes = [row[0] for row in cursor.fetchall()]

        for old_code in existing_codes:
            if old_code and old_code.strip().upper() in letter_to_number:
                new_code = str(letter_to_number[old_code.strip().upper()])
                cursor.execute(
                    "UPDATE scheduling_classparttemplate SET class_part_code = %s WHERE class_part_code = %s",
                    [new_code, old_code],
                )


def reverse_numbers_to_letters(apps, schema_editor):
    """Reverse: Convert class_part_code from numbers back to letters."""
    ClassPart = apps.get_model("scheduling", "ClassPart")
    ClassPartTemplate = apps.get_model("scheduling", "ClassPartTemplate")

    # Mapping from numbers to letters
    number_to_letter = {
        1: "A",
        2: "B",
        3: "C",
        4: "D",
        5: "E",
        6: "F",
        7: "G",
        8: "H",
        9: "I",
        10: "J",
        11: "K",
        12: "L",
        13: "M",
        14: "N",
        15: "O",
        16: "P",
        17: "Q",
        18: "R",
        19: "S",
        20: "T",
        21: "U",
        22: "V",
        23: "W",
        24: "X",
        25: "Y",
        26: "Z",
    }

    # Convert ClassPart records back
    for part in ClassPart.objects.all():
        try:
            old_code = int(part.class_part_code)
            if old_code in number_to_letter:
                part.class_part_code = number_to_letter[old_code]
                part.save(update_fields=["class_part_code"])
        except (ValueError, TypeError):
            pass  # Skip invalid values

    # Convert ClassPartTemplate records back
    for template in ClassPartTemplate.objects.all():
        try:
            old_code = int(template.class_part_code)
            if old_code in number_to_letter:
                template.class_part_code = number_to_letter[old_code]
                template.save(update_fields=["class_part_code"])
        except (ValueError, TypeError):
            pass  # Skip invalid values


class Migration(migrations.Migration):
    dependencies = [
        ("scheduling", "0007_centralize_class_part_types_and_uuid7"),
    ]

    operations = [
        migrations.RunPython(
            convert_letters_to_numbers,
            reverse_numbers_to_letters,
        ),
    ]
