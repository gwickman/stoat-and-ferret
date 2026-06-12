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

class LayoutError(Exception):
    """Raised when layout validation fails.

    This exception is raised when:
    - Coordinate fields (x, y, width, height) are outside the valid 0.0-1.0 range
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
        """Path to the source media file (empty string for generator clips)."""
        ...

    @property
    def clip_type(self) -> str:
        """Clip type: 'file' or 'generator'."""
        ...

    @property
    def generator_params(self) -> str | None:
        """JSON-encoded generator parameters (None for file clips)."""
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

class TrackAudioConfig:
    """Per-track audio configuration for multi-track mixing.

    Specifies volume level and fade durations for a single audio track
    within an AudioMixSpec composition.
    """

    @property
    def volume(self) -> float:
        """Volume multiplier in range [0.0, 2.0]."""
        ...

    @property
    def fade_in(self) -> float:
        """Fade-in duration in seconds (0.0 = no fade)."""
        ...

    @property
    def fade_out(self) -> float:
        """Fade-out duration in seconds (0.0 = no fade)."""
        ...

    def __new__(cls, volume: float, fade_in: float, fade_out: float) -> TrackAudioConfig:
        """Creates a new TrackAudioConfig.

        Args:
            volume: Volume multiplier in range [0.0, 2.0].
            fade_in: Fade-in duration in seconds (>= 0.0).
            fade_out: Fade-out duration in seconds (>= 0.0).

        Raises:
            ValueError: If volume is outside [0.0, 2.0] or fade durations are negative.
        """
        ...

    def __repr__(self) -> str: ...

class AudioMixSpec:
    """Coordinated multi-track audio mixing specification.

    Wraps AmixBuilder, VolumeBuilder, and AfadeBuilder to compose a complete
    filter chain for multi-track audio mixing with per-track volume, fade-in,
    and fade-out.
    """

    def __new__(cls, tracks: list[TrackAudioConfig]) -> AudioMixSpec:
        """Creates a new AudioMixSpec from a list of TrackAudioConfig.

        Args:
            tracks: List of TrackAudioConfig (2-8 tracks).

        Raises:
            ValueError: If track count is outside [2, 8].
        """
        ...

    def build_filter_chain(self) -> str:
        """Builds the filter chain string for multi-track audio mixing.

        Returns:
            A string containing the composed FFmpeg filter chain.
        """
        ...

    def track_count(self) -> int:
        """Returns the number of tracks."""
        ...

    def __repr__(self) -> str: ...

class SubBassBuilder:
    """Type-safe builder for an FFmpeg sub-bass isolation filter chain.

    Extracts the sub-bass frequency band using a ``lowpass`` filter and
    optionally adjusts the output level. Useful for adding a grounding
    low-frequency layer alongside the main mix.

    Examples::

        # 80 Hz crossover, no level change
        chain = SubBassBuilder(80.0).build()

        # 60 Hz crossover, boosted 6 dB
        chain = SubBassBuilder(60.0).with_level_db(6.0).build()
    """

    def __new__(cls, cutoff_hz: float) -> SubBassBuilder:
        """Create a new SubBassBuilder.

        Args:
            cutoff_hz: Lowpass crossover frequency in Hz, range [20.0, 300.0].
                Typical sub-bass crossover: 60–100 Hz.

        Raises:
            ValueError: If cutoff_hz is outside the allowed range.
        """
        ...

    def with_level_db(self, level_db: float) -> SubBassBuilder:
        """Set the output level adjustment in dB.

        Args:
            level_db: Level adjustment in dB, range [-20.0, 20.0].

        Raises:
            ValueError: If level_db is outside the allowed range.
        """
        ...

    def build(self) -> FilterChain:
        """Build the sub-bass FilterChain.

        Returns:
            A FilterChain with ``lowpass=f=<cutoff>`` and optionally a
            ``volume`` filter when level_db is non-zero.
        """
        ...

    @property
    def cutoff_hz(self) -> float:
        """Returns the crossover frequency in Hz."""
        ...

    @property
    def level_db(self) -> float:
        """Returns the level adjustment in dB."""
        ...

    def __repr__(self) -> str: ...

def ducking_effect_schema() -> list[ParameterSchema]:
    """Return the ParameterSchema list for DuckingPattern.

    Exposes ``DuckingPattern`` as a schema-validated registry effect so that
    agents and tooling can discover and validate its parameters without
    constructing an instance.

    Returns:
        A list of four ``ParameterSchema`` entries: threshold, ratio, attack,
        and release — each with type, bounds, description, and AI hint.
    """
    ...

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

# ========== Voice Repair Builders ==========

class NoiseReductionBuilder:
    """Type-safe builder for FFmpeg noise reduction filters.

    Supports two modes:
    - ``"broadband"``: uses ``afftdn`` (adaptive spectral NR) with configurable strength
    - ``"adeclick"``: uses ``adeclick`` (click/impulse removal) with configurable threshold
    """

    def __new__(cls, mode: str) -> NoiseReductionBuilder:
        """Create a new NoiseReductionBuilder.

        Args:
            mode: ``"broadband"`` (afftdn adaptive spectral NR) or
                ``"adeclick"`` (click/impulse removal).

        Raises:
            ValueError: If mode is not ``"broadband"`` or ``"adeclick"``.
        """
        ...

    def strength(self, strength: float) -> NoiseReductionBuilder:
        """Set the noise reduction strength (0.0–1.0). Used in broadband mode.

        Args:
            strength: Strength in range [0.0, 1.0]; maps to afftdn nr=0..97.

        Returns:
            self for method chaining.

        Raises:
            ValueError: If strength is outside [0.0, 1.0].
        """
        ...

    def threshold(self, threshold: float) -> NoiseReductionBuilder:
        """Set the click detection threshold (0.0–1.0). Used in adeclick mode.

        Args:
            threshold: Threshold in range [0.0, 1.0].

        Returns:
            self for method chaining.

        Raises:
            ValueError: If threshold is outside [0.0, 1.0].
        """
        ...

    def build(self) -> Filter:
        """Build the noise reduction Filter.

        Returns:
            A Filter with ``afftdn=nr=<nr>`` (broadband) or ``adeclick`` (adeclick mode).
        """
        ...

    def __repr__(self) -> str: ...

class DeesserBuilder:
    """Type-safe builder for FFmpeg de-esser filter.

    Reduces sibilant energy ("s", "sh") using the FFmpeg ``deesser`` filter.
    Configurable frequency and mode (``"wide"`` or ``"split"``).
    """

    def __new__(cls, frequency: float) -> DeesserBuilder:
        """Create a new DeesserBuilder.

        Args:
            frequency: Sibilance detection frequency in Hz (1000–16000).

        Raises:
            ValueError: If frequency is outside [1000, 16000].
        """
        ...

    def mode(self, mode: str) -> DeesserBuilder:
        """Set the filter mode (``"wide"`` or ``"split"``).

        Args:
            mode: ``"wide"`` (affects full range) or ``"split"`` (splits at frequency).

        Returns:
            self for method chaining.

        Raises:
            ValueError: If mode is not ``"wide"`` or ``"split"``.
        """
        ...

    def build(self) -> Filter:
        """Build the de-esser Filter.

        Returns:
            A Filter with ``deesser=f=<freq>:m=<mode>`` syntax.
        """
        ...

    def __repr__(self) -> str: ...

class DeplosiveBuilder:
    """Type-safe builder for FFmpeg de-plosive filter chain.

    Attenuates low-frequency plosive bursts ("p", "b") using a composite chain:
    ``highpass`` (removes sub-cutoff energy) → ``acompressor`` (controls burst peaks).
    """

    def __new__(cls) -> DeplosiveBuilder:
        """Create a new DeplosiveBuilder with default parameters.

        Defaults: cutoff=60 Hz, threshold=0.1, ratio=4.0.
        """
        ...

    def cutoff(self, cutoff: float) -> DeplosiveBuilder:
        """Set the highpass cutoff frequency in Hz (10–200).

        Args:
            cutoff: Cutoff frequency in Hz in range [10, 200].

        Returns:
            self for method chaining.

        Raises:
            ValueError: If cutoff is outside [10, 200].
        """
        ...

    def threshold(self, threshold: float) -> DeplosiveBuilder:
        """Set the acompressor threshold (0.0–1.0).

        Args:
            threshold: Threshold in range [0.0, 1.0].

        Returns:
            self for method chaining.

        Raises:
            ValueError: If threshold is outside [0.0, 1.0].
        """
        ...

    def ratio(self, ratio: float) -> DeplosiveBuilder:
        """Set the acompressor ratio (1.0–20.0).

        Args:
            ratio: Compression ratio in range [1.0, 20.0].

        Returns:
            self for method chaining.

        Raises:
            ValueError: If ratio is outside [1.0, 20.0].
        """
        ...

    def build(self) -> FilterChain:
        """Build the de-plosive FilterChain.

        Returns:
            A FilterChain with ``highpass=f=<cutoff>,acompressor=...`` stages.
        """
        ...

    def __repr__(self) -> str: ...

class TimeStretchBuilder:
    """Type-safe builder for FFmpeg time-stretch filter chain.

    Adjusts audio playback duration without affecting pitch. Supports three modes:

    - ``"rubberband"``: uses ``rubberband`` filter (high-quality, requires rubberband FFmpeg build)
    - ``"atempo"``: uses chained ``atempo`` filters (always available, chains for factors
      outside [0.5, 2.0])
    - ``"auto"``: probes FFmpeg for rubberband availability at build time, falls back to atempo
    """

    def __new__(cls, factor: float, mode: str) -> TimeStretchBuilder:
        """Create a new TimeStretchBuilder.

        Args:
            factor: Time-stretch factor in range (0.0, 4.0]. Values < 1.0 slow down, > 1.0 speed up.
            mode: Filter mode - ``"rubberband"``, ``"atempo"``, or ``"auto"``.

        Raises:
            ValueError: If factor is out of range or mode is not recognized.
        """
        ...

    @property
    def factor(self) -> float:
        """Returns the stretch factor."""
        ...

    @property
    def mode(self) -> str:
        """Returns the filter mode."""
        ...

    def build(self) -> FilterChain:
        """Build the time-stretch FilterChain.

        Returns:
            A FilterChain with rubberband or chained atempo filters.
        """
        ...

    def __repr__(self) -> str: ...

class PitchShiftBuilder:
    """Type-safe builder for FFmpeg ``arubberband`` pitch-shift filter.

    Shifts voice pitch by a configured number of semitones while optionally
    preserving formants for natural-sounding vocal warmth or correction.

    Requires FFmpeg built with libRubberBand (same dependency as
    ``TimeStretchBuilder`` rubberband mode).

    Examples::

        # Warm the voice up by 2 semitones, preserving formants
        chain = PitchShiftBuilder(2.0).with_formant("preserved").build()

        # Lower pitch by a perfect fifth (7 semitones) with fast processing
        chain = PitchShiftBuilder(-7.0).with_quality("speedy").build()
    """

    def __new__(cls, semitones: float) -> PitchShiftBuilder:
        """Create a new PitchShiftBuilder.

        Args:
            semitones: Pitch shift in semitones, range [-24.0, 24.0].
                Positive values raise pitch, negative values lower it.
                Typical vocal warmth: +1 to +3 semitones.

        Raises:
            ValueError: If semitones is outside the allowed range.
        """
        ...

    def with_formant(self, formant: str) -> PitchShiftBuilder:
        """Set the formant mode.

        Args:
            formant: ``"shifted"`` (default, formants shift with pitch) or
                ``"preserved"`` (formant envelope preserved, more natural).

        Raises:
            ValueError: If formant is not ``"shifted"`` or ``"preserved"``.
        """
        ...

    def with_quality(self, quality: str) -> PitchShiftBuilder:
        """Set the pitch quality mode.

        Args:
            quality: ``"speedy"`` (fastest), ``"consistency"`` (stable across frames),
                or ``"quality"`` (best quality, default).

        Raises:
            ValueError: If quality is not one of the allowed modes.
        """
        ...

    def build(self) -> FilterChain:
        """Build the pitch-shift FilterChain.

        The pitch factor is computed as ``2 ** (semitones / 12)``.

        Returns:
            A FilterChain containing a single ``arubberband`` filter.
        """
        ...

    @property
    def semitones(self) -> float:
        """Returns the pitch shift in semitones."""
        ...

    @property
    def formant(self) -> str:
        """Returns the formant mode."""
        ...

    @property
    def quality(self) -> str:
        """Returns the pitch quality mode."""
        ...

    def __repr__(self) -> str: ...

class Filter:
    """A single FFmpeg filter with optional parameters."""

    def __new__(cls, name: str) -> Filter:
        """Creates a new filter with the given name."""
        ...

    def name(self) -> str:
        """Returns the filter name."""
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

    def filters(self) -> list[Filter]:
        """Returns a list of filters in this chain."""
        ...

    def filter_count(self) -> int:
        """Returns the number of filters in this chain."""
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

    def chains(self) -> list[FilterChain]:
        """Returns a list of chains in this graph."""
        ...

    def chain_count(self) -> int:
        """Returns the number of chains in this graph."""
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

# ========== Automation Types ==========

class CurveKind:
    """Interpolation curve kind for keyframe segments.

    Used as string values in :class:`Keyframe`'s ``curve`` field.
    """

    Hold: str
    Linear: str
    Exponential: str
    EaseInOut: str

class Keyframe:
    """A single keyframe with a time, value, and interpolation curve.

    The ``curve`` field controls how the value is interpolated from this
    keyframe to the next. Use :class:`CurveKind` constants for valid values.
    """

    @property
    def t(self) -> float:
        """Time position of this keyframe (in seconds)."""
        ...

    @property
    def value(self) -> float:
        """Value at this keyframe."""
        ...

    @property
    def curve(self) -> str:
        """Interpolation curve kind (see :class:`CurveKind`)."""
        ...

    def __new__(cls, t: float, value: float, curve: str) -> Keyframe:
        """Creates a new Keyframe.

        Args:
            t: Time position in seconds.
            value: Value at this keyframe.
            curve: Interpolation curve kind string (e.g. ``"Linear"``).
        """
        ...

    def __repr__(self) -> str: ...

class Automation:
    """An automation curve defined by a default value and a list of keyframes.

    When compiled via :func:`compile_automation`, produces an FFmpeg
    ``if(lt(t,...))`` expression tree that evaluates to the interpolated
    value at any time ``t``.
    """

    @property
    def default(self) -> float:
        """Default value used when no keyframes are present."""
        ...

    @property
    def keyframes(self) -> list[Keyframe]:
        """Ordered list of keyframes defining the automation curve."""
        ...

    def __new__(cls, default: float, keyframes: list[Keyframe]) -> Automation:
        """Creates a new Automation.

        Args:
            default: Fallback value when keyframes list is empty.
            keyframes: List of keyframes defining the curve.
        """
        ...

    def __repr__(self) -> str: ...

# ========== Automation Functions ==========

def compile_automation(automation: Automation) -> str:
    """Compile an automation curve into an FFmpeg expression string.

    Converts a keyframe list into a nested ``if(lt(t,...))`` expression
    suitable for use in FFmpeg filter parameters that accept dynamic
    expressions (e.g. ``volume``, ``x``, ``y``).

    Args:
        automation: The automation curve to compile.

    Returns:
        An FFmpeg expression string.

    Raises:
        ValueError: If keyframe times are not strictly increasing.
    """
    ...

# ========== Layout Types ==========

class LayoutPosition:
    """A layout position using normalized coordinates (0.0-1.0).

    All coordinate fields (x, y, width, height) are normalized to the range
    0.0-1.0, representing fractions of the output dimensions. The z_index
    field controls stacking order (higher values are drawn on top).
    """

    @property
    def x(self) -> float:
        """The normalized x coordinate."""
        ...

    @x.setter
    def x(self, value: float) -> None: ...
    @property
    def y(self) -> float:
        """The normalized y coordinate."""
        ...

    @y.setter
    def y(self, value: float) -> None: ...
    @property
    def width(self) -> float:
        """The normalized width."""
        ...

    @width.setter
    def width(self, value: float) -> None: ...
    @property
    def height(self) -> float:
        """The normalized height."""
        ...

    @height.setter
    def height(self, value: float) -> None: ...
    @property
    def z_index(self) -> int:
        """The stacking order index."""
        ...

    @z_index.setter
    def z_index(self, value: int) -> None: ...
    def __new__(
        cls, x: float, y: float, width: float, height: float, z_index: int
    ) -> LayoutPosition:
        """Creates a new LayoutPosition.

        Args:
            x: Normalized x coordinate (0.0-1.0).
            y: Normalized y coordinate (0.0-1.0).
            width: Normalized width (0.0-1.0).
            height: Normalized height (0.0-1.0).
            z_index: Stacking order (higher values drawn on top).

        Returns:
            A new LayoutPosition instance.
        """
        ...

    def to_pixels(self, output_width: int, output_height: int) -> tuple[int, int, int, int]:
        """Converts normalized coordinates to pixel values.

        Returns a tuple of (x, y, width, height) in pixels.

        Args:
            output_width: Output width in pixels.
            output_height: Output height in pixels.

        Returns:
            A tuple of (x, y, width, height) in pixels.
        """
        ...

    def validate(self) -> None:
        """Validates that all coordinates are in the 0.0-1.0 range.

        Raises:
            LayoutError: If any coordinate is out of range.
        """
        ...

    def __repr__(self) -> str: ...

class LayoutPreset:
    """Predefined layout configurations for multi-stream composition.

    Each variant produces a set of LayoutPosition values when
    ``positions()`` is called.

    PIP presets place a full-screen base layer (z_index=0) with a smaller
    overlay in one corner (z_index=1). Tiling presets divide the output
    into non-overlapping regions, all at z_index=0.
    """

    PipTopLeft: LayoutPreset
    PipTopRight: LayoutPreset
    PipBottomLeft: LayoutPreset
    PipBottomRight: LayoutPreset
    SideBySide: LayoutPreset
    TopBottom: LayoutPreset
    Grid2x2: LayoutPreset

    def positions(self, input_count: int) -> list[LayoutPosition]:
        """Returns the layout positions for this preset.

        Args:
            input_count: Number of inputs (reserved for future use).

        Returns:
            A list of LayoutPosition objects defining the composition layout.
        """
        ...

# ========== Composition Functions ==========

def build_overlay_filter(
    position: LayoutPosition,
    output_w: int,
    output_h: int,
    start: float,
    end: float,
) -> str:
    """Builds an FFmpeg overlay filter string from a LayoutPosition.

    Converts normalized coordinates to pixel positions and generates an
    overlay filter with time-based enable expression.

    Args:
        position: Layout position with normalized coordinates (0.0-1.0).
        output_w: Output canvas width in pixels.
        output_h: Output canvas height in pixels.
        start: Start time in seconds for the overlay.
        end: End time in seconds for the overlay.

    Returns:
        FFmpeg overlay filter string.
    """
    ...

def build_scale_for_layout(
    position: LayoutPosition,
    output_w: int,
    output_h: int,
    preserve_aspect: bool,
) -> str:
    """Builds an FFmpeg scale filter string from a LayoutPosition.

    Converts normalized dimensions to pixel values with even-number
    enforcement and optional aspect ratio preservation.

    Args:
        position: Layout position with normalized coordinates (0.0-1.0).
        output_w: Output canvas width in pixels.
        output_h: Output canvas height in pixels.
        preserve_aspect: If true, preserves original aspect ratio.

    Returns:
        FFmpeg scale filter string.
    """
    ...

# ========== Composition Timeline Types ==========

class CompositionClip:
    """A clip positioned on the composition timeline.

    Represents a single input clip with its calculated timeline position,
    track assignment, and z-ordering for multi-layer composition.
    """

    @property
    def input_index(self) -> int:
        """Index of the input source (0-based)."""
        ...

    @property
    def timeline_start(self) -> float:
        """Start time on the composition timeline in seconds."""
        ...

    @property
    def timeline_end(self) -> float:
        """End time on the composition timeline in seconds."""
        ...

    @property
    def track_index(self) -> int:
        """Track index for multi-track layouts."""
        ...

    @property
    def z_index(self) -> int:
        """Z-order for layering (higher = on top)."""
        ...

    def __init__(
        self,
        input_index: int,
        timeline_start: float,
        timeline_end: float,
        track_index: int,
        z_index: int,
    ) -> None:
        """Creates a new CompositionClip.

        Args:
            input_index: Index of the input source (0-based).
            timeline_start: Start time in seconds.
            timeline_end: End time in seconds.
            track_index: Track index for multi-track layouts.
            z_index: Z-order for layering.
        """
        ...

    def duration(self) -> float:
        """Returns the duration of this clip in seconds."""
        ...

class TransitionSpec:
    """Specifies a transition between two adjacent clips.

    The transition duration defines how much the clips overlap on the timeline.
    Duration is clamped during calculation to prevent negative-duration clips.
    """

    transition_type: TransitionType
    duration: float
    offset: float

    def __init__(self, transition_type: TransitionType, duration: float, offset: float) -> None:
        """Creates a new TransitionSpec.

        Args:
            transition_type: The type of transition effect.
            duration: Duration of the transition overlap in seconds.
            offset: Offset adjustment for transition timing.
        """
        ...

def calculate_composition_positions(
    clips: list[CompositionClip],
    transitions: list[TransitionSpec],
) -> list[CompositionClip]:
    """Calculates composition positions for clips with transition overlaps.

    For each adjacent pair of clips, the transition duration creates an overlap.
    Transition durations are clamped to min(clip_n.duration, clip_n+1.duration).

    Args:
        clips: List of CompositionClip objects with input positions.
        transitions: List of TransitionSpec objects for adjacent pairs.

    Returns:
        List of CompositionClip with adjusted timeline positions.
    """
    ...

def calculate_timeline_duration(
    clips: list[CompositionClip],
    transitions: list[TransitionSpec],
) -> float:
    """Calculates total timeline duration accounting for transition overlaps.

    Args:
        clips: List of CompositionClip objects.
        transitions: List of TransitionSpec objects for adjacent pairs.

    Returns:
        Total duration in seconds.
    """
    ...

# ========== Composition Graph Builder ==========

class LayoutSpec:
    """Layout specification for multi-stream composition.

    Contains a list of LayoutPosition values that define where each
    input stream is placed on the output canvas.
    """

    def __init__(self, positions: list[LayoutPosition]) -> None:
        """Creates a new LayoutSpec.

        Args:
            positions: List of LayoutPosition (at least 1 required).

        Raises:
            ValueError: If positions is empty.
        """
        ...

    def positions(self) -> list[LayoutPosition]:
        """Returns the layout positions."""
        ...

    def position_count(self) -> int:
        """Returns the number of positions."""
        ...

    def __repr__(self) -> str: ...

def build_composition_graph(
    clips: list[CompositionClip],
    transitions: list[TransitionSpec],
    layout: LayoutSpec | None,
    audio_mix: AudioMixSpec | None,
    output_width: int,
    output_height: int,
) -> FilterGraph:
    """Builds a complete FilterGraph for multi-clip composition.

    This is the primary composition entry point. Builds either sequential
    (concat/xfade) or spatial (overlay/scale) filter graphs depending on
    whether a layout is provided.

    Args:
        clips: List of CompositionClip objects with timeline positions.
        transitions: List of TransitionSpec for adjacent clip pairs.
        layout: Optional LayoutSpec for spatial composition.
        audio_mix: Optional AudioMixSpec for multi-track audio mixing.
        output_width: Output canvas width in pixels.
        output_height: Output canvas height in pixels.

    Returns:
        A FilterGraph ready for FFmpeg's -filter_complex argument.
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

