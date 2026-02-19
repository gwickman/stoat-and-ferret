"""Type stubs for stoat_ferret_core._core (internal Rust module).

This module contains the actual PyO3 bindings from Rust.
"""

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

# ========== Clip Types ==========

class Clip:
    """A video clip representing a segment of a source media file.

    A clip defines a portion of a source video through in and out points,
    and optionally includes the source file's total duration for bounds validation.
    """

    @property
    def source_path(self) -> str:
        """Path to the source media file."""
        ...

    @property
    def in_point(self) -> Position:
        """Start position within the source file (inclusive)."""
        ...

    @property
    def out_point(self) -> Position:
        """End position within the source file (exclusive)."""
        ...

    @property
    def source_duration(self) -> Duration | None:
        """Total duration of the source file (optional, used for bounds validation)."""
        ...

    def __new__(
        cls,
        source_path: str,
        in_point: Position,
        out_point: Position,
        source_duration: Duration | None = None,
    ) -> Clip:
        """Creates a new clip.

        Args:
            source_path: Path to the source media file.
            in_point: Start position within the source file.
            out_point: End position within the source file.
            source_duration: Total duration of the source file (optional).

        Returns:
            A new Clip instance.
        """
        ...

    def duration(self) -> Duration | None:
        """Calculates the duration of this clip.

        Returns:
            The duration between in_point and out_point, or None if out_point <= in_point.
        """
        ...

    def __repr__(self) -> str: ...

class ClipValidationError:
    """A validation error with detailed information about what went wrong.

    Each error includes the field name, a human-readable message, and optionally
    the actual and expected values to help users understand and fix the problem.

    Note: This is distinct from the ValidationError exception type.
    This class provides detailed validation failure information as data.
    """

    @property
    def field(self) -> str:
        """The name of the field that failed validation."""
        ...

    @property
    def message(self) -> str:
        """A human-readable message explaining the validation failure."""
        ...

    @property
    def actual(self) -> str | None:
        """The actual value that failed validation (optional)."""
        ...

    @property
    def expected(self) -> str | None:
        """The expected value or constraint (optional)."""
        ...

    def __new__(cls, field: str, message: str) -> ClipValidationError:
        """Creates a new validation error with just a field and message.

        Args:
            field: The name of the field that failed validation.
            message: A human-readable explanation of the error.

        Returns:
            A new ClipValidationError instance.
        """
        ...

    @staticmethod
    def with_values_py(field: str, message: str, actual: str, expected: str) -> ClipValidationError:
        """Creates a validation error with actual and expected values.

        Args:
            field: The name of the field that failed validation.
            message: A human-readable explanation of the error.
            actual: The actual value that was provided.
            expected: The expected value or constraint.

        Returns:
            A new ClipValidationError instance.
        """
        ...

    def __repr__(self) -> str: ...
    def __str__(self) -> str: ...

def validate_clip(clip: Clip) -> list[ClipValidationError]:
    """Validates a single clip and returns all validation errors.

    This function checks:
    - Source path is non-empty
    - Out point is greater than in point
    - In point is within source duration (if source duration is known)
    - Out point is within source duration (if source duration is known)

    Args:
        clip: The clip to validate.

    Returns:
        A list of validation errors. Empty if the clip is valid.
    """
    ...

def validate_clips(clips: list[Clip]) -> list[tuple[int, ClipValidationError]]:
    """Validates a list of clips and returns all validation errors.

    Unlike single-clip validation, this function collects errors from all clips
    and reports which clip index each error belongs to.

    Args:
        clips: A list of clips to validate.

    Returns:
        A list of tuples containing (clip_index, validation_error) for each error found.
    """
    ...

# ========== Timeline Types ==========

