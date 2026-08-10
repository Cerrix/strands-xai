"""Unit tests for the xAI model provider."""

import base64
import json
import unittest.mock
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

import pytest
from xai_sdk.chat import chat_pb2 as xai_chat_pb2

import strands_xai.xai
from strands_xai import xAIModel
from strands_xai.xai import XAI_STATE_MARKER, XAI_STATE_MARKER_END


@contextmanager
def mock_xai_sdk() -> Generator[dict[str, unittest.mock.Mock], None, None]:
    """Context manager to mock the xAI SDK components."""
    with (
        unittest.mock.patch.object(strands_xai.xai, "AsyncClient") as mock_client_cls,
        unittest.mock.patch.object(strands_xai.xai, "xai_tool") as mock_xai_tool,
        unittest.mock.patch.object(strands_xai.xai, "xai_system") as mock_xai_system,
        unittest.mock.patch.object(strands_xai.xai, "xai_user") as mock_xai_user,
        unittest.mock.patch.object(strands_xai.xai, "xai_tool_result") as mock_xai_tool_result,
        unittest.mock.patch.object(
            strands_xai.xai, "get_tool_call_type", return_value="client_side_tool"
        ) as mock_get_tool_call_type,
    ):
        mock_client = mock_client_cls.return_value

        def create_tool_mock(name: str, description: str, parameters: dict) -> dict[str, Any]:
            return {
                "type": "function",
                "function": {"name": name, "description": description, "parameters": parameters},
            }

        mock_xai_tool.side_effect = create_tool_mock

        yield {
            "client": mock_client,
            "client_cls": mock_client_cls,
            "xai_tool": mock_xai_tool,
            "xai_system": mock_xai_system,
            "xai_user": mock_xai_user,
            "xai_tool_result": mock_xai_tool_result,
            "get_tool_call_type": mock_get_tool_call_type,
        }


@contextmanager
def mock_xai_client() -> Generator[unittest.mock.Mock, None, None]:
    """Context manager to mock the xAI AsyncClient."""
    with mock_xai_sdk() as mocks:
        yield mocks["client"]


@pytest.fixture
def mock_xai_client_fixture() -> Generator[unittest.mock.Mock, None, None]:
    """Pytest fixture to mock the xAI AsyncClient."""
    with mock_xai_client() as client:
        yield client


@pytest.fixture
def mock_xai_sdk_fixture() -> Generator[dict[str, unittest.mock.Mock], None, None]:
    """Pytest fixture to mock the full xAI SDK."""
    with mock_xai_sdk() as mocks:
        yield mocks


@pytest.fixture
def model_id() -> str:
    """Default model ID for tests."""
    return "grok-4.5"


@pytest.fixture
def model(mock_xai_sdk_fixture: dict[str, unittest.mock.Mock], model_id: str) -> xAIModel:
    """Create a xAIModel instance with mocked SDK."""
    _ = mock_xai_sdk_fixture
    return xAIModel(model_id=model_id)


class TestxAIConfigRoundTrip:
    """Tests for configuration round-trip consistency."""

    @pytest.mark.parametrize(
        "model_id",
        [
            "grok-3-mini-fast-latest",
            "grok-2-latest",
            "test-model-123",
            "model_with_underscores",
            "model-with-dashes",
        ],
    )
    def test_config_round_trip_model_id_only(self, model_id: str) -> None:
        """For any valid model_id, get_config returns equivalent config."""
        with mock_xai_client():
            model = xAIModel(model_id=model_id)
            config = model.get_config()
            assert config["model_id"] == f"xai/{model_id}"

    @pytest.mark.parametrize(
        "model_id,params",
        [
            ("grok-3-mini-fast-latest", {"temperature": 0.7}),
            ("grok-2-latest", {"max_tokens": 1000}),
            ("test-model", {"temperature": 1.5, "max_tokens": 2048}),
            ("model-123", {}),
        ],
    )
    def test_config_round_trip_with_params(self, model_id: str, params: dict) -> None:
        """For any valid model_id and params, config round-trip preserves values."""
        with mock_xai_client():
            model = xAIModel(model_id=model_id, params=params)
            config = model.get_config()
            assert config["model_id"] == f"xai/{model_id}"
            if params:
                assert config["params"] == params

    @pytest.mark.parametrize(
        "model_id,reasoning_effort",
        [
            ("grok-3-mini-fast-latest", "low"),
            ("grok-2-latest", "high"),
        ],
    )
    def test_config_round_trip_with_reasoning_effort(self, model_id: str, reasoning_effort: str) -> None:
        """For any valid model_id and reasoning_effort, config round-trip preserves values."""
        with mock_xai_client():
            model = xAIModel(model_id=model_id, reasoning_effort=reasoning_effort)
            config = model.get_config()
            assert config["model_id"] == f"xai/{model_id}"
            assert config["reasoning_effort"] == reasoning_effort

    @pytest.mark.parametrize(
        "model_id,include",
        [
            ("grok-3-mini-fast-latest", ["verbose_streaming"]),
            ("grok-2-latest", ["inline_citations"]),
            ("test-model", ["verbose_streaming", "inline_citations"]),
            ("model-123", []),
        ],
    )
    def test_config_round_trip_with_include(self, model_id: str, include: list) -> None:
        """For any valid model_id and include list, config round-trip preserves values."""
        with mock_xai_client():
            model = xAIModel(model_id=model_id, include=include)
            config = model.get_config()
            assert config["model_id"] == f"xai/{model_id}"
            if include:
                assert config["include"] == include

    @pytest.mark.parametrize(
        "model_id,agent_count",
        [
            ("grok-4.20-multi-agent", 4),
            ("grok-4.20-multi-agent", 16),
        ],
    )
    def test_config_round_trip_with_agent_count(self, model_id: str, agent_count: int) -> None:
        """For any valid model_id and agent_count, config round-trip preserves values."""
        with mock_xai_client():
            model = xAIModel(model_id=model_id, agent_count=agent_count)
            config = model.get_config()
            assert config["model_id"] == f"xai/{model_id}"
            assert config["agent_count"] == agent_count


class TestxAIModelInit:
    """Unit tests for xAIModel initialization."""

    def test_init_with_model_id(self, mock_xai_client_fixture: unittest.mock.Mock, model_id: str) -> None:
        """Test initialization with just model_id."""
        _ = mock_xai_client_fixture
        model = xAIModel(model_id=model_id)
        assert model.get_config()["model_id"] == f"xai/{model_id}"

    def test_init_with_params(self, mock_xai_client_fixture: unittest.mock.Mock, model_id: str) -> None:
        """Test initialization with params."""
        _ = mock_xai_client_fixture
        model = xAIModel(model_id=model_id, params={"temperature": 0.7})
        config = model.get_config()
        assert config["model_id"] == f"xai/{model_id}"
        assert config["params"] == {"temperature": 0.7}

    def test_init_with_client_args(self, mock_xai_client_fixture: unittest.mock.Mock, model_id: str) -> None:
        """Test initialization with client_args."""
        _ = mock_xai_client_fixture
        model = xAIModel(model_id=model_id, client_args={"api_key": "test-key"})
        assert model.client_args == {"api_key": "test-key"}

    def test_init_with_custom_client(self, model_id: str) -> None:
        """Test initialization with a custom client."""
        mock_client = unittest.mock.Mock()
        model = xAIModel(client=mock_client, model_id=model_id)
        assert model._custom_client is mock_client

    def test_init_with_both_client_and_client_args_raises_error(self, model_id: str) -> None:
        """Test that providing both client and client_args raises ValueError."""
        mock_client = unittest.mock.Mock()
        with pytest.raises(ValueError, match="Only one of 'client' or 'client_args' should be provided"):
            xAIModel(client=mock_client, client_args={"api_key": "test"}, model_id=model_id)


