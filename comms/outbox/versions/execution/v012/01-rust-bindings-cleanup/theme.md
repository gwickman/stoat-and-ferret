# Theme 01: rust-bindings-cleanup

## Description

Resolve the execute_command() wiring gap and remove unused PyO3 bindings from v001 and v006 that have zero production callers. This reduces the public API surface from 11 unused Python-facing bindings to zero, lowers maintenance burden, and clarifies which Rust functions are intended for Python consumption.

## Features

- **001-execute-command-removal**
- **002-v001-bindings-trim**
- **003-v006-bindings-trim**

## Live Progress

For current per-feature execution status, see `version-state.json` in the version outbox directory.
