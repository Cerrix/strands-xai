"""Final validation test for xAI model provider.

Tests all the examples from the PR description.
Run with: hatch run python test_grok_final.py
"""

import json
import os

import boto3

from strands import Agent
from strands_xai import xAIModel


def get_text(result) -> str:
    """Extract text from result."""
    text_parts = []
    for content_block in result.message["content"]:
        if "text" in content_block:
            text_parts.append(content_block["text"])
    return " ".join(text_parts)


def get_api_key() -> str:
    """Get XAI API key from environment or AWS Secrets Manager."""
    if os.getenv("XAI_API_KEY"):
        return os.getenv("XAI_API_KEY")

    session = boto3.session.Session(region_name="us-west-2")
    client = session.client(service_name="secretsmanager")
    secret_name = "strands-agents-test-api-keys"
    response = client.get_secret_value(SecretId=secret_name)
    if "SecretString" in response:
        secret = json.loads(response["SecretString"])
        return secret.get("xai", secret.get("XAI"))
    raise ValueError("XAI_API_KEY not found")


def test_basic_usage(api_key: str) -> None:
    """Test basic usage."""
    print("\n" + "=" * 60)
    print("TEST 1: Basic usage")
    print("=" * 60)

    model = xAIModel(
        client_args={"api_key": api_key},
        model_id="grok-4-1-fast-non-reasoning-latest",
    )
    agent = Agent(model=model)
    result = agent("Hello! Say hi back in one word.")

    text = get_text(result)
    print(f"Result: {text}")
    assert text, "Should have text response"
    print("✅ PASSED")


def test_reasoning_model(api_key: str) -> None:
    """Test reasoning model (grok-3-mini)."""
    print("\n" + "=" * 60)
    print("TEST 2: Reasoning model (grok-3-mini)")
    print("=" * 60)

    model = xAIModel(
        client_args={"api_key": api_key},
        model_id="grok-3-mini",
        reasoning_effort="high",
    )
    agent = Agent(model=model)
    result = agent("What is 15 + 27?")

    text = get_text(result)
    print(f"Result: {text}")
    assert "42" in text, "Should contain 42"
    print("✅ PASSED")


def test_encrypted_reasoning_multi_turn(api_key: str) -> None:
    """Test encrypted reasoning for multi-turn context (grok-4)."""
    print("\n" + "=" * 60)
    print("TEST 3: Encrypted reasoning multi-turn (grok-4)")
    print("=" * 60)

    model = xAIModel(
        client_args={"api_key": api_key},
        model_id="grok-4-fast-reasoning",
        use_encrypted_content=True,
    )
    agent = Agent(model=model)

    # Turn 1
    print("Turn 1: What is 2+2?")
    result1 = agent("What is 2+2?")
    text1 = get_text(result1)
    print(f"Response: {text1}")

    # Turn 2 - should remember context
    print("\nTurn 2: +5?")
    result2 = agent("+5?")
    text2 = get_text(result2)
    print(f"Response: {text2}")

    assert "9" in text2 or "seven" in text2.lower(), "Should understand context and return 9"
    print("✅ PASSED")


def test_server_side_tools(api_key: str) -> None:
    """Test server-side tools (executed by xAI)."""
    print("\n" + "=" * 60)
    print("TEST 4: Server-side tools (web_search)")
    print("=" * 60)

    from xai_sdk.tools import web_search

    model = xAIModel(
        client_args={"api_key": api_key},
        model_id="grok-4-1-fast-non-reasoning-latest",
        xai_tools=[web_search()],
    )
    agent = Agent(model=model)
    result = agent("What is the current year? Use web search.")

    text = get_text(result)
    print(f"Result: {text}")
    assert any(year in text for year in ["2025", "2026"]), "Should return current year"
    print("✅ PASSED")


def test_hybrid_tools(api_key: str) -> None:
    """Test combining server-side and client-side tools."""
    print("\n" + "=" * 60)
    print("TEST 5: Hybrid tools (server + client)")
    print("=" * 60)

    from xai_sdk.tools import x_search

    from strands import tool

    @tool
    def get_weather(city: str) -> str:
        """Get the weather for a city."""
        return f"Weather in {city}: Sunny, 22°C"

    model = xAIModel(
        client_args={"api_key": api_key},
        model_id="grok-4-1-fast-non-reasoning-latest",
        xai_tools=[x_search()],
    )
    agent = Agent(model=model, tools=[get_weather])
    result = agent("What's the weather in Paris?")

    text = get_text(result)
    print(f"Result: {text}")
    assert "22" in text or "sunny" in text.lower(), "Should use client-side tool"
    print("✅ PASSED")


def main() -> None:
    """Run all tests."""
    print("=" * 60)
    print("xAI MODEL PROVIDER - FINAL VALIDATION")
    print("=" * 60)

    api_key = get_api_key()

    tests = [
        ("Basic usage", test_basic_usage),
        ("Reasoning model", test_reasoning_model),
        ("Encrypted reasoning multi-turn", test_encrypted_reasoning_multi_turn),
        ("Server-side tools", test_server_side_tools),
        ("Hybrid tools", test_hybrid_tools),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        try:
            test_fn(api_key)
            passed += 1
        except Exception as e:
            print(f"❌ FAILED: {name}")
            print(f"   Error: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed > 0:
        exit(1)


if __name__ == "__main__":
    main()
