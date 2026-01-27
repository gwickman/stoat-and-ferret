# Implementation Plan: AGENTS.md PyO3 Guidance

## Step 1: Identify Insertion Point
Read AGENTS.md, find appropriate location (likely after Rust/quality sections).

## Step 2: Draft Section
```markdown
## PyO3 Bindings

### Incremental Binding Rule
When implementing new Rust types or functions, add PyO3 bindings in the SAME feature. Do not defer bindings to a later feature—this creates tech debt that accumulates.

**Wrong:** Implement Rust type in feature 1, add bindings in feature 5.
**Right:** Implement Rust type AND bindings together in feature 1.

### Stub Regeneration
After modifying any PyO3 bindings, regenerate type stubs:

```bash
cd rust/stoat_ferret_core
cargo run --bin stub_gen
```

CI verifies stubs match the Rust API. Forgetting to regenerate will cause CI failure.

### Naming Convention
Use `py_` prefix for Rust method names, with `#[pyo3(name = "...")]` to expose clean names to Python:

```rust
#[pymethods]
impl MyType {
    #[pyo3(name = "calculate")]
    fn py_calculate(&self, value: i32) -> i32 {
        // PyRefMut pattern for method chaining
    }
}
```

This allows:
- Rust: `my_type.calculate(5)` (returns Self for chaining)
- Python: `my_type.calculate(5)` (clean API, no py_ prefix visible)

### Example: Complete Type with Bindings

```rust
use pyo3::prelude::*;
use pyo3_stub_gen::derive::gen_stub_pyclass;

#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct Segment {
    #[pyo3(get)]
    pub start: u64,
    #[pyo3(get)]  
    pub end: u64,
}

#[pymethods]
impl Segment {
    #[new]
    fn py_new(start: u64, end: u64) -> PyResult<Self> {
        if end <= start {
            return Err(PyValueError::new_err("end must be > start"));
        }
        Ok(Self { start, end })
    }
    
    #[pyo3(name = "length")]
    fn py_length(&self) -> u64 {
        self.end - self.start
    }
}
```

Always regenerate stubs after adding or modifying bindings.
```

## Step 3: Add to AGENTS.md
Insert section at identified location.

## Step 4: Verify Formatting
Ensure markdown renders correctly, code blocks are properly fenced.

## Verification
- AGENTS.md contains new section
- Section is readable and actionable
- Example code is syntactically correct