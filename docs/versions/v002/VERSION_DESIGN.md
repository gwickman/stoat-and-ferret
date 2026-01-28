# v002 Version Design

## Overview

**Version:** v002
**Title:** Database & FFmpeg Integration with Python Bindings Completion. Addresses roadmap M1.4-1.5. Fixes stub drift, completes Python bindings for v001 Rust types, establishes database foundation with repository pattern, and integrates FFmpeg executor with Rust command builder.
**Themes:** 4

## Themes

| # | Theme | Goal | Features |
|---|-------|------|----------|
| 1 | 01-rust-python-bindings | Fix stub drift and complete Python bindings for all v001 Rust types. Must execute first as subsequent themes may use these types. | 4 |
| 2 | 02-tooling-process | Document PyO3 binding patterns in AGENTS.md to prevent future tech debt from deferred bindings. | 1 |
| 3 | 03-database-foundation | Establish SQLite database layer with repository pattern for video metadata storage. | 4 |
| 4 | 04-ffmpeg-integration | Create observable, testable FFmpeg integration connecting Rust command builder to Python execution. | 4 |

## Success Criteria

Version is complete when:

- [ ] Theme 01 (rust-python-bindings): Fix stub drift and complete Python bindings for all v001 Rust types. Must execute first as subsequent themes may use these types.
- [ ] Theme 02 (tooling-process): Document PyO3 binding patterns in AGENTS.md to prevent future tech debt from deferred bindings.
- [ ] Theme 03 (database-foundation): Establish SQLite database layer with repository pattern for video metadata storage.
- [ ] Theme 04 (ffmpeg-integration): Create observable, testable FFmpeg integration connecting Rust command builder to Python execution.
