//! Filter simplification logic for preview quality levels.
//!
//! Provides functions to reduce filter graph complexity by removing expensive
//! filters at Draft and Medium quality levels.

use pyo3::prelude::*;

use crate::ffmpeg::filter::{FilterChain, FilterGraph};
use crate::preview::PreviewQuality;

/// The 11 known expensive filters from the Phase 4 design spec.
const EXPENSIVE_FILTERS: &[&str] = &[
    "hue",
    "eq",
    "colorbalance",
    "unsharp",
    "gblur",
    "boxblur",
    "smartblur",
    "atadenoise",
    "nlmeans",
    "perspective",
    "lenscorrection",
];

/// Returns true if the given filter name is classified as expensive.
///
/// Expensive filters are those that have high computational cost and can be
/// safely removed during preview without affecting structural correctness.
pub fn is_expensive_filter(name: &str) -> bool {
    EXPENSIVE_FILTERS.contains(&name)
}

/// Simplifies a filter chain by removing expensive filters based on quality.
///
/// - **High**: Returns an identical clone of the chain.
/// - **Medium**: Removes filters from `EXPENSIVE_FILTERS`.
/// - **Draft**: Removes filters from `EXPENSIVE_FILTERS`.
///
/// At Draft and Medium levels, the current behavior is identical — both remove
/// all expensive filters. This provides a clear extension point for future
/// graduated simplification (e.g., Medium could keep some filters).
pub fn simplify_filter_chain(chain: &FilterChain, quality: PreviewQuality) -> FilterChain {
    match quality {
        PreviewQuality::High => chain.clone(),
        PreviewQuality::Medium | PreviewQuality::Draft => {
            let mut simplified = FilterChain::new();
            for filter in chain.filters() {
                if !is_expensive_filter(filter.name()) {
                    simplified = simplified.filter(filter.clone());
                }
            }
            simplified
        }
    }
}

/// Simplifies a filter graph by simplifying each chain based on quality.
///
/// - **High**: Returns an identical clone of the graph.
/// - **Medium/Draft**: Simplifies each chain individually.
pub fn simplify_filter_graph(graph: &FilterGraph, quality: PreviewQuality) -> FilterGraph {
    match quality {
        PreviewQuality::High => graph.clone(),
        PreviewQuality::Medium | PreviewQuality::Draft => {
            let mut simplified = FilterGraph::new();
            for chain in graph.chains() {
                simplified = simplified.chain(simplify_filter_chain(chain, quality));
            }
            simplified
        }
    }
}

/// Python binding: Returns true if the filter name is expensive.
#[pyfunction]
#[pyo3(name = "is_expensive_filter")]
pub fn py_is_expensive_filter(name: &str) -> bool {
    is_expensive_filter(name)
}

/// Python binding: Simplifies a filter chain based on preview quality.
#[pyfunction]
#[pyo3(name = "simplify_filter_chain")]
pub fn py_simplify_filter_chain(chain: &FilterChain, quality: PreviewQuality) -> FilterChain {
    simplify_filter_chain(chain, quality)
}