class TestModelIdQualification:
    """Tests for provider-qualified model_id (telemetry/pricing) vs bare id (SDK call)."""

    def test_model_id_is_qualified_for_telemetry(self) -> None:
        """A bare model_id is stored provider-qualified for OTel/cost backends."""
        with mock_xai_client():
            m = xAIModel(client_args={"api_key": "x"}, model_id="grok-4.3")
            assert m.get_config()["model_id"] == "xai/grok-4.3"

    def test_no_double_prefix(self) -> None:
        """An already-qualified model_id is left untouched (idempotent)."""
        with mock_xai_client():
            m = xAIModel(client_args={"api_key": "x"}, model_id="xai/grok-4.3")
            assert m.get_config()["model_id"] == "xai/grok-4.3"

    def test_update_config_requalifies(self) -> None:
        """update_config(model_id=...) re-qualifies the new id."""
        with mock_xai_client():
            m = xAIModel(client_args={"api_key": "x"}, model_id="grok-4.3")
            m.update_config(model_id="grok-4-fast")
            assert m.get_config()["model_id"] == "xai/grok-4-fast"

    def test_sdk_receives_bare_id(self, mock_xai_sdk_fixture: dict[str, unittest.mock.Mock]) -> None:
        """The xAI SDK is called with the bare id even though config holds the qualified one."""
        model = xAIModel(model_id="grok-4.3")
        mock_client = mock_xai_sdk_fixture["client"]
        mock_client.chat.create.return_value = unittest.mock.Mock()

        model._build_chat(mock_client)

        assert model.get_config()["model_id"] == "xai/grok-4.3"
        assert mock_client.chat.create.call_args[1]["model"] == "grok-4.3"

    def test_sdk_receives_bare_id_when_user_passes_qualified(
        self, mock_xai_sdk_fixture: dict[str, unittest.mock.Mock]
    ) -> None:
        """Passing an already-qualified id still results in a bare id at the SDK call site."""
        model = xAIModel(model_id="xai/grok-4.3")
        mock_client = mock_xai_sdk_fixture["client"]
        mock_client.chat.create.return_value = unittest.mock.Mock()

        model._build_chat(mock_client)

        assert mock_client.chat.create.call_args[1]["model"] == "grok-4.3"


class TestGrok45:
    """Tests for grok-4.5, xAI's current frontier model.

    grok-4.5 needs no allow-list entry in this provider (model ids are forwarded verbatim), so
    these tests pin the behavior that matters: the id survives qualification round-trips, the
    SDK receives the bare slug, its reasoning levels pass through, and its aliases work too.
    """

    def test_model_id_qualified_and_bare_at_sdk(self, mock_xai_sdk_fixture: dict[str, unittest.mock.Mock]) -> None:
        """grok-4.5 is stored qualified for cost backends but sent bare to the SDK."""
        model = xAIModel(model_id="grok-4.5")
        mock_client = mock_xai_sdk_fixture["client"]
        mock_client.chat.create.return_value = unittest.mock.Mock()

        model._build_chat(mock_client)

        assert model.get_config()["model_id"] == "xai/grok-4.5"
        assert mock_client.chat.create.call_args[1]["model"] == "grok-4.5"

    @pytest.mark.parametrize("alias", ["grok-4.5", "grok-4.5-latest", "grok-build-latest", "grok-latest"])
    def test_aliases_are_forwarded_verbatim(
        self, mock_xai_sdk_fixture: dict[str, unittest.mock.Mock], alias: str
    ) -> None:
        """Every grok-4.5 alias reaches the SDK unmodified (no provider-side allow-list)."""
        model = xAIModel(model_id=alias)
        mock_client = mock_xai_sdk_fixture["client"]
        mock_client.chat.create.return_value = unittest.mock.Mock()

        model._build_chat(mock_client)

        assert mock_client.chat.create.call_args[1]["model"] == alias

    @pytest.mark.parametrize("effort", ["low", "medium", "high"])
    def test_reasoning_levels_pass_through(
        self, mock_xai_sdk_fixture: dict[str, unittest.mock.Mock], effort: str
    ) -> None:
        """grok-4.5 accepts low/medium/high (it has no "none" level)."""
        model = xAIModel(model_id="grok-4.5", reasoning_effort=effort)
        mock_client = mock_xai_sdk_fixture["client"]
        mock_client.chat.create.return_value = unittest.mock.Mock()

        model._build_chat(mock_client)

        assert mock_client.chat.create.call_args[1]["reasoning_effort"] == effort

    def test_default_reasoning_effort_is_left_to_the_api(
        self, mock_xai_sdk_fixture: dict[str, unittest.mock.Mock]
    ) -> None:
        """Omitting reasoning_effort sends no key, so xAI applies its own default (high on grok-4.5)."""
        model = xAIModel(model_id="grok-4.5")
        mock_client = mock_xai_sdk_fixture["client"]
        mock_client.chat.create.return_value = unittest.mock.Mock()

        model._build_chat(mock_client)

        assert "reasoning_effort" not in mock_client.chat.create.call_args[1]

    def test_usage_mapping_against_real_sdk_proto(self, model: xAIModel) -> None:
        """Cache/reasoning mapping holds against a real xai-sdk usage proto, not just a stub.

        Guards against the SDK renaming or dropping cached_prompt_text_tokens on a future bump.
        """
        usage_pb2 = xai_chat_pb2.xai_dot_api_dot_v1_dot_usage__pb2
        usage = usage_pb2.SamplingUsage(
            prompt_tokens=4120,
            completion_tokens=380,
            reasoning_tokens=120,
            total_tokens=4620,
            prompt_text_tokens=4120,
            cached_prompt_text_tokens=3712,
        )

        u = model._format_chunk({"chunk_type": "metadata", "data": usage})["metadata"]["usage"]

        assert u["inputTokens"] == 4120
        assert u["outputTokens"] == 500
        assert u["totalTokens"] == 4620
        assert u["cacheReadInputTokens"] == 3712
        assert u["reasoningTokens"] == 120


class TestxAIModelGetClient:
    """Unit tests for xAIModel._get_client method."""

    def test_get_client_returns_custom_client(self, model_id: str) -> None:
        """Test that _get_client returns the injected client when provided."""
        mock_client = unittest.mock.Mock()
        model = xAIModel(client=mock_client, model_id=model_id)
        result = model._get_client()
        assert result is mock_client

    def test_get_client_creates_new_client(self, mock_xai_client_fixture: unittest.mock.Mock, model_id: str) -> None:
        """Test that _get_client creates a new client when no custom client is provided."""
        model = xAIModel(model_id=model_id, client_args={"api_key": "test-key"})
        model._get_client()
        strands_xai.xai.AsyncClient.assert_called_with(api_key="test-key")


