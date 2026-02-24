## Context

Job queue systems often need to pass new contextual information (job ID, cancellation signals, progress callbacks) to handlers. Changing the handler function signature breaks all existing handlers and their tests.

## Learning

Inject contextual information into the handler's payload dictionary (e.g., `payload["_job_id"] = job_id`) rather than adding parameters to the handler function signature. This preserves backward compatibility with existing handlers while giving new handlers access to the context they need. Use underscore-prefixed keys to distinguish injected context from user-provided data.

## Evidence

v010 Feature 001 (progress-reporting) needed to give scan handlers access to their job ID for progress updates. Rather than changing the handler signature from `(job_type, payload)` to `(job_type, payload, job_id)`, the `process_jobs()` worker injected `_job_id` into the payload dict. This:
- Kept all existing handlers working without changes
- Avoided modifying the handler Protocol or type signature
- Let the scan handler access `payload["_job_id"]` for progress callbacks
- Maintained backward compatibility across all test fixtures and conftest wiring

## Application

When extending a callback/handler interface with new context:
- Inject into existing data structures (dicts, context objects) rather than adding function parameters
- Use underscore-prefixed or namespaced keys to avoid collisions with user data
- This approach works best when the interface is used by many callsites and backward compatibility matters
- For greenfield designs, explicit parameters are preferable for type safety