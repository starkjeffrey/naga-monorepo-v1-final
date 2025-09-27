#!/usr/bin/env python3
"""Simple PO file translation script using Google Translate.
Usage: python translate_po.py [--test]
"""

import sys
import time

import polib
from googletrans import Translator


def translate_po_file(po_file_path, target_lang="km", test_mode=False):
    """Translate a .po file using Google Translate.

    Args:
        po_file_path: Path to the .po file
        target_lang: Target language code (default: 'km' for Khmer)
        test_mode: If True, only translate first 10 entries
    """
    # Load the .po file
    po = polib.pofile(po_file_path)
    translator = Translator()

    # Count entries to translate
    entries_to_translate = [entry for entry in po if not entry.msgstr and entry.msgid]
    total_entries = len(entries_to_translate)

    if test_mode:
        entries_to_translate = entries_to_translate[:10]
        print(f"TEST MODE: Translating only first 10 entries out of {total_entries}")
    else:
        print(f"Found {total_entries} entries to translate")

    # Translate entries
    for i, entry in enumerate(entries_to_translate):
        try:
            # Skip empty or whitespace-only strings
            if not entry.msgid.strip():
                continue

            print(f"Translating {i + 1}/{len(entries_to_translate)}: {entry.msgid[:50]}...")

            # Translate the text
            translation = translator.translate(entry.msgid, src="en", dest=target_lang)
            entry.msgstr = translation.text

            # Add a small delay to avoid rate limiting
            time.sleep(0.5)

        except Exception as e:
            print(f"Error translating '{entry.msgid}': {e}")
            continue

    # Save the translated file
    if test_mode:
        output_path = po_file_path.replace(".po", "_test_translated.po")
    else:
        output_path = po_file_path.replace(".po", "_translated.po")

    po.save(output_path)
    print(f"\nTranslation complete! Saved to: {output_path}")

    # Show a sample of translations
    print("\nSample translations:")
    for entry in po[:5]:
        if entry.msgstr:
            print(f"  {entry.msgid} -> {entry.msgstr}")


if __name__ == "__main__":
    # Path to your Django .po file
    po_file_path = "../../locale/km/LC_MESSAGES/django.po"

    # Check if test mode
    test_mode = "--test" in sys.argv

    # Run translation
    translate_po_file(po_file_path, test_mode=test_mode)