class FrameRate:
    """A frame rate represented as a rational number (numerator/denominator)."""

    def __new__(cls, numerator: int, denominator: int) -> FrameRate:
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
    def fps_24() -> FrameRate:
        """Returns a 24 fps frame rate (film standard)."""
        ...

    @staticmethod
    def fps_25() -> FrameRate:
        """Returns a 25 fps frame rate (PAL/SECAM standard)."""
        ...

    @staticmethod
    def fps_30() -> FrameRate:
        """Returns a 30 fps frame rate (NTSC compatible integer rate)."""
        ...

    @staticmethod
    def fps_60() -> FrameRate:
        """Returns a 60 fps frame rate (high frame rate video)."""
        ...

    @staticmethod
    def ntsc_30() -> FrameRate:
        """Returns a 29.97 fps frame rate (NTSC broadcast standard)."""
        ...

    @staticmethod
    def ntsc_60() -> FrameRate:
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

    def __new__(cls, frames: int) -> Position:
        """Creates a position from a frame count.

        Args:
            frames: The frame number (0-indexed).

        Returns:
            A new Position instance.
        """
        ...

    @staticmethod
    def from_frames(frames: int) -> Position:
        """Creates a position from a frame count.

        Args:
            frames: The frame number (0-indexed).

        Returns:
            A new Position instance.
        """
        ...

    @staticmethod
    def from_seconds(seconds: float, frame_rate: FrameRate) -> Position:
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
    ) -> Position:
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
    def __lt__(self, other: Position) -> bool: ...
    def __le__(self, other: Position) -> bool: ...
    def __gt__(self, other: Position) -> bool: ...
    def __ge__(self, other: Position) -> bool: ...
    def __add__(self, other: Duration) -> Position: ...
    def __sub__(self, other: Duration) -> Position: ...

class Duration:
    """A duration on a timeline represented as a frame count."""

    def __new__(cls, frames: int) -> Duration:
        """Creates a duration from a frame count.

        Args:
            frames: The number of frames.

        Returns:
            A new Duration instance.
        """
        ...

    @staticmethod
    def from_frames(frames: int) -> Duration:
        """Creates a duration from a frame count.

        Args:
            frames: The number of frames.

        Returns:
            A new Duration instance.
        """
        ...

    @staticmethod
    def from_seconds(seconds: float, frame_rate: FrameRate) -> Duration:
        """Creates a duration from a time in seconds.

        Args:
            seconds: The time in seconds.
            frame_rate: The frame rate to use for conversion.

        Returns:
            A new Duration instance.
        """
        ...

    @staticmethod
    def between(start: Position, end: Position) -> Duration:
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
    def __lt__(self, other: Duration) -> bool: ...
    def __le__(self, other: Duration) -> bool: ...
    def __gt__(self, other: Duration) -> bool: ...
    def __ge__(self, other: Duration) -> bool: ...
    def __add__(self, other: Duration) -> Duration: ...

class TimeRange:
    """A contiguous time range represented as a half-open interval [start, end)."""

    def __new__(cls, start: Position, end: Position) -> TimeRange:
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

    def overlaps(self, other: TimeRange) -> bool:
        """Checks if this range overlaps with another range."""
        ...

    def adjacent(self, other: TimeRange) -> bool:
        """Checks if this range is adjacent to another range."""
        ...

    def overlap(self, other: TimeRange) -> TimeRange | None:
        """Returns the overlap region between this range and another, if any."""
        ...

    def gap(self, other: TimeRange) -> TimeRange | None:
        """Returns the gap between this range and another, if any."""
        ...

    def intersection(self, other: TimeRange) -> TimeRange | None:
        """Returns the intersection of this range and another."""
        ...

    def union(self, other: TimeRange) -> TimeRange | None:
        """Returns the union of this range and another, if they are contiguous."""
        ...

    def difference(self, other: TimeRange) -> list[TimeRange]:
        """Returns the difference of this range minus another."""
        ...

    def __repr__(self) -> str: ...
    def __eq__(self, other: object) -> bool: ...

# ========== TimeRange List Operations ==========

def find_gaps(ranges: list[TimeRange]) -> list[TimeRange]:
    """Finds gaps between non-overlapping portions of the given ranges.

    The ranges are sorted by start position and merged, then gaps
    between merged ranges are returned.

    Args:
        ranges: List of TimeRange objects to find gaps between.

    Returns:
        List of TimeRange objects representing the gaps between input ranges.
    """
    ...

def merge_ranges(ranges: list[TimeRange]) -> list[TimeRange]:
    """Merges overlapping and adjacent ranges into non-overlapping ranges.

    The result is a minimal set of non-overlapping, non-adjacent ranges
    that cover the same time as the input ranges.

    Args:
        ranges: List of TimeRange objects to merge.

    Returns:
        List of merged TimeRange objects with no overlaps or adjacencies.
    """
    ...

