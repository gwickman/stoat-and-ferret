# Learnings Summary - Applicable to v006

25 total learnings in the project repository. The following are directly applicable to v006 effects engine design.

## High Relevance

### LRN-001: PyO3 Method Chaining with PyRefMut
- **Insight:** Use `PyRefMut<'_, Self>` return type for fluent builder APIs that work identically in Rust and Python
- **Applicability:** All v006 Rust builders (expression engine BL-037, drawtext BL-040, speed control BL-041, composition BL-039) should use this pattern for their PyO3 bindings

### LRN-011: Python Business Logic, Rust Input Safety
- **Insight:** Rust owns input sanitization and type safety; Python owns business policy and domain rules
- **Applicability:** Filter expression construction, graph validation, and text escaping belong in Rust. Effect registration, API routing, clip model updates, and business rules belong in Python. Clear boundary for BL-042 and BL-043.

### LRN-012: PyO3 FFI Overhead for Simple Operations
- **Insight:** PyO3 FFI makes Rust 7-10x slower for simple operations; Rust wins for string-heavy processing (1.9x faster)
- **Applicability:** Filter string generation (string-heavy) justifies Rust. Simple validation or parameter checking could stay in Python. Don't over-optimize by pushing everything to Rust.

### LRN-016: Validate Acceptance Criteria Against Codebase During Design
- **Insight:** Check that referenced domain models/APIs exist before finalizing requirements
- **Applicability:** BL-043 references storing effects on the clip model, but no effect field exists yet. Design must explicitly plan the model extension. BL-042 references a registry that doesn't exist — design must define it.

### LRN-019: Build Infrastructure First in Sequential Version Planning
- **Insight:** Sequence infrastructure themes before consumer themes
- **Applicability:** v006 must build expression engine and graph validation before drawtext, speed control, composition, and API endpoints. The dependency chain is: BL-037 -> BL-040/041, BL-038 -> BL-039, BL-040+041 -> BL-042, BL-040+042 -> BL-043.

## Medium Relevance

### LRN-008: Record-Replay with Strict Mode for External Dependencies
- **Insight:** Three-tier executor pattern (Real/Recording/Fake) with strict argument verification
- **Applicability:** BL-040 contract tests (ffmpeg -filter_complex validation) should use the established Recording/Fake FFmpeg executor pattern from v004.

### LRN-013: Progressive Coverage Thresholds
- **Insight:** Start with conservative threshold, ratchet up after baseline confirmation
- **Applicability:** Rust coverage is at 75% (target 90%). v006 adds significant Rust code — proptest in BL-037 and unit tests across all Rust items should push coverage toward the 90% target.

### LRN-025: Feature Handoff Documents Enable Zero-Rework Sequencing
- **Insight:** Handoff documents communicating integration points enable clean feature chains
- **Applicability:** The BL-037->BL-040/041->BL-042->BL-043 chain requires clear handoffs documenting expression types, builder APIs, and registration interfaces.

### LRN-005: Constructor DI over dependency_overrides
- **Insight:** Use `create_app()` constructor parameters for test wiring
- **Applicability:** The effect registry (BL-042) and any new services should be injected via `create_app()` kwargs, consistent with existing patterns.

## Low Relevance (Contextual)

### LRN-003: Security Validation Whitelist Pattern
- **Applicability:** May inform input validation for effect parameters (allowed fonts, paths)

### LRN-009: Handler Registration Pattern for Generic Job Queues
- **Applicability:** Registry pattern concept may inform effect registration design in BL-042

### LRN-007: Parity Tests Prevent Test Double Drift
- **Applicability:** If InMemory effect repository is created, parity tests should verify it matches real storage
