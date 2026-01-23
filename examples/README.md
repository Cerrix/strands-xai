# Examples

This directory contains example scripts for testing and demonstrating the strands-xai package.

## Interactive Chat (`interactive_chat.py`)

Full-featured interactive chat with 10 different agent configurations:

```bash
# Set your API key
export XAI_API_KEY="your-xai-api-key"

# Run the interactive chat
cd /Users/francesco/git/strands-xai
source .venv/bin/activate
python examples/interactive_chat.py
```

**Available configurations**:
1. Simple (non-streaming)
2. Streaming
3. Streaming (DEBUG)
4. Strands tools (calculator, weather)
5. X search (server-side)
6. Hybrid (server + client tools)
7. Reasoning (grok-3-mini)
8. Reasoning encrypted (grok-4)
9. Reasoning encrypted DEBUG
10. Web search + citations

## Quick Test (`test_grok_final.py`)

Simple test script for basic functionality:

```bash
export XAI_API_KEY="your-xai-api-key"
cd /Users/francesco/git/strands-xai
source .venv/bin/activate
python examples/test_grok_final.py
```

## Running Examples

All examples require:
- Active virtual environment: `source .venv/bin/activate`
- XAI API key set: `export XAI_API_KEY="your-key"`
- Package installed: Already done with `uv pip install -e ".[dev]"`
