//! Batch render progress aggregation.
//!
//! Provides a pure function to compute overall batch render progress
//! from individual job states.
//!
//! # Examples
//!
//! ```
//! use stoat_ferret_core::batch::{BatchJobStatus, calculate_batch_progress};
//!
//! let jobs = vec![
//!     BatchJobStatus::Pending,
//!     BatchJobStatus::InProgress(0.5),
//!     BatchJobStatus::Completed,
//!     BatchJobStatus::Failed,
//! ];
//! let progress = calculate_batch_progress(&jobs);
//! assert_eq!(progress.total_jobs, 4);
//! assert_eq!(progress.completed_jobs, 1);
//! assert_eq!(progress.failed_jobs, 1);
//! ```

use pyo3::prelude::*;
use pyo3_stub_gen::derive::gen_stub_pyclass;

/// Status of an individual batch render job.
///
/// Each variant represents a distinct job state. `InProgress` carries
/// a progress value in the range [0.0, 1.0].
#[derive(Debug, Clone, PartialEq)]
pub enum BatchJobStatus {
    /// Job is queued but has not started.
    Pending,
    /// Job is actively rendering with progress in [0.0, 1.0].
    InProgress(f64),
    /// Job finished successfully.
    Completed,
    /// Job failed.
    Failed,
}

impl BatchJobStatus {
    /// Returns the progress value for this job status.
    ///
    /// - Pending: 0.0
    /// - InProgress(p): p (clamped to [0.0, 1.0])
    /// - Completed: 1.0
    /// - Failed: 0.0
    fn progress(&self) -> f64 {
        match self {
            BatchJobStatus::Pending => 0.0,
            BatchJobStatus::InProgress(p) => p.clamp(0.0, 1.0),
            BatchJobStatus::Completed => 1.0,
            BatchJobStatus::Failed => 0.0,
        }
    }
}

/// Aggregated progress for a batch of render jobs.
///
/// Reports counts and an overall progress value computed as the mean
/// of individual job progress values.
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone, PartialEq)]
pub struct BatchProgress {
    /// Total number of jobs in the batch.
    #[pyo3(get)]
    pub total_jobs: usize,
    /// Number of jobs that completed successfully.
    #[pyo3(get)]
    pub completed_jobs: usize,
    /// Number of jobs that failed.
    #[pyo3(get)]
    pub failed_jobs: usize,
    /// Overall progress as mean of individual job progress values (0.0-1.0).
    #[pyo3(get)]
    pub overall_progress: f64,
}

#[pymethods]
impl BatchProgress {
    /// Creates a new BatchProgress.
    ///
    /// Args:
    ///     total_jobs: Total number of jobs.
    ///     completed_jobs: Number of completed jobs.
    ///     failed_jobs: Number of failed jobs.
    ///     overall_progress: Overall progress (0.0-1.0).
    #[new]
    fn py_new(
        total_jobs: usize,
        completed_jobs: usize,
        failed_jobs: usize,
        overall_progress: f64,
    ) -> Self {
        Self {
            total_jobs,
            completed_jobs,
            failed_jobs,
            overall_progress,
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "BatchProgress(total={}, completed={}, failed={}, progress={:.3})",
            self.total_jobs, self.completed_jobs, self.failed_jobs, self.overall_progress
        )
    }
}

/// PyO3-friendly wrapper for [`BatchJobStatus`].
///
/// Since Rust enums with data cannot use `#[pyclass(eq, eq_int)]`,
/// this struct wraps the internal enum and exposes factory methods.
#[gen_stub_pyclass]
#[pyclass(name = "BatchJobStatus")]
#[derive(Debug, Clone)]
pub struct PyBatchJobStatus {
    pub(crate) inner: BatchJobStatus,
}

#[pymethods]
impl PyBatchJobStatus {
    /// Creates a Pending job status.
    #[staticmethod]
    #[pyo3(name = "pending")]
    fn py_pending() -> Self {
        Self {
            inner: BatchJobStatus::Pending,
        }
    }

