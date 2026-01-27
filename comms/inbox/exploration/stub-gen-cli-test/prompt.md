Explore and TEST the pyo3-stub-gen stub generation behavior in the stoat-and-ferret project.

## Tasks

1. **Test the stub_gen binary without arguments**
   - Run: `cargo run --bin stub_gen` from `rust/stoat_ferret_core/`
   - Document: Exit code, stdout, stderr
   - Check: What files were created or modified? Where?

2. **Test the stub_gen binary WITH --output-dir argument**
   - Run: `cargo run --bin stub_gen -- --output-dir /tmp/test-stubs`
   - Document: Does this fail? What error message?
   - This tests the hypothesis that CLI args are not supported

3. **Examine pyproject.toml configuration**
   - What is `python-source` set to?
   - What is `module-name` set to?
   - Based on pyo3-stub-gen docs, where should stubs be generated?

4. **Locate generated stub files**
   - Search for all .pyi files in the project (excluding .venv)
   - Compare timestamps before/after running stub_gen
   - Document exact output location

5. **Test git diff verification pattern**
   - After running stub_gen, run `git diff --exit-code`
   - Document if stubs are up-to-date or need regeneration

## Output Requirements

Create findings in comms/outbox/exploration/stub-gen-cli-test/:

### README.md (required)
First paragraph: Concise summary - does stub_gen accept CLI args? Where do stubs go?
Then: Links to detailed test results.

### cli-test-results.md
- Exact commands run
- Full stdout/stderr output
- Exit codes
- Analysis of what happened

### stub-locations.md
- pyproject.toml configuration
- Expected vs actual stub output locations
- List of .pyi files found

## Guidelines
- Under 200 lines per document
- Include exact command output (truncated if needed)
- Be precise about file paths
- Test BEFORE theorizing

## When Complete
git add comms/outbox/exploration/stub-gen-cli-test/
git commit -m "exploration: stub-gen-cli-test - tested CLI args and output locations"
