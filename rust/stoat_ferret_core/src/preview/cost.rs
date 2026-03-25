//! Filter cost estimation and auto-quality selection.
//!
//! Provides a heuristic cost score (0.0-1.0) for filter graphs based on
//! filter count and presence of expensive filters. Used to automatically
//! select preview quality levels.

use pyo3::prelude::*;

use crate::ffmpeg::filter::FilterGraph;
use crate::preview::simplify::is_expensive_filter;
use crate::preview::PreviewQuality;

/// Weight multiplier for expensive filters in cost calculation.
const EXPENSIVE_WEIGHT: f64 = 3.0;

/// Weight for cheap (non-expensive) filters.
const CHEAP_WEIGHT: f64 = 1.0;

/// Sigmoid midpoint: the weighted filter count at which cost reaches 0.5.
const SIGMOID_MIDPOINT: f64 = 10.0;

/// Sigmoid steepness factor.
const SIGMOID_STEEPNESS: f64 = 0.3;

/// Estimates the computational cost of a filter graph as a score in [0.0, 1.0].
///
/// The score is computed by:
/// 1. Summing weighted filter counts (expensive filters count more)
/// 2. Normalizing via a sigmoid function to bound the result in (0.0, 1.0)
/// 3. Returning exactly 0.0 for empty graphs
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::preview::cost::estimate_filter_cost;
/// use stoat_ferret_core::ffmpeg::filter::{FilterGraph, FilterChain, Filter};
///
/// let empty = FilterGraph::new();
/// assert_eq!(estimate_filter_cost(&empty), 0.0);
///
/// let small = FilterGraph::new()
///     .chain(FilterChain::new().filter(Filter::new("scale")));
/// assert!(estimate_filter_cost(&small) > 0.0);
/// assert!(estimate_filter_cost(&small) < 1.0);
/// ```
pub fn estimate_filter_cost(graph: &FilterGraph) -> f64 {
    let mut weighted_sum = 0.0;

    for chain in graph.chains() {
        for filter in chain.filters() {
            if is_expensive_filter(filter.name()) {
                weighted_sum += EXPENSIVE_WEIGHT;
            } else {
                weighted_sum += CHEAP_WEIGHT;
            }
        }
    }

    if weighted_sum == 0.0 {
        return 0.0;
    }

    // Sigmoid: 1 / (1 + e^(-k*(x - midpoint)))
    1.0 / (1.0 + (-SIGMOID_STEEPNESS * (weighted_sum - SIGMOID_MIDPOINT)).exp())
}

/// Selects preview quality based on estimated cost.
///
/// - Cost > 0.7: Draft (fastest preview)
/// - Cost 0.3..=0.7: Medium (balanced)
/// - Cost < 0.3: High (full quality)
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::preview::cost::select_preview_quality;
/// use stoat_ferret_core::preview::PreviewQuality;
///
/// assert_eq!(select_preview_quality(0.1), PreviewQuality::High);
/// assert_eq!(select_preview_quality(0.5), PreviewQuality::Medium);
/// assert_eq!(select_preview_quality(0.9), PreviewQuality::Draft);
/// ```
pub fn select_preview_quality(cost: f64) -> PreviewQuality {
    if cost > 0.7 {
        PreviewQuality::Draft
    } else if cost >= 0.3 {
        PreviewQuality::Medium
    } else {
        PreviewQuality::High
    }
}

/// Python binding: Estimates filter graph cost as a score in [0.0, 1.0].
#[pyfunction]
#[pyo3(name = "estimate_filter_cost")]
pub fn py_estimate_filter_cost(graph: &FilterGraph) -> f64 {
    estimate_filter_cost(graph)
}

/// Python binding: Selects preview quality based on cost score.
#[pyfunction]
#[pyo3(name = "select_preview_quality")]
pub fn py_select_preview_quality(cost: f64) -> PreviewQuality {
    select_preview_quality(cost)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::ffmpeg::filter::{Filter, FilterChain};

    #[test]
    fn test_empty_graph_returns_zero() {
        let graph = FilterGraph::new();
        assert_eq!(estimate_filter_cost(&graph), 0.0);
    }

    #[test]
    fn test_single_cheap_filter_positive() {
        let graph = FilterGraph::new().chain(FilterChain::new().filter(Filter::new("scale")));
        let cost = estimate_filter_cost(&graph);
        assert!(cost > 0.0);
        assert!(cost < 1.0);
    }

    #[test]
    fn test_cost_bounded() {
        // Large graph with many expensive filters
        let mut chain = FilterChain::new();
        for _ in 0..50 {
            chain = chain.filter(Filter::new("nlmeans"));
        }
        let graph = FilterGraph::new().chain(chain);
        let cost = estimate_filter_cost(&graph);
        assert!(cost > 0.0);
        assert!(cost <= 1.0);
    }

    #[test]
    fn test_more_filters_higher_cost() {
        let small = FilterGraph::new().chain(
            FilterChain::new()
                .filter(Filter::new("scale"))
                .filter(Filter::new("format")),
        );
        let large = FilterGraph::new().chain(
            FilterChain::new()
                .filter(Filter::new("scale"))
                .filter(Filter::new("format"))
                .filter(Filter::new("setpts"))
                .filter(Filter::new("asetpts"))
                .filter(Filter::new("concat"))
                .filter(Filter::new("scale"))
                .filter(Filter::new("format"))
                .filter(Filter::new("setpts"))
                .filter(Filter::new("asetpts"))
                .filter(Filter::new("concat")),
        );
        assert!(estimate_filter_cost(&large) > estimate_filter_cost(&small));
    }

    #[test]
    fn test_expensive_filters_higher_cost() {
        let cheap = FilterGraph::new().chain(
            FilterChain::new()
                .filter(Filter::new("scale"))
                .filter(Filter::new("format"))
                .filter(Filter::new("setpts")),
        );
        let expensive = FilterGraph::new().chain(
            FilterChain::new()
                .filter(Filter::new("nlmeans"))
                .filter(Filter::new("gblur"))
                .filter(Filter::new("hue")),
        );
        assert!(estimate_filter_cost(&expensive) > estimate_filter_cost(&cheap));
    }

    #[test]
    fn test_select_quality_high() {
        assert_eq!(select_preview_quality(0.0), PreviewQuality::High);
        assert_eq!(select_preview_quality(0.1), PreviewQuality::High);
        assert_eq!(select_preview_quality(0.29), PreviewQuality::High);
    }

    #[test]
    fn test_select_quality_medium() {
        assert_eq!(select_preview_quality(0.3), PreviewQuality::Medium);
        assert_eq!(select_preview_quality(0.5), PreviewQuality::Medium);
        assert_eq!(select_preview_quality(0.7), PreviewQuality::Medium);
    }

    #[test]
    fn test_select_quality_draft() {
        assert_eq!(select_preview_quality(0.71), PreviewQuality::Draft);
        assert_eq!(select_preview_quality(0.9), PreviewQuality::Draft);
        assert_eq!(select_preview_quality(1.0), PreviewQuality::Draft);
    }
}

#[cfg(test)]
mod proptests {
    use super::*;
    use crate::ffmpeg::filter::{Filter, FilterChain};
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

    fn arb_filter_name() -> impl Strategy<Value = &'static str> {
        proptest::sample::select(ALL_FILTER_NAMES)
    }

    fn arb_filter_chain() -> impl Strategy<Value = FilterChain> {
        proptest::collection::vec(arb_filter_name(), 1..=20).prop_map(|names| {
            let mut chain = FilterChain::new();
            for name in names {
                chain = chain.filter(Filter::new(name));
            }
            chain
        })
    }

    fn arb_filter_graph() -> impl Strategy<Value = FilterGraph> {
        proptest::collection::vec(arb_filter_chain(), 1..=5).prop_map(|chains| {
            let mut graph = FilterGraph::new();
            for chain in chains {
                graph = graph.chain(chain);
            }
            graph
        })
    }

    proptest! {
        /// Cost is always in [0.0, 1.0] for random graphs.
        #[test]
        fn cost_always_bounded(graph in arb_filter_graph()) {
            let cost = estimate_filter_cost(&graph);
            prop_assert!(cost >= 0.0, "cost {} < 0.0", cost);
            prop_assert!(cost <= 1.0, "cost {} > 1.0", cost);
        }

        /// Cost is monotonically non-decreasing as filters are added.
        #[test]
        fn cost_monotonically_nondecreasing(
            base_names in proptest::collection::vec(arb_filter_name(), 1..=10),
            extra_names in proptest::collection::vec(arb_filter_name(), 1..=10),
        ) {
            let mut base_chain = FilterChain::new();
            for name in &base_names {
                base_chain = base_chain.filter(Filter::new(*name));
            }
            let base_graph = FilterGraph::new().chain(base_chain);

            let mut extended_chain = FilterChain::new();
            for name in &base_names {
                extended_chain = extended_chain.filter(Filter::new(*name));
            }
            for name in &extra_names {
                extended_chain = extended_chain.filter(Filter::new(*name));
            }
            let extended_graph = FilterGraph::new().chain(extended_chain);

            let base_cost = estimate_filter_cost(&base_graph);
            let extended_cost = estimate_filter_cost(&extended_graph);
            prop_assert!(
                extended_cost >= base_cost,
                "adding filters decreased cost: {} -> {}",
                base_cost,
                extended_cost
            );
        }
    }
}