def total_coverage(ranges: list[TimeRange]) -> Duration:
    """Calculates the total duration covered by the given ranges.

    Overlapping ranges are merged before calculating the total,
    so overlapping portions are only counted once.

    Args:
        ranges: List of TimeRange objects to calculate coverage for.

    Returns:
        Duration representing the total time covered by all ranges.
    """
    ...

# ========== FFmpeg Command Building ==========

class FFmpegCommand:
    """A type-safe builder for constructing FFmpeg command arguments."""

    def __new__(cls) -> FFmpegCommand:
        """Creates a new empty FFmpeg command builder."""
        ...

    def overwrite(self, yes: bool) -> FFmpegCommand:
        """Sets the overwrite flag (-y)."""
        ...

    def loglevel(self, level: str) -> FFmpegCommand:
        """Sets the log level (-loglevel)."""
        ...

    def input(self, path: str) -> FFmpegCommand:
        """Adds an input file (-i)."""
        ...

    def seek(self, seconds: float) -> FFmpegCommand:
        """Sets the seek position (-ss) for the most recent input."""
        ...

    def duration(self, seconds: float) -> FFmpegCommand:
        """Sets the duration limit (-t) for the most recent input."""
        ...

    def stream_loop(self, count: int) -> FFmpegCommand:
        """Sets the stream loop count (-stream_loop) for the most recent input."""
        ...

    def output(self, path: str) -> FFmpegCommand:
        """Adds an output file."""
        ...

    def video_codec(self, codec: str) -> FFmpegCommand:
        """Sets the video codec (-c:v) for the most recent output."""
        ...

    def audio_codec(self, codec: str) -> FFmpegCommand:
        """Sets the audio codec (-c:a) for the most recent output."""
        ...

    def preset(self, preset: str) -> FFmpegCommand:
        """Sets the encoding preset (-preset) for the most recent output."""
        ...

    def crf(self, crf: int) -> FFmpegCommand:
        """Sets the CRF quality level (-crf) for the most recent output."""
        ...

    def format(self, format: str) -> FFmpegCommand:
        """Sets the output format (-f) for the most recent output."""
        ...

    def filter_complex(self, filter: str) -> FFmpegCommand:
        """Sets a complex filtergraph (-filter_complex)."""
        ...

    def map(self, stream: str) -> FFmpegCommand:
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

