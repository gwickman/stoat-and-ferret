# CLI Test Results

## Test 1: stub_gen without arguments

### Command
```bash
cd rust/stoat_ferret_core && cargo run --bin stub_gen
```

### Output
```
Finished `dev` profile [unoptimized + debuginfo] target(s) in 0.15s
Running `target\debug\stub_gen.exe`
Error: The system cannot find the file specified. (os error 2)
error: process didn't exit successfully: `target\debug\stub_gen.exe` (exit code: 1)
```

### Exit Code
**1** (failure)

### Analysis
The binary fails because `define_stub_info_gatherer!` macro looks for `pyproject.toml` at `CARGO_MANIFEST_DIR` (i.e., `rust/stoat_ferret_core/`). That file doesn't exist there - it's at the project root.

Backtrace shows failure at:
```
pyo3_stub_gen::pyproject::PyProject::parse_toml
```

---

## Test 2: stub_gen with --output-dir argument

### Command
```bash
cd rust/stoat_ferret_core && cargo run --bin stub_gen -- --output-dir /tmp/test-stubs
```

### Output
```
Finished `dev` profile [unoptimized + debuginfo] target(s) in 0.08s
Running `target\debug\stub_gen.exe --output-dir '/tmp/test-stubs'`
Error: The system cannot find the file specified. (os error 2)
error: process didn't exit successfully: `target\debug\stub_gen.exe --output-dir '/tmp/test-stubs'` (exit code: 1)
```

### Exit Code
**1** (failure)

### Analysis
Same error as without arguments. The failure occurs when reading pyproject.toml, **before** any CLI arguments would be processed.

**Important:** The stub_gen.rs source code does NOT parse CLI arguments:
```rust
fn main() -> Result<()> {
    let stub = stoat_ferret_core::stub_info()?;
    stub.generate()?;
    Ok(())
}
```

There is no argument parsing - `--output-dir` is simply ignored.

---

## Test 3: Running from project root

### Command
```bash
cd /project/root && ./rust/stoat_ferret_core/target/debug/stub_gen.exe
```

### Output
```
Error: The system cannot find the file specified. (os error 2)
```

### Exit Code
**1** (failure)

### Analysis
Running from project root does not help. The `define_stub_info_gatherer!` macro hardcodes the path at compile time using `env!("CARGO_MANIFEST_DIR")`, which is always `rust/stoat_ferret_core/`.

---

## Test 4: git diff verification

### Command
```bash
git diff --exit-code stubs/
```

### Exit Code
**0** (success - no differences)

### Analysis
The existing stub files in `stubs/stoat_ferret_core/` are up-to-date with the committed version. Since stub_gen doesn't run successfully, these stubs must be manually maintained.
