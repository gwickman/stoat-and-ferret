# Implementation Plan: Filter Chain

## Step 1: Define Filter Types
`rust/stoat_ferret_core/src/ffmpeg/filter.rs`:
```rust
#[derive(Debug, Clone)]
pub struct Filter {
    name: String,
    params: Vec<(String, String)>,
}

impl Filter {
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            params: Vec::new(),
        }
    }

    pub fn param(mut self, key: impl Into<String>, value: impl ToString) -> Self {
        self.params.push((key.into(), value.to_string()));
        self
    }
}

impl std::fmt::Display for Filter {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.name)?;
        if !self.params.is_empty() {
            write!(f, "=")?;
            let params: Vec<String> = self.params
                .iter()
                .map(|(k, v)| format!("{}={}", k, v))
                .collect();
            write!(f, "{}", params.join(":"))?;
        }
        Ok(())
    }
}
```

## Step 2: Common Filter Constructors
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

pub fn scale_fit(width: i32, height: i32) -> Filter {
    Filter::new("scale")
        .param("w", width)
        .param("h", height)
        .param("force_original_aspect_ratio", "decrease")
}

pub fn pad(width: i32, height: i32, color: &str) -> Filter {
    Filter::new("pad")
        .param("w", width)
        .param("h", height)
        .param("x", "(ow-iw)/2")
        .param("y", "(oh-ih)/2")
        .param("color", color)
}

pub fn format(pix_fmt: &str) -> Filter {
    Filter::new("format")
        .param("pix_fmts", pix_fmt)
}
```

## Step 3: FilterChain
```rust
#[derive(Debug, Clone, Default)]
pub struct FilterChain {
    inputs: Vec<String>,
    filters: Vec<Filter>,
    outputs: Vec<String>,
}

impl FilterChain {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn input(mut self, label: impl Into<String>) -> Self {
        self.inputs.push(format!("[{}]", label.into()));
        self
    }

    pub fn filter(mut self, f: Filter) -> Self {
        self.filters.push(f);
        self
    }

    pub fn output(mut self, label: impl Into<String>) -> Self {
        self.outputs.push(format!("[{}]", label.into()));
        self
    }
}

impl std::fmt::Display for FilterChain {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.inputs.join(""))?;
        let filters: Vec<String> = self.filters.iter().map(|x| x.to_string()).collect();
        write!(f, "{}", filters.join(","))?;
        write!(f, "{}", self.outputs.join(""))?;
        Ok(())
    }
}
```

## Step 4: FilterGraph
```rust
#[derive(Debug, Clone, Default)]
pub struct FilterGraph {
    chains: Vec<FilterChain>,
}

impl FilterGraph {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn chain(mut self, chain: FilterChain) -> Self {
        self.chains.push(chain);
        self
    }
}

impl std::fmt::Display for FilterGraph {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let chains: Vec<String> = self.chains.iter().map(|c| c.to_string()).collect();
        write!(f, "{}", chains.join(";"))
    }
}
```

## Step 5: Unit Tests
Test filter string generation.

## Verification
- Filter strings are valid FFmpeg syntax
- Complex graphs generate correctly