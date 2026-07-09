# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Single source of truth mapping UC-MEDIA-MPS-001 outcomes to QC check IDs.

Machine-verifiable OCs and the check IDs that cover them.
Human-only OCs are listed separately — they require perceptual assessment
and cannot be verified by automated QC checks.
"""

from __future__ import annotations

OC_TO_QC_CHECK: dict[str, list[str]] = {
    "OC-1": ["chapters_present"],
    "OC-2": ["unintended_silence"],
    "OC-6": ["spatial_correlation"],  # voice in perceptible spatial field; phase correlation
    "OC-7": ["loop_seam"],
    "OC-8": ["tone_presence"],
    "OC-9": ["ducking"],
    "OC-10": ["section_arc"],
    "OC-11": ["loudness_integrated", "true_peak"],
    "OC-12": ["clipping", "unintended_silence"],  # no clipping/distortion/unintended silence
    "OC-13": ["av_sync"],
    "OC-16": ["chapters_present"],
    "OC-17": ["decode_integrity"],
}

# human-only outcomes: require perceptual / subjective human assessment;
# no automated QC check can verify these.
# OC-15: "deliverables produced in every required format" — requires checking output file presence
# against a delivery manifest, which is outside the scope of the QC audio/video analysis layer.
# Verified manually in the Tier-2 headed checklist.
OC_HUMAN_ONLY: list[str] = ["OC-3", "OC-4", "OC-5", "OC-14", "OC-15"]
