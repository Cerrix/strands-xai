"""Strands Agents - xAI Model Interactive Chat.

This script provides an interactive multi-turn chat with different xAI agent configurations:
1. Simple non-streaming agent
2. Simple streaming agent  
3. Agent with Strands tools (client-side function calling)
4. Agent with X search server-side tool
5. Agent with both X search (server-side) and Strands tools (client-side)

Run with: hatch run python test_grok_strands.py
"""

import json
import os
import sys
from typing import Any

import boto3

from strands import Agent, tool
from strands.handlers.callback_handler import PrintingCallbackHandler
from strands_xai import xAIModel


# =============================================================================
# API KEY HELPER
# =============================================================================

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


# =============================================================================
# STRANDS TOOLS (CLIENT-SIDE)
# =============================================================================

@tool
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression.
    
    Args:
        expression: A mathematical expression to evaluate (e.g., "2 + 2", "15 * 7")
        
    Returns:
        The result of the calculation
    """
    try:
        allowed = set("0123456789+-*/.() ")
        if all(c in allowed for c in expression):
            result = eval(expression)
            return f"Result: {result}"
        return "Error: Invalid expression"
    except Exception as e:
        return f"Error: {e}"


@tool
def get_weather(city: str) -> str:
    """Get the current weather for a city.
    
    Args:
        city: Name of the city
        
    Returns:
        Weather description for the city
    """
    weather_data = {
        "paris": "Sunny, 22°C",
        "london": "Cloudy, 15°C", 
        "tokyo": "Rainy, 18°C",
        "new york": "Clear, 20°C",
    }
    city_lower = city.lower()
    if city_lower in weather_data:
        return f"Weather in {city}: {weather_data[city_lower]}"
    return f"Weather in {city}: Partly cloudy, 20°C (default)"


# =============================================================================
# CALLBACK HANDLERS
# =============================================================================

class StreamingCallbackHandler(PrintingCallbackHandler):
    """Callback handler that shows streaming text output.
    
    Server-side tools (x_search, web_search, etc.) are emitted inline as text
    in the format: [xAI Tool: tool_name({arguments})]
    
    Visually separates reasoning content from final answers.
    """
    
    def __init__(self, debug: bool = False, show_reasoning: bool = True):
        super().__init__(verbose_tool_use=True)
        self.debug = debug
        self.show_reasoning = show_reasoning
        self._in_reasoning = False
        self._reasoning_started = False
    
    def __call__(self, **kwargs: Any) -> None:
        # Handle reasoning content with visual styling
        if "reasoningText" in kwargs:
            if self.show_reasoning:
                if not self._reasoning_started:
                    print("\n\033[2m💭 Thinking...\033[0m", flush=True)
                    self._reasoning_started = True
                # Print reasoning in dim/italic style
                print(f"\033[2;3m{kwargs['reasoningText']}\033[0m", end="", flush=True)
            return
        
        # Detect transition from reasoning to final answer
        if "data" in kwargs and self._reasoning_started and not self._in_reasoning:
            print("\n\033[2m───────────────────────────────────────\033[0m")
            print("\033[1m📝 Answer:\033[0m ", end="", flush=True)
            self._in_reasoning = True
        
        # Reset state on new message
        if "complete" in kwargs and kwargs.get("complete"):
            self._reasoning_started = False
            self._in_reasoning = False
        
        if self.debug:
            # Debug mode: show all kwargs (filter out empty values for readability)
            filtered = {k: v for k, v in kwargs.items() 
                       if v is not None and v != "" and v != {} and k != "delta"}
            if filtered:
                # Format nicely
                print(f"\n[DEBUG] {list(filtered.keys())}: ", end="")
                for k, v in filtered.items():
                    if k == "data":
                        print(f"'{v}'", end=" ")
                    elif k == "current_tool_use":
                        print(f"tool={v.get('name', 'unknown')}", end=" ")
                    elif k == "reasoningText":
                        print(f"reasoning='{v[:50]}...'" if len(str(v)) > 50 else f"reasoning='{v}'", end=" ")
                    else:
                        print(f"{k}={v}", end=" ")
        else:
            # Normal mode: just stream text (server-side tools appear inline automatically)
            super().__call__(**kwargs)


# =============================================================================
# AGENT CONFIGURATIONS
# =============================================================================

def create_simple_agent(api_key: str) -> Agent:
    """Create a simple non-streaming agent."""
    model = xAIModel(
        client_args={"api_key": api_key},
        model_id="grok-4-1-fast-non-reasoning-latest",
    )
    return Agent(
        model=model,
        system_prompt="You are a helpful assistant. Be concise.",
        callback_handler=None,
    )


def create_streaming_agent(api_key: str, debug: bool = False) -> Agent:
    """Create a streaming agent with optional debug mode."""
    model = xAIModel(
        client_args={"api_key": api_key},
        model_id="grok-4-1-fast-non-reasoning-latest",
    )
    return Agent(
        model=model,
        system_prompt="You are a helpful assistant. Be concise.",
        callback_handler=StreamingCallbackHandler(debug=debug),
    )


def create_tools_agent(api_key: str, debug: bool = False) -> Agent:
    """Create an agent with Strands tools (client-side function calling)."""
    model = xAIModel(
        client_args={"api_key": api_key},
        model_id="grok-4-1-fast-non-reasoning-latest",
    )
    return Agent(
        model=model,
        system_prompt="You are a helpful assistant with access to tools. Use them when appropriate.",
        tools=[calculate, get_weather],
        callback_handler=StreamingCallbackHandler(debug=debug),
    )


def create_x_search_agent(api_key: str, debug: bool = False) -> Agent:
    """Create an agent with X search server-side tool."""
    from xai_sdk.tools import x_search
    
    model = xAIModel(
        client_args={"api_key": api_key},
        model_id="grok-4-1-fast-non-reasoning-latest",
        xai_tools=[x_search()],
    )
    return Agent(
        model=model,
        system_prompt="You are a helpful assistant that can search X (Twitter) for information.",
        callback_handler=StreamingCallbackHandler(debug=debug),
    )


def create_hybrid_agent(api_key: str, debug: bool = False) -> Agent:
    """Create an agent with both X search (server-side) and Strands tools (client-side)."""
    from xai_sdk.tools import x_search
    
    model = xAIModel(
        client_args={"api_key": api_key},
        model_id="grok-4-1-fast-non-reasoning-latest",
        xai_tools=[x_search()],
    )
    return Agent(
        model=model,
        system_prompt="""You are a helpful assistant with multiple capabilities:
