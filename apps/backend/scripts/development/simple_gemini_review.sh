#!/bin/bash
# Simple Gemini Code Review for Academic App
# This script manually creates a working review command

set -e

WORKING_DIR="/Users/jeffreystark/PycharmProjects/naga-monorepo/backend/project-docs/working-folder"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RESULTS_FILE="$WORKING_DIR/review_results_academic_manual_$TIMESTAMP.md"

echo "🚀 Manual Gemini Code Review for Academic App"
echo "📄 Results will be saved to: $RESULTS_FILE"
echo ""

# Check if gemini-cli is available
if ! command -v gemini-cli &> /dev/null; then
    echo "❌ Gemini CLI not found. Install with: npm install -g @google/generative-ai-cli"
    exit 1
fi

echo "🤖 Executing Gemini review..."
echo ""

# Create the prompt and pipe to gemini-cli, then save to file
cat << 'EOF' | gemini-cli > "$RESULTS_FILE"
You are a senior Python engineer reviewing Django code from a junior developer. Your goal is to provide constructive, mentoring feedback that helps them improve their skills. Your tone should be helpful and educational.

Please analyze the following Django academic app code and provide actionable suggestions. For each suggestion, provide:
1. A clear explanation of the issue
2. Before and after code examples

Focus on:
- Performance (N+1 queries, inefficient operations)
- Django best practices (ORM usage, admin customizations)
- Security vulnerabilities
- Code organization and readability

Here is the academic app code to review:

```python
EOF

# Append the actual code file
cat "$WORKING_DIR/gemini_review_academic_20250717_194739.txt" >> "$RESULTS_FILE.tmp"

# Combine prompt with code
cat << 'EOF' >> "$RESULTS_FILE.tmp"
```

Please provide your review with specific, actionable improvements.
EOF

# Now send the complete prompt to Gemini
echo "Sending code to Gemini for review..."
cat "$RESULTS_FILE.tmp" | gemini-cli > "$RESULTS_FILE"

# Cleanup temp file
rm -f "$RESULTS_FILE.tmp"

if [ -f "$RESULTS_FILE" ] && [ -s "$RESULTS_FILE" ]; then
    echo "✅ Review completed successfully!"
    echo "📄 Results saved to: $RESULTS_FILE"
    echo ""
    echo "📊 Review stats:"
    echo "   Lines: $(wc -l < "$RESULTS_FILE")"
    echo "   Characters: $(wc -c < "$RESULTS_FILE")"
    echo ""
    echo "📋 Preview (first 10 lines):"
    head -10 "$RESULTS_FILE" | sed 's/^/   /'
else
    echo "❌ Review failed - no output generated"
    exit 1
fi

echo ""
echo "🎉 Academic app code review complete!"
echo "📖 Full review: $RESULTS_FILE"