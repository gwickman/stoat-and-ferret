# C4 Code Level: Preview Module

**Source:** `rust/stoat_ferret_core/src/preview/`
**Component:** Rust Core

## Purpose

Provides quality-level-based simplification of FFmpeg filter graphs for real-time preview playback, cost estimation for auto-quality selection, and scale filter injection for resolution control. Expensive filters are removed at lower quality levels to improve performance while maintaining structural correctness.

## Module Structure

The preview module consists of three submodules with centralized registration:

- `cost` — Filter cost estimation and auto-quality selection
- `scale` — Preview scale filter injection for resolution control
- `simplify` — Filter simplification by removing expensive filters

All submodules implement PyO3 functions and types registered via `register(m: &Bound<PyModule>)` in mod.rs.

## Public Interface

### Enums

#### `PreviewQuality`
Enumeration controlling preview quality level and filter simplification aggressiveness.

**Variants:**
- `Draft` — Fastest preview: removes all expensive filters
- `Medium` — Balanced preview: removes most expensive filters, keeps some visual fidelity
- `High` — Full quality: preserves all filters unchanged (production quality)

**PyO3 Attributes:**
- `#[pyclass(eq, eq_int)]` — Supports Python equality and integer comparisons
- Derive: `Debug`, `Clone`, `Copy`, `PartialEq`, `Eq`

### Functions (simplify Submodule)

#### `is_expensive_filter(name: &str) -> bool`

**Purpose:** Classify a filter by computational cost.

**Expensive filters (11 known):**
- `hue`, `eq`, `colorbalance` — Color manipulation (CPU-intensive)
- `unsharp`, `gblur`, `boxblur`, `smartblur` — Blurring/sharpening (high bandwidth)
- `atadenoise`, `nlmeans` — Denoising (very expensive)
- `perspective`, `lenscorrection` — Geometric transforms (complex calculations)

**Returns:** `true` if filter name is in EXPENSIVE_FILTERS list, `false` otherwise.

**Python binding:** `py_is_expensive_filter(name: str) -> bool`

#### `simplify_filter_chain(chain: &FilterChain, quality: PreviewQuality) -> FilterChain`

**Purpose:** Simplify a filter chain based on quality level.

**Algorithm:**
- **High**: Returns exact clone of chain unchanged
- **Medium/Draft**: Creates new chain, filtering out expensive filters via `is_expensive_filter()`

**Returns:** Simplified FilterChain with expensive filters removed at Medium/Draft levels.

**Note:** Current implementation treats Medium and Draft identically; this provides extension point for future graduated simplification (e.g., Medium could preserve specific filters).

**Python binding:** `py_simplify_filter_chain(chain: FilterChain, quality: PreviewQuality) -> FilterChain`

#### `simplify_filter_graph(graph: &FilterGraph, quality: PreviewQuality) -> FilterGraph`

**Purpose:** Simplify all chains in a filter graph based on quality level.

**Algorithm:**
1. For High quality: Returns exact clone of graph unchanged
2. For Medium/Draft:
   - Iterates over all chains in graph
   - Applies `simplify_filter_chain()` to each
   - Rebuilds graph from simplified chains

**Returns:** Simplified FilterGraph with all expensive filters removed at Medium/Draft levels.

**Python binding:** `py_simplify_filter_graph(graph: FilterGraph, quality: PreviewQuality) -> FilterGraph`

### Functions (cost Submodule)

#### `estimate_filter_cost(graph: &FilterGraph) -> f64`

**Purpose:** Compute computational cost of a filter graph as a score in [0.0, 1.0].

**Algorithm:**
1. Iterate over all filters in all chains
2. For each filter:
   - If expensive (via `is_expensive_filter()`): add EXPENSIVE_WEIGHT (3.0)
   - Otherwise: add CHEAP_WEIGHT (1.0)
3. Sum weighted counts
4. If sum is 0.0, return 0.0 (empty graph)
5. Apply sigmoid normalization:
   ```
   sigmoid(x) = 1 / (1 + e^(-k * (x - midpoint)))
   ```
   where:
   - midpoint = 10.0 (cost = 0.5 at 10 weighted filters)
   - steepness = 0.3 (sigmoid slope parameter)

**Returns:** Cost score in [0.0, 1.0]. Higher cost = more computational burden.

**Key Properties:**
- Empty graph → exactly 0.0
- Score bounded in [0.0, 1.0] even for very large graphs
- Monotonically non-decreasing as filters added
- Expensive filters contribute 3x more than cheap filters

**Python binding:** `py_estimate_filter_cost(graph: FilterGraph) -> f64`