- You can search X (Twitter) for recent posts and trends
- You can calculate mathematical expressions
- You can get weather information for cities
Use the appropriate tool based on the user's request.""",
        tools=[calculate, get_weather],
        callback_handler=StreamingCallbackHandler(debug=debug),
    )


def create_reasoning_agent(api_key: str, debug: bool = False) -> Agent:
    """Create a reasoning agent (grok-3-mini with reasoning_effort)."""
    model = xAIModel(
        client_args={"api_key": api_key},
        model_id="grok-3-mini",
        reasoning_effort="high",
    )
    return Agent(
        model=model,
        system_prompt="You are a helpful assistant that thinks through problems carefully.",
        callback_handler=StreamingCallbackHandler(debug=debug),
    )


def create_reasoning_encrypted_agent(api_key: str, debug: bool = False) -> Agent:
    """Create a grok-4 reasoning agent with encrypted content for multi-turn context."""
    model = xAIModel(
        client_args={"api_key": api_key},
        model_id="grok-4-fast-reasoning",
        use_encrypted_content=True,
    )
    return Agent(
        model=model,
        system_prompt="You are a helpful assistant that thinks through problems carefully.",
        callback_handler=StreamingCallbackHandler(debug=debug),
    )


def create_reasoning_encrypted_debug_agent(api_key: str) -> Agent:
    """Create a grok-4 reasoning agent with DEBUG to see encrypted content detection."""
    import logging
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("strands.models.xai").setLevel(logging.DEBUG)
    
    model = xAIModel(
        client_args={"api_key": api_key},
        model_id="grok-4-fast-reasoning",
        use_encrypted_content=True,
    )
    return Agent(
        model=model,
        system_prompt="You are a helpful assistant that thinks through problems carefully.",
        callback_handler=StreamingCallbackHandler(debug=True),
    )


def create_web_search_citations_agent(api_key: str, debug: bool = False) -> Agent:
    """Create an agent with web search and inline citations enabled."""
    from xai_sdk.tools import web_search
    
    model = xAIModel(
        client_args={"api_key": api_key},
        model_id="grok-4-1-fast-non-reasoning-latest",
        xai_tools=[web_search()],
        include=["inline_citations"],  # Enable inline citations in responses
    )
    return Agent(
        model=model,
        system_prompt="You are a helpful assistant that searches the web for information. Always cite your sources.",
        callback_handler=StreamingCallbackHandler(debug=debug),
    )


# =============================================================================
# INTERACTIVE CHAT
# =============================================================================

