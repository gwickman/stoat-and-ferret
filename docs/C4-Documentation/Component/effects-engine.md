# Effects Engine

## Purpose

The Effects Engine component manages the catalog of video and audio effects available in the application. It defines an extensible registry of named effects, validates effect parameters against JSON schemas, and produces FFmpeg filter strings by delegating construction to Rust Core builders. The component serves as the bridge between user-facing effect selection and the low-level filter syntax consumed by FFmpeg.

## Responsibilities

- Maintain a named registry of available effect definitions
- Validate user-supplied effect parameters against each effect's JSON Schema (Draft 7)
- Generate FFmpeg filter strings by delegating to PyO3 builder objects from the Rust Core component
- Provide AI-friendly hints for each parameter to support LLM-guided effect configuration
- Expose a default registry pre-populated with all built-in effects
- Report structured validation errors with per-field path and message for client-side highlighting

## Interfaces

### Provided Interfaces

**EffectRegistry**
- `register(effect_type: str, definition: EffectDefinition) -> None` — Register a named effect
- `get(effect_type: str) -> EffectDefinition | None` — Retrieve a registered effect
- `list_all() -> list[tuple[str, EffectDefinition]]` — Enumerate all registered effects
- `validate(effect_type: str, parameters: dict) -> list[EffectValidationError]` — Validate parameters; empty list means valid

**EffectDefinition (frozen dataclass)**
- `name: str` — Human-readable name
- `description: str` — Effect description
- `parameter_schema: dict` — JSON Schema Draft 7 for parameter validation
- `ai_hints: dict[str, str]` — Per-parameter LLM guidance strings
- `preview_fn: Callable[[], str]` — Returns example filter string with default parameters
- `build_fn: Callable[[dict], str]` — Returns FFmpeg filter string from parameter dict

**Factory Function**
- `create_default_registry() -> EffectRegistry` — Creates and returns a registry pre-populated with all 9 built-in effects

**Built-in Effect Types**

| Effect Type | Description |
|-------------|-------------|
| `text_overlay` | Text overlay via FFmpeg `drawtext` filter |
| `speed_control` | Playback speed adjustment (0.25–4.0×) via `setpts` and `atempo` |
| `audio_mix` | Multi-stream audio mixing via `amix` |
| `volume` | Audio volume adjustment (linear or dB) |
| `audio_fade` | Audio fade in or out via `afade` |
| `audio_ducking` | Sidechain compression for speech-over-music via `sidechaincompress` |
| `video_fade` | Video fade in or out via `fade` |
| `xfade` | Video crossfade transition via `xfade` |
| `acrossfade` | Audio crossfade between two streams via `acrossfade` |

### Required Interfaces

- **Rust Core component** — All FFmpeg filter string builders: `DrawtextBuilder`, `SpeedControl`, `AmixBuilder`, `VolumeBuilder`, `AfadeBuilder`, `DuckingPattern`, `FadeBuilder`, `XfadeBuilder`, `AcrossfadeBuilder`, `TransitionType`

## Code Modules

| Module | Source | Purpose |
|--------|--------|---------|
| Registry | `src/stoat_ferret/effects/registry.py` | `EffectRegistry` class with dict-based storage and `jsonschema.Draft7Validator` parameter validation; `EffectValidationError` with path and message |
| Definitions | `src/stoat_ferret/effects/definitions.py` | `EffectDefinition` frozen dataclass; all 9 built-in effect definitions as module-level constants; `create_default_registry()` factory |

## Key Behaviors

**Schema-Driven Validation:** The `validate()` method creates a `Draft7Validator` from the effect's `parameter_schema` and calls `iter_errors()` to collect all validation failures in a single pass. Errors include the JSON path to the failing field, enabling client-side per-field highlighting.

**Builder Delegation Pattern:** Each effect's `build_fn` extracts relevant keys from the parameter dict, constructs a PyO3 builder from Rust Core, applies optional parameters with method chaining, and returns the builder's string representation. This keeps all FFmpeg filter syntax inside the Rust layer.

**Optional Parameter Handling:** Build functions use `if "param" in parameters` guards rather than requiring every parameter. This allows partial parameter dicts for preview operations.

**Lazy Registry Initialization:** The API Gateway lazily creates the default registry on first use via `create_default_registry()`. An alternative registry can be injected via `create_app()` for testing or custom effect sets.

**AI Discoverability:** The `ai_hints` dict on each effect definition provides parameter-level guidance for LLMs (e.g., "values <1 slow down, >1 speed up" for speed factor). These hints are included in the `/api/v1/effects` list endpoint response.

## Inter-Component Relationships

```
API Gateway (effects router)
    |-- uses --> Effects Engine (EffectRegistry)
    |                   |
    |                   |-- parameter validation --> (internal JSON Schema validation)
    |                   |-- filter string generation --> Rust Core (builder objects)
    |
    |-- inject via create_app() --> Effects Engine (EffectRegistry, custom or default)
```

## Version History

| Version | Changes |
|---------|---------|
| v011 | Initial effects engine with registry and 9 built-in definitions |