class DrawtextBuilder:
    """Type-safe builder for FFmpeg drawtext filters.

    Constructs drawtext filters with position presets, font styling,
    shadow effects, box backgrounds, and alpha animation via the
    expression engine.

    Example::

        from stoat_ferret_core import DrawtextBuilder

        f = (
            DrawtextBuilder("Hello World")
            .font("monospace")
            .fontsize(24)
            .fontcolor("white")
            .position("center")
            .shadow(2, 2, "black")
            .build()
        )
    """

    def __new__(cls, text: str) -> DrawtextBuilder:
        """Creates a new drawtext builder with the given text.

        The text is automatically escaped for FFmpeg drawtext syntax.

        Args:
            text: The text to display.

        Returns:
            A new DrawtextBuilder instance.
        """
        ...

    def font(self, name: str) -> DrawtextBuilder:
        """Sets the font name via fontconfig lookup.

        Args:
            name: The fontconfig font name (e.g., "monospace", "Sans").

        Returns:
            Self for method chaining.
        """
        ...

    def fontfile(self, path: str) -> DrawtextBuilder:
        """Sets the font file path directly.

        Args:
            path: Path to the font file.

        Returns:
            Self for method chaining.
        """
        ...

    def fontsize(self, size: int) -> DrawtextBuilder:
        """Sets the font size in pixels.

        Default is 16.

        Args:
            size: Font size in pixels.

        Returns:
            Self for method chaining.
        """
        ...

    def fontcolor(self, color: str) -> DrawtextBuilder:
        """Sets the font color.

        Default is "black". Accepts FFmpeg color names or hex values.

        Args:
            color: Font color (e.g., "white", "red", "#FF0000", "white@0.5").

        Returns:
            Self for method chaining.
        """
        ...

    def position(self, preset: str, margin: int = 10, x: int = 0, y: int = 0) -> DrawtextBuilder:
        """Sets the text position using a preset name.

        Preset names: "center", "bottom_center", "top_left", "top_right",
        "bottom_left", "bottom_right", "absolute".

        For presets with margin, pass the margin parameter (default: 10).
        For absolute positioning, pass x and y coordinates.

        Args:
            preset: Position preset name.
            margin: Margin in pixels for corner/edge presets.
            x: X coordinate for absolute positioning.
            y: Y coordinate for absolute positioning.

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If preset name is unknown.
        """
        ...

    def shadow(self, x_offset: int, y_offset: int, color: str) -> DrawtextBuilder:
        """Adds a shadow effect to the text.

        Args:
            x_offset: Horizontal shadow offset in pixels.
            y_offset: Vertical shadow offset in pixels.
            color: Shadow color.

        Returns:
            Self for method chaining.
        """
        ...

    def box_background(self, color: str, borderw: int) -> DrawtextBuilder:
        """Adds a box background behind the text.

        Args:
            color: Box background color (e.g., "black@0.5").
            borderw: Box border width in pixels.

        Returns:
            Self for method chaining.
        """
        ...

    def alpha(self, value: float) -> DrawtextBuilder:
        """Sets a static alpha value (0.0 to 1.0).

        Args:
            value: Alpha value between 0.0 (transparent) and 1.0 (opaque).

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If alpha is not in [0.0, 1.0].
        """
        ...

    def alpha_fade(
        self, start_time: float, fade_in: float, end_time: float, fade_out: float
    ) -> DrawtextBuilder:
        """Sets an alpha fade animation.

        Generates a fade-in/fade-out expression using the expression engine.

        Args:
            start_time: When the text first appears (seconds).
            fade_in: Duration of fade in (seconds).
            end_time: When the text starts fading out (seconds).
            fade_out: Duration of fade out (seconds).

        Returns:
            Self for method chaining.
        """
        ...

    def enable(self, expr: str) -> DrawtextBuilder:
        """Sets a time-based enable expression.

        Args:
            expr: An FFmpeg expression string for the enable parameter.

        Returns:
            Self for method chaining.
        """
        ...

    def build(self) -> Filter:
        """Builds the drawtext filter.

        Returns:
            A Filter that can be used in filter chains and graphs.
        """
        ...

    def __repr__(self) -> str: ...

class SpeedControl:
    """Type-safe speed control builder for FFmpeg video and audio speed adjustment.

    Generates `setpts` filters for video and `atempo` filters for audio.
    The atempo builder automatically chains instances to keep each within
    the [0.5, 2.0] quality range.

    Example::

        from stoat_ferret_core import SpeedControl

        ctrl = SpeedControl(2.0)
        video = ctrl.setpts_filter()
        audio = ctrl.atempo_filters()
    """

    def __new__(cls, factor: float) -> SpeedControl:
        """Creates a new speed control with the given factor.

        Args:
            factor: Speed multiplier in range [0.25, 4.0].

        Raises:
            ValueError: If factor is outside [0.25, 4.0].
        """
        ...

    def drop_audio(self, drop: bool) -> SpeedControl:
        """Sets whether to drop audio instead of speed-adjusting it.

        When enabled, atempo_filters() returns an empty list.

        Args:
            drop: Whether to drop audio.

        Returns:
            Self for method chaining.
        """
        ...

    @property
    def speed_factor(self) -> float:
        """Returns the speed factor."""
        ...

    @property
    def drop_audio_enabled(self) -> bool:
        """Returns whether audio will be dropped."""
        ...

    def setpts_filter(self) -> Filter:
        """Generates the setpts filter for video speed adjustment.

        Returns:
            A Filter with the setpts expression.
        """
        ...

    def atempo_filters(self) -> list[Filter]:
        """Generates atempo filter(s) for audio speed adjustment.

        Returns a list of Filter instances. Multiple filters are chained
        for speeds above 2.0x or below 0.5x to maintain audio quality.
        Returns an empty list if drop_audio is enabled or speed is 1.0.
        """
        ...

    def __repr__(self) -> str: ...

# ========== Audio Mixing Builders ==========

