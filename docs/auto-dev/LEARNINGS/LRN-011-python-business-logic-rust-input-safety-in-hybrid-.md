## Context

In hybrid Python/Rust architectures, the boundary between what belongs in each language can be unclear, especially for validation and security concerns.

## Learning

Maintain a clean architectural boundary: Rust owns low-level input sanitization (null bytes, malformed strings, type validation), Python owns business policy (allowed paths, authentication, authorization, business rules). This separation ensures Rust code remains reusable across contexts while Python handles domain-specific decisions that may change with business requirements.

## Evidence

- v004 Theme 04 Feature 001 (security-audit): Rust's `validate_path` intentionally only checks for empty/null — it doesn't enforce business logic like allowed scan roots. `ALLOWED_SCAN_ROOTS` was correctly added in the Python scan service.
- Performance benchmarks confirmed Rust's value is correctness and type safety, not raw speed (PyO3 FFI overhead makes simple Rust operations 7-10x slower than Python equivalents).
- The version retrospective identified this as a key cross-theme learning.

## Application

- Rust layer: type safety, input sanitization, string processing, compute-heavy operations.
- Python layer: business rules, policy enforcement, configuration, HTTP routing.
- Don't put business rules in Rust — they change more frequently and are harder to modify.
- Justify Rust usage by safety/correctness benefits, not performance assumptions.