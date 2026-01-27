# Implementation Plan: Stub Regeneration

**Execution Order: FIRST in Theme 01**

## Step 1: Audit Current Stub Binary
```bash
cd rust/stoat_ferret_core
cat src/bin/stub_gen.rs
```
Verify it uses pyo3-stub-gen correctly.

## Step 2: Run Stub Generation
```bash
cd rust/stoat_ferret_core
cargo run --bin stub_gen
```
Note output location and format.

## Step 3: Configure Output Path
Modify stub_gen.rs if needed to output directly to `../../stubs/stoat_ferret_core/`.

## Step 4: Replace Manual Stubs
```bash
rm stubs/stoat_ferret_core/_core.pyi
cargo run --bin stub_gen
```
Verify `__init__.pyi` re-exports correctly.

## Step 5: Identify Test Breakages
```bash
uv run pytest tests/test_pyo3_bindings.py -v 2>&1 | grep -E "(FAILED|ERROR)"
```

## Step 6: Update Tests (~20 assertions expected)
For each failing test, update method names to match generated stubs.

Common fixes based on exploration findings:
- `Duration.between()` → `Duration.between_positions()`
- `FrameRate.ntsc_30()` → `FrameRate.fps_29_97()`
- `FrameRate.ntsc_60()` → `FrameRate.fps_59_94()`
- `FrameRate.as_float()` → `FrameRate.fps` (property)
- `Position.from_frames(n)` → `Position(n)` (constructor)
- `Duration.from_frames(n)` → `Duration(n)` (constructor)
- Check property names: `py_frames` → `frames`, etc.

## Step 7: Add CI Verification
Add to `.github/workflows/ci.yml`:
```yaml
- name: Verify stubs are up-to-date
  run: |
    cd rust/stoat_ferret_core
    cargo run --bin stub_gen -- --output-dir /tmp/stubs
    diff -r /tmp/stubs ../../stubs/stoat_ferret_core || (echo "Stubs out of date! Run: cd rust/stoat_ferret_core && cargo run --bin stub_gen" && exit 1)
```

## Step 8: Update Documentation
Add to README.md:
```markdown
## Regenerating Type Stubs
After modifying Rust PyO3 bindings:
```bash
cd rust/stoat_ferret_core
cargo run --bin stub_gen
```
CI will fail if stubs are out of date.
```

## Verification
- `uv run pytest tests/ -v` all pass
- `uv run mypy src/` passes with new stubs
- CI stub verification step passes