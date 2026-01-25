# Implementation Plan: Command Construction

## Step 1: Define Core Types
Create `rust/stoat_ferret_core/src/ffmpeg/mod.rs`:

```rust
pub mod command;
pub mod input;
pub mod output;

pub use command::FFmpegCommand;
```

Create `command.rs`:
```rust
use std::path::Path;

#[derive(Debug, Clone)]
pub struct FFmpegCommand {
    global_options: GlobalOptions,
    inputs: Vec<InputSpec>,
    outputs: Vec<OutputSpec>,
}

#[derive(Debug, Clone, Default)]
struct GlobalOptions {
    overwrite: bool,
    loglevel: Option<String>,
}
```

## Step 2: Implement Global Options
```rust
impl FFmpegCommand {
    pub fn new() -> Self {
        Self {
            global_options: GlobalOptions::default(),
            inputs: Vec::new(),
            outputs: Vec::new(),
        }
    }

    pub fn overwrite(mut self, yes: bool) -> Self {
        self.global_options.overwrite = yes;
        self
    }

    pub fn loglevel(mut self, level: &str) -> Self {
        self.global_options.loglevel = Some(level.to_string());
        self
    }
}
```

## Step 3: Implement Input Builder
```rust
pub struct InputBuilder<'a> {
    command: &'a mut FFmpegCommand,
    spec: InputSpec,
}

impl FFmpegCommand {
    pub fn input<P: AsRef<Path>>(mut self, path: P) -> InputBuilder {
        InputBuilder {
            command: &mut self,
            spec: InputSpec::new(path),
        }
    }
}

impl<'a> InputBuilder<'a> {
    pub fn seek(mut self, position: Position) -> Self {
        self.spec.seek = Some(position);
        self
    }

    pub fn duration(mut self, duration: Duration) -> Self {
        self.spec.duration = Some(duration);
        self
    }

    pub fn done(self) -> FFmpegCommand {
        self.command.inputs.push(self.spec);
        // Return ownership
        ...
    }
}
```

## Step 4: Implement Output Builder
Similar pattern for output options.

## Step 5: Implement build()
```rust
impl FFmpegCommand {
    pub fn build(&self) -> Result<Vec<String>, CommandError> {
        self.validate()?;

        let mut args = Vec::new();

        // Global options
        if self.global_options.overwrite {
            args.push("-y".to_string());
        }
        if let Some(ref level) = self.global_options.loglevel {
            args.extend([format!("-loglevel"), level.clone()]);
        }

        // Inputs
        for input in &self.inputs {
            input.append_args(&mut args);
        }

        // Outputs
        for output in &self.outputs {
            output.append_args(&mut args);
        }

        Ok(args)
    }

    fn validate(&self) -> Result<(), CommandError> {
        if self.inputs.is_empty() {
            return Err(CommandError::NoInputs);
        }
        if self.outputs.is_empty() {
            return Err(CommandError::NoOutputs);
        }
        Ok(())
    }
}
```

## Step 6: Unit Tests
Test command generation produces expected arguments.

## Verification
- Builder compiles and is usable
- Generated commands match expected FFmpeg syntax
- Validation catches missing inputs/outputs