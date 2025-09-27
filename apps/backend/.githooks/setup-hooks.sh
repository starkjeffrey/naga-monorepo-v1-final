#!/bin/bash

# Setup script for git hooks

echo "🔧 Setting up git hooks for backend file organization..."

# Set git to use our hooks directory
git config core.hooksPath .githooks

echo "✅ Git hooks configured!"
echo ""
echo "The pre-commit hook will now:"
echo "  • Block commits with files in backend/ root directory"
echo "  • Suggest proper locations for different file types"
echo "  • Help maintain clean project structure"
echo ""
echo "To disable hooks temporarily: git config --unset core.hooksPath"
echo "To re-enable: git config core.hooksPath .githooks"