#### `select_preview_quality(cost: f64) -> PreviewQuality`

**Purpose:** Auto-select quality level based on estimated cost.

**Decision Logic:**
- Cost > 0.7 → Draft (fastest preview, max simplification)
- 0.3 ≤ Cost ≤ 0.7 → Medium (balanced)
- Cost < 0.3 → High (full quality, no simplification)

**Returns:** PreviewQuality variant based on cost threshold.

**Use Case:** Application can automatically choose quality level when user doesn't explicitly specify it.

**Python binding:** `py_select_preview_quality(cost: f64) -> PreviewQuality`

### Functions (scale Submodule)

#### `inject_preview_scale(graph: &FilterGraph, width: i32, height: i32) -> FilterGraph`

**Purpose:** Append a resolution scale filter to filter graph for preview playback at reduced resolution.

**Algorithm:**
1. Create scale filter via `scale(width, height)` from ffmpeg::filter module
2. Wrap filter in new FilterChain
3. Clone input graph
4. Append scale chain to cloned graph
5. Return modified graph

**Behavior:**
- If input graph is empty: creates graph with single chain containing only scale filter
- If input graph has chains: preserves all existing chains, appends scale as new chain
- Total filter count increases by exactly 1

**Returns:** FilterGraph with scale filter injected as new final chain.

**Note:** Scale filter is applied AFTER all existing filters, ensuring resolution reduction happens at output.

**Python binding:** `py_inject_preview_scale(graph: FilterGraph, width: i32, height: i32) -> FilterGraph`

## Dependencies

### Internal Crate Dependencies

- `ffmpeg::filter` — FilterGraph, FilterChain, Filter types and scale() builder
- (No circular dependencies; simplify and cost modules do not depend on scale)

### External Crate Dependencies

- **pyo3** — PyO3 Python bindings for class/function definitions
- **pyo3_stub_gen** — Stub generation support for Python type hints
- **proptest** — Property-based testing (test-only, comprehensive coverage)

## Key Implementation Details

### Expensive Filter Classification

The 11 expensive filters are hardcoded constants in simplify.rs:
```rust
const EXPENSIVE_FILTERS: &[&str] = &[
    "hue", "eq", "colorbalance",
    "unsharp", "gblur", "boxblur", "smartblur",
    "atadenoise", "nlmeans",
    "perspective", "lenscorrection",
];
```

Classification is O(n) contains-check. Future optimization could use a perfect hash set if performance critical.

### Sigmoid Cost Normalization

The sigmoid function bounds cost in (0.0, 1.0):
```
cost = 1 / (1 + e^(-0.3 * (weighted_sum - 10.0)))
```

**Behavior:**
- weighted_sum = 0 → cost = 0.0 (special case, early return)
- weighted_sum = 10 → cost ≈ 0.5 (midpoint)
- weighted_sum = 20 → cost ≈ 0.88 (approaching saturation)
- weighted_sum = ∞ → cost → 1.0 (asymptotically bounded)

Steepness (0.3) controls how quickly cost rises; larger values create sharper transitions.

### Quality-Based Simplification Strategy

**High quality path:** Pure identity operation, returns cloned input unchanged. This preserves all filters for production or detailed preview.

**Draft/Medium path:** Removes all filters in EXPENSIVE_FILTERS list. Current implementation treats Draft and Medium identically, providing a clear extension point:
- Future: Medium could keep some filters (e.g., keep colorbalance but remove nlmeans)
- Future: Draft could keep only structural filters (scale, concat, etc.)

### Scale Injection Placement

Scale filter is always injected as a NEW CHAIN (not appended to existing chain). This ensures:
1. Readability: scale operation is visually separate in filter graph
2. Composability: existing filter chains remain unchanged
3. Ordering: scale is guaranteed to be final operation

Alternative (appending to last chain) rejected because:
- Would modify existing chain structure
- Could create unintended filter dependencies
- Harder to reason about filter ordering in complex graphs

## Relationships

**Used by:**
- Python preview system — Selects quality level, simplifies graphs before encoding
- Real-time preview rendering — Injects scale filter for resolution control
- Auto-quality heuristics — Estimates cost and auto-selects quality when user doesn't specify

**Uses:**
- `ffmpeg::filter` module — Filter, FilterChain, FilterGraph types and builders

## Testing

Comprehensive test suite with 50+ unit tests and property-based tests:

### Simplify Module (20+ tests)

1. **Expensive filter classification (2 tests):**
   - All 11 expensive filters classified correctly
   - Common cheap filters not classified as expensive