class TestGrokToolsValidation:
    """Unit tests for xai_tools validation."""

    def test_validate_xai_tools_rejects_function_tools(
        self, mock_xai_client_fixture: unittest.mock.Mock, model_id: str
    ) -> None:
        """Test that function-based tools (dicts with type=function) are rejected in xai_tools."""
        _ = mock_xai_client_fixture
        # Client-side tools created via xai_tool() are dicts with "type": "function"
        mock_function_tool = {"type": "function", "function": {"name": "test_function"}}
        with pytest.raises(ValueError, match="xai_tools should not contain function-based tools"):
            xAIModel(model_id=model_id, xai_tools=[mock_function_tool])

    def test_validate_xai_tools_accepts_server_side_tools(
        self, mock_xai_client_fixture: unittest.mock.Mock, model_id: str
    ) -> None:
        """Test that server-side tools (protobuf objects) are accepted in xai_tools."""
        _ = mock_xai_client_fixture
        # Server-side tools like web_search() are protobuf objects, not dicts
        mock_server_tool = unittest.mock.Mock(spec=[])
        model = xAIModel(model_id=model_id, xai_tools=[mock_server_tool])
        assert "xai_tools" in model.get_config()

    def test_validate_xai_tools_on_update_config(
        self, mock_xai_client_fixture: unittest.mock.Mock, model_id: str
    ) -> None:
        """Test that xai_tools validation runs on update_config."""
        _ = mock_xai_client_fixture
        model = xAIModel(model_id=model_id)
        # Client-side tools created via xai_tool() are dicts with "type": "function"
        mock_function_tool = {"type": "function", "function": {"name": "test_function"}}
        with pytest.raises(ValueError, match="xai_tools should not contain function-based tools"):
            model.update_config(xai_tools=[mock_function_tool])


class TestFormatRequestTools:
    """Unit tests for _format_request_tools method."""

    def test_format_empty_tools(self, model: xAIModel) -> None:
        """Test formatting with no tools."""
        result = model._format_request_tools(None)
        assert result == []

    def test_format_single_tool(self, mock_xai_sdk_fixture: dict[str, unittest.mock.Mock], model_id: str) -> None:
        """Test formatting a single tool spec."""
        model = xAIModel(model_id=model_id)
        tool_specs = [
            {
                "name": "get_weather",
                "description": "Get weather for a location",
                "inputSchema": {"json": {"type": "object", "properties": {"location": {"type": "string"}}}},
            }
        ]
        result = model._format_request_tools(tool_specs)
        assert len(result) == 1
        mock_xai_sdk_fixture["xai_tool"].assert_called_once_with(
            name="get_weather",
            description="Get weather for a location",
            parameters={"type": "object", "properties": {"location": {"type": "string"}}},
        )

    def test_format_multiple_tools(self, mock_xai_sdk_fixture: dict[str, unittest.mock.Mock], model_id: str) -> None:
        """Test formatting multiple tool specs."""
        model = xAIModel(model_id=model_id)
        tool_specs = [
            {"name": "tool1", "description": "First tool", "inputSchema": {"json": {"type": "object"}}},
            {"name": "tool2", "description": "Second tool", "inputSchema": {"json": {"type": "object"}}},
        ]
        result = model._format_request_tools(tool_specs)
        assert len(result) == 2
        assert mock_xai_sdk_fixture["xai_tool"].call_count == 2

    def test_format_tools_with_xai_tools(
        self, mock_xai_sdk_fixture: dict[str, unittest.mock.Mock], model_id: str
    ) -> None:
        """Test that xai_tools are appended to formatted tools."""
        mock_server_tool = unittest.mock.Mock(spec=[])
        model = xAIModel(model_id=model_id, xai_tools=[mock_server_tool])
        tool_specs = [{"name": "tool1", "description": "Tool", "inputSchema": {"json": {"type": "object"}}}]
        result = model._format_request_tools(tool_specs)
        assert len(result) == 2
        assert mock_server_tool in result


