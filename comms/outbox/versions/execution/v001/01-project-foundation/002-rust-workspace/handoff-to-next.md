# Handoff: 002-rust-workspace

## What Was Done

Created the Rust workspace structure for `stoat_ferret_core`:

### Files Created
```
rust/stoat_ferret_core/
├── Cargo.toml              # PyO3 0.26, pyo3-stub-gen 0.17
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

### Configuration Changes
- `pyproject.toml`: Added `[tool.maturin]` config, currently using `hatchling` backend

## What Needs to Be Done

### Before Next Feature

1. **Fix Build Environment**: Install Visual Studio Build Tools 2022 with C++ workload
2. **Build Native Module**: Run `maturin develop`
3. **Switch Build Backend**: Change pyproject.toml from `hatchling` to `maturin`
4. **Verify Rust Quality Gates**:
   ```bash
   cd rust/stoat_ferret_core
   cargo clippy -- -D warnings
   cargo test
   ```

### Testing the Build

Once build environment is fixed:
```bash
# Build native extension
maturin develop

# Verify it works
python -c "from stoat_ferret_core import health_check; print(health_check())"
# Should print: stoat_ferret_core OK

# Run Rust tests
cargo test --manifest-path rust/stoat_ferret_core/Cargo.toml
```

## Key Technical Decisions

1. **PyO3 0.26** (not 0.23): Required for compatibility with pyo3-stub-gen 0.17
2. **abi3-py310**: ABI stability from Python 3.10+
3. **Fallback stub**: `stoat_ferret_core/__init__.py` catches ImportError to allow Python-only development

## Dependencies

The Rust workspace depends on:
- pyo3 = "0.26" with features = ["abi3-py310"]
- pyo3-stub-gen = "0.17"
- proptest = "1.0" (dev dependency for property-based testing)

## Notes for Future Development

- Add new Rust functions to `lib.rs`, annotate with `#[gen_stub_pyfunction]` and `#[pyfunction]`
- Register them in the `_core` pymodule
- Re-run stub generator to update type stubs
- Export from `src/stoat_ferret_core/__init__.py`
