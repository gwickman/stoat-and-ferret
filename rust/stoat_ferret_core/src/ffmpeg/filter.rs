//! FFmpeg filter chain builder for complex filtergraphs.
//!
//! This module provides types for constructing FFmpeg filter chains that can be
//! used with the `-filter_complex` argument.
//!
//! # Overview
//!
//! - [`Filter`] - A single FFmpeg filter with parameters
//! - [`FilterChain`] - A sequence of filters connected with commas
//! - [`FilterGraph`] - Multiple filter chains connected with semicolons
//!
//! # Examples
//!
//! ```
//! use stoat_ferret_core::ffmpeg::filter::{Filter, FilterChain, FilterGraph, scale, pad, format};
//!
//! // Build a filter chain that scales, pads, and converts pixel format
//! let chain = FilterChain::new()
//!     .input("0:v")
//!     .filter(scale(1920, 1080))
//!     .filter(pad(1920, 1080, "black"))
//!     .filter(format("yuv420p"))
//!     .output("outv");
//!
//! assert_eq!(
//!     chain.to_string(),
//!     "[0:v]scale=w=1920:h=1080,pad=w=1920:h=1080:x=(ow-iw)/2:y=(oh-ih)/2:color=black,format=pix_fmts=yuv420p[outv]"
//! );
//! ```

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3_stub_gen::derive::{gen_stub_pyclass, gen_stub_pyfunction};
use std::collections::{HashMap, VecDeque};
use std::fmt;
use std::sync::atomic::{AtomicU64, Ordering};

/// Errors detected during filter graph validation.
///
/// These errors represent structural problems with the graph that would cause
/// FFmpeg to fail at runtime.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum GraphValidationError {
    /// A pad label has no matching connection in the graph.
    UnconnectedPad {
        /// The unmatched pad label.
        label: String,
    },
    /// The graph contains a cycle, preventing topological ordering.
    CycleDetected {
        /// Labels involved in the cycle.
        labels: Vec<String>,
    },
    /// The same label is used as an output by multiple chains.
    DuplicateLabel {
        /// The duplicated label.
        label: String,
    },
}

impl fmt::Display for GraphValidationError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            GraphValidationError::UnconnectedPad { label } => {
                write!(
                    f,
                    "Unconnected pad [{label}]: no matching output found. \
                     Add an output label [{label}] to another chain, or remove this input."
                )
            }
            GraphValidationError::CycleDetected { labels } => {
                let list = labels.join(", ");
                write!(
                    f,
                    "Cycle detected involving labels: [{list}]. \
                     Break the cycle by removing or redirecting one of these connections."
                )
            }
            GraphValidationError::DuplicateLabel { label } => {
                write!(
                    f,
                    "Duplicate output label [{label}]: each output label must be unique. \
                     Rename one of the outputs to a different label."
                )
            }
        }
    }
}

impl std::error::Error for GraphValidationError {}

/// Global counter for generating unique label prefixes across `LabelGenerator` instances.
static LABEL_COUNTER: AtomicU64 = AtomicU64::new(0);

/// Generates unique pad labels for filter graph composition.
///
/// Each generator has a unique prefix (based on a global atomic counter) to avoid
/// conflicts between independently created generators. Labels follow the pattern
/// `_auto_{prefix}_{seq}` (e.g., `_auto_0_0`, `_auto_0_1`).
#[derive(Debug)]
struct LabelGenerator {
    prefix: u64,
    next: u64,
}

impl LabelGenerator {
    /// Creates a new label generator with a unique prefix.
    fn new() -> Self {
        Self {
            prefix: LABEL_COUNTER.fetch_add(1, Ordering::Relaxed),
            next: 0,
        }
    }

    /// Generates the next unique label.
    fn next_label(&mut self) -> String {
        let label = format!("_auto_{}_{}", self.prefix, self.next);
        self.next += 1;
        label
    }
}

/// A single FFmpeg filter with optional parameters.
///
/// Filters are the building blocks of FFmpeg filtergraphs. Each filter has a name
/// and zero or more key-value parameters.
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::ffmpeg::filter::Filter;
///
/// let filter = Filter::new("scale")
///     .param("w", 1920)
///     .param("h", 1080);
///
/// assert_eq!(filter.to_string(), "scale=w=1920:h=1080");
/// ```
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct Filter {
    name: String,
    params: Vec<(String, String)>,
}

impl Filter {
    /// Creates a new filter with the given name.
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::ffmpeg::filter::Filter;
    ///
    /// let filter = Filter::new("scale");
    /// assert_eq!(filter.to_string(), "scale");
    /// ```
    #[must_use]
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            params: Vec::new(),
        }
    }

    /// Adds a parameter to the filter.
    ///
    /// Parameters are rendered as `key=value` pairs separated by colons.
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::ffmpeg::filter::Filter;
    ///
    /// let filter = Filter::new("scale")
    ///     .param("w", 1920)
    ///     .param("h", -1);
    ///
    /// assert_eq!(filter.to_string(), "scale=w=1920:h=-1");
    /// ```
    #[must_use]
    pub fn param(mut self, key: impl Into<String>, value: impl ToString) -> Self {
        self.params.push((key.into(), value.to_string()));
        self
    }
}

impl fmt::Display for Filter {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.name)?;
        if !self.params.is_empty() {
            write!(f, "=")?;
            let params: Vec<String> = self
                .params
                .iter()
                .map(|(k, v)| format!("{k}={v}"))
                .collect();
            write!(f, "{}", params.join(":"))?;
        }
        Ok(())
    }
}

#[pymethods]
impl Filter {
    /// Creates a new filter with the given name.
    #[new]
    fn py_new(name: String) -> Self {
        Self::new(name)
    }

