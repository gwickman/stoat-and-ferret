# Handoff: 002-rust-workspace

## What Was Done

The Rust workspace is fully set up and operational:

### Files Created
```
rust/stoat_ferret_core/
├── Cargo.toml              # PyO3 0.26, pyo3-stub-gen 0.17
├── Cargo.lock              # Locked dependencies
├── rustfmt.toml            # edition = 2021, max_width = 100
└── src/
    ├── lib.rs              # health_check() + pymodule
    └── bin/
        └── stub_gen.rs     # pyo3-stub-gen binary

src/stoat_ferret_core/
└── __init__.py             # Python wrapper with ImportError fallback

stubs/stoat_ferret_core/
├── __init__.pyi            # Type stubs
└── _core.pyi               # Internal module stubs
```

### Configuration
- `pyproject.toml`: Added `[tool.maturin]` config

### Verified Working
- `maturin develop` builds and installs the module
- `from stoat_ferret_core import health_check` returns `"stoat_ferret_core OK"`
- `cargo clippy -- -D warnings` passes
- `cargo test` passes (1 test)
- All Python quality gates pass

## How to Build the Rust Extension

```bash
# Set PATH to include cargo (if not already in PATH)
PATH="$HOME/.cargo/bin:$PATH" uv run maturin develop

# Or from a shell with cargo in PATH
uv run maturin develop
```

## How to Run Quality Gates

### Rust
```bash
cd rust/stoat_ferret_core
cargo clippy -- -D warnings
cargo test
```

### Python
```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest -v
```

## Adding New Rust Functions

1. Add the function to `rust/stoat_ferret_core/src/lib.rs`:
   ```rust
   #[gen_stub_pyfunction]
   #[pyfunction]
   fn my_function(arg: i32) -> String {
       // implementation
   }
   ```

2. Register in the pymodule:
   ```rust
   #[pymodule]
   fn _core(m: &Bound<PyModule>) -> PyResult<()> {
       m.add_function(wrap_pyfunction!(health_check, m)?)?;
       m.add_function(wrap_pyfunction!(my_function, m)?)?;  // Add here
       Ok(())
   }
   ```

3. Export from Python wrapper (`src/stoat_ferret_core/__init__.py`):
   ```python
   from stoat_ferret_core._core import health_check, my_function
   __all__ = ["health_check", "my_function"]
   ```

4. Update type stubs in `stubs/stoat_ferret_core/__init__.pyi`

5. Rebuild: `maturin develop`

## Key Dependencies

- **pyo3** 0.26 with `abi3-py310` - Python bindings
- **pyo3-stub-gen** 0.17 - Type stub generation support
- **proptest** 1.0 (dev) - Property-based testing

## Notes for Next Feature

The Rust core is ready for implementing:
- Filter string generation
- Timeline math calculations
- FFmpeg command building
- Input sanitization

The Python wrapper with fallback allows development to continue even if the Rust extension isn't built, which is useful for CI environments without Rust tooling.
