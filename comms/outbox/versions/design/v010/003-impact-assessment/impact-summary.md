# Impact Summary — v010

## Substantial Impacts (feature scope)

These impacts require dedicated design attention and should be scoped as features or explicit sub-tasks during logical design.

1. **Jobs router does not wire progress field** (#1) — `jobs.py` never passes `progress` from `JobResult` to `JobStatusResponse`. Without fixing this, BL-073's progress tracking is invisible to the API. *Owning feature: BL-073*

2. **InMemoryJobQueue missing new protocol methods** (#2) — The test-double `InMemoryJobQueue` must gain `set_progress()` and `cancel()` to match the extended `AsyncJobQueue` protocol. *Owning feature: BL-073, BL-074*

3. **Scan handler has no cancellation check** (#4) — The file iteration loop in `scan_directory()` has no checkpoint where a cancellation flag is inspected. BL-074's cancel mechanism is ineffective without this. *Owning feature: BL-074*

4. **Scan handler has no progress reporting call** (#5) — The scan loop processes files without ever calling `set_progress()`. BL-073's progress infrastructure is unused without this. *Owning feature: BL-073*

5. **Handler signature lacks job_id context** (#6) — Handlers receive `(job_type, payload)` but `set_progress(job_id, value)` requires the job_id. A design decision is needed: extend handler signature, wrap in a context object, or provide a callback. *Owning feature: BL-073*

6. **ScanModal cancel button non-functional during scan** (#7) — The cancel button is disabled while scanning and calls `onClose` rather than a cancel API. BL-074 must enable it and wire it to the new cancel endpoint. *Owning feature: BL-074*

## Small Impacts (sub-task scope)

These can be handled as sub-tasks within the features that cause them.

7. **Scan service must await async ffprobe** (#3) — `scan.py:154` calls `ffprobe_video()` synchronously; after BL-072, this becomes an await call. *Owning feature: BL-072*

8. **JobStatus enum needs CANCELLED value** (#8) — No enum member for cancelled state. *Owning feature: BL-074*

9. **C4 ffmpeg doc stale** (#9) — `ffprobe_video` documented as sync with subprocess dependency. *Owning feature: BL-072*

10. **C4 jobs doc incomplete** (#10) — Missing new queue methods and fields. *Owning feature: BL-073, BL-074*

11. **C4 schemas doc incomplete** (#11) — Missing cancelled status and progress semantics. *Owning feature: BL-073, BL-074*

12. **API reference incomplete** (#12) — Progress and cancel endpoint not documented. *Owning feature: BL-073, BL-074*

13. **Rendering guide cancel endpoint inconsistency** (#13) — Planned render cancel may overlap with generic cancel. *Owning feature: BL-074*

14. **API specification design doc missing cancel endpoint** (#14) — No generic job cancel in design spec. *Owning feature: BL-074*

15. **CHANGELOG needs v010 entries** (#15) — Standard post-implementation task. *Owning feature: All*

16. **CI workflow needs blocking-call step** (#16) — New quality gate needs CI integration. *Owning feature: BL-077*

17. **Test fixtures need protocol updates** (#17) — InMemoryJobQueue instances across 6 conftest files. *Owning feature: BL-073, BL-074*

18. **Test mocks may need signature updates** (#18) — ffprobe_video mock targets across test files. *Owning feature: BL-072*

## Cross-Version Impacts (backlog scope)

None identified. All impacts are addressable within v010's scope.
