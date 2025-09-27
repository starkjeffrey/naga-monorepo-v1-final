#!/usr/bin/env python3
"""Batch PO file translation with resume capability.
Translates in smaller batches to avoid timeouts.
Usage: python translate_po_batch.py [--batch-size 100]
"""

import os
import sys
import time

import polib
from deep_translator import GoogleTranslator


def translate_batch(po_file_path, batch_size=100, max_entries=None):
    """Translate a .po file in batches with resume capability."""
    # Paths
    progress_file = po_file_path.replace(".po", "_in_progress.po")
    final_file = po_file_path.replace(".po", "_translated.po")

    # Check if we're resuming
    if os.path.exists(progress_file):
        print(f"Resuming from {progress_file}...")
        po = polib.pofile(progress_file)
    else:
        print(f"Starting fresh translation of {po_file_path}...")
        po = polib.pofile(po_file_path)

    # Initialize translator
    translator = GoogleTranslator(source="en", target="km")

    # Count what needs translation
    entries_to_translate = []
    for i, entry in enumerate(po):
        if not entry.msgstr and entry.msgid and entry.msgid.strip():
            entries_to_translate.append((i, entry))

    total_to_translate = len(entries_to_translate)

    if total_to_translate == 0:
        print("No entries left to translate!")
        if os.path.exists(progress_file):
            os.rename(progress_file, final_file)
            print(f"Moved completed file to: {final_file}")
        return

    # Apply max_entries limit if specified
    if max_entries:
        entries_to_translate = entries_to_translate[:max_entries]
        print(f"Limiting to {max_entries} entries for this batch")

    print(f"Found {total_to_translate} entries still needing translation")
    print(f"Processing batch of up to {batch_size} entries...")

    # Translate in this batch
    translated_count = 0
    error_count = 0

    for idx, (_original_idx, entry) in enumerate(entries_to_translate):
        if translated_count >= batch_size:
            break

        try:
            print(f"[{idx + 1}/{min(batch_size, len(entries_to_translate))}] Translating: {entry.msgid[:60]}...")

            translation = translator.translate(entry.msgid)
            if translation:
                entry.msgstr = translation
                translated_count += 1

            # Small delay to avoid rate limiting
            time.sleep(0.1)

        except Exception as e:
            print(f"  ERROR: {e}")
            error_count += 1
            continue

    # Save progress
    po.save(progress_file)
    print("\nBatch complete!")
    print(f"  Translated: {translated_count} entries")
    print(f"  Errors: {error_count} entries")
    print(f"  Progress saved to: {progress_file}")

    # Check if fully complete
    remaining = sum(1 for e in po if not e.msgstr and e.msgid and e.msgid.strip())
    print(f"  Remaining to translate: {remaining} entries")

    if remaining == 0:
        os.rename(progress_file, final_file)
        print(f"\nTranslation COMPLETE! Final file: {final_file}")
    else:
        print("\nRun this script again to continue translation.")


if __name__ == "__main__":
    # Parse arguments
    batch_size = 100
    if "--batch-size" in sys.argv:
        idx = sys.argv.index("--batch-size")
        if idx + 1 < len(sys.argv):
            batch_size = int(sys.argv[idx + 1])

    po_file_path = "../../locale/km/LC_MESSAGES/django.po"

    print("=" * 60)
    print(f"Batch Translation (batch size: {batch_size})")
    print("=" * 60)

    translate_batch(po_file_path, batch_size=batch_size)
