# Implementation Plan: Position Calculations

## Step 1: Create Module Structure
```
rust/stoat_ferret_core/src/
├── lib.rs
└── timeline/
    ├── mod.rs
    ├── framerate.rs
    ├── position.rs
    └── duration.rs
```

## Step 2: Implement FrameRate
`timeline/framerate.rs`:
```rust
/// Rational frame rate representation
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct FrameRate {
    numerator: u32,
    denominator: u32,
}

impl FrameRate {
    pub const FPS_23_976: Self = Self { numerator: 24000, denominator: 1001 };
    pub const FPS_24: Self = Self { numerator: 24, denominator: 1 };
    pub const FPS_25: Self = Self { numerator: 25, denominator: 1 };
    pub const FPS_29_97: Self = Self { numerator: 30000, denominator: 1001 };
    pub const FPS_30: Self = Self { numerator: 30, denominator: 1 };
    pub const FPS_50: Self = Self { numerator: 50, denominator: 1 };
    pub const FPS_59_94: Self = Self { numerator: 60000, denominator: 1001 };
    pub const FPS_60: Self = Self { numerator: 60, denominator: 1 };

    pub fn new(numerator: u32, denominator: u32) -> Option<Self> {
        if denominator == 0 { return None; }
        Some(Self { numerator, denominator })
    }

    pub fn frames_per_second(&self) -> f64 {
        self.numerator as f64 / self.denominator as f64
    }
}
```

## Step 3: Implement Position
`timeline/position.rs`:
```rust
use super::FrameRate;

/// Timeline position in frames (frame-accurate)
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Default)]
pub struct Position(u64);

impl Position {
    pub const ZERO: Self = Self(0);

    pub fn from_frames(frames: u64) -> Self {
        Self(frames)
    }

    pub fn from_seconds(seconds: f64, fps: FrameRate) -> Self {
        let frames = (seconds * fps.numerator as f64 / fps.denominator as f64).round() as u64;
        Self(frames)
    }

    pub fn frames(&self) -> u64 {
        self.0
    }

    pub fn to_seconds(&self, fps: FrameRate) -> f64 {
        self.0 as f64 * fps.denominator as f64 / fps.numerator as f64
    }
}
```

## Step 4: Implement Duration
`timeline/duration.rs`:
```rust
use super::{FrameRate, Position};

/// Duration in frames
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Default)]
pub struct Duration(u64);

impl Duration {
    pub const ZERO: Self = Self(0);

    pub fn from_frames(frames: u64) -> Self {
        Self(frames)
    }

    pub fn from_seconds(seconds: f64, fps: FrameRate) -> Self {
        let frames = (seconds * fps.numerator as f64 / fps.denominator as f64).round() as u64;
        Self(frames)
    }

    pub fn between(start: Position, end: Position) -> Option<Self> {
        if end.frames() >= start.frames() {
            Some(Self(end.frames() - start.frames()))
        } else {
            None
        }
    }

    pub fn frames(&self) -> u64 {
        self.0
    }

    pub fn to_seconds(&self, fps: FrameRate) -> f64 {
        self.0 as f64 * fps.denominator as f64 / fps.numerator as f64
    }
}
```

## Step 5: Property Tests
```rust
#[cfg(test)]
mod tests {
    use super::*;
    use proptest::prelude::*;

    proptest! {
        #[test]
        fn round_trip_position(frames in 0u64..1_000_000_000) {
            let pos = Position::from_frames(frames);
            let fps = FrameRate::FPS_24;
            let seconds = pos.to_seconds(fps);
            let back = Position::from_seconds(seconds, fps);
            prop_assert_eq!(pos, back);
        }

        #[test]
        fn duration_between_valid(start in 0u64..1_000_000, len in 0u64..1_000_000) {
            let s = Position::from_frames(start);
            let e = Position::from_frames(start + len);
            let dur = Duration::between(s, e);
            prop_assert!(dur.is_some());
            prop_assert_eq!(dur.unwrap().frames(), len);
        }
    }
}
```

## Step 6: Export from lib.rs
Update `lib.rs` to include timeline module.

## Verification
- `cargo test` passes all property tests
- No floating-point in Position/Duration internals
- All frame rate constants work correctly