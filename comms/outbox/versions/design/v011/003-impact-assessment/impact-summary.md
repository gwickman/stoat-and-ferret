# Impact Summary: v011

## Small Impacts (sub-task scope)

These can be handled as sub-tasks within their owning features:

1. **C4 component docs — clip API consumption** (#2) — Add POST/PATCH/DELETE clip endpoints to c4-component-web-gui.md. Owning feature: BL-075.
2. **C4 code docs — ProjectDetails update** (#3) — Update ProjectDetails.tsx documentation with new CRUD components. Owning feature: BL-075.
3. **GUI guide — verify clip management section** (#5) — Existing docs already describe clip add/update/remove; verify accuracy post-implementation. Owning feature: BL-075.
4. **Roadmap — clip CRUD milestone** (#6) — Add clip CRUD GUI to milestone checklist. Owning feature: BL-075.
5. **GUI guide — scan section update** (#7) — Document Browse button in "Scanning for Videos" section. Owning feature: BL-070.
6. **GUI architecture — ScanModal description** (#8) — Update ScanModal component description with browse mechanism. Owning feature: BL-070.
7. **Getting-started — .env.example reference** (#10) — Add .env.example mention to getting-started guide. Owning feature: BL-071.
8. **Development setup — .env.example step** (#11) — Add "copy .env.example" step to dev setup. Owning feature: BL-071.
9. **Configuration docs — cross-check completeness** (#12) — Ensure .env.example includes all 10 Settings fields. Owning feature: BL-071.
10. **AGENTS.md — Windows section** (#13) — Add Windows Git Bash /dev/null guidance. This IS the primary deliverable of BL-019.
11. **BL-076 caller impact — no risk** (#14) — New file with existing consumer; no adoption gap. Owning feature: BL-076.

## Substantial Impacts (feature scope)

These require explicit scoping within the feature implementation plan:

1. **GUI architecture — clip CRUD controls** (#1) — The architecture spec (08-gui-architecture.md) has no clip management wireframe, no add/edit/delete workflow, and no component specification for clip forms. BL-075's implementation plan must include updating this spec before or during implementation. This is a significant documentation gap that, if unaddressed, risks vague implementation. Owning feature: BL-075.

2. **Frontend clip API client — zero callers** (#4) — The most significant caller-adoption finding: backend clip write endpoints are fully implemented and tested, but the frontend has literally zero code paths that call them. `useProjects.ts` only has `fetchClips()`. The BL-075 feature must deliver new API client functions (createClip, updateClip, deleteClip) and wire them to UI controls. This is core to the feature, not an ancillary concern. Owning feature: BL-075.

3. **API spec — directory browsing endpoint** (#9) — If BL-070 uses a backend-assisted folder picker (likely, given browser API limitations), a new API endpoint for directory listing is needed. This endpoint does not exist in 05-api-specification.md. The BL-070 design must decide the browse mechanism (browser API vs backend endpoint) during logical design, as this determines whether backend work is needed. Owning feature: BL-070.

## Cross-Version Impacts (backlog scope)

None identified. All impacts from v011 changes are addressable within the version.

**Note:** The C4 documentation being 2 versions behind (last updated v008) is pre-existing tech debt from before v011. The small C4 updates for BL-075 (#2, #3) are in-scope, but a comprehensive C4 refresh is a separate backlog concern.
