# Recording Mechanism

How to capture FFmpeg commands, store them, and replay for verification.

## Recording Strategy

### What to Record

For each FFmpeg invocation, capture:

1. **Command arguments** - The full argument list passed to FFmpeg
2. **stdin content** - Any piped input data (for filter scripts, raw frames)
3. **stdout content** - Output data (for pipe output mode)
4. **stderr content** - FFmpeg's progress/error messages
5. **Return code** - Success (0) or error code
6. **Execution context** - Working directory, environment variables if relevant

### What NOT to Record

- **Timestamps** - FFmpeg includes timing info; normalize or strip
- **Absolute paths** - Use relative paths or path tokens
- **Version strings** - FFmpeg stderr includes version; strip for comparison

## Storage Format

JSON cassette files organized by test scenario:

```
tests/
└── fixtures/
    └── ffmpeg_recordings/
        ├── transcode_mp4_to_webm.json
        ├── extract_audio.json
        ├── apply_filter_chain.json
        └── probe_video_metadata.json
```

### Cassette Structure

```json
{
  "version": 1,
  "recorded_at": "2026-01-25T12:00:00Z",
  "ffmpeg_version": "6.1",
  "interactions": [
    {
      "type": "run",
      "args": ["-i", "INPUT", "-c:v", "libvpx-vp9", "OUTPUT"],
      "stdin": null,
      "result": {
        "returncode": 0,
        "stdout": "",
        "stderr": "6672657573...truncated_hex"
      }
    }
  ]
}
```

## Recording Modes

Inspired by VCR.py's recording modes:

```python
from enum import Enum


class RecordMode(Enum):
    NONE = "none"          # Never record, always replay
    ONCE = "once"          # Record if cassette missing, else replay
    NEW_EPISODES = "new"   # Record new interactions, replay existing
    ALL = "all"            # Always record (for regenerating cassettes)
```

## Path Tokenization

Replace absolute paths with tokens for portability:

```python
def tokenize_args(args: list[str], mappings: dict[str, str]) -> list[str]:
    """Replace paths with tokens for portable recordings.

    Args:
        args: Original command arguments.
        mappings: Dict of path -> token mappings.

    Returns:
        Arguments with paths replaced by tokens.
    """
    result = []
    for arg in args:
        for path, token in mappings.items():
            arg = arg.replace(path, token)
        result.append(arg)
    return result


# Usage in recording
mappings = {
    "/tmp/test_abc123/input.mp4": "INPUT",
    "/tmp/test_abc123/output.webm": "OUTPUT",
}
tokenized = tokenize_args(
    ["-i", "/tmp/test_abc123/input.mp4", "/tmp/test_abc123/output.webm"],
    mappings,
)
# Result: ["-i", "INPUT", "OUTPUT"]
```

## Cassette Management

```python
from pathlib import Path
import json
from dataclasses import asdict


class CassetteManager:
    """Manage FFmpeg recording cassettes."""

    def __init__(self, cassette_dir: Path):
        self.cassette_dir = cassette_dir
        self.cassette_dir.mkdir(parents=True, exist_ok=True)

    def cassette_path(self, name: str) -> Path:
        return self.cassette_dir / f"{name}.json"

    def load(self, name: str) -> list[dict] | None:
        """Load cassette if it exists."""
        path = self.cassette_path(name)
        if path.exists():
            data = json.loads(path.read_text())
            return data["interactions"]
        return None

    def save(self, name: str, interactions: list[dict], ffmpeg_version: str) -> None:
        """Save interactions to cassette."""
        from datetime import datetime, timezone

        data = {
            "version": 1,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "ffmpeg_version": ffmpeg_version,
            "interactions": interactions,
        }
        self.cassette_path(name).write_text(json.dumps(data, indent=2))

    def exists(self, name: str) -> bool:
        return self.cassette_path(name).exists()
```

## Stderr Normalization

FFmpeg stderr contains noisy output. Normalize for comparison:

```python
import re


def normalize_stderr(stderr: str) -> str:
    """Remove non-deterministic parts of FFmpeg stderr."""
    # Remove version line
    stderr = re.sub(r"^ffmpeg version .+$", "", stderr, flags=re.MULTILINE)
    # Remove timestamp lines
    stderr = re.sub(r"^  built with .+$", "", stderr, flags=re.MULTILINE)
    # Remove frame progress
    stderr = re.sub(r"frame=\s*\d+.*$", "", stderr, flags=re.MULTILINE)
    # Remove timing stats
    stderr = re.sub(r"time=\d+:\d+:\d+\.\d+", "time=NORMALIZED", stderr)
    return stderr.strip()
```

## Binary Data Handling

For commands that pipe binary data:

```python
import base64
import hashlib


def store_binary(data: bytes, max_inline_size: int = 1024) -> dict:
    """Store binary data, using hash reference for large content."""
    if len(data) <= max_inline_size:
        return {"type": "inline", "data": data.hex()}
    else:
        # Store hash only; actual data lives in separate file
        return {
            "type": "hash",
            "sha256": hashlib.sha256(data).hexdigest(),
            "size": len(data),
        }
```

## Replay Matching

Match incoming commands to recorded interactions:

```python
def find_matching_interaction(
    args: list[str],
    interactions: list[dict],
    used_indices: set[int],
) -> tuple[int, dict] | None:
    """Find first unused interaction matching the command pattern."""
    for i, interaction in enumerate(interactions):
        if i in used_indices:
            continue
        if interaction["type"] == "run":
            if args_match(args, interaction["args"]):
                return i, interaction
    return None


def args_match(actual: list[str], recorded: list[str]) -> bool:
    """Check if arguments match, accounting for tokens."""
    if len(actual) != len(recorded):
        return False
    for a, r in zip(actual, recorded):
        # Tokens like INPUT/OUTPUT match any value
        if r in ("INPUT", "OUTPUT", "TEMP"):
            continue
        if a != r:
            return False
    return True
```
