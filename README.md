# stoat-and-ferret

[Alpha] AI-driven video editor with hybrid Python/Rust architecture - not production ready.

**v076 (Release 2, Wave 1 — Verify & Deliver):** Added QC infrastructure — `qc.*` event namespace, 5 Rust FFmpeg-output parsers with PyO3 bindings, QCService 11-pass analysis orchestrator, `/qc` API endpoints with Alembic migration (BL-423, BL-424, PRs #526–#529); added delivery profiles model + CRUD API + QC-gated export pipeline (BL-425, PR #530); added chapter/clip metadata embedding architecture with passthrough hooks (BL-426, PR #531); added OC→QC assertion mapping infrastructure (14/17 outcomes mapped), golden regression fixture scaffold, chatbot scenario acceptance tests, browser UAT journeys, and UC-MEDIA-MPS-001 acceptance harness scaffold (BL-427, BL-456–BL-459). FFmpeg-gated ACs deferred with discharge plans. See [CHANGELOG.md](docs/CHANGELOG.md) for release details.
