# Test Strategy: v006 — Effects Engine Foundation

## Theme 01: `01-filter-expression-infrastructure`

### Feature 001-expression-engine (BL-037)

| Test Type | Requirement | Details |
|-----------|-------------|---------|
| **Unit tests** | Expression AST types, builder API, serialization | Cover all expression types: enable, alpha, time, arithmetic. Verify builder prevents invalid construction. Test serialization produces valid FFmpeg syntax strings. |
| **Property-based tests** | Proptest for random valid expressions | Generate random valid expression trees via proptest. Verify all serialize to syntactically valid FFmpeg expressions. Verify round-trip properties where applicable. |
| **Unit tests** | PyO3 bindings | Test builder API works identically from Python via bindings. Verify method chaining returns self. |
| **Contract tests** | N/A | Expression serialization correctness tested via property-based tests; no FFmpeg binary needed at this level. |

### Feature 002-graph-validation (BL-038)

| Test Type | Requirement | Details |
|-----------|-------------|---------|
| **Unit tests** | Pad matching validation | Verify output labels connect to matching input labels. Test mismatched labels produce errors with specific pad names. |
| **Unit tests** | Unconnected pad detection | Verify unconnected pads reported with the specific pad name in error. |
| **Unit tests** | Cycle detection | Verify cyclic graphs rejected before serialization. Test topological sort correctness. |
| **Unit tests** | Error message quality | Verify error messages include actionable guidance per AC4. |
| **Unit tests** | Existing test compatibility | Existing FilterGraph tests must continue passing — validation extends, not replaces. |

---

## Theme 02: `02-filter-builders-and-composition`

### Feature 001-filter-composition (BL-039)

| Test Type | Requirement | Details |
|-----------|-------------|---------|
| **Unit tests** | Chain composition | Verify sequential filter application to single stream. Test multi-step chains. |
| **Unit tests** | Branch composition | Verify stream splitting into multiple outputs. Test pad label auto-management. |
| **Unit tests** | Merge composition | Verify overlay, amix, and concat merge modes. Test multi-input merge. |
| **Unit tests** | Automatic validation | Verify composed graphs pass validation automatically. Test that invalid compositions caught. |
| **Unit tests** | PyO3 bindings | Test composition API works from Python. Verify method chaining pattern. |

### Feature 002-drawtext-builder (BL-040)

| Test Type | Requirement | Details |
|-----------|-------------|---------|
| **Unit tests** | Position options | Test absolute coordinates, centered placement, margin-based positioning. |
| **Unit tests** | Styling parameters | Test font size, color, shadow offset/color, box background generation. |
| **Unit tests** | Alpha animation | Test fade in/out generation using expression engine. Verify expression integration. |
| **Unit tests** | PyO3 bindings | Test builder API from Python with type stubs. |
| **Contract tests** | FFmpeg filter validation | Verify generated drawtext filters pass `ffmpeg -filter_complex` validation. Use record-replay pattern (LRN-008). Run on single CI matrix entry (LRN-015). |

### Feature 003-speed-control (BL-041)

| Test Type | Requirement | Details |
|-----------|-------------|---------|
| **Unit tests** | setpts video speed | Test factor range 0.25x–4.0x. Verify PTS expression generation. |
| **Unit tests** | atempo audio speed | Test automatic chaining for factors >2.0x. Verify chain decomposition correctness. |
| **Unit tests** | Audio drop option | Test audio drop mode generates correct filter (no atempo). |
| **Unit tests** | Validation | Test out-of-range values rejected with helpful messages. |
| **Unit tests** | Edge cases | Test 1x (no-op), boundary values (0.25x, 4.0x), and extreme speeds. |

---

## Theme 03: `03-effects-api-layer`

### Feature 001-effect-discovery (BL-042)

| Test Type | Requirement | Details |
|-----------|-------------|---------|
| **Unit tests** | Effect registry service | Test registration, retrieval, and listing. Test DI integration via `create_app()`. |
| **Unit tests** | Parameter JSON schema generation | Verify schemas generated correctly for text overlay and speed control parameters. |
| **Unit tests** | AI hints | Verify AI hints included in effect metadata for each parameter. |
| **System/Golden tests** | GET /effects endpoint | Test endpoint returns complete effect list with expected structure. Verify text overlay and speed control registered. |
| **Unit tests** | Filter preview | Test Rust-generated filter preview for default parameters included in response. |

### Feature 002-clip-effect-model (BL-043, partial)

| Test Type | Requirement | Details |
|-----------|-------------|---------|
| **Unit tests** | Pydantic model extension | Test clip schema accepts effects list. Test serialization/deserialization. |
| **Unit tests** | DB repository | Test effect storage and retrieval in clip repository. |
| **Contract tests** | Schema round-trip | Verify effect configuration survives full round-trip: Python → DB → Python. |
| **Parity tests** | Repository parity | If InMemory clip repository double created, run parity tests (LRN-007). |

### Feature 003-text-overlay-apply (BL-043, partial)

| Test Type | Requirement | Details |
|-----------|-------------|---------|
| **Unit tests** | Endpoint handler | Test parameter validation, Rust builder invocation, effect storage on clip. |
| **Unit tests** | Error handling | Test Rust validation errors surface as structured API error responses. |
| **System/Golden tests** | POST apply flow | Black box test: POST text overlay → verify effect stored → verify filter string in response. |
| **Unit tests** | WebSocket events | Test `effect.applied` event emitted on successful application. |
| **Unit tests** | Filter string transparency | Verify response includes generated FFmpeg filter string. |

---

## Cross-Cutting Test Concerns

| Concern | Strategy |
|---------|----------|
| **Rust coverage** | Currently ~75%, target 90%. All new Rust code in Themes 01-02 must have comprehensive tests to close this gap (LRN-013). |
| **Python coverage** | Currently 93.28%, threshold 80%. Maintain with standard test coverage for Theme 03 features. |
| **Contract test CI** | FFmpeg contract tests (BL-040) run on single CI matrix entry per LRN-015. |
| **Record-replay** | Contract tests use existing FFmpegExecutor record-replay infrastructure (LRN-008). |
| **Handoff documents** | Each feature produces handoff-to-next.md for zero-rework sequencing (LRN-025). |
| **Type stubs** | CI verifies stubs match Rust API after each Rust feature. |