    /// Creates an InProgress job status with the given progress (0.0-1.0).
    ///
    /// Args:
    ///     progress: Current progress value between 0.0 and 1.0.
    #[staticmethod]
    #[pyo3(name = "in_progress")]
    fn py_in_progress(progress: f64) -> Self {
        Self {
            inner: BatchJobStatus::InProgress(progress),
        }
    }

    /// Creates a Completed job status.
    #[staticmethod]
    #[pyo3(name = "completed")]
    fn py_completed() -> Self {
        Self {
            inner: BatchJobStatus::Completed,
        }
    }

    /// Creates a Failed job status.
    #[staticmethod]
    #[pyo3(name = "failed")]
    fn py_failed() -> Self {
        Self {
            inner: BatchJobStatus::Failed,
        }
    }

    /// Returns the progress value for this status.
    #[pyo3(name = "progress")]
    fn py_progress(&self) -> f64 {
        self.inner.progress()
    }

    fn __repr__(&self) -> String {
        match &self.inner {
            BatchJobStatus::Pending => "BatchJobStatus.pending()".to_string(),
            BatchJobStatus::InProgress(p) => format!("BatchJobStatus.in_progress({p})"),
            BatchJobStatus::Completed => "BatchJobStatus.completed()".to_string(),
            BatchJobStatus::Failed => "BatchJobStatus.failed()".to_string(),
        }
    }
}

/// Calculates aggregated batch progress from individual job statuses.
///
/// The overall progress is the mean of individual job progress values:
/// - Pending: 0.0
/// - InProgress(p): p (clamped to [0.0, 1.0])
/// - Completed: 1.0
/// - Failed: 0.0
///
/// Returns a [`BatchProgress`] with counts and the mean progress.
/// An empty job list returns a BatchProgress with 0 total_jobs and 0.0 progress.
pub fn calculate_batch_progress(jobs: &[BatchJobStatus]) -> BatchProgress {
    if jobs.is_empty() {
        return BatchProgress {
            total_jobs: 0,
            completed_jobs: 0,
            failed_jobs: 0,
            overall_progress: 0.0,
        };
    }

    let total_jobs = jobs.len();
    let mut completed_jobs = 0usize;
    let mut failed_jobs = 0usize;
    let mut progress_sum = 0.0f64;

    for job in jobs {
        match job {
            BatchJobStatus::Completed => completed_jobs += 1,
            BatchJobStatus::Failed => failed_jobs += 1,
            _ => {}
        }
        progress_sum += job.progress();
    }

    BatchProgress {
        total_jobs,
        completed_jobs,
        failed_jobs,
        overall_progress: progress_sum / total_jobs as f64,
    }
}

// ---------------------------------------------------------------------------
// PyO3 function binding
// ---------------------------------------------------------------------------

/// Calculates aggregated batch progress from individual job statuses.
///
/// Args:
///     jobs: List of BatchJobStatus objects representing individual job states.
///
/// Returns:
///     BatchProgress with total_jobs, completed_jobs, failed_jobs, and overall_progress.
#[pyfunction]
#[pyo3(name = "calculate_batch_progress")]
fn py_calculate_batch_progress(jobs: Vec<PyBatchJobStatus>) -> BatchProgress {
    let statuses: Vec<BatchJobStatus> = jobs.into_iter().map(|j| j.inner).collect();
    calculate_batch_progress(&statuses)
}

/// Registers batch progress types and functions with the Python module.
pub fn register(m: &Bound<PyModule>) -> PyResult<()> {
    m.add_class::<BatchProgress>()?;
    m.add_class::<PyBatchJobStatus>()?;
    m.add_function(wrap_pyfunction!(py_calculate_batch_progress, m)?)?;
    Ok(())
}

