# Effects Definitions

**Source:** `src/stoat_ferret/effects/definitions.py`
**Component:** Effects Engine

## Purpose

Defines the available effects that can be applied to media (video and audio) through the effects engine. Provides effect definitions with JSON schemas, AI hints for LLM guidance, and FFmpeg filter builders for 10 built-in effects (text overlay, speed control, audio mixing, volume, fading, ducking, crossfading).

## Public Interface

### Classes

- `EffectDefinition`: Frozen dataclass defining an available effect with schema, AI hints, and FFmpeg builder functions
  - `name: str`: Human-readable effect name
  - `description: str`: Description of what the effect does
  - `parameter_schema: dict[str, object]`: JSON Schema dict describing effect parameters
  - `ai_hints: dict[str, str]`: Map of parameter name to AI hint string for LLM guidance
  - `preview_fn: Callable[[], str]`: Function returning FFmpeg filter string preview using default parameters
  - `build_fn: Callable[[dict[str, Any]], str]`: Function receiving parameter dict and returning FFmpeg filter string

### Functions

- `create_default_registry() -> EffectRegistry`: Create a registry with all built-in effects registered

### Built-in Effects (Module Constants)

- `TEXT_OVERLAY`: Add text overlays to video with customizable font, position, and styling
- `SPEED_CONTROL`: Adjust video and audio playback speed with automatic tempo chaining
- `AUDIO_MIX`: Mix multiple audio input streams into a single output
- `VOLUME`: Adjust audio volume with linear or dB control
- `AUDIO_FADE`: Apply fade in or fade out to audio with configurable duration and curve
- `AUDIO_DUCKING`: Lower music volume during speech using sidechain compression
- `VIDEO_FADE`: Apply fade in or fade out to video with configurable color and duration
- `XFADE`: Crossfade between two video inputs with selectable transition effect
- `ACROSSFADE`: Crossfade between two audio inputs with configurable curve types

## Dependencies

### Internal Dependencies

- `stoat_ferret.effects.registry`: TYPE_CHECKING import for EffectRegistry type hint

### External Dependencies

- `stoat_ferret_core`: PyO3 bindings for FFmpeg filter builders:
  - `AcrossfadeBuilder`: Build acrossfade filter strings
  - `AfadeBuilder`: Build afade (audio fade) filter strings
  - `AmixBuilder`: Build amix (audio mix) filter strings
  - `DrawtextBuilder`: Build drawtext (text overlay) filter strings
  - `DuckingPattern`: Build sidechaincompress filter graphs for ducking
  - `FadeBuilder`: Build fade (video fade) filter strings
  - `SpeedControl`: Generate setpts and atempo filter strings for speed control
  - `TransitionType`: Enumeration of xfade transition types
  - `VolumeBuilder`: Build volume filter strings
  - `XfadeBuilder`: Build xfade (crossfade) filter strings

## Key Implementation Details

### Effect Definition Pattern

Each effect is defined as a frozen `EffectDefinition` instance with:
1. **Metadata**: Name and description
2. **JSON Schema**: Complete parameter validation schema (Draft 7)
3. **AI Hints**: Guidance strings for each parameter to help LLMs generate appropriate values
4. **Preview Function**: Returns example FFmpeg filter string with default parameters
5. **Build Function**: Takes parameter dict and returns actual FFmpeg filter string

### Builder Delegation Pattern

All effects delegate FFmpeg filter string generation to PyO3 builder objects from `stoat_ferret_core`. Build functions:
- Extract relevant parameters from the parameter dict
- Create builder instances
- Call chainable builder methods for optional parameters
- Return string representation of the filter

### Parameter Handling

Build functions implement optional parameter handling:
- Required parameters (e.g., `text` for text overlay) are extracted with defaults
- Optional parameters are checked with `if "param" in parameters` pattern
- Parameters are passed to builder methods in order of specificity
- Type conversions (e.g., string volume to float) occur in build functions

### JSON Schema Validation

Each effect's `parameter_schema` uses JSON Schema Draft 7:
- Defines `type: "object"` with properties and constraints
- Includes `required` array for mandatory parameters
- Specifies type constraints, enumerations, min/max bounds, defaults
- Includes human-readable descriptions for each parameter

### AI Hints

The `ai_hints` dict provides LLM-friendly guidance:
- Typical value ranges (e.g., "0.25-4.0" for speed factor)
- Semantic guidance (e.g., "values <1 slow down, >1 speed up")
- Unit information (e.g., "in milliseconds", "in pixels")
- Example values and recommended ranges
- Contextual advice for effect selection

## Relationships

- **Used by:** `EffectRegistry` (registered via `create_default_registry()`)
- **Uses:** `stoat_ferret_core` builder classes for FFmpeg filter generation
