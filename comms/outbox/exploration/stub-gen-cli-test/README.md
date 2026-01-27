# Stub Generation CLI Test Results

**Summary:** The `stub_gen` binary does NOT accept CLI arguments and currently FAILS to run. It looks for `pyproject.toml` at `CARGO_MANIFEST_DIR` (rust/stoat_ferret_core/), but that file only exists at the project root. The stubs in `stubs/stoat_ferret_core/` appear to be manually written, not auto-generated.

## Key Findings

1. **stub_gen does not parse CLI arguments** - The source code simply calls `stub.generate()` with no argument parsing
2. **stub_gen fails with "file not found" error** - It expects pyproject.toml at CARGO_MANIFEST_DIR
3. **Existing stubs are manually written** - Located at `stubs/stoat_ferret_core/` (not auto-generated)
4. **git diff shows stubs are up-to-date** - No pending changes to stub files

## Documentation

- [CLI Test Results](./cli-test-results.md) - Detailed command outputs and exit codes
- [Stub Locations](./stub-locations.md) - Configuration analysis and file locations