class TestFormatChunk:
    """Unit tests for _format_chunk method."""

    def test_format_message_start(self, model: xAIModel) -> None:
        """Test formatting message_start chunk."""
        result = model._format_chunk({"chunk_type": "message_start"})
        assert result == {"messageStart": {"role": "assistant"}}

    def test_format_content_start_text(self, model: xAIModel) -> None:
        """Test formatting content_start chunk for text."""
        result = model._format_chunk({"chunk_type": "content_start", "data_type": "text"})
        assert result == {"contentBlockStart": {"start": {}}}

    def test_format_content_start_tool(self, model: xAIModel) -> None:
        """Test formatting content_start chunk for tool."""
        result = model._format_chunk(
            {
                "chunk_type": "content_start",
                "data_type": "tool",
                "data": {"name": "get_weather", "id": "tool-123"},
            }
        )
        assert result == {"contentBlockStart": {"start": {"toolUse": {"name": "get_weather", "toolUseId": "tool-123"}}}}

    def test_format_content_delta_text(self, model: xAIModel) -> None:
        """Test formatting content_delta chunk for text."""
        result = model._format_chunk({"chunk_type": "content_delta", "data_type": "text", "data": "Hello"})
        assert result == {"contentBlockDelta": {"delta": {"text": "Hello"}}}

    def test_format_content_delta_tool(self, model: xAIModel) -> None:
        """Test formatting content_delta chunk for tool."""
        result = model._format_chunk(
            {
                "chunk_type": "content_delta",
                "data_type": "tool",
                "data": {"arguments": '{"location": "Paris"}'},
            }
        )
        assert result == {"contentBlockDelta": {"delta": {"toolUse": {"input": '{"location": "Paris"}'}}}}

    def test_format_content_delta_reasoning(self, model: xAIModel) -> None:
        """Test formatting content_delta chunk for reasoning content."""
        result = model._format_chunk(
            {"chunk_type": "content_delta", "data_type": "reasoning_content", "data": "Thinking..."}
        )
        assert result == {"contentBlockDelta": {"delta": {"reasoningContent": {"text": "Thinking..."}}}}

    def test_format_content_stop(self, model: xAIModel) -> None:
        """Test formatting content_stop chunk."""
        result = model._format_chunk({"chunk_type": "content_stop"})
        assert result == {"contentBlockStop": {}}

    def test_format_message_stop_end_turn(self, model: xAIModel) -> None:
        """Test formatting message_stop chunk with end_turn."""
        result = model._format_chunk({"chunk_type": "message_stop", "data": "end_turn"})
        assert result == {"messageStop": {"stopReason": "end_turn"}}

    def test_format_message_stop_tool_use(self, model: xAIModel) -> None:
        """Test formatting message_stop chunk with tool_use."""
        result = model._format_chunk({"chunk_type": "message_stop", "data": "tool_use"})
        assert result == {"messageStop": {"stopReason": "tool_use"}}

    def test_format_message_stop_max_tokens(self, model: xAIModel) -> None:
        """Test formatting message_stop chunk with max_tokens."""
        result = model._format_chunk({"chunk_type": "message_stop", "data": "max_tokens"})
        assert result == {"messageStop": {"stopReason": "max_tokens"}}

    def test_format_metadata(self, model: xAIModel) -> None:
        """Test formatting metadata chunk."""
        mock_usage = unittest.mock.Mock()
        mock_usage.prompt_tokens = 100
        mock_usage.completion_tokens = 50
        mock_usage.total_tokens = 150
        mock_usage.reasoning_tokens = None
        result = model._format_chunk({"chunk_type": "metadata", "data": mock_usage})
        assert result["metadata"]["usage"]["inputTokens"] == 100
        assert result["metadata"]["usage"]["outputTokens"] == 50
        assert result["metadata"]["usage"]["totalTokens"] == 150

    def test_format_metadata_with_reasoning_tokens(self, model: xAIModel) -> None:
        """Test formatting metadata chunk with reasoning tokens."""
        mock_usage = unittest.mock.Mock()
        mock_usage.prompt_tokens = 100
        mock_usage.completion_tokens = 50
        mock_usage.total_tokens = 150
        mock_usage.reasoning_tokens = 25
        result = model._format_chunk({"chunk_type": "metadata", "data": mock_usage})
        assert result["metadata"]["usage"]["reasoningTokens"] == 25

    def test_format_metadata_folds_reasoning_into_output(self, model: xAIModel) -> None:
        """Reasoning tokens fold into outputTokens and total reconciles as input + output."""
        from types import SimpleNamespace

        usage = SimpleNamespace(prompt_tokens=337, completion_tokens=174, total_tokens=908, reasoning_tokens=397)
        u = model._format_chunk({"chunk_type": "metadata", "data": usage})["metadata"]["usage"]
        assert u["inputTokens"] == 337
        assert u["outputTokens"] == 174 + 397
        assert u["totalTokens"] == u["inputTokens"] + u["outputTokens"] == 908
        assert u["reasoningTokens"] == 397

    def test_format_metadata_no_reasoning_unchanged(self, model: xAIModel) -> None:
        """Non-reasoning responses: output == completion, total == input + output, no reasoningTokens key."""
        from types import SimpleNamespace

        usage = SimpleNamespace(prompt_tokens=100, completion_tokens=50, total_tokens=150, reasoning_tokens=0)
        u = model._format_chunk({"chunk_type": "metadata", "data": usage})["metadata"]["usage"]
        assert u["outputTokens"] == 50
        assert u["totalTokens"] == 150
        assert "reasoningTokens" not in u

    def test_format_metadata_reports_cached_prompt_tokens(self, model: xAIModel) -> None:
        """Cached prompt tokens surface as cacheReadInputTokens for cost attribution."""
        from types import SimpleNamespace

        usage = SimpleNamespace(
            prompt_tokens=4120,
            completion_tokens=380,
            total_tokens=4500,
            reasoning_tokens=0,
            cached_prompt_text_tokens=3712,
        )
        u = model._format_chunk({"chunk_type": "metadata", "data": usage})["metadata"]["usage"]
        assert u["cacheReadInputTokens"] == 3712

    def test_cached_tokens_are_a_subset_of_input_tokens(self, model: xAIModel) -> None:
        """cacheReadInputTokens is not subtracted from inputTokens, matching Strands' OpenAI provider."""
        from types import SimpleNamespace

        usage = SimpleNamespace(
            prompt_tokens=4120,
            completion_tokens=380,
            total_tokens=4500,
            reasoning_tokens=0,
            cached_prompt_text_tokens=3712,
        )
        u = model._format_chunk({"chunk_type": "metadata", "data": usage})["metadata"]["usage"]
        assert u["inputTokens"] == 4120
        assert u["cacheReadInputTokens"] < u["inputTokens"]
        assert u["totalTokens"] == u["inputTokens"] + u["outputTokens"]

    def test_no_cache_key_on_cache_miss(self, model: xAIModel) -> None:
        """A cache-cold request reports no cacheReadInputTokens key at all."""
        from types import SimpleNamespace

        usage = SimpleNamespace(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            reasoning_tokens=0,
            cached_prompt_text_tokens=0,
        )
        u = model._format_chunk({"chunk_type": "metadata", "data": usage})["metadata"]["usage"]
        assert "cacheReadInputTokens" not in u

    def test_missing_cached_field_is_tolerated(self, model: xAIModel) -> None:
        """Usage objects without the cached-token field (older xai-sdk) degrade gracefully."""
        from types import SimpleNamespace

        usage = SimpleNamespace(prompt_tokens=100, completion_tokens=50, total_tokens=150, reasoning_tokens=0)
        u = model._format_chunk({"chunk_type": "metadata", "data": usage})["metadata"]["usage"]
        assert "cacheReadInputTokens" not in u

    def test_cached_and_reasoning_tokens_coexist(self, model: xAIModel) -> None:
        """A cached reasoning request reports both cacheReadInputTokens and reasoningTokens."""
        from types import SimpleNamespace

        usage = SimpleNamespace(
            prompt_tokens=2000,
            completion_tokens=100,
            total_tokens=2500,
            reasoning_tokens=400,
            cached_prompt_text_tokens=1800,
        )
        u = model._format_chunk({"chunk_type": "metadata", "data": usage})["metadata"]["usage"]
        assert u["cacheReadInputTokens"] == 1800
        assert u["reasoningTokens"] == 400
        assert u["outputTokens"] == 500
        assert u["totalTokens"] == u["inputTokens"] + u["outputTokens"] == 2500

    def test_format_metadata_with_citations(self, model: xAIModel) -> None:
        """Test formatting metadata chunk with citations."""
        mock_usage = unittest.mock.Mock()
        mock_usage.prompt_tokens = 100
        mock_usage.completion_tokens = 50
        mock_usage.total_tokens = 150
        mock_usage.reasoning_tokens = None
        citations = [{"url": "https://example.com"}]
        result = model._format_chunk({"chunk_type": "metadata", "data": mock_usage, "citations": citations})
        assert result["metadata"]["citations"] == citations

    def test_format_unknown_chunk_raises_error(self, model: xAIModel) -> None:
        """Test that unknown chunk types raise RuntimeError."""
        with pytest.raises(RuntimeError, match="chunk_type=<unknown> | unknown type"):
            model._format_chunk({"chunk_type": "unknown"})


class TestHandleStreamError:
    """Unit tests for _handle_stream_error method."""

    def test_rate_limit_error(self, mock_xai_client_fixture: unittest.mock.Mock, model_id: str) -> None:
        """Test that rate limit errors raise ModelThrottledException."""
        from strands.types.exceptions import ModelThrottledException

        _ = mock_xai_client_fixture
        model = xAIModel(model_id=model_id)
        error = Exception("Rate limit exceeded")
        with pytest.raises(ModelThrottledException, match="Rate limit"):
            model._handle_stream_error(error)

    def test_rate_limit_error_429(self, mock_xai_client_fixture: unittest.mock.Mock, model_id: str) -> None:
        """Test that 429 errors raise ModelThrottledException."""
        from strands.types.exceptions import ModelThrottledException

        _ = mock_xai_client_fixture
        model = xAIModel(model_id=model_id)
        error = Exception("Error 429: Too many requests")
        with pytest.raises(ModelThrottledException, match="429"):
            model._handle_stream_error(error)

    def test_too_many_requests_error(self, mock_xai_client_fixture: unittest.mock.Mock, model_id: str) -> None:
        """Test that 'too many requests' errors raise ModelThrottledException."""
        from strands.types.exceptions import ModelThrottledException

        _ = mock_xai_client_fixture
        model = xAIModel(model_id=model_id)
        error = Exception("Too many requests, please slow down")
        with pytest.raises(ModelThrottledException, match="Too many requests"):
            model._handle_stream_error(error)

    def test_context_length_error(self, mock_xai_client_fixture: unittest.mock.Mock, model_id: str) -> None:
        """Test that context length errors raise ContextWindowOverflowException."""
        from strands.types.exceptions import ContextWindowOverflowException

        _ = mock_xai_client_fixture
        model = xAIModel(model_id=model_id)
        error = Exception("Context length exceeded")
        with pytest.raises(ContextWindowOverflowException, match="Context length"):
            model._handle_stream_error(error)

    def test_maximum_context_error(self, mock_xai_client_fixture: unittest.mock.Mock, model_id: str) -> None:
        """Test that maximum context errors raise ContextWindowOverflowException."""
        from strands.types.exceptions import ContextWindowOverflowException

        _ = mock_xai_client_fixture
        model = xAIModel(model_id=model_id)
        error = Exception("Maximum context length reached")
        with pytest.raises(ContextWindowOverflowException, match="Maximum context"):
            model._handle_stream_error(error)

    def test_token_limit_error(self, mock_xai_client_fixture: unittest.mock.Mock, model_id: str) -> None:
        """Test that token limit errors raise ContextWindowOverflowException."""
        from strands.types.exceptions import ContextWindowOverflowException

        _ = mock_xai_client_fixture
        model = xAIModel(model_id=model_id)
        error = Exception("Token limit exceeded")
        with pytest.raises(ContextWindowOverflowException, match="Token limit"):
            model._handle_stream_error(error)

    def test_other_error_reraises(self, mock_xai_client_fixture: unittest.mock.Mock, model_id: str) -> None:
        """Test that other errors are re-raised unchanged."""
        _ = mock_xai_client_fixture
        model = xAIModel(model_id=model_id)
        error = Exception("Some other error")
        with pytest.raises(Exception, match="Some other error"):
            model._handle_stream_error(error)


