# FFmpeg Metrics

**Source:** `src/stoat_ferret/ffmpeg/metrics.py`
**Component:** FFmpeg Integration

## Purpose

Defines Prometheus metrics for monitoring FFmpeg execution performance and health. Provides metrics for tracking total execution counts, execution duration distributions, and active process counts.

## Public Interface

### Metrics (Module-Level Constants)

- `ffmpeg_executions_total: Counter`: Total FFmpeg command executions
  - Labels: `status` (values: "success", "failure")
  - Type: Prometheus Counter
  - Usage: Increment with `.labels(status=...).inc()` to track execution outcomes

- `ffmpeg_execution_duration_seconds: Histogram`: FFmpeg command execution duration in seconds
  - Buckets: [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0]
  - Type: Prometheus Histogram
  - Usage: Observe with `.observe(seconds)` to record execution duration

- `ffmpeg_active_processes: Gauge`: Number of currently running FFmpeg processes
  - Type: Prometheus Gauge
  - Usage: Increment with `.inc()` on start, decrement with `.dec()` on completion

## Dependencies

### Internal Dependencies

None

### External Dependencies

- `prometheus_client`: Prometheus metrics library
  - `Counter`: For counting total executions
  - `Gauge`: For tracking active processes
  - `Histogram`: For distribution of execution durations

## Key Implementation Details

### Metric Design

Three complementary metrics provide comprehensive FFmpeg execution observability:

1. **Counter (`ffmpeg_executions_total`)**: Cumulative success/failure counts
   - Labeled by status to distinguish successful and failed executions
   - Used for calculating success rate (successes / total)
   - Increases monotonically

2. **Histogram (`ffmpeg_execution_duration_seconds`)**: Execution time distribution
   - Buckets span 100ms to 5 minutes (common FFmpeg operation range)
   - Enables percentile analysis (p50, p95, p99 latencies)
   - Automatically computes count and sum for averages
   - Useful for performance trends and SLO monitoring

3. **Gauge (`ffmpeg_active_processes`)**: Real-time concurrent processes
   - Incremented at execution start
   - Decremented at execution completion (success or failure)
   - Reflects current load and potential resource contention
   - Peaks during batch processing

### Metric Naming Convention

All metrics follow the `stoat_ferret_` prefix pattern:
- `stoat_ferret_ffmpeg_executions_total`
- `stoat_ferret_ffmpeg_execution_duration_seconds`
- `stoat_ferret_ffmpeg_active_processes`

This enables:
- Namespace isolation in multi-application Prometheus instances
- Easy filtering and aggregation by subsystem
- Clear association with the stoat-and-ferret project

## Relationships

- **Used by:** ObservableFFmpegExecutor wrapper for metric recording
- **Uses:** Prometheus client library for metric types
