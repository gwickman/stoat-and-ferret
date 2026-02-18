# Learnings Summary - v006 Design

Relevant learnings from the project learning repository (25 total learnings, 8 directly applicable to v006).

## Highly Applicable to v006

### LRN-001: PyO3 Method Chaining with PyRefMut
- **Tags:** rust, pyo3, patterns, builder
- **Insight:** Use `PyRefMut<'_, Self>` as return type for fluent builder methods in PyO3. Returns self without cloning, enabling identical chaining in Rust and Python.
- **v006 applicability:** Directly applicable to the filter expression builder (BL-037), drawtext builder (BL-040), and speed control builder (BL-041). All three need fluent builder APIs exposed to Python.

### LRN-011: Python Business Logic, Rust Input Safety in Hybrid Architectures
- **Tags:** architecture, rust, python, hybrid, security, boundaries
- **Insight:** Rust owns input sanitization and type safety; Python owns business policy and domain rules. Don't put business rules in Rust -- they change more frequently.
- **v006 applicability:** Critical boundary design for v006. Rust: expression construction, filter validation, serialization. Python: effect registry, API routing, clip model effects storage, business rules for which effects can be applied.

### LRN-012: PyO3 FFI Overhead Makes Rust Slower for Simple Operations
- **Tags:** performance, rust, pyo3, ffi, benchmarking
- **Insight:** PyO3 FFI overhead makes Rust 7-10x slower than Python for simple operations. Rust wins only for string-heavy processing (1.9x faster).
- **v006 applicability:** Justifies Rust for the filter engine on safety/correctness grounds (preventing invalid FFmpeg syntax), not performance. Filter string serialization is string-heavy, which is where Rust does show performance benefits.

### LRN-016: Validate Acceptance Criteria Against Codebase During Design
- **Tags:** process, design, requirements, validation
- **Insight:** Validate that AC references existing domain models and APIs during design phase. Mark criteria depending on unimplemented prerequisites as deferred.
- **v006 applicability:** BL-043 references "clip/project model" effects storage that doesn't exist yet. Design must address this model extension before execution begins.

## Moderately Applicable to v006

### LRN-002: Frame-Accurate Timeline Math
- **Tags:** rust, video, precision, math
- **Insight:** Use integer frame counts internally with rational frame rates. Convert to f64 only at API boundaries.
- **v006 applicability:** Speed control (BL-041) setpts expressions involve time calculations. Ensure speed factors maintain frame accuracy when calculating PTS values.

### LRN-003: Security Validation Whitelist Pattern
- **Tags:** security, validation, patterns
- **Insight:** Whitelist-based validation for security-sensitive inputs.
- **v006 applicability:** The drawtext builder (BL-040) will accept user text input. Ensure the existing `escape_filter_text()` whitelist approach extends to new parameters (font paths, color values).

### LRN-019: Build Infrastructure First in Sequential Version Planning
- **Tags:** process, planning, architecture, sequencing
- **Insight:** Sequence infrastructure themes before consumer themes. The upfront investment pays off when subsequent themes consume the infrastructure.
- **v006 applicability:** Confirms the dependency ordering: expression engine (BL-037) and validation (BL-038) are infrastructure; builders (BL-040, BL-041) and API (BL-042, BL-043) are consumers.

### LRN-025: Feature Handoff Documents Enable Zero-Rework Sequencing
- **Tags:** process, sequencing, handoff, documentation, patterns
- **Insight:** Feature handoff documents communicating integration points and patterns enable zero-rework feature chains.
- **v006 applicability:** The BL-037 -> BL-040 -> BL-042 -> BL-043 chain requires each feature to clearly document its API surface for the next consumer. Handoff docs are critical.

## Not Directly Applicable (Reference Only)

The remaining 17 learnings (LRN-004 through LRN-010, LRN-013 through LRN-015, LRN-017, LRN-018, LRN-020 through LRN-024) cover testing patterns, CI configuration, frontend state management, and accessibility testing. These are valuable project knowledge but not directly relevant to v006's Rust filter engine and API endpoint scope.
