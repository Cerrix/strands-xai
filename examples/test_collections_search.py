"""Test collections_search server-side tool with strands-xai.

Requires:
  - XAI_API_KEY env var
  - XAI_COLLECTION_ID env var (e.g. "collection_xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
  - The collection must be indexed and ready

Run with:
    XAI_API_KEY=... XAI_COLLECTION_ID=... .venv/bin/python examples/test_collections_search.py
"""

import os
import sys

from strands import Agent
from strands.handlers.callback_handler import PrintingCallbackHandler
from xai_sdk.tools import collections_search

from strands_xai import xAIModel


def test_collections_search_basic():
    """Test basic collections_search with a simple query."""
    collection_id = os.environ["XAI_COLLECTION_ID"]
    print(f"\n=== Test: collections_search (collection: {collection_id}) ===")

    model = xAIModel(
        model_id="grok-4.20-reasoning",
        xai_tools=[collections_search(collection_ids=[collection_id])],
    )

    agent = Agent(model=model, callback_handler=PrintingCallbackHandler())
    result = agent("What documents are available in the collection? Summarize what you find in 2-3 sentences.")
    print(f"\nResult: {result}")
    print("PASS")


def test_collections_search_with_web_search():
    """Test hybrid: collections_search + web_search."""
    from xai_sdk.tools import web_search

    collection_id = os.environ["XAI_COLLECTION_ID"]
    print(f"\n=== Test: collections_search + web_search (hybrid) ===")

    model = xAIModel(
        model_id="grok-4.20-reasoning",
        xai_tools=[
            collections_search(collection_ids=[collection_id]),
            web_search(),
        ],
    )

    agent = Agent(model=model, callback_handler=PrintingCallbackHandler())
    result = agent(
        "Search my collection for the main topics covered, then do a quick web search "
        "to find any recent news related to those topics. Keep the summary brief."
    )
    print(f"\nResult: {result}")
    print("PASS")


if __name__ == "__main__":
    if not os.getenv("XAI_API_KEY"):
        print("ERROR: Set XAI_API_KEY environment variable")
        sys.exit(1)
    if not os.getenv("XAI_COLLECTION_ID"):
        print("ERROR: Set XAI_COLLECTION_ID environment variable")
        print("Example: export XAI_COLLECTION_ID=collection_xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
        sys.exit(1)

    test_collections_search_basic()
    test_collections_search_with_web_search()
    print("\n=== All collections_search tests passed! ===")
