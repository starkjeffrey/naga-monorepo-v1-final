# Translation Tools

This directory contains isolated translation tools that are NOT included in the main Docker container.

## Setup

### Option 1: Using System Python (if sentencepiece build fails)

```bash
# Install with system python
pip3 install --user argostranslate polib

# Or use homebrew to install dependencies first
brew install cmake pkg-config sentencepiece
pip3 install --user argostranslate polib
```

### Option 2: Using Virtual Environment (Recommended)

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Option 3: Alternative Translation Tools

If argostranslate fails to install due to sentencepiece issues, you can use:

```bash
# Google Translate API (requires API key)
pip install googletrans==4.0.0-rc1

# LibreTranslate (self-hosted or API)
pip install libretranslatepy
```

## Usage

### Example Translation Script

```python
#!/usr/bin/env python3
import polib
import argostranslate.package
import argostranslate.translate

# Download and install language packages
from_code = "en"
to_code = "km"

# Download language package if not already installed
argostranslate.package.update_package_index()
available_packages = argostranslate.package.get_available_packages()
package_to_install = next(
    filter(
        lambda x: x.from_code == from_code and x.to_code == to_code,
        available_packages
    ),
    None
)

if package_to_install:
    argostranslate.package.install_from_path(package_to_install.download())

# Load .po file
po = polib.pofile('../../locale/km/LC_MESSAGES/django.po')

# Translate entries
for entry in po:
    if not entry.msgstr and entry.msgid:
        translation = argostranslate.translate.translate(entry.msgid, from_code, to_code)
        entry.msgstr = translation

# Save translated file
po.save('../../locale/km/LC_MESSAGES/django.po')
```

## Important Notes

1. **NOT in Docker**: This directory is isolated from the main project dependencies
2. **Large Models**: Argos translation models can be several hundred MB each
3. **Alternative**: Consider using Django's built-in translation management commands with professional translators
4. **Backup**: Always backup your .po files before running automated translation

## Why Separate?

- Keeps translation tools out of production Docker image
- Avoids dependency conflicts
- Translation is typically a one-time or occasional task
- Models can be large and unnecessary in production
