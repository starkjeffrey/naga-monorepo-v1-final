#!/bin/bash
# Setup Context7 MCP for persistent project memory
#
# This script sets up Context7 to provide persistent memory across Claude sessions

set -e

# Color output functions
red() { echo -e "\033[31m$1\033[0m"; }
green() { echo -e "\033[32m$1\033[0m"; }
yellow() { echo -e "\033[33m$1\033[0m"; }
blue() { echo -e "\033[34m$1\033[0m"; }
bold() { echo -e "\033[1m$1\033[0m"; }

echo "$(bold "🧠 Setting up Context7 Persistent Memory for Naga Backend")"
echo

# Step 1: Install Context7 if not already available
echo "$(bold "📦 Step 1: Context7 Installation")"
if command -v context7 >/dev/null 2>&1; then
    echo "$(green "✅ Context7 already installed")"
else
    echo "$(yellow "⚠️  Context7 not found. Install instructions:")"
    echo "   1. Install via npm: npm install -g context7"
    echo "   2. Or download from: https://github.com/context7/context7"
    echo "   3. Follow setup instructions for your system"
    echo "   4. Run this script again after installation"
    exit 1
fi
echo

# Step 2: Initialize project memory space
echo "$(bold "🔧 Step 2: Initialize Project Memory")"
PROJECT_NAME="naga-backend-v1"

# Store basic project info
context7 store --project "$PROJECT_NAME" --tag "project-info" <<EOF
Project: Naga Backend v1.0
Type: Django Student Information System
Architecture: Clean architecture, two-environment setup (LOCAL/MIGRATION)
Database: PostgreSQL (development), SQLite (testing)
Key Apps: people, curriculum, scholarships, enrollment, scheduling
EOF

echo "$(green "✅ Project info stored")"

# Step 3: Store current completion status
echo "$(bold "📋 Step 3: Store Current Work Status")"

# Read existing work status
if [ -f "project-docs/work-status/student-migration-COMPLETED-250626" ]; then
    context7 store --project "$PROJECT_NAME" --tag "migration-status" <<EOF
Student Migration: COMPLETED 2025-06-26
- Script: scripts/migration_environment/migrate_legacy_students_250626.py
- Records: 18,034 legacy students available
- Imported: ~100 students (sample data)
- Sponsorship Detection: Implemented but needs verification with sponsored student sample
- Next: Import full dataset or test with specific sponsored students
EOF
    echo "$(green "✅ Migration status stored")"
fi

# Step 4: Store environment setup
context7 store --project "$PROJECT_NAME" --tag "environment" <<EOF
Environment Architecture: Two-environment strategy
- LOCAL: PostgreSQL with realistic development data
- MIGRATION: PostgreSQL with legacy data processing  
- Testing: Local SQLite in-memory (10-50x faster)

Scripts:
- ./scripts/check-environment-status.sh: Health monitoring
- ./scripts/compare-environment-data.sh: Data comparison
- ./scripts/refresh-local-from-migration.sh: Data refresh
- ./scripts/verify-migration-completion.sh: Prevent rework

Database Commands:
- LOCAL: docker compose -f docker-compose.local.yml
- MIGRATION: docker compose -f docker-compose.migration.yml
- Testing: DATABASE_URL="sqlite:///:memory:" DJANGO_SETTINGS_MODULE=config.settings.test_sqlite uv run pytest
EOF

echo "$(green "✅ Environment info stored")"

# Step 5: Create memory helper scripts
echo "$(bold "🛠️  Step 4: Create Memory Helper Scripts")"

# Create memory query script
cat > scripts/query-project-memory.sh << 'EOF'
#!/bin/bash
# Query project memory from Context7
PROJECT_NAME="naga-backend-v1"

echo "🧠 Querying Project Memory for: $PROJECT_NAME"
echo

if [ $# -eq 0 ]; then
    echo "Usage: $0 <query>"
    echo "Examples:"
    echo "  $0 'migration status'"
    echo "  $0 'environment setup'"
    echo "  $0 'sponsor data'"
    exit 1
fi

QUERY="$*"
echo "Query: $QUERY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

context7 query --project "$PROJECT_NAME" "$QUERY"
EOF

chmod +x scripts/query-project-memory.sh

# Create memory update script  
cat > scripts/update-project-memory.sh << 'EOF'
#!/bin/bash
# Update project memory in Context7
PROJECT_NAME="naga-backend-v1"

if [ $# -lt 2 ]; then
    echo "Usage: $0 <tag> <content>"
    echo "Examples:"
    echo "  $0 'task-completed' 'Sponsor linking completed 2025-06-27'"
    echo "  $0 'migration-status' 'All 18034 students imported successfully'"
    exit 1
fi

TAG="$1"
shift
CONTENT="$*"

echo "🧠 Updating Project Memory"
echo "Tag: $TAG"
echo "Content: $CONTENT"

echo "$CONTENT" | context7 store --project "$PROJECT_NAME" --tag "$TAG"
echo "✅ Memory updated successfully"
EOF

chmod +x scripts/update-project-memory.sh

echo "$(green "✅ Helper scripts created:")"
echo "   📝 scripts/query-project-memory.sh"
echo "   📝 scripts/update-project-memory.sh"
echo

# Step 6: Usage instructions
echo "$(bold "📖 Usage Instructions")"
echo
echo "$(blue "Query project memory:")"
echo "  ./scripts/query-project-memory.sh 'what work has been completed?'"
echo "  ./scripts/query-project-memory.sh 'migration status'"
echo "  ./scripts/query-project-memory.sh 'environment setup'"
echo
echo "$(blue "Update project memory:")"
echo "  ./scripts/update-project-memory.sh 'task-completed' 'Sponsorship linking verified 2025-06-27'"
echo "  ./scripts/update-project-memory.sh 'migration-status' 'Full student import completed'"
echo
echo "$(blue "Integration with workflow:")"
echo "  # Always check memory before starting work"
echo "  ./scripts/query-project-memory.sh 'current status'"
echo "  ./scripts/verify-migration-completion.sh"
echo
echo "  # Update memory after completing work" 
echo "  ./scripts/update-project-memory.sh 'work-completed' 'Description of completed work'"
echo

echo "$(bold "🎉 Context7 Persistent Memory Setup Complete!")"
echo
echo "$(yellow "📋 Next Steps:")"
echo "1. Install Context7 if not available"
echo "2. Run helper scripts to test functionality"
echo "3. Integrate memory queries into development workflow"
echo "4. Update memory after completing work"
EOF