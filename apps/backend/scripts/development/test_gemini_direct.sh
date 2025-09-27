#!/bin/bash
# Simple test script to verify Gemini CLI works with a small prompt

echo "🚀 Testing Gemini CLI with simple prompt..."

# Create a simple test prompt
TEST_PROMPT="You are a Python code reviewer. Please review this simple Python function and provide one improvement suggestion:

def calculate_total(items):
    total = 0
    for item in items:
        total = total + item
    return total

Provide a brief suggestion for improvement."

echo "📝 Test prompt created"
echo "🤖 Sending to Gemini CLI..."
echo ""

# Try to execute gemini-cli with the test prompt
echo "$TEST_PROMPT" | gemini-cli

echo ""
echo "✅ Test complete!"