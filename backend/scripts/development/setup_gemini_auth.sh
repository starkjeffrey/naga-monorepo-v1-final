#!/bin/bash
# Gemini CLI Authentication Setup Script

echo "🔐 Gemini CLI Authentication Setup"
echo "=================================="
echo ""
echo "To authenticate with Gemini CLI, you have two options:"
echo ""
echo "Option 1: Set API Key as Environment Variable"
echo "1. Go to: https://makersuite.google.com/app/apikey"
echo "2. Sign in with your Google account"
echo "3. Create a new API key"
echo "4. Copy the API key"
echo "5. Set it as an environment variable:"
echo ""
echo "   export GOOGLE_AI_API_KEY=\"your-api-key-here\""
echo ""
echo "Option 2: Interactive Setup"
echo "Run gemini-cli and it will prompt you for the API key on first use."
echo ""
echo "After authentication, you can test with:"
echo "   echo 'Hello, test message' | gemini-cli"
echo ""
echo "Then run your code review:"
echo "   bash project-docs/working-folder/gemini_review_academic_20250717_194739.sh"
echo ""

# Check if API key is already set
if [ -n "$GOOGLE_AI_API_KEY" ]; then
    echo "✅ GOOGLE_AI_API_KEY is already set in environment"
    echo "🚀 You're ready to run code reviews!"
else
    echo "⚠️  GOOGLE_AI_API_KEY not set in environment"
    echo "📝 You'll need to set it manually or use interactive mode"
fi

echo ""
echo "📚 Resources:"
echo "- Google AI Studio: https://makersuite.google.com/"
echo "- Gemini CLI docs: https://github.com/google/generative-ai-cli"