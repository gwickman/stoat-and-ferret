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

    Builds drawtext filters with position presets, font styling, shadow,
    box background, and alpha animation via the expression engine.
    """

    def __new__(cls, text: str) -> DrawtextBuilder:
        """Creates a new drawtext builder with the given text.

        The text is automatically escaped for FFmpeg drawtext syntax,
        including ``%`` -> ``%%`` for text expansion mode.

        Args:
            text: The text to display.
        """
        ...

    def font(self, name: str) -> DrawtextBuilder:
        """Sets the font name via fontconfig lookup.

        Args:
            name: The fontconfig font name (e.g., "monospace", "Sans").
        """
        ...

    def fontfile(self, path: str) -> DrawtextBuilder:
        """Sets the font file path directly.

        Args:
            path: Path to the font file.
        """
        ...

    def fontsize(self, size: int) -> DrawtextBuilder:
        """Sets the font size in pixels. Default is 16.

        Args:
            size: Font size in pixels.
        """
        ...

    def fontcolor(self, color: str) -> DrawtextBuilder:
        """Sets the font color. Default is "black".

        Args:
            color: Font color (e.g., "white", "#FF0000", "white@0.5").
        """
        ...

    def position(self, preset: str, margin: int = 10, x: int = 0, y: int = 0) -> DrawtextBuilder:
        """Sets the text position using a preset name.

        Preset names: "center", "bottom_center", "top_left", "top_right",
        "bottom_left", "bottom_right", "absolute".

        For margin-based presets, pass the margin parameter.
        For absolute positioning, use preset="absolute" with x and y.

        Args:
            preset: Position preset name.
            margin: Margin in pixels for margin-based presets (default: 10).
            x: X coordinate for absolute positioning (default: 0).
            y: Y coordinate for absolute positioning (default: 0).

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
        """
        ...

    def box_background(self, color: str, borderw: int) -> DrawtextBuilder:
        """Adds a box background behind the text.

        Args:
            color: Box background color (e.g., "black@0.5").
            borderw: Box border width in pixels.
        """
        ...

    def alpha(self, value: float) -> DrawtextBuilder:
        """Sets a static alpha value.

        Args:
            value: Alpha value between 0.0 (transparent) and 1.0 (opaque).

        Raises:
            ValueError: If alpha is not in [0.0, 1.0].
        """
        ...

    def alpha_fade(
        self, start_time: float, fade_in: float, end_time: float, fade_out: float
    ) -> DrawtextBuilder:
        """Sets an alpha fade animation using the expression engine.

        Args:
            start_time: When the text first appears (seconds).
            fade_in: Duration of fade in (seconds).
            end_time: When the text starts fading out (seconds).
            fade_out: Duration of fade out (seconds).
        """
        ...

    def enable(self, expr: str) -> DrawtextBuilder:
        """Sets a time-based enable expression.

        Args:
            expr: An FFmpeg expression string for the enable parameter.
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
    """Speed control builder for FFmpeg video and audio speed adjustment.

    Generates setpts filters for video and atempo filters for audio.
    The atempo builder automatically chains instances to keep each within
    the [0.5, 2.0] quality range.
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
        Useful for timelapse-style effects.

        Args:
            drop: True to drop audio, False to speed-adjust it.
        """
        ...

    @property
    def speed_factor(self) -> float:
        """The speed multiplier."""
        ...

    @property
    def drop_audio_enabled(self) -> bool:
        """Whether audio will be dropped."""
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

class VolumeBuilder:
    """Type-safe builder for FFmpeg volume audio filter.

    Supports linear (float) and dB (string like "3dB") modes, plus
    precision control. Validates volume range 0.0-10.0.
    """

    def __new__(cls, volume: float) -> VolumeBuilder:
        """Creates a new VolumeBuilder with a linear volume value.

        Args:
            volume: Volume multiplier in range [0.0, 10.0].

        Raises:
            ValueError: If volume is outside [0.0, 10.0].
        """
        ...

    @staticmethod
    def from_db(db_str: str) -> VolumeBuilder:
        """Creates a VolumeBuilder from a dB string (e.g., "3dB", "-6dB").

        Args:
            db_str: Volume in dB format.

        Raises:
            ValueError: If the string format is invalid.
        """
        ...

    def precision(self, precision: str) -> VolumeBuilder:
        """Sets the precision mode ("fixed", "float", or "double").

        Args:
            precision: Precision mode.

        Raises:
            ValueError: If precision is not one of the valid values.
        """
        ...

    def build(self) -> Filter:
        """Builds the volume Filter.

        Returns:
            A Filter with the volume syntax.
        """
        ...

    def __repr__(self) -> str: ...

