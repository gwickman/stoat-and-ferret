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

use pyo3::prelude::*;
use pyo3_stub_gen::derive::{gen_stub_pyclass, gen_stub_pyfunction};
use std::fmt;

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
}
