//! Composition filter builders for multi-stream video layouts.
//!
//! This module provides functions to generate FFmpeg overlay and scale filter
//! strings from [`LayoutPosition`] normalized coordinates.

pub mod overlay;
pub mod timeline;
