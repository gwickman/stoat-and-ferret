# Stub File Locations

## pyproject.toml Configuration

**Location:** `pyproject.toml` (project root)

### Relevant Settings
```toml
[tool.maturin]
python-source = "src"
module-name = "stoat_ferret_core._core"
features = ["pyo3/extension-module"]
manifest-path = "rust/stoat_ferret_core/Cargo.toml"

[tool.mypy]
mypy_path = ["src", "stubs"]
```

### Expected Output Location (per pyo3-stub-gen docs)

Based on:
- `python-source = "src"`
- `module-name = "stoat_ferret_core._core"`

pyo3-stub-gen would generate stubs at:
```
src/stoat_ferret_core/_core.pyi
```

---

## Actual Stub Locations

### .pyi Files Found (excluding .venv)
```
stubs/stoat_ferret_core/_core.pyi    (16,912 bytes, Jan 26 16:55)
stubs/stoat_ferret_core/__init__.pyi (1,852 bytes, Jan 26 16:55)
```

### File Analysis

**`stubs/stoat_ferret_core/__init__.pyi`**
- Appears manually written
- Contains docstring: "These stubs are generated from the Rust code using pyo3-stub-gen"
- Re-exports all types from `_core` with proper `as X` syntax for explicit exports

**`stubs/stoat_ferret_core/_core.pyi`**
- Contains comprehensive type definitions
- Includes detailed docstrings for all classes and methods
- 632 lines of well-documented type stubs
- Covers: Timeline types, FFmpeg command building, Filter helpers, Sanitization functions, Custom exceptions

---

## Configuration Mismatch

| Aspect | Expected | Actual |
|--------|----------|--------|
| pyproject.toml location | rust/stoat_ferret_core/ | project root |
| Stub output path | src/stoat_ferret_core/_core.pyi | stubs/stoat_ferret_core/_core.pyi |
| Generation method | Automated via stub_gen | Manual maintenance |

---

## Implications

1. **stub_gen binary is non-functional** - Cannot auto-generate stubs without fixing the pyproject.toml path issue

2. **Stubs are manually maintained** - The `stubs/` directory is referenced in `tool.mypy.mypy_path` and works for type checking

3. **To fix stub_gen**, either:
   - Create a pyproject.toml in rust/stoat_ferret_core/ with appropriate maturin settings
   - Or modify the stub_gen binary to accept a custom pyproject.toml path
