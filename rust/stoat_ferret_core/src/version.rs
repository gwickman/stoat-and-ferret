//! Deployment version metadata exposed to Python.
//!
//! The [`VersionInfo`] PyO3 class carries fields baked in at compile time by
//! `build.rs`:
//!
//! - `core_version` — value of `CARGO_PKG_VERSION` from `Cargo.toml`.
//! - `build_timestamp` — ISO 8601 UTC timestamp generated when the crate
//!   compiled.
//! - `git_sha` — short git SHA, or the literal string `"unknown"` when the
//!   `GIT_SHA` env var was unset and `git rev-parse` did not resolve a value
//!   at build time.
//!
//! The Python `/api/v1/version` endpoint instantiates this type via
//! `VersionInfo::current()` (see [`VersionInfo`]) to report deployment
//! metadata alongside the alembic revision of the database.
//!
//! The `option_env!("GIT_SHA")` macro reads the env value captured at build
//! time rather than the runtime environment, so the returned struct reflects
//! the build, not the process.

use pyo3::prelude::*;
use pyo3_stub_gen::derive::{gen_stub_pyclass, gen_stub_pymethods};

/// Build-time deployment metadata surfaced to Python.
///
/// Fields are populated from values captured at compile time by `build.rs`
/// (see module docs). The struct is `Clone` so Python callers can freely
/// rebind without worrying about ownership.
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct VersionInfo {
    /// Semver version from Cargo.toml (`CARGO_PKG_VERSION`).
    #[pyo3(get)]
    pub core_version: String,
    /// ISO 8601 UTC timestamp captured at build time.
    #[pyo3(get)]
    pub build_timestamp: String,
    /// Short git SHA of HEAD, or `"unknown"` when unavailable.
    #[pyo3(get)]
    pub git_sha: String,
}

impl VersionInfo {
    /// Return a [`VersionInfo`] populated from the build-time metadata.
    ///
    /// Pure accessor over compile-time constants; cheap and never fails. The
    /// PyO3 binding (`py_current`) delegates to this function and exposes it
    /// to Python as `VersionInfo.current()`.
    ///
    /// # Example
    ///
    /// ```
    /// use stoat_ferret_core::version::VersionInfo;
    ///
    /// let info = VersionInfo::current();
    /// // core_version is the crate version from Cargo.toml (semver).
    /// assert_eq!(info.core_version.split('.').count(), 3);
    /// // git_sha is always populated; "unknown" when GIT_SHA was unset.
    /// assert!(!info.git_sha.is_empty());
    /// ```
    pub fn current() -> Self {
        Self {
            core_version: env!("CARGO_PKG_VERSION").to_string(),
            build_timestamp: env!("BUILD_TIMESTAMP").to_string(),
            git_sha: option_env!("GIT_SHA").unwrap_or("unknown").to_string(),
        }
    }
}

#[gen_stub_pymethods]
#[pymethods]
impl VersionInfo {
    /// PyO3 binding for [`VersionInfo::current`].
    ///
    /// Exposed to Python as `VersionInfo.current()` (via `#[pyo3(name =
    /// "current")]`).
    ///
    /// # Example (Python)
    ///
    /// ```python
    /// from stoat_ferret_core import VersionInfo
    ///
    /// info = VersionInfo.current()
    /// print(info.core_version, info.build_timestamp, info.git_sha)
    /// ```
    #[staticmethod]
    #[pyo3(name = "current")]
    fn py_current() -> Self {
        Self::current()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_version_info_returns_valid_semver() {
        let info = VersionInfo::py_current();
        let parts: Vec<&str> = info.core_version.split('.').collect();
        assert_eq!(
            parts.len(),
            3,
            "core_version must be major.minor.patch: {}",
            info.core_version
        );
        for part in &parts {
            assert!(
                part.parse::<u64>().is_ok(),
                "semver component must parse as u64: {part}"
            );
        }
    }

    #[test]
    fn test_version_info_has_build_timestamp() {
        let info = VersionInfo::py_current();
        assert!(
            !info.build_timestamp.is_empty(),
            "build_timestamp must be non-empty"
        );
        // ISO 8601 UTC format: YYYY-MM-DDTHH:MM:SSZ
        assert!(
            info.build_timestamp.ends_with('Z'),
            "build_timestamp must end with Z: {}",
            info.build_timestamp
        );
        assert!(
            info.build_timestamp.contains('T'),
            "build_timestamp must contain date/time separator T: {}",
            info.build_timestamp
        );
    }

    #[test]
    fn test_version_info_handles_missing_git_sha() {
        // The struct is always constructible regardless of whether GIT_SHA was
        // set at build time; when unset, option_env!() evaluates to None and
        // the fallback "unknown" is substituted. Verify the field is always a
        // non-empty string (short hash or the literal "unknown").
        let info = VersionInfo::py_current();
        assert!(
            !info.git_sha.is_empty(),
            "git_sha must never be empty (falls back to \"unknown\")"
        );
    }
}