class VolumeBuilder:
    """Type-safe builder for FFmpeg `volume` audio filter.

    Supports linear (float) and dB (string like "3dB") modes, plus precision
    control. Validates volume range 0.0-10.0.

    Example::

        from stoat_ferret_core import VolumeBuilder

        f = VolumeBuilder(0.5).build()
        assert str(f) == "volume=volume=0.5"

        f = VolumeBuilder.from_db("3dB").build()
        assert str(f) == "volume=volume=3dB"
    """

    def __new__(cls, level: float) -> VolumeBuilder:
        """Creates a new volume builder with a linear level.

        Args:
            level: Volume level in range [0.0, 10.0].

        Raises:
            ValueError: If level is outside [0.0, 10.0].
        """
        ...

    @staticmethod
    def from_db(db_str: str) -> VolumeBuilder:
        """Creates a volume builder from a dB string.

        Args:
            db_str: Volume in dB format (e.g., "3dB", "-6dB").

        Returns:
            A new VolumeBuilder instance.

        Raises:
            ValueError: If the dB string is invalid.
        """
        ...

    def precision(self, precision: str) -> VolumeBuilder:
        """Sets the volume precision mode.

        Args:
            precision: Precision mode ("fixed", "float", or "double").

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If precision is not a valid mode.
        """
        ...

    def build(self) -> Filter:
        """Builds the volume filter.

        Returns:
            A Filter instance.
        """
        ...

    def __repr__(self) -> str: ...

class AfadeBuilder:
    """Type-safe builder for FFmpeg `afade` audio filter.

    Supports fade in/out with configurable duration, start time, and curve type.

    Example::

        from stoat_ferret_core import AfadeBuilder

        f = AfadeBuilder("in", 3.0).build()
        assert str(f) == "afade=t=in:d=3"
    """

    def __new__(cls, fade_type: str, duration: float) -> AfadeBuilder:
        """Creates a new fade builder.

        Args:
            fade_type: Either "in" or "out".
            duration: Fade duration in seconds (must be > 0).

        Raises:
            ValueError: If fade_type is invalid or duration <= 0.
        """
        ...

    def start_time(self, time: float) -> AfadeBuilder:
        """Sets the start time of the fade.

        Args:
            time: Start time in seconds.

        Returns:
            Self for method chaining.
        """
        ...

    def curve(self, curve: str) -> AfadeBuilder:
        """Sets the fade curve type.

        Args:
            curve: Curve name. Valid: "tri", "qsin", "hsin", "esin", "log",
                "ipar", "qua", "cub", "squ", "cbr", "par".

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If curve name is not recognized.
        """
        ...

    def build(self) -> Filter:
        """Builds the afade filter.

        Returns:
            A Filter instance.
        """
        ...

    def __repr__(self) -> str: ...

class AmixBuilder:
    """Type-safe builder for FFmpeg `amix` audio mixing filter.

    Mixes multiple audio inputs into a single output.

    Example::

        from stoat_ferret_core import AmixBuilder

        f = AmixBuilder(4).build()
        assert str(f) == "amix=inputs=4"
    """

    def __new__(cls, inputs: int) -> AmixBuilder:
        """Creates a new amix builder.

        Args:
            inputs: Number of input streams (2-32).

        Raises:
            ValueError: If inputs is outside [2, 32].
        """
        ...

    def duration_mode(self, mode: str) -> AmixBuilder:
        """Sets the duration mode.

        Args:
            mode: Duration mode ("longest", "shortest", or "first").

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If mode is not recognized.
        """
        ...

    def weights(self, weights: list[float]) -> AmixBuilder:
        """Sets per-input weights.

        Args:
            weights: List of float weights, one per input.

        Returns:
            Self for method chaining.
        """
        ...

    def normalize(self, enable: bool) -> AmixBuilder:
        """Sets whether to normalize output volume.

        Args:
            enable: Whether to enable normalization.

        Returns:
            Self for method chaining.
        """
        ...

    def build(self) -> Filter:
        """Builds the amix filter.

        Returns:
            A Filter instance.
        """
        ...

    def __repr__(self) -> str: ...