2. **Chain simplification (6 tests):**
   - High preserves all filters
   - Draft/Medium remove expensive filters
   - Filters in correct order after removal
   - Empty chain handling

3. **Graph simplification (5 tests):**
   - High preserves structure
   - Draft/Medium reduce filter counts
   - Chain count preserved
   - Draft ≤ Medium filter counts (idempotent)
   - Empty graph handling

4. **All-expensive chain test (1 test):**
   - Chain with only expensive filters → empty result

5. **Property-based tests (6 proptests):**
   - Never panics on random chains/graphs
   - Simplified ≤ original (subset property)
   - High quality is identity operation (both chain and graph)
   - Simplification is idempotent: simplify(simplify(x)) = simplify(x)

### Cost Module (15+ tests)

1. **Empty graph (1 test):**
   - Empty graph cost = exactly 0.0

2. **Single filter (2 tests):**
   - Single cheap filter: 0.0 < cost < 1.0
   - Cost is bounded [0.0, 1.0]

3. **Cost ordering (2 tests):**
   - More filters → higher cost
   - Expensive filters → higher cost than cheap

4. **Quality selection thresholds (3 tests):**
   - Cost < 0.3 → High
   - 0.3 ≤ Cost ≤ 0.7 → Medium
   - Cost > 0.7 → Draft

5. **Property-based tests (4 proptests):**
   - Cost always bounded [0.0, 1.0]
   - Cost monotonically non-decreasing as filters added
   - More filters generally correlates to higher cost

### Scale Module (12+ tests)

1. **Empty graph injection (1 test):**
   - Empty graph + scale → 1 chain with 1 filter

2. **Chain preservation (3 tests):**
   - Existing chains preserved at positions
   - Scale added as new final chain
   - Filter counts unchanged in original chains

3. **Filter count (2 tests):**
   - Total filters increase by exactly 1
   - No filters removed

4. **Property-based tests (2+ proptests):**
   - Always adds exactly 1 filter to total count
   - Never removes existing filters
   - Scale chain appended (doesn't modify existing chains)

## Notes

- **Simplification Idempotence:** Applying simplification twice at same quality level produces same result as once. Safe to call multiple times.
- **Cost Monotonicity:** Cost never decreases as more filters added. Useful for early termination in heuristics.
- **Quality Extension:** Draft/Medium currently identical; straightforward to add intermediate levels without breaking changes.
- **Filter Classification:** New expensive filters can be added to EXPENSIVE_FILTERS constant. No code changes needed elsewhere.
- **Python Integration:** All public functions have py_ bindings; all types are PyO3 classes. Fully accessible from Python.
- **No State:** All functions pure; no internal state or side effects. Thread-safe.

## Example Usage

```python
from stoat_ferret_core import (
    FilterGraph, FilterChain, Filter,
    PreviewQuality,
    estimate_filter_cost, select_preview_quality,
    simplify_filter_graph, inject_preview_scale,
    is_expensive_filter
)

# Build a complex filter graph with expensive filters
graph = FilterGraph()
chain = FilterChain()
chain = chain.filter(Filter("scale"))
chain = chain.filter(Filter("hue"))  # expensive
chain = chain.filter(Filter("nlmeans"))  # very expensive
graph = graph.chain(chain)

# Estimate computational cost
cost = estimate_filter_cost(graph)  # ~0.75 (high cost)
quality = select_preview_quality(cost)  # PreviewQuality.Draft

# Simplify for faster preview
simplified = simplify_filter_graph(graph, quality)
# Result: graph with only scale filter; hue and nlmeans removed

# Inject resolution scaling
final = inject_preview_scale(simplified, 640, 480)
# Result: simplified graph + scale(640, 480) as final chain

# Use in FFmpeg encoding
filter_str = final.to_filter_string()
# ffmpeg -filter_complex "<filter_str>" ...
```

## Preview Quality Selection Workflow

```python
# Typical workflow in Python preview system:

def render_preview(clip, user_quality=None):
    # Build full filter graph
    graph = build_filter_graph_from_clip(clip)

    # Auto-select quality if not specified
    if user_quality is None:
        cost = estimate_filter_cost(graph)
        quality = select_preview_quality(cost)
    else:
        quality = user_quality

    # Simplify for performance
    simplified = simplify_filter_graph(graph, quality)

    # Inject preview resolution
    final = inject_preview_scale(simplified, 1280, 720)

    # Generate FFmpeg command
    filter_str = final.to_filter_string()
    cmd = ["ffmpeg", "-i", clip.path, "-filter_complex", filter_str, ...]

    # Execute (much faster at Draft quality)
    result = subprocess.run(cmd, ...)
    return result
```
