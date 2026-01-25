# Implementation Plan: Filter Chain

## Step 1: Define Filter Types
Create `rust/stoat_ferret_core/src/ffmpeg/filter.rs`:

```rust
/// A single filter with parameters
#[derive(Debug, Clone)]
pub struct Filter {
    name: String,
    params: Vec<(String, String)>,
}

impl Filter {
    pub fn new(name: &str) -> Self {
        Self {
            name: name.to_string(),
            params: Vec::new(),
        }
    }

    pub fn param(mut self, key: &str, value: impl ToString) -> Self {
        self.params.push((key.to_string(), value.to_string()));
        self
    }

    pub fn to_string(&self) -> String {
        if self.params.is_empty() {
            self.name.clone()
        } else {
            let params: Vec<String> = self.params.iter()
                .map(|(k, v)| format!("{}={}", k, v))
                .collect();
            format!("{}={}", self.name, params.join(":"))
        }
    }
}
```

## Step 2: Implement Common Filters
```rust
pub fn concat(n: usize, v: usize, a: usize) -> Filter {
    Filter::new("concat")
        .param("n", n)
        .param("v", v)
        .param("a", a)
}

pub fn scale(width: i32, height: i32) -> Filter {
    Filter::new("scale")
        .param("w", width)
        .param("h", height)
}

pub fn scale_preserve_aspect(width: i32, height: i32) -> Filter {
    Filter::new("scale")
        .param("w", width)
        .param("h", height)
        .param("force_original_aspect_ratio", "decrease")
}

pub fn pad(width: i32, height: i32, x: &str, y: &str, color: &str) -> Filter {
    Filter::new("pad")
        .param("w", width)
        .param("h", height)
        .param("x", x)
        .param("y", y)
        .param("color", color)
}

pub fn format(pix_fmt: &str) -> Filter {
    Filter::new("format")
        .param("pix_fmts", pix_fmt)
}
```

## Step 3: Implement Filter Chain
```rust
/// A chain of filters with input/output labels
#[derive(Debug, Clone)]
pub struct FilterChain {
    inputs: Vec<String>,   // e.g., ["[0:v]", "[1:v]"]
    filters: Vec<Filter>,
    outputs: Vec<String>,  // e.g., ["[outv]"]
}

impl FilterChain {
    pub fn new() -> Self { ... }
    
    pub fn input(mut self, label: &str) -> Self {
        self.inputs.push(format!("[{}]", label));
        self
    }
    
    pub fn filter(mut self, f: Filter) -> Self {
        self.filters.push(f);
        self
    }
    
    pub fn output(mut self, label: &str) -> Self {
        self.outputs.push(format!("[{}]", label));
        self
    }
    
    pub fn to_string(&self) -> String {
        let inputs = self.inputs.join("");
        let filters: Vec<String> = self.filters.iter()
            .map(|f| f.to_string())
            .collect();
        let outputs = self.outputs.join("");
        format!("{}{}{}", inputs, filters.join(","), outputs)
    }
}
```

## Step 4: Implement FilterGraph
```rust
/// Multiple filter chains combined
#[derive(Debug, Clone)]
pub struct FilterGraph {
    chains: Vec<FilterChain>,
}

impl FilterGraph {
    pub fn new() -> Self {
        Self { chains: Vec::new() }
    }
    
    pub fn chain(mut self, chain: FilterChain) -> Self {
        self.chains.push(chain);
        self
    }
    
    pub fn to_string(&self) -> String {
        self.chains.iter()
            .map(|c| c.to_string())
            .collect::<Vec<_>>()
            .join(";")
    }
}
```

## Step 5: Integrate with FFmpegCommand
```rust
impl FFmpegCommand {
    pub fn filter_complex(mut self, graph: FilterGraph) -> Self {
        self.filter_complex = Some(graph);
        self
    }
}
```

## Step 6: Unit Tests
Test filter string generation matches FFmpeg syntax.

## Verification
- Filter strings are valid
- Complex filter graphs generate correctly
- Concat with multiple inputs works