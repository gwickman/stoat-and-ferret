# 006 Critical Thinking — v012 API Surface & Bindings Cleanup

Reviewed all 6 risks from Task 005's logical design, investigated 3 resolvable risks through codebase analysis and Phase 3 scope review, and produced a refined design with 2 concrete design changes and 1 resolved risk downgrade.

## Risks Investigated

- **Total risks**: 6
- **Investigate now**: 3 (Phase 3 binding needs, ClipPairSelector UX, stub regeneration)
- **Accept with mitigation**: 2 (parity test removal, Edit tool non-unique matches)
- **Accept (known gap)**: 1 (C4 documentation drift)

## Resolutions

1. **Phase 3 binding needs resolved**: Phase 3 scope (8 milestones in roadmap) does not require Python-level access to any of the 11 removed bindings. Rust-internal implementations remain intact. Risk downgraded from medium/unverified to low/resolved.
2. **ClipPairSelector replaced with extended ClipSelector**: Extending the existing component with optional pair-mode props is simpler (~30-40 lines vs ~80-120 new component) and avoids code duplication.
3. **Stub verification gap identified**: verify_stubs.py only checks one direction (generated -> manual). Added explicit grep verification step to binding trim features to catch stale manual stub entries.

## Design Changes

1. **Theme 02 / Feature 001**: Replaced separate `ClipPairSelector` component with pair-mode extension of existing `ClipSelector`. Reduces component count and maintenance burden.
2. **Theme 01 / Features 002, 003**: Added post-removal stub grep verification as explicit acceptance criteria (AC #6 in each feature).

## Remaining TBDs

- None. All risks either resolved or have documented mitigations. No items require runtime testing beyond standard CI verification.

## Confidence Assessment

**High confidence**. All 6 risks are addressed with evidence-backed resolutions or explicit mitigations. The design changes are minor refinements that improve implementation quality without altering scope. All 5 backlog items (BL-061, BL-066, BL-067, BL-068, BL-079) remain fully covered with no deferrals.
