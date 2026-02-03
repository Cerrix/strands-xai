#!/usr/bin/env python3
"""Test vision support with strands-xai."""

import asyncio
import io
import os

from PIL import Image
from strands import Agent
from strands_xai import xAIModel


async def test_vision():
    """Test that vision models can analyze images."""
    # Create a simple red square
    img = Image.new("RGB", (100, 100), color="red")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    image_bytes = buffer.getvalue()

    model = xAIModel(model_id="grok-4-1-fast-reasoning")
    agent = Agent(model=model)

    # Send image as content block
    message = [
        {"text": "What color is this image? Reply with just the color name."},
        {"image": {"format": "png", "source": {"bytes": image_bytes}}},
    ]

    response = ""
    async for event in agent.stream_async(message):
        if "data" in event:
            response += event["data"]

    assert "red" in response.lower(), f"Expected 'red' in response, got: {response}"
    print(f"✅ Vision test passed: {response.strip()}")


if __name__ == "__main__":
    if not os.getenv("XAI_API_KEY"):
        print("Set XAI_API_KEY")
        exit(1)
    asyncio.run(test_vision())