# ========== Batch Progress Types ==========

class BatchJobStatus:
    """Status of an individual batch render job.

    Use the static factory methods to create instances:
    - BatchJobStatus.pending()
    - BatchJobStatus.in_progress(0.5)
    - BatchJobStatus.completed()
    - BatchJobStatus.failed()
    """

    @staticmethod
    def pending() -> BatchJobStatus:
        """Creates a Pending job status."""
        ...

    @staticmethod
    def in_progress(progress: float) -> BatchJobStatus:
        """Creates an InProgress job status with the given progress (0.0-1.0).

        Args:
            progress: Current progress value between 0.0 and 1.0.
        """
        ...

    @staticmethod
    def completed() -> BatchJobStatus:
        """Creates a Completed job status."""
        ...

    @staticmethod
    def failed() -> BatchJobStatus:
        """Creates a Failed job status."""
        ...

    def progress(self) -> float:
        """Returns the progress value for this status."""
        ...

class BatchProgress:
    """Aggregated progress for a batch of render jobs.

    Reports counts and an overall progress value computed as the mean
    of individual job progress values.
    """

    @property
    def total_jobs(self) -> int:
        """Total number of jobs in the batch."""
        ...

    @property
    def completed_jobs(self) -> int:
        """Number of jobs that completed successfully."""
        ...

    @property
    def failed_jobs(self) -> int:
        """Number of jobs that failed."""
        ...

    @property
    def overall_progress(self) -> float:
        """Overall progress as mean of individual job progress values (0.0-1.0)."""
        ...

    def __init__(
        self,
        total_jobs: int,
        completed_jobs: int,
        failed_jobs: int,
        overall_progress: float,
    ) -> None:
        """Creates a new BatchProgress.

        Args:
            total_jobs: Total number of jobs.
            completed_jobs: Number of completed jobs.
            failed_jobs: Number of failed jobs.
            overall_progress: Overall progress (0.0-1.0).
        """
        ...

