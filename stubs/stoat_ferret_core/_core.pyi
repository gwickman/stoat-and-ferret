"""Type stubs for stoat_ferret_core._core (internal Rust module).

This module contains the actual PyO3 bindings from Rust.
"""

from typing import Optional

# ========== Custom Exception Types ==========


class ValidationError(Exception):
    """Raised when validation of input parameters fails.

    This exception is raised when:
    - Timeline parameters are invalid (e.g., end before start)
    - Frame rate has zero denominator
    - Timecode components are out of range
    """

    ...


class CommandError(Exception):
    """Raised when FFmpeg command building fails.

    This exception is raised when:
    - No inputs are provided to the command
    - No outputs are provided to the command
    - Required parameters are missing
    """

    ...


class SanitizationError(Exception):
    """Raised when input sanitization fails.

    This exception is raised when:
    - Path validation fails (empty or contains null bytes)
    - Numeric bounds validation fails (CRF, speed, volume out of range)
    - Codec/preset validation fails (not in allowed list)
    """

    ...


# ========== Utility Functions ==========

def health_check() -> str:
    """Performs a health check to verify the Rust module is loaded correctly.

    Returns:
        A status string indicating the module is operational.
    """
    ...

# ========== Timeline Types ==========

class FrameRate:
    """A frame rate represented as a rational number (numerator/denominator)."""

    def __new__(cls, numerator: int, denominator: int) -> "FrameRate":
        """Creates a new frame rate from numerator and denominator.

        Args:
            numerator: The number of frames.
            denominator: The time unit (typically 1 for integer rates, 1001 for NTSC).

        Returns:
            A new FrameRate instance.

        Raises:
            ValueError: If denominator is zero.
        """
        ...

    @staticmethod
    def fps_24() -> "FrameRate":
        """Returns a 24 fps frame rate (film standard)."""
        ...

    @staticmethod
    def fps_25() -> "FrameRate":
        """Returns a 25 fps frame rate (PAL/SECAM standard)."""
        ...

    @staticmethod
    def fps_30() -> "FrameRate":
        """Returns a 30 fps frame rate (NTSC compatible integer rate)."""
        ...

    @staticmethod
    def fps_60() -> "FrameRate":
        """Returns a 60 fps frame rate (high frame rate video)."""
        ...

    @staticmethod
    def ntsc_30() -> "FrameRate":
        """Returns a 29.97 fps frame rate (NTSC broadcast standard)."""
        ...

    @staticmethod
    def ntsc_60() -> "FrameRate":
        """Returns a 59.94 fps frame rate (NTSC high frame rate)."""
        ...

    @property
    def numerator(self) -> int:
        """The numerator of the frame rate fraction."""
        ...

    @property
    def denominator(self) -> int:
        """The denominator of the frame rate fraction."""
        ...

    def as_float(self) -> float:
        """Returns the frame rate as a floating point number."""
        ...

    def __repr__(self) -> str: ...
    def __eq__(self, other: object) -> bool: ...


class Position:
    """A position on a timeline represented as a frame count."""

    @staticmethod
    def from_frames(frames: int) -> "Position":
        """Creates a position from a frame count.

        Args:
            frames: The frame number (0-indexed).

        Returns:
            A new Position instance.
        """
        ...

    @staticmethod
    def from_seconds(seconds: float, frame_rate: FrameRate) -> "Position":
        """Creates a position from a time in seconds.

        Args:
            seconds: The time in seconds.
            frame_rate: The frame rate to use for conversion.

        Returns:
            A new Position instance.
        """
        ...

    @staticmethod
    def from_timecode(
        hours: int, minutes: int, seconds: int, frames: int, frame_rate: FrameRate
    ) -> "Position":
        """Creates a position from a timecode.

        Args:
            hours: Hours component.
            minutes: Minutes component.
            seconds: Seconds component.
            frames: Frames component.
            frame_rate: The frame rate for interpretation.

        Returns:
            A new Position instance.

        Raises:
            ValueError: If any component is out of valid range.
        """
        ...

    def frames(self) -> int:
        """Returns the position as a frame count."""
        ...

    def to_seconds(self, frame_rate: FrameRate) -> float:
        """Converts the position to seconds.

        Args:
            frame_rate: The frame rate to use for conversion.

        Returns:
            The position in seconds.
        """
        ...

    def __repr__(self) -> str: ...
    def __eq__(self, other: object) -> bool: ...
    def __lt__(self, other: "Position") -> bool: ...
    def __le__(self, other: "Position") -> bool: ...
    def __gt__(self, other: "Position") -> bool: ...
    def __ge__(self, other: "Position") -> bool: ...
    def __add__(self, other: "Duration") -> "Position": ...
    def __sub__(self, other: "Duration") -> "Position": ...


