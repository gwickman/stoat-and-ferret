# Theme 3: command-builder

## Overview
Implement type-safe FFmpeg command construction with input sanitization. This module generates FFmpeg argument arrays (never shell strings) with security built in.

## Context
Based on EXP-002 (recording-fake-pattern) exploration:
- Python orchestration will use an FFmpegExecutor protocol
- Rust builds the commands, Python executes via subprocess
- Recording/replay happens at the Python boundary

This theme implements the Rust command builder that generates safe, validated commands.

## Architecture Decisions

### AD-001: Argument Arrays
Generate `Vec<String>` argument arrays, never shell strings:
- Avoids shell injection entirely
- Python uses `subprocess.run(args)` without shell=True
- Each argument properly isolated

### AD-002: Sanitization at Build Time
All user-provided text is sanitized when building the command:
- Text for filters escaped before filter string generation
- Paths validated against traversal
- Parameters bounds-checked

### AD-003: Builder Pattern
Fluent builder API for command construction:
- Type-safe, catches errors at compile time
- Validation on `build()` call
- Mutable builder for ergonomics

## Dependencies
- Theme 1 (project-foundation) — build infrastructure
- Theme 2 (timeline-math) — Position/Duration types for clip references

## Risks
- FFmpeg syntax complexity
- Filter graph escaping edge cases

## Success Criteria
- Generated commands execute correctly with FFmpeg
- All user input sanitized
- Type stubs enable IDE completion
- Mypy passes with generated stubs