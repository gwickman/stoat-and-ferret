# stoat-and-ferret

[Alpha] AI-driven video editor with hybrid Python/Rust architecture - not production ready.

**v074 (Agent-Surface Accuracy & Architecture Hygiene):** Hoisted render settings key validation to router level so `POST /api/v1/render` returns 422 PREFLIGHT_FAILED when `render_plan.settings` is absent or malformed (BL-465); fixed operator-guide.md, 03_api-reference.md, and prompt-recipes.md render payload examples (BL-375, BL-464, BL-402); added `GET /clips/{cid}` and `GET /clips/{cid}/effects` endpoints (BL-409); added 8 API ergonomics fixes including `ClipResponse.effects` default, waveform async-id string, and EFFECT_NOT_FOUND enumeration (BL-405); added `subtitle_count` and `data_count` to VideoResponse schema with Alembic migration (BL-408); refreshed C4 docs for StaleRenderSweeper and updated smoke test inventory from 84 to 191 tests (BL-399, BL-400); added UAT runner subprocess timeout (BL-398). See [CHANGELOG.md](docs/CHANGELOG.md) for release details.
