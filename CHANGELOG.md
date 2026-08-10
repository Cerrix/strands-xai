# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2026-08-07

### Added
- **`grok-4.5` support** — xAI's frontier model for coding, agentic tasks, and knowledge work
  (500K context, vision, function calling, structured outputs, $2.00/$6.00 per MTok under a 200K
  prompt). No provider change was required to *call* it — model IDs are forwarded verbatim — so
  this release is about making it the documented default and pinning its behavior in tests.
  Note that `xai_sdk`'s `ChatModel` type alias still does not list `grok-4.5` (as of 1.17.0), but
  its `model` parameter is typed `ChatModel | str`, so the slug is valid at runtime and under mypy.

- **Cached input tokens are now reported as `cacheReadInputTokens`** (cost attribution). xAI's
  `SamplingUsage` carries `cached_prompt_text_tokens` — the subset of the prompt served from the
  prompt cache and billed at the discounted cached-input rate ($0.30 vs $2.00 per MTok on
  grok-4.5, a ~85% saving). The provider previously dropped this field, so cache hits were
  invisible and cost backends charged every cached token at the full input rate. It is now mapped
  onto Strands' optional `Usage.cacheReadInputTokens` (emitted only when non-zero), which also
  surfaces on the OTel span as `gen_ai.usage.cache_read_input_tokens`.

  Following the convention of Strands' own OpenAI and LiteLLM providers, the cached count is a
  **subset** of `inputTokens` rather than a separate addend, so `totalTokens == inputTokens +
  outputTokens` still holds.

- README sections for **long-context pricing** (the ≥200K-prompt tier that re-bills *all* tokens
  in a request at the higher rate) and **prompt caching** (what invalidates the cache, and why
  there is no `prompt_cache_key` option — the gRPC `xai_sdk` does not expose that Responses-API
  parameter; `conversation_id` can be passed through `params` for trace grouping).

- Unit tests for grok-4.5 (qualified/bare id round-trip, the `grok-4.5-latest`, `grok-build-latest`
  and `grok-latest` aliases, and each reasoning level) plus cache-token accounting. The usage
  mapping is additionally asserted against a **real** `xai_sdk` `SamplingUsage` protobuf, so a
  future SDK rename of `cached_prompt_text_tokens` fails the suite instead of silently zeroing the
  discount.

### Changed
- **Dependency floors raised** to `strands-agents>=1.50.2` and `xai-sdk>=1.17.0,<2.0.0` (both
  latest). The SDK surface this provider relies on (`chat.create` kwargs, streaming
  `(response, chunk)` pairs, `chat_pb2` message/role types, `get_tool_call_type`) is unchanged on
  1.17.0.
- **`reasoning_effort` is no longer documented as grok-4.3-only.** `grok-4.5` accepts `low`,
  `medium`, and `high` and defaults to `high`; it has **no `none` level** (unlike grok-4.3, which
  accepts `none` and defaults to `low`). Passing the parameter to `grok-build-0.1` or the
  `grok-4.20-0309-*` snapshots still returns `INVALID_ARGUMENT`.
- README now presents `grok-4.5` as the default choice, matching xAI's own guidance to use it for
  everything text-based including code, while noting the trade-off: it costs ~1.6× the input and
  ~2.4× the output of grok-4.3 and has a smaller context window (500K vs 1M), so grok-4.3 remains
  the pick for long-context or cost-sensitive workloads and for `reasoning_effort="none"`.
- `grok-build-latest` is documented as an alias of `grok-4.5`, which is why `grok-build-0.1` is
  effectively superseded.
- **Examples migrated off retired model aliases.** `interactive_chat.py`, `test_grok_final.py`,
  and `test_vision.py` still used slugs retired on 2026-05-15 (`grok-4-1-fast-non-reasoning-latest`,
  `grok-4-fast-reasoning`, `grok-4-1-fast-reasoning`, `grok-3-mini`) and now use `grok-4.5`;
  `test_grok420.py` and `test_collections_search.py` moved from the non-existent
  `grok-4.20-reasoning` / `grok-4.20-non-reasoning` slugs to the pinned `grok-4.20-0309-*`
  snapshots.

