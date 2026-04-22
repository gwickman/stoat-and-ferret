//! Build script that embeds deployment metadata into the compiled crate.
//!
//! Emits two `cargo:rustc-env` directives so the library code can read them
//! via the `env!()` and `option_env!()` macros at compile time:
//!
//! - `BUILD_TIMESTAMP` — UTC timestamp in ISO 8601 format, generated at build
//!   time from the system clock. Always present.
//! - `GIT_SHA` — short git SHA of HEAD. Prefers the `GIT_SHA` env var (set by
//!   the container build), falls back to running `git rev-parse --short HEAD`,
//!   and is otherwise left unset so `option_env!("GIT_SHA")` returns `None` and
//!   the Rust code can substitute `"unknown"`.

use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

fn main() {
    let build_timestamp = iso8601_utc_now();
    println!("cargo:rustc-env=BUILD_TIMESTAMP={build_timestamp}");

    if let Some(sha) = resolve_git_sha() {
        println!("cargo:rustc-env=GIT_SHA={sha}");
    }

    println!("cargo:rerun-if-env-changed=GIT_SHA");
    println!("cargo:rerun-if-env-changed=SOURCE_DATE_EPOCH");
    println!("cargo:rerun-if-changed=build.rs");
    println!("cargo:rerun-if-changed=../../.git/HEAD");
}

fn resolve_git_sha() -> Option<String> {
    if let Ok(sha) = std::env::var("GIT_SHA") {
        let trimmed = sha.trim();
        if !trimmed.is_empty() {
            return Some(trimmed.to_string());
        }
    }

    let output = Command::new("git")
        .args(["rev-parse", "--short", "HEAD"])
        .output()
        .ok()?;
    if !output.status.success() {
        return None;
    }
    let sha = String::from_utf8(output.stdout).ok()?;
    let trimmed = sha.trim();
    if trimmed.is_empty() {
        None
    } else {
        Some(trimmed.to_string())
    }
}

fn iso8601_utc_now() -> String {
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("system clock set before UNIX epoch")
        .as_secs() as i64;

    let (year, month, day, hour, minute, second) = epoch_to_ymd_hms(secs);
    format!("{year:04}-{month:02}-{day:02}T{hour:02}:{minute:02}:{second:02}Z")
}

/// Convert a UNIX timestamp to a (year, month, day, hour, minute, second)
/// tuple in UTC using Howard Hinnant's `civil_from_days` algorithm.
fn epoch_to_ymd_hms(secs: i64) -> (i64, u32, u32, u32, u32, u32) {
    let days = secs.div_euclid(86_400);
    let remainder = secs.rem_euclid(86_400);
    let hour = (remainder / 3_600) as u32;
    let minute = ((remainder % 3_600) / 60) as u32;
    let second = (remainder % 60) as u32;

    let z = days + 719_468;
    let era = if z >= 0 {
        z / 146_097
    } else {
        (z - 146_096) / 146_097
    };
    let doe = (z - era * 146_097) as u64;
    let yoe = (doe - doe / 1_460 + doe / 36_524 - doe / 146_096) / 365;
    let y = (yoe as i64) + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let day = (doy - (153 * mp + 2) / 5 + 1) as u32;
    let month = (if mp < 10 { mp + 3 } else { mp - 9 }) as u32;
    let year = if month <= 2 { y + 1 } else { y };

    (year, month, day, hour, minute, second)
}
