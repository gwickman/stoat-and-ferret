//! Composition filter builders for multi-stream video layouts.
//!
//! This module provides functions to generate FFmpeg overlay and scale filter
//! strings from [`LayoutPosition`] normalized coordinates, and the primary
//! [`graph::build_composition_graph`] entry point for building complete
//! FFmpeg filter graphs from multi-clip compositions.

pub mod graph;
pub mod overlay;
pub mod timeline;
