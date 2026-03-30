# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
