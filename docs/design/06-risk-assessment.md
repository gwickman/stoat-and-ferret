# stoat-and-ferret - Risk Assessment

**Project:** stoat-and-ferret — AI-driven video editor with hybrid Python/Rust architecture

## Overview

This document identifies potential risks for the AI-driven video editor project using a **hybrid Python/Rust architecture** and proposes mitigation strategies. Risks are categorized by type and rated by likelihood and impact.

**Architecture Context:**
- Python (FastAPI) provides the API layer for AI discoverability
- Rust core handles compute-intensive operations (filter generation, timeline math, sanitization)
- PyO3 bridges Python and Rust via native extension modules

**Quality-First Approach:** Many traditional risks are mitigated by the quality infrastructure built into the foundation. The Rust core provides additional compile-time guarantees. See **07-quality-architecture.md** for detailed patterns.

**Risk Rating Scale:**
- **Likelihood:** Low (L), Medium (M), High (H)
- **Impact:** Low (1), Medium (2), High (3)
- **Priority:** Likelihood × Impact

---

## Technical Risks

### T1: FFmpeg Complexity

| Attribute | Value |
|-----------|-------|
| Likelihood | High |
| Impact | High |
| Priority | Critical |

**Description:**
FFmpeg has a steep learning curve with complex filter syntax, cryptic error messages, and many edge cases. Incorrect filter chains can produce corrupt output or crashes.

**Consequences:**
- Long debugging sessions
- Incorrect video output
- Performance issues
- User frustration

**Mitigation (Hybrid Approach):**

| Mitigation | Component | Implementation |
|------------|-----------|----------------|
| Pure function filter builders | Rust | No side effects, compile-time safety |
| Property-based testing | Rust (proptest) | Fuzz filter generation with random inputs |
| Contract tests | Python/pytest | Run generated commands against real FFmpeg |
| Command logging | Python | Log every FFmpeg command for debugging |
| Input sanitization | Rust | Compile-time verified escaping |

**Quality Implementation:**
```rust
// Rust core - pure functions, property tested
pub fn build_text_overlay_filter(params: &TextOverlayParams) -> String {
    let sanitized = escape_ffmpeg_text(&params.text);
    format!(
        "drawtext=text='{}':fontsize={}:fontcolor={}:x=(w-text_w)/2:y=(h-text_h)/2",
        sanitized, params.font_size, params.font_color
    )
}

#[cfg(test)]
mod tests {
    use proptest::prelude::*;

    proptest! {
        #[test]
        fn filter_handles_any_text(text in ".*") {
            // Never panics, always produces valid filter
            let _ = build_text_overlay_filter(&TextOverlayParams { text, .. });
        }
    }
}
```

```python
# Python - contract test validates against real FFmpeg
@pytest.mark.contract
def test_text_overlay_valid_ffmpeg(rust_core, test_video):
    filter_str = rust_core.build_text_overlay_filter(TextOverlayParams(text="Hello", ...))
    result = subprocess.run(["ffmpeg", "-i", test_video, "-vf", filter_str, ...])
    assert result.returncode == 0
```

**Residual Risk:** Low - Rust guarantees + property testing catch issues early

---

### T2: Rust-Python FFI Boundary

| Attribute | Value |
|-----------|-------|
| Likelihood | Medium |
| Impact | High |
| Priority | High |

**Description:**
The boundary between Python and Rust introduces complexity. Type conversion, error handling, and memory management across the FFI boundary can cause issues.

**Consequences:**
- Panics in Rust crashing Python process
- Memory leaks if ownership unclear
- Performance overhead from type conversion
- Debugging complexity across language boundary

**Mitigation:**

| Mitigation | Implementation |
|------------|----------------|
| Result types | Return Result<T, E> from Rust, convert to Python exceptions |
| Zero-copy where possible | Use PyO3's buffer protocol for large data |
| Thin boundary | Keep FFI surface minimal, complex logic stays in Rust |
| Integration tests | Test Python→Rust→Python round-trips |
| Type mapping tests | Verify Pydantic models match Rust structs |

**Quality Implementation:**
```rust
// Rust - explicit error handling, no panics across FFI
#[pyfunction]
fn build_text_overlay(params: TextOverlayParamsRust) -> PyResult<String> {
    build_text_overlay_filter(&params)
        .map_err(|e| PyValueError::new_err(e.to_string()))
}
```

```python
# Python - graceful handling of Rust errors
try:
    filter_str = rust_core.build_text_overlay(params.to_rust())
except ValueError as e:
    raise InvalidEffectParams(str(e)) from e
```

**Residual Risk:** Medium - Requires careful design at boundary

