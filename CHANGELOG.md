# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