class AfadeBuilder:
    """Type-safe builder for FFmpeg afade audio filter.

    Supports fade in/out with configurable duration, start time, and curve type.
    """

    def __new__(cls, fade_type: str, duration: float) -> AfadeBuilder:
        """Creates a new AfadeBuilder.

        Args:
            fade_type: "in" or "out".
            duration: Fade duration in seconds (must be > 0).

        Raises:
            ValueError: If fade_type is invalid or duration <= 0.
        """
        ...

    def start_time(self, start_time: float) -> AfadeBuilder:
        """Sets the start time for the fade in seconds.

        Args:
            start_time: Start time in seconds.
        """
        ...

    def curve(self, curve: str) -> AfadeBuilder:
        """Sets the fade curve type.

        Valid curves: tri, qsin, hsin, esin, log, ipar, qua, cub, squ, cbr, par.

        Args:
            curve: Curve type name.

        Raises:
            ValueError: If curve name is invalid.
        """
        ...

    def build(self) -> Filter:
        """Builds the afade Filter.

        Returns:
            A Filter with the afade syntax.
        """
        ...

    def __repr__(self) -> str: ...

class AmixBuilder:
    """Type-safe builder for FFmpeg amix audio mixing filter.

    Mixes multiple audio input streams into a single output. Supports
    configurable input count (2-32), duration mode, per-input weights,
    and normalization.
    """

    def __new__(cls, inputs: int) -> AmixBuilder:
        """Creates a new AmixBuilder with the given input count.

        Args:
            inputs: Number of audio inputs (2-32).

        Raises:
            ValueError: If inputs is outside [2, 32].
        """
        ...

    def duration_mode(self, mode: str) -> AmixBuilder:
        """Sets the duration mode ("longest", "shortest", or "first").

        Args:
            mode: Duration mode.

        Raises:
            ValueError: If mode is not one of the valid values.
        """
        ...

    def weights(self, weights: list[float]) -> AmixBuilder:
        """Sets per-input weights as a list of floats.

        Args:
            weights: List of weight values.
        """
        ...

    def normalize(self, normalize: bool) -> AmixBuilder:
        """Sets the normalize flag.

        Args:
            normalize: Whether to normalize the output.
        """
        ...

    def build(self) -> Filter:
        """Builds the amix Filter.

        Returns:
            A Filter with the amix syntax.
        """
        ...

    def __repr__(self) -> str: ...

class DuckingPattern:
    """Builds a ducking pattern that lowers music volume during speech.

    Uses FFmpeg's sidechaincompress filter in a FilterGraph composition.
    """

    def __new__(cls) -> DuckingPattern:
        """Creates a new DuckingPattern with default parameters.

        Defaults: threshold=0.125, ratio=2, attack=20, release=250.
        """
        ...

    def threshold(self, threshold: float) -> DuckingPattern:
        """Sets the detection threshold (0.00097563-1.0).

        Args:
            threshold: Detection threshold.

        Raises:
            ValueError: If threshold is out of range.
        """
        ...

    def ratio(self, ratio: float) -> DuckingPattern:
        """Sets the compression ratio (1-20).

        Args:
            ratio: Compression ratio.

        Raises:
            ValueError: If ratio is out of range.
        """
        ...

    def attack(self, attack: float) -> DuckingPattern:
        """Sets the attack time in milliseconds (0.01-2000).

        Args:
            attack: Attack time in ms.

        Raises:
            ValueError: If attack is out of range.
        """
        ...

    def release(self, release: float) -> DuckingPattern:
        """Sets the release time in milliseconds (0.01-9000).

        Args:
            release: Release time in ms.

        Raises:
            ValueError: If release is out of range.
        """
        ...

    def build(self) -> FilterGraph:
        """Builds the ducking FilterGraph.

        Returns:
            A FilterGraph implementing the ducking pattern.
        """
        ...

    def __repr__(self) -> str: ...

class TransitionType:
    """All FFmpeg xfade transition variants.

    Use class attributes to access specific transition types, or
    ``TransitionType.from_str("wipeleft")`` to parse from a string.
    """

    Fade: TransitionType
    Fadeblack: TransitionType
    Fadewhite: TransitionType
    Fadegrays: TransitionType
    Fadefast: TransitionType
    Fadeslow: TransitionType
    Wipeleft: TransitionType
    Wiperight: TransitionType
    Wipeup: TransitionType
    Wipedown: TransitionType
    Wipetl: TransitionType
    Wipetr: TransitionType
    Wipebl: TransitionType
    Wipebr: TransitionType
    Slideleft: TransitionType
    Slideright: TransitionType
    Slideup: TransitionType
    Slidedown: TransitionType
    Smoothleft: TransitionType
    Smoothright: TransitionType
    Smoothup: TransitionType
    Smoothdown: TransitionType
    Circlecrop: TransitionType
    Rectcrop: TransitionType
    Circleopen: TransitionType
    Circleclose: TransitionType
    Radial: TransitionType
    Vertopen: TransitionType
    Vertclose: TransitionType
    Horzopen: TransitionType
    Horzclose: TransitionType
    Dissolve: TransitionType
    Pixelize: TransitionType
    Distance: TransitionType
    Hblur: TransitionType
    Diagtl: TransitionType
    Diagtr: TransitionType
    Diagbl: TransitionType
    Diagbr: TransitionType
    Hlslice: TransitionType
    Hrslice: TransitionType
    Vuslice: TransitionType
    Vdslice: TransitionType
    Squeezeh: TransitionType
    Squeezev: TransitionType
    Zoomin: TransitionType
    Hlwind: TransitionType
    Hrwind: TransitionType
    Vuwind: TransitionType
    Vdwind: TransitionType
    Coverleft: TransitionType
    Coverright: TransitionType
    Coverup: TransitionType
    Coverdown: TransitionType
    Revealleft: TransitionType
    Revealright: TransitionType
    Revealup: TransitionType
    Revealdown: TransitionType
    Custom: TransitionType

    @staticmethod
    def from_str(name: str) -> TransitionType:
        """Creates a TransitionType from a string name.

        Args:
            name: Transition type name (e.g., "wipeleft", "dissolve").

        Raises:
            ValueError: If the name is not a valid transition type.
        """
        ...

    def as_str(self) -> str:
        """Returns the FFmpeg string representation of this transition type."""
        ...

    def __repr__(self) -> str: ...
    def __str__(self) -> str: ...
    def __eq__(self, other: object) -> bool: ...
    def __hash__(self) -> int: ...

class FadeBuilder:
    """Type-safe builder for FFmpeg fade video filter.

    Supports fade in/out with configurable duration, color, alpha mode,
    start time, and nb_frames alternative.
    """

    def __new__(cls, fade_type: str, duration: float) -> FadeBuilder:
        """Creates a new FadeBuilder.

        Args:
            fade_type: "in" or "out".
            duration: Fade duration in seconds (must be > 0).

        Raises:
            ValueError: If fade_type is invalid or duration <= 0.
        """
        ...

    def start_time(self, start_time: float) -> FadeBuilder:
        """Sets the start time for the fade in seconds.

        Args:
            start_time: Start time in seconds.
        """
        ...

    def color(self, color: str) -> FadeBuilder:
        """Sets the fade color (named colors or hex #RRGGBB).

        Args:
            color: Fade color (e.g., "black", "white", "#FF0000").
        """
        ...

    def alpha(self, alpha: bool) -> FadeBuilder:
        """Enables or disables alpha channel fading.

        Args:
            alpha: Whether to fade the alpha channel.
        """
        ...

    def nb_frames(self, nb_frames: int) -> FadeBuilder:
        """Sets the number of frames for the fade (alternative to duration).

        Args:
            nb_frames: Number of frames.
        """
        ...

    def build(self) -> Filter:
        """Builds the fade Filter.

        Returns:
            A Filter with the fade syntax.
        """
        ...

    def __repr__(self) -> str: ...

class XfadeBuilder:
    """Type-safe builder for FFmpeg xfade video crossfade filter.

    Creates a two-input crossfade with a selectable transition effect.
    Duration is validated in range 0.0-60.0 seconds.
    """

    def __new__(cls, transition: TransitionType, duration: float, offset: float) -> XfadeBuilder:
        """Creates a new XfadeBuilder.

        Args:
            transition: The transition effect to use.
            duration: Transition duration in seconds (0.0-60.0).
            offset: When the transition starts relative to the first input.

        Raises:
            ValueError: If duration is outside [0.0, 60.0].
        """
        ...

    def build(self) -> Filter:
        """Builds the xfade Filter.

        Returns:
            A Filter with the xfade syntax.
        """
        ...

    def __repr__(self) -> str: ...

class AcrossfadeBuilder:
    """Type-safe builder for FFmpeg acrossfade audio crossfade filter.

    Creates a two-input audio crossfade with configurable duration,
    curve types, and overlap toggle.
    """

    def __new__(cls, duration: float) -> AcrossfadeBuilder:
        """Creates a new AcrossfadeBuilder.

        Args:
            duration: Crossfade duration in seconds (> 0 and <= 60.0).

        Raises:
            ValueError: If duration is <= 0 or > 60.0.
        """
        ...

    def curve1(self, curve: str) -> AcrossfadeBuilder:
        """Sets the fade curve for the first input.

        Valid curves: tri, qsin, hsin, esin, log, ipar, qua, cub, squ, cbr, par.

        Args:
            curve: Curve type name.

        Raises:
            ValueError: If curve name is invalid.
        """
        ...

    def curve2(self, curve: str) -> AcrossfadeBuilder:
        """Sets the fade curve for the second input.

        Valid curves: tri, qsin, hsin, esin, log, ipar, qua, cub, squ, cbr, par.

        Args:
            curve: Curve type name.

        Raises:
            ValueError: If curve name is invalid.
        """
        ...

    def overlap(self, overlap: bool) -> AcrossfadeBuilder:
        """Sets the overlap toggle.

        Args:
            overlap: Whether inputs overlap (default: enabled).
        """
        ...

    def build(self) -> Filter:
        """Builds the acrossfade Filter.

        Returns:
            A Filter with the acrossfade syntax.
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

    def validate(self) -> None:
        """Validates the filter graph structure.

        Checks for duplicate output labels, unconnected input pads, and cycles.

        Raises:
            ValueError: If any validation errors are found.
        """
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
