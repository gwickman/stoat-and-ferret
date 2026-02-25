## Context

When trimming a public API surface (removing bindings, endpoints, or exported functions), the underlying implementation may still be used internally or may need to be re-exposed in the future. This applies to FFI boundaries, SDK surfaces, and any layered architecture where internal logic is wrapped by a public-facing layer.

## Learning

When removing public API wrappers, delete only the wrapper layer (bindings, exports, registrations) while preserving the internal implementation. Document the removal in a changelog with explicit re-add triggers describing the conditions under which the functionality should be re-exposed. This approach makes re-exposure a cheap, mechanical operation (add wrapper + registration) rather than a re-implementation.

## Evidence

Eleven PyO3 binding wrappers were removed from a Rust-Python boundary while all Rust-internal implementations (enums, methods, algorithms) were preserved. The changelog documented specific re-add triggers (e.g., "re-add when orchestrated multi-step pipelines need a unified entry point"). Internal tests continued passing because the underlying code was untouched.

## Application

1. Distinguish between the wrapper layer (bindings, exports) and the implementation layer (logic, algorithms)
2. Remove only the wrapper layer — imports, registrations, exports, public-facing stubs
3. Verify internal tests still pass (they should, since implementation is unchanged)
4. Document each removal in a changelog with a specific re-add trigger condition
5. When the trigger condition is met in a future version, re-adding is a small PR (wrapper + registration only)