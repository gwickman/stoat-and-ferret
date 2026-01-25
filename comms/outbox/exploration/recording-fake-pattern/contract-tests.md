# Contract Tests

Pattern for periodic verification that fakes match real FFmpeg behavior.

## The Verified Fake Pattern

Contract tests run the same assertions against both the fake and real
implementations. When both pass, the fake is "verified" to behave like the real
thing.

```
                    ┌─────────────────┐
                    │ Contract Tests  │
                    │ (shared specs)  │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
              ▼                             ▼
    ┌─────────────────┐           ┌─────────────────┐
    │ FakeFFmpegExec  │           │ RealFFmpegExec  │
    │ (fast, in CI)   │           │ (nightly only)  │
    └─────────────────┘           └─────────────────┘
```

## Contract Test Structure

```python
from abc import ABC, abstractmethod
import pytest


class FFmpegExecutorContract(ABC):
    """Contract tests that both fake and real executors must pass."""

    @abstractmethod
    def get_executor(self) -> FFmpegExecutor:
        """Return the executor implementation to test."""
        ...

    @abstractmethod
    def get_test_video_path(self) -> str:
        """Return path to a test video file."""
        ...

    def test_probe_returns_valid_metadata(self):
        """Probing a video returns format and stream info."""
        executor = self.get_executor()
        result = executor.probe(self.get_test_video_path())

        assert "format" in result
        assert "streams" in result
        assert result["format"]["format_name"] is not None

    def test_transcode_succeeds_with_valid_input(self):
        """Basic transcode operation completes successfully."""
        executor = self.get_executor()
        result = executor.run([
            "-i", self.get_test_video_path(),
            "-t", "1",  # Only 1 second
            "-c:v", "libx264",
            "-f", "null",
            "-",
        ])

        assert result.returncode == 0

    def test_invalid_input_returns_error(self):
        """Non-existent input file returns error code."""
        executor = self.get_executor()
        result = executor.run([
            "-i", "/nonexistent/file.mp4",
            "-f", "null",
            "-",
        ])

        assert result.returncode != 0
        assert b"No such file" in result.stderr or b"does not exist" in result.stderr
```

## Running Against Real Implementation

```python
import pytest


@pytest.mark.contract
@pytest.mark.slow
class TestRealFFmpegContract(FFmpegExecutorContract):
    """Contract tests against real FFmpeg."""

    @pytest.fixture(autouse=True)
    def setup(self, test_video_file):
        self._test_video = test_video_file
        self._executor = RealFFmpegExecutor()

    def get_executor(self) -> FFmpegExecutor:
        return self._executor

    def get_test_video_path(self) -> str:
        return str(self._test_video)
```

## Running Against Fake Implementation

```python
@pytest.mark.contract
class TestFakeFFmpegContract(FFmpegExecutorContract):
    """Contract tests against fake FFmpeg."""

    @pytest.fixture(autouse=True)
    def setup(self, ffmpeg_cassette):
        self._executor = FakeFFmpegExecutor.from_file(ffmpeg_cassette)
        self._test_video = "INPUT"  # Token from recording

    def get_executor(self) -> FFmpegExecutor:
        return self._executor

    def get_test_video_path(self) -> str:
        return self._test_video
```

## CI Configuration

Run fake-based contract tests on every commit; real tests nightly:

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run unit tests
        run: pytest tests/ -m "not slow"

  contract-tests-fake:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run contract tests (fake)
        run: pytest tests/ -m "contract and not slow"
```

```yaml
# .github/workflows/nightly.yml
name: Nightly Contract Verification

on:
  schedule:
    - cron: "0 3 * * *"  # 3 AM daily

jobs:
  contract-tests-real:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install FFmpeg
        run: sudo apt-get install -y ffmpeg
      - name: Run contract tests (real)
        run: pytest tests/ -m "contract and slow"
      - name: Update cassettes if needed
        if: failure()
        run: pytest tests/ -m "contract" --record-mode=all
```

## Handling Contract Failures

When real FFmpeg behavior changes:

1. **Nightly job fails** - Contract test against real FFmpeg produces different result
2. **Investigate** - Is it an FFmpeg update, or did our expectations drift?
3. **Update recordings** - Re-record cassettes with new behavior
4. **Update tests** - If contract expectations need adjustment
5. **PR the fix** - Include updated cassettes and any test changes

```python
# conftest.py
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "contract: marks tests as contract tests"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (run nightly)"
    )
```

## Recording New Cassettes

When adding new functionality, record against real FFmpeg:

```bash
# Record new interactions
pytest tests/test_new_feature.py --record-mode=once

# Verify recordings work
pytest tests/test_new_feature.py --record-mode=none
```

## Version Compatibility

Track FFmpeg version in cassettes for debugging:

```python
def get_ffmpeg_version() -> str:
    """Get installed FFmpeg version string."""
    result = subprocess.run(
        ["ffmpeg", "-version"],
        capture_output=True,
        text=True,
    )
    # First line: "ffmpeg version N.N.N ..."
    return result.stdout.split("\n")[0].split()[2]
```

When cassette version differs significantly from installed FFmpeg, warn:

```python
def check_version_compatibility(cassette_version: str, installed_version: str) -> None:
    """Warn if FFmpeg versions differ significantly."""
    cassette_major = int(cassette_version.split(".")[0])
    installed_major = int(installed_version.split(".")[0])

    if cassette_major != installed_major:
        warnings.warn(
            f"Cassette recorded with FFmpeg {cassette_version}, "
            f"but {installed_version} is installed. "
            "Consider re-recording cassettes.",
            UserWarning,
        )
```