---

### T3: Rust Learning Curve

| Attribute | Value |
|-----------|-------|
| Likelihood | High |
| Impact | Medium |
| Priority | High |

**Description:**
Rust has a steep learning curve compared to Python. The borrow checker, lifetime annotations, and ownership model require adjustment.

**Consequences:**
- Slower initial development
- Frustration with compiler errors
- Suboptimal patterns used early on
- Temptation to put logic in Python instead

**Mitigation:**
1. **Start simple** - begin with pure functions (no lifetimes needed)
2. **Clone freely** - optimize later, get it working first
3. **Use idiomatic patterns** - follow Rust community conventions
4. **Leverage AI assistance** - Claude Code understands Rust well
5. **Keep scope limited** - only core compute in Rust, not everything

**Residual Risk:** Medium - Learning curve is real but manageable

---

### T4: Build Complexity (PyO3/maturin)

| Attribute | Value |
|-----------|-------|
| Likelihood | Medium |
| Impact | Medium |
| Priority | Medium |

**Description:**
Building Python extensions from Rust adds toolchain complexity. maturin must build Rust code and package it as Python wheels. CI/CD becomes more complex.

**Consequences:**
- Build failures in CI
- Platform-specific build issues
- Slow build times
- Dependency on multiple toolchains

**Mitigation:**
1. **Use maturin** - handles most complexity automatically
2. **Pin toolchain versions** - Rust version in rust-toolchain.toml
3. **Docker for builds** - consistent environment
4. **Separate CI jobs** - Rust tests, Python tests, integration tests
5. **Cache aggressively** - Rust target directory, pip cache

**Quality Implementation:**
```toml
# rust-toolchain.toml
[toolchain]
channel = "1.70"
components = ["rustfmt", "clippy"]
```

```yaml
# CI pipeline (simplified)
jobs:
  rust-tests:
    steps:
      - uses: actions-rust-lang/setup-rust-toolchain@v1
      - run: cargo test
      - run: cargo clippy -- -D warnings

  python-tests:
    needs: rust-tests
    steps:
      - run: maturin develop
      - run: pytest tests/
```

**Residual Risk:** Low - maturin and PyO3 are mature tools

---

### T5: Real-Time Preview Performance

| Attribute | Value |
|-----------|-------|
| Likelihood | Medium |
| Impact | Medium |
| Priority | Medium |

**Description:**
Real-time preview with effects applied may not achieve acceptable frame rates, especially with complex filters or high-resolution content.

**Consequences:**
- Stuttering playback
- Delayed preview updates
- Poor user experience

**Mitigation:**
1. **Rust for timeline calculations** - sub-millisecond performance
2. **Implement proxy workflow** early (720p for 4K, 540p for 1080p)
3. **Use libmpv GPU acceleration** where available
4. **Simplify preview filters** compared to final render
5. **Benchmark each effect** during development

**Residual Risk:** Low - Rust performance + proxy workflow solve most issues

---

### T6: Cross-Platform Compatibility

| Attribute | Value |
|-----------|-------|
| Likelihood | Medium |
| Impact | Medium |
| Priority | Medium |

**Description:**
FFmpeg, libmpv, Python, and Rust behavior may differ between Linux, Windows, and macOS. The Rust core adds another dimension of cross-platform concerns.

**Consequences:**
- Features work on one platform but fail on another
- Triple maintenance burden (Python + Rust + FFmpeg)
- Delayed releases

**Mitigation:**
1. **Cross-compile wheels** with maturin for major platforms
2. **Use pathlib (Python)** and std::path (Rust) for all paths
3. **Test on all target platforms** in CI
4. **Linux-first** development, others as validation
5. **Conditional compilation** for platform-specific Rust code

**Residual Risk:** Medium - Some issues inevitable

---

### T7: Hardware Acceleration Variability

| Attribute | Value |
|-----------|-------|
| Likelihood | Medium |
| Impact | Low |
| Priority | Low |

**Description:**
Hardware encoding (NVENC, VAAPI, QSV) availability and capabilities vary by system. Detection may fail, or encoding may produce lower quality than expected.

**Consequences:**
- Slower renders on some systems
- Quality inconsistency
- User confusion

**Mitigation:**
1. **Implement robust detection** with fallback chain
2. **Software encoding as default** - HW as optimization
3. **Document hardware requirements** clearly
4. **Allow user override** of encoder selection

**Residual Risk:** Low - Software fallback ensures functionality

---

### T8: Large File Handling

| Attribute | Value |
|-----------|-------|
| Likelihood | Medium |
| Impact | Medium |
| Priority | Medium |

