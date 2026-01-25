# Implementation Plan: Position Calculations

## Step 1: Define Core Types
Create `rust/stoat_ferret_core/src/timeline/mod.rs`:

```rust
pub mod position;
pub mod framerate;
```

Create `framerate.rs`:
```rust
/// Rational frame rate representation
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct FrameRate {
    numerator: u32,
    denominator: u32,
}

impl FrameRate {
    pub const FPS_24: Self = Self { numerator: 24, denominator: 1 };
    pub const FPS_23_976: Self = Self { numerator: 24000, denominator: 1001 };
    pub const FPS_25: Self = Self { numerator: 25, denominator: 1 };
    pub const FPS_29_97: Self = Self { numerator: 30000, denominator: 1001 };
    pub const FPS_30: Self = Self { numerator: 30, denominator: 1 };
    // etc.
}
```

## Step 2: Implement Position Type
Create `position.rs`:
```rust
/// Timeline position in frames (frame-accurate)
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub struct Position(u64);

impl Position {
    pub fn from_frames(frames: u64) -> Self { Self(frames) }
    pub fn from_seconds(seconds: f64, fps: FrameRate) -> Self { ... }
    pub fn to_seconds(&self, fps: FrameRate) -> f64 { ... }
    pub fn frames(&self) -> u64 { self.0 }
}
```

## Step 3: Implement Duration Type
```rust
/// Duration in frames
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Duration(u64);

impl Duration {
    pub fn between(start: Position, end: Position) -> Option<Self> { ... }
    pub fn from_frames(frames: u64) -> Self { ... }
    pub fn from_seconds(seconds: f64, fps: FrameRate) -> Self { ... }
}
```

## Step 4: Implement SMPTE Timecode
```rust
/// SMPTE timecode (HH:MM:SS:FF)
pub struct Timecode {
    hours: u8,
    minutes: u8,
    seconds: u8,
    frames: u8,
}

impl Timecode {
    pub fn from_position(pos: Position, fps: FrameRate) -> Self { ... }
    pub fn to_position(&self, fps: FrameRate) -> Position { ... }
    pub fn parse(s: &str) -> Result<Self, TimecodeError> { ... }
}
```

## Step 5: Property-Based Tests
```rust
#[cfg(test)]
mod tests {
    use proptest::prelude::*;

    proptest! {
        #[test]
        fn round_trip_frames_seconds(frames in 0u64..1_000_000) {
            let pos = Position::from_frames(frames);
            let seconds = pos.to_seconds(FrameRate::FPS_24);
            let back = Position::from_seconds(seconds, FrameRate::FPS_24);
            prop_assert_eq!(pos, back);
        }
    }
}
```

## Step 6: Export from lib.rs
Add module to `lib.rs` and ensure it compiles.

## Verification
- `cargo test` passes all property tests
- No floating-point in Position/Duration internals
- Timecode round-trips correctly