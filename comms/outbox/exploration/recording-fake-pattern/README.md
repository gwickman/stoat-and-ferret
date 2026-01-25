# Recording Fake Pattern for FFmpeg Testing

**Recommended approach**: Use the Verified Fake pattern with a `Protocol`-based
`FFmpegExecutor` interface. A `RecordingExecutor` wraps the real implementation
to capture commands during contract tests, while a `FakeExecutor` replays
recorded responses in unit tests. Run contract tests nightly against real
FFmpeg to verify the fake stays synchronized.

## Overview

Testing code that shells out to FFmpeg presents challenges: real FFmpeg is slow,
requires media files, and produces non-deterministic output (timestamps, encoder
versions). The recording fake pattern solves this by:

1. **Defining an interface** - `FFmpegExecutor` protocol abstracts subprocess calls
2. **Recording interactions** - Capture real FFmpeg command/response pairs
3. **Replaying in tests** - Fast, deterministic tests using recorded data
4. **Verifying periodically** - Contract tests ensure fakes match real behavior

## Documents

- [executor-interface.md](./executor-interface.md) - Protocol design for FFmpegExecutor
- [recording-mechanism.md](./recording-mechanism.md) - How to capture and store commands
- [contract-tests.md](./contract-tests.md) - Pattern for periodic real FFmpeg verification
- [pytest-integration.md](./pytest-integration.md) - Fixtures and test organization

## Key Libraries

- **pytest-subprocess**: Fixture-based subprocess mocking with `fp.register()`
- **testfixtures.MockPopen**: Records subprocess interactions for verification
- **VCR.py pattern** (adapted): Record once, replay forever approach

## Architecture Decision

For stoat-and-ferret's hybrid Python/Rust architecture:

- Python orchestration layer uses `FFmpegExecutor` protocol
- Rust `stoat_ferret_core` generates filter strings (tested independently)
- Recording happens at the Python subprocess boundary
- Contract tests run against real FFmpeg in CI nightly job
