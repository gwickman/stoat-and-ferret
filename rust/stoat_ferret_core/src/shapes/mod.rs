// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Grant Wickman

//! Procedural shape generators producing RGBA PNG output.

pub mod checkerboard;
pub mod concentric_rings;
pub mod radial_burst;
pub mod spiral;

pub use checkerboard::CheckerboardGenerator;
pub use concentric_rings::ConcentricRingsGenerator;
pub use radial_burst::RadialBurstGenerator;
pub use spiral::SpiralGenerator;
