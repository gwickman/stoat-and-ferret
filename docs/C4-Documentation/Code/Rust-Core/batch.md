# C4 Code Level: Batch Module

**Source:** `rust/stoat_ferret_core/src/batch.rs`
**Component:** Rust Core

## Purpose

Provides pure functions for computing overall batch render progress from individual job states. Aggregates progress information from multiple rendering jobs for progress bar and status display in the UI.

## Public Interface

### Enums

#### `BatchJobStatus`
Represents the state of an individual batch render job.

**Variants (Rust enum):**
- `Pending` — Job queued but not yet started (progress: 0.0)
- `InProgress(f64)` — Job rendering with progress in [0.0, 1.0] (progress: clamped value)
- `Completed` — Job finished successfully (progress: 1.0)
- `Failed` — Job failed (progress: 0.0)

**Methods:**
- `progress() -> f64` — Get progress value for this status

#### `PyBatchJobStatus` (PyO3 Wrapper)
Python-accessible wrapper for BatchJobStatus enum (Rust enums with data can't use eq derivation for PyO3).

**PyO3 Static Factory Methods:**
- `BatchJobStatus.pending() -> PyBatchJobStatus` — Create Pending status
- `BatchJobStatus.in_progress(progress: float) -> PyBatchJobStatus` — Create InProgress with progress value
- `BatchJobStatus.completed() -> PyBatchJobStatus` — Create Completed status
- `BatchJobStatus.failed() -> PyBatchJobStatus` — Create Failed status

**PyO3 Instance Methods:**
- `progress() -> float` — Get progress value for this status

### Structs (PyO3 Classes)

#### `BatchProgress`
Aggregated progress for a batch of render jobs.

**Fields:**
- `total_jobs: usize` — Total number of jobs in batch (PyO3: `#[pyo3(get)]`)
- `completed_jobs: usize` — Number of successfully completed jobs (PyO3: `#[pyo3(get)]`)
- `failed_jobs: usize` — Number of failed jobs (PyO3: `#[pyo3(get)]`)
- `overall_progress: f64` — Overall progress as mean of individual job progress (0.0-1.0) (PyO3: `#[pyo3(get)]`)

**Construction:**
- `BatchProgress::new(total_jobs: usize, completed_jobs: usize, failed_jobs: usize, overall_progress: f64) -> Self`

**PyO3 Constructor:**
- `BatchProgress(total_jobs: int, completed_jobs: int, failed_jobs: int, overall_progress: float) -> BatchProgress`

### Functions

#### `calculate_batch_progress(jobs: &[BatchJobStatus]) -> BatchProgress`

**Purpose:** Compute aggregated batch progress from individual job statuses.

**Algorithm:**
1. Return early with all-zero progress if jobs list is empty
2. Count total, completed, and failed jobs
3. Calculate progress_sum as sum of individual job progress values
4. Return BatchProgress with:
   - total_jobs = jobs.len()
   - completed_jobs = count of Completed variants
   - failed_jobs = count of Failed variants
   - overall_progress = progress_sum / total_jobs

**Progress Values Used:**
- Pending → 0.0
- InProgress(p) → p clamped to [0.0, 1.0]
- Completed → 1.0
- Failed → 0.0

**Returns:** `BatchProgress` with aggregated counts and mean progress

#### `py_calculate_batch_progress(jobs: Vec<PyBatchJobStatus>) -> BatchProgress`

**PyO3 binding of `calculate_batch_progress`.**

**Python function signature:**
```python
def calculate_batch_progress(jobs: List[PyBatchJobStatus]) -> BatchProgress
```

## Dependencies

### Internal Crate Dependencies

None — batch module is self-contained with no dependencies on other crate modules.

### External Crate Dependencies

- **pyo3** — PyO3 Python bindings
- **pyo3_stub_gen** — Stub generation support
- **proptest** — Property-based testing (test-only)

## Key Implementation Details

### Progress Calculation Strategy

**Mean-based aggregation:**
```
overall_progress = (p1 + p2 + ... + pn) / n
```

Where each job's progress is determined by its status. This provides a smooth, linear progress indicator that:
- Starts at 0.0 when all jobs are pending
- Increases monotonically as jobs complete
- Reaches 1.0 when all jobs are completed
- Accounts for failed jobs as 0.0 progress

### Progress Clamping

InProgress values are clamped to [0.0, 1.0] to handle edge cases:
```rust
match self {
    InProgress(p) => p.clamp(0.0, 1.0),
    ...
}
```

This prevents negative or >100% progress from skewing overall progress.

### Fail/Completion Counting

Counts are tracked separately:
- `completed_jobs` — Only counts Completed variant
- `failed_jobs` — Only counts Failed variant
- `total_jobs` — Always jobs.len()

This allows UI to display:
- "5/10 completed, 1 failed, 4 in progress"
- Progress bar showing overall_progress percentage
- Status indicators for each job

### Empty Batch Handling

Empty batch (0 jobs) returns:
```rust
BatchProgress {
    total_jobs: 0,
    completed_jobs: 0,
    failed_jobs: 0,
    overall_progress: 0.0,  // not NaN
}
```

This avoids division by zero and provides sensible defaults.

## Relationships

**Used by:**
- Python UI progress display — Shows overall render progress and job status
- Batch render management — Aggregates progress from render worker threads
- Progress callbacks — Reports progress updates to WebSocket or polling clients

**Uses:**
- (No internal dependencies)

## Testing

Comprehensive test suite with 40+ tests including:

1. **BatchJobStatus progress values (6 tests):**
   - Pending returns 0.0
   - InProgress returns the value (0.5 → 0.5)
   - InProgress clamps > 1.0 (1.5 → 1.0)
   - InProgress clamps < 0.0 (-0.5 → 0.0)
   - Completed returns 1.0
   - Failed returns 0.0

2. **Empty job list (1 test):**
   - Returns zero progress with all-zero counts

3. **Single job tests (4 tests):**
   - Single pending → 0.0 progress
   - Single completed → 1.0 progress
   - Single failed → 0.0 progress
   - Single in-progress → that progress value

4. **Mixed state tests (3 tests):**
   - [Pending, InProgress(0.5), Completed] → 0.5 average
   - All completed → 1.0 progress
   - All failed → 0.0 progress
   - Mixed with failed → correct mean

5. **BatchProgress repr test (1 test):**
   - __repr__ format: "BatchProgress(total=3, completed=1, failed=1, progress=0.500)"

6. **PyBatchJobStatus repr tests (4 tests):**
   - pending() → "BatchJobStatus.pending()"
   - in_progress(0.5) → "BatchJobStatus.in_progress(0.5)"
   - completed() → "BatchJobStatus.completed()"
   - failed() → "BatchJobStatus.failed()"

7. **Property-based tests (6 proptests):**
   - No panics with random job lists (0-100 jobs)
   - Progress always in [0.0, 1.0]
   - Counts are consistent (completed + failed ≤ total)
   - All completed → 1.0 progress
   - All failed → 0.0 progress

## Notes

- **Status Distinction:** BatchJobStatus tracks current state; once Completed or Failed, status doesn't revert. If a job needs to restart, create new status.
- **Progress Meaning:** overall_progress is the mean, not a weighted score. A job completing has the same impact as another halfway done.
- **Real-Time Updates:** Designed for periodic updates from render workers; Python code sends current job statuses for aggregation.
- **No Persistence:** Progress calculation is pure and stateless. Caller responsible for tracking job states over time.
- **Failure Transparency:** Failed jobs contribute 0.0 to progress mean. They count in failed_jobs separately so UI can highlight failures.

## Example Usage

```python
from stoat_ferret_core import (
    BatchJobStatus, calculate_batch_progress
)

# Simulate render job states
jobs = [
    BatchJobStatus.pending(),
    BatchJobStatus.in_progress(0.5),
    BatchJobStatus.completed(),
    BatchJobStatus.failed(),
]

# Calculate aggregated progress
progress = calculate_batch_progress(jobs)

print(f"Total: {progress.total_jobs}")           # 4
print(f"Completed: {progress.completed_jobs}")   # 1
print(f"Failed: {progress.failed_jobs}")         # 1
print(f"Overall: {progress.overall_progress}")   # 0.375 (mean of [0.0, 0.5, 1.0, 0.0])

# Update one job and recalculate
jobs[1] = BatchJobStatus.in_progress(0.75)
progress = calculate_batch_progress(jobs)
print(f"Updated: {progress.overall_progress}")   # 0.4375 (mean of [0.0, 0.75, 1.0, 0.0])
```

## UI Integration Pattern

```python
# In Python render manager
def on_job_status_update(job_states):
    # job_states = [status for each render job]
    progress = calculate_batch_progress(job_states)

    # Update UI
    progress_bar.set_value(progress.overall_progress * 100)
    status_label.setText(
        f"{progress.completed_jobs}/{progress.total_jobs} complete"
    )
    if progress.failed_jobs > 0:
        error_label.setText(f"{progress.failed_jobs} failed")
```
