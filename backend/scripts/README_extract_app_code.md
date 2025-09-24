# Extract App Code Script

This script extracts base models code and a specified app folder, generating one .txt file that can be reviewed.

## Features

- Includes base models from `apps/common/models.py`
- Extracts all Python (.py), HTML (.html), and CSS (.css) files
- Creates clear file separators in the output
- Provides file statistics and error handling
- Shows available apps if invalid app name is provided

## Usage

```bash
python scripts/extract_app_code.py <app_name>
```

## Examples

```bash
# Extract attendance app code
python scripts/extract_app_code.py attendance

# Extract finance app code
python scripts/extract_app_code.py finance

# Extract curriculum app code
python scripts/extract_app_code.py curriculum
```

## Output

The script generates a file named `{app_name}_code_review.txt` in the `scripts/` directory.

Example output file: `scripts/attendance_code_review.txt`

## File Structure

The generated file includes:

### 1. Header Section

- App information and file count
- Table of contents

### 2. BASE MODELS Section

- Common models and utilities from `apps/common/`
- Clearly labeled with `[BASE MODELS]` prefix

### 3. APP Implementation Section

- All files from the specified app
- Clearly labeled with `[{APP_NAME} APP]` prefix

### File Type Labels

Each file is clearly identified with:

- 🏗️ **MODELS**: Data models and database schema
- 🌐 **VIEWS**: View logic and request handling
- 📝 **FORMS**: Form definitions and validation
- ⚙️ **ADMIN**: Django admin configuration
- 🔗 **URLS**: URL routing configuration
- 📦 **APP CONFIG**: Django app configuration
- 🧪 **TESTS**: Test cases and test utilities
- 🔧 **SERVICES**: Business logic and service layer
- 📊 **SERIALIZERS**: API serialization logic
- 🔄 **MIGRATION**: Database migration
- 📋 **INIT**: Python package initialization
- 🌐 **TEMPLATE**: HTML template
- 🎨 **STYLES**: CSS stylesheet
- 🐍 **PYTHON**: General Python module

## Available Apps

The script will automatically list available apps if you provide an invalid app name.

Current apps:

- academic
- academic_records
- accounts
- attendance
- common
- curriculum
- enrollment
- finance
- grading
- level_testing
- people
- scheduling