### Fixed
- Two duplicate local annotations in `_append_messages_to_chat` (`tool_results`, `result_parts`)
  that `mypy` 2.3 reports as `no-redef` errors. The defect pre-dated this release and was only
  surfaced by the type-checker bump; `mypy src/strands_xai` is clean again.
- `tests/test_hooks_integration.py` (a local, gitignored integration suite) built its fixture
  model from the retired `grok-3-mini` slug; it now uses `grok-4.5`.

### Verified
Live integration tests against the xAI API (xai-sdk 1.17.0, strands-agents 1.50.2) on `grok-4.5`:
- `reasoning_effort` ∈ {`low`, `medium`, `high`} all accepted. `reasoning_effort="none"` is
  rejected with `INVALID_ARGUMENT` ("This model does not support `reasoning_effort`"), confirming
  grok-4.5 has no `none` level.
- Summarized reasoning surfaces as a `reasoningContent` block alongside the `text` block.
- **Prompt caching confirmed end-to-end.** With a byte-identical ~6.3K-token system prompt, the
  first call reported `cacheReadInputTokens=640` of 6350 input tokens and each subsequent call
  reported 6272 of 6350 (~99% served from cache). The subset invariant
  (`cacheReadInputTokens <= inputTokens`) and `totalTokens == inputTokens + outputTokens` held on
  every call.
- `structured_output` (`chat.parse`) returns a correctly populated pydantic model.
- A live call succeeds while `get_config()["model_id"]` holds the qualified `xai/grok-4.5`,
  re-confirming that the prefix is stripped at the SDK call site.
- All 8 previously-skipped hook integration tests pass (invocation/model/tool hook ordering, tool
  cancellation, tool-input modification, tool-result redaction, and `AfterModelCallEvent` retry).

  Note: `reasoningTokens` is emitted on the stream's metadata event but does not appear in
  `result.metrics.accumulated_usage`, because Strands' accumulator only copies the keys it knows.
  This is unchanged behavior and is why the count is documented as a metadata-event field.

## [0.4.0] - 2026-06-12

### Changed
- **`model_id` is now stored provider-qualified as `xai/<model>`** for telemetry and cost
  attribution. Strands stamps the OpenTelemetry span's `gen_ai.request.model` directly from
  `config["model_id"]`, and cost backends (LiteLLM, SideSeat, etc.) price Grok under the
  qualified key `xai/<model>` — there is no bare `grok-*` price key — so reporting the bare id
  produced a `$0` cost. The provider now qualifies the id (idempotent: passing either
  `"grok-4.3"` or `"xai/grok-4.3"` yields `"xai/grok-4.3"`) and strips the `xai/` prefix only at
  the xAI SDK call site, so **inference is unchanged** (the SDK still receives the bare id and
  rejects the prefix).

  **Behavior change to note:** `model.get_config()["model_id"]` now returns the qualified
  `"xai/<model>"` instead of the bare string. Callers that do an exact-equality check on the old
  bare value should account for the prefix.

### Added
- README **Cost tracking and the qualified model id** subsection explaining the qualified id and
  reiterating `XAI_SDK_DISABLE_TRACING=1` for reconciling token totals. With both in place, a
  Grok reasoning run's exported trace reconciles (`inputTokens + outputTokens == totalTokens`)
  and carries a non-zero cost.

## [0.3.4] - 2026-06-04

### Added
- README **Observability / OpenTelemetry** section documenting `XAI_SDK_DISABLE_TRACING=1`.
  `xai_sdk` ships its own OpenTelemetry auto-instrumentation that emits a duplicate
  `chat.stream` CLIENT span (`gen_ai.system="xai"`) per call, whose raw usage is internally
  inconsistent (`output_tokens` excludes reasoning while `total_tokens` includes it), which can
  skew trace-level totals in observability backends. Setting the env var before process start
  suppresses that span so only Strands' (correct) spans are exported. Docs only — the package
  does **not** set the variable itself (it would be a surprising global side effect, and
  `xai_sdk` binds its tracer at import time so a programmatic set after import has no effect).

## [0.3.3] - 2026-06-04