/// Python binding: Simplifies a filter graph based on preview quality.
#[pyfunction]
#[pyo3(name = "simplify_filter_graph")]
pub fn py_simplify_filter_graph(graph: &FilterGraph, quality: PreviewQuality) -> FilterGraph {
    simplify_filter_graph(graph, quality)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::ffmpeg::filter::Filter;

    #[test]
    fn test_expensive_filters_classified() {
        for name in EXPENSIVE_FILTERS {
            assert!(
                is_expensive_filter(name),
                "{name} should be classified as expensive"
            );
        }
    }

    #[test]
    fn test_cheap_filters_not_expensive() {
        let cheap = ["scale", "format", "setpts", "asetpts", "concat"];
        for name in cheap {
            assert!(
                !is_expensive_filter(name),
                "{name} should not be classified as expensive"
            );
        }
    }

    #[test]
    fn test_simplify_chain_high_preserves_all() {
        let chain = FilterChain::new()
            .filter(Filter::new("scale"))
            .filter(Filter::new("hue"))
            .filter(Filter::new("format"));

        let result = simplify_filter_chain(&chain, PreviewQuality::High);
        assert_eq!(result.filter_count(), 3);
    }

    #[test]
    fn test_simplify_chain_draft_removes_expensive() {
        let chain = FilterChain::new()
            .filter(Filter::new("scale"))
            .filter(Filter::new("hue"))
            .filter(Filter::new("eq"))
            .filter(Filter::new("format"));

        let result = simplify_filter_chain(&chain, PreviewQuality::Draft);
        assert_eq!(result.filter_count(), 2);
        // Only scale and format should remain
        assert_eq!(result.filters()[0].name(), "scale");
        assert_eq!(result.filters()[1].name(), "format");
    }

    #[test]
    fn test_simplify_chain_medium_removes_expensive() {
        let chain = FilterChain::new()
            .filter(Filter::new("scale"))
            .filter(Filter::new("nlmeans"))
            .filter(Filter::new("format"));

        let result = simplify_filter_chain(&chain, PreviewQuality::Medium);
        assert_eq!(result.filter_count(), 2);
    }

    #[test]
    fn test_simplify_graph_high_preserves_all() {
        let graph = FilterGraph::new()
            .chain(
                FilterChain::new()
                    .filter(Filter::new("scale"))
                    .filter(Filter::new("hue")),
            )
            .chain(FilterChain::new().filter(Filter::new("format")));

        let result = simplify_filter_graph(&graph, PreviewQuality::High);
        assert_eq!(result.chain_count(), 2);
        assert_eq!(result.chains()[0].filter_count(), 2);
        assert_eq!(result.chains()[1].filter_count(), 1);
    }

    #[test]
    fn test_simplify_graph_draft_reduces_filters() {
        let graph = FilterGraph::new()
            .chain(
                FilterChain::new()
                    .filter(Filter::new("scale"))
                    .filter(Filter::new("hue"))
                    .filter(Filter::new("gblur")),
            )
            .chain(FilterChain::new().filter(Filter::new("format")));

        let result = simplify_filter_graph(&graph, PreviewQuality::Draft);
        assert_eq!(result.chain_count(), 2);
        assert_eq!(result.chains()[0].filter_count(), 1); // only scale
        assert_eq!(result.chains()[1].filter_count(), 1); // format unchanged
    }

    #[test]
    fn test_draft_fewer_filters_than_medium_concept() {
        // Both Draft and Medium currently remove the same filters,
        // but Draft should produce <= filters than Medium (satisfied since they're equal).
        let chain = FilterChain::new()
            .filter(Filter::new("scale"))
            .filter(Filter::new("hue"))
            .filter(Filter::new("format"));

        let draft = simplify_filter_chain(&chain, PreviewQuality::Draft);
        let medium = simplify_filter_chain(&chain, PreviewQuality::Medium);

        assert!(draft.filter_count() <= medium.filter_count());
        assert!(medium.filter_count() < chain.filter_count());
    }

    #[test]
    fn test_simplify_empty_chain() {
        let chain = FilterChain::new();
        let result = simplify_filter_chain(&chain, PreviewQuality::Draft);
        assert_eq!(result.filter_count(), 0);
    }

    #[test]
    fn test_simplify_empty_graph() {
        let graph = FilterGraph::new();
        let result = simplify_filter_graph(&graph, PreviewQuality::Draft);
        assert_eq!(result.chain_count(), 0);
    }

    #[test]
    fn test_simplify_chain_all_expensive() {
        let chain = FilterChain::new()
            .filter(Filter::new("hue"))
            .filter(Filter::new("eq"))
            .filter(Filter::new("gblur"));

        let result = simplify_filter_chain(&chain, PreviewQuality::Draft);
        assert_eq!(result.filter_count(), 0);
    }
}

#[cfg(test)]
mod proptests {
    use super::*;
    use crate::ffmpeg::filter::Filter;
    use proptest::prelude::*;

