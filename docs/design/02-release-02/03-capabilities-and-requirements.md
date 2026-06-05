# Release 2 — Capabilities & Requirements Register

The consolidated requirement set for Release 2, derived from two production use cases (see [04-use-cases.md](04-use-cases.md)) plus the commercial-editor capability survey. Each row is a requirement with its current state in snf and the FFmpeg mechanism that delivers it.

**Status legend:** ✅ have (Release 1) · 🟡 engine-ready (needs wiring / keyframe compiler) · 🆕 new FFmpeg wrap (builder + registry) · 🔴 new subsystem / different paradigm (out of scope this release).

---

## Audio — repair, pitch & time

| ID | Requirement | Status | Mechanism |
|----|-------------|--------|-----------|
| R-A01 | Noise reduction / spectral repair | 🟡 | `afftdn`, `anlmdn`, `arnndn`, `adeclick`, `adeclip` |
| R-A02 | De-esser / de-plosive | 🆕 | `deesser`; de-plosive = `highpass` + expander |
| R-A03 | Time-stretch without pitch change | 🟡 | `atempo` (pitch-preserving); `rubberband` for quality |
| R-A04 | Pitch-shift / formant control | 🆕 | `rubberband` (pitch + formant flags) |

## Audio — spatial & sound design

| ID | Requirement | Status | Mechanism |
|----|-------------|--------|-----------|
| R-S01 | Stereo / binaural panning | 🆕 | `pan` / `sofalizer` (HRTF) |
| R-S02 | Automated pan (LFO / keyframed) | 🟡 | keyframe→expression compiler |
| R-S03 | Convolution reverb (custom IRs) | 🆕 | `afir` + impulse-response asset pack |
| R-S04 | Loopable beds, seamless loop points | 🆕 | `aloop` + boundary crossfade |
| R-S05 | Tone synthesis (isochronic / binaural beats, freq automation) | 🆕 | `sine`/`aevalsrc` + keyframe compiler (frequency sweep) |
| R-S06 | Sidechain ducking | ✅ | `sidechaincompress` (formalise as registry effect) |
| R-S07 | Sub-bass grounding layer | 🆕 | track + `lowpass` / tone source |
| R-S08 | Ambisonic / surround delivery | 🔴 | channel-layout encode/decode — deferred |

## Audio — mix & master

| ID | Requirement | Status | Mechanism |
|----|-------------|--------|-----------|
| R-M01 | Per-track volume/level automation curves | 🟡 | keyframe compiler |
| R-M02 | Parametric EQ (multi-band) + EQ automation | 🆕/🟡 | `anequalizer` + keyframe compiler |
| R-M03 | Multiband compression | 🆕 | `mcompand` (or `asplit`→`acompressor`→`amix`) |
| R-M04 | Mastering limiter | 🆕 | `alimiter` |
| R-M05 | LUFS normalization + true-peak ceiling | 🆕 | two-pass `loudnorm` (EBU R128) |
| R-M06 | Multi-track layering (≥4 simultaneous audio tracks) | 🟡 | timeline + `amix` (wiring/test) |

## Editing & arrangement

| ID | Requirement | Status | Mechanism |
|----|-------------|--------|-----------|
| R-E01 | Non-destructive trims, fades, crossfades | ✅ | clips + fades + `acrossfade` |
| R-E02 | Frame-accurate crossfades (linear/exponential) | ✅ | `xfade` (59 types) / `acrossfade` |
| R-E03 | **Reverse clip (video + audio)** | 🆕 | `reverse` + `areverse` (whole-segment buffering — bound to short clips) |
| R-E04 | **Clip split / razor** | 🆕 | timeline editing op (segment a clip) |
| R-E05 | **Range-bound effect gating (any effect, frames X–Y)** | 🟡 | generalise existing `enable='between(t,a,b)'` |
| R-E06 | Ripple edit / track grouping | 🔴 | editing-model semantics — deferred |
| R-E07 | Nested sequences / submix buses | 🔴 | render-graph generalisation — deferred |

## Time & speed

| ID | Requirement | Status | Mechanism |
|----|-------------|--------|-----------|
| R-T01 | Constant speed change | ✅ | `setpts`/`atempo` (`speed_control`) |
| R-T02 | Variable-speed / time-remapping curves | 🆕 | segmented speeds or PTS-integral expression |
| R-T03 | Frame-rate conversion (optical-flow / blend) | 🆕 | `minterpolate` / `framerate` |
| R-T04 | Freeze frame / hold | 🆕 | `freezeframes` / `tpad` |

## Video FX

