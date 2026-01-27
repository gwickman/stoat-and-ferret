# Command Integration

## Goal
Create integration layer connecting Rust FFmpegCommand to Python executor.

## Requirements

### FR-001: Integration Function
- execute_command(executor, command) -> ExecutionResult
- Calls command.build() to get args
- Passes args to executor.run()

### FR-002: Error Handling
- Handle FFmpegCommand validation errors (no inputs/outputs)
- Handle executor errors (timeout, subprocess failure)
- Wrap errors with context

### FR-003: Integration Tests
- Test with real Rust command and fake executor
- Test error cases

## Acceptance Criteria
- [ ] Rust command successfully passed to Python executor
- [ ] Validation errors handled gracefully
- [ ] Integration test demonstrates full flow