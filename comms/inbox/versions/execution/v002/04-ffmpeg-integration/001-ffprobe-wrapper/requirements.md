# FFprobe Wrapper

## Goal
Create wrapper that runs ffprobe and returns structured video metadata.

## Requirements

### FR-001: VideoMetadata Dataclass
Create dataclass with:
- duration_seconds: float
- duration_frames: int (computed from duration and frame_rate)
- width: int
- height: int
- frame_rate: tuple[int, int] (numerator, denominator)
- video_codec: str
- audio_codec: str | None
- file_size: int

### FR-002: ffprobe_video Function
- Signature: ffprobe_video(path: str, ffprobe_path: str = "ffprobe") -> VideoMetadata
- Run ffprobe with JSON output
- Parse and return VideoMetadata
- Raise FileNotFoundError if path doesn't exist
- Raise ValueError if not a video file

### FR-003: Error Handling
- Handle ffprobe not installed
- Handle corrupt/unreadable files
- Include helpful error messages

### FR-004: Contract Test
- Test with real ffprobe on sample video in CI
- Sample video committed to tests/fixtures/

## Acceptance Criteria
- [ ] ffprobe_video returns correct metadata
- [ ] Errors handled gracefully with clear messages
- [ ] Contract test passes with real ffprobe