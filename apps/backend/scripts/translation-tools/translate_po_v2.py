#!/usr/bin/env python3
"""PO file translation script using deep-translator (supports multiple providers).
Usage: python translate_po_v2.py [--test] [--provider google]
"""

import sys
import time

import polib
from deep_translator import GoogleTranslator


def translate_po_file(po_file_path, source_lang="en", target_lang="km", test_mode=False, batch_size=10):
    """Translate a .po file using deep-translator.

    Args:
        po_file_path: Path to the .po file
        source_lang: Source language code (default: 'en')
        target_lang: Target language code (default: 'km' for Khmer)
        test_mode: If True, only translate first 10 entries
        batch_size: Number of translations before saving progress
    """
    # Load the .po file
    print(f"Loading {po_file_path}...")
    po = polib.pofile(po_file_path)

    # Initialize translator
    translator = GoogleTranslator(source=source_lang, target=target_lang)

    # Count entries to translate
    entries_to_translate = [entry for entry in po if not entry.msgstr and entry.msgid and entry.msgid.strip()]
    total_entries = len(entries_to_translate)

    if test_mode:
        entries_to_translate = entries_to_translate[:10]
        print(f"TEST MODE: Translating only first 10 entries out of {total_entries}")
    else:
        print(f"Found {total_entries} entries to translate")

    # Translate entries
    translated_count = 0
    error_count = 0

    for i, entry in enumerate(entries_to_translate):
        try:
            # Skip if already translated (for resuming)
            if entry.msgstr:
                continue

            print(f"Translating {i + 1}/{len(entries_to_translate)}: {entry.msgid[:50]}...")

            # Translate the text
            translation = translator.translate(entry.msgid)
            if translation:
                entry.msgstr = translation
                translated_count += 1

            # Save progress periodically
            if translated_count % batch_size == 0:
                temp_path = po_file_path.replace(".po", "_progress.po")
                po.save(temp_path)
                print(f"Progress saved to {temp_path}")

            # Add a small delay to avoid rate limiting
            time.sleep(0.1)

        except Exception as e:
            print(f"Error translating '{entry.msgid}': {e}")
            error_count += 1
            # Continue with next entry
            continue

    # Save the final translated file
    if test_mode:
        output_path = po_file_path.replace(".po", "_test_translated.po")
    else:
        output_path = po_file_path.replace(".po", "_translated.po")

    po.save(output_path)
    print("\nTranslation complete!")
    print(f"  Translated: {translated_count} entries")
    print(f"  Errors: {error_count} entries")
    print(f"  Saved to: {output_path}")

    # Show a sample of translations
    print("\nSample translations:")
    sample_count = 0
    for entry in po:
        if entry.msgstr and entry.msgid:
            print(f"  EN: {entry.msgid[:60]}")
            print(f"  KM: {entry.msgstr[:60]}")
            print()
            sample_count += 1
            if sample_count >= 3:
                break


if __name__ == "__main__":
    # Path to your Django .po file
    po_file_path = "../../locale/km/LC_MESSAGES/django.po"

    # Check if test mode
    test_mode = "--test" in sys.argv

    print("Starting translation from English to Khmer...")
    print("=" * 60)

    # Run translation
    translate_po_file(po_file_path, test_mode=test_mode)