class Duration:
    """A duration on a timeline represented as a frame count."""

    @staticmethod
    def from_frames(frames: int) -> "Duration":
        """Creates a duration from a frame count.

        Args:
            frames: The number of frames.

        Returns:
            A new Duration instance.
        """
        ...

    @staticmethod
    def from_seconds(seconds: float, frame_rate: FrameRate) -> "Duration":
        """Creates a duration from a time in seconds.

        Args:
            seconds: The time in seconds.
            frame_rate: The frame rate to use for conversion.

        Returns:
            A new Duration instance.
        """
        ...

    @staticmethod
    def between(start: Position, end: Position) -> "Duration":
        """Creates a duration as the difference between two positions.

        Args:
            start: The start position.
            end: The end position.

        Returns:
            A new Duration instance.

        Raises:
            ValueError: If end is before start.
        """
        ...

    def frames(self) -> int:
        """Returns the duration as a frame count."""
        ...

    def to_seconds(self, frame_rate: FrameRate) -> float:
        """Converts the duration to seconds.

        Args:
            frame_rate: The frame rate to use for conversion.

        Returns:
            The duration in seconds.
        """
        ...

    def __repr__(self) -> str: ...
    def __eq__(self, other: object) -> bool: ...
    def __lt__(self, other: "Duration") -> bool: ...
    def __le__(self, other: "Duration") -> bool: ...
    def __gt__(self, other: "Duration") -> bool: ...
    def __ge__(self, other: "Duration") -> bool: ...
    def __add__(self, other: "Duration") -> "Duration": ...


class TimeRange:
    """A contiguous time range represented as a half-open interval [start, end)."""

    def __new__(cls, start: Position, end: Position) -> "TimeRange":
        """Creates a new time range from start and end positions.

        Args:
            start: The start position (inclusive).
            end: The end position (exclusive).

        Returns:
            A new TimeRange instance.

        Raises:
            ValueError: If end <= start.
        """
        ...

    @property
    def start(self) -> Position:
        """The start position of the range."""
        ...

    @property
    def end(self) -> Position:
        """The end position of the range."""
        ...

    @property
    def duration(self) -> Duration:
        """The duration of the range."""
        ...

    def overlaps(self, other: "TimeRange") -> bool:
        """Checks if this range overlaps with another range."""
        ...

    def adjacent(self, other: "TimeRange") -> bool:
        """Checks if this range is adjacent to another range."""
        ...

    def overlap(self, other: "TimeRange") -> Optional["TimeRange"]:
        """Returns the overlap region between this range and another, if any."""
        ...

    def gap(self, other: "TimeRange") -> Optional["TimeRange"]:
        """Returns the gap between this range and another, if any."""
        ...

    def intersection(self, other: "TimeRange") -> Optional["TimeRange"]:
        """Returns the intersection of this range and another."""
        ...

    def union(self, other: "TimeRange") -> Optional["TimeRange"]:
        """Returns the union of this range and another, if they are contiguous."""
        ...

    def difference(self, other: "TimeRange") -> list["TimeRange"]:
        """Returns the difference of this range minus another."""
        ...

    def __repr__(self) -> str: ...
    def __eq__(self, other: object) -> bool: ...


# ========== FFmpeg Command Building ==========

class FFmpegCommand:
    """A type-safe builder for constructing FFmpeg command arguments."""

    def __new__(cls) -> "FFmpegCommand":
        """Creates a new empty FFmpeg command builder."""
        ...

    def overwrite(self, yes: bool) -> "FFmpegCommand":
        """Sets the overwrite flag (-y)."""
        ...

    def loglevel(self, level: str) -> "FFmpegCommand":
        """Sets the log level (-loglevel)."""
        ...

    def input(self, path: str) -> "FFmpegCommand":
        """Adds an input file (-i)."""
        ...

    def seek(self, seconds: float) -> "FFmpegCommand":
        """Sets the seek position (-ss) for the most recent input."""
        ...

    def duration(self, seconds: float) -> "FFmpegCommand":
        """Sets the duration limit (-t) for the most recent input."""
        ...

    def stream_loop(self, count: int) -> "FFmpegCommand":
        """Sets the stream loop count (-stream_loop) for the most recent input."""
        ...

    def output(self, path: str) -> "FFmpegCommand":
        """Adds an output file."""
        ...

    def video_codec(self, codec: str) -> "FFmpegCommand":
        """Sets the video codec (-c:v) for the most recent output."""
        ...

    def audio_codec(self, codec: str) -> "FFmpegCommand":
        """Sets the audio codec (-c:a) for the most recent output."""
        ...

    def preset(self, preset: str) -> "FFmpegCommand":
        """Sets the encoding preset (-preset) for the most recent output."""
        ...

    def crf(self, crf: int) -> "FFmpegCommand":
        """Sets the CRF quality level (-crf) for the most recent output."""
        ...

    def format(self, format: str) -> "FFmpegCommand":
        """Sets the output format (-f) for the most recent output."""
        ...

    def filter_complex(self, filter: str) -> "FFmpegCommand":
        """Sets a complex filtergraph (-filter_complex)."""
        ...

    def map(self, stream: str) -> "FFmpegCommand":
        """Adds a stream mapping (-map) for the most recent output."""
        ...

    def build(self) -> list[str]:
        """Builds the FFmpeg command arguments.

        Returns:
            A list of strings suitable for passing to subprocess.

        Raises:
            ValueError: If validation fails (no inputs, no outputs, empty paths, invalid CRF).
        """
        ...

    def __repr__(self) -> str: ...