class TestBuildChat:
    """Unit tests for _build_chat method."""

    def test_build_chat_basic(self, mock_xai_sdk_fixture: dict[str, unittest.mock.Mock], model_id: str) -> None:
        """Test building a basic chat."""
        model = xAIModel(model_id=model_id)
        mock_client = mock_xai_sdk_fixture["client"]
        mock_chat = unittest.mock.Mock()
        mock_client.chat.create.return_value = mock_chat

        result = model._build_chat(mock_client)

        mock_client.chat.create.assert_called_once_with(model=model_id, store_messages=False)
        assert result is mock_chat

    def test_build_chat_with_tools(self, mock_xai_sdk_fixture: dict[str, unittest.mock.Mock], model_id: str) -> None:
        """Test building a chat with tools."""
        model = xAIModel(model_id=model_id)
        mock_client = mock_xai_sdk_fixture["client"]
        mock_chat = unittest.mock.Mock()
        mock_client.chat.create.return_value = mock_chat
        tool_specs = [{"name": "tool1", "description": "Tool", "inputSchema": {"json": {"type": "object"}}}]

        model._build_chat(mock_client, tool_specs)

        call_kwargs = mock_client.chat.create.call_args[1]
        assert "tools" in call_kwargs
        assert len(call_kwargs["tools"]) == 1

    def test_build_chat_with_reasoning_effort(
        self, mock_xai_sdk_fixture: dict[str, unittest.mock.Mock], model_id: str
    ) -> None:
        """Test building a chat with reasoning_effort."""
        model = xAIModel(model_id=model_id, reasoning_effort="high")
        mock_client = mock_xai_sdk_fixture["client"]
        mock_chat = unittest.mock.Mock()
        mock_client.chat.create.return_value = mock_chat

        model._build_chat(mock_client)

        call_kwargs = mock_client.chat.create.call_args[1]
        assert call_kwargs["reasoning_effort"] == "high"

    def test_build_chat_with_include(self, mock_xai_sdk_fixture: dict[str, unittest.mock.Mock], model_id: str) -> None:
        """Test building a chat with include options."""
        model = xAIModel(model_id=model_id, include=["verbose_streaming"])
        mock_client = mock_xai_sdk_fixture["client"]
        mock_chat = unittest.mock.Mock()
        mock_client.chat.create.return_value = mock_chat

        model._build_chat(mock_client)

        call_kwargs = mock_client.chat.create.call_args[1]
        assert call_kwargs["include"] == ["verbose_streaming"]

    def test_build_chat_with_params(self, mock_xai_sdk_fixture: dict[str, unittest.mock.Mock], model_id: str) -> None:
        """Test building a chat with additional params."""
        model = xAIModel(model_id=model_id, params={"temperature": 0.7, "max_tokens": 1000})
        mock_client = mock_xai_sdk_fixture["client"]
        mock_chat = unittest.mock.Mock()
        mock_client.chat.create.return_value = mock_chat

        model._build_chat(mock_client)

        call_kwargs = mock_client.chat.create.call_args[1]
        assert call_kwargs["temperature"] == 0.7
        assert call_kwargs["max_tokens"] == 1000

    def test_build_chat_with_agent_count(self, mock_xai_sdk_fixture: dict[str, unittest.mock.Mock]) -> None:
        """Test building a chat with agent_count for multi-agent models."""
        model = xAIModel(model_id="grok-4.20-multi-agent", agent_count=16)
        mock_client = mock_xai_sdk_fixture["client"]
        mock_chat = unittest.mock.Mock()
        mock_client.chat.create.return_value = mock_chat

        model._build_chat(mock_client)

        call_kwargs = mock_client.chat.create.call_args[1]
        assert call_kwargs["agent_count"] == 16

    def test_build_chat_without_agent_count(
        self, mock_xai_sdk_fixture: dict[str, unittest.mock.Mock], model_id: str
    ) -> None:
        """Test that agent_count is not passed when not configured."""
        model = xAIModel(model_id=model_id)
        mock_client = mock_xai_sdk_fixture["client"]
        mock_chat = unittest.mock.Mock()
        mock_client.chat.create.return_value = mock_chat

        model._build_chat(mock_client)

        call_kwargs = mock_client.chat.create.call_args[1]
        assert "agent_count" not in call_kwargs


class TestAppendMessagesToChat:
    """Unit tests for _append_messages_to_chat method."""

    def test_append_system_prompt(self, mock_xai_sdk_fixture: dict[str, unittest.mock.Mock], model_id: str) -> None:
        """Test appending system prompt."""
        model = xAIModel(model_id=model_id)
        mock_chat = unittest.mock.Mock()
        mock_xai_sdk_fixture["xai_system"].return_value = "system_msg"

        model._append_messages_to_chat(mock_chat, [], system_prompt="You are helpful")

        mock_xai_sdk_fixture["xai_system"].assert_called_once_with("You are helpful")
        mock_chat.append.assert_called_once_with("system_msg")

    def test_append_user_message_with_text(
        self, mock_xai_sdk_fixture: dict[str, unittest.mock.Mock], model_id: str
    ) -> None:
        """Test appending user message with text."""
        model = xAIModel(model_id=model_id)
        mock_chat = unittest.mock.Mock()
        mock_xai_sdk_fixture["xai_user"].return_value = "user_msg"
        messages = [{"role": "user", "content": [{"text": "Hello"}]}]

        model._append_messages_to_chat(mock_chat, messages)

        mock_xai_sdk_fixture["xai_user"].assert_called_once_with("Hello")
        mock_chat.append.assert_called_once_with("user_msg")

    def test_append_user_message_with_tool_result(
        self, mock_xai_sdk_fixture: dict[str, unittest.mock.Mock], model_id: str
    ) -> None:
        """Test appending user message with tool result."""
        model = xAIModel(model_id=model_id)
        mock_chat = unittest.mock.Mock()
        mock_xai_sdk_fixture["xai_tool_result"].return_value = "tool_result_msg"
        messages = [
            {"role": "user", "content": [{"toolResult": {"toolUseId": "123", "content": [{"text": "Result"}]}}]}
        ]

        model._append_messages_to_chat(mock_chat, messages)

        mock_xai_sdk_fixture["xai_tool_result"].assert_called_once_with("Result")
        mock_chat.append.assert_called_once_with("tool_result_msg")

    def test_append_user_message_with_json_tool_result(
        self, mock_xai_sdk_fixture: dict[str, unittest.mock.Mock], model_id: str
    ) -> None:
        """Test appending user message with JSON tool result."""
        model = xAIModel(model_id=model_id)
        mock_chat = unittest.mock.Mock()
        mock_xai_sdk_fixture["xai_tool_result"].return_value = "tool_result_msg"
        messages = [
            {"role": "user", "content": [{"toolResult": {"toolUseId": "123", "content": [{"json": {"key": "value"}}]}}]}
        ]

        model._append_messages_to_chat(mock_chat, messages)

        mock_xai_sdk_fixture["xai_tool_result"].assert_called_once_with('{"key": "value"}')

    def test_append_assistant_message_with_text(
        self, mock_xai_sdk_fixture: dict[str, unittest.mock.Mock], model_id: str
    ) -> None:
        """Test that assistant messages are reconstructed as protobuf messages."""
        model = xAIModel(model_id=model_id)
        mock_chat = unittest.mock.Mock()
        messages = [{"role": "assistant", "content": [{"text": "Hello"}]}]

        model._append_messages_to_chat(mock_chat, messages)

        # Assistant messages should be appended as protobuf Message objects
        mock_chat.append.assert_called_once()
        # Verify the appended message is a protobuf Message with correct content
        appended_msg = mock_chat.append.call_args[0][0]
        assert appended_msg.role == 2  # ROLE_ASSISTANT
        assert len(appended_msg.content) == 1
        assert appended_msg.content[0].text == "Hello"


