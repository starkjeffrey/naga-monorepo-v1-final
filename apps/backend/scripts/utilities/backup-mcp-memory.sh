#!/bin/bash

# Backup Memory MCP data for Naga monorepo
# This script exports the Memory MCP graph data and saves it to the repository

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKUP_DIR="$BACKEND_DIR/project-docs/mcp-memory-backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/memory_graph_backup_$TIMESTAMP.json"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo "🔍 Checking Memory MCP server status..."
if ! claude mcp list | grep -q "memory.*✓ Connected"; then
    echo "❌ Memory MCP server is not connected. Please ensure it's running."
    exit 1
fi

echo "📤 Exporting Memory MCP graph data..."

# Create a temporary Python script to export the memory graph
cat > /tmp/export_memory_graph.py << 'EOF'
import json
import sys

# This would normally use the MCP client to fetch the graph
# For now, we'll create a placeholder that shows the structure
print(json.dumps({
    "export_timestamp": "PLACEHOLDER",
    "note": "This requires MCP client integration to export actual data",
    "structure": {
        "entities": "Array of knowledge graph entities",
        "relations": "Array of entity relationships"
    }
}, indent=2))
EOF

# Note: This is a placeholder. In practice, you'd need to:
# 1. Use the MCP protocol to connect to the memory server
# 2. Call the read_graph function
# 3. Export the results

echo "⚠️  Note: Full MCP memory export requires MCP client integration."
echo "    For now, you can manually export using Claude Code's interface."
echo ""
echo "📝 To manually backup your Memory MCP data:"
echo "   1. In Claude Code, run: mcp__memory__read_graph"
echo "   2. Copy the entire output"
echo "   3. Save it to: $BACKUP_FILE"
echo ""
echo "💡 Alternative: The Memory MCP data might be stored in:"
echo "   - ~/.claude/memory/ (if it exists)"
echo "   - A temporary directory managed by the MCP server"
echo "   - Check 'lsof -p <memory-mcp-pid>' for open files"

# Create a template file
cat > "$BACKUP_FILE" << EOF
{
  "_README": "This is a template for Memory MCP backup. Replace with actual export from mcp__memory__read_graph",
  "export_timestamp": "$TIMESTAMP",
  "entities": [],
  "relations": []
}
EOF

echo "✅ Created backup template at: $BACKUP_FILE"
echo ""
echo "📋 Next steps:"
echo "   1. Run 'mcp__memory__read_graph' in Claude Code"
echo "   2. Save the output to $BACKUP_FILE"
echo "   3. Commit the backup to your repository"

# Clean up
rm -f /tmp/export_memory_graph.py