// ---------------------------------------------------------------------------
// Unit tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    // -- BatchJobStatus progress values --

    #[test]
    fn pending_progress_is_zero() {
        assert!((BatchJobStatus::Pending.progress() - 0.0).abs() < 1e-9);
    }

    #[test]
    fn in_progress_returns_value() {
        assert!((BatchJobStatus::InProgress(0.5).progress() - 0.5).abs() < 1e-9);
    }

    #[test]
    fn in_progress_clamps_above_one() {
        assert!((BatchJobStatus::InProgress(1.5).progress() - 1.0).abs() < 1e-9);
    }

    #[test]
    fn in_progress_clamps_below_zero() {
        assert!((BatchJobStatus::InProgress(-0.5).progress() - 0.0).abs() < 1e-9);
    }

    #[test]
    fn completed_progress_is_one() {
        assert!((BatchJobStatus::Completed.progress() - 1.0).abs() < 1e-9);
    }

    #[test]
    fn failed_progress_is_zero() {
        assert!((BatchJobStatus::Failed.progress() - 0.0).abs() < 1e-9);
    }

    // -- Empty job list --

    #[test]
    fn empty_jobs_returns_zero_progress() {
        let result = calculate_batch_progress(&[]);
        assert_eq!(result.total_jobs, 0);
        assert_eq!(result.completed_jobs, 0);
        assert_eq!(result.failed_jobs, 0);
        assert!((result.overall_progress - 0.0).abs() < 1e-9);
    }

    // -- Single job --

    #[test]
    fn single_pending_job() {
        let result = calculate_batch_progress(&[BatchJobStatus::Pending]);
        assert_eq!(result.total_jobs, 1);
        assert_eq!(result.completed_jobs, 0);
        assert_eq!(result.failed_jobs, 0);
        assert!((result.overall_progress - 0.0).abs() < 1e-9);
    }

    #[test]
    fn single_completed_job() {
        let result = calculate_batch_progress(&[BatchJobStatus::Completed]);
        assert_eq!(result.total_jobs, 1);
        assert_eq!(result.completed_jobs, 1);
        assert_eq!(result.failed_jobs, 0);
        assert!((result.overall_progress - 1.0).abs() < 1e-9);
    }

    #[test]
    fn single_failed_job() {
        let result = calculate_batch_progress(&[BatchJobStatus::Failed]);
        assert_eq!(result.total_jobs, 1);
        assert_eq!(result.completed_jobs, 0);
        assert_eq!(result.failed_jobs, 1);
        assert!((result.overall_progress - 0.0).abs() < 1e-9);
    }

    #[test]
    fn single_in_progress_job() {
        let result = calculate_batch_progress(&[BatchJobStatus::InProgress(0.75)]);
        assert_eq!(result.total_jobs, 1);
        assert_eq!(result.completed_jobs, 0);
        assert_eq!(result.failed_jobs, 0);
        assert!((result.overall_progress - 0.75).abs() < 1e-9);
    }

    // -- Mixed states --

    #[test]
    fn mixed_states_mean_progress() {
        // [Pending(0.0), InProgress(0.5), Completed(1.0)] -> mean = 0.5
        let jobs = vec![
            BatchJobStatus::Pending,
            BatchJobStatus::InProgress(0.5),
            BatchJobStatus::Completed,
        ];
        let result = calculate_batch_progress(&jobs);
        assert_eq!(result.total_jobs, 3);
        assert_eq!(result.completed_jobs, 1);
        assert_eq!(result.failed_jobs, 0);
        assert!((result.overall_progress - 0.5).abs() < 1e-9);
    }

    #[test]
    fn all_completed() {
        let jobs = vec![
            BatchJobStatus::Completed,
            BatchJobStatus::Completed,
            BatchJobStatus::Completed,
        ];
        let result = calculate_batch_progress(&jobs);
        assert_eq!(result.total_jobs, 3);
        assert_eq!(result.completed_jobs, 3);
        assert_eq!(result.failed_jobs, 0);
        assert!((result.overall_progress - 1.0).abs() < 1e-9);
    }

    #[test]
    fn all_failed() {
        let jobs = vec![
            BatchJobStatus::Failed,
            BatchJobStatus::Failed,
            BatchJobStatus::Failed,
        ];
        let result = calculate_batch_progress(&jobs);
        assert_eq!(result.total_jobs, 3);
        assert_eq!(result.completed_jobs, 0);
        assert_eq!(result.failed_jobs, 3);
        assert!((result.overall_progress - 0.0).abs() < 1e-9);
    }

    #[test]
    fn mixed_with_failed() {
        // [Completed(1.0), Failed(0.0), InProgress(0.5), Pending(0.0)] -> mean = 1.5/4 = 0.375
        let jobs = vec![
            BatchJobStatus::Completed,
            BatchJobStatus::Failed,
            BatchJobStatus::InProgress(0.5),
            BatchJobStatus::Pending,
        ];
        let result = calculate_batch_progress(&jobs);
        assert_eq!(result.total_jobs, 4);
        assert_eq!(result.completed_jobs, 1);
        assert_eq!(result.failed_jobs, 1);
        assert!((result.overall_progress - 0.375).abs() < 1e-9);
    }

    // -- BatchProgress repr --

    #[test]
    fn batch_progress_repr() {
        let progress = BatchProgress {
            total_jobs: 3,
            completed_jobs: 1,
            failed_jobs: 1,
            overall_progress: 0.5,
        };
        let repr = progress.__repr__();
        assert!(repr.contains("total=3"));
        assert!(repr.contains("completed=1"));
        assert!(repr.contains("failed=1"));
        assert!(repr.contains("0.500"));
    }

    // -- PyBatchJobStatus repr --

    #[test]
    fn py_status_repr() {
        let pending = PyBatchJobStatus {
            inner: BatchJobStatus::Pending,
        };
        assert_eq!(pending.__repr__(), "BatchJobStatus.pending()");

        let in_progress = PyBatchJobStatus {
            inner: BatchJobStatus::InProgress(0.5),
        };
        assert_eq!(in_progress.__repr__(), "BatchJobStatus.in_progress(0.5)");

        let completed = PyBatchJobStatus {
            inner: BatchJobStatus::Completed,
        };
        assert_eq!(completed.__repr__(), "BatchJobStatus.completed()");

        let failed = PyBatchJobStatus {
            inner: BatchJobStatus::Failed,
        };
        assert_eq!(failed.__repr__(), "BatchJobStatus.failed()");
    }
}

