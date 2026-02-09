## Context

Testing against external dependencies (FFmpeg, APIs, databases) is slow and environment-dependent. Fake implementations risk diverging from real behavior.

## Learning

Use a three-tier executor pattern: Real (calls actual dependency), Recording (wraps Real and captures interactions), and Fake (replays recorded interactions). Add a `strict` mode to the Fake that verifies input arguments match the recording before replaying, catching cases where code changes cause different inputs to be sent to the dependency.

## Evidence

- v004 Theme 02 Feature 002 (ffmpeg-contract-tests): 21 parametrized tests across Real, Recording, and Fake FFmpeg executors.
- `strict=True` on FakeFFmpegExecutor verified args match recordings before replaying.
- Only 23 lines added to executor.py for strict mode — minimal code for significant verification.
- `@pytest.mark.requires_ffmpeg` separated environment-dependent tests from universal tests.

## Application

- For any external dependency wrapper, implement the Real/Recording/Fake trio.
- Add strict mode to fakes for argument verification during testing.
- Use pytest markers to separate tests requiring real dependencies from those using fakes.
- This pattern scales to any external dependency (APIs, databases, file systems).