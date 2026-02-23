# RCA: Scan Directory Delivered Without Browse Button

## Summary

The Scan Directory feature was delivered in v005 (Theme 03, Feature 003-library-browser) with a text-only path input and no folder browse dialog. This was **never specified** in any design document, backlog item, or implementation plan — the browse capability was simply absent from the requirements chain from the start.

## Root Cause

The gap originated in the design documents and propagated unchanged through the entire pipeline:

1. **Design doc** (`docs/design/08-gui-architecture.md:164`) shows `[Scan Directory]` button in the Library Browser wireframe but the scan modal wireframe is absent — no detail on what the modal contains
2. **Design doc** (`docs/design/08-gui-architecture.md:192-193`) lists features as "Scan directory button with progress modal" — no mention of a browse/file-picker capability
3. **Backlog item BL-033** acceptance criteria say "Scan modal triggers directory scan and shows progress feedback" — no mention of how the path is selected
4. **Implementation plan** (`comms/inbox/.../003-library-browser/implementation-plan.md:52`) describes "directory path input, submit button" — specifies a text input
5. **Implementation** (`gui/src/components/ScanModal.tsx`) delivers exactly what was specified: a text `<input>` for the path

No one in the pipeline (design, backlog, version design, implementation plan, implementation, review, retrospective) flagged the missing browse capability.

## Key Finding

This is a **specification gap**, not an implementation failure. The executing agent built exactly what was specified. The issue is that a standard UX pattern (folder picker dialog) was never part of the spec.

## Already Addressed

- **BL-070** ("Add Browse button for scan directory path selection") was created 2026-02-23 as an open P2 backlog item with acceptance criteria covering Browse button, folder dialog, and path population
- **BL-073** and **BL-074** address related scan UX gaps (progress reporting and cancellation)

## Recommendations

See [recommendations.md](recommendations.md) for specific process changes.
See [evidence-trail.md](evidence-trail.md) for the chronological trace.
