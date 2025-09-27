#!/bin/bash
# File-based project memory system (works without Context7)
#
# This provides persistent memory functionality using local files
# until Context7 is installed and configured

set -e

# Color output functions
red() { echo -e "\033[31m$1\033[0m"; }
green() { echo -e "\033[32m$1\033[0m"; }
yellow() { echo -e "\033[33m$1\033[0m"; }
blue() { echo -e "\033[34m$1\033[0m"; }
bold() { echo -e "\033[1m$1\033[0m"; }

# Ensure we're in the project root
cd "$(dirname "$0")/.."

MEMORY_DIR="project-docs/project-memory"
mkdir -p "$MEMORY_DIR"

# Function to store memory
store_memory() {
    local tag="$1"
    local content="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    echo "[$timestamp] $content" >> "$MEMORY_DIR/${tag}.log"
    echo "$(green "✅ Memory stored under tag: $tag")"
}

# Function to query memory
query_memory() {
    local query="$1"
    
    echo "$(bold "🧠 Searching Project Memory for: '$query'")"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Search in memory files
    found=false
    if find "$MEMORY_DIR" -name "*.log" -exec grep -l -i "$query" {} \; 2>/dev/null | head -10 | while read -r file; do
        found=true
        tag=$(basename "$file" .log)
        echo "$(blue "📄 Found in tag: $tag")"
        grep -i "$query" "$file" | tail -3 | sed 's/^/  /'
        echo
    done
    
    # Search in session logs
    if find "project-docs/session-logs" -name "*.md" -exec grep -l -i "$query" {} \; 2>/dev/null | head -5 | while read -r file; do
        echo "$(blue "📄 Found in session log: $(basename "$file")")"
        grep -i -A 2 -B 2 "$query" "$file" | head -5 | sed 's/^/  /'
        echo
    done
    
    # Search in work status
    if ls project-docs/work-status/*COMPLETED* 2>/dev/null | grep -i "$query"; then
        echo "$(green "✅ Found completed work matching query")"
    fi
}

# Function to show all memory
show_all_memory() {
    echo "$(bold "🧠 All Project Memory")"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if ls "$MEMORY_DIR"/*.log 2>/dev/null; then
        for file in "$MEMORY_DIR"/*.log; do
            tag=$(basename "$file" .log)
            echo "$(blue "📄 Tag: $tag")"
            tail -3 "$file" | sed 's/^/  /'
            echo
        done
    else
        echo "$(yellow "⚠️  No memory files found")"
    fi
}

# Main command handling
case "${1:-help}" in
    "store")
        if [ $# -lt 3 ]; then
            echo "Usage: $0 store <tag> <content>"
            echo "Example: $0 store 'migration-status' 'Sponsorship detection verified working'"
            exit 1
        fi
        store_memory "$2" "$3"
        ;;
    
    "query")
        if [ $# -lt 2 ]; then
            echo "Usage: $0 query <search-term>"
            echo "Example: $0 query 'migration'"
            exit 1
        fi
        query_memory "$2"
        ;;
    
    "show")
        show_all_memory
        ;;
    
    "init")
        echo "$(bold "🔧 Initializing Project Memory")"
        
        # Store initial project info
        store_memory "project-info" "Naga Backend v1.0 - Django SIS with clean architecture"
        store_memory "architecture" "Two-environment strategy: LOCAL (PostgreSQL dev), MIGRATION (PostgreSQL legacy), Testing (SQLite)"
        store_memory "current-status" "Student migration script verified working, sponsorship detection confirmed"
        
        echo "$(green "✅ Project memory initialized")"
        ;;
    
    "help"|*)
        echo "$(bold "🧠 Project Memory System (File-based)")"
        echo
        echo "Usage: $0 <command> [args]"
        echo
        echo "Commands:"
        echo "  $(blue "init")                Initialize project memory"
        echo "  $(blue "store <tag> <content>") Store information under a tag"
        echo "  $(blue "query <search-term>")   Search memory for information"
        echo "  $(blue "show")                 Show all stored memory"
        echo
        echo "Examples:"
        echo "  $0 init"
        echo "  $0 store 'task-completed' 'Sponsorship linking verified 2025-06-27'"
        echo "  $0 query 'migration'"
        echo "  $0 show"
        echo
        echo "Integration with workflow:"
        echo "  # Before starting work"
        echo "  $0 query 'current status'"
        echo "  ./scripts/verify-migration-completion.sh"
        echo
        echo "  # After completing work"
        echo "  $0 store 'work-completed' 'Description of completed work'"
        ;;
esac