// ---------------------------------------------------------------------------
// Property-based tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod proptests {
    use super::*;
    use proptest::prelude::*;

    fn arb_job_status() -> impl Strategy<Value = BatchJobStatus> {
        prop_oneof![
            Just(BatchJobStatus::Pending),
            (0.0f64..=1.0).prop_map(BatchJobStatus::InProgress),
            Just(BatchJobStatus::Completed),
            Just(BatchJobStatus::Failed),
        ]
    }

    proptest! {
        #[test]
        fn no_panics_random_jobs(
            jobs in proptest::collection::vec(arb_job_status(), 0..=100),
        ) {
            let _ = calculate_batch_progress(&jobs);
        }

        #[test]
        fn progress_in_valid_range(
            jobs in proptest::collection::vec(arb_job_status(), 0..=100),
        ) {
            let result = calculate_batch_progress(&jobs);
            prop_assert!(result.overall_progress >= 0.0, "Progress must be >= 0.0: {}", result.overall_progress);
            prop_assert!(result.overall_progress <= 1.0, "Progress must be <= 1.0: {}", result.overall_progress);
        }

        #[test]
        fn counts_consistent(
            jobs in proptest::collection::vec(arb_job_status(), 0..=100),
        ) {
            let result = calculate_batch_progress(&jobs);
            prop_assert_eq!(result.total_jobs, jobs.len());
            prop_assert!(result.completed_jobs + result.failed_jobs <= result.total_jobs,
                "completed ({}) + failed ({}) must be <= total ({})",
                result.completed_jobs, result.failed_jobs, result.total_jobs);
        }

        #[test]
        fn all_completed_gives_full_progress(
            count in 1usize..=50,
        ) {
            let jobs: Vec<BatchJobStatus> = vec![BatchJobStatus::Completed; count];
            let result = calculate_batch_progress(&jobs);
            prop_assert!((result.overall_progress - 1.0).abs() < 1e-9,
                "All completed should give 1.0 progress, got {}", result.overall_progress);
        }

        #[test]
        fn all_failed_gives_zero_progress(
            count in 1usize..=50,
        ) {
            let jobs: Vec<BatchJobStatus> = vec![BatchJobStatus::Failed; count];
            let result = calculate_batch_progress(&jobs);
            prop_assert!((result.overall_progress - 0.0).abs() < 1e-9,
                "All failed should give 0.0 progress, got {}", result.overall_progress);
        }
    }
}
