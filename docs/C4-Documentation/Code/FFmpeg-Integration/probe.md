# FFmpeg Probe

**Source:** `src/stoat_ferret/ffmpeg/probe.py`
**Component:** FFmpeg Integration

## Purpose

Provides an async wrapper around ffprobe for extracting video metadata. Parses ffprobe JSON output into structured VideoMetadata objects with computed properties like frame count and frame rate ratios.

## Public Interface

### Classes

- `VideoMetadata`: Video metadata extracted from ffprobe
  - `duration_seconds: float`: Video duration in seconds
  - `width: int`: Video width in pixels
  - `height: int`: Video height in pixels
  - `frame_rate_numerator: int`: Frame rate numerator (e.g., 30000 in 30000/1001)
  - `frame_rate_denominator: int`: Frame rate denominator (e.g., 1001 in 30000/1001)
  - `video_codec: str`: Video codec name (e.g., "h264")
  - `audio_codec: str | None`: Audio codec name or None if no audio
  - `file_size: int`: File size in bytes
  - `frame_rate` property: `tuple[int, int]` - Returns (numerator, denominator)
  - `duration_frames` property: `int` - Computed frame count from duration and frame rate

- `FFprobeError`: Exception raised when ffprobe execution fails
  - Inherits from Exception
  - Raised for missing ffprobe, timeouts, or output parsing failures

### Functions

- `ffprobe_video(path: str, ffprobe_path: str = "ffprobe") -> VideoMetadata`: Run ffprobe and return structured metadata
  - Async function using asyncio
  - Args: path to video file, optional ffprobe executable path
  - Returns: VideoMetadata object
  - Raises: FileNotFoundError, FFprobeError, ValueError

- `_parse_ffprobe_output(data: dict[str, Any], file_path: Path) -> VideoMetadata`: Parse ffprobe JSON output
  - Internal helper function
  - Args: Parsed JSON dict and original file path
  - Returns: VideoMetadata extracted from ffprobe output
  - Raises: ValueError if no video stream found

## Dependencies

### Internal Dependencies

None

### External Dependencies

- `asyncio`: Async subprocess creation and communication
  - `asyncio.create_subprocess_exec()`: Launch ffprobe process
  - `asyncio.wait_for()`: Timeout enforcement with 30s default
  - `asyncio.TimeoutError`: Raised by wait_for() on timeout (caught and converted to FFprobeError)
- `json`: Parse ffprobe JSON output with `json.loads()`
- `pathlib.Path`: File existence checks and error messages
- `typing.Any`: Type hints for JSON data

## Key Implementation Details

### Async Subprocess Pattern

`ffprobe_video()` uses asyncio subprocess:
1. Creates subprocess with `asyncio.create_subprocess_exec()`
2. Launches ffprobe with args:
   - `-v quiet`: Suppress verbose output
   - `-print_format json`: Request JSON output
   - `-show_format`: Include file format metadata
   - `-show_streams`: Include stream information
   - `path`: The video file to probe
3. Communicates with timeout:
   - `asyncio.wait_for(proc.communicate(), timeout=30)` - 30 second timeout
   - Timeout raises `asyncio.TimeoutError`
4. Kills process on timeout:
   - `proc.kill()` terminates the process
   - `await proc.communicate()` waits for termination

### Error Handling

Comprehensive error handling with specific exceptions:

1. **FileNotFoundError** (ffprobe executable not found)
   - Caught from subprocess creation
   - Raised as FFprobeError with helpful message about FFmpeg installation

2. **asyncio.TimeoutError** (ffprobe takes >30 seconds)
   - Caught and converted to FFprobeError
   - Includes timeout duration and file path

3. **Non-zero return code** (ffprobe execution failed)
   - Checked via `proc.returncode != 0`
   - Includes stderr text decoded with error replacement

4. **JSON parsing failure** (malformed ffprobe output)
   - Caught from `json.loads()`
   - Preserved with original JSONDecodeError

5. **No video stream** (file is audio-only or invalid)
   - Checked in `_parse_ffprobe_output()`
   - Raised as ValueError with file path

### File Existence Validation

Pre-execution check:
- `Path(path).exists()` validates file before launching ffprobe
- Raises FileNotFoundError if missing
- Prevents subprocess creation for non-existent files

### Frame Rate Parsing

Handles frame rates as rational numbers:
- FFmpeg represents frame rate as "numerator/denominator" string (e.g., "30000/1001")
- Parsed via `map(int, r_frame_rate.split("/"))`
- Defaults to "24/1" (24 fps) if field missing
- Supports NTSC (30000/1001) and other fractional rates

### Frame Count Calculation

Computes total frames from duration and frame rate:
```python
fps = frame_rate_numerator / frame_rate_denominator
duration_frames = int(duration_seconds * fps)
```
- Converts duration to frame count
- Useful for timeline calculations and progress tracking
- Integer truncation (not rounding)

### Metadata Extraction

`_parse_ffprobe_output()` extracts data from ffprobe JSON:
1. Locates first video stream: `next((s for s in ... if codec_type == "video"), None)`
2. Locates audio stream (optional): Similar pattern but can be None
3. Extracts format metadata: `data.get("format", {})`
4. Parses frame rate, resolution, codecs, duration, file size
5. Handles optional audio codec (None if no audio)

## Relationships

- **Used by:** Application code needing video metadata for timeline, codec, and duration information
- **Uses:** Async subprocess execution, JSON parsing, pathlib file operations