    /// Adds a parameter to the filter.
    ///
    /// Parameters are rendered as `key=value` pairs separated by colons.
    /// Returns self to support method chaining.
    #[pyo3(name = "param")]
    fn py_param(mut slf: PyRefMut<'_, Self>, key: String, value: String) -> PyRefMut<'_, Self> {
        slf.params.push((key, value));
        slf
    }

    /// Returns a string representation of the filter.
    fn __str__(&self) -> String {
        self.to_string()
    }

    /// Returns a debug representation of the filter.
    fn __repr__(&self) -> String {
        format!("Filter({self})")
    }

    /// Creates a scale filter for resizing video.
    ///
    /// Use -1 for either dimension to auto-calculate while preserving aspect ratio.
    #[staticmethod]
    fn scale(width: i32, height: i32) -> Self {
        scale(width, height)
    }

    /// Creates a scale filter that maintains aspect ratio.
    ///
    /// Uses `force_original_aspect_ratio=decrease` to fit within the target dimensions.
    #[staticmethod]
    fn scale_fit(width: i32, height: i32) -> Self {
        scale_fit(width, height)
    }

    /// Creates a concat filter for concatenating multiple inputs.
    ///
    /// # Arguments
    ///
    /// * `n` - Number of input segments
    /// * `v` - Number of video streams per segment (0 or 1)
    /// * `a` - Number of audio streams per segment (0 or 1)
    #[staticmethod]
    fn concat(n: usize, v: usize, a: usize) -> Self {
        concat(n, v, a)
    }

    /// Creates a pad filter to add borders and center content.
    ///
    /// # Arguments
    ///
    /// * `width` - Target width after padding
    /// * `height` - Target height after padding
    /// * `color` - Color for the padding (e.g., "black", "#FF0000")
    #[staticmethod]
    fn pad(width: i32, height: i32, color: String) -> Self {
        pad(width, height, &color)
    }

    /// Creates a format filter for pixel format conversion.
    ///
    /// # Arguments
    ///
    /// * `pix_fmt` - Target pixel format (e.g., "yuv420p", "rgb24")
    #[staticmethod]
    fn format(pix_fmt: String) -> Self {
        format(&pix_fmt)
    }
}

/// Creates a concat filter for concatenating multiple inputs.
///
/// # Arguments
///
/// * `n` - Number of input segments
/// * `v` - Number of video streams per segment (0 or 1)
/// * `a` - Number of audio streams per segment (0 or 1)
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::ffmpeg::filter::concat;
///
/// let filter = concat(3, 1, 1);
/// assert_eq!(filter.to_string(), "concat=n=3:v=1:a=1");
/// ```
#[must_use]
pub fn concat(n: usize, v: usize, a: usize) -> Filter {
    Filter::new("concat")
        .param("n", n)
        .param("v", v)
        .param("a", a)
}

/// Creates a scale filter for resizing video.
///
/// Use -1 for either dimension to auto-calculate while preserving aspect ratio.
///
/// # Arguments
///
/// * `width` - Target width in pixels (-1 for auto)
/// * `height` - Target height in pixels (-1 for auto)
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::ffmpeg::filter::scale;
///
/// let filter = scale(1280, 720);
/// assert_eq!(filter.to_string(), "scale=w=1280:h=720");
///
/// // Auto-calculate height
/// let filter = scale(1920, -1);
/// assert_eq!(filter.to_string(), "scale=w=1920:h=-1");
/// ```
#[must_use]
pub fn scale(width: i32, height: i32) -> Filter {
    Filter::new("scale").param("w", width).param("h", height)
}

/// Creates a scale filter that maintains aspect ratio.
///
/// Uses `force_original_aspect_ratio=decrease` to fit within the target dimensions
/// while preserving the original aspect ratio.
///
/// # Arguments
///
/// * `width` - Maximum target width in pixels
/// * `height` - Maximum target height in pixels
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::ffmpeg::filter::scale_fit;
///
/// let filter = scale_fit(1920, 1080);
/// assert_eq!(
///     filter.to_string(),
///     "scale=w=1920:h=1080:force_original_aspect_ratio=decrease"
/// );
/// ```
#[must_use]
pub fn scale_fit(width: i32, height: i32) -> Filter {
    Filter::new("scale")
        .param("w", width)
        .param("h", height)
        .param("force_original_aspect_ratio", "decrease")
}

/// Creates a pad filter to add borders and center content.
///
/// Pads the video to the target dimensions, centering the original content.
///
/// # Arguments
///
/// * `width` - Target width after padding
/// * `height` - Target height after padding
/// * `color` - Color for the padding (e.g., "black", "#FF0000")
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::ffmpeg::filter::pad;
///
/// let filter = pad(1920, 1080, "black");
/// assert_eq!(
///     filter.to_string(),
///     "pad=w=1920:h=1080:x=(ow-iw)/2:y=(oh-ih)/2:color=black"
/// );
/// ```
#[must_use]
pub fn pad(width: i32, height: i32, color: &str) -> Filter {
    Filter::new("pad")
        .param("w", width)
        .param("h", height)
        .param("x", "(ow-iw)/2")
        .param("y", "(oh-ih)/2")
        .param("color", color)
}

/// Creates a format filter for pixel format conversion.
///
/// # Arguments
///
/// * `pix_fmt` - Target pixel format (e.g., "yuv420p", "rgb24")
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::ffmpeg::filter::format;
///
/// let filter = format("yuv420p");
/// assert_eq!(filter.to_string(), "format=pix_fmts=yuv420p");
/// ```
#[must_use]
pub fn format(pix_fmt: &str) -> Filter {
    Filter::new("format").param("pix_fmts", pix_fmt)
}

/// A chain of filters connected in sequence.
///
/// Filter chains have optional input labels, one or more filters, and optional
/// output labels. Within a chain, filters are connected with commas.
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::ffmpeg::filter::{FilterChain, scale, format};
///
/// let chain = FilterChain::new()
///     .input("0:v")
///     .filter(scale(1280, 720))
///     .filter(format("yuv420p"))
///     .output("scaled");
///
/// assert_eq!(
///     chain.to_string(),
///     "[0:v]scale=w=1280:h=720,format=pix_fmts=yuv420p[scaled]"
/// );
/// ```
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone, Default)]
pub struct FilterChain {
    inputs: Vec<String>,
    filters: Vec<Filter>,
    outputs: Vec<String>,
}

impl FilterChain {
    /// Creates a new empty filter chain.
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::ffmpeg::filter::FilterChain;
    ///
    /// let chain = FilterChain::new();
    /// ```
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// Adds an input label to the chain.
    ///
    /// Input labels reference streams from inputs or outputs of other chains.
    /// The label will be wrapped in brackets automatically.
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::ffmpeg::filter::{FilterChain, scale};
    ///
    /// let chain = FilterChain::new()
    ///     .input("0:v")
    ///     .filter(scale(1280, 720))
    ///     .output("out");
    ///
    /// assert!(chain.to_string().starts_with("[0:v]"));
    /// ```
    #[must_use]
    pub fn input(mut self, label: impl Into<String>) -> Self {
        self.inputs.push(format!("[{}]", label.into()));
        self
    }

    /// Adds a filter to the chain.
    ///
    /// Filters are applied in the order they are added.
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::ffmpeg::filter::{FilterChain, Filter};
    ///
    /// let chain = FilterChain::new()
    ///     .filter(Filter::new("null"));
    ///
    /// assert_eq!(chain.to_string(), "null");
    /// ```
    #[must_use]
    pub fn filter(mut self, f: Filter) -> Self {
        self.filters.push(f);
        self
    }