### Changed
- Raised the `xai-sdk` dependency floor to `>=1.15.0,<2.0.0` (latest). Verified the full
  test suite passes against xai-sdk 1.15.0 and that the SDK API surface this provider relies
  on (`chat.create`, streaming `(response, chunk)`, reasoning/usage fields, `chat_pb2`
  message types, `get_tool_call_type`) is unchanged.

## [0.3.2] - 2026-06-04

### Fixed
- **Token-usage accounting for reasoning models** (observability / cost). The `metadata`
  branch of `_format_chunk` copied xai_sdk's counters verbatim, but `completion_tokens`
  **excludes** reasoning while `total_tokens` **includes** it — so the reported usage violated
  Strands' invariant that `totalTokens == inputTokens + outputTokens` (e.g. grok-4.3:
  337 input + 174 output but 908 total, leaving 397 reasoning tokens unaccounted). Downstream
  OTel consumers showed `reasoning_tokens = 0` and undercounted cost.

  Reasoning tokens are now folded into `outputTokens`, and `totalTokens` is computed as
  `prompt + completion + reasoning` (no longer trusting xai_sdk's `total_tokens`). This makes
  the triple self-consistent and bills reasoning as output — the same convention the native
  Amazon Bedrock OpenAI Responses and Anthropic Converse providers already use. The
  non-standard `reasoningTokens` key is still emitted when present (Strands ignores it;
  aware consumers can read it).

## [0.3.1] - 2026-06-04

### Changed
- **Reduced multi-turn payload size.** `stream()` no longer emits a standalone
  `reasoningContent.redactedContent` block for `final_response.encrypted_content`. That
  encrypted state is already preserved inside the `XAI_STATE` protobuf capture (the captured
  response Message carries its own `encrypted_content`), so the separate block only duplicated
  the encrypted payload in message history (~1.5–2.2 KB per turn observed) without adding any
  restorable context. Server-side tool and encrypted-reasoning continuity across turns is
  unchanged — `_extract_xai_state` only ever restored from the `XAI_STATE` marker.

### Added
- Deterministic regression tests for multi-turn encrypted-state continuity
  (`TestEncryptedStateContinuity`). These assert the state-preservation mechanism via real
  protobuf serialization (never model output): the round-trip replays preserved state
  byte-for-byte and then appends the new user turn, and `stream()` emits exactly one
  `XAI_STATE` block with no duplicate raw encrypted block.

### Fixed
- README: corrected the summarized-reasoning description (the summary is typically a few
  hundred characters and always shorter than the billed `reasoning_tokens`, not "~100 chars"),
  and removed a stale hard-coded unit-test count.

### Verified
- Live F1 multi-turn continuity ("what were the latest race results?" → "list the URLs you
  used") confirmed intact on `grok-4.3` + `web_search`: turn two returns turn one's source
  URLs from the encrypted tool state with no re-search, and message history now contains zero
  duplicate raw encrypted blocks.
- `reasoning_effort` ∈ {`none`, `low`, `high`} verified flowing through `xAIModel`: `none`
  yields no reasoning text/tokens; `low`/`high` surface a summary plus `reasoningTokens`.

## [0.3.0] - 2026-05-26

### Added
- Documentation for the latest Grok models verified against the official xAI docs:
  - `grok-4.3` — flagship with configurable reasoning (1M context, $1.25/$2.50 per MTok)
  - `grok-build-0.1` — agentic coding model, early access (256K context, vision-capable, $1/$2 per MTok)
  - `grok-4.20-multi-agent-0309` — pinned multi-agent snapshot
  - `grok-4.20-0309-reasoning` / `grok-4.20-0309-non-reasoning` — pinned 4.20 snapshots
- New "Retired model aliases" section in the README covering the 2026-05-15 retirements
  (`grok-4-1-fast-*`, `grok-4-fast-*`, `grok-4-0709`, `grok-3*`, `grok-3-mini*`, `grok-code-fast-1`)
  and the targets they now redirect to.
- New "Model aliases" subsection documenting xAI's `<name>` / `<name>-latest` / `<name>-<date>`
  convention so users can pick rolling vs. pinned model IDs intentionally.

### Changed
- **Dependency floors raised** to `strands-agents>=1.41.0` and `xai-sdk>=1.12.0`. The xai-sdk floor
  is required to use `reasoning_effort="none"` and `"medium"` on `grok-4.3` — earlier xai-sdk
  releases ship a client-side validator that only accepts `"low"` and `"high"`.
- README examples migrated from retired aliases (`grok-4-1-fast-non-reasoning-latest`,
  `grok-4-fast-reasoning`, `grok-3-mini`) to `grok-4.3`.
- "With Reasoning" section now documents `grok-4.3` with all four `reasoning_effort` levels
  (`none`, `low`, `medium`, `high`) and notes the incompatibility of `presence_penalty`,
  `frequency_penalty`, and `stop` with reasoning models.
- "With Encrypted Reasoning" section retitled and rewritten to show `grok-4.3` instead of `grok-4-fast-reasoning`.
- "Multi-Agent Research" section now flags the API's **beta** status, documents that only the leader agent's output is returned (sub-agent state preserved via the auto-enabled `use_encrypted_content`), and notes that leader + sub-agent tokens and tool calls are all billed.
- Clarified that `reasoning_effort` is **only** accepted by `grok-4.3`. The xAI API returns
  `INVALID_ARGUMENT` if it's passed to `grok-build-0.1`, `grok-4.20-0309-reasoning`,
  or `grok-4.20-0309-non-reasoning` (those snapshots have their reasoning behavior baked in).

### Verified
Live integration tests against the xAI API (xai-sdk 1.12.2):
- `grok-4.3` with `reasoning_effort` ∈ {`none`, `low`, `medium`, `high`} — all pass.
- `grok-build-0.1` basic chat — passes.
- `grok-4.20-0309-non-reasoning` basic chat — passes.
- `grok-4.20-multi-agent-0309` with `agent_count` ∈ {4, 16} — both pass.
- `grok-4.3` multi-turn with `use_encrypted_content=True` — context preserved across turns.
- **Reasoning-content visibility** confirmed for every reasoning-capable model:
  `grok-4.3` (low and high effort), `grok-build-0.1`, and `grok-4.20-0309-reasoning`
  all stream `reasoning_content` summaries and `usage.reasoning_tokens` counts that
  are surfaced through `xAIModel.stream()` as Strands `reasoningContent.reasoningText`
  blocks. `grok-4.20-0309-non-reasoning` correctly emits zero reasoning tokens. With
  `use_encrypted_content=True`, encrypted reasoning state (~2.5KB per turn observed)
  is preserved as `reasoningContent.redactedContent`.
- Configuration Options table updated: `reasoning_effort` is now described as a `grok-4.3` parameter,
  and `params` flags the reasoning-model parameter restrictions.
- `xAIConfig` docstring and module-level usage example refreshed to use current model IDs.
- Internal code comments referring to "grok-4" / "grok-3-mini" updated to "grok-4.3".

## [0.2.0] - 2026-03-30

### Added
- Support for new Grok 4.20 models (grok-4.20-reasoning, grok-4.20-non-reasoning)
- Multi-agent research support with grok-4.20-multi-agent model
- New `agent_count` configuration option (4 or 16 agents) for multi-agent models
- Documentation for `collections_search()` server-side tool

### Changed
- Updated available models table with latest xAI model lineup and pricing

## [0.1.3] - 2026-02-03

### Fixed
- Fixed bug where local Strands tool results were ignored when `xai_tools` was enabled
- Tool results are now correctly appended to the xAI chat when restoring xAI state

## [0.1.1] - 2026-01-26

### Fixed
- Corrected streaming example in README to use `PrintingCallbackHandler` instead of non-existent `agent.stream()` method

## [0.1.0] - 2026-01-23

### Added
- Initial release of strands-xai
- Full support for xAI Grok models
- Server-side tools integration (web_search, x_search, code_execution)
- Reasoning model support (grok-3-mini with visible reasoning)
- Encrypted reasoning support (grok-4 multi-turn context)
- Streaming response support
- Hybrid tool usage (server-side + client-side tools)
- Comprehensive unit and integration tests
- Type hints and mypy support