class TestUpdateConfig:
    """Unit tests for update_config method."""

    def test_update_model_id(self, mock_xai_client_fixture: unittest.mock.Mock, model_id: str) -> None:
        """Test updating model_id."""
        _ = mock_xai_client_fixture
        model = xAIModel(model_id=model_id)
        model.update_config(model_id="grok-4-fast")
        assert model.get_config()["model_id"] == "xai/grok-4-fast"

    def test_update_params(self, mock_xai_client_fixture: unittest.mock.Mock, model_id: str) -> None:
        """Test updating params."""
        _ = mock_xai_client_fixture
        model = xAIModel(model_id=model_id)
        model.update_config(params={"temperature": 0.5})
        assert model.get_config()["params"] == {"temperature": 0.5}

    def test_update_reasoning_effort(self, mock_xai_client_fixture: unittest.mock.Mock, model_id: str) -> None:
        """Test updating reasoning_effort."""
        _ = mock_xai_client_fixture
        model = xAIModel(model_id=model_id)
        model.update_config(reasoning_effort="low")
        assert model.get_config()["reasoning_effort"] == "low"

    def test_update_include(self, mock_xai_client_fixture: unittest.mock.Mock, model_id: str) -> None:
        """Test updating include."""
        _ = mock_xai_client_fixture
        model = xAIModel(model_id=model_id)
        model.update_config(include=["inline_citations"])
        assert model.get_config()["include"] == ["inline_citations"]

    def test_update_agent_count(self, mock_xai_client_fixture: unittest.mock.Mock) -> None:
        """Test updating agent_count."""
        _ = mock_xai_client_fixture
        model = xAIModel(model_id="grok-4.20-multi-agent")
        model.update_config(agent_count=16)
        assert model.get_config()["agent_count"] == 16


class TestStream:
    """Unit tests for stream method."""

    @pytest.mark.asyncio
    async def test_stream_basic_response(
        self, mock_xai_sdk_fixture: dict[str, unittest.mock.Mock], model_id: str
    ) -> None:
        """Test streaming a basic response."""
        model = xAIModel(model_id=model_id)
        mock_client = mock_xai_sdk_fixture["client"]
        mock_chat = unittest.mock.Mock()
        mock_client.chat.create.return_value = mock_chat

        # Create mock response and chunk
        mock_response = unittest.mock.Mock()
        mock_response.usage = unittest.mock.Mock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15
        mock_response.usage.reasoning_tokens = None
        mock_response.citations = None
        mock_response.encrypted_content = None  # Explicitly set to avoid xAI state capture

        mock_chunk = unittest.mock.Mock()
        mock_chunk.content = "Hello"
        mock_chunk.reasoning_content = None
        mock_chunk.tool_calls = None

        async def mock_stream():
            yield mock_response, mock_chunk

        mock_chat.stream.return_value = mock_stream()

        events = []
        async for event in model.stream(messages=[], system_prompt="Test"):
            events.append(event)

        # Should have: message_start, content_start, content_delta, content_stop, message_stop, metadata
        assert len(events) >= 5
        assert events[0] == {"messageStart": {"role": "assistant"}}

    @pytest.mark.asyncio
    async def test_stream_with_tool_calls(
        self, mock_xai_sdk_fixture: dict[str, unittest.mock.Mock], model_id: str
    ) -> None:
        """Test streaming a response with client-side tool calls."""
        model = xAIModel(model_id=model_id)
        mock_client = mock_xai_sdk_fixture["client"]
        mock_chat = unittest.mock.Mock()
        mock_client.chat.create.return_value = mock_chat

        mock_response = unittest.mock.Mock()
        mock_response.usage = unittest.mock.Mock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15
        mock_response.usage.reasoning_tokens = None
        mock_response.citations = None
        mock_response.encrypted_content = None

        mock_tool_call = unittest.mock.Mock()
        mock_tool_call.id = "tool-123"
        mock_tool_call.function = unittest.mock.Mock()
        mock_tool_call.function.name = "get_weather"
        mock_tool_call.function.arguments = '{"location": "Paris"}'

        mock_chunk = unittest.mock.Mock()
        mock_chunk.content = None
        mock_chunk.reasoning_content = None
        mock_chunk.tool_calls = [mock_tool_call]

        async def mock_stream():
            yield mock_response, mock_chunk

        mock_chat.stream.return_value = mock_stream()

        events = []
        async for event in model.stream(messages=[]):
            events.append(event)

        # Should have tool_use stop reason (get_tool_call_type is mocked to return "client_side_tool")
        stop_events = [e for e in events if "messageStop" in e]
        assert len(stop_events) == 1
        assert stop_events[0]["messageStop"]["stopReason"] == "tool_use"

    @pytest.mark.asyncio
    async def test_stream_with_reasoning_content(
        self, mock_xai_sdk_fixture: dict[str, unittest.mock.Mock], model_id: str
    ) -> None:
        """Test streaming a response with reasoning content."""
        model = xAIModel(model_id=model_id)
        mock_client = mock_xai_sdk_fixture["client"]
        mock_chat = unittest.mock.Mock()
        mock_client.chat.create.return_value = mock_chat

        mock_response = unittest.mock.Mock()
        mock_response.usage = unittest.mock.Mock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15
        mock_response.usage.reasoning_tokens = 20
        mock_response.citations = None
        mock_response.encrypted_content = None  # Explicitly set to None to avoid Mock auto-attribute

        mock_chunk = unittest.mock.Mock()
        mock_chunk.content = None
        mock_chunk.reasoning_content = "Thinking..."
        mock_chunk.tool_calls = None

        async def mock_stream():
            yield mock_response, mock_chunk

        mock_chat.stream.return_value = mock_stream()

        events = []
        async for event in model.stream(messages=[]):
            events.append(event)

        # Should have reasoning content delta with text (not encrypted)
        reasoning_text_events = [
            e
            for e in events
            if "contentBlockDelta" in e
            and "reasoningContent" in e.get("contentBlockDelta", {}).get("delta", {})
            and "text" in e.get("contentBlockDelta", {}).get("delta", {}).get("reasoningContent", {})
        ]
        assert len(reasoning_text_events) == 1
        assert reasoning_text_events[0]["contentBlockDelta"]["delta"]["reasoningContent"]["text"] == "Thinking..."


