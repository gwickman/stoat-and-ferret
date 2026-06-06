# stoat-and-ferret

[Alpha] AI-driven video editor with hybrid Python/Rust architecture - not production ready.

**v073 (Render Correctness & Test-Coverage Discharge):** Hoisted total_duration preflight before noop/real split so real-mode renders now reject incomplete plans with 422 (BL-460); fixed -progress pipe:1 flag missing from FFmpeg argv so render progress advances monotonically (BL-394); fixed Python 3.13 async_executor race by replacing communicate() with process.wait() (BL-393); added ConfigDict(extra="forbid") to CreateRenderRequest and RenderPreviewRequest (BL-417); added partial_file_cancel, render_progress_increments, and preview_no_deadlock smoke tests (BL-462); repaired concurrent output-path smoke test (BL-461); corrected smoke-test-harness.md discharge procedures (BL-463). See [CHANGELOG.md](docs/CHANGELOG.md) for release details.