**Description:**
Users may have very large files (4K, ProRes, long recordings) that stress memory, disk I/O, and processing time. Library scanning and thumbnail generation may be slow.

**Consequences:**
- Memory exhaustion
- Slow operations
- Timeouts
- Poor user experience

**Mitigation:**
1. **Stream processing** - never load entire files into memory
2. **Rust for CPU-bound parsing** - if needed in future
3. **Background scanning** with progress reporting
4. **Incremental updates** - only scan changed files
5. **Progress indicators** for long operations

**Residual Risk:** Low - Streaming approach handles most cases

---

## Project Risks

### P1: Scope Creep

| Attribute | Value |
|-----------|-------|
| Likelihood | High |
| Impact | High |
| Priority | Critical |

**Description:**
Solo developer projects tend to expand scope as ideas emerge. The hybrid architecture could encourage "while I'm in Rust, let me also add..." patterns.

**Consequences:**
- Never-ending project
- Incomplete features
- Burnout
- Abandoned project

**Mitigation:**
1. **Strict MVP definition** - prototype document defines boundaries
2. **Minimal Rust scope** - only what needs performance
3. **Phase gates** - complete each phase before moving on
4. **Feature parking lot** - document ideas but don't implement
5. **Working software** over perfect software

**Residual Risk:** Medium - Requires discipline

---

### P2: Solo Developer Bottleneck

| Attribute | Value |
|-----------|-------|
| Likelihood | High |
| Impact | Medium |
| Priority | High |

**Description:**
Single developer means all knowledge, decisions, and work flow through one person. Two languages (Python + Rust) increase cognitive load.

**Consequences:**
- Project stalls
- Knowledge loss
- Context switching overhead
- Bus factor = 1

**Mitigation:**
1. **Document decisions** as they're made
2. **Keep Rust simple** - pure functions, no complex lifetimes
3. **Regular commits** with descriptive messages
4. **Break work into small chunks** - always something achievable
5. **AI-assisted development** - Claude Code helps with both languages

**Residual Risk:** Medium - Inherent to solo projects

---

### P3: Integration Complexity

| Attribute | Value |
|-----------|-------|
| Likelihood | Medium |
| Impact | Medium |
| Priority | Medium |

**Description:**
Multiple components (API, Rust core, FFmpeg, libmpv, database, queue) must work together. The Python-Rust boundary adds another integration point.

**Consequences:**
- Architectural changes late in project
- Component conflicts
- Performance bottlenecks at boundaries

**Mitigation:**
1. **Black box testing harness** - validates complete workflows through REST API (see 07-quality-architecture.md)
2. **Recording test doubles** - capture external interactions for verification without execution
3. **Contract tests** - verify test doubles match real implementations
4. **Vertical slices** - implement full workflows, not layers
5. **Real Rust core in all tests** - never mock the property-tested core
6. **Docker for dependencies** to ensure consistency
7. **Continuous integration** from day one

**Quality Implementation:**
```python
# Black box test validates integration
def test_complete_render_workflow(client, ffmpeg_recorder, job_queue):
    """Validates entire workflow is wired correctly."""
    project_id = create_project_via_api(client)

    # Start render through API
    response = client.post("/render/start", json={
        "project_id": project_id,
        "output_path": "/output/final.mp4"
    })
    job_id = response.json()["job_id"]

    # Execute (synchronous in test)
    job_queue.execute_pending(ffmpeg_recorder)

    # Verify complete workflow
    assert client.get(f"/render/status/{job_id}").json()["status"] == "completed"
    ffmpeg_recorder.assert_command_generated("-filter_complex")
```

**Residual Risk:** Very Low - Black box testing harness catches integration failures early

---

## Operational Risks

### O1: Data Loss

| Attribute | Value |
|-----------|-------|
| Likelihood | Low |
| Impact | High |
| Priority | Medium |

**Description:**
Projects, database, or original video files could be lost due to bugs, disk failure, or user error.

**Consequences:**
- Lost work
- Lost media
- User trust destroyed

**Mitigation (Quality-First Approach):**

| Mitigation | Quality Attribute | Implementation |
|------------|------------------|----------------|
| Non-destructive editing | Reliability | Never modify original files |
| Project versioning | Reliability | Keep last N versions for recovery |
| Atomic saves | Reliability | Write to temp, then rename |
| Migration backups | Reliability | Backup DB before schema changes |
| Audit logging | Debuggability | Track all modifications |

**Residual Risk:** Very Low - Multiple layers of protection

---

### O2: Security Vulnerabilities

| Attribute | Value |
|-----------|-------|
| Likelihood | Medium |
| Impact | High |
| Priority | High |

