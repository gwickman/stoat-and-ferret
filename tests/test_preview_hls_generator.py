# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Tests for HLS generator arg building (build_hls_args).

Covers multi-input paths, optional start_offset_s (-ss flag), and
verifies that edge cases (None, 0.0) produce no -ss argument.
"""

from __future__ import annotations

from pathlib import Path

from stoat_ferret.preview.hls_generator import build_hls_args


class TestBuildHlsArgs:
    """Tests for build_hls_args()."""

    def test_single_input_no_offset(self, tmp_path: Path) -> None:
        """Single input with no start_offset_s yields one -i flag and no -ss."""
        args = build_hls_args(
            input_paths=["video.mp4"],
            output_dir=tmp_path,
            filter_complex=None,
            segment_duration=2.0,
        )
        assert args[:2] == ["-i", "video.mp4"]
        assert "-ss" not in args

    def test_multiple_inputs_produce_multiple_i_flags(self, tmp_path: Path) -> None:
        """Multiple input paths each produce a -i flag in order."""
        args = build_hls_args(
            input_paths=["a.mp4", "b.mp4"],
            output_dir=tmp_path,
            filter_complex=None,
            segment_duration=2.0,
        )
        assert args[0] == "-i"
        assert args[1] == "a.mp4"
        assert args[2] == "-i"
        assert args[3] == "b.mp4"

    def test_start_offset_s_inserts_ss_flag(self, tmp_path: Path) -> None:
        """start_offset_s=5.0 inserts -ss 5.0 after all -i flags."""
        args = build_hls_args(
            input_paths=["a.mp4"],
            output_dir=tmp_path,
            filter_complex=None,
            segment_duration=2.0,
            start_offset_s=5.0,
        )
        # Find the -ss flag
        assert "-ss" in args
        ss_idx = args.index("-ss")
        assert args[ss_idx + 1] == "5.0"
        # Must appear after all -i flags
        last_i_idx = max(i for i, v in enumerate(args) if v == "-i")
        assert ss_idx > last_i_idx

    def test_start_offset_s_none_no_ss_flag(self, tmp_path: Path) -> None:
        """start_offset_s=None yields no -ss flag."""
        args = build_hls_args(
            input_paths=["a.mp4"],
            output_dir=tmp_path,
            filter_complex=None,
            segment_duration=2.0,
            start_offset_s=None,
        )
        assert "-ss" not in args

    def test_start_offset_s_zero_no_ss_flag(self, tmp_path: Path) -> None:
        """start_offset_s=0.0 yields no -ss flag (guard: > 0)."""
        args = build_hls_args(
            input_paths=["a.mp4"],
            output_dir=tmp_path,
            filter_complex=None,
            segment_duration=2.0,
            start_offset_s=0.0,
        )
        assert "-ss" not in args

    def test_ss_appears_after_all_i_flags_with_multiple_inputs(self, tmp_path: Path) -> None:
        """-ss appears after all -i flags when multiple inputs are provided."""
        args = build_hls_args(
            input_paths=["a.mp4", "b.mp4", "c.mp4"],
            output_dir=tmp_path,
            filter_complex=None,
            segment_duration=2.0,
            start_offset_s=3.5,
        )
        ss_idx = args.index("-ss")
        # All -i flags must precede -ss
        i_indices = [i for i, v in enumerate(args) if v == "-i"]
        assert all(i < ss_idx for i in i_indices)
        assert args[ss_idx + 1] == "3.5"