class Filter:
    """A single FFmpeg filter with optional parameters."""

    def __new__(cls, name: str) -> "Filter":
        """Creates a new filter with the given name."""
        ...

    def param(self, key: str, value: str) -> "Filter":
        """Adds a parameter to the filter."""
        ...

    @staticmethod
    def scale(width: int, height: int) -> "Filter":
        """Creates a scale filter for resizing video."""
        ...

    @staticmethod
    def scale_fit(width: int, height: int) -> "Filter":
        """Creates a scale filter that maintains aspect ratio."""
        ...

    @staticmethod
    def concat(n: int, v: int, a: int) -> "Filter":
        """Creates a concat filter for concatenating multiple inputs."""
        ...

    @staticmethod
    def pad(width: int, height: int, color: str) -> "Filter":
        """Creates a pad filter to add borders and center content."""
        ...

    @staticmethod
    def format(pix_fmt: str) -> "Filter":
        """Creates a format filter for pixel format conversion."""
        ...

    def __str__(self) -> str: ...
    def __repr__(self) -> str: ...


class FilterChain:
    """A chain of filters connected in sequence."""

    def __new__(cls) -> "FilterChain":
        """Creates a new empty filter chain."""
        ...

    def input(self, label: str) -> "FilterChain":
        """Adds an input label to the chain."""
        ...

    def filter(self, f: Filter) -> "FilterChain":
        """Adds a filter to the chain."""
        ...

    def output(self, label: str) -> "FilterChain":
        """Adds an output label to the chain."""
        ...

    def __str__(self) -> str: ...
    def __repr__(self) -> str: ...


class FilterGraph:
    """A complete filter graph composed of multiple filter chains."""

    def __new__(cls) -> "FilterGraph":
        """Creates a new empty filter graph."""
        ...

    def chain(self, chain: FilterChain) -> "FilterGraph":
        """Adds a filter chain to the graph."""
        ...

    def __str__(self) -> str: ...
    def __repr__(self) -> str: ...


# ========== Filter Helper Functions ==========

def scale_filter(width: int, height: int) -> Filter:
    """Creates a scale filter for resizing video.

    Args:
        width: Target width in pixels (-1 for auto).
        height: Target height in pixels (-1 for auto).

    Returns:
        A Filter instance.
    """
    ...


def concat_filter(n: int, v: int, a: int) -> Filter:
    """Creates a concat filter for concatenating multiple inputs.

    Args:
        n: Number of input segments.
        v: Number of video streams per segment (0 or 1).
        a: Number of audio streams per segment (0 or 1).

    Returns:
        A Filter instance.
    """
    ...


# ========== Sanitization Functions ==========

def escape_filter_text(input: str) -> str:
    """Escapes special characters in text for use in FFmpeg filter parameters.

    Args:
        input: The text to escape.

    Returns:
        The escaped text safe for use in FFmpeg filter parameters.
    """
    ...


def validate_path(path: str) -> None:
    """Validates that a file path is safe to use.

    Args:
        path: The path to validate.

    Raises:
        ValueError: If the path is empty or contains null bytes.
    """
    ...


def validate_crf(crf: int) -> int:
    """Validates a CRF (Constant Rate Factor) value.

    Args:
        crf: The CRF value to validate (0-51).

    Returns:
        The validated CRF value.

    Raises:
        ValueError: If the value is out of range.
    """
    ...


def validate_speed(speed: float) -> float:
    """Validates a speed multiplier for video playback.

    Args:
        speed: The speed multiplier to validate (0.25-4.0).

    Returns:
        The validated speed value.

    Raises:
        ValueError: If the value is out of range.
    """
    ...


def validate_volume(volume: float) -> float:
    """Validates an audio volume multiplier.

    Args:
        volume: The volume multiplier to validate (0.0-10.0).

    Returns:
        The validated volume value.

    Raises:
        ValueError: If the value is out of range.
    """
    ...


def validate_video_codec(codec: str) -> str:
    """Validates a video codec name.

    Args:
        codec: The codec name to validate.

    Returns:
        The validated codec name.

    Raises:
        ValueError: If the codec is not in the allowed list.
    """
    ...


def validate_audio_codec(codec: str) -> str:
    """Validates an audio codec name.

    Args:
        codec: The codec name to validate.

    Returns:
        The validated codec name.

    Raises:
        ValueError: If the codec is not in the allowed list.
    """
    ...


def validate_preset(preset: str) -> str:
    """Validates an encoding preset name.

    Args:
        preset: The preset name to validate.

    Returns:
        The validated preset name.

    Raises:
        ValueError: If the preset is not in the allowed list.
    """
    ...