def chat_loop(agent: Agent, agent_name: str, is_streaming: bool = True) -> None:
    """Run an interactive multi-turn chat loop."""
    print(f"\n{'=' * 60}")
    print(f"CHAT: {agent_name}")
    print(f"{'=' * 60}")
    print("Type your message and press Enter. Commands:")
    print("  /quit or /q  - Exit chat")
    print("  /clear or /c - Clear conversation history")
    print("  /help or /h  - Show this help")
    print("-" * 60)
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nGoodbye!")
            break
        
        if not user_input:
            continue
        
        # Handle commands
        if user_input.lower() in ["/quit", "/q"]:
            print("Goodbye!")
            break
        elif user_input.lower() in ["/clear", "/c"]:
            agent.messages.clear()
            print("[Conversation cleared]")
            continue
        elif user_input.lower() in ["/help", "/h"]:
            print("Commands: /quit, /clear, /help")
            continue
        
        # Send message to agent
        if is_streaming:
            print("\nAssistant: ", end="", flush=True)
        else:
            print("\nAssistant: ", end="")
        
        try:
            result = agent(user_input)
            if not is_streaming:
                print(result)
        except Exception as e:
            print(f"\n[Error]: {e}")


# =============================================================================
# MAIN
# =============================================================================

def print_menu() -> None:
    """Print the agent selection menu."""
    print("\n" + "=" * 60)
    print("STRANDS AGENTS - xAI INTERACTIVE CHAT")
    print("=" * 60)
    print("\nSelect an agent configuration:")
    print("  1. Simple (non-streaming)")
    print("  2. Streaming")
    print("  3. Streaming (DEBUG - shows all callback events)")
    print("  4. With Strands tools (calculate, weather)")
    print("  5. With X search (server-side)")
    print("  6. Hybrid (X search + Strands tools)")
    print("  7. Reasoning (grok-3-mini)")
    print("  8. Reasoning encrypted (grok-4-fast-reasoning)")
    print("  9. Reasoning encrypted DEBUG (grok-4 + logging)")
    print("  10. Web search with inline citations")
    print("  q. Quit")
    print()


def main() -> None:
    """Main entry point."""
    api_key = get_api_key()
    
    agents = {
        "1": ("Simple (non-streaming)", lambda: create_simple_agent(api_key), False),
        "2": ("Streaming", lambda: create_streaming_agent(api_key), True),
        "3": ("Streaming (DEBUG)", lambda: create_streaming_agent(api_key, debug=True), True),
        "4": ("Strands tools", lambda: create_tools_agent(api_key), True),
        "5": ("X search", lambda: create_x_search_agent(api_key), True),
        "6": ("Hybrid", lambda: create_hybrid_agent(api_key), True),
        "7": ("Reasoning (grok-3-mini)", lambda: create_reasoning_agent(api_key), True),
        "8": ("Reasoning encrypted (grok-4)", lambda: create_reasoning_encrypted_agent(api_key), True),
        "9": ("Reasoning encrypted DEBUG", lambda: create_reasoning_encrypted_debug_agent(api_key), True),
        "10": ("Web search + citations", lambda: create_web_search_citations_agent(api_key), True),
    }
    
    while True:
        print_menu()
        choice = input("Enter choice: ").strip().lower()
        
        if choice == "q":
            print("Goodbye!")
            break
        elif choice in agents:
            name, create_fn, is_streaming = agents[choice]
            try:
                agent = create_fn()
                chat_loop(agent, name, is_streaming)
            except Exception as e:
                print(f"\n[Error creating agent]: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    # Allow running a specific agent from command line
    if len(sys.argv) > 1:
        api_key = get_api_key()
        agent_num = sys.argv[1]
        debug = "--debug" in sys.argv
        
        agents = {
            "1": ("Simple", lambda: create_simple_agent(api_key), False),
            "2": ("Streaming", lambda: create_streaming_agent(api_key, debug), True),
            "3": ("Streaming (DEBUG)", lambda: create_streaming_agent(api_key, True), True),
            "4": ("Strands tools", lambda: create_tools_agent(api_key, debug), True),
            "5": ("X search", lambda: create_x_search_agent(api_key, debug), True),
            "6": ("Hybrid", lambda: create_hybrid_agent(api_key, debug), True),
            "7": ("Reasoning (grok-3-mini)", lambda: create_reasoning_agent(api_key, debug), True),
            "8": ("Reasoning encrypted (grok-4)", lambda: create_reasoning_encrypted_agent(api_key, debug), True),
            "9": ("Reasoning encrypted DEBUG", lambda: create_reasoning_encrypted_debug_agent(api_key), True),
            "10": ("Web search + citations", lambda: create_web_search_citations_agent(api_key, debug), True),
        }
        
        if agent_num in agents:
            name, create_fn, is_streaming = agents[agent_num]
            agent = create_fn()
            chat_loop(agent, name, is_streaming)
        else:
            print(f"Unknown agent: {agent_num}")
            print("Available: 1-10")
            sys.exit(1)
    else:
        main()