def calculate_batch_progress(jobs: list[BatchJobStatus]) -> BatchProgress:
    """Calculates aggregated batch progress from individual job statuses.

    The overall progress is the mean of individual job progress values:
    - Pending: 0.0
    - InProgress(p): p (clamped to [0.0, 1.0])
    - Completed: 1.0
    - Failed: 0.0

    Args:
        jobs: List of BatchJobStatus objects representing individual job states.

    Returns:
        BatchProgress with total_jobs, completed_jobs, failed_jobs, and overall_progress.
    """
    ...

# ========== Preview Types ==========

class PreviewQuality:
    """Preview quality level for filter simplification.

    Controls how aggressively filters are simplified for preview playback.
    """

    Draft: PreviewQuality
    Medium: PreviewQuality
    High: PreviewQuality

# ========== Preview Functions ==========

def is_expensive_filter(name: str) -> bool:
    """Returns true if the filter name is classified as expensive.

    Expensive filters are those with high computational cost that can be
    safely removed during preview without affecting structural correctness.

    Args:
        name: The FFmpeg filter name to check.

    Returns:
        True if the filter is expensive, False otherwise.
    """
    ...

def simplify_filter_chain(chain: FilterChain, quality: PreviewQuality) -> FilterChain:
    """Simplifies a filter chain by removing expensive filters based on quality.

    Args:
        chain: The filter chain to simplify.
        quality: The preview quality level.

    Returns:
        A simplified filter chain.
    """
    ...

