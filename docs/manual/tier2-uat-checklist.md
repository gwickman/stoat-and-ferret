# Tier-2 UAT Checklist — Reverse-Split Journey (v080)

Headed perceptual assessment items for human-only outcomes in the reverse-split UAT journey.
These outcomes require subjective evaluation and cannot be verified by automated QC checks.

**Required for BL-457-AC-4 (uat-journeys feature)**

Run this checklist after the automated journey (J705) completes without error. The UAT conductor
listens to and views the rendered output, marking each item pass or fail.

## OC-3: Perceptual Audio Quality

Evaluate overall clarity, presence, and freedom from artifacts in audio processed through the
reverse effect and split workflow.

- [ ] OC-3.1: Reversed audio segment plays cleanly with no unexpected clicks, pops, or glitches at the reversal boundary
- [ ] OC-3.2: Audio at the split point transitions cleanly — no discontinuity, pop, or abrupt tonal shift between clip_a and clip_b
- [ ] OC-3.3: Full audio spectrum remains balanced before and after split; no anomalous frequency gaps introduced by effect application

## OC-4: Tonal and Dynamic Processing Quality

Verify that the reverse effect does not introduce unintended tonal or dynamic artifacts.

- [ ] OC-4.1: Reversed segment retains the same perceived tonal character as the forward version (no unexpected coloration from reversal)
- [ ] OC-4.2: Dynamic range is preserved across the split boundary — no audible compression pumping or level jump at the cut point
- [ ] OC-4.3: Any processing applied before the split is correctly inherited by both resulting clips without artifact

## OC-5: Mastering Loudness Perception

Confirm that loudness and level perception are correct across the split and reversed clips.

- [ ] OC-5.1: Perceived loudness is consistent between clip_a and clip_b after the split — no sudden level jump at the boundary
- [ ] OC-5.2: No audible clipping or distortion introduced by the reverse effect at the clip start or end
- [ ] OC-5.3: Silence/tone generator clips produce a neutral baseline with no unexpected level anomalies after reverse processing

## OC-14: Voice Repair Quality

Assess that voice repair and noise reduction processing (if applicable) is unaffected by the
reverse-split operation.

- [ ] OC-14.1: If voice repair effects are stacked with reverse, the repair processing remains effective and transparent in both split segments
- [ ] OC-14.2: No de-esser or noise-gate artifacts are introduced at the split boundary from inherited effect chains
- [ ] OC-14.3: Voice intelligibility and natural character are preserved in both clip_a and clip_b after the split

---

**Completion note:** All items in each OC section must be checked `[x]` for that outcome to be
considered "pass" during headed UAT. Document any failures in the UAT report with specific
timestamps and descriptions of the perceptual issue observed.

**Related:**
- Automated journey: `tests/uat/journeys/j_reverse_split.py` (J705)
- Machine-verifiable OC mapping: `tests/qc/oc_mapping.py`
- Acceptance harness Tier-2 checklist: `docs/manual/tier2-acceptance-checklist.md`