class TestStructuredOutput:
    """Unit tests for structured_output method."""

    @pytest.mark.asyncio
    async def test_structured_output_basic(
        self, mock_xai_sdk_fixture: dict[str, unittest.mock.Mock], model_id: str
    ) -> None:
        """Test structured output with a Pydantic model."""
        import pydantic

        class Weather(pydantic.BaseModel):
            temperature: int
            condition: str

        model = xAIModel(model_id=model_id)
        mock_client = mock_xai_sdk_fixture["client"]
        mock_chat = unittest.mock.Mock()
        mock_client.chat.create.return_value = mock_chat

        parsed_output = Weather(temperature=25, condition="sunny")
        mock_response = unittest.mock.Mock()

        async def mock_parse(output_model):
            return mock_response, parsed_output

        mock_chat.parse = mock_parse

        messages = [{"role": "user", "content": [{"text": "What's the weather?"}]}]
        results = []
        async for result in model.structured_output(Weather, messages):
            results.append(result)

        assert len(results) == 1
        assert results[0]["output"] == parsed_output
        assert results[0]["output"].temperature == 25
        assert results[0]["output"].condition == "sunny"

    @pytest.mark.asyncio
    async def test_structured_output_with_system_prompt(
        self, mock_xai_sdk_fixture: dict[str, unittest.mock.Mock], model_id: str
    ) -> None:
        """Test structured output with system prompt."""
        import pydantic

        class Result(pydantic.BaseModel):
            value: str

        model = xAIModel(model_id=model_id)
        mock_client = mock_xai_sdk_fixture["client"]
        mock_chat = unittest.mock.Mock()
        mock_client.chat.create.return_value = mock_chat

        parsed_output = Result(value="test")
        mock_response = unittest.mock.Mock()

        async def mock_parse(output_model):
            return mock_response, parsed_output

        mock_chat.parse = mock_parse
        mock_xai_sdk_fixture["xai_system"].return_value = "system_msg"

        messages = [{"role": "user", "content": [{"text": "Test"}]}]
        results = []
        async for result in model.structured_output(Result, messages, system_prompt="Be helpful"):
            results.append(result)

        mock_xai_sdk_fixture["xai_system"].assert_called_once_with("Be helpful")


class TestServerSideToolCalls:
    """Unit tests for server-side tool call handling."""

    def test_format_metadata_with_server_tool_calls(self, model: xAIModel) -> None:
        """Test formatting metadata chunk with server tool calls."""
        mock_usage = unittest.mock.Mock()
        mock_usage.prompt_tokens = 100
        mock_usage.completion_tokens = 50
        mock_usage.total_tokens = 150
        mock_usage.reasoning_tokens = None

        server_tool_calls = [
            {"id": "tool-1", "name": "x_search", "arguments": '{"query": "test"}'},
            {"id": "tool-2", "name": "web_search", "arguments": '{"query": "hello"}'},
        ]

        result = model._format_chunk(
            {
                "chunk_type": "metadata",
                "data": mock_usage,
                "server_tool_calls": server_tool_calls,
            }
        )

        assert "serverToolCalls" in result["metadata"]
        assert len(result["metadata"]["serverToolCalls"]) == 2
        assert result["metadata"]["serverToolCalls"][0]["name"] == "x_search"
        assert result["metadata"]["serverToolCalls"][1]["name"] == "web_search"

    def test_format_metadata_without_server_tool_calls(self, model: xAIModel) -> None:
        """Test formatting metadata chunk without server tool calls."""
        mock_usage = unittest.mock.Mock()
        mock_usage.prompt_tokens = 100
        mock_usage.completion_tokens = 50
        mock_usage.total_tokens = 150
        mock_usage.reasoning_tokens = None

        result = model._format_chunk(
            {
                "chunk_type": "metadata",
                "data": mock_usage,
            }
        )

        assert "serverToolCalls" not in result["metadata"]

    @pytest.mark.asyncio
    async def test_stream_with_server_side_tool_calls(
        self, mock_xai_sdk_fixture: dict[str, unittest.mock.Mock], model_id: str
    ) -> None:
        """Test streaming a response with server-side tool calls (not executed by Strands)."""
        # Override get_tool_call_type to return server_side_tool for this test
        mock_xai_sdk_fixture["get_tool_call_type"].return_value = "server_side_tool"

        model = xAIModel(model_id=model_id)
        mock_client = mock_xai_sdk_fixture["client"]
        mock_chat = unittest.mock.Mock()
        mock_client.chat.create.return_value = mock_chat

        # Mock chat.messages for state capture
        mock_msg = unittest.mock.Mock()
        mock_msg.role = 1  # ROLE_USER
        mock_msg.SerializeToString.return_value = b"mock_serialized"
        mock_chat.messages = [mock_msg]

        mock_response = unittest.mock.Mock()
        mock_response.usage = unittest.mock.Mock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15
        mock_response.usage.reasoning_tokens = None
        mock_response.citations = None
        mock_response.encrypted_content = None

        # Server-side tool call (e.g., x_search)
        mock_tool_call = unittest.mock.Mock()
        mock_tool_call.id = "server-tool-123"
        mock_tool_call.function = unittest.mock.Mock()
        mock_tool_call.function.name = "x_search"
        mock_tool_call.function.arguments = '{"query": "test"}'

        mock_chunk = unittest.mock.Mock()
        mock_chunk.content = "Here are the search results..."
        mock_chunk.reasoning_content = None
        mock_chunk.tool_calls = [mock_tool_call]

        async def mock_stream():
            yield mock_response, mock_chunk

        mock_chat.stream.return_value = mock_stream()

        events = []
        async for event in model.stream(messages=[]):
            events.append(event)

        # Server-side tools should NOT trigger tool_use stop reason
        stop_events = [e for e in events if "messageStop" in e]
        assert len(stop_events) == 1
        assert stop_events[0]["messageStop"]["stopReason"] == "end_turn"

        # Server-side tools should be in metadata
        metadata_events = [e for e in events if "metadata" in e]
        assert len(metadata_events) == 1
        assert "serverToolCalls" in metadata_events[0]["metadata"]
        assert len(metadata_events[0]["metadata"]["serverToolCalls"]) == 1
        assert metadata_events[0]["metadata"]["serverToolCalls"][0]["name"] == "x_search"

    @pytest.mark.asyncio
    async def test_stream_with_mixed_tool_calls(
        self, mock_xai_sdk_fixture: dict[str, unittest.mock.Mock], model_id: str
    ) -> None:
        """Test streaming with both client-side and server-side tool calls."""
        model = xAIModel(model_id=model_id)
        mock_client = mock_xai_sdk_fixture["client"]
        mock_chat = unittest.mock.Mock()
        mock_client.chat.create.return_value = mock_chat

        # Mock chat.messages for state capture
        mock_msg = unittest.mock.Mock()
        mock_msg.role = 1  # ROLE_USER
        mock_msg.SerializeToString.return_value = b"mock_serialized"
        mock_chat.messages = [mock_msg]

        mock_response = unittest.mock.Mock()
        mock_response.usage = unittest.mock.Mock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15
        mock_response.usage.reasoning_tokens = None
        mock_response.citations = None
        mock_response.encrypted_content = None

        # Client-side tool call
        mock_client_tool = unittest.mock.Mock()
        mock_client_tool.id = "client-tool-123"
        mock_client_tool.function = unittest.mock.Mock()
        mock_client_tool.function.name = "get_weather"
        mock_client_tool.function.arguments = '{"city": "Paris"}'

        # Server-side tool call
        mock_server_tool = unittest.mock.Mock()
        mock_server_tool.id = "server-tool-456"
        mock_server_tool.function = unittest.mock.Mock()
        mock_server_tool.function.name = "x_search"
        mock_server_tool.function.arguments = '{"query": "weather"}'

        mock_chunk = unittest.mock.Mock()
        mock_chunk.content = None
        mock_chunk.reasoning_content = None
        mock_chunk.tool_calls = [mock_client_tool, mock_server_tool]

        # Mock get_tool_call_type to return different types based on tool
        def mock_get_type(tool_call):
            if tool_call.function.name == "get_weather":
                return "client_side_tool"
            return "server_side_tool"

        mock_xai_sdk_fixture["get_tool_call_type"].side_effect = mock_get_type

        async def mock_stream():
            yield mock_response, mock_chunk

        mock_chat.stream.return_value = mock_stream()

        events = []
        async for event in model.stream(messages=[]):
            events.append(event)

        # Should have tool_use stop reason (client-side tool present)
        stop_events = [e for e in events if "messageStop" in e]
        assert len(stop_events) == 1
        assert stop_events[0]["messageStop"]["stopReason"] == "tool_use"

        # Should have client-side tool in content blocks
        tool_start_events = [
            e
            for e in events
            if "contentBlockStart" in e and e.get("contentBlockStart", {}).get("start", {}).get("toolUse")
        ]
        assert len(tool_start_events) == 1
        assert tool_start_events[0]["contentBlockStart"]["start"]["toolUse"]["name"] == "get_weather"

        # Server-side tools should be in metadata
        metadata_events = [e for e in events if "metadata" in e]
        assert len(metadata_events) == 1
        assert "serverToolCalls" in metadata_events[0]["metadata"]
        assert len(metadata_events[0]["metadata"]["serverToolCalls"]) == 1
        assert metadata_events[0]["metadata"]["serverToolCalls"][0]["name"] == "x_search"

    def test_format_content_delta_server_tool(self, model: xAIModel) -> None:
        """Test formatting content_delta chunk for server-side tool (inline text)."""
        tool_data = {"id": "tool-123", "name": "x_search", "arguments": '{"query": "test"}'}
        result = model._format_chunk(
            {
                "chunk_type": "content_delta",
                "data_type": "server_tool",
                "data": tool_data,
            }
        )
        assert "contentBlockDelta" in result
        assert "text" in result["contentBlockDelta"]["delta"]
        assert "x_search" in result["contentBlockDelta"]["delta"]["text"]
        assert '{"query": "test"}' in result["contentBlockDelta"]["delta"]["text"]