def simplify_filter_graph(graph: FilterGraph, quality: PreviewQuality) -> FilterGraph:
    """Simplifies a filter graph by simplifying each chain based on quality.

    Args:
        graph: The filter graph to simplify.
        quality: The preview quality level.

    Returns:
        A simplified filter graph.
    """
    ...

def estimate_filter_cost(graph: FilterGraph) -> float:
    """Estimates the computational cost of a filter graph as a score in [0.0, 1.0].

    Uses weighted filter counts normalized via sigmoid. Expensive filters
    contribute more to the score. Empty graphs return 0.0.

    Args:
        graph: The filter graph to estimate cost for.

    Returns:
        A cost score between 0.0 and 1.0 inclusive.
    """
    ...

def select_preview_quality(cost: float) -> PreviewQuality:
    """Selects preview quality based on estimated cost score.

    - Cost > 0.7: Draft (fastest preview)
    - Cost 0.3-0.7: Medium (balanced)
    - Cost < 0.3: High (full quality)

    Args:
        cost: A cost score in [0.0, 1.0].

    Returns:
        The recommended PreviewQuality level.
    """
    ...

def inject_preview_scale(graph: FilterGraph, width: int, height: int) -> FilterGraph:
    """Appends a scale filter with the given dimensions to the filter graph.

    The scale filter is added as a new chain at the end of the graph.

    Args:
        graph: The filter graph to inject scale into.
        width: Target width in pixels.
        height: Target height in pixels.

    Returns:
        A new FilterGraph with the scale filter appended.
    """
    ...

# ========== Render Plan Types ==========

class RenderSettings:
    """Settings controlling how a render is executed.

    Contains the output format, resolution, codec, quality preset, and frame rate.
    """

    @property
    def output_format(self) -> str:
        """Output container format (e.g., "mp4", "mkv")."""
        ...

    @property
    def width(self) -> int:
        """Output width in pixels."""
        ...

    @property
    def height(self) -> int:
        """Output height in pixels."""
        ...

    @property
    def codec(self) -> str:
        """Video codec (e.g., "libx264", "libx265")."""
        ...

    @property
    def quality_preset(self) -> str:
        """Quality preset (e.g., "fast", "medium", "slow")."""
        ...

    @property
    def fps(self) -> float:
        """Frames per second for the output."""
        ...

    @property
    def audio_sample_rate(self) -> int | None:
        """Audio sample rate in Hz (e.g., 44100, 48000, 96000). None if not set."""
        ...

    @property
    def audio_bit_depth(self) -> int | None:
        """Audio bit depth (e.g., 16, 24, 32). None if not set."""
        ...

    def __init__(
        self,
        output_format: str,
        width: int,
        height: int,
        codec: str,
        quality_preset: str,
        fps: float,
        audio_sample_rate: int | None = None,
        audio_bit_depth: int | None = None,
    ) -> None:
        """Creates a new RenderSettings.

        Args:
            output_format: Container format (e.g., "mp4").
            width: Output width in pixels.
            height: Output height in pixels.
            codec: Video codec (e.g., "libx264").
            quality_preset: Encoding preset (e.g., "medium").
            fps: Output frame rate.
            audio_sample_rate: Audio sample rate in Hz (optional).
            audio_bit_depth: Audio bit depth (optional).
        """
        ...

    def with_audio(self, sample_rate: int, bit_depth: int) -> RenderSettings:
        """Returns a copy with audio parameters set.

        Args:
            sample_rate: Audio sample rate in Hz.
            bit_depth: Audio bit depth.

        Returns:
            A new RenderSettings with audio fields set.
        """
        ...