    /// Adds an output label to the chain.
    ///
    /// Output labels can be referenced by other chains or used in `-map` arguments.
    /// The label will be wrapped in brackets automatically.
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::ffmpeg::filter::{FilterChain, scale};
    ///
    /// let chain = FilterChain::new()
    ///     .input("0:v")
    ///     .filter(scale(1280, 720))
    ///     .output("scaled");
    ///
    /// assert!(chain.to_string().ends_with("[scaled]"));
    /// ```
    #[must_use]
    pub fn output(mut self, label: impl Into<String>) -> Self {
        self.outputs.push(format!("[{}]", label.into()));
        self
    }
}

impl fmt::Display for FilterChain {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.inputs.join(""))?;
        let filters: Vec<String> = self.filters.iter().map(|x| x.to_string()).collect();
        write!(f, "{}", filters.join(","))?;
        write!(f, "{}", self.outputs.join(""))?;
        Ok(())
    }
}

#[pymethods]
impl FilterChain {
    /// Creates a new empty filter chain.
    #[new]
    fn py_new() -> Self {
        Self::new()
    }

    /// Adds an input label to the chain.
    ///
    /// Input labels reference streams from inputs or outputs of other chains.
    /// The label will be wrapped in brackets automatically.
    /// Returns self to support method chaining.
    #[pyo3(name = "input")]
    fn py_input(mut slf: PyRefMut<'_, Self>, label: String) -> PyRefMut<'_, Self> {
        slf.inputs.push(format!("[{}]", label));
        slf
    }

    /// Adds a filter to the chain.
    ///
    /// Filters are applied in the order they are added.
    /// Returns self to support method chaining.
    #[pyo3(name = "filter")]
    fn py_filter(mut slf: PyRefMut<'_, Self>, f: Filter) -> PyRefMut<'_, Self> {
        slf.filters.push(f);
        slf
    }

    /// Adds an output label to the chain.
    ///
    /// Output labels can be referenced by other chains or used in `-map` arguments.
    /// The label will be wrapped in brackets automatically.
    /// Returns self to support method chaining.
    #[pyo3(name = "output")]
    fn py_output(mut slf: PyRefMut<'_, Self>, label: String) -> PyRefMut<'_, Self> {
        slf.outputs.push(format!("[{}]", label));
        slf
    }

    /// Returns a string representation of the filter chain.
    fn __str__(&self) -> String {
        self.to_string()
    }

    /// Returns a debug representation of the filter chain.
    fn __repr__(&self) -> String {
        format!(
            "FilterChain(inputs={}, filters={}, outputs={})",
            self.inputs.len(),
            self.filters.len(),
            self.outputs.len()
        )
    }
}

/// A complete filter graph composed of multiple filter chains.
///
/// Filter graphs are used with FFmpeg's `-filter_complex` argument. Multiple
/// chains are separated by semicolons.
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::ffmpeg::filter::{FilterGraph, FilterChain, scale, concat};
///
/// // Scale two inputs and concatenate them
/// let graph = FilterGraph::new()
///     .chain(
///         FilterChain::new()
///             .input("0:v")
///             .filter(scale(1280, 720))
///             .output("v0")
///     )
///     .chain(
///         FilterChain::new()
///             .input("1:v")
///             .filter(scale(1280, 720))
///             .output("v1")
///     )
///     .chain(
///         FilterChain::new()
///             .input("v0")
///             .input("v1")
///             .filter(concat(2, 1, 0))
///             .output("outv")
///     );
///
/// let expected = "[0:v]scale=w=1280:h=720[v0];[1:v]scale=w=1280:h=720[v1];[v0][v1]concat=n=2:v=1:a=0[outv]";
/// assert_eq!(graph.to_string(), expected);
/// ```
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone, Default)]
pub struct FilterGraph {
    chains: Vec<FilterChain>,
}

impl FilterGraph {
    /// Creates a new empty filter graph.
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::ffmpeg::filter::FilterGraph;
    ///
    /// let graph = FilterGraph::new();
    /// ```
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// Adds a filter chain to the graph.
    ///
    /// Chains are rendered in the order they are added, separated by semicolons.
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::ffmpeg::filter::{FilterGraph, FilterChain, Filter};
    ///
    /// let graph = FilterGraph::new()
    ///     .chain(FilterChain::new().filter(Filter::new("null")));
    ///
    /// assert_eq!(graph.to_string(), "null");
    /// ```
    #[must_use]
    pub fn chain(mut self, chain: FilterChain) -> Self {
        self.chains.push(chain);
        self
    }

    /// Validates the filter graph structure.
    ///
    /// Checks for duplicate output labels, unconnected input pads, and cycles
    /// (via Kahn's algorithm). Stream references like `[0:v]` or `[1:a]` are
    /// treated as external inputs and are not required to match an output label.
    ///
    /// Returns `Ok(())` if the graph is valid, or a list of all detected errors.
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::ffmpeg::filter::{FilterGraph, FilterChain, scale, concat};
    ///
    /// let graph = FilterGraph::new()
    ///     .chain(FilterChain::new().input("0:v").filter(scale(1280, 720)).output("v0"))
    ///     .chain(FilterChain::new().input("v0").filter(scale(640, 480)).output("out"));
    ///
    /// assert!(graph.validate().is_ok());
    /// ```
    pub fn validate(&self) -> Result<(), Vec<GraphValidationError>> {
        let mut errors = Vec::new();

        // Strip brackets: "[label]" -> "label"
        let strip =
            |s: &str| -> String { s.trim_start_matches('[').trim_end_matches(']').to_string() };

        // Returns true for stream references like "0:v", "1:a", "2:v"
        let is_stream_ref = |label: &str| -> bool {
            if let Some((left, _right)) = label.split_once(':') {
                left.chars().all(|c| c.is_ascii_digit())
            } else {
                false
            }
        };

        // Build output label -> chain index map, detect duplicates
        let mut output_map: HashMap<String, usize> = HashMap::new();
        for (chain_idx, chain) in self.chains.iter().enumerate() {
            for out in &chain.outputs {
                let label = strip(out);
                if let Some(_prev) = output_map.insert(label.clone(), chain_idx) {
                    errors.push(GraphValidationError::DuplicateLabel { label });
                }
            }
        }

        // Check for unconnected input pads (skip stream references)
        for chain in &self.chains {
            for inp in &chain.inputs {
                let label = strip(inp);
                if !is_stream_ref(&label) && !output_map.contains_key(&label) {
                    errors.push(GraphValidationError::UnconnectedPad { label });
                }
            }
        }

        // Cycle detection via Kahn's algorithm
        // Build adjacency: for each chain, find which chains feed into it
        let num_chains = self.chains.len();
        let mut in_degree = vec![0usize; num_chains];
        let mut adjacency: Vec<Vec<usize>> = vec![Vec::new(); num_chains];

        for (chain_idx, chain) in self.chains.iter().enumerate() {
            for inp in &chain.inputs {
                let label = strip(inp);
                if let Some(&src_chain) = output_map.get(&label) {
                    adjacency[src_chain].push(chain_idx);
                    in_degree[chain_idx] += 1;
                }
            }
        }

        // BFS with zero in-degree nodes
        let mut queue = VecDeque::new();
        for (i, &deg) in in_degree.iter().enumerate() {
            if deg == 0 {
                queue.push_back(i);
            }
        }

        let mut visited = 0usize;
        while let Some(node) = queue.pop_front() {
            visited += 1;
            for &neighbor in &adjacency[node] {
                in_degree[neighbor] -= 1;
                if in_degree[neighbor] == 0 {
                    queue.push_back(neighbor);
                }
            }
        }

        if visited < num_chains {
            // Collect labels from chains involved in the cycle
            let cycle_labels: Vec<String> = self
                .chains
                .iter()
                .enumerate()
                .filter(|(i, _)| in_degree[*i] > 0)
                .flat_map(|(_, chain)| chain.outputs.iter().map(|o| strip(o)).collect::<Vec<_>>())
                .collect();
            errors.push(GraphValidationError::CycleDetected {
                labels: cycle_labels,
            });
        }

        if errors.is_empty() {
            Ok(())
        } else {
            Err(errors)
        }
    }

    /// Validates the graph and returns the filter string if valid.
    ///
    /// Convenience method that calls [`validate()`](Self::validate) first, then
    /// serializes the graph to a string.
    ///
    /// # Errors
    ///
    /// Returns a list of validation errors if the graph is invalid.
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::ffmpeg::filter::{FilterGraph, FilterChain, scale};
    ///
    /// let graph = FilterGraph::new()
    ///     .chain(FilterChain::new().input("0:v").filter(scale(1280, 720)).output("out"));
    ///
    /// let result = graph.validated_to_string().unwrap();
    /// assert_eq!(result, "[0:v]scale=w=1280:h=720[out]");
    /// ```
    pub fn validated_to_string(&self) -> Result<String, Vec<GraphValidationError>> {
        self.validate()?;
        Ok(self.to_string())
    }

    /// Composes a chain of filters applied sequentially to an input stream.
    ///
    /// Creates intermediate pad labels automatically so each filter feeds into
    /// the next. Returns the output label of the final filter in the chain.
    ///
    /// # Arguments
    ///
    /// * `input` - The input pad label (e.g., `"0:v"`)
    /// * `filters` - A sequence of filters to apply in order
    ///
    /// # Errors
    ///
    /// Returns an error if `filters` is empty.
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::ffmpeg::filter::{FilterGraph, Filter, scale, format};
    ///
    /// let mut graph = FilterGraph::new();
    /// let out = graph.compose_chain("0:v", vec![scale(1280, 720), format("yuv420p")]).unwrap();
    /// assert!(!out.is_empty());
    /// assert!(graph.validate().is_ok());
    /// ```
    pub fn compose_chain(
        &mut self,
        input: &str,
        filters: Vec<Filter>,
    ) -> Result<String, String> {
        if filters.is_empty() {
            return Err("compose_chain requires at least one filter".to_string());
        }

        let mut gen = LabelGenerator::new();
        let output_label = gen.next_label();

        let mut chain = FilterChain::new().input(input);
        for f in filters {
            chain = chain.filter(f);
        }
        chain = chain.output(&output_label);

        self.chains.push(chain);
        Ok(output_label)
    }

    /// Splits one stream into multiple output streams.
    ///
    /// Uses the FFmpeg `split` (video) or `asplit` (audio) filter to duplicate
    /// the input stream. Returns the output labels for each branch.
    ///
    /// # Arguments
    ///
    /// * `input` - The input pad label (e.g., `"0:v"` or an auto-generated label)
    /// * `count` - Number of output streams to create (must be >= 2)
    /// * `audio` - If `true`, uses `asplit` instead of `split`
    ///
    /// # Errors
    ///
    /// Returns an error if `count` is less than 2.
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::ffmpeg::filter::FilterGraph;
    ///
    /// let mut graph = FilterGraph::new();
    /// let labels = graph.compose_branch("0:v", 3, false).unwrap();
    /// assert_eq!(labels.len(), 3);
    /// assert!(graph.validate().is_ok());
    /// ```
    pub fn compose_branch(
        &mut self,
        input: &str,
        count: usize,
        audio: bool,
    ) -> Result<Vec<String>, String> {
        if count < 2 {
            return Err("compose_branch requires count >= 2".to_string());
        }

        let mut gen = LabelGenerator::new();
        let filter_name = if audio { "asplit" } else { "split" };
        let split_filter = Filter::new(filter_name).param("outputs", count);

        let mut chain = FilterChain::new().input(input).filter(split_filter);
        let mut output_labels = Vec::with_capacity(count);
        for _ in 0..count {
            let label = gen.next_label();
            chain = chain.output(&label);
            output_labels.push(label);
        }

        self.chains.push(chain);
        Ok(output_labels)
    }

    /// Merges multiple input streams using a specified filter.
    ///
    /// Wires the given input labels into a single filter (e.g., `overlay`,
    /// `amix`, `concat`) and returns the output label.
    ///
    /// # Arguments
    ///
    /// * `inputs` - The input pad labels to merge
    /// * `merge_filter` - The filter to use for merging (e.g., `overlay()`, `concat(2,1,0)`)
    ///
    /// # Errors
    ///
    /// Returns an error if fewer than 2 inputs are provided.
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::ffmpeg::filter::{FilterGraph, Filter};
    ///
    /// let mut graph = FilterGraph::new();
    /// let out = graph.compose_merge(&["v0", "v1"], Filter::new("overlay")).unwrap();
    /// assert!(!out.is_empty());
    /// ```
    pub fn compose_merge(
        &mut self,
        inputs: &[&str],
        merge_filter: Filter,
    ) -> Result<String, String> {
        if inputs.len() < 2 {
            return Err("compose_merge requires at least 2 inputs".to_string());
        }

        let mut gen = LabelGenerator::new();
        let output_label = gen.next_label();

        let mut chain = FilterChain::new();
        for &inp in inputs {
            chain = chain.input(inp);
        }
        chain = chain.filter(merge_filter).output(&output_label);

        self.chains.push(chain);
        Ok(output_label)
    }
}

impl fmt::Display for FilterGraph {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let chains: Vec<String> = self.chains.iter().map(|c| c.to_string()).collect();
        write!(f, "{}", chains.join(";"))
    }
}

#[pymethods]
impl FilterGraph {
    /// Creates a new empty filter graph.
    #[new]
    fn py_new() -> Self {
        Self::new()
    }

    /// Adds a filter chain to the graph.
    ///
    /// Chains are rendered in the order they are added, separated by semicolons.
    /// Returns self to support method chaining.
    #[pyo3(name = "chain")]
    fn py_chain(mut slf: PyRefMut<'_, Self>, chain: FilterChain) -> PyRefMut<'_, Self> {
        slf.chains.push(chain);
        slf
    }

    /// Validates the filter graph structure.
    ///
    /// Checks for duplicate output labels, unconnected input pads, and cycles.
    /// Raises ValueError if any validation errors are found.
    #[pyo3(name = "validate")]
    fn py_validate(&self) -> PyResult<()> {
        self.validate().map_err(|errors| {
            let messages: Vec<String> = errors.iter().map(|e| e.to_string()).collect();
            PyValueError::new_err(messages.join("; "))
        })
    }

    /// Validates the graph and returns the filter string if valid.
    ///
    /// Convenience method that validates first, then serializes.
    /// Raises ValueError if any validation errors are found.
    #[pyo3(name = "validated_to_string")]
    fn py_validated_to_string(&self) -> PyResult<String> {
        self.validated_to_string().map_err(|errors| {
            let messages: Vec<String> = errors.iter().map(|e| e.to_string()).collect();
            PyValueError::new_err(messages.join("; "))
        })
    }

    /// Composes a chain of filters applied sequentially to an input stream.
    ///
    /// Creates intermediate pad labels automatically. Returns the output label
    /// of the final filter in the chain.
    ///
    /// Args:
    ///     input: The input pad label (e.g., "0:v").
    ///     filters: A list of filters to apply in order.
    ///
    /// Returns:
    ///     The output pad label.
    ///
    /// Raises:
    ///     ValueError: If filters list is empty.
    #[pyo3(name = "compose_chain")]
    fn py_compose_chain(
        mut slf: PyRefMut<'_, Self>,
        input: String,
        filters: Vec<Filter>,
    ) -> PyResult<String> {
        slf.compose_chain(&input, filters)
            .map_err(PyValueError::new_err)
    }

    /// Splits one stream into multiple output streams.
    ///
    /// Uses the FFmpeg split (video) or asplit (audio) filter to duplicate
    /// the input stream.
    ///
    /// Args:
    ///     input: The input pad label.
    ///     count: Number of output streams (must be >= 2).
    ///     audio: If True, uses asplit instead of split.
    ///
    /// Returns:
    ///     A list of output pad labels.
    ///
    /// Raises:
    ///     ValueError: If count < 2.
    #[pyo3(name = "compose_branch", signature = (input, count, audio = false))]
    fn py_compose_branch(
        mut slf: PyRefMut<'_, Self>,
        input: String,
        count: usize,
        audio: bool,
    ) -> PyResult<Vec<String>> {
        slf.compose_branch(&input, count, audio)
            .map_err(PyValueError::new_err)
    }

    /// Merges multiple input streams using a specified filter.
    ///
    /// Wires the given input labels into a single filter and returns
    /// the output label.
    ///
    /// Args:
    ///     inputs: List of input pad labels.
    ///     merge_filter: The filter to use for merging (e.g., overlay, amix, concat).
    ///
    /// Returns:
    ///     The output pad label.
    ///
    /// Raises:
    ///     ValueError: If fewer than 2 inputs are provided.
    #[pyo3(name = "compose_merge")]
    fn py_compose_merge(
        mut slf: PyRefMut<'_, Self>,
        inputs: Vec<String>,
        merge_filter: Filter,
    ) -> PyResult<String> {
        let refs: Vec<&str> = inputs.iter().map(|s| s.as_str()).collect();
        slf.compose_merge(&refs, merge_filter)
            .map_err(PyValueError::new_err)
    }

    /// Returns a string representation of the filter graph.
    fn __str__(&self) -> String {
        self.to_string()
    }

    /// Returns a debug representation of the filter graph.
    fn __repr__(&self) -> String {
        format!("FilterGraph(chains={})", self.chains.len())
    }
}

/// Python-exposed scale filter function.
#[gen_stub_pyfunction]
#[pyfunction]
#[pyo3(name = "scale_filter")]
pub fn py_scale_filter(width: i32, height: i32) -> Filter {
    scale(width, height)
}

/// Python-exposed concat filter function.
#[gen_stub_pyfunction]
#[pyfunction]
#[pyo3(name = "concat_filter")]
pub fn py_concat_filter(n: usize, v: usize, a: usize) -> Filter {
    concat(n, v, a)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_filter_no_params() {
        let filter = Filter::new("null");
        assert_eq!(filter.to_string(), "null");
    }

    #[test]
    fn test_filter_single_param() {
        let filter = Filter::new("scale").param("w", 1920);
        assert_eq!(filter.to_string(), "scale=w=1920");
    }

    #[test]
    fn test_filter_multiple_params() {
        let filter = Filter::new("scale").param("w", 1920).param("h", 1080);
        assert_eq!(filter.to_string(), "scale=w=1920:h=1080");
    }

    #[test]
    fn test_filter_clone() {
        let filter = Filter::new("scale").param("w", 1920);
        let cloned = filter.clone();
        assert_eq!(filter.to_string(), cloned.to_string());
    }

    #[test]
    fn test_concat_filter() {
        let filter = concat(3, 1, 1);
        assert_eq!(filter.to_string(), "concat=n=3:v=1:a=1");
    }

    #[test]
    fn test_concat_video_only() {
        let filter = concat(2, 1, 0);
        assert_eq!(filter.to_string(), "concat=n=2:v=1:a=0");
    }

    #[test]
    fn test_scale_filter() {
        let filter = scale(1280, 720);
        assert_eq!(filter.to_string(), "scale=w=1280:h=720");
    }

    #[test]
    fn test_scale_auto_height() {
        let filter = scale(1920, -1);
        assert_eq!(filter.to_string(), "scale=w=1920:h=-1");
    }

    #[test]
    fn test_scale_auto_width() {
        let filter = scale(-1, 1080);
        assert_eq!(filter.to_string(), "scale=w=-1:h=1080");
    }

    #[test]
    fn test_scale_fit_filter() {
        let filter = scale_fit(1920, 1080);
        assert_eq!(
            filter.to_string(),
            "scale=w=1920:h=1080:force_original_aspect_ratio=decrease"
        );
    }

    #[test]
    fn test_pad_filter() {
        let filter = pad(1920, 1080, "black");
        assert_eq!(
            filter.to_string(),
            "pad=w=1920:h=1080:x=(ow-iw)/2:y=(oh-ih)/2:color=black"
        );
    }

    #[test]
    fn test_pad_filter_hex_color() {
        let filter = pad(1280, 720, "#FF0000");
        assert_eq!(
            filter.to_string(),
            "pad=w=1280:h=720:x=(ow-iw)/2:y=(oh-ih)/2:color=#FF0000"
        );
    }

    #[test]
    fn test_format_filter() {
        let filter = format("yuv420p");
        assert_eq!(filter.to_string(), "format=pix_fmts=yuv420p");
    }

    #[test]
    fn test_format_filter_rgb() {
        let filter = format("rgb24");
        assert_eq!(filter.to_string(), "format=pix_fmts=rgb24");
    }

    #[test]
    fn test_filter_chain_empty() {
        let chain = FilterChain::new();
        assert_eq!(chain.to_string(), "");
    }

    #[test]
    fn test_filter_chain_single_filter() {
        let chain = FilterChain::new().filter(Filter::new("null"));
        assert_eq!(chain.to_string(), "null");
    }

    #[test]
    fn test_filter_chain_with_input() {
        let chain = FilterChain::new().input("0:v").filter(scale(1280, 720));
        assert_eq!(chain.to_string(), "[0:v]scale=w=1280:h=720");
    }

    #[test]
    fn test_filter_chain_with_output() {
        let chain = FilterChain::new().filter(scale(1280, 720)).output("scaled");
        assert_eq!(chain.to_string(), "scale=w=1280:h=720[scaled]");
    }

    #[test]
    fn test_filter_chain_full() {
        let chain = FilterChain::new()
            .input("0:v")
            .filter(scale(1280, 720))
            .output("scaled");
        assert_eq!(chain.to_string(), "[0:v]scale=w=1280:h=720[scaled]");
    }

    #[test]
    fn test_filter_chain_multiple_filters() {
        let chain = FilterChain::new()
            .input("0:v")
            .filter(scale(1920, 1080))
            .filter(format("yuv420p"))
            .output("out");
        assert_eq!(
            chain.to_string(),
            "[0:v]scale=w=1920:h=1080,format=pix_fmts=yuv420p[out]"
        );
    }

    #[test]
    fn test_filter_chain_multiple_inputs() {
        let chain = FilterChain::new()
            .input("0:v")
            .input("1:v")
            .filter(concat(2, 1, 0))
            .output("outv");
        assert_eq!(chain.to_string(), "[0:v][1:v]concat=n=2:v=1:a=0[outv]");
    }

    #[test]
    fn test_filter_chain_multiple_outputs() {
        let chain = FilterChain::new()
            .input("0:v")
            .filter(Filter::new("split"))
            .output("v1")
            .output("v2");
        assert_eq!(chain.to_string(), "[0:v]split[v1][v2]");
    }

    #[test]
    fn test_filter_chain_clone() {
        let chain = FilterChain::new()
            .input("0:v")
            .filter(scale(1280, 720))
            .output("out");
        let cloned = chain.clone();
        assert_eq!(chain.to_string(), cloned.to_string());
    }

    #[test]
    fn test_filter_graph_empty() {
        let graph = FilterGraph::new();
        assert_eq!(graph.to_string(), "");
    }

    #[test]
    fn test_filter_graph_single_chain() {
        let graph = FilterGraph::new().chain(
            FilterChain::new()
                .input("0:v")
                .filter(scale(1280, 720))
                .output("out"),
        );
        assert_eq!(graph.to_string(), "[0:v]scale=w=1280:h=720[out]");
    }

    #[test]
    fn test_filter_graph_multiple_chains() {
        let graph = FilterGraph::new()
            .chain(
                FilterChain::new()
                    .input("0:v")
                    .filter(scale(1280, 720))
                    .output("v0"),
            )
            .chain(
                FilterChain::new()
                    .input("1:v")
                    .filter(scale(1280, 720))
                    .output("v1"),
            );
        assert_eq!(
            graph.to_string(),
            "[0:v]scale=w=1280:h=720[v0];[1:v]scale=w=1280:h=720[v1]"
        );
    }

    #[test]
    fn test_filter_graph_concat_workflow() {
        // A realistic workflow: scale two inputs and concatenate
        let graph = FilterGraph::new()
            .chain(
                FilterChain::new()
                    .input("0:v")
                    .filter(scale(1280, 720))
                    .output("v0"),
            )
            .chain(
                FilterChain::new()
                    .input("1:v")
                    .filter(scale(1280, 720))
                    .output("v1"),
            )
            .chain(
                FilterChain::new()
                    .input("v0")
                    .input("v1")
                    .filter(concat(2, 1, 0))
                    .output("outv"),
            );
        assert_eq!(
            graph.to_string(),
            "[0:v]scale=w=1280:h=720[v0];[1:v]scale=w=1280:h=720[v1];[v0][v1]concat=n=2:v=1:a=0[outv]"
        );
    }

    #[test]
    fn test_filter_graph_scale_pad_format_workflow() {
        // Scale to fit, pad to fill, convert format
        let graph = FilterGraph::new().chain(
            FilterChain::new()
                .input("0:v")
                .filter(scale_fit(1920, 1080))
                .filter(pad(1920, 1080, "black"))
                .filter(format("yuv420p"))
                .output("outv"),
        );
        assert_eq!(
            graph.to_string(),
            "[0:v]scale=w=1920:h=1080:force_original_aspect_ratio=decrease,pad=w=1920:h=1080:x=(ow-iw)/2:y=(oh-ih)/2:color=black,format=pix_fmts=yuv420p[outv]"
        );
    }

    #[test]
    fn test_filter_graph_clone() {
        let graph = FilterGraph::new().chain(
            FilterChain::new()
                .input("0:v")
                .filter(scale(1280, 720))
                .output("out"),
        );
        let cloned = graph.clone();
        assert_eq!(graph.to_string(), cloned.to_string());
    }

    #[test]
    fn test_integration_with_ffmpeg_command_string() {
        // Verify the filter graph produces valid -filter_complex values
        let graph = FilterGraph::new().chain(
            FilterChain::new()
                .input("0:v")
                .filter(scale(1280, 720))
                .output("scaled"),
        );

        let filter_complex = graph.to_string();
        assert_eq!(filter_complex, "[0:v]scale=w=1280:h=720[scaled]");

        // This string can be passed to FFmpegCommand::filter_complex()
    }

    // ========== Graph Validation Tests ==========

    #[test]
    fn test_validate_valid_linear_graph() {
        let graph = FilterGraph::new()
            .chain(
                FilterChain::new()
                    .input("0:v")
                    .filter(scale(1280, 720))
                    .output("v0"),
            )
            .chain(
                FilterChain::new()
                    .input("v0")
                    .filter(format("yuv420p"))
                    .output("out"),
            );
        assert!(graph.validate().is_ok());
    }

    #[test]
    fn test_validate_valid_concat_graph() {
        let graph = FilterGraph::new()
            .chain(
                FilterChain::new()
                    .input("0:v")
                    .filter(scale(1280, 720))
                    .output("v0"),
            )
            .chain(
                FilterChain::new()
                    .input("1:v")
                    .filter(scale(1280, 720))
                    .output("v1"),
            )
            .chain(
                FilterChain::new()
                    .input("v0")
                    .input("v1")
                    .filter(concat(2, 1, 0))
                    .output("outv"),
            );
        assert!(graph.validate().is_ok());
    }

    #[test]
    fn test_validate_stream_refs_not_checked() {
        // Stream references like 0:v, 1:a should pass validation
        let graph = FilterGraph::new().chain(
            FilterChain::new()
                .input("0:v")
                .input("1:a")
                .filter(Filter::new("amerge"))
                .output("out"),
        );
        assert!(graph.validate().is_ok());
    }

    #[test]
    fn test_validate_empty_graph() {
        let graph = FilterGraph::new();
        assert!(graph.validate().is_ok());
    }

    #[test]
    fn test_validate_single_chain_no_labels() {
        let graph = FilterGraph::new().chain(FilterChain::new().filter(Filter::new("null")));
        assert!(graph.validate().is_ok());
    }

    #[test]
    fn test_validate_unconnected_pad() {
        let graph = FilterGraph::new().chain(
            FilterChain::new()
                .input("missing")
                .filter(scale(1280, 720))
                .output("out"),
        );
        let errors = graph.validate().unwrap_err();
        assert_eq!(errors.len(), 1);
        assert!(matches!(
            &errors[0],
            GraphValidationError::UnconnectedPad { label } if label == "missing"
        ));
    }

    #[test]
    fn test_validate_duplicate_label() {
        let graph = FilterGraph::new()
            .chain(
                FilterChain::new()
                    .input("0:v")
                    .filter(scale(1280, 720))
                    .output("dup"),
            )
            .chain(
                FilterChain::new()
                    .input("1:v")
                    .filter(scale(640, 480))
                    .output("dup"),
            );
        let errors = graph.validate().unwrap_err();
        assert!(errors.iter().any(
            |e| matches!(e, GraphValidationError::DuplicateLabel { label } if label == "dup")
        ));
    }

    #[test]
    fn test_validate_cycle_detected() {
        // Chain 0: input [a] -> output [b]
        // Chain 1: input [b] -> output [a]
        let graph = FilterGraph::new()
            .chain(
                FilterChain::new()
                    .input("a")
                    .filter(Filter::new("null"))
                    .output("b"),
            )
            .chain(
                FilterChain::new()
                    .input("b")
                    .filter(Filter::new("null"))
                    .output("a"),
            );
        let errors = graph.validate().unwrap_err();
        assert!(errors
            .iter()
            .any(|e| matches!(e, GraphValidationError::CycleDetected { .. })));
    }

    #[test]
    fn test_validate_multiple_errors() {
        // Both unconnected pad and duplicate label
        let graph = FilterGraph::new()
            .chain(
                FilterChain::new()
                    .input("0:v")
                    .filter(Filter::new("null"))
                    .output("dup"),
            )
            .chain(
                FilterChain::new()
                    .input("1:v")
                    .filter(Filter::new("null"))
                    .output("dup"),
            )
            .chain(
                FilterChain::new()
                    .input("missing")
                    .filter(Filter::new("null"))
                    .output("out"),
            );
        let errors = graph.validate().unwrap_err();
        assert!(errors.len() >= 2);
    }

    #[test]
    fn test_validated_to_string_valid() {
        let graph = FilterGraph::new().chain(
            FilterChain::new()
                .input("0:v")
                .filter(scale(1280, 720))
                .output("out"),
        );
        let result = graph.validated_to_string().unwrap();
        assert_eq!(result, "[0:v]scale=w=1280:h=720[out]");
    }

    #[test]
    fn test_validated_to_string_invalid() {
        let graph = FilterGraph::new().chain(
            FilterChain::new()
                .input("missing")
                .filter(Filter::new("null"))
                .output("out"),
        );
        assert!(graph.validated_to_string().is_err());
    }

    #[test]
    fn test_validation_error_display_unconnected() {
        let err = GraphValidationError::UnconnectedPad {
            label: "foo".to_string(),
        };
        let msg = err.to_string();
        assert!(msg.contains("foo"));
        assert!(msg.contains("Unconnected pad"));
    }

    #[test]
    fn test_validation_error_display_cycle() {
        let err = GraphValidationError::CycleDetected {
            labels: vec!["a".to_string(), "b".to_string()],
        };
        let msg = err.to_string();
        assert!(msg.contains("Cycle detected"));
        assert!(msg.contains("a, b"));
    }

    #[test]
    fn test_validation_error_display_duplicate() {
        let err = GraphValidationError::DuplicateLabel {
            label: "dup".to_string(),
        };
        let msg = err.to_string();
        assert!(msg.contains("Duplicate output label"));
        assert!(msg.contains("dup"));
    }

    #[test]
    fn test_existing_graph_to_string_unchanged() {
        // Verify existing to_string() / Display is not affected by validation code
        let graph = FilterGraph::new()
            .chain(
                FilterChain::new()
                    .input("0:v")
                    .filter(scale(1280, 720))
                    .output("v0"),
            )
            .chain(
                FilterChain::new()
                    .input("1:v")
                    .filter(scale(1280, 720))
                    .output("v1"),
            )
            .chain(
                FilterChain::new()
                    .input("v0")
                    .input("v1")
                    .filter(concat(2, 1, 0))
                    .output("outv"),
            );
        assert_eq!(
            graph.to_string(),
            "[0:v]scale=w=1280:h=720[v0];[1:v]scale=w=1280:h=720[v1];[v0][v1]concat=n=2:v=1:a=0[outv]"
        );
    }

    #[test]
    fn test_validate_graph_with_split() {
        // One output feeding two inputs (split pattern)
        let graph = FilterGraph::new()
            .chain(
                FilterChain::new()
                    .input("0:v")
                    .filter(Filter::new("split"))
                    .output("s1")
                    .output("s2"),
            )
            .chain(
                FilterChain::new()
                    .input("s1")
                    .filter(scale(1280, 720))
                    .output("out1"),
            )
            .chain(
                FilterChain::new()
                    .input("s2")
                    .filter(scale(640, 480))
                    .output("out2"),
            );
        assert!(graph.validate().is_ok());
    }

    // ========== Label Generator Tests ==========

    #[test]
    fn test_label_generator_produces_unique_labels() {
        let mut gen = LabelGenerator::new();
        let l1 = gen.next_label();
        let l2 = gen.next_label();
        let l3 = gen.next_label();
        assert_ne!(l1, l2);
        assert_ne!(l2, l3);
        assert_ne!(l1, l3);
        assert!(l1.starts_with("_auto_"));
        assert!(l2.starts_with("_auto_"));
    }

    #[test]
    fn test_label_generator_different_instances_unique() {
        let mut gen1 = LabelGenerator::new();
        let mut gen2 = LabelGenerator::new();
        let l1 = gen1.next_label();
        let l2 = gen2.next_label();
        assert_ne!(l1, l2);
    }

    // ========== Compose Chain Tests ==========

    #[test]
    fn test_compose_chain_single_filter() {
        let mut graph = FilterGraph::new();
        let out = graph.compose_chain("0:v", vec![scale(1280, 720)]).unwrap();
        assert!(!out.is_empty());
        assert!(graph.validate().is_ok());
        let s = graph.to_string();
        assert!(s.contains("[0:v]"));
        assert!(s.contains("scale=w=1280:h=720"));
        assert!(s.contains(&format!("[{out}]")));
    }

    #[test]
    fn test_compose_chain_multiple_filters() {
        let mut graph = FilterGraph::new();
        let out = graph
            .compose_chain("0:v", vec![scale(1280, 720), format("yuv420p")])
            .unwrap();
        assert!(graph.validate().is_ok());
        let s = graph.to_string();
        assert!(s.contains("scale=w=1280:h=720,format=pix_fmts=yuv420p"));
        assert!(s.contains(&format!("[{out}]")));
    }

    #[test]
    fn test_compose_chain_empty_filters_error() {
        let mut graph = FilterGraph::new();
        let result = graph.compose_chain("0:v", vec![]);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("at least one filter"));
    }