class DuckingPattern:
    """Builds a ducking pattern that lowers music volume during speech.

    Uses FFmpeg's sidechaincompress filter in a FilterGraph composition.

    Example::

        from stoat_ferret_core import DuckingPattern

        graph = DuckingPattern().build()
        s = str(graph)
        assert "asplit" in s
        assert "sidechaincompress" in s
    """

    def __new__(cls) -> DuckingPattern:
        """Creates a new ducking pattern with default parameters."""
        ...

    def threshold(self, value: float) -> DuckingPattern:
        """Sets the compression threshold (0.0-1.0).

        Args:
            value: Threshold value.

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If value is outside [0.0, 1.0].
        """
        ...

    def ratio(self, value: float) -> DuckingPattern:
        """Sets the compression ratio (1.0-20.0).

        Args:
            value: Ratio value.

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If value is outside [1.0, 20.0].
        """
        ...

    def attack(self, value: float) -> DuckingPattern:
        """Sets the attack time in milliseconds (0.01-2000.0).

        Args:
            value: Attack time in ms.

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If value is outside [0.01, 2000.0].
        """
        ...

    def release(self, value: float) -> DuckingPattern:
        """Sets the release time in milliseconds (0.01-9000.0).

        Args:
            value: Release time in ms.

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If value is outside [0.01, 9000.0].
        """
        ...

    def build(self) -> FilterGraph:
        """Builds the ducking filter graph.

        Returns:
            A FilterGraph containing the ducking pattern.
        """
        ...

    def __repr__(self) -> str: ...

class Filter:
    """A single FFmpeg filter with optional parameters."""

    def __new__(cls, name: str) -> Filter:
        """Creates a new filter with the given name."""
        ...

    def param(self, key: str, value: str) -> Filter:
        """Adds a parameter to the filter."""
        ...

    @staticmethod
    def scale(width: int, height: int) -> Filter:
        """Creates a scale filter for resizing video."""
        ...

    @staticmethod
    def scale_fit(width: int, height: int) -> Filter:
        """Creates a scale filter that maintains aspect ratio."""
        ...

    @staticmethod
    def concat(n: int, v: int, a: int) -> Filter:
        """Creates a concat filter for concatenating multiple inputs."""
        ...

    @staticmethod
    def pad(width: int, height: int, color: str) -> Filter:
        """Creates a pad filter to add borders and center content."""
        ...

    @staticmethod
    def format(pix_fmt: str) -> Filter:
        """Creates a format filter for pixel format conversion."""
        ...

    def __str__(self) -> str: ...
    def __repr__(self) -> str: ...

class FilterChain:
    """A chain of filters connected in sequence."""

    def __new__(cls) -> FilterChain:
        """Creates a new empty filter chain."""
        ...

    def input(self, label: str) -> FilterChain:
        """Adds an input label to the chain."""
        ...

    def filter(self, f: Filter) -> FilterChain:
        """Adds a filter to the chain."""
        ...

    def output(self, label: str) -> FilterChain:
        """Adds an output label to the chain."""
        ...

    def __str__(self) -> str: ...
    def __repr__(self) -> str: ...

class FilterGraph:
    """A complete filter graph composed of multiple filter chains."""

    def __new__(cls) -> FilterGraph:
        """Creates a new empty filter graph."""
        ...

    def chain(self, chain: FilterChain) -> FilterGraph:
        """Adds a filter chain to the graph."""
        ...

    def compose_chain(self, input: str, filters: list[Filter]) -> str:
        """Compose filters sequentially on a single stream.

        Connects filters in order with auto-generated intermediate labels.

        Args:
            input: The input pad label to start the chain from.
            filters: One or more filters to apply sequentially.

        Returns:
            The output pad label of the final filter.

        Raises:
            ValueError: If filters is empty.
        """
        ...

    def compose_branch(self, input: str, count: int, audio: bool = False) -> list[str]:
        """Split a stream into multiple branches.

        Uses ``split`` for video or ``asplit`` for audio.

        Args:
            input: The input pad label to split.
            count: Number of output branches (must be >= 2).
            audio: If True, use ``asplit`` instead of ``split``.

        Returns:
            List of output pad labels, one per branch.

        Raises:
            ValueError: If count < 2.
        """
        ...

    def compose_merge(self, inputs: list[str], merge_filter: Filter) -> str:
        """Merge multiple streams through a single filter.

        Args:
            inputs: Input pad labels to merge (must be >= 2).
            merge_filter: The filter to merge through (e.g. overlay, amix, concat).

        Returns:
            The output pad label.

        Raises:
            ValueError: If fewer than 2 inputs provided.
        """
        ...

    def __str__(self) -> str: ...
    def __repr__(self) -> str: ...

