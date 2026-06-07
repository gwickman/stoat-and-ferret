# Release 2 — GUI Integration

The GUI remains an API client (Release 1 pattern). Release 2 adds four surfaces, all `data-testid`-instrumented for UAT, all driven by the new endpoints in [05-api-specification.md](05-api-specification.md).

---

## 1. Automation lanes (keyframe editor)

A per-clip / per-track automation lane beneath the timeline for any parameter that accepts an automation envelope (volume, EQ band gain, pan, blur radius, opacity, scale, tone frequency).

- Add/move/delete keyframe nodes; choose curve type per segment (hold / linear / exponential / ease-in-out).
- Live readout of the **Rust-compiled expression** (`filter_preview`) for transparency, mirroring the Release 1 "show the generated FFmpeg" philosophy.
- Snap-to-marker option so envelopes align to section boundaries (Induction/Deepening/Suggestion/Emergence).
- `data-testid`: `automation-lane`, `keyframe-node`, `curve-select`, `expr-preview`.

## 2. QC results panel

Displays the QC report after render/export with per-check pass/fail, measured vs target, and unit.

- Green/red per assertion; click a failed check to jump to the offending region (uses QC timestamps where available).
- "Re-master" affordance for failures (drives exception flows A3/A5) — re-runs export with adjusted settings, re-verifies.
- Live updates via `qc.*` WebSocket events.
- `data-testid`: `qc-panel`, `qc-check-row`, `qc-overall`, `qc-remaster-btn`.

## 3. Delivery profiles

A profile editor and a profile selector in the render/export dialog.

- Editor: outputs list (container/codec/bitrate), loudness target + true-peak ceiling, metadata + "embed chapters from markers".
- Export dialog: pick a profile → shows the formats that will be produced and the loudness target; export runs QC against the profile.
- `data-testid`: `delivery-profile-editor`, `delivery-profile-select`, `profile-output-row`.

## 4. Markers / regions

A marker track on the timeline for naming and placing the session sections.

- Create/rename/resize regions; section regions are non-overlapping and ordered.
- Regions feed automation snap targets and chapter export.
- `data-testid`: `marker-track`, `region`, `region-label`.

---

## Editing affordances (timeline)

- **Razor / split**: split a clip at the playhead (`POST .../split`).
- **Reverse**: toggle on a clip; UI surfaces the buffer-length limit and shows a structured error if exceeded.
- **Range-bound effect**: when adding an effect, an optional "apply to range" sets the `window` (start/end frame), reflected in the `enable` clause preview.

## New effect panels

The existing schema-driven `EffectParameterForm` renders the new audio/video/generator effects automatically from their JSON schemas + AI hints — no bespoke forms required, except:
- **Tone generator**: a small spectrum/frequency-envelope widget (binaural offset, isochronic rate).
- **Parametric EQ**: a multi-band curve widget (bands as a structured param array).
- **Color LUT**: a LUT picker with graded thumbnail preview.

## Accessibility & compatibility

Carries Release 1 standards forward: keyboard navigation for all new controls, ARIA labels, WCAG AA contrast, focus management. Automation lanes provide keyboard keyframe nudging. Browser support matrix unchanged (Chrome/Firefox/Safari/Edge current+prior).

## Theater Mode

The QC overall status and the active section label surface in Theater Mode's HUD during render, alongside the existing `ai_action` indicator — so an observer watching the AI build/master the session sees both what it is doing and whether the output is passing QC.
