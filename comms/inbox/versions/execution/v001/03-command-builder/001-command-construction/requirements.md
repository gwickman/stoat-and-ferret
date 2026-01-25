# FFmpeg Command Construction

## Goal
Implement type-safe FFmpeg command builder that generates argument arrays for subprocess execution.

## Requirements

### FR-001: Command Structure
- Build complete FFmpeg commands as Vec<String>
- Support global options (overwrite, loglevel)
- Support input specifications with options
- Support output specifications with codec options

### FR-002: Input Options
- `-i` input file path
- `-ss` seek to position
- `-t` duration limit
- `-stream_loop` for looping inputs

### FR-003: Output Options
- `-c:v` video codec
- `-c:a` audio codec
- `-preset` encoding preset
- `-crf` quality level
- `-f` output format

### FR-004: Builder API
```rust
FFmpegCommand::new()
    .overwrite(true)
    .input("input.mp4")
        .seek(Position::from_seconds(10.0))
        .done()
    .output("output.mp4")
        .video_codec("libx264")
        .preset("fast")
        .done()
    .build()?
```

### FR-005: Validation
- At least one input required
- At least one output required
- Paths must be non-empty
- Numeric values in valid ranges

## Acceptance Criteria
- [ ] Builder API compiles and is ergonomic
- [ ] Generated commands are valid FFmpeg syntax
- [ ] All validation rules enforced on build()
- [ ] No shell escaping needed (array output)