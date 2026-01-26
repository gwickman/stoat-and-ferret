---
status: complete
acceptance_passed: 4
acceptance_total: 4
quality_gates:
  ruff: pass
  mypy: pass
  pytest: pass
  clippy: pass
  cargo_test: pass
---
# Completion Report: 001-command-construction

## Summary

Implemented a type-safe FFmpeg command builder in Rust that generates argument arrays for subprocess execution. The builder follows a fluent API pattern allowing chained method calls to construct complete FFmpeg commands without shell escaping concerns.

## Acceptance Criteria

| Criterion | Status | Notes |
|-----------|--------|-------|
| Builder API compiles and is ergonomic | PASS | Fluent builder pattern with method chaining |
| Generated commands are valid FFmpeg syntax | PASS | Arguments ordered correctly: globals, inputs with options, filter_complex, outputs with options |
| All validation rules enforced on build() | PASS | Validates inputs/outputs present, paths non-empty, CRF 0-51 |
| No shell escaping needed (array output) | PASS | Returns `Vec<String>` for direct use with `std::process::Command` |

## Implementation Details

### Files Created

1. `rust/stoat_ferret_core/src/ffmpeg/mod.rs` - Module definition and integration tests
2. `rust/stoat_ferret_core/src/ffmpeg/command.rs` - Core builder implementation

### Files Modified

1. `rust/stoat_ferret_core/src/lib.rs` - Added `ffmpeg` module export

### API Surface

```rust
FFmpegCommand::new()
    .overwrite(true)          // -y
    .loglevel("warning")      // -loglevel warning
    .input("input.mp4")       // -i input.mp4
    .seek(10.0)               // -ss 10.000 (applies to last input)
    .duration(5.0)            // -t 5.000 (applies to last input)
    .stream_loop(3)           // -stream_loop 3 (applies to last input)
    .filter_complex("...")    // -filter_complex ...
    .output("output.mp4")
    .video_codec("libx264")   // -c:v libx264 (applies to last output)
    .audio_codec("aac")       // -c:a aac (applies to last output)
    .preset("fast")           // -preset fast (applies to last output)
    .crf(23)                  // -crf 23 (applies to last output)
    .format("mp4")            // -f mp4 (applies to last output)
    .map("[scaled]")          // -map [scaled] (applies to last output)
    .build()?                 // Returns Result<Vec<String>, CommandError>
```

### Error Handling

- `CommandError::NoInputs` - No input files specified
- `CommandError::NoOutputs` - No output files specified
- `CommandError::EmptyPath` - Input or output path is empty string
- `CommandError::InvalidCrf(u8)` - CRF value > 51

All errors implement `Display` and `std::error::Error`.

## Test Coverage

- Unit tests in `ffmpeg::command::tests` module
- Integration tests in `ffmpeg::tests` module
- Doc tests for all public API methods
- All 161 Rust tests pass

## Quality Gates

| Gate | Status | Details |
|------|--------|---------|
| cargo clippy | PASS | No warnings with -D warnings |
| cargo test | PASS | 161 unit tests, 71 doc tests |
| ruff check | PASS | All checks passed |
| ruff format | PASS | 4 files already formatted |
| mypy | PASS | No issues in 2 source files |
| pytest | PASS | 4 tests, 86% coverage |
