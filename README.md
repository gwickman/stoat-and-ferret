# stoat-and-ferret

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

[Alpha] AI-driven video editor with hybrid Python/Rust architecture - not production ready.

**v092 (R3 Wave 7 + Wave D + TTS P1 Riders):** Subtitle builders — `SubtitleScriptBuilder` (timed drawtext caption chains), `BurnedSubtitleBuilder` (SRT/ASS sidecar burn-in via FFmpeg subtitles/ass filters), soft subtitle embedding (`SoftSubtitleSpec` in `RenderPlanSettings` for MP4/MKV native tracks with BCP-47 → ISO-639 mapping); TTS P1 hotfixes — `TtsCueResponse.audio_path` schema repair (BL-577), source-audio amix preservation in TTS renders (BL-578); `docs/STATUS.md` consolidated as sole canonical status file (BL-556). (PRs #694–#700.) See [CHANGELOG.md](docs/CHANGELOG.md) for release details.
