# BL-DRAFT-bl515-asset-library

**Status:** drafted, not filed
**Supersedes / amends:** BL-515 (User-asset library — upload + reference custom PNGs / brand graphics / overlays)
**Evidence:** wellness showcase needed user-supplied images (logo, hypnotherapy spiral); no path exists today.
**Why now:** dependency for BL-511 (image-as-clip) and likely BL-DRAFT-bl513 (procedural shapes saved as assets).

## Problem statement

snf has no concept of a user-asset library. Users cannot upload an image and reference it by ID across projects. The hypnotherapy showcase had to manually drop a `working/hypno/spiral.png` into the local workspace because there was no API path.

## Proposed acceptance criteria

### Schema

1. **Asset record:**
   - `id: UUID`
   - `kind: Literal["image","audio","subtitle","font","lut"]`
   - `file_path: str` (server-side storage location)
   - `original_filename: str`
   - `mime_type: str`
   - `size_bytes: int`
   - `licence: str | None` (user-supplied; for traceability)
   - `tags: list[str]`
   - `uploaded_by_user_id: UUID | None`
   - `created_at: datetime`

### API

2. **POST /assets** — multipart upload, returns asset id.
3. **GET /assets** — paginated list with kind / tag filters.
4. **GET /assets/{id}** — metadata.
5. **GET /assets/{id}/file** — download.
6. **DELETE /assets/{id}** — soft delete (mark deleted; do not remove file until orphaned for N days).

### Storage

7. **File storage** under a configurable `assets_dir` (default `working/assets/`). Filenames are content-hashed to deduplicate.
8. **Limits:** max upload size 100 MB. Reject by content-type allow-list per `kind`.

### Cross-cutting

9. **Referencing assets in clips/effects:** existing `source_video_id` extends to `source_asset_id`; `lut3d` builder, `subtitles` builder, etc. take `asset_id` instead of raw paths.
10. **Render-time resolution:** the BL-505 translator resolves `asset_id → file_path` at render time via the asset repository.
11. **Path scope (per codex `14`):** asset resolution returns **raw paths for argv use** (`-i <path>`, `-y <path>`). The BL-499 `emit_filter_option_path` helper is applied ONLY when the asset path flows into a filter-graph option value (lut3d, subtitles, ass, movie). Wiring should make this distinction explicit at the renderer layer, not at the asset library.

### Security ACs (added per codex `14`)

12. **Content-sniff validation.** Server validates the actual file type (e.g. magic bytes via `python-magic` or `infer` crate), NOT just the uploaded MIME extension. Rejects mismatches with a clear 415.
13. **Path traversal hardening.** All filesystem operations resolve under a configured `assets_dir` root. Reject any computed path that escapes the root (test with `../`, absolute paths, symlink chains).
14. **STOAT_* config ownership (per codex `18` Major Risk).** This BL owns `STOAT_ASSETS_DIR` AND `STOAT_ASSETS_MAX_SIZE_BYTES`. Both documented in BOTH `docs/setup/04_configuration.md` AND `docs/manual/configuration-reference.md`. `KNOWN_UNDOCUMENTED_SETTINGS_VARS` stays empty after this BL lands.

14a. **OpenAPI freshness:** PR includes regenerated `gui/openapi.json` (via `uv run python -m scripts.export_openapi`) + `gui/src/generated/api-types.ts` (via `cd gui && npm run generate:types`). CI freshness checks pass.
15. **DB migration idempotency.** The new `assets` table migration is idempotent (re-running is a no-op) and includes downgrade behaviour (drop table if no rows, refuse if rows exist OR offer a flag to truncate).

### Tests

16. Upload+list+download round-trip.
17. Soft-delete invariants — asset still referenced by a clip cannot be hard-deleted.
18. Filename hash dedup — uploading the same file twice returns the same asset id (or a clear "already exists" response).
19. Security suite: traversal attempt, type-mismatch upload, oversize upload, MIME-vs-magic mismatch — all rejected with appropriate status codes.

## Out of scope

- Multi-tenant access control. Per-user scoping is a future concern.
- Versioning.
- Cloud-storage backend (S3/Azure Blob).

## Dependencies

- None hard-blocking. Required by BL-511 (image-as-clip) and ideally BL-DRAFT-bl513 (procedural shapes saved as assets).

## Risks

- Renaming/moving the `assets_dir` should be supported. Make it a config setting; don't hardcode.
- Path escape: when asset paths flow into filter graphs (lut3d, subtitles), apply BL-499 escape policy.
