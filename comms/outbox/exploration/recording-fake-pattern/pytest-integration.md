# Pytest Integration

Fixtures, conftest.py patterns, and test organization for FFmpeg testing.

## Directory Structure

```
tests/
├── conftest.py                 # Shared fixtures
├── fixtures/
│   ├── media/                  # Small test media files
│   │   ├── sample_video.mp4    # 1-second test video
│   │   └── sample_audio.mp3    # 1-second test audio
│   └── cassettes/              # FFmpeg recordings
│       ├── transcode_basic.json
│       ├── probe_video.json
│       └── filter_chain.json
├── unit/                       # Fast tests with fakes
│   ├── test_video_processor.py
│   └── test_filter_builder.py
├── contract/                   # Contract tests
│   ├── test_executor_contract.py
│   └── test_probe_contract.py
└── integration/                # Real FFmpeg (slow)
    └── test_end_to_end.py
```

## Core Fixtures

```python
# tests/conftest.py
from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest


# Paths
FIXTURES_DIR = Path(__file__).parent / "fixtures"
CASSETTES_DIR = FIXTURES_DIR / "cassettes"
MEDIA_DIR = FIXTURES_DIR / "media"


@pytest.fixture
def cassettes_dir() -> Path:
    """Path to cassettes directory."""
    return CASSETTES_DIR


@pytest.fixture
def test_video_file() -> Path:
    """Path to sample video file for testing."""
    path = MEDIA_DIR / "sample_video.mp4"
    if not path.exists():
        pytest.skip("Test video file not found; run `make test-media` to create")
    return path


@pytest.fixture
def test_audio_file() -> Path:
    """Path to sample audio file for testing."""
    path = MEDIA_DIR / "sample_audio.mp3"
    if not path.exists():
        pytest.skip("Test audio file not found; run `make test-media` to create")
    return path
```

## Executor Fixtures

```python
# tests/conftest.py (continued)

@pytest.fixture
def real_executor() -> RealFFmpegExecutor:
    """Real FFmpeg executor for integration tests."""
    return RealFFmpegExecutor()


@pytest.fixture
def fake_executor(request, cassettes_dir: Path) -> FakeFFmpegExecutor:
    """Fake executor loaded from cassette matching test name.

    Cassette is determined by test function name:
    - test_transcode_mp4 -> cassettes/transcode_mp4.json
    """
    # Extract cassette name from test function
    test_name = request.node.name
    cassette_name = test_name.replace("test_", "")
    cassette_path = cassettes_dir / f"{cassette_name}.json"

    if not cassette_path.exists():
        pytest.skip(f"Cassette not found: {cassette_path}")

    return FakeFFmpegExecutor.from_file(cassette_path)


@pytest.fixture
def executor(request) -> FFmpegExecutor:
    """Executor fixture that switches based on markers.

    Use @pytest.mark.real_ffmpeg to use real executor.
    Default is fake executor.
    """
    if request.node.get_closest_marker("real_ffmpeg"):
        return RealFFmpegExecutor()
    else:
        return request.getfixturevalue("fake_executor")
```

## Recording Fixture

```python
@pytest.fixture
def recording_executor(
    real_executor: RealFFmpegExecutor,
    request,
    cassettes_dir: Path,
) -> Iterator[RecordingExecutor]:
    """Executor that records interactions for later replay.

    Use with --record-mode=once to create new cassettes.
    """
    test_name = request.node.name
    cassette_name = test_name.replace("test_", "")
    cassette_path = cassettes_dir / f"{cassette_name}.json"

    recorder = RecordingExecutor(real_executor, cassette_path)
    yield recorder
    recorder.save()
```

## Pytest Configuration

```python
# tests/conftest.py (continued)

def pytest_addoption(parser):
    parser.addoption(
        "--record-mode",
        action="store",
        default="none",
        choices=["none", "once", "new", "all"],
        help="Recording mode for FFmpeg interactions",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "real_ffmpeg: use real FFmpeg executor")
    config.addinivalue_line("markers", "contract: contract test")
    config.addinivalue_line("markers", "slow: slow test (nightly only)")


@pytest.fixture
def record_mode(request) -> str:
    """Current recording mode from CLI."""
    return request.config.getoption("--record-mode")
```

## Using pytest-subprocess

If using pytest-subprocess library for simpler cases:

```python
# tests/unit/test_with_fp.py
import pytest


def test_ffmpeg_called_correctly(fp):
    """Test using pytest-subprocess fixture."""
    # Register expected command
    fp.register(
        ["ffmpeg", "-i", fp.any(), "-c:v", "libx264", fp.any()],
        returncode=0,
        stderr=b"Encoding complete",
    )

    # Run code under test
    processor = VideoProcessor(executor=None)  # Uses subprocess directly
    processor.transcode_subprocess("input.mp4", "output.mp4")

    # Verify call was made
    assert fp.call_count(["ffmpeg", fp.any()]) == 1
```

## Test Examples

### Unit Test with Fake

```python
# tests/unit/test_video_processor.py
import pytest


class TestVideoProcessor:
    def test_transcode_calls_executor_with_correct_args(self, fake_executor):
        """Verify transcode passes correct arguments."""
        processor = VideoProcessor(executor=fake_executor)

        result = processor.transcode("input.mp4", "output.webm")

        assert result.returncode == 0

    def test_transcode_handles_error(self, fake_executor):
        """Error from FFmpeg is propagated correctly."""
        # Load error cassette
        fake = FakeFFmpegExecutor.from_file(CASSETTES_DIR / "transcode_error.json")
        processor = VideoProcessor(executor=fake)

        result = processor.transcode("corrupt.mp4", "output.webm")

        assert result.returncode != 0
```

### Contract Test

```python
# tests/contract/test_executor_contract.py
import pytest


@pytest.mark.contract
class TestProbeContract:
    """Contract: probe returns consistent structure."""

    @pytest.fixture(params=["fake", "real"])
    def executor(self, request, fake_executor, real_executor):
        if request.param == "fake":
            return fake_executor
        else:
            pytest.mark.slow
            return real_executor

    def test_probe_returns_streams(self, executor, test_video_file):
        result = executor.probe(str(test_video_file))

        assert "streams" in result
        assert len(result["streams"]) > 0
        assert result["streams"][0]["codec_type"] in ("video", "audio")
```

## Running Tests

```bash
# Fast unit tests (default)
pytest tests/unit/

# Contract tests with fake
pytest tests/contract/ -m "contract and not slow"

# Contract tests with real FFmpeg
pytest tests/contract/ -m "contract" --real-ffmpeg

# Record new cassettes
pytest tests/ --record-mode=once

# Full test suite (CI)
pytest tests/ -m "not slow"
```

## Makefile Integration

```makefile
# Makefile
.PHONY: test test-fast test-contract test-record

test:
	pytest tests/ -m "not slow"

test-fast:
	pytest tests/unit/

test-contract:
	pytest tests/contract/ -m "contract and not slow"

test-contract-real:
	pytest tests/contract/ -m "contract" --real-ffmpeg

test-record:
	pytest tests/ --record-mode=once

test-media:
	# Generate minimal test media files
	ffmpeg -f lavfi -i testsrc=duration=1:size=320x240 -c:v libx264 tests/fixtures/media/sample_video.mp4
	ffmpeg -f lavfi -i sine=duration=1 tests/fixtures/media/sample_audio.mp3
```
