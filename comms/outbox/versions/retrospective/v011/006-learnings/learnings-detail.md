# Learnings Detail - v011 Retrospective

## LRN-060: Wire Frontend to Existing Backend Endpoints Before Creating New Ones

**Tags:** pattern, frontend, api-design, planning, efficiency
**Source:** v011/01-scan-and-clip-ux retrospective, v011 version retrospective

### Content

#### Context

When building GUI features that need to interact with backend data, there is a choice between creating new endpoints or wiring the frontend to existing ones.

#### Learning

Prioritize wiring the frontend to already-existing backend endpoints before creating new ones. When the backend API surface is already mature, GUI features ship faster and with fewer defects because the data contract is already tested and stable.

#### Evidence

In v011 Theme 01 (scan-and-clip-ux), the clip-crud-controls feature required zero new backend endpoints — it wired the frontend directly to existing POST/PATCH/DELETE endpoints on `/api/v1/projects/{id}/clips`. The browse-directory feature reused `validate_scan_path()` from the scan module for security validation. Both features completed on the first pass with all acceptance criteria passing.

#### Application

When planning GUI features, audit the existing API surface first. If the required endpoints already exist, scope the feature as frontend-only wiring work. This reduces risk, eliminates backend test regressions, and allows the feature to focus entirely on UI/UX concerns. Build backend first in earlier versions, then wire GUI in later versions.

---

## LRN-061: Documentation-Only Themes Are Low-Risk High-Value Process Investments

**Tags:** process, documentation, planning, risk-management, efficiency
**Source:** v011/02-developer-onboarding retrospective, v011 version retrospective

### Content

#### Context

Versions may include themes that involve only documentation, configuration templates, or process artifacts — no runtime code changes.

#### Learning

Documentation-only themes execute with zero test regressions and consistent quality gate results, making them ideal vehicles for process improvements. They carry negligible risk and compound value over subsequent versions when the artifacts they produce (templates, design-time checks, onboarding guides) are referenced during future work.

#### Evidence

v011 Theme 02 (developer-onboarding) delivered three documentation/config features: `.env.example` template, Windows Git Bash guidance, and an impact assessment document with 4 design-time checks. All three completed on the first pass with 17/17 acceptance criteria passing and unchanged test results (968 passed, 20 skipped, 93% coverage) throughout. Zero iteration cycles required.

#### Application

When planning versions, include documentation-only themes for process improvements, onboarding artifacts, and design-time quality checks. These themes are safe to batch together and execute quickly. Pair them with code-change themes to balance version risk profiles.

---

## LRN-062: Design-Time Impact Checks Shift Defect Detection Left from Implementation to Design

**Tags:** process, design, quality, failure-mode, institutional-knowledge
**Source:** v011/02-developer-onboarding/003-impact-assessment completion-report, v011 version retrospective

### Content

#### Context

Recurring issue patterns (async safety violations, missing settings documentation, cross-version wiring gaps, GUI input mechanism mismatches) can be detected during version design rather than during implementation or code review.

#### Learning

Codifying recurring issue patterns into a reusable impact assessment document with structured checks (trigger condition, what to check, action required) shifts defect detection from implementation to design phase. These checks act as institutional memory that persists across agent sessions and version boundaries.

#### Evidence

v011 Feature 003 (impact-assessment) created `IMPACT_ASSESSMENT.md` with 4 design-time checks derived from patterns observed in prior versions: async safety, settings documentation completeness, cross-version wiring, and GUI input mechanisms. Each check uses a consistent three-section structure (trigger, check, action) consumed during version design Task 003.

#### Application

After each version retrospective, review new failure patterns and add them as design-time checks in `IMPACT_ASSESSMENT.md`. Reference this document during version design to catch known patterns before they reach implementation. Keep checks general enough to apply across versions but specific enough to be actionable.