    /// All filter names used in property-based tests.
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
        "boxblur",
        "smartblur",
        "atadenoise",
        "nlmeans",
        "perspective",
        "lenscorrection",
    ];

    /// Generates a random filter name from the known set.
    fn arb_filter_name() -> impl Strategy<Value = &'static str> {
        proptest::sample::select(ALL_FILTER_NAMES)
    }

    /// Generates a random filter chain with 1-20 filters.
    fn arb_filter_chain() -> impl Strategy<Value = FilterChain> {
        proptest::collection::vec(arb_filter_name(), 1..=20).prop_map(|names| {
            let mut chain = FilterChain::new();
            for name in names {
                chain = chain.filter(Filter::new(name));
            }
            chain
        })
    }

    /// Generates a random filter graph with 1-5 chains, each with 1-20 filters.
    fn arb_filter_graph() -> impl Strategy<Value = FilterGraph> {
        proptest::collection::vec(arb_filter_chain(), 1..=5).prop_map(|chains| {
            let mut graph = FilterGraph::new();
            for chain in chains {
                graph = graph.chain(chain);
            }
            graph
        })
    }

    /// Generates a random PreviewQuality variant.
    fn arb_quality() -> impl Strategy<Value = PreviewQuality> {
        prop_oneof![
            Just(PreviewQuality::Draft),
            Just(PreviewQuality::Medium),
            Just(PreviewQuality::High),
        ]
    }

    proptest! {
        /// Simplification never panics on random filter chains.
        #[test]
        fn simplify_chain_never_panics(
            chain in arb_filter_chain(),
            quality in arb_quality(),
        ) {
            let _ = simplify_filter_chain(&chain, quality);
        }

        /// Simplification never panics on random filter graphs.
        #[test]
        fn simplify_graph_never_panics(
            graph in arb_filter_graph(),
            quality in arb_quality(),
        ) {
            let _ = simplify_filter_graph(&graph, quality);
        }

        /// Simplified chain is always a subset of original (filter count <= original).
        #[test]
        fn simplified_chain_is_subset(
            chain in arb_filter_chain(),
            quality in arb_quality(),
        ) {
            let result = simplify_filter_chain(&chain, quality);
            prop_assert!(result.filter_count() <= chain.filter_count());
        }

        /// Simplified graph is always a subset of original (total filter count <= original).
        #[test]
        fn simplified_graph_is_subset(
            graph in arb_filter_graph(),
            quality in arb_quality(),
        ) {
            let original_total: usize = graph.chains().iter().map(|c| c.filter_count()).sum();
            let result = simplify_filter_graph(&graph, quality);
            let result_total: usize = result.chains().iter().map(|c| c.filter_count()).sum();
            prop_assert!(result_total <= original_total);
        }

        /// High quality is identity: output equals input.
        #[test]
        fn high_quality_is_identity_chain(chain in arb_filter_chain()) {
            let result = simplify_filter_chain(&chain, PreviewQuality::High);
            prop_assert_eq!(result.filter_count(), chain.filter_count());
            for (orig, res) in chain.filters().iter().zip(result.filters().iter()) {
                prop_assert_eq!(orig.name(), res.name());
            }
        }

        /// High quality is identity for graphs.
        #[test]
        fn high_quality_is_identity_graph(graph in arb_filter_graph()) {
            let result = simplify_filter_graph(&graph, PreviewQuality::High);
            prop_assert_eq!(result.chain_count(), graph.chain_count());
            for (orig, res) in graph.chains().iter().zip(result.chains().iter()) {
                prop_assert_eq!(orig.filter_count(), res.filter_count());
            }
        }

        /// Simplification is idempotent: simplify(simplify(x)) == simplify(x).
        #[test]
        fn simplification_is_idempotent_chain(
            chain in arb_filter_chain(),
            quality in arb_quality(),
        ) {
            let once = simplify_filter_chain(&chain, quality);
            let twice = simplify_filter_chain(&once, quality);
            prop_assert_eq!(once.filter_count(), twice.filter_count());
            for (a, b) in once.filters().iter().zip(twice.filters().iter()) {
                prop_assert_eq!(a.name(), b.name());
            }
        }

        /// Simplification is idempotent for graphs.
        #[test]
        fn simplification_is_idempotent_graph(
            graph in arb_filter_graph(),
            quality in arb_quality(),
        ) {
            let once = simplify_filter_graph(&graph, quality);
            let twice = simplify_filter_graph(&once, quality);
            prop_assert_eq!(once.chain_count(), twice.chain_count());
            for (a, b) in once.chains().iter().zip(twice.chains().iter()) {
                prop_assert_eq!(a.filter_count(), b.filter_count());
            }
        }
    }
}
