# Tier-2 Acceptance Checklist (UC-MEDIA-MPS-001)

Headed perceptual assessment items for human-only outcomes. These outcomes cannot be automatically verified by QC checks and require subjective evaluation by a trained UAT conductor.

**Required for Feature 011 (acceptance-harness) — BL-459-AC-3**

## OC-3: Perceptual Audio Quality

Evaluate the overall clarity, presence, and freedom from artifacts in the rendered audio.

- [ ] OC-3.1: Voice track clarity is uncompromised — no excessive processing artifacts or loss of presence
- [ ] OC-3.2: Ambience/background audio blends naturally without hollow or unnatural phase effects
- [ ] OC-3.3: Full-spectrum content is balanced across all four tracks (voice, ambience, music, tones) with no anomalous frequency gaps

## OC-4: Tonal and Dynamic Processing Quality

Verify that tone shaping and dynamic control are applied appropriately without overcorrection.

- [ ] OC-4.1: EQ adjustments (if applied) do not introduce coloration or make the voice sound thin or overly bright
- [ ] OC-4.2: Compression (if applied) maintains natural dynamics — no audible "pumping" or loss of dynamic expression
- [ ] OC-4.3: Harmonic enhancement (if applied) adds presence without sounding synthetic or overprocessed

## OC-5: Mastering Loudness Perception

Confirm that loudness targets and metering are perceptually correct.

- [ ] OC-5.1: Integrated loudness feels balanced relative to reference material (-16 LUFS target) — not too loud or too quiet for use case
- [ ] OC-5.2: True peak ceiling compliance (-1 dBTP limit) is maintained; no audible clipping or distortion at peak moments
- [ ] OC-5.3: Loudness consistency across clips is maintained — no sudden jumps or level surprises between transitions

## OC-14: Voice Repair Quality

Assess the effectiveness and transparency of noise reduction and vocal restoration.

- [ ] OC-14.1: Unwanted noise (hum, hiss, room tone) is audibly reduced without removing essential vocal detail or creating artifacts
- [ ] OC-14.2: De-esser or sibilant control (if applied) does not cause lisping or over-suppression of critical frequencies
- [ ] OC-14.3: Vocal track remains intelligible and retains natural character after repair processing — no "pumping" or "gating" artifacts

---

**Completion Note (UC-MEDIA-MPS-001):** All items in each OC section must be checked `[x]` for that outcome to be considered "pass" during headed UAT. Document any failures in the UAT report with specific timestamps and audio excerpts demonstrating the issue.

---

# v081 Video FX Effects — Headed UAT Discharge Checklist

Headed verification items for v081 video FX effects (BL-450–BL-455). These items require a
running application with a visible browser window and cannot be verified by headless tests alone.

**Required for v081 acceptance — BL-450-AC-4, BL-455-AC-4**

## BL-450-AC-4: Color LUT Grading GUI Preview (J706)

Verify that the `color_lut` effect is selectable in the GUI with a live graded preview.

Discharge command:
```
python scripts/uat_runner.py --headed --journey 706
```

- [ ] Color LUT effect appears in the effects panel for a clip
- [ ] Selecting a LUT preset (e.g. `warm_fade`) updates the timeline preview visually
- [ ] Preview thumbnail reflects the graded color palette
- [ ] Journey J706 passes (exit code 0) in headed mode

## BL-455-AC-4: Opacity / Scale Automation Lane Editing (Headed)

Verify that opacity and scale effects expose an editable automation lane in the GUI.

Discharge command:
```
python scripts/uat_runner.py --headed
```
Then manually interact with the automation lane:

- [ ] Apply an `opacity` effect to a clip — automation lane appears in the effects panel
- [ ] Keyframes can be added by clicking on the automation lane timeline
- [ ] Apply a `scale` effect — slow zoom is visible in the preview when start/end keyframes are set
- [ ] Keyframe edits persist after saving the project

## Video FX Headed UAT Journeys (J707–J710)

Run each journey in headed mode for visual evidence of v081 effects rendering in the browser.

```
python scripts/uat_runner.py --headed --journey 707   # blur
python scripts/uat_runner.py --headed --journey 708   # chroma_key
python scripts/uat_runner.py --headed --journey 709   # lens_distort
python scripts/uat_runner.py --headed --journey 710   # gradient_generator
```

- [ ] J707 blur: gblur filter renders visibly in browser; screenshot evidence captured
- [ ] J708 chroma_key: chromakey filter renders visibly in browser; screenshot evidence captured
- [ ] J709 lens_distort: lenscorrection filter renders visibly in browser; screenshot evidence captured
- [ ] J710 gradient_generator: gradients filter renders visibly in browser; screenshot evidence captured

---

**Completion Note (v081 Video FX):** All items above must be checked `[x]` before v081 headed UAT
is considered discharged. Document any failures with screenshots and journey IDs in the UAT report.
