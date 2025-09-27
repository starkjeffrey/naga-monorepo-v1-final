#!/usr/bin/env python3
"""Fast PO file translation using parallel processing.
Translates multiple entries concurrently for speed.
Usage: python translate_po_fast.py [--workers 5]
"""

import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import polib
from deep_translator import GoogleTranslator

# Thread-safe counter
translate_counter = threading.Lock()
completed_count = 0


def translate_entry(entry, translator, index, total):
    """Translate a single entry."""
    global completed_count
    try:
        if not entry.msgstr and entry.msgid and entry.msgid.strip():
            translation = translator.translate(entry.msgid)
            if translation:
                entry.msgstr = translation

                with translate_counter:
                    completed_count += 1
                    if completed_count % 10 == 0:
                        print(f"Progress: {completed_count}/{total} entries translated...")

                return True, entry, None
    except Exception as e:
        return False, entry, str(e)
    return False, entry, "Already translated or empty"


def translate_po_parallel(po_file_path, workers=5, batch_size=500):
    """Translate a .po file using parallel processing."""
    global completed_count
    completed_count = 0

    # Paths
    progress_file = po_file_path.replace(".po", "_in_progress.po")
    final_file = po_file_path.replace(".po", "_translated.po")

    # Load file
    if os.path.exists(progress_file):
        print(f"Resuming from {progress_file}...")
        po = polib.pofile(progress_file)
    else:
        print(f"Starting fresh translation of {po_file_path}...")
        po = polib.pofile(po_file_path)

    # Find entries to translate
    entries_to_translate = []
    for entry in po:
        if not entry.msgstr and entry.msgid and entry.msgid.strip():
            entries_to_translate.append(entry)

    if not entries_to_translate:
        print("No entries to translate!")
        return

    # Limit batch size
    if len(entries_to_translate) > batch_size:
        entries_to_translate = entries_to_translate[:batch_size]
        print(f"Processing batch of {batch_size} entries...")

    total = len(entries_to_translate)
    print(f"Translating {total} entries with {workers} workers...")

    # Create translator instances for each worker
    translators = [GoogleTranslator(source="en", target="km") for _ in range(workers)]

    # Translate in parallel
    success_count = 0
    error_count = 0

    with ThreadPoolExecutor(max_workers=workers) as executor:
        # Submit all translation tasks
        future_to_entry = {}
        for i, entry in enumerate(entries_to_translate):
            translator = translators[i % workers]
            future = executor.submit(translate_entry, entry, translator, i, total)
            future_to_entry[future] = entry

        # Process results as they complete
        for future in as_completed(future_to_entry):
            success, entry, error = future.result()
            if success:
                success_count += 1
            elif error and error != "Already translated or empty":
                error_count += 1
                print(f"  Error: {error} for '{entry.msgid[:50]}...'")

    # Save progress
    po.save(progress_file)

    print("\nBatch complete!")
    print(f"  Successfully translated: {success_count} entries")
    print(f"  Errors: {error_count} entries")
    print(f"  Progress saved to: {progress_file}")

    # Check if complete
    remaining = sum(1 for e in po if not e.msgstr and e.msgid and e.msgid.strip())
    print(f"  Remaining to translate: {remaining} entries")

    if remaining == 0:
        os.rename(progress_file, final_file)
        print(f"\nTranslation COMPLETE! Final file: {final_file}")


if __name__ == "__main__":
    # Parse arguments
    workers = 5
    if "--workers" in sys.argv:
        idx = sys.argv.index("--workers")
        if idx + 1 < len(sys.argv):
            workers = int(sys.argv[idx + 1])

    po_file_path = "../../locale/km/LC_MESSAGES/django.po"

    print("=" * 60)
    print(f"Fast Parallel Translation (workers: {workers})")
    print("=" * 60)

    translate_po_parallel(po_file_path, workers=workers)
