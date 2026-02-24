## Context

Progress reporting requires knowing both the current position and the total count. Lazy iterators and generators process items one at a time without knowing the total upfront, making accurate percentage-based progress impossible.

## Learning

When adding progress reporting to an operation that uses lazy iteration, pre-collect items into a list first to determine the total count. The cost of collecting upfront (memory for the item list) is typically negligible compared to the per-item processing cost, and it enables accurate `processed / total` progress calculation.

## Evidence

v010 Feature 001 (progress-reporting) changed `scan_directory()` from lazy `root.glob()` iteration to pre-collecting video files into a list:
- Before: `for path in root.glob("**/*"):` — no total count available
- After: `video_files = [p for p in root.glob("**/*") if p.suffix in VIDEO_EXTENSIONS]` — total known
- Progress callback: `progress_callback(processed / len(video_files))`

The pre-collection cost was minimal (just path objects in memory) while enabling real-time 0.0–1.0 progress updates per file.

## Application

When adding progress reporting to existing iterative operations:
1. Collect the work items into a list/sequence before starting processing
2. Calculate progress as `completed_count / total_count`
3. This pattern is appropriate when the collection is much cheaper than per-item processing
4. For very large collections where memory is a concern, consider a two-pass approach: first count, then process