def _encode_xai_state(messages: list[bytes]) -> bytes:
    """Encode serialized protobuf messages into an XAI_STATE redactedContent payload.

    Mirrors the production encoder in stream(): protobuf bytes -> base64 -> JSON -> base64 -> markers.
    """
    state_json = json.dumps({"messages": [base64.b64encode(m).decode("utf-8") for m in messages]})
    state_b64 = base64.b64encode(state_json.encode("utf-8")).decode("utf-8")
    return f"{XAI_STATE_MARKER}{state_b64}{XAI_STATE_MARKER_END}".encode("utf-8")


class TestEncryptedStateContinuity:
    """Regression tests for multi-turn encrypted-state preservation.

    These tests are fully deterministic: they never assert on model output. They assert the
    state-preservation *mechanism* using real protobuf serialization — the exact invariant that,
    if broken, drops server-side tool results / encrypted reasoning between turns (the F1
    "list the URLs you used" continuity bug).
    """

    def test_round_trip_restores_exact_protobuf_state(
        self, mock_xai_sdk_fixture: dict[str, unittest.mock.Mock], model_id: str
    ) -> None:
        """Preserved XAI_STATE must be replayed back to the SDK byte-for-byte, then the new user turn appended."""
        model = xAIModel(model_id=model_id)
        mock_chat = unittest.mock.Mock()
        mock_xai_sdk_fixture["xai_user"].return_value = "new_user_msg"

        # A previous-turn assistant message carrying encrypted state (e.g. server-side tool results).
        prior = xai_chat_pb2.Message()
        prior.role = xai_chat_pb2.ROLE_ASSISTANT
        prior.encrypted_content = "ENCRYPTED_TOOL_AND_REASONING_STATE"
        serialized_prior = prior.SerializeToString()

        messages = [
            {"role": "user", "content": [{"text": "What were the latest F1 results?"}]},
            {
                "role": "assistant",
                "content": [{"reasoningContent": {"redactedContent": _encode_xai_state([serialized_prior])}}],
            },
            {"role": "user", "content": [{"text": "List the URLs you used."}]},
        ]

        model._append_messages_to_chat(mock_chat, messages)

        appended = [c.args[0] for c in mock_chat.append.call_args_list]
        # First append must be the restored protobuf message with encrypted state intact.
        assert isinstance(appended[0], xai_chat_pb2.Message)
        assert appended[0].SerializeToString() == serialized_prior
        assert appended[0].encrypted_content == "ENCRYPTED_TOOL_AND_REASONING_STATE"
        # Last append must be the new user turn (so the follow-up question is actually asked).
        assert appended[-1] == "new_user_msg"

    @pytest.mark.asyncio
    async def test_stream_emits_xai_state_once_without_duplicate_raw_block(
        self, mock_xai_sdk_fixture: dict[str, unittest.mock.Mock], model_id: str
    ) -> None:
        """When encrypted reasoning is present, stream emits exactly one XAI_STATE block and no raw duplicate."""
        model = xAIModel(model_id=model_id)
        mock_client = mock_xai_sdk_fixture["client"]
        mock_chat = unittest.mock.Mock()
        mock_client.chat.create.return_value = mock_chat

        # chat.messages drives _capture_xai_state — a real protobuf message carrying encrypted state.
        captured = xai_chat_pb2.Message()
        captured.role = xai_chat_pb2.ROLE_ASSISTANT
        captured.encrypted_content = "ENCRYPTED_REASONING_STATE"
        mock_chat.messages = [captured]

        mock_response = unittest.mock.Mock()
        mock_response.usage = unittest.mock.Mock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15
        mock_response.usage.reasoning_tokens = 20
        mock_response.citations = None
        mock_response.encrypted_content = "ENCRYPTED_REASONING_STATE"

        mock_chunk = unittest.mock.Mock()
        mock_chunk.content = "Answer"
        mock_chunk.reasoning_content = None
        mock_chunk.tool_calls = None

        async def mock_stream():
            yield mock_response, mock_chunk

        mock_chat.stream.return_value = mock_stream()

        events = []
        async for event in model.stream(messages=[]):
            events.append(event)

        redacted = [
            e["contentBlockDelta"]["delta"]["reasoningContent"]["redactedContent"]
            for e in events
            if "contentBlockDelta" in e
            and "redactedContent" in e.get("contentBlockDelta", {}).get("delta", {}).get("reasoningContent", {})
        ]
        # Exactly one redactedContent block, and it is the XAI_STATE marker (no standalone raw encrypted block).
        assert len(redacted) == 1
        assert redacted[0].startswith(XAI_STATE_MARKER.encode("utf-8"))
        assert redacted[0] != b"ENCRYPTED_REASONING_STATE"

        # The encrypted state is NOT lost: it is carried inside the XAI_STATE protobuf capture.
        encoded = redacted[0].decode("utf-8")[len(XAI_STATE_MARKER) : -len(XAI_STATE_MARKER_END)]
        state = json.loads(base64.b64decode(encoded).decode("utf-8"))
        restored = xai_chat_pb2.Message()
        restored.ParseFromString(base64.b64decode(state["messages"][0]))
        assert restored.encrypted_content == "ENCRYPTED_REASONING_STATE"
