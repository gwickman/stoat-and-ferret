# Implementation Plan: FFprobe Wrapper

## Step 1: Create Module Structure
```bash
mkdir -p src/stoat_ferret/ffmpeg
touch src/stoat_ferret/ffmpeg/__init__.py
touch src/stoat_ferret/ffmpeg/probe.py
```

## Step 2: Create VideoMetadata
In `src/stoat_ferret/ffmpeg/probe.py`:

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class VideoMetadata:
    duration_seconds: float
    width: int
    height: int
    frame_rate_numerator: int
    frame_rate_denominator: int
    video_codec: str
    audio_codec: Optional[str]
    file_size: int
    
    @property
    def frame_rate(self) -> float:
        return self.frame_rate_numerator / self.frame_rate_denominator
    
    @property
    def duration_frames(self) -> int:
        return int(self.duration_seconds * self.frame_rate)
```

## Step 3: Implement ffprobe_video
```python
import json
import subprocess
from pathlib import Path

class FFprobeError(Exception):
    """Error running ffprobe."""
    pass

def ffprobe_video(path: str, ffprobe_path: str = "ffprobe") -> VideoMetadata:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Video file not found: {path}")
    
    try:
        result = subprocess.run(
            [
                ffprobe_path,
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                path,
            ],
            capture_output=True,
            timeout=30,
        )
    except FileNotFoundError:
        raise FFprobeError(f"ffprobe not found at: {ffprobe_path}. Is FFmpeg installed?")
    except subprocess.TimeoutExpired:
        raise FFprobeError(f"ffprobe timed out reading: {path}")
    
    if result.returncode != 0:
        raise FFprobeError(f"ffprobe failed for {path}: {result.stderr.decode()}")
    
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise FFprobeError(f"Failed to parse ffprobe output: {e}")
    
    return _parse_ffprobe_output(data, file_path)

def _parse_ffprobe_output(data: dict, file_path: Path) -> VideoMetadata:
    video_stream = next(
        (s for s in data.get("streams", []) if s.get("codec_type") == "video"),
        None
    )
    if not video_stream:
        raise ValueError(f"No video stream found in: {file_path}")
    
    audio_stream = next(
        (s for s in data.get("streams", []) if s.get("codec_type") == "audio"),
        None
    )
    
    # Parse frame rate (e.g., "24/1" or "30000/1001")
    r_frame_rate = video_stream.get("r_frame_rate", "24/1")
    num, den = map(int, r_frame_rate.split("/"))
    
    format_info = data.get("format", {})
    
    return VideoMetadata(
        duration_seconds=float(format_info.get("duration", 0)),
        width=int(video_stream["width"]),
        height=int(video_stream["height"]),
        frame_rate_numerator=num,
        frame_rate_denominator=den,
        video_codec=video_stream["codec_name"],
        audio_codec=audio_stream["codec_name"] if audio_stream else None,
        file_size=int(format_info.get("size", 0)),
    )
```

## Step 4: Add Sample Video for Testing
Create small test video:
```bash
ffmpeg -f lavfi -i testsrc=duration=1:size=320x240:rate=24 -f lavfi -i sine=frequency=440:duration=1 -c:v libx264 -c:a aac tests/fixtures/sample.mp4
```

Commit to tests/fixtures/sample.mp4

## Step 5: Add Unit Tests
```python
import pytest
from stoat_ferret.ffmpeg.probe import ffprobe_video, FFprobeError

def test_ffprobe_video_success():
    metadata = ffprobe_video("tests/fixtures/sample.mp4")
    assert metadata.width == 320
    assert metadata.height == 240
    assert metadata.duration_seconds > 0
    assert metadata.video_codec == "h264"

def test_ffprobe_file_not_found():
    with pytest.raises(FileNotFoundError, match="not found"):
        ffprobe_video("/nonexistent/path.mp4")

def test_ffprobe_not_video(tmp_path):
    text_file = tmp_path / "test.txt"
    text_file.write_text("not a video")
    with pytest.raises((ValueError, FFprobeError)):
        ffprobe_video(str(text_file))
```

## Verification
- Tests pass with real ffprobe
- Error handling works for edge cases