Research the PyO3/maturin hybrid Python+Rust build workflow to answer:

1. What is the developer workflow for a hybrid project? (edit Rust → rebuild → test in Python)
2. How does `maturin develop` vs `maturin build` work? When to use each?
3. How are Python type stubs (.pyi files) generated for PyO3 bindings?
4. What CI configuration is needed for hybrid builds? (GitHub Actions examples)
5. What are common gotchas and best practices?

## Research Approach

Since stoat-and-ferret has no code yet, research external sources:
- PyO3 documentation and examples
- maturin documentation
- Open source projects using PyO3/maturin (pydantic-core, polars, ruff)
- GitHub Actions workflow examples for Rust+Python

## Output Requirements

Create findings in comms/outbox/exploration/rust-python-hybrid/:

### README.md (required)
First paragraph: Concise summary of the recommended workflow.
Then: Overview and links to detailed documents.

### dev-workflow.md
Step-by-step developer workflow: setup, edit-compile-test cycle, debugging tips.

### stub-generation.md
How to generate and maintain .pyi type stubs for PyO3 bindings.

### ci-setup.md
GitHub Actions configuration for hybrid Python+Rust projects.

### gotchas.md
Common pitfalls and how to avoid them.

## Guidelines
- Under 200 lines per document
- Use clear headings
- Include concrete code/config snippets
- Reference source documentation

## When Complete
git add comms/outbox/exploration/rust-python-hybrid/
git commit -m "exploration: rust-python-hybrid complete"