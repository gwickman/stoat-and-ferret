## Context

When building GUI features that need to interact with backend data, there is a choice between creating new endpoints or wiring the frontend to existing ones.

## Learning

Prioritize wiring the frontend to already-existing backend endpoints before creating new ones. When the backend API surface is already mature, GUI features ship faster and with fewer defects because the data contract is already tested and stable.

## Evidence

In v011 Theme 01 (scan-and-clip-ux), the clip-crud-controls feature required zero new backend endpoints — it wired the frontend directly to existing POST/PATCH/DELETE endpoints on `/api/v1/projects/{id}/clips`. The browse-directory feature reused `validate_scan_path()` from the scan module for security validation. Both features completed on the first pass with all acceptance criteria passing.

## Application

When planning GUI features, audit the existing API surface first. If the required endpoints already exist, scope the feature as frontend-only wiring work. This reduces risk, eliminates backend test regressions, and allows the feature to focus entirely on UI/UX concerns. Build backend first in earlier versions, then wire GUI in later versions.