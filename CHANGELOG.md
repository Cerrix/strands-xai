# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
