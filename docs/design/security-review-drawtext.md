# Security Review: DrawtextBuilder Text Input Sanitization

**Backlog Item:** BL-085
**Date:** 2026-03-17
**Scope:** `escape_drawtext()` in `rust/stoat_ferret_core/src/ffmpeg/drawtext.rs:36-53`

## 1. Escaped Characters

The `escape_drawtext()` function handles 9 special characters:

| # | Character | Escape Sequence | Reason |
|---|-----------|----------------|--------|
| 1 | `\` (backslash) | `\\` | FFmpeg escape character — must be doubled to produce literal backslash |
| 2 | `'` (single quote) | `'\''` | Shell-style quote escaping — ends current quote, inserts escaped quote, resumes quoting |
| 3 | `:` (colon) | `\:` | FFmpeg filter parameter separator — must be escaped in text values |
| 4 | `[` (left bracket) | `\[` | FFmpeg stream label delimiter — must be escaped to prevent stream label injection |
| 5 | `]` (right bracket) | `\]` | FFmpeg stream label delimiter — closing bracket |
| 6 | `;` (semicolon) | `\;` | FFmpeg filter chain separator — must be escaped to prevent filter chain injection |
| 7 | `\n` (newline) | `\n` (literal) | Prevents filter string breakout via embedded newlines |
| 8 | `\r` (carriage return) | `\r` (literal) | Prevents filter string breakout via embedded carriage returns |
| 9 | `%` (percent) | `%%` | FFmpeg text expansion trigger — must be doubled to produce literal percent |

All other characters, including Unicode, pass through unchanged.

## 2. Defense-in-Depth Layers

The system employs three layers of defense against injection:

### Layer 1: Rust Text Escaping (`escape_drawtext`)

All user-supplied text is escaped at construction time in `DrawtextBuilder::new()` (line 176). This is the primary defense and runs before any filter string is assembled. The escaping is character-level iteration over the input — no regex, no partial matching — so it cannot be bypassed by encoding tricks.

### Layer 2: Argument Array Subprocess Execution

`RealFFmpegExecutor` in `src/stoat_ferret/ffmpeg/executor.py:96-101` uses:

```python
result = subprocess.run(
    command,       # list[str] argument array
    input=stdin,
    capture_output=True,
    timeout=timeout,
)
```

- No `shell=True` — the command is passed as an argument array, not a shell string
- No string interpolation of user input into command strings
- This neutralizes all shell injection vectors (backticks, `$()`, pipes, `&&`, etc.)

### Layer 3: Typed Expression Engine

The `alpha_fade()` method generates FFmpeg expressions via a typed expression engine (`Expr` AST in `expression.rs`), not string concatenation. The expression engine only produces:

- Mathematical operators: `+`, `-`, `*`, `/`
- Comparison functions: `lt()`, `gt()`, `gte()`, `lte()`
- Control flow: `if()`
- Variables: `t`, `n` (FFmpeg-defined, not user-controlled)
- Numeric constants

This makes it impossible for user input to inject arbitrary FFmpeg expressions through `alpha_fade()`.

The `enable()` method accepts raw expression strings. This is by design for API flexibility, but should only be used with trusted/validated expressions — not raw user input.

## 3. FFmpeg Text Expansion Modes

FFmpeg's drawtext filter supports `%{...}` text expansion syntax:

| Expansion | Description | Risk |
|-----------|-------------|------|
| `%{localtime}` | System local time | Information disclosure |
| `%{pts}` | Presentation timestamp | Low (timing info) |
| `%{n}` | Frame number | Low |
| `%{expr:EXPR}` | Evaluate FFmpeg expression | Expression injection |
| `%{eif:EXPR:FMT}` | Evaluate and format expression | Expression injection |
| `%{metadata:KEY}` | Read stream metadata | Information disclosure |

**Mitigation:** `escape_drawtext()` converts `%` → `%%`, which neutralizes all expansion modes. FFmpeg interprets `%%` as a literal `%` character, so `%%{localtime}` displays as `%{localtime}` rather than expanding to the system time.

**Test coverage:** 6 Rust tests verify specific expansion patterns are neutralized (`%{expr:1+1}`, `%{metadata:key}`, `%{localtime}`, `%{pts}`, `%{eif:n:d}`, and nested expansions).

## 4. Unicode Handling

Unicode characters (including zero-width characters, RTL markers, and combining characters) pass through `escape_drawtext()` without modification. This is correct because:

1. FFmpeg's drawtext filter accepts UTF-8 text natively
2. These characters have no special meaning in FFmpeg filter syntax
3. Stripping or modifying them would corrupt legitimate multilingual text

**Test coverage:**
- 8 Rust tests verify individual Unicode categories (zero-width, RTL, combining)
- 1 Rust test verifies Unicode + special char combinations
- 10 Python tests verify the full path through PyO3 (Python → Rust → filter string)
- Property-based tests cover arbitrary Unicode text (`\p{L}\p{N}\p{P}` character classes)

**Note on RTL override (U+202E):** This character can cause display spoofing (reversed text direction). This is a rendering concern, not a security vulnerability in the FFmpeg filter context. The text is passed to FFmpeg which renders it according to font/layout rules.

## 5. Expression Context Security

The `build()` method wraps `alpha` and `enable` values in single quotes:

```rust
filter = filter.param("alpha", format!("'{alpha}'"));
filter = filter.param("enable", format!("'{enable}'"));
```

**Analysis:**

- `alpha_fade()` generates expressions via the typed `Expr` AST — no user-controlled strings can inject single quotes because the AST only produces numeric constants, variables, and mathematical operators
- `alpha()` accepts a clamped float value — no string injection possible
- `enable()` accepts raw expression strings — this is intentionally for FFmpeg expressions, not user text. The API boundary between user text (escaped via `DrawtextBuilder::new()`) and expressions (passed to `enable()`) is the key design decision

**Test coverage:** 3 Rust tests verify expression wrapping integrity and the absence of raw single quotes in generated expressions.

## 6. Conclusions

**No vulnerabilities found.** The DrawtextBuilder text sanitization is sound:

1. All 9 FFmpeg-special characters are correctly escaped
2. `%` → `%%` escaping neutralizes all text expansion injection vectors
3. Unicode text passes through correctly without corruption
4. Subprocess execution uses argument arrays — no shell injection possible
5. The typed expression engine prevents expression injection through `alpha_fade()`
6. Clear API boundary: user text is escaped at `new()`, expressions are separate methods

**Recommendations:**

- No changes to `escape_drawtext()` are needed
- The `enable()` method should continue to be documented as accepting trusted FFmpeg expressions only
- Future API surfaces accepting user text should route through `escape_drawtext()` or equivalent