class RenderSegment:
    """A single non-overlapping segment of the render timeline.

    Segments partition the full timeline so their durations sum to the
    total render duration with no gaps or overlaps.
    """

    @property
    def index(self) -> int:
        """Zero-based segment index."""
        ...

    @property
    def timeline_start(self) -> float:
        """Start time on the composition timeline in seconds."""
        ...

    @property
    def timeline_end(self) -> float:
        """End time on the composition timeline in seconds."""
        ...

    @property
    def frame_count(self) -> int:
        """Number of frames in this segment."""
        ...

    @property
    def cost_estimate(self) -> float:
        """Estimated cost (proportional to frame count x active clip count)."""
        ...

    def __init__(
        self,
        index: int,
        timeline_start: float,
        timeline_end: float,
        frame_count: int,
        cost_estimate: float,
    ) -> None:
        """Creates a new RenderSegment.

        Args:
            index: Zero-based segment index.
            timeline_start: Start time in seconds.
            timeline_end: End time in seconds.
            frame_count: Number of frames in this segment.
            cost_estimate: Estimated rendering cost.
        """
        ...

    def duration(self) -> float:
        """Returns the duration of this segment in seconds."""
        ...

class RenderPlan:
    """A complete render plan decomposed from composition data.

    Contains ordered, non-overlapping segments covering the full timeline
    duration, along with aggregate totals and the render settings.
    """

    @property
    def total_frames(self) -> int:
        """Total frame count across all segments."""
        ...

    @property
    def total_duration(self) -> float:
        """Total timeline duration in seconds."""
        ...

    def __init__(
        self,
        segments: list[RenderSegment],
        total_frames: int,
        total_duration: float,
        settings: RenderSettings,
    ) -> None:
        """Creates a new RenderPlan.

        Args:
            segments: Ordered list of RenderSegment.
            total_frames: Total frame count.
            total_duration: Total duration in seconds.
            settings: Render settings.
        """
        ...

    def segments(self) -> list[RenderSegment]:
        """Returns the list of segments."""
        ...

    def settings(self) -> RenderSettings:
        """Returns the render settings."""
        ...

    def segment_count(self) -> int:
        """Returns the number of segments."""
        ...

    def total_cost(self) -> float:
        """Returns the total estimated cost."""
        ...

# ========== Render Plan Functions ==========

def build_render_plan(
    clips: list[CompositionClip],
    transitions: list[TransitionSpec],
    layout: LayoutSpec | None,
    audio_mix: AudioMixSpec | None,
    output_width: int,
    output_height: int,
    settings: RenderSettings,
) -> RenderPlan:
    """Builds a render plan from composition data.

    Decomposes the timeline into ordered segments with frame counts and cost
    estimates. Uses composition timeline logic for transition clamping.

    Args:
        clips: List of CompositionClip with timeline positions.
        transitions: List of TransitionSpec for adjacent clip pairs.
        layout: Optional LayoutSpec for spatial composition.
        audio_mix: Optional AudioMixSpec for audio mixing.
        output_width: Output width in pixels.
        output_height: Output height in pixels.
        settings: RenderSettings controlling format, resolution, codec, fps.

    Returns:
        A RenderPlan with segments, total_frames, total_duration, and settings.
    """
    ...

def validate_render_settings(settings: RenderSettings) -> None:
    """Validates render settings before execution.

    Checks output format, resolution, codec, quality preset, and fps.

    Args:
        settings: RenderSettings to validate.

    Raises:
        ValueError: If any setting is invalid, with a descriptive message.
    """
    ...

# ========== Encoder Detection Types ==========

class EncoderType:
    """Type of hardware acceleration used by an encoder.

    Use class attributes to access specific encoder types.
    """

    Software: EncoderType
    Nvenc: EncoderType
    Qsv: EncoderType
    Vaapi: EncoderType
    Amf: EncoderType
    Mf: EncoderType

    def __eq__(self, other: object) -> bool: ...
    def __hash__(self) -> int: ...

class QualityPreset:
    """Quality preset for encoding output.

    Maps to encoder-specific parameters (CRF, CQ, QP, etc.) rather than
    FFmpeg's built-in preset names.
    """

    Draft: QualityPreset
    Standard: QualityPreset
    High: QualityPreset

    def __eq__(self, other: object) -> bool: ...
    def __hash__(self) -> int: ...

class EncoderInfo:
    """Information about a detected video encoder.

    Contains the encoder name, codec, hardware classification, and description
    as parsed from FFmpeg ``-encoders`` output.
    """

    @property
    def name(self) -> str:
        """Encoder name as reported by FFmpeg (e.g., "h264_nvenc", "libx264")."""
        ...

    @property
    def codec(self) -> str:
        """Codec identifier (e.g., "h264", "hevc", "av1")."""
        ...

    @property
    def is_hardware(self) -> bool:
        """Whether this is a hardware-accelerated encoder."""
        ...

    @property
    def encoder_type(self) -> EncoderType:
        """Type of hardware acceleration."""
        ...

    @property
    def description(self) -> str:
        """Encoder description from FFmpeg output."""
        ...

    def __new__(
        cls,
        name: str,
        codec: str,
        is_hardware: bool,
        encoder_type: EncoderType,
        description: str,
    ) -> EncoderInfo:
        """Creates a new EncoderInfo.

        Args:
            name: Encoder name (e.g., "h264_nvenc").
            codec: Codec identifier (e.g., "h264").
            is_hardware: Whether this is hardware-accelerated.
            encoder_type: Type of hardware acceleration.
            description: Encoder description.
        """
        ...

    def __repr__(self) -> str: ...

# ========== Encoder Detection Functions ==========

def detect_hardware_encoders(ffmpeg_output: str) -> list[EncoderInfo]:
    """Detects available video encoders by parsing FFmpeg ``-encoders`` output.

    Parses each line, filters to video encoders only, and classifies each
    as hardware or software based on the ``{codec}_{platform}`` naming pattern.

    Args:
        ffmpeg_output: Complete output from ``ffmpeg -encoders``.

    Returns:
        List of detected video encoders with classification.
    """
    ...

def select_encoder(available: list[EncoderInfo], codec: str) -> EncoderInfo:
    """Selects the best encoder for a codec from available encoders.

    Follows the fallback chain: nvenc -> qsv -> vaapi -> amf -> mf -> software.
    Always returns a valid encoder; synthesises a default software encoder
    if no matching encoder is found in the available list.

    Args:
        available: List of detected encoders.
        codec: Target codec (e.g., "h264", "hevc").

    Returns:
        The best available encoder for the requested codec.
    """
    ...

def build_encoding_args(encoder: EncoderInfo, quality: QualityPreset) -> list[str]:
    """Builds FFmpeg encoding arguments for an encoder and quality preset.

    Returns a list of FFmpeg command-line arguments appropriate for the
    encoder type and quality level (codec flag, quality params, preset).

    Args:
        encoder: The encoder to build arguments for.
        quality: The target quality preset.

    Returns:
        List of FFmpeg CLI argument strings.
    """
    ...

# ========== Render Command Builder Types ==========

class RenderCommand:
    """A complete FFmpeg render command for a single segment.

    Contains the argument list, output path, and segment index for tracking.
    """

    def __init__(
        self,
        args: list[str],
        output_path: str,
        segment_index: int,
    ) -> None:
        """Creates a new RenderCommand.

        Args:
            args: FFmpeg argument list.
            output_path: Output file path.
            segment_index: Zero-based segment index.
        """
        ...

    def args(self) -> list[str]:
        """Returns the FFmpeg argument list."""
        ...

    @property
    def output_path(self) -> str:
        """Output file path for this segment."""
        ...

    @property
    def segment_index(self) -> int:
        """Zero-based segment index this command renders."""
        ...

class ConcatCommand:
    """Result of a concat demuxer command build.

    Contains the FFmpeg argument list and the concat file content.
    """

    def __init__(
        self,
        args: list[str],
        concat_file_content: str,
    ) -> None:
        """Creates a new ConcatCommand.

        Args:
            args: FFmpeg argument list.
            concat_file_content: Concat demuxer file content.
        """
        ...

    def args(self) -> list[str]:
        """Returns the FFmpeg argument list."""
        ...

    @property
    def concat_file_content(self) -> str:
        """Content of the concat demuxer file."""
        ...

