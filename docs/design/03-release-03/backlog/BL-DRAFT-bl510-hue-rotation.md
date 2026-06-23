# BL-DRAFT-bl510-hue-rotation

**Status:** drafted, not filed
**Supersedes / amends:** BL-510 (currently "HueRotationBuilder — hue rotation / colour cycling"; live AC says "Comma escape rules from BL-502 are honored")
**Evidence:** `poc-work/poc-4-escape-policy/`, codex `07` Section H, codex `12`
**Why now:** the BL-502 escape rule is the wrong reference (BL-502 is itself runtime-broken — see BL-DRAFT-bl502-opacity-redesign). For `hue` specifically, single-quote-wrap protects commas; that is the correct policy.

## Problem statement

PoC-4 verified across multiple shell layers that `hue=H='<expression with commas>'` works without `\,` escape. Single-quote-wrap is sufficient to protect commas inside hue's `H` option. Tested cases:

- `hue=H='2*PI*t/3'` — works (9786 bytes)
- `hue=H='if(lt(t,1),0,PI)'` (unescaped commas) — works (6802 bytes)
- `hue=H='if(lt(t\,1)\,0\,PI)'` (escaped commas) — works (6802 bytes, byte-identical)

This holds via MSYS bash AND via native Python `subprocess.run([...])` with arg list.

## Proposed acceptance criteria

1. **HueRotationBuilder emits the user expression wrapped in single quotes**: `hue=H='<user-expression>'`. No comma-escape transform applied.
2. **Contract test exercises a comma-bearing expression**. Specifically `if(lt(t,1),0,PI)` — proves the policy is load-bearing.
3. **Replace the existing AC text "Comma escape rules from BL-502 are honored"**. That references a broken pattern (BL-502 is runtime-broken).
4. **Reject embedded single quotes in user input at the API boundary** (i.e. before construction). A user expression containing `'` cannot be safely wrapped; reject early with a clear 422.

## Out of scope

- Generalising the single-quote policy to other filters — known per-PoC-4 that it does NOT generalise (colorchannelmixer breaks). Per-value-kind escape policy is its own design ticket (Track F of `08` and Track 4 of `11`).

## Unit test seeds

```rust
#[test]
fn hue_builder_emits_single_quoted_expression() {
    let b = HueRotationBuilder::new("if(lt(t,1),0,PI)");
    let s = b.build().unwrap().to_filter_string();
    assert_eq!(s, "hue=H='if(lt(t,1),0,PI)'");
}
#[test]
fn hue_builder_rejects_single_quote_in_user_input() {
    let b = HueRotationBuilder::new("PI*sin(t)+'evil'");
    assert!(b.build().is_err());
}
```

## Evidence pointers

- `poc-work/poc-4-escape-policy/animated-hue.mp4` (escaped commas)
- `poc-work/poc-4-escape-policy/animated-hue-UNESCAPED.mp4` (unescaped commas, same bytes)
- `poc-work/poc-4-escape-policy/retest-native/test_lut3d.py` (no-shell confirmation)
