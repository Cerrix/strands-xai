#!/bin/bash
# Quick test script for strands-xai examples

set -e

# Check if API key is set
if [ -z "$XAI_API_KEY" ]; then
    echo "❌ Error: XAI_API_KEY environment variable not set"
    echo ""
    echo "Set it with:"
    echo "  export XAI_API_KEY='your-xai-api-key'"
    exit 1
fi

# Activate virtual environment
if [ ! -d ".venv" ]; then
    echo "❌ Error: Virtual environment not found"
    echo "Run: uv venv && source .venv/bin/activate && uv pip install -e '.[dev]'"
    exit 1
fi

source .venv/bin/activate

echo "🚀 Running strands-xai examples..."
echo ""

# Choose which example to run
if [ "$1" = "chat" ]; then
    echo "📱 Starting interactive chat..."
    python examples/interactive_chat.py
elif [ "$1" = "test" ]; then
    echo "🧪 Running quick test..."
    python examples/test_grok_final.py
else
    echo "Usage:"
    echo "  ./run_examples.sh chat   # Interactive chat with 10 configurations"
    echo "  ./run_examples.sh test   # Quick functionality test"
    echo ""
    echo "Or run directly:"
    echo "  source .venv/bin/activate"
    echo "  python examples/interactive_chat.py"
    echo "  python examples/test_grok_final.py"
fi