# ========== Render Command Builder Functions ==========

def build_render_command(
    segment: RenderSegment,
    encoder: EncoderInfo,
    quality: QualityPreset,
    settings: RenderSettings,
    input_path: str,
    output_path: str,
    ffmetadata_path: str | None = None,
) -> RenderCommand:
    """Builds a complete FFmpeg render command for a single segment.

    The command includes input file, seek position, duration,
    encoder-specific arguments, output format, and progress reporting flags.

    Args:
        segment: The render segment to build a command for.
        encoder: The selected encoder.
        quality: The quality preset.
        settings: Render settings (format, resolution, fps).
        input_path: Path to the input media file.
        output_path: Path to write the rendered segment output.

    Returns:
        A RenderCommand with the complete argument list.
    """
    ...

def build_concat_command(
    segment_outputs: list[str],
    final_output: str,
    concat_file_path: str,
) -> ConcatCommand:
    """Builds an FFmpeg concat demuxer command for joining multiple segments.

    Generates ``ffconcat version 1.0`` file content listing all segment
    files with forward slashes and ``safe=0`` for absolute path support.

    Args:
        segment_outputs: List of segment output file paths.
        final_output: Path for the final concatenated output.
        concat_file_path: Path where the concat list file will be written.

    Returns:
        A ConcatCommand with the argument list and file content.
    """
    ...

def check_output_conflict(output_path: str) -> bool:
    """Checks whether a file already exists at the given output path.

    Args:
        output_path: Path to check for an existing file.

    Returns:
        True if a file exists at the path, False otherwise.
    """
    ...

def estimate_output_size(
    duration_seconds: float,
    codec: str,
    quality_preset: str,
) -> int:
    """Estimates the output file size in bytes.

    Uses a hardcoded bitrate lookup table keyed by (codec, quality_preset)
    with a 20% safety margin for overestimation.

    Formula: ``duration_seconds * bitrate_bps / 8 * 1.2``

    Args:
        duration_seconds: Total render duration in seconds.
        codec: Video codec string (e.g., "libx264").
        quality_preset: Quality preset string ("draft", "standard", "high").

    Returns:
        Estimated file size in bytes.
    """
    ...

def build_generator_source_filter(params_json: str, duration: float) -> str:
    """Build an FFmpeg source filter string for a generator clip.

    Supported types in params_json:
    - ``"sine"``: Simple sine wave. Requires ``frequency`` (Hz).
    - ``"aevalsrc"``: Arbitrary expression evaluator. Requires ``expr``.
      Optional ``duration`` overrides the clip duration.
    - ``"tone"``: Entrainment tone with optional frequency sweep and binaural
      beat mode. Requires ``frequency`` (Hz). Optional fields:
      ``frequency_end`` (Hz) — sweeps from ``frequency`` to ``frequency_end``
      using a linear chirp; ``binaural_offset`` (Hz) — adds a right-channel
      copy offset by this amount to produce a binaural beat at that frequency.

    Args:
        params_json: JSON string with generator parameters including a 'type' field.
        duration: Clip duration in seconds.

    Returns:
        FFmpeg source filter expression string.

    Raises:
        ValueError: If params_json is invalid, 'type' is missing, a required
            field for the chosen type is absent, or the type is unknown.
    """
    ...

def build_generator_render_command(
    params_json: str, duration: float, output_path: str
) -> RenderCommand:
    """Build a complete FFmpeg render command for a generator clip.

    Args:
        params_json: JSON string with generator parameters including a 'type' field.
        duration: Clip duration in seconds.
        output_path: Path to write the rendered output.

    Returns:
        A RenderCommand with the complete argument list.
    """
    ...

def build_loop_render_command(
    input_path: str,
    target_duration: float,
    output_path: str,
    crossfade_duration: float = 0.0,
    loop_start: float = 0.0,
) -> RenderCommand:
    """Build an FFmpeg render command to loop a short audio bed to a target duration.

    Uses ``-stream_loop -1`` to repeat the input, trimmed to ``target_duration``.
    An optional ``crossfade_duration`` applies fade-in/out around each loop boundary
    to reduce the audible seam. ``loop_start`` shifts the loop boundary within the
    source file (useful for reshaping the loop point to a zero crossing).

    Args:
        input_path: Path to the source audio file to loop.
        target_duration: Desired output duration in seconds.
        output_path: Path to write the looped output.
        crossfade_duration: Seconds of fade-in/out at each loop boundary (0 = disabled).
        loop_start: Seek offset into the source file before looping (seconds).

    Returns:
        A RenderCommand with the complete argument list.
    """
    ...

# ========== Progress Tracking Types ==========

class FfmpegProgressUpdate:
    """A single progress update parsed from FFmpeg ``-progress pipe:1`` output.

    Each block of key=value lines terminated by ``progress=continue`` or
    ``progress=end`` produces one update. Fields that FFmpeg omits (e.g.,
    ``frame``/``fps`` for audio-only streams) are ``None``.
    """

    @property
    def frame(self) -> int | None:
        """Frame number reached (None for audio-only streams)."""
        ...

    @property
    def fps(self) -> float | None:
        """Current encoding speed in fps (None for audio-only streams)."""
        ...

    @property
    def out_time_us(self) -> int:
        """Output time in microseconds (primary progress metric)."""
        ...

    @property
    def bitrate(self) -> str:
        """Current bitrate string (e.g., '1234.5kbits/s' or 'N/A')."""
        ...

    @property
    def speed(self) -> str:
        """Encoding speed multiplier string (e.g., '1.5x' or 'N/A')."""
        ...

    @property
    def progress_end(self) -> bool:
        """True when this is the final progress block."""
        ...

class ProgressInfo:
    """Calculated progress information for a render job.

    Combines the raw completion ratio with optional ETA and frame counts.
    """

    def __init__(
        self,
        progress: float,
        eta_seconds: float | None = None,
        frames_done: int | None = None,
        total_frames: int | None = None,
    ) -> None:
        """Creates a new ProgressInfo.

        Args:
            progress: Completion ratio clamped to [0.0, 1.0].
            eta_seconds: Estimated seconds remaining, or None.
            frames_done: Frames encoded so far, or None.
            total_frames: Total frames expected, or None.
        """
        ...

    @property
    def progress(self) -> float:
        """Completion ratio clamped to [0.0, 1.0]."""
        ...

    @property
    def eta_seconds(self) -> float | None:
        """Estimated seconds remaining, or None if progress is zero."""
        ...

    @property
    def frames_done(self) -> int | None:
        """Frames encoded so far (None if unknown)."""
        ...

    @property
    def total_frames(self) -> int | None:
        """Total frames expected (None if unknown)."""
        ...

# ========== Progress Tracking Functions ==========

def parse_ffmpeg_progress(output: str) -> list[FfmpegProgressUpdate]:
    """Parses FFmpeg ``-progress pipe:1`` output into progress updates.

    Each block of key=value lines terminated by ``progress=continue`` or
    ``progress=end`` produces one update. Handles the documented deviation
    where ``out_time_ms`` actually reports microseconds.

    Args:
        output: Complete or partial FFmpeg progress output.

    Returns:
        List of parsed progress updates.
    """
    ...

def calculate_progress(current_time_us: int, total_duration_us: int) -> float:
    """Calculates render progress as a ratio in [0.0, 1.0].

    Returns 0.0 when total_duration_us is zero or negative.

    Args:
        current_time_us: Current output time in microseconds.
        total_duration_us: Total expected duration in microseconds.

    Returns:
        Progress ratio clamped to [0.0, 1.0].
    """
    ...

def estimate_eta(elapsed_seconds: float, progress: float) -> float | None:
    """Estimates remaining time in seconds.

    Formula: eta = (elapsed / progress) * (1 - progress).
    Returns None when progress is zero or >= 1.0.

    Args:
        elapsed_seconds: Time elapsed so far in seconds.
        progress: Current progress ratio (0.0 to 1.0).

    Returns:
        Estimated seconds remaining, or None.
    """
    ...

def aggregate_segment_progress(segments: list[tuple[float, float]]) -> float:
    """Aggregates per-segment progress into an overall progress ratio.

    Each tuple is (segment_progress, segment_duration). Segments are
    weighted by their proportion of the total duration.

    Args:
        segments: List of (progress, duration) tuples.

    Returns:
        Weighted aggregate progress clamped to [0.0, 1.0].
    """
    ...

# ========== Parameter Schema ==========

class ParameterSchema:
    """Structured parameter metadata for a single effect parameter.

    Fields mirror the JSON Schema-style descriptors emitted by the Python
    effect registry, with normalised ``param_type`` values and an AI hint
    sourced from the per-effect ``ai_hints`` dict. All bound and enum
    fields are optional.
    """

    @property
    def name(self) -> str:
        """Parameter name (key in the JSON Schema ``properties`` dict)."""
        ...

    @property
    def param_type(self) -> str:
        """Normalised type: ``int``, ``float``, ``string``, ``bool``, ``enum``, or ``array``."""
        ...

    @property
    def default_value(self) -> int | float | str | bool | None:
        """Default value from the schema, or ``None`` when omitted."""
        ...

    @property
    def min_value(self) -> float | None:
        """Lower numeric bound from JSON Schema ``minimum``."""
        ...

    @property
    def max_value(self) -> float | None:
        """Upper numeric bound from JSON Schema ``maximum``."""
        ...

    @property
    def enum_values(self) -> list[str] | None:
        """Allowed string values when the parameter is an enum."""
        ...

    @property
    def description(self) -> str:
        """Human-readable description from JSON Schema ``description``."""
        ...

    @property
    def ai_hint(self) -> str:
        """AI-oriented natural-language hint for this parameter."""
        ...

    def __repr__(self) -> str: ...

def parameter_schemas_from_dict(
    schema: dict[str, object],
    ai_hints: dict[str, str],
) -> list[ParameterSchema]:
    """Translate a JSON Schema parameter dict into a list of ParameterSchema.

    Iterates ``schema["properties"]`` and extracts a structured record for
    each property. Returns an empty list when ``schema`` has no
    ``properties`` key.

    Args:
        schema: JSON Schema-style dict (e.g. ``{"properties": {"x": {...}}}``).
        ai_hints: Map of parameter name -> AI hint string.

    Returns:
        List of :class:`ParameterSchema` objects, one per property.
    """
    ...

# ========== Version Metadata ==========

class VersionInfo:
    """Build-time deployment metadata captured at compile time.

    Populated by ``build.rs``:

    - ``core_version`` is the crate version from ``Cargo.toml``.
    - ``build_timestamp`` is an ISO 8601 UTC timestamp.
    - ``git_sha`` is the short git SHA of HEAD, or the literal ``"unknown"``
      when neither the ``GIT_SHA`` env var nor ``git rev-parse`` could
      resolve a value at build time.

    Instantiate via :meth:`VersionInfo.current`.
    """

    @property
    def core_version(self) -> str:
        """Semver version from Cargo.toml (``CARGO_PKG_VERSION``)."""
        ...

    @property
    def build_timestamp(self) -> str:
        """ISO 8601 UTC timestamp captured at build time."""
        ...

    @property
    def git_sha(self) -> str:
        """Short git SHA of HEAD, or ``"unknown"`` when unavailable."""
        ...

    @staticmethod
    def current() -> VersionInfo:
        """Return a :class:`VersionInfo` populated from the build metadata."""
        ...

# ========== QC Parser Types ==========

class LoudnessReport:
    """Loudness measurements parsed from ebur128/loudnorm JSON output."""

    def __new__(
        cls,
        integrated_lufs: float,
        lra: float,
        true_peak_dbtp: float,
    ) -> LoudnessReport:
        """Creates a new LoudnessReport."""
        ...

    @property
    def integrated_lufs(self) -> float:
        """Integrated loudness in LUFS."""
        ...

    @property
    def lra(self) -> float:
        """Loudness range in LU."""
        ...

    @property
    def true_peak_dbtp(self) -> float:
        """True peak in dBTP."""
        ...

    def __repr__(self) -> str: ...

class PeakReport:
    """Peak/clipping measurements parsed from astats/volumedetect output."""

    def __new__(cls, peak_level: float, clipped_samples: int) -> PeakReport:
        """Creates a new PeakReport."""
        ...

    @property
    def peak_level(self) -> float:
        """Peak level in dB."""
        ...

    @property
    def clipped_samples(self) -> int:
        """Number of clipped samples."""
        ...

    def __repr__(self) -> str: ...

class SilenceRegion:
    """A single silence region with start and end times in seconds."""

    def __new__(cls, start: float, end: float) -> SilenceRegion:
        """Creates a new SilenceRegion."""
        ...

    @property
    def start(self) -> float:
        """Start of silence in seconds."""
        ...

    @property
    def end(self) -> float:
        """End of silence in seconds."""
        ...

    def __repr__(self) -> str: ...

class SilenceReport:
    """Silence analysis result containing all detected silence regions."""

    def __new__(cls, regions: list[SilenceRegion]) -> SilenceReport:
        """Creates a new SilenceReport."""
        ...

    @property
    def regions(self) -> list[SilenceRegion]:
        """Returns the list of silence regions."""
        ...

    def __repr__(self) -> str: ...

class SpectralReport:
    """Per-channel spectral statistics parsed from aspectralstats output."""

    def __new__(cls, channel_count: int, channel_means: list[float]) -> SpectralReport:
        """Creates a new SpectralReport."""
        ...

    @property
    def channel_count(self) -> int:
        """Number of channels detected."""
        ...

    @property
    def channel_means(self) -> list[float]:
        """Mean spectral energy per channel."""
        ...

    def __repr__(self) -> str: ...

class Region:
    """A detected time region with start and end times in seconds."""

    def __new__(cls, start: float, end: float) -> Region:
        """Creates a new Region."""
        ...

    @property
    def start(self) -> float:
        """Start of region in seconds."""
        ...

    @property
    def end(self) -> float:
        """End of region in seconds."""
        ...

    def __repr__(self) -> str: ...

class VideoDefectReport:
    """Video defect analysis result with black and freeze regions."""

    def __new__(
        cls, black_regions: list[Region], freeze_regions: list[Region]
    ) -> VideoDefectReport:
        """Creates a new VideoDefectReport."""
        ...

    @property
    def black_regions(self) -> list[Region]:
        """Returns the list of black detection regions."""
        ...

    @property
    def freeze_regions(self) -> list[Region]:
        """Returns the list of freeze detection regions."""
        ...

    def __repr__(self) -> str: ...

# ========== QC Parser Functions ==========

def parse_loudness_report(output: str) -> LoudnessReport:
    """Parse ebur128/loudnorm JSON output into a LoudnessReport.

    Accepts both ``input_i`` (FFmpeg >=5.x) and ``integrated_loudness``
    (FFmpeg <=4.x) field names. JSON values may be quoted strings or bare floats.

    Raises ValueError on missing required fields.
    """
    ...

def parse_peak_report(output: str) -> PeakReport:
    """Parse astats/volumedetect text output into a PeakReport.

    For astats: uses the "Overall" section, ignoring per-channel blocks.
    For volumedetect: uses max_volume and histogram_0db fields.

    Raises ValueError if no peak level field is found.
    """
    ...