**Description:**
User-provided paths and filenames could enable path traversal, command injection, or other attacks. The Rust core helps but doesn't eliminate all risks.

**Consequences:**
- Unauthorized file access
- System compromise
- Command injection via FFmpeg filters

**Mitigation (Rust-Enhanced):**

| Mitigation | Implementation |
|------------|----------------|
| Path validation | Rust validates all paths at compile-time boundaries |
| Input sanitization | Rust escapes all user text for FFmpeg |
| No shell execution | Python uses subprocess.exec, never shell=True |
| Bounded inputs | Rust enforces parameter ranges (speed 0.25-4.0, etc.) |
| Rate limiting | Python/FastAPI handles API rate limits |

**Quality Implementation:**
```rust
// Rust - compile-time enforced sanitization
pub fn escape_ffmpeg_text(input: &str) -> String {
    input
        .replace('\\', "\\\\")
        .replace('\'', "'\\''")
        .replace(':', "\\:")
        // ... all dangerous characters
}

pub fn validate_path(path: &Path, allowed_dirs: &[PathBuf]) -> Result<(), PathError> {
    let canonical = path.canonicalize()?;
    if !allowed_dirs.iter().any(|d| canonical.starts_with(d)) {
        return Err(PathError::OutsideAllowedDirectory);
    }
    Ok(())
}
```

**Residual Risk:** Low - Rust sanitization + Python defense in depth

---

### O3: Resource Exhaustion

| Attribute | Value |
|-----------|-------|
| Likelihood | Medium |
| Impact | Medium |
| Priority | Medium |

**Description:**
Multiple render jobs, large libraries, or complex projects could exhaust disk space, memory, or CPU.

**Consequences:**
- Failed renders
- System instability
- Data corruption

**Mitigation:**
1. **Job queue** limits concurrent renders
2. **Disk space checks** before rendering
3. **Rust core is memory-efficient** - no GC pressure
4. **Configurable limits** for library size, render queue
5. **Cleanup old renders/proxies** automatically

**Residual Risk:** Low - Resource management built into design

---

## External Risks

### E1: FFmpeg/libmpv API Changes

| Attribute | Value |
|-----------|-------|
| Likelihood | Low |
| Impact | Medium |
| Priority | Low |

**Description:**
New FFmpeg or libmpv versions might deprecate filters, change syntax, or modify behavior.

**Consequences:**
- Broken functionality after update
- Maintenance burden
- Version lock-in

**Mitigation:**
1. **Pin major versions** in requirements
2. **Contract tests** validate filter output against FFmpeg
3. **Abstract FFmpeg calls** in Rust command builder
4. **Monitor release notes** for breaking changes

**Residual Risk:** Low - Stable APIs, slow change

---

### E2: PyO3/maturin Ecosystem Changes

| Attribute | Value |
|-----------|-------|
| Likelihood | Low |
| Impact | Medium |
| Priority | Low |

**Description:**
PyO3 and maturin are actively developed. Breaking changes could require migration effort.

**Consequences:**
- Build failures after updates
- API changes in Rust bindings
- Migration work

**Mitigation:**
1. **Pin PyO3 version** in Cargo.toml
2. **Pin maturin version** in dev dependencies
3. **Follow PyO3 migration guides** when updating
4. **Test thoroughly** after any toolchain update

**Residual Risk:** Low - Both projects are mature with good backwards compatibility

---

### E3: Codec Licensing

| Attribute | Value |
|-----------|-------|
| Likelihood | Low |
| Impact | Low |
| Priority | Low |

**Description:**
Some codecs (H.264, H.265) have patent/licensing considerations for commercial use.

**Consequences:**
- Legal concerns if commercialized
- Limited codec options

**Mitigation:**
1. **Personal/educational use** is generally safe
2. **Use royalty-free codecs** (VP9, AV1) when possible
3. **Document codec options** for users

**Residual Risk:** Low - Personal project, open-source codecs available

---

## Risk Matrix Summary

```
           Impact
         Low  Med  High
      ┌─────┬─────┬─────┐
High  │ T7  │T3,T5│T1,P1│
      │     │ P2  │     │
Likelihood├─────┼─────┼─────┤
Medium│ E3  │T4,T6│T2,O2│
      │     │T8,P3│     │
      │     │ O3  │     │
      ├─────┼─────┼─────┤
Low   │E1,E2│     │ O1  │
      └─────┴─────┴─────┘
```

**Critical (address immediately):**
- T1: FFmpeg Complexity
- P1: Scope Creep

