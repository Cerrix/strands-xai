"""Quick smoke test for new Grok 4.20 models.

Run with: XAI_API_KEY=... .venv/bin/python examples/test_grok420.py
"""

import os

from strands import Agent
from strands.handlers.callback_handler import PrintingCallbackHandler

from strands_xai import xAIModel


def test_grok420_reasoning():
    """Test grok-4.20-reasoning basic usage."""
    print("\n=== Test: grok-4.20-reasoning ===")
    model = xAIModel(
        model_id="grok-4.20-reasoning",
    )
    agent = Agent(model=model, callback_handler=PrintingCallbackHandler())
    result = agent("What is 2+2? Reply in one sentence.")
    print(f"\nResult: {result}")


def test_grok420_non_reasoning():
    """Test grok-4.20-non-reasoning basic usage."""
    print("\n=== Test: grok-4.20-non-reasoning ===")
    model = xAIModel(
        model_id="grok-4.20-non-reasoning",
    )
    agent = Agent(model=model, callback_handler=PrintingCallbackHandler())
    result = agent("What is the capital of France? Reply in one sentence.")
    print(f"\nResult: {result}")


def test_grok420_multi_agent():
    """Test grok-4.20-multi-agent with web search."""
    print("\n=== Test: grok-4.20-multi-agent (4 agents) ===")
    from xai_sdk.tools import web_search

    model = xAIModel(
        model_id="grok-4.20-multi-agent",
        xai_tools=[web_search()],
        agent_count=4,
    )
    agent = Agent(model=model, callback_handler=PrintingCallbackHandler())
    result = agent("What are the latest developments in AI? Keep it brief.")
    print(f"\nResult: {result}")


if __name__ == "__main__":
    if not os.getenv("XAI_API_KEY"):
        print("ERROR: Set XAI_API_KEY environment variable")
        exit(1)

    test_grok420_reasoning()
    test_grok420_non_reasoning()
    test_grok420_multi_agent()
    print("\n=== All Grok 4.20 tests passed! ===")
