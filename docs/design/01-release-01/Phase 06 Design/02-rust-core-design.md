# Phase 6: Rust Core Design

Phase 6 is primarily Python-side infrastructure and documentation. Rust core additions are limited to version info exposure, schema introspection helpers for AI discovery, and stub generation updates.

## Module: `version` (new)

**Location:** `rust/stoat_ferret_core/src/version.rs`

Exposes build metadata to Python via PyO3. Uses compile-time environment variables set by `build.rs`.

```rust
// build.rs additions
fn main() {
    println!("cargo:rustc-env=BUILD_TIMESTAMP={}", chrono::Utc::now().to_rfc3339());
    if let Ok(sha) = std::env::var("GIT_SHA") {
        println!("cargo:rustc-env=GIT_SHA={sha}");
    }
}
```

```rust
// src/version.rs
use pyo3::prelude::*;

#[pyclass]
pub struct VersionInfo {
    #[pyo3(get)]
    pub core_version: String,
    #[pyo3(get)]
    pub build_timestamp: String,
    #[pyo3(get)]
    pub git_sha: Option<String>,
}

#[pymethods]
impl VersionInfo {
    #[staticmethod]
    pub fn current() -> Self {
        Self {
            core_version: env!("CARGO_PKG_VERSION").to_string(),
            build_timestamp: env!("BUILD_TIMESTAMP").to_string(),
            git_sha: option_env!("GIT_SHA").map(String::from),
        }
    }
}
```

**PyO3 binding:** Add `m.add_class::<VersionInfo>()?;` to `lib.rs`.

**Stub:** Add to `src/stoat_ferret_core/_core.pyi`:
```python
class VersionInfo:
    core_version: str
    build_timestamp: str
    git_sha: str | None
    @staticmethod
    def current() -> VersionInfo: ...
```

## Module: `schema` (new)

**Location:** `rust/stoat_ferret_core/src/schema.rs`

Provides structured parameter metadata for AI agent discovery. This extends the existing effect registry with machine-readable parameter schemas.

```rust
use pyo3::prelude::*;

#[pyclass]
#[derive(Clone)]
pub struct ParameterSchema {
    #[pyo3(get)]
    pub name: String,
    #[pyo3(get)]
    pub param_type: String,
    #[pyo3(get)]
    pub default_value: Option<String>,
    #[pyo3(get)]
    pub min_value: Option<f64>,
    #[pyo3(get)]
    pub max_value: Option<f64>,
    #[pyo3(get)]
    pub enum_values: Option<Vec<String>>,
    #[pyo3(get)]
    pub description: String,
    #[pyo3(get)]
    pub ai_hint: Option<String>,
}

/// Returns parameter schemas for a named effect.
/// Called from Python effect registry to enrich AI discovery responses.
#[pyfunction]
pub fn get_effect_parameter_schemas(effect_name: &str) -> Vec<ParameterSchema> {
    // Implementation reads from compiled effect definitions
    // Returns empty vec for unknown effects
    todo!()
}
```

**Design rationale:** Parameter schemas live in Rust because effect definitions (filter builders, validation ranges) are already in Rust. Exposing schemas from the same source prevents drift between validation logic and documented constraints.

## Existing Module Updates

### `batch.rs` — No changes
Batch processing infrastructure (BatchJobStatus, calculate_batch_progress) is complete from Phase 5. Phase 6 uses it as-is.

### `lib.rs` — Registration updates
```rust
// Add to existing module registration in lib.rs
m.add_class::<version::VersionInfo>()?;
m.add_class::<schema::ParameterSchema>()?;
m.add_function(wrap_pyfunction!(schema::get_effect_parameter_schemas, m)?)?;
```

## Property-Based Tests

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn version_info_current_returns_valid_semver() {
        let info = VersionInfo::current();
        assert!(semver::Version::parse(&info.core_version).is_ok());
        assert!(!info.build_timestamp.is_empty());
    }
}
```

Schema introspection tests will use proptest to verify that all registered effects return non-empty parameter lists with valid type strings.

## Impact Summary

| Change | Files | Risk |
|--------|-------|------|
| New `version.rs` module | 2 new (version.rs, build.rs update) | Low — read-only, no state |
| New `schema.rs` module | 1 new | Medium — must stay in sync with effect definitions |
| `lib.rs` registration | 1 modified | Low — additive only |
| Stub generation | 1 modified (_core.pyi) | Low — add new classes |