**High (address in planning):**
- T2: Rust-Python FFI Boundary
- T3: Rust Learning Curve
- P2: Solo Developer Bottleneck
- O2: Security Vulnerabilities

**Medium (monitor and mitigate):**
- T4: Build Complexity (PyO3/maturin)
- T5: Real-Time Preview Performance
- T6: Cross-Platform Compatibility
- T8: Large File Handling
- P3: Integration Complexity
- O1: Data Loss
- O3: Resource Exhaustion

**Low (accept with monitoring):**
- T7: Hardware Acceleration Variability
- E1: FFmpeg/libmpv API Changes
- E2: PyO3/maturin Ecosystem Changes
- E3: Codec Licensing

---

## Risk Response Plan

### Pre-Development Checklist

- [ ] Review FFmpeg worked examples and scaffolds
- [ ] Set up Rust development environment
- [ ] Verify PyO3/maturin builds successfully
- [ ] Set up integration test framework (Python + Rust)
- [ ] Define MVP scope in writing
- [ ] Establish backup strategy for code and data

### During Development

- [ ] Weekly scope check: "Is this in MVP?"
- [ ] Run both Rust and Python tests before each commit
- [ ] Run integration tests before merging
- [ ] Document all architectural decisions
- [ ] Test new features on secondary platform monthly
- [ ] Review security considerations for new endpoints

### Before Release

- [ ] Security review of all input handling (Rust sanitization)
- [ ] Performance testing with large files
- [ ] Cross-platform wheel builds verified
- [ ] Resource limit testing
- [ ] User documentation review

---

## Contingency Plans

### If FFmpeg Issues Block Progress

1. Simplify the problematic effect
2. Consult FFmpeg documentation and forums
3. Use proptest to find edge cases
4. Consider skipping effect for MVP
5. Document limitation and workaround

### If Rust Learning Curve Slows Development

1. Implement feature in Python first (prototype)
2. Move to Rust once patterns clear
3. Use `clone()` liberally, optimize later
4. Ask Claude Code for idiomatic Rust help
5. Keep Rust scope minimal

### If PyO3 Build Issues Occur

1. Check PyO3 GitHub issues for similar problems
2. Verify toolchain versions match requirements
3. Try building in Docker for clean environment
4. Simplify FFI boundary if needed
5. Consider vendoring Rust core as last resort

### If Scope Expands Beyond Control

1. Stop all new feature work
2. Review original MVP document
3. Cut any non-essential features
4. Focus on completing existing work
5. Release MVP, plan Phase 2

### If Motivation Drops

1. Take a break (days, not weeks)
2. Work on a fun/easy feature
3. Review completed work for perspective
4. Let Claude Code handle tedious refactoring
5. Reduce scope to achievable milestone

---

## Quality Attributes as Risk Mitigation

The hybrid architecture provides systematic mitigation for most risks:

| Risk Category | Quality Attributes | How It Helps |
|--------------|-------------------|--------------|
| FFmpeg bugs | Testability (Rust) | Pure functions, proptest catches edge cases |
| Input injection | Security (Rust) | Compile-time sanitization verification |
| Production debugging | Observability (Python) | Metrics, logs, traces identify root cause |
| Configuration errors | Operability (Python) | Validated config, health checks detect problems |
| Service instability | Reliability (both) | Graceful shutdown, retry logic, recovery |
| Render failures | Reliability | Retry, fallback, job recovery |
| Data loss | Reliability (Python) | Versioning, atomic saves, backups |
| FFI boundary issues | Testability | Integration tests, type mapping tests |
| **Integration failures** | **Black Box Testing** | **Complete workflow validation, recording fakes** |
| Preview performance | Observability | Rust timing metrics identify bottlenecks |
| Deployment issues | Deployability | Wheel builds, smoke tests, rollback capability |

**See 07-quality-architecture.md for detailed implementation patterns, including the Black Box Testing Harness.**

---

## Acceptance Criteria for Risk Management

Risk management is successful when:

1. **No critical bugs** in production releases
2. **MVP delivered** without major scope changes
3. **Core features work** on both target platforms
4. **No data loss incidents** reported
5. **Performance meets** documented requirements
6. **Security review** passes without critical findings

### Quality Infrastructure Acceptance

7. **Test coverage >80%** across Python modules
8. **Rust tests pass** with proptest iterations
9. **Health checks passing** (including rust_core check)
10. **Metrics being collected** and monitored
11. **Structured logs** with correlation IDs
12. **Graceful shutdown** verified working
13. **Error responses** include actionable suggestions
14. **PyO3 build succeeds** on all target platforms
15. **Black box integration tests passing** for all core workflows
16. **Contract tests verify** test doubles match real implementations
