# Implementation Plan: Command Construction

## Step 1: Define Core Types
`rust/stoat_ferret_core/src/ffmpeg/mod.rs`:
```rust
pub mod command;

pub use command::FFmpegCommand;
```

## Step 2: Implement FFmpegCommand
`rust/stoat_ferret_core/src/ffmpeg/command.rs`:
```rust
#[derive(Debug, Clone, Default)]
pub struct FFmpegCommand {
    overwrite: bool,
    loglevel: Option<String>,
    inputs: Vec<InputSpec>,
    outputs: Vec<OutputSpec>,
    filter_complex: Option<String>,
}

#[derive(Debug, Clone)]
struct InputSpec {
    path: String,
    seek: Option<f64>,
    duration: Option<f64>,
    stream_loop: Option<i32>,
}

#[derive(Debug, Clone)]
struct OutputSpec {
    path: String,
    video_codec: Option<String>,
    audio_codec: Option<String>,
    preset: Option<String>,
    crf: Option<u8>,
    format: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CommandError {
    NoInputs,
    NoOutputs,
    EmptyPath,
    InvalidCrf(u8),
}

impl FFmpegCommand {
    pub fn new() -> Self { Self::default() }

    pub fn overwrite(mut self, yes: bool) -> Self {
        self.overwrite = yes;
        self
    }

    pub fn loglevel(mut self, level: impl Into<String>) -> Self {
        self.loglevel = Some(level.into());
        self
    }

    pub fn input(mut self, path: impl Into<String>) -> Self {
        self.inputs.push(InputSpec {
            path: path.into(),
            seek: None,
            duration: None,
            stream_loop: None,
        });
        self
    }

    pub fn seek(mut self, seconds: f64) -> Self {
        if let Some(input) = self.inputs.last_mut() {
            input.seek = Some(seconds);
        }
        self
    }

    pub fn duration(mut self, seconds: f64) -> Self {
        if let Some(input) = self.inputs.last_mut() {
            input.duration = Some(seconds);
        }
        self
    }

    pub fn output(mut self, path: impl Into<String>) -> Self {
        self.outputs.push(OutputSpec {
            path: path.into(),
            video_codec: None,
            audio_codec: None,
            preset: None,
            crf: None,
            format: None,
        });
        self
    }

    pub fn video_codec(mut self, codec: impl Into<String>) -> Self {
        if let Some(output) = self.outputs.last_mut() {
            output.video_codec = Some(codec.into());
        }
        self
    }

    pub fn audio_codec(mut self, codec: impl Into<String>) -> Self {
        if let Some(output) = self.outputs.last_mut() {
            output.audio_codec = Some(codec.into());
        }
        self
    }

    pub fn preset(mut self, preset: impl Into<String>) -> Self {
        if let Some(output) = self.outputs.last_mut() {
            output.preset = Some(preset.into());
        }
        self
    }

    pub fn crf(mut self, crf: u8) -> Self {
        if let Some(output) = self.outputs.last_mut() {
            output.crf = Some(crf);
        }
        self
    }

    pub fn filter_complex(mut self, filter: impl Into<String>) -> Self {
        self.filter_complex = Some(filter.into());
        self
    }

    pub fn build(&self) -> Result<Vec<String>, CommandError> {
        self.validate()?;

        let mut args = Vec::new();

        if self.overwrite {
            args.push("-y".to_string());
        }
        if let Some(ref level) = self.loglevel {
            args.push("-loglevel".to_string());
            args.push(level.clone());
        }

        for input in &self.inputs {
            if let Some(seek) = input.seek {
                args.push("-ss".to_string());
                args.push(format!("{:.3}", seek));
            }
            if let Some(dur) = input.duration {
                args.push("-t".to_string());
                args.push(format!("{:.3}", dur));
            }
            if let Some(loops) = input.stream_loop {
                args.push("-stream_loop".to_string());
                args.push(loops.to_string());
            }
            args.push("-i".to_string());
            args.push(input.path.clone());
        }

        if let Some(ref filter) = self.filter_complex {
            args.push("-filter_complex".to_string());
            args.push(filter.clone());
        }

        for output in &self.outputs {
            if let Some(ref codec) = output.video_codec {
                args.push("-c:v".to_string());
                args.push(codec.clone());
            }
            if let Some(ref codec) = output.audio_codec {
                args.push("-c:a".to_string());
                args.push(codec.clone());
            }
            if let Some(ref preset) = output.preset {
                args.push("-preset".to_string());
                args.push(preset.clone());
            }
            if let Some(crf) = output.crf {
                args.push("-crf".to_string());
                args.push(crf.to_string());
            }
            if let Some(ref fmt) = output.format {
                args.push("-f".to_string());
                args.push(fmt.clone());
            }
            args.push(output.path.clone());
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
        for input in &self.inputs {
            if input.path.is_empty() {
                return Err(CommandError::EmptyPath);
            }
        }
        for output in &self.outputs {
            if output.path.is_empty() {
                return Err(CommandError::EmptyPath);
            }
            if let Some(crf) = output.crf {
                if crf > 51 {
                    return Err(CommandError::InvalidCrf(crf));
                }
            }
        }
        Ok(())
    }
}
```

## Step 3: Unit Tests
Test builder produces expected argument arrays.

## Verification
- Builder compiles and is usable
- Generated commands match expected FFmpeg syntax
- Validation catches missing inputs/outputs