def parse_silence_report(output: str) -> SilenceReport:
    """Parse silencedetect text output into a SilenceReport.

    Pairs ``silence_start`` and ``silence_end`` lines in order. A trailing
    start without a matching end gets end=float('inf').

    Never raises; returns an empty SilenceReport on empty/garbled input.
    """
    ...

def parse_spectral_report(output: str) -> SpectralReport:
    """Parse aspectralstats lavfi key=value output into a SpectralReport.

    Extracts ``lavfi.aspectralstats.{channel}.mean`` values per channel.
    Channels are ordered by number (BTreeMap).

    Raises ValueError if no channel mean data is found.
    """
    ...

def parse_video_defect_report(output: str) -> VideoDefectReport:
    """Parse blackdetect and freezedetect output into a VideoDefectReport.

    blackdetect lines: ``black_start:X black_end:Y black_duration:Z``.
    freezedetect lines: ``lavfi.freezedetect.freeze_start: X`` / ``freeze_end: X``.

    Never raises; returns empty lists on empty/garbled input.
    """
    ...

# ========== Mastering Builders ==========

class LimiterBuilder:
    """Type-safe builder for FFmpeg ``alimiter`` true-peak limiter.

    Converts ``ceiling_dbtp`` (a non-positive dBTP value) to a linear ratio for the
    ``alimiter`` ``limit`` parameter: ``limit = 10^(ceiling_dbtp / 20)``.

    Example: −1 dBTP → limit=0.891251 (verified at interface-contracts.md §3).
    """

    def __new__(cls, ceiling_dbtp: float) -> LimiterBuilder:
        """Create a new LimiterBuilder.

        Args:
            ceiling_dbtp: Ceiling in dBTP. Must be <= 0.0; positive values would permit
                          gain above 0 dBFS which is non-sensical for a true-peak ceiling.

        Raises:
            ValueError: If ceiling_dbtp > 0.0.
        """
        ...

    @property
    def ceiling_dbtp(self) -> float:
        """Returns the ceiling in dBTP."""
        ...

    def build(self) -> Filter:
        """Build the alimiter Filter.

        Returns:
            A Filter with ``alimiter=limit=<ratio>:level=disabled`` syntax.
        """
        ...

    def __repr__(self) -> str: ...

class LoudnormBuilder:
    """Type-safe builder for FFmpeg ``loudnorm`` two-pass LUFS normalization.

    Pass-1 filter (``build_pass1``): emits ``loudnorm=I=...:TP=...:LRA=...:print_format=json``
    so FFmpeg writes measurement JSON to stderr.

    Pass-2 filter (``build_pass2``): emits the linear normalization filter using the
    measurements from :class:`LoudnormPassOneResult`.

    Default LRA is 11.0 LU (EBU R128 recommendation).
    """

    def __new__(
        cls,
        target_lufs: float,
        ceiling_dbtp: float,
        lra: float,
    ) -> LoudnormBuilder:
        """Creates a new LoudnormBuilder.

        Args:
            target_lufs: Target integrated loudness in LUFS (e.g. -16.0 for podcasts,
                         -14.0 for streaming).
            ceiling_dbtp: True-peak ceiling in dBTP (must be <= 0.0).
            lra: Loudness range target in LU (default 11.0, EBU R128 recommendation).

        Raises:
            ValueError: If ceiling_dbtp > 0.0.
        """
        ...

    @property
    def target_lufs(self) -> float:
        """Target integrated loudness in LUFS."""
        ...

    @property
    def ceiling_dbtp(self) -> float:
        """True-peak ceiling in dBTP."""
        ...

    @property
    def lra(self) -> float:
        """Loudness range target in LU."""
        ...

    def build_pass1(self) -> Filter:
        """Build the pass-1 loudnorm filter (measurement pass).

        Returns:
            A Filter with ``loudnorm=I=...:TP=...:LRA=...:print_format=json`` syntax.
        """
        ...

    def build_pass2(
        self,
        measured_i: float,
        measured_lra: float,
        measured_tp: float,
        offset: float,
    ) -> Filter:
        """Build the pass-2 loudnorm filter using pass-1 measurements.

        Args:
            measured_i: Measured integrated loudness from pass-1 (LUFS).
            measured_lra: Measured loudness range from pass-1 (LU).
            measured_tp: Measured true-peak from pass-1 (dBTP).
            offset: Gain offset from pass-1.

        Returns:
            A Filter with linear normalization syntax.
        """
        ...

    def __repr__(self) -> str: ...

class ParametricEqBuilder:
    """Type-safe builder for FFmpeg ``anequalizer`` parametric equalizer filter.

    Generates pipe-separated band specifications:
    ``anequalizer=c0 f={hz} w={width} g={gain_db} t=1|c1 f={hz} w={width} g={gain_db} t=1|...``
    """

    def __new__(cls, bands: list[dict[str, float]]) -> ParametricEqBuilder:
        """Create a new ParametricEqBuilder.

        Args:
            bands: List of band dicts, each with required keys:
                - ``frequency`` (float): Band center frequency in Hz (20–20000).
                - ``gain`` (float): Band gain in dB (−24 to +24).
                - ``width`` (float): Band width in Hz (> 0).

        Raises:
            ValueError: If bands is empty, any frequency is outside 20–20000 Hz,
                any gain is outside ±24 dB, or any width is <= 0.
        """
        ...

    def build(self) -> Filter:
        """Build the anequalizer Filter.

        Returns:
            A Filter with ``anequalizer=c0 f=... w=... g=... t=1|...`` syntax.
        """
        ...

    def __repr__(self) -> str: ...

class MultibandCompressorBuilder:
    """Type-safe builder for multiband compression using asplit → acompressor×N → amix.

    Each band applies independent dynamics control with configurable threshold, ratio,
    attack, and release parameters.
    """

    def __new__(cls, bands: list[dict[str, float]]) -> MultibandCompressorBuilder:
        """Create a new MultibandCompressorBuilder.

        Args:
            bands: List of band dicts, each with required keys:
                - ``threshold`` (float): Compression threshold in dB (must be < 0).
                - ``ratio`` (float): Compression ratio (must be > 1.0).
                - ``attack`` (float): Attack time in ms (> 0).
                - ``release`` (float): Release time in ms (> 0).

        Raises:
            ValueError: If bands is empty, any threshold >= 0, or any ratio <= 1.0.
        """
        ...

    def build(self) -> FilterGraph:
        """Build the multiband compressor FilterGraph.

        Returns:
            A FilterGraph with ``asplit=outputs=N`` → per-band ``acompressor`` → ``amix=inputs=N``.
        """
        ...

    def __repr__(self) -> str: ...

# ========== Spatial Audio Builders ==========

class PanBuilder:
    def __new__(cls, position: float) -> PanBuilder: ...
    def with_automation(self, automation: Automation) -> PanBuilder: ...
    def build(self) -> Filter: ...

class ConvolutionReverbBuilder:
    def __new__(cls, ir_name: str, mix: float) -> ConvolutionReverbBuilder: ...
    def build(self) -> Filter: ...
    def ir_name(self) -> str: ...

# ========== Effect Builder — Reverse ==========

class ReverseBuilder:
    """Type-safe builder for FFmpeg video and audio reversal filters.

    Generates the ``reverse`` filter for video and the ``areverse`` filter for audio.
    Both filters buffer the entire clip segment in memory — use only on short clips.
    Maximum duration enforcement is handled by the application layer via
    ``STOAT_REVERSE_MAX_DURATION_S``.

    Examples::

        builder = ReverseBuilder()
        video_filter = builder.video_filter()  # "reverse"
        audio_filter = builder.audio_filter()  # "areverse"
    """

    def __new__(cls) -> ReverseBuilder: ...
    def video_filter(self) -> Filter: ...
    def audio_filter(self) -> Filter: ...
    def __repr__(self) -> str: ...