| ID | Requirement | Status | Mechanism |
|----|-------------|--------|-----------|
| R-V01 | Color grading / LUTs | 🆕 | `lut3d` / `haldclut` |
| R-V02 | Blur / sharpen (gaussian/directional, keyframable) | 🆕 | `gblur`, `dblur`, `unsharp` + keyframe compiler |
| R-V03 | Keying + blend modes | 🆕 | `chromakey`, `colorkey`, `blend` (~30 modes) |
| R-V04 | Optical distortion (lens/barrel, chromatic aberration) | 🆕 | `lenscorrection`/`lensfun`, `rgbashift` |
| R-V05 | Procedural generators (perlin/cellular/gradient/noise) | 🆕 | `perlin`, `cellauto`, `gradients`, `noise` (introduces generator-clip concept) |
| R-V06 | Vector masking & feathering | 🔴 | mask-authoring layer — deferred |

## Video motion & text

| ID | Requirement | Status | Mechanism |
|----|-------------|--------|-----------|
| R-G01 | Keyframed opacity / scale (slow zoom/crossfade) | 🟡 | keyframe compiler + `zoompan`/`scale`/`overlay` |
| R-G02 | Transitions (59-type xfade) | ✅ | `xfade` |
| R-G03 | Text / lower-thirds (cues, affirmations) | ✅ | `drawtext` |
| R-G04 | Color/LUT styling consistency for visual track | 🆕 | `lut3d` (shared with R-V01) |
| R-G05 | Motion-graphics templates (MOGRT) | 🔴 | template system — deferred |

## Project, ingest & structure

| ID | Requirement | Status | Mechanism |
|----|-------------|--------|-----------|
| R-P01 | Multi-track project (sample-rate / bit-depth / fps config) | 🟡 | extend project model |
| R-P02 | Multi-format ingest; proxy/transcode | ✅ | Release 1 ingest + proxy |
| R-P03 | **Markers / regions** (session structure → chapters) | 🆕 | markers model + `ffmetadata` |

## Verification & delivery (testing-enabling)

| ID | Requirement | Status | Mechanism |
|----|-------------|--------|-----------|
| R-Q01 | QC: loudness + true-peak measurement | 🆕 | `ebur128` / `loudnorm` JSON |
| R-Q02 | QC: clipping / peak / distortion | 🆕 | `astats`, `volumedetect` |
| R-Q03 | QC: unintended silence / gaps | 🆕 | `silencedetect` |
| R-Q04 | QC: loop-seam continuity | 🆕 | boundary-sample comparison |
| R-Q05 | QC: tone presence / evolution | 🆕 | `aspectralstats` |
| R-Q06 | QC: ducking verification | 🆕 | per-track level analysis |
| R-Q07 | QC: per-section intensity arc | 🆕 | per-region integrated LUFS |
| R-Q08 | QC: video defect detection | 🆕 | `blackdetect`, `freezedetect` |
| R-Q09 | QC: A/V sync verification | 🆕 | known-offset probe |
| R-Q10 | QC: decode integrity (plays end-to-end) | 🆕 | `ffmpeg -v error -f null -` |
| R-Q11 | QC: embedded metadata / chapters check | 🆕 | `ffprobe` |
| R-D01 | Delivery profiles (format+loudness+peak+metadata, validated) | 🆕 | profile + QC gate over batch export |
| R-D02 | Export presets (WAV + MP3/AAC; H.264/H.265) | ✅ | Release 1 render/audio export |
| R-D03 | Batch export (formats × loudness targets) | ✅ | Release 1 batch render |
| R-D04 | Chapter markers / metadata embedding | 🆕 | `ffmetadata` (depends on R-P03) |
| R-D05 | A/B monitoring / reference compare | 🔴 | interactive monitoring — deferred |

## Cross-cutting enabler

| ID | Requirement | Status | Mechanism |
|----|-------------|--------|-----------|
| R-X01 | Keyframe → expression compiler | 🟡 | Rust pure function (Subsystem 1) — **build first** |

---

## Shape of the release

- **~12 ✅ already shipped** (reused/formalised).
- **~7 🟡** unlocked by the keyframe→expression compiler (R-X01).
- **~30 🆕** clean FFmpeg wraps in the existing builder/registry pattern (including the 11 QC checks).
- **~8 🔴** deferred (capture, buses, masking, Ambisonic, MOGRT, A/B, ripple/grouping).

The dependency spine is **R-X01 first** (converts the 🟡 column to done), then **R-Q01…R-Q11 (QC pass)** which makes every other requirement testable.
