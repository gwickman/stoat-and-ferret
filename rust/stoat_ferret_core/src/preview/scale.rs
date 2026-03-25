//! Preview scale filter injection.
//!
//! Provides a function to append a resolution scale filter to a filter graph
//! for preview playback at reduced resolution.

use pyo3::prelude::*;

use crate::ffmpeg::filter::{scale, FilterChain, FilterGraph};

/// Appends a scale filter with the given dimensions to the filter graph.
///
/// The scale filter is added as a new chain at the end of the graph.
/// If the graph is empty, a single chain containing only the scale filter
/// is created.
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::preview::scale::inject_preview_scale;
/// use stoat_ferret_core::ffmpeg::filter::{FilterGraph, FilterChain, Filter};
///
/// let graph = FilterGraph::new()
///     .chain(FilterChain::new().filter(Filter::new("format")));
///
/// let result = inject_preview_scale(&graph, 640, 480);
/// assert_eq!(result.chain_count(), 2);
/// ```
pub fn inject_preview_scale(graph: &FilterGraph, width: i32, height: i32) -> FilterGraph {
    let scale_chain = FilterChain::new().filter(scale(width, height));

    let mut result = graph.clone();
    result = result.chain(scale_chain);
    result
}

/// Python binding: Injects a preview scale filter into the graph.
#[pyfunction]
#[pyo3(name = "inject_preview_scale")]
pub fn py_inject_preview_scale(graph: &FilterGraph, width: i32, height: i32) -> FilterGraph {
    inject_preview_scale(graph, width, height)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::ffmpeg::filter::Filter;

    #[test]
    fn test_inject_into_empty_graph() {
        let graph = FilterGraph::new();
        let result = inject_preview_scale(&graph, 640, 480);
        assert_eq!(result.chain_count(), 1);
        assert_eq!(result.chains()[0].filter_count(), 1);
        assert_eq!(result.chains()[0].filters()[0].name(), "scale");
    }

    #[test]
    fn test_inject_adds_one_chain() {
        let graph = FilterGraph::new()
            .chain(FilterChain::new().filter(Filter::new("format")))
            .chain(FilterChain::new().filter(Filter::new("setpts")));

        let result = inject_preview_scale(&graph, 1280, 720);
        assert_eq!(result.chain_count(), 3);
    }

    #[test]
    fn test_inject_preserves_existing_filters() {
        let graph = FilterGraph::new().chain(
            FilterChain::new()
                .filter(Filter::new("hue"))
                .filter(Filter::new("format")),
        );

        let result = inject_preview_scale(&graph, 640, 480);
        // Original chain preserved
        assert_eq!(result.chains()[0].filter_count(), 2);
        assert_eq!(result.chains()[0].filters()[0].name(), "hue");
        assert_eq!(result.chains()[0].filters()[1].name(), "format");
        // New scale chain appended
        assert_eq!(result.chains()[1].filter_count(), 1);
        assert_eq!(result.chains()[1].filters()[0].name(), "scale");
    }

    #[test]
    fn test_total_filter_count_increases_by_one() {
        let graph = FilterGraph::new()
            .chain(FilterChain::new().filter(Filter::new("scale")).filter(Filter::new("format")));

        let original_total: usize = graph.chains().iter().map(|c| c.filter_count()).sum();
        let result = inject_preview_scale(&graph, 640, 480);
        let result_total: usize = result.chains().iter().map(|c| c.filter_count()).sum();
        assert_eq!(result_total, original_total + 1);
    }
}

#[cfg(test)]
mod proptests {
    use super::*;
    use crate::ffmpeg::filter::Filter;
    use proptest::prelude::*;

    const ALL_FILTER_NAMES: &[&str] = &[
        "scale",
        "format",
        "setpts",
        "asetpts",
        "concat",
        "hue",
        "eq",
        "colorbalance",
        "unsharp",
        "gblur",
    ];

    fn arb_filter_name() -> impl Strategy<Value = &'static str> {
        proptest::sample::select(ALL_FILTER_NAMES)
    }

    fn arb_filter_chain() -> impl Strategy<Value = FilterChain> {
        proptest::collection::vec(arb_filter_name(), 1..=10).prop_map(|names| {
            let mut chain = FilterChain::new();
            for name in names {
                chain = chain.filter(Filter::new(name));
            }
            chain
        })
    }

    fn arb_filter_graph() -> impl Strategy<Value = FilterGraph> {
        proptest::collection::vec(arb_filter_chain(), 0..=5).prop_map(|chains| {
            let mut graph = FilterGraph::new();
            for chain in chains {
                graph = graph.chain(chain);
            }
            graph
        })
    }

    proptest! {
        /// inject_preview_scale adds exactly one filter to the total count.
        #[test]
        fn scale_adds_exactly_one_filter(
            graph in arb_filter_graph(),
            width in 1i32..=3840,
            height in 1i32..=2160,
        ) {
            let original_total: usize = graph.chains().iter().map(|c| c.filter_count()).sum();
            let result = inject_preview_scale(&graph, width, height);
            let result_total: usize = result.chains().iter().map(|c| c.filter_count()).sum();
            prop_assert_eq!(result_total, original_total + 1);
        }

        /// inject_preview_scale never removes existing filters.
        #[test]
        fn scale_never_removes_existing(
            graph in arb_filter_graph(),
            width in 1i32..=3840,
            height in 1i32..=2160,
        ) {
            let result = inject_preview_scale(&graph, width, height);
            // All original chains preserved at their positions
            for (i, original_chain) in graph.chains().iter().enumerate() {
                let result_chain = &result.chains()[i];
                prop_assert_eq!(
                    result_chain.filter_count(),
                    original_chain.filter_count(),
                    "chain {} filter count changed",
                    i
                );
                for (j, original_filter) in original_chain.filters().iter().enumerate() {
                    prop_assert_eq!(
                        result_chain.filters()[j].name(),
                        original_filter.name(),
                        "chain {} filter {} name changed",
                        i,
                        j
                    );
                }
            }
        }
    }
}