# ========== Expression Engine ==========

class Expr:
    """A type-safe FFmpeg filter expression builder.

    Expressions are built using static constructor methods and operator
    overloading, then serialized to FFmpeg syntax via str().

    Supports constants, variables (t, n, w, h, etc.), arithmetic operators
    (+, -, *, /), and FFmpeg functions (between, if, gt, lt, etc.).
    """

    @staticmethod
    def constant(value: float) -> Expr:
        """Creates a constant numeric expression.

        Args:
            value: The numeric value.

        Returns:
            A new Expr representing a constant.
        """
        ...

    @staticmethod
    def var(name: str) -> Expr:
        """Creates a variable expression from a variable name string.

        Valid names: "t", "n", "pos", "w", "h", "text_w", "text_h",
        "line_h", "main_w", "main_h".

        Args:
            name: The FFmpeg variable name.

        Returns:
            A new Expr representing a variable.

        Raises:
            ValueError: If the variable name is not recognized.
        """
        ...

    @staticmethod
    def negate(operand: Expr) -> Expr:
        """Creates a negation expression (-x).

        Args:
            operand: The expression to negate.

        Returns:
            A new Expr representing the negation.
        """
        ...

    @staticmethod
    def between(x: Expr, min: Expr, max: Expr) -> Expr:
        """Creates a between(x, min, max) expression.

        Returns 1 if min <= x <= max, 0 otherwise.

        Args:
            x: The value to test.
            min: The minimum bound.
            max: The maximum bound.

        Returns:
            A new Expr representing the between function.
        """
        ...

    @staticmethod
    def if_then_else(cond: Expr, then_expr: Expr, else_expr: Expr) -> Expr:
        """Creates an if(cond, then, else) conditional expression.

        Args:
            cond: The condition expression.
            then_expr: Expression evaluated when condition is true.
            else_expr: Expression evaluated when condition is false.

        Returns:
            A new Expr representing the conditional.
        """
        ...

    @staticmethod
    def if_not(cond: Expr, then_expr: Expr, else_expr: Expr) -> Expr:
        """Creates an ifnot(cond, then, else) inverted conditional expression.

        Args:
            cond: The condition expression.
            then_expr: Expression evaluated when condition is false.
            else_expr: Expression evaluated when condition is true.

        Returns:
            A new Expr representing the inverted conditional.
        """
        ...

    @staticmethod
    def lt(a: Expr, b: Expr) -> Expr:
        """Creates a lt(x, y) less-than expression."""
        ...

    @staticmethod
    def gt(a: Expr, b: Expr) -> Expr:
        """Creates a gt(x, y) greater-than expression."""
        ...

    @staticmethod
    def eq_expr(a: Expr, b: Expr) -> Expr:
        """Creates an eq(x, y) equality expression."""
        ...

    @staticmethod
    def gte(a: Expr, b: Expr) -> Expr:
        """Creates a gte(x, y) greater-than-or-equal expression."""
        ...

    @staticmethod
    def lte(a: Expr, b: Expr) -> Expr:
        """Creates a lte(x, y) less-than-or-equal expression."""
        ...

    @staticmethod
    def clip(x: Expr, min: Expr, max: Expr) -> Expr:
        """Creates a clip(x, min, max) clamping expression."""
        ...

    @staticmethod
    def abs(x: Expr) -> Expr:
        """Creates an abs(x) absolute value expression."""
        ...

    @staticmethod
    def min(a: Expr, b: Expr) -> Expr:
        """Creates a min(x, y) minimum expression."""
        ...

    @staticmethod
    def max(a: Expr, b: Expr) -> Expr:
        """Creates a max(x, y) maximum expression."""
        ...

    @staticmethod
    def modulo(a: Expr, b: Expr) -> Expr:
        """Creates a mod(x, y) modulo expression."""
        ...

    @staticmethod
    def not_(x: Expr) -> Expr:
        """Creates a not(x) logical not expression."""
        ...

    def __add__(self, other: Expr) -> Expr: ...
    def __sub__(self, other: Expr) -> Expr: ...
    def __mul__(self, other: Expr) -> Expr: ...
    def __truediv__(self, other: Expr) -> Expr: ...
    def __neg__(self) -> Expr: ...
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
