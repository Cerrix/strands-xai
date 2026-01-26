# strands-xai

[![PyPI version](https://badge.fury.io/py/strands-xai.svg)](https://badge.fury.io/py/strands-xai)
[![Python Support](https://img.shields.io/pypi/pyversions/strands-xai.svg)](https://pypi.org/project/strands-xai/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

xAI model provider for [Strands Agents SDK](https://github.com/strands-agents/sdk-python)

## Features

- **Full Grok Model Support** - Access all xAI Grok models (grok-4, grok-3-mini, etc.)
- **Server-Side Tools** - Use xAI's built-in tools (web_search, x_search, code_execution)
- **Reasoning Models** - Leverage visible reasoning (grok-3-mini) or encrypted reasoning (grok-4)
- **Streaming Support** - Real-time response streaming with full event handling
- **Hybrid Tool Usage** - Combine xAI server-side tools with Strands client-side tools
- **Multi-Turn Context** - Seamless conversation history with encrypted content preservation
- **Type Safe** - Full type hints and mypy support

## Requirements

- Python 3.10+
- Strands Agents SDK 1.23.0+
- xAI API key from [xAI Console](https://console.x.ai/)

## Installation

```bash
pip install strands-agents strands-xai
```

## Quick Start

### Basic Usage

```python
from strands_xai import xAIModel
from strands import Agent

# Initialize xAI model
model = xAIModel(
    client_args={"api_key": "your-xai-api-key"},  # or set XAI_API_KEY env var
    model_id="grok-4-1-fast-non-reasoning-latest",
)

# Create an agent
agent = Agent(model=model)

# Use the agent
result = agent("What is the capital of France?")
print(result)
```

### With Streaming

```python
from strands_xai import xAIModel
from strands import Agent

model = xAIModel(
    client_args={"api_key": "your-xai-api-key"},
    model_id="grok-4-1-fast-non-reasoning-latest",
)

agent = Agent(model=model)

# Streaming is automatic with Strands callback handlers
for chunk in agent.stream("Tell me a story"):
    print(chunk, end="", flush=True)
```

### With Server-Side Tools

```python
from strands_xai import xAIModel
from strands import Agent
from xai_sdk.tools import x_search, web_search

# Use xAI's built-in tools (executed on xAI servers)
model = xAIModel(
    client_args={"api_key": "your-xai-api-key"},
    model_id="grok-4-1-fast-non-reasoning-latest",
    xai_tools=[x_search(), web_search()],
)

agent = Agent(model=model)
result = agent("What are people saying about AI on X?")
print(result)
```

### With Reasoning (grok-3-mini)

```python
from strands_xai import xAIModel
from strands import Agent

# Enable visible reasoning
model = xAIModel(
    client_args={"api_key": "your-xai-api-key"},
    model_id="grok-3-mini",
    reasoning_effort="high",  # "low" or "high"
)

agent = Agent(model=model)
result = agent("Solve this logic puzzle: If all roses are flowers...")
print(result)
```

### With Encrypted Reasoning (grok-4)

For multi-turn conversations with reasoning preserved:

```python
from strands_xai import xAIModel
from strands import Agent

model = xAIModel(
    client_args={"api_key": "your-xai-api-key"},
    model_id="grok-4-fast-reasoning",
    use_encrypted_content=True,  # Preserves reasoning across turns
)

agent = Agent(model=model)

# First turn
result1 = agent("Think through this problem: 2+2")
print(result1)

# Second turn - reasoning context preserved
result2 = agent("Now multiply that by 3")
print(result2)
```

### With Inline Citations

Get sources cited directly in responses:

```python
from strands_xai import xAIModel
from strands import Agent
from xai_sdk.tools import web_search

model = xAIModel(
    client_args={"api_key": "your-xai-api-key"},
    model_id="grok-4-1-fast-non-reasoning-latest",
    xai_tools=[web_search()],
    include=["inline_citations"],  # Enable citations
)

agent = Agent(
    model=model,
    system_prompt="You are a helpful assistant. Always cite sources."
)

result = agent("What are the latest developments in AI?")
print(result)
# Output includes inline citations like [1], [2] with source URLs
```

### Hybrid: Server-Side + Client-Side Tools

```python
from strands_xai import xAIModel
from strands import Agent, tool
from xai_sdk.tools import x_search

@tool
def get_weather(city: str) -> str:
    """Get weather for a city."""
    return f"Weather in {city}: Sunny, 22°C"

# Combine xAI tools with Strands tools
model = xAIModel(
    client_args={"api_key": "your-xai-api-key"},
    model_id="grok-4-1-fast-non-reasoning-latest",
    xai_tools=[x_search()],
)

agent = Agent(model=model, tools=[get_weather])
result = agent("What's the weather in Paris and what are people tweeting about it?")
print(result)
```

## Configuration Options

| Parameter | Type | Description |
|-----------|------|-------------|
| `model_id` | `str` | Grok model ID (e.g., "grok-4", "grok-3-mini") |
| `client_args` | `dict` | Arguments for xAI client (api_key, timeout, etc.) |
| `params` | `dict` | Model parameters (temperature, max_tokens, etc.) |
| `xai_tools` | `list` | Server-side tools from xai_sdk.tools |
| `reasoning_effort` | `str` | "low" or "high" (grok-3-mini only) |
| `use_encrypted_content` | `bool` | Enable encrypted reasoning for multi-turn |
| `include` | `list` | Optional xAI features (e.g., `["inline_citations"]`) |

### Model Parameters

Common parameters you can pass in `params`:

```python
model = xAIModel(
    client_args={"api_key": "your-xai-api-key"},
    model_id="grok-4-1-fast-non-reasoning-latest",
    params={
        "temperature": 0.7,      # 0.0-2.0, controls randomness
        "max_tokens": 2048,      # Maximum tokens in response
        "top_p": 0.9,            # Nucleus sampling
        "frequency_penalty": 0,  # -2.0 to 2.0
        "presence_penalty": 0,   # -2.0 to 2.0
    }
)
```

## Available Models

| Model | Context | Best For |
|-------|---------|----------|
| `grok-4-1-fast-reasoning` | 2M | Fast reasoning with encrypted thinking |
| `grok-4-1-fast-non-reasoning` | 2M | Fast, high-performance inference |
| `grok-4-fast-reasoning` | 2M | Reasoning with encrypted thinking |
| `grok-4-fast-non-reasoning` | 2M | Fast inference without reasoning |
| `grok-4-0709` | 256K | Premium model (higher cost) |
| `grok-code-fast-1` | 256K | Code-optimized model |
| `grok-3-mini` | 131K | Compact with visible reasoning |

See [xAI documentation](https://docs.x.ai/) for pricing and rate limits.

## Server-Side Tools

xAI provides built-in tools executed on their infrastructure:

### Available Tools

- **`web_search()`** - Search the web for current information
- **`x_search()`** - Search X (Twitter) for posts and trends  
- **`code_execution()`** - Execute Python code safely

### Basic Usage

```python
from strands_xai import xAIModel
from strands import Agent
from xai_sdk.tools import web_search, x_search, code_execution

model = xAIModel(
    client_args={"api_key": "your-xai-api-key"},
    model_id="grok-4-1-fast-non-reasoning-latest",
    xai_tools=[web_search(), x_search(), code_execution()],
)

agent = Agent(model=model)
result = agent("What's trending on X about AI?")
```

### Why Server-Side Tools?

- ✅ **No implementation needed** - xAI handles execution
- ✅ **Always up-to-date** - Real-time web/X data
- ✅ **Secure** - Code execution in sandboxed environment
- ✅ **Fast** - Optimized by xAI infrastructure

### Combining with Client-Side Tools

Mix xAI server-side tools with your own Strands tools:

```python
from strands_xai import xAIModel
from strands import Agent, tool
from xai_sdk.tools import x_search

@tool
def get_weather(city: str) -> str:
    """Get weather for a city."""
    return f"Weather in {city}: Sunny, 22°C"

model = xAIModel(
    client_args={"api_key": "your-xai-api-key"},
    model_id="grok-4-1-fast-non-reasoning-latest",
    xai_tools=[x_search()],  # Server-side
)

agent = Agent(
    model=model,
    tools=[get_weather]  # Client-side
)

# Agent can use both types of tools
result = agent("What's the weather in Paris and what are people saying about it on X?")
```

## Examples

See the [examples](examples/) directory for complete working examples.

### Interactive Chat

Full-featured interactive chat with 10 different agent configurations:

```bash
export XAI_API_KEY="your-xai-api-key"
cd strands-xai
source .venv/bin/activate
python examples/interactive_chat.py
```

Choose from:
- Simple (non-streaming)
- Streaming with debug mode
- Client-side tools (calculator, weather)
- Server-side tools (X search, web search)
- Hybrid (both server and client tools)
- Reasoning models (grok-3-mini, grok-4)
- Web search with citations

### Quick Test

```bash
export XAI_API_KEY="your-xai-api-key"
python examples/test_grok_final.py
```

Or use the convenience script:

```bash
./run_examples.sh chat   # Interactive chat
./run_examples.sh test   # Quick test
```

## Development

```bash
# Clone the repository
git clone https://github.com/Cerrix/strands-xai.git
cd strands-xai

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=strands_xai --cov-report=html

# Format code
ruff format .

# Lint code
ruff check .

# Type check
mypy src/strands_xai
```

## Testing

### Unit Tests

The package includes 74 comprehensive unit tests:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=strands_xai --cov-report=html

# Run specific test
pytest tests/test_xai.py::TestBuildChat -v
```

### Integration Tests with Real API

Test with your xAI API key using the example scripts:

```bash
export XAI_API_KEY="your-xai-api-key"

# Interactive testing
python examples/interactive_chat.py

# Quick functionality test
python examples/test_grok_final.py
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- [GitHub Issues](https://github.com/Cerrix/strands-xai/issues)
- [Strands Agents Documentation](https://strandsagents.com/)
- [xAI Documentation](https://docs.x.ai/)

## Acknowledgments

Built for the [Strands Agents](https://github.com/strands-agents/sdk-python) community.
