# stoat-and-ferret

[Alpha] AI-driven video editor with hybrid Python/Rust architecture - not production ready.

**v080 (R2 Wave 4 — Editing & Time):** Added ReverseBuilder with `STOAT_REVERSE_MAX_DURATION_S` buffer-limit guard (BL-444, PR #580), universal range-window `WindowSpec` on all effects (BL-446, PR #581), VariableSpeedBuilder with segmented-concat + per-segment pitch control (BL-447, PR #582), FramerateConvertBuilder with blend/optical-flow/duplicate modes (BL-448, PR #583), FreezeFrameBuilder via freezeframes+tpad (BL-449, PR #584); `POST /clips/{id}/split` atomic endpoint + GUI `RazorTool.tsx` (BL-445, PR #586); UAT journeys 701–706 + acceptance harness `uc_media_mps_001_harness.py` (BL-457, BL-459, PRs #589–#590); golden QC regression suite with real FFmpeg measurements (BL-458, PR #588); smoke test harness guide update (PR #591); 3069 tests passing. 8 FFmpeg/UAT-gated ACs deferred with discharge plans. See [CHANGELOG.md](docs/CHANGELOG.md) for release details.
