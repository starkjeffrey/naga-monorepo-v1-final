#!/bin/bash
# Git History Tools - Access historical repositories

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
GIT_REFS_DIR="$PROJECT_ROOT/.git-references"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

usage() {
    echo -e "${GREEN}Git History Tools${NC}"
    echo "Access historical repositories from before monorepo consolidation"
    echo ""
    echo "Usage: $0 <command> [repository] [options]"
    echo ""
    echo "Repositories:"
    echo "  frontend    - Vue.js PWA frontend (pre-monorepo)"
    echo "  backend     - Django backend (pre-monorepo)"  
    echo "  version-0   - Legacy architecture (reference only)"
    echo ""
    echo "Commands:"
    echo "  log         - Show commit history"
    echo "  show        - Show specific commit or file"
    echo "  diff        - Compare with current monorepo"
    echo "  extract     - Extract file from history"
    echo "  branches    - List all branches"
    echo "  tags        - List all tags"
    echo "  stats       - Repository statistics"
    echo ""
    echo "Examples:"
    echo "  $0 log frontend                           # Show frontend commit history"
    echo "  $0 show backend HEAD:apps/people/models.py   # Show file from backend"
    echo "  $0 diff frontend src/components/           # Compare frontend components"
    echo "  $0 extract version-0 apps/core/models.py  # Extract file from version-0"
    echo "  $0 stats backend                          # Show backend repository stats"
}

check_repo() {
    local repo="$1"
    local git_dir="$GIT_REFS_DIR/${repo}.git"
    
    if [[ ! -d "$git_dir" ]]; then
        echo -e "${RED}Error: Repository '$repo' not found${NC}"
        echo "Available repositories:"
        ls -1 "$GIT_REFS_DIR" | grep '\.git$' | sed 's/\.git$//' | sed 's/^/  /'
        exit 1
    fi
    
    echo "$git_dir"
}

cmd_log() {
    local repo="$1"
    local git_dir=$(check_repo "$repo")
    shift
    
    echo -e "${GREEN}Commit history for $repo repository:${NC}"
    git --git-dir="$git_dir" log --oneline --graph --decorate "$@"
}

cmd_show() {
    local repo="$1"
    local target="$2"
    local git_dir=$(check_repo "$repo")
    
    if [[ -z "$target" ]]; then
        echo -e "${RED}Error: Must specify commit or file to show${NC}"
        echo "Example: $0 show $repo HEAD:path/to/file.py"
        exit 1
    fi
    
    echo -e "${GREEN}Showing $target from $repo repository:${NC}"
    git --git-dir="$git_dir" show "$target"
}

cmd_diff() {
    local repo="$1"
    local path="$2"
    local git_dir=$(check_repo "$repo")
    
    if [[ -z "$path" ]]; then
        echo -e "${RED}Error: Must specify path to compare${NC}"
        echo "Example: $0 diff frontend src/components/"
        exit 1
    fi
    
    echo -e "${GREEN}Comparing $path between $repo and current monorepo:${NC}"
    
    # Create temp file with historical content
    local temp_file=$(mktemp)
    git --git-dir="$git_dir" show "HEAD:$path" > "$temp_file" 2>/dev/null || {
        echo -e "${RED}Error: Path '$path' not found in $repo repository${NC}"
        rm -f "$temp_file"
        exit 1
    }
    
    # Determine current path based on repository
    local current_path
    case "$repo" in
        frontend)
            current_path="frontend/$path"
            ;;
        backend)
            current_path="backend/$path"
            ;;
        version-0)
            current_path="backend/$path"  # Version 0 maps to current backend
            ;;
        *)
            current_path="$path"
            ;;
    esac
    
    if [[ -f "$current_path" ]]; then
        diff -u "$temp_file" "$current_path" || true
    else
        echo -e "${YELLOW}Warning: Current file '$current_path' does not exist${NC}"
        echo -e "${BLUE}Historical content:${NC}"
        cat "$temp_file"
    fi
    
    rm -f "$temp_file"
}

cmd_extract() {
    local repo="$1"
    local file_path="$2"
    local output_file="$3"
    local git_dir=$(check_repo "$repo")
    
    if [[ -z "$file_path" ]]; then
        echo -e "${RED}Error: Must specify file path to extract${NC}"
        echo "Example: $0 extract $repo apps/people/models.py [output-file]"
        exit 1
    fi
    
    if [[ -z "$output_file" ]]; then
        output_file="/tmp/$(basename "$file_path")-${repo}-$(date +%s)"
    fi
    
    echo -e "${GREEN}Extracting $file_path from $repo repository to $output_file${NC}"
    git --git-dir="$git_dir" show "HEAD:$file_path" > "$output_file"
    echo -e "${GREEN}File extracted successfully${NC}"
}

cmd_branches() {
    local repo="$1"
    local git_dir=$(check_repo "$repo")
    
    echo -e "${GREEN}Branches in $repo repository:${NC}"
    git --git-dir="$git_dir" branch -a
}

cmd_tags() {
    local repo="$1"
    local git_dir=$(check_repo "$repo")
    
    echo -e "${GREEN}Tags in $repo repository:${NC}"
    git --git-dir="$git_dir" tag -l
}

cmd_stats() {
    local repo="$1"
    local git_dir=$(check_repo "$repo")
    
    echo -e "${GREEN}Statistics for $repo repository:${NC}"
    echo ""
    
    echo -e "${BLUE}Commit count:${NC}"
    git --git-dir="$git_dir" rev-list --all --count
    
    echo -e "${BLUE}Contributors:${NC}"
    git --git-dir="$git_dir" shortlog -sn --all
    
    echo -e "${BLUE}Latest commit:${NC}"
    git --git-dir="$git_dir" log -1 --format="%h %ai %s (%an)"
    
    echo -e "${BLUE}Repository size:${NC}"
    du -sh "$git_dir"
}

# Main script logic
if [[ $# -lt 1 ]]; then
    usage
    exit 1
fi

# Check if .git-references directory exists
if [[ ! -d "$GIT_REFS_DIR" ]]; then
    echo -e "${RED}Error: Git references directory not found${NC}"
    echo "Run the setup script first to create historical repository references"
    exit 1
fi

command="$1"
shift

case "$command" in
    log)
        cmd_log "$@"
        ;;
    show)
        cmd_show "$@"
        ;;
    diff)
        cmd_diff "$@"
        ;;
    extract)
        cmd_extract "$@"
        ;;
    branches)
        cmd_branches "$@"
        ;;
    tags)
        cmd_tags "$@"
        ;;
    stats)
        cmd_stats "$@"
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        echo -e "${RED}Error: Unknown command '$command'${NC}"
        echo ""
        usage
        exit 1
        ;;
esac