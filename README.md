# strands-xai

[![PyPI version](https://badge.fury.io/py/strands-xai.svg)](https://badge.fury.io/py/strands-xai)
[![Python Support](https://img.shields.io/pypi/pyversions/strands-xai.svg)](https://pypi.org/project/strands-xai/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

xAI model provider for [Strands Agents SDK](https://github.com/strands-agents/sdk-python)

## Features

- **Full Grok Model Support** - Access all xAI Grok models (grok-4.6, grok-4.5, grok-4.3, grok-4.20-multi-agent, etc.)
- **Multi-Agent Research** - Orchestrate 4 or 16 collaborating agents with grok-4.20-multi-agent
- **Vision & Documents** - Send images and PDF/CSV/DOCX attachments to vision-capable models
- **Server-Side Tools** - Use xAI's built-in tools (web_search, x_search, code_execution, collections_search)
- **Configurable Reasoning** - grok-4.6 adds `xhigh` on top of `low`/`medium`/`high`; grok-4.3 adds `none`
- **Native Tool Choice** - Force a specific tool, any tool, or automatic selection
- **First-Class Citations** - Web and X sources surface as Strands citation blocks
- **Prompt Cache Reporting** - Cached input tokens surfaced as `cacheReadInputTokens` for accurate cost attribution
- **Encrypted Reasoning** - Preserve sub-agent and reasoning state across turns via `use_encrypted_content`
- **Streaming Support** - Real-time response streaming with full event handling
- **Hybrid Tool Usage** - Combine xAI server-side tools with Strands client-side tools
- **Multi-Turn Context** - Seamless conversation history with encrypted content preservation
- **Type Safe** - Full type hints and mypy support

## Requirements

- Python 3.10+
- Strands Agents SDK 1.52.0+
- xai-sdk 1.18.0+ (required for grok-4.6's `xhigh` reasoning level)
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
    model_id="grok-4.6",
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
from strands.handlers.callback_handler import PrintingCallbackHandler

model = xAIModel(
    client_args={"api_key": "your-xai-api-key"},
    model_id="grok-4.6",
)

# Streaming happens automatically with callback handlers
agent = Agent(
    model=model,
    callback_handler=PrintingCallbackHandler()
)

# Text streams to console in real-time
result = agent("Tell me a story")
```

### With Server-Side Tools

```python
from strands_xai import xAIModel
from strands import Agent
from xai_sdk.tools import x_search, web_search

# Use xAI's built-in tools (executed on xAI servers)
model = xAIModel(
    client_args={"api_key": "your-xai-api-key"},
    model_id="grok-4.6",
    xai_tools=[x_search(), web_search()],
)

agent = Agent(model=model)
result = agent("What are people saying about AI on X?")
print(result)
```

### With Reasoning

```python
from strands_xai import xAIModel
from strands import Agent

# Configurable reasoning depth
model = xAIModel(
    client_args={"api_key": "your-xai-api-key"},
    model_id="grok-4.6",
    reasoning_effort="high",  # grok-4.6: "low", "medium", "high" (default), or "xhigh"
)

agent = Agent(model=model)
result = agent("Solve this logic puzzle: If all roses are flowers...")
print(result)
```

Accepted levels differ per model:

| Model | Levels | Default |
|---|---|---|
| `grok-4.6` | `low`, `medium`, `high`, `xhigh` | `high` |
| `grok-4.5` | `low`, `medium`, `high` | `high` |
| `grok-4.3` | `none`, `low`, `medium`, `high` | `low` |

`xhigh` is grok-4.6's deepest setting — it thinks longer and bills more reasoning tokens, so reach for
it on genuinely hard problems rather than as a default. It requires **xai-sdk 1.18.0+**; older SDK
releases reject the value client-side with `ValueError: Invalid reasoning effort`.

> **Note:** neither `grok-4.6` nor `grok-4.5` has a `none` level — they always reason; pass `"low"` for the cheapest/fastest setting. `reasoning_effort` is accepted **only** by `grok-4.6`, `grok-4.5` and `grok-4.3`. The xAI API returns `INVALID_ARGUMENT` if you pass it to `grok-build-0.1`, `grok-4.20-0309-reasoning`, or `grok-4.20-0309-non-reasoning` — those snapshots have their reasoning behavior baked in. On `grok-4.20-multi-agent` use `agent_count` instead — see the [Multi-Agent Research](#multi-agent-research-grok-420-multi-agent) section. Reasoning models do not accept `presence_penalty`, `frequency_penalty`, or `stop` in `params`.

#### What you get back

For every reasoning-capable model (`grok-4.6`, `grok-4.5`, `grok-4.3`, `grok-build-0.1`, `grok-4.20-0309-reasoning`, `grok-4.20-multi-agent`), the SDK streams three signals that this provider surfaces to Strands automatically:

| xAI SDK channel | Strands location | Notes |
|---|---|---|
| `chunk.reasoning_content` | `reasoningContent.reasoningText.text` content blocks | A **summarized** trace of the model's thinking — typically a few hundred characters, and always far shorter than the billed `reasoning_tokens` would imply. The full chain-of-thought is **not** exposed (older models like `grok-3-mini` streamed the raw trace; current Grok models only return this summary). |
| `usage.reasoning_tokens` | metadata `usage.reasoningTokens` | Billed reasoning-token count, even when the summary is short. |
| `final_response.encrypted_content` (only when `use_encrypted_content=True`) | `reasoningContent.redactedContent` | Encrypted full reasoning state, restored verbatim on the next turn for multi-turn context preservation. |

`grok-4.20-0309-non-reasoning` emits none of the above (`reasoning_tokens` is zero and the reasoning channels stay empty), as expected for an inference-only snapshot.

### With Encrypted Reasoning

For multi-turn conversations with reasoning state preserved across turns:

```python
from strands_xai import xAIModel
from strands import Agent

model = xAIModel(
    client_args={"api_key": "your-xai-api-key"},
    model_id="grok-4.6",
    reasoning_effort="medium",
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

> **Note:** `use_encrypted_content` is auto-enabled when `xai_tools` is set so server-side tool state is preserved. You only need to pass it explicitly if you want encrypted reasoning preservation without server-side tools.

### Multi-Agent Research (grok-4.20-multi-agent)

> **Beta:** The multi-agent API is currently in beta on xAI. The interface and behavior may change as it iterates — expect occasional breaking changes.

Orchestrate multiple AI agents that collaborate on research tasks:

```python
from strands_xai import xAIModel
from strands import Agent
from xai_sdk.tools import web_search, x_search

# 4 agents for focused queries, 16 for deep research
model = xAIModel(
    client_args={"api_key": "your-xai-api-key"},
    model_id="grok-4.20-multi-agent",
    xai_tools=[web_search(), x_search()],
    agent_count=4,  # or 16 for comprehensive analysis
)

agent = Agent(model=model)
result = agent("Research the latest breakthroughs in quantum computing")
print(result)
```

> **Notes:**
> - The multi-agent model does **not** support client-side tools (function calling) or `max_tokens`.
> - Only the **leader agent's** output is returned by default. Sub-agent reasoning, tool calls, and outputs are encrypted and only preserved when `use_encrypted_content=True` — which `xAIModel` auto-enables whenever `xai_tools` is set, so multi-turn context is kept intact.
> - All tokens consumed by the leader **and** every sub-agent are billed (input, output, and reasoning), and each agent's server-side tool calls also count against your tool usage. Expect usage to scale with `agent_count`.

### With Inline Citations

Get sources cited directly in responses:

```python
from strands_xai import xAIModel
from strands import Agent
from xai_sdk.tools import web_search

model = xAIModel(
    client_args={"api_key": "your-xai-api-key"},
    model_id="grok-4.6",
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

### Vision (Image Understanding)

Analyze images with vision-capable models:

```python
from strands_xai import xAIModel
from strands import Agent

model = xAIModel(
    client_args={"api_key": "your-xai-api-key"},
    model_id="grok-4.6",  # Vision-capable model
)

agent = Agent(model=model)

# Read image bytes
with open("image.png", "rb") as f:
    image_bytes = f.read()

# Send image as content block
message = [
    {"text": "What's in this image?"},
    {"image": {"format": "png", "source": {"bytes": image_bytes}}}
]

result = agent(message)
print(result)
```

Vision-capable models: `grok-4.6`, `grok-4.5`, `grok-4.3`, `grok-build-0.1`, `grok-4.20-0309-reasoning`, `grok-4.20-0309-non-reasoning`, `grok-4.20-multi-agent`, `grok-4.20-multi-agent-0309`

### Document Attachments

Send PDFs, spreadsheets and other files alongside your prompt. The bytes are attached inline to the
request — no Files API upload step required:

```python
from strands_xai import xAIModel
from strands import Agent

agent = Agent(model=xAIModel(model_id="grok-4.6"))

with open("contract.pdf", "rb") as f:
    pdf_bytes = f.read()

result = agent([
    {"text": "Summarize the termination clauses in this contract."},
    {"document": {"format": "pdf", "name": "contract.pdf", "source": {"bytes": pdf_bytes}}},
])
```

Supported `format` values map to the MIME type xAI expects: `pdf`, `csv`, `doc`, `docx`, `xls`,
`xlsx`, `html`, `txt`, `md`, `json`. An unrecognized format is still sent, as
`application/octet-stream`.

Content blocks that xAI's chat API cannot represent (`video`, `guardContent`) raise `TypeError`
rather than being dropped, so an attachment can never silently go missing from a request.
`cachePoint` blocks are accepted and ignored, because xAI's prompt cache is automatic and has no
explicit breakpoints.

### Forcing Tool Use

`tool_choice` maps onto xAI's native parameter:

```python
from strands import Agent

agent = Agent(model=model, tools=[get_weather, get_time])

# Let the model decide (default)
agent("What's the weather?", tool_choice={"auto": {}})

# Require at least one tool call
agent("What's the weather?", tool_choice={"any": {}})

# Force one specific tool
agent("What's the weather?", tool_choice={"tool": {"name": "get_weather"}})
```

`tool_choice` is only sent when tools are present, since xAI rejects it otherwise.

### Citations

When a server-side search tool runs, sources surface as standard Strands citation blocks
(`contentBlockDelta.delta.citation`) with the URL under `location.web.url`, so anything consuming
the normal content stream sees them:

```python
from xai_sdk.tools import web_search

model = xAIModel(
    model_id="grok-4.6",
    xai_tools=[web_search()],
    include=["inline_citations"],  # adds position-aware citations with display ids
)
```

Both of xAI's citation channels are normalized and de-duplicated: plain source URLs and, when
`include=["inline_citations"]` is set, the richer inline entries for web and X results. The legacy
non-standard `metadata["citations"]` key is still emitted for backwards compatibility.

`x_search` sources are cited the same way — an X post URL arrives under `location.web.url`, because
Strands' citation location has no X-specific variant. A hybrid `[web_search(), x_search()]` run
yields article URLs and `x.com` post URLs in one de-duplicated stream.

> **Note on tool names:** the names xAI reports in `metadata["serverToolCalls"]` are the underlying
> operations, not the helper you configured. `x_search()` shows up as `x_keyword_search` and
> `x_semantic_search`, and xAI may also invoke `open_page` on its own to read a result it found. If
> you filter on these names, match those rather than the helper name.

Inline citations are captured as they stream rather than read off the final response, because xAI
populates them on intermediate responses and leaves the final one empty.

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
    model_id="grok-4.6",
    xai_tools=[x_search()],
)

agent = Agent(model=model, tools=[get_weather])
result = agent("What's the weather in Paris and what are people tweeting about it?")
print(result)
```

## Configuration Options

| Parameter | Type | Description |
|-----------|------|-------------|
| `model_id` | `str` | Grok model ID (e.g., "grok-4.6", "grok-4.5", "grok-4.20-multi-agent") |
| `client_args` | `dict` | Arguments for xAI client (api_key, timeout, etc.) |
| `params` | `dict` | Model parameters (temperature, max_tokens, etc.). Reasoning models reject `presence_penalty`, `frequency_penalty`, and `stop`. |
| `xai_tools` | `list` | Server-side tools from xai_sdk.tools |
| `reasoning_effort` | `str` | grok-4.6: `"low"`, `"medium"`, `"high"` (default), `"xhigh"`. grok-4.5 drops `"xhigh"`; grok-4.3 adds `"none"` (default `"low"`) |
| `use_encrypted_content` | `bool` | Preserve reasoning / sub-agent state across turns (auto-enabled when `xai_tools` is set) |
| `include` | `list` | Optional xAI features (e.g., `["inline_citations"]`) |
| `agent_count` | `int` | Number of agents (4 or 16) for grok-4.20-multi-agent |
| `context_window_limit` | `int` | Context window in tokens. Resolved automatically from `model_id` (grok-4.6/4.5 500K, grok-4.3 1M, grok-build-0.1 256K, grok-4.20-* 1M); set it only for a model this provider doesn't know yet, or to deliberately cap the window |

### Context management

Strands uses `context_window_limit` to decide when to compact a conversation and to compute
utilization. This provider resolves it from the model id, so compaction triggers against the real
window:

```python
model = xAIModel(model_id="grok-4.6")
model.context_window_limit   # 500000
```

Without it, Strands falls back to its own 200K default, which would compact a grok-4.6 conversation
at 40% of the real window (and a grok-4.3 one at 20%) and log a warning. An explicitly configured
value always wins over the lookup.

### Model Parameters

Common parameters you can pass in `params`:

```python
model = xAIModel(
    client_args={"api_key": "your-xai-api-key"},
    model_id="grok-4.6",
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

| Model | Context | Vision | Best For |
|-------|---------|--------|----------|
| `grok-4.6` | 500K | ✅ | **Frontier default** — coding, agentic tasks, knowledge work; adds `xhigh` reasoning ($2/$6 per MTok) |
| `grok-4.5` | 500K | ✅ | Previous frontier model; cheaper cached input than 4.6 ($2/$6 per MTok) |
| `grok-4.3` | 1M | ✅ | Long context (1M) at lower cost, or when you need `reasoning_effort="none"` ($1.25/$2.50 per MTok) |
| `grok-build-0.1` | 256K | ✅ | Agentic coding, early access — superseded by grok-4.6 ($1/$2 per MTok) |
| `grok-4.20-multi-agent` | 1M | ✅ | Multi-agent research — rolling alias |
| `grok-4.20-multi-agent-0309` | 1M | ✅ | Multi-agent research — pinned snapshot ($1.25/$2.50 per MTok) |
| `grok-4.20-0309-reasoning` | 1M | ✅ | Pinned 4.20 reasoning snapshot ($1.25/$2.50 per MTok) |
| `grok-4.20-0309-non-reasoning` | 1M | ✅ | Pinned 4.20 inference snapshot ($1.25/$2.50 per MTok) |

xAI's own guidance is to use **grok-4.6** for everything text-based, including code. Its knowledge cutoff is
February 1, 2026, and it is available in `us-east-1` and `us-west-2`.

Pricing is shown as input/output per million tokens. Dated `*-0309` IDs are pinned snapshots; the unsuffixed `grok-4.20-multi-agent` is a rolling alias that points to the latest stable revision. See [xAI documentation](https://docs.x.ai/docs/models) for the authoritative pricing and rate-limit reference.

### Long-context pricing

Every current Grok model uses **tiered long-context pricing**: once a request's prompt reaches
200K tokens, *all* tokens in that request are billed at the higher rate.

| Model | < 200K prompt | ≥ 200K prompt |
|---|---|---|
| `grok-4.6` | $2.00 in / $0.50 cached / $6.00 out | $4.00 in / $1.00 cached / $12.00 out |
| `grok-4.5` | $2.00 in / $0.30 cached / $6.00 out | $4.00 in / $0.60 cached / $12.00 out |
| `grok-4.3` | $1.25 in / $0.20 cached / $2.50 out | $2.50 in / $0.40 cached / $5.00 out |

grok-4.6 matches grok-4.5 on fresh input and output but charges **more for cached input**
($0.50 vs $0.30 per MTok), so a heavily cache-reliant workload is the one case where 4.5 is still
cheaper. Both are roughly 1.6× the input and 2.4× the output cost of grok-4.3, with a smaller
(500K vs 1M) context window — pick them for capability, not for price or raw context length.

### Prompt caching

Cached input tokens cost a fraction of fresh input ($0.50 vs $2.00 per MTok on grok-4.6), and this
provider reports them to Strands as `cacheReadInputTokens` so cost backends can apply the discount:

```python
result = agent("...")
print(result.metrics.accumulated_usage)
# {'inputTokens': 4120, 'outputTokens': 380, 'totalTokens': 4500, 'cacheReadInputTokens': 3712}
```

`cacheReadInputTokens` is the **subset** of `inputTokens` that was served from cache — it is not
added on top (the same convention Strands' OpenAI and LiteLLM providers use). It also surfaces on
the OpenTelemetry span as `gen_ai.usage.cache_read_input_tokens`.

xAI recommends pinning a conversation to one server so cache hits are reliable. The gRPC `xai_sdk`
this provider wraps does **not** expose the Responses-API `prompt_cache_key` parameter, so there is
no strands-xai config option for it; caching still works server-side, but hit rates depend on
routing. You can pass the SDK's `conversation_id` through `params` for trace grouping:

```python
model = xAIModel(model_id="grok-4.6", params={"conversation_id": "user-42-session-7"})
```

Keep the stable prefix of your prompt (system prompt, tool definitions) byte-identical across turns
— any change to it invalidates the cache.

### Model aliases

xAI follows a consistent alias convention for every model line:

| Form | Resolves to | Use when |
|---|---|---|
| `<modelname>` | latest **stable** version | recommended default — picks up patches automatically |
| `<modelname>-latest` | latest version (may include preview features) | you want the bleeding edge |
| `<modelname>-<date>` | a specific dated snapshot | reproducibility-critical workloads that must not move |

So for `grok-4.6` the forms are `grok-4.6` / `grok-4.6-latest`; for the multi-agent line they are `grok-4.20-multi-agent` / `grok-4.20-multi-agent-latest` / `grok-4.20-multi-agent-0309`. Two extra aliases resolve to the current flagship: **`grok-build-latest`** (the Grok Build coding agent's default, which is why `grok-build-0.1` is effectively superseded) and the generic `grok-latest`. Pass any of these as `model_id` — the SDK forwards the string verbatim, so you control which side of the rolling/pinned trade-off you take.

> **Note:** `xai_sdk` 1.18.0 lists `grok-4.6` and `grok-4.5` in its `ChatModel` type alias, and its `model` parameter is typed `ChatModel | str` regardless, so any current or future slug is valid at runtime and under mypy. This provider maintains no allow-list of model IDs — unknown slugs are forwarded as-is (they simply fall back to Strands' default context window until added to the table).

### Retired model aliases

The following slugs were retired on 2026-05-15 and now silently redirect (and are billed) at `grok-4.3` or `grok-build-0.1` rates. Update your code to migrate explicitly:

| Retired slug | Now routed to |
|---|---|
| `grok-4-1-fast-reasoning`, `grok-4-fast-reasoning`, `grok-4-0709`, `grok-4`, `grok-4-latest` | `grok-4.3` with `reasoning_effort="low"` |
| `grok-4-1-fast-non-reasoning`, `grok-4-fast-non-reasoning`, `grok-3` | `grok-4.3` with `reasoning_effort="none"` |
| `grok-3-mini` and all `grok-3-mini-*` variants | `grok-4.3` |
| `grok-code-fast-1`, `grok-code-fast`, `grok-code-fast-1-0825` | `grok-build-0.1` |

## Server-Side Tools

xAI provides built-in tools executed on their infrastructure:

### Available Tools

- **`web_search()`** - Search the web for current information
- **`x_search()`** - Search X (Twitter) for posts and trends
- **`code_execution()`** - Execute Python code safely
- **`collections_search()`** - Search uploaded document collections (RAG)

### Basic Usage

```python
from strands_xai import xAIModel
from strands import Agent
from xai_sdk.tools import web_search, x_search, code_execution

model = xAIModel(
    client_args={"api_key": "your-xai-api-key"},
    model_id="grok-4.6",
    xai_tools=[web_search(), x_search(), code_execution()],
)

agent = Agent(model=model)
result = agent("What's trending on X about AI?")
```

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
    model_id="grok-4.6",
    xai_tools=[x_search()],  # Server-side
)

agent = Agent(
    model=model,
    tools=[get_weather]  # Client-side
)

# Agent can use both types of tools
result = agent("What's the weather in Paris and what are people saying about it on X?")
```

## Observability / OpenTelemetry

### Using strands-xai with OpenTelemetry

Strands instruments each model call and emits spans with correct token usage. The underlying `xai_sdk` also has its own OpenTelemetry instrumentation, which emits a duplicate `chat.stream` span for the same call. That extra span reports token usage in xAI's raw form (output excludes reasoning, total includes it), which can make trace-level totals inconsistent in observability tools.

When running strands-xai with any OpenTelemetry backend, disable `xai_sdk`'s own tracing so only Strands' spans are exported:

```bash
export XAI_SDK_DISABLE_TRACING=1
```

Set it in your environment **before** starting the process — `xai_sdk` binds its tracer at import time, so setting it from Python after import has no effect. With this set, traces contain a single clean span tree and token totals reconcile (`input + output == total`, with reasoning folded into output).

### Cost tracking and the qualified model id

You construct the model exactly as normal — `xAIModel(model_id="grok-4.5")`. Internally, the provider stores the **provider-qualified** id `xai/grok-4.5` in its config, and that is what appears on the trace as `gen_ai.request.model`. This is intentional: cost backends (LiteLLM, SideSeat, etc.) price Grok under the qualified key `xai/<model>` — there is no bare `grok-*` price key — so the qualified id is what lets them attach a non-zero cost. The xAI SDK itself is always called with the **bare** id (`grok-4.5`); the `xai/` prefix is stripped at the call site, so inference is unaffected.

You can pass either form (`"grok-4.5"` or `"xai/grok-4.5"`) — normalization is idempotent. The only observable change is that `model.get_config()["model_id"]` now returns the qualified `xai/grok-4.5`.

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
- Reasoning models (grok-4.5 with configurable effort)
- Multi-agent research (grok-4.20-multi-agent)
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

The package includes a comprehensive unit test suite:

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