    #[test]
    fn test_compose_chain_chained_operations() {
        let mut graph = FilterGraph::new();
        let mid = graph.compose_chain("0:v", vec![scale(1280, 720)]).unwrap();
        let out = graph
            .compose_chain(&mid, vec![format("yuv420p")])
            .unwrap();
        assert!(graph.validate().is_ok());
        let s = graph.to_string();
        assert!(s.contains(";"));
        assert!(s.contains(&format!("[{mid}]")));
        assert!(s.contains(&format!("[{out}]")));
    }

    // ========== Compose Branch Tests ==========

    #[test]
    fn test_compose_branch_video() {
        let mut graph = FilterGraph::new();
        let labels = graph.compose_branch("0:v", 3, false).unwrap();
        assert_eq!(labels.len(), 3);
        assert!(graph.validate().is_ok());
        let s = graph.to_string();
        assert!(s.contains("[0:v]"));
        assert!(s.contains("split=outputs=3"));
        for label in &labels {
            assert!(s.contains(&format!("[{label}]")));
        }
    }

    #[test]
    fn test_compose_branch_audio() {
        let mut graph = FilterGraph::new();
        let labels = graph.compose_branch("0:a", 2, true).unwrap();
        assert_eq!(labels.len(), 2);
        let s = graph.to_string();
        assert!(s.contains("asplit=outputs=2"));
    }

    #[test]
    fn test_compose_branch_count_too_low() {
        let mut graph = FilterGraph::new();
        let result = graph.compose_branch("0:v", 1, false);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("count >= 2"));
    }

    #[test]
    fn test_compose_branch_labels_unique() {
        let mut graph = FilterGraph::new();
        let labels = graph.compose_branch("0:v", 4, false).unwrap();
        let unique: std::collections::HashSet<&String> = labels.iter().collect();
        assert_eq!(unique.len(), 4);
    }

    // ========== Compose Merge Tests ==========

    #[test]
    fn test_compose_merge_overlay() {
        let mut graph = FilterGraph::new();
        let out = graph
            .compose_merge(&["v0", "v1"], Filter::new("overlay"))
            .unwrap();
        assert!(!out.is_empty());
        let s = graph.to_string();
        assert!(s.contains("[v0][v1]"));
        assert!(s.contains("overlay"));
        assert!(s.contains(&format!("[{out}]")));
    }

    #[test]
    fn test_compose_merge_concat() {
        let mut graph = FilterGraph::new();
        let out = graph
            .compose_merge(&["v0", "v1", "v2"], concat(3, 1, 0))
            .unwrap();
        assert!(!out.is_empty());
        let s = graph.to_string();
        assert!(s.contains("[v0][v1][v2]"));
        assert!(s.contains("concat=n=3:v=1:a=0"));
    }

    #[test]
    fn test_compose_merge_too_few_inputs() {
        let mut graph = FilterGraph::new();
        let result = graph.compose_merge(&["v0"], Filter::new("overlay"));
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("at least 2 inputs"));
    }

    // ========== Composition Integration Tests ==========

    #[test]
    fn test_compose_chain_branch_merge() {
        let mut graph = FilterGraph::new();
        let scaled = graph.compose_chain("0:v", vec![scale(1280, 720)]).unwrap();
        let branches = graph.compose_branch(&scaled, 2, false).unwrap();
        let out = graph
            .compose_merge(
                &branches.iter().map(|s| s.as_str()).collect::<Vec<_>>(),
                concat(2, 1, 0),
            )
            .unwrap();

        assert!(graph.validate().is_ok());
        let s = graph.to_string();
        assert!(s.contains("scale=w=1280:h=720"));
        assert!(s.contains("split=outputs=2"));
        assert!(s.contains("concat=n=2:v=1:a=0"));
        assert!(s.contains(&format!("[{out}]")));
    }

    #[test]
    fn test_compose_two_inputs_merge() {
        let mut graph = FilterGraph::new();
        let v0 = graph.compose_chain("0:v", vec![scale(1280, 720)]).unwrap();
        let v1 = graph.compose_chain("1:v", vec![scale(1280, 720)]).unwrap();
        let out = graph
            .compose_merge(&[&v0, &v1], Filter::new("overlay"))
            .unwrap();

        assert!(graph.validate().is_ok());
        let s = graph.to_string();
        assert_eq!(s.matches(';').count(), 2);
        assert!(s.contains(&format!("[{out}]")));
    }

    #[test]
    fn test_compose_validates_automatically() {
        let mut graph = FilterGraph::new();
        let out = graph
            .compose_chain("0:v", vec![scale(1280, 720), format("yuv420p")])
            .unwrap();
        let result = graph.validated_to_string();
        assert!(result.is_ok());
        assert!(result.unwrap().contains(&format!("[{out}]")));
    }

    #[test]
    fn test_compose_mixed_with_manual_chains() {
        let mut graph = FilterGraph::new();
        let auto_out = graph.compose_chain("0:v", vec![scale(1280, 720)]).unwrap();

        let graph = graph.chain(
            FilterChain::new()
                .input(&auto_out)
                .filter(format("yuv420p"))
                .output("final"),
        );

        assert!(graph.validate().is_ok());
        let s = graph.to_string();
        assert!(s.contains("[final]"));
    }
}
