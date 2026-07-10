// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Grant Wickman

//! Keyframe→expression compiler for automation envelopes.
//!
//! Provides [`py_compile_automation`] which converts an [`Automation`] (a list of
//! time-stamped [`Keyframe`]s with curve kinds) into a nested FFmpeg expression
//! string in variable `t`.

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3_stub_gen::derive::{gen_stub_pyclass, gen_stub_pyfunction};

use crate::ffmpeg::expression::{BinaryOp, Expr, Variable};

/// Curve interpolation kind between two consecutive keyframes.
/// Note: #[gen_stub_pyclass] is intentionally omitted — pyo3-stub-gen 0.17 does not support
/// PyO3 enum classes. The CurveKind stub is hand-written in _core.pyi (LRN-079 step 3).
#[pyclass]
#[derive(Debug, Clone)]
pub enum CurveKind {
    /// Step function: holds the previous keyframe's value until the next keyframe.
    Hold,
    /// Linear interpolation between keyframe values.
    Linear,
    /// Quadratic (exponential-feel) interpolation between keyframe values.
    Exponential,
    /// Cubic bezier ease-in-out (smooth-step) interpolation.
    EaseInOut,
}

/// A single keyframe at a specific time with a value and outgoing curve kind.
///
/// The `curve` field is stored as a string (`"Hold"`, `"Linear"`, `"Exponential"`,
/// `"EaseInOut"`) for hashability — see LRN-088.
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct Keyframe {
    /// Time in seconds.
    #[pyo3(get)]
    pub t: f64,
    /// Value at this keyframe.
    #[pyo3(get)]
    pub value: f64,
    /// Outgoing curve kind stored as string for hashability (LRN-088).
    #[pyo3(get)]
    pub curve: String,
}

#[pymethods]
impl Keyframe {
    /// Creates a new Keyframe.
    #[new]
    fn py_new(t: f64, value: f64, curve: String) -> Self {
        Self { t, value, curve }
    }

    fn __repr__(&self) -> String {
        format!(
            "Keyframe(t={}, value={}, curve={:?})",
            self.t, self.value, self.curve
        )
    }
}

/// A time-varying automation envelope: a default value and an ordered list of keyframes.
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct Automation {
    /// Default value returned when no keyframes are present.
    #[pyo3(get)]
    pub default: f64,
    /// Ordered list of keyframes (must have strictly increasing `t` values).
    #[pyo3(get)]
    pub keyframes: Vec<Keyframe>,
}

#[pymethods]
impl Automation {
    /// Creates a new Automation envelope.
    #[new]
    fn py_new(default: f64, keyframes: Vec<Keyframe>) -> Self {
        Self { default, keyframes }
    }

    fn __repr__(&self) -> String {
        format!(
            "Automation(default={}, keyframes=[{} items])",
            self.default,
            self.keyframes.len()
        )
    }
}

/// Compiles an [`Automation`] envelope into a nested FFmpeg expression string in variable `t`.
///
/// - Zero keyframes → returns a constant equal to `automation.default`.
/// - One keyframe → returns a constant equal to `keyframe.value`.
/// - N keyframes → returns a nested `if(lt(t,...))` expression covering each segment.
///
/// Returns [`pyo3::exceptions::PyValueError`] if keyframe times are not strictly increasing.
#[gen_stub_pyfunction]
#[pyfunction]
#[pyo3(name = "compile_automation")]
pub fn py_compile_automation(automation: &Automation) -> PyResult<String> {
    Ok(compile_automation_impl(automation)?.to_string())
}

/// Internal implementation returning an [`Expr`] tree.
///
/// Separated from the public function to allow test-side evaluation without
/// reparsing the compiled string.
pub(crate) fn compile_automation_impl(automation: &Automation) -> PyResult<Expr> {
    let kf = &automation.keyframes;

    if kf.is_empty() {
        return Ok(Expr::constant(automation.default));
    }
    if kf.len() == 1 {
        return Ok(Expr::constant(kf[0].value));
    }

    // Validate: keyframe times must be strictly increasing.
    for i in 1..kf.len() {
        if kf[i].t <= kf[i - 1].t {
            return Err(PyValueError::new_err(
                "keyframe times must be strictly increasing",
            ));
        }
    }

    // Build nested if-then-else right-to-left.
    // Tail: value after the last keyframe.
    let mut expr = Expr::constant(kf[kf.len() - 1].value);

    for i in (0..kf.len() - 1).rev() {
        let segment = build_segment(&kf[i], &kf[i + 1])?;
        expr = Expr::if_then_else(
            Expr::lt(Expr::var(Variable::T), Expr::constant(kf[i + 1].t)),
            segment,
            expr,
        );
    }

    // Prepend before-first-keyframe case: return first keyframe's value.
    Ok(Expr::if_then_else(
        Expr::lt(Expr::var(Variable::T), Expr::constant(kf[0].t)),
        Expr::constant(kf[0].value),
        expr,
    ))
}

/// Builds the interpolation [`Expr`] for the segment `t ∈ [kf0.t, kf1.t)`.
fn build_segment(kf0: &Keyframe, kf1: &Keyframe) -> PyResult<Expr> {
    let t0 = kf0.t;
    let t1 = kf1.t;
    let v0 = kf0.value;
    let v1 = kf1.value;
    let dt = t1 - t0;

    match kf0.curve.as_str() {
        "Hold" => Ok(Expr::constant(v0)),

        "Linear" => {
            // v0 + (v1 - v0) * (t - t0) / dt
            let u = (Expr::var(Variable::T) - Expr::constant(t0)) / Expr::constant(dt);
            Ok(Expr::constant(v0) + Expr::constant(v1 - v0) * u)
        }

        "Exponential" => {
            // v0 + (v1 - v0) * u²  where u = (t - t0) / dt
            let u = (Expr::var(Variable::T) - Expr::constant(t0)) / Expr::constant(dt);
            let u_sq = Expr::BinaryOp(BinaryOp::Pow, Box::new(u), Box::new(Expr::constant(2.0)));
            Ok(Expr::constant(v0) + Expr::constant(v1 - v0) * u_sq)
        }

        "EaseInOut" => {
            // s = 3u² − 2u³  where u = (t − t0) / dt
            // v = v0 + (v1 − v0) * s
            let u_for_sq = (Expr::var(Variable::T) - Expr::constant(t0)) / Expr::constant(dt);
            let u_for_cu = (Expr::var(Variable::T) - Expr::constant(t0)) / Expr::constant(dt);
            let u_sq = Expr::BinaryOp(
                BinaryOp::Pow,
                Box::new(u_for_sq),
                Box::new(Expr::constant(2.0)),
            );
            let u_cu = Expr::BinaryOp(
                BinaryOp::Pow,
                Box::new(u_for_cu),
                Box::new(Expr::constant(3.0)),
            );
            let s = Expr::constant(3.0) * u_sq - Expr::constant(2.0) * u_cu;
            Ok(Expr::constant(v0) + Expr::constant(v1 - v0) * s)
        }

        other => Err(PyValueError::new_err(format!(
            "unknown curve kind: {other}"
        ))),
    }
}

// ---- Tests ----

#[cfg(test)]
mod tests {
    use super::*;
    use proptest::prelude::*;

    // --- Helper: evaluate an Expr tree at a given t ---

    fn eval_expr(expr: &Expr, t: f64) -> f64 {
        use crate::ffmpeg::expression::{FuncName, UnaryOp};
        match expr {
            Expr::Const(v) => *v,
            Expr::Var(Variable::T) => t,
            Expr::Var(_) => 0.0,
            Expr::BinaryOp(op, a, b) => {
                let av = eval_expr(a, t);
                let bv = eval_expr(b, t);
                match op {
                    BinaryOp::Add => av + bv,
                    BinaryOp::Sub => av - bv,
                    BinaryOp::Mul => av * bv,
                    BinaryOp::Div => {
                        if bv == 0.0 {
                            0.0
                        } else {
                            av / bv
                        }
                    }
                    BinaryOp::Pow => av.powf(bv),
                }
            }
            Expr::UnaryOp(UnaryOp::Neg, e) => -eval_expr(e, t),
            Expr::Func(FuncName::If, args) if args.len() == 3 => {
                if eval_expr(&args[0], t) != 0.0 {
                    eval_expr(&args[1], t)
                } else {
                    eval_expr(&args[2], t)
                }
            }
            Expr::Func(FuncName::Lt, args) if args.len() == 2 => {
                if eval_expr(&args[0], t) < eval_expr(&args[1], t) {
                    1.0
                } else {
                    0.0
                }
            }
            _ => 0.0,
        }
    }

    fn kf(t: f64, value: f64, curve: &str) -> Keyframe {
        Keyframe {
            t,
            value,
            curve: curve.to_string(),
        }
    }

    fn auto(default: f64, keyframes: Vec<Keyframe>) -> Automation {
        Automation { default, keyframes }
    }

    // --- Unit tests: one per curve kind ---

    #[test]
    fn test_hold_midpoint() {
        let a = auto(0.0, vec![kf(0.0, 1.0, "Hold"), kf(1.0, 2.0, "Hold")]);
        let expr = compile_automation_impl(&a).unwrap();
        // Hold: midpoint returns v0 = 1.0
        assert!((eval_expr(&expr, 0.5) - 1.0).abs() < 1e-10);
    }

    #[test]
    fn test_linear_midpoint() {
        let a = auto(0.0, vec![kf(0.0, 0.0, "Linear"), kf(1.0, 1.0, "Linear")]);
        let expr = compile_automation_impl(&a).unwrap();
        assert!((eval_expr(&expr, 0.5) - 0.5).abs() < 1e-10);
        assert!((eval_expr(&expr, 0.25) - 0.25).abs() < 1e-10);
    }

    #[test]
    fn test_exponential_midpoint() {
        // u² at u=0.5 → 0.25; v = 0 + 1*0.25 = 0.25
        let a = auto(
            0.0,
            vec![kf(0.0, 0.0, "Exponential"), kf(1.0, 1.0, "Exponential")],
        );
        let expr = compile_automation_impl(&a).unwrap();
        assert!((eval_expr(&expr, 0.5) - 0.25).abs() < 1e-10);
    }

    #[test]
    fn test_ease_in_out_midpoint() {
        // s = 3*(0.5)² − 2*(0.5)³ = 0.75 − 0.25 = 0.5
        let a = auto(
            0.0,
            vec![kf(0.0, 0.0, "EaseInOut"), kf(1.0, 1.0, "EaseInOut")],
        );
        let expr = compile_automation_impl(&a).unwrap();
        assert!((eval_expr(&expr, 0.5) - 0.5).abs() < 1e-10);
    }

    // --- Endpoint invariant ---

    #[test]
    fn test_endpoint_invariant_all_curves() {
        for curve in &["Hold", "Linear", "Exponential", "EaseInOut"] {
            let keyframes = vec![kf(0.0, 2.0, curve), kf(3.0, 5.0, curve)];
            let a = auto(0.0, keyframes);
            let expr = compile_automation_impl(&a).unwrap();
            assert!(
                (eval_expr(&expr, 0.0) - 2.0).abs() < 1e-10,
                "curve={curve}: endpoint at t=0 failed"
            );
            assert!(
                (eval_expr(&expr, 3.0) - 5.0).abs() < 1e-10,
                "curve={curve}: endpoint at t=3 failed"
            );
        }
    }

    #[test]
    fn test_endpoint_invariant_three_keyframes() {
        let keyframes = vec![
            kf(0.0, 1.0, "Linear"),
            kf(2.0, 3.0, "Linear"),
            kf(5.0, -1.0, "Linear"),
        ];
        let a = auto(0.0, keyframes.clone());
        let expr = compile_automation_impl(&a).unwrap();
        for keyframe in &keyframes {
            let result = eval_expr(&expr, keyframe.t);
            assert!(
                (result - keyframe.value).abs() < 1e-10,
                "t={}: expected {}, got {result}",
                keyframe.t,
                keyframe.value
            );
        }
    }

    // --- Edge cases ---

    #[test]
    fn test_zero_keyframes_returns_default() {
        let result = py_compile_automation(&auto(3.14, vec![])).unwrap();
        assert_eq!(result, "3.14");
    }

    #[test]
    fn test_zero_keyframes_integer_default() {
        let result = py_compile_automation(&auto(5.0, vec![])).unwrap();
        assert_eq!(result, "5");
    }

    #[test]
    fn test_one_keyframe_returns_constant() {
        let result = py_compile_automation(&auto(0.0, vec![kf(5.0, 7.0, "Linear")])).unwrap();
        assert_eq!(result, "7");
    }

    #[test]
    fn test_two_keyframe_structure() {
        let a = auto(0.0, vec![kf(0.0, 0.0, "Linear"), kf(1.0, 1.0, "Linear")]);
        let result = py_compile_automation(&a).unwrap();
        // Must start with: if(lt(t,0),0,if(lt(t,1),...
        assert!(
            result.starts_with("if(lt(t,0),0,if(lt(t,1),"),
            "unexpected: {result}"
        );
        // Must end with the last keyframe value
        assert!(result.ends_with(",1))"), "unexpected: {result}");
    }

    // --- Constructor and repr coverage (py_new / __repr__) ---

    #[test]
    fn test_keyframe_py_new_and_repr() {
        let kf = Keyframe::py_new(1.5, 2.0, "Linear".to_string());
        assert!((kf.t - 1.5).abs() < 1e-10);
        assert!((kf.value - 2.0).abs() < 1e-10);
        assert_eq!(kf.curve, "Linear");
        let repr = kf.__repr__();
        assert!(repr.contains("Keyframe"), "repr: {repr}");
        assert!(repr.contains("Linear"), "repr: {repr}");
    }

    #[test]
    fn test_automation_py_new_and_repr() {
        let kf = Keyframe::py_new(0.0, 0.5, "Hold".to_string());
        let a = Automation::py_new(0.25, vec![kf]);
        assert!((a.default - 0.25).abs() < 1e-10);
        assert_eq!(a.keyframes.len(), 1);
        let repr = a.__repr__();
        assert!(repr.contains("Automation"), "repr: {repr}");
        assert!(repr.contains("1 items"), "repr: {repr}");
    }

    // --- Non-monotonic rejection ---

    #[test]
    fn test_non_monotonic_rejected() {
        let a = auto(0.0, vec![kf(1.0, 0.0, "Linear"), kf(0.5, 1.0, "Linear")]);
        let result = py_compile_automation(&a);
        assert!(result.is_err());
        assert!(result
            .unwrap_err()
            .to_string()
            .contains("strictly increasing"));
    }

    #[test]
    fn test_equal_times_rejected() {
        let a = auto(0.0, vec![kf(1.0, 0.0, "Linear"), kf(1.0, 1.0, "Linear")]);
        assert!(py_compile_automation(&a).is_err());
    }

    // --- Before / after keyframe region ---

    #[test]
    fn test_before_first_keyframe_returns_first_value() {
        let a = auto(0.0, vec![kf(5.0, 10.0, "Linear"), kf(10.0, 20.0, "Linear")]);
        let expr = compile_automation_impl(&a).unwrap();
        assert!((eval_expr(&expr, 0.0) - 10.0).abs() < 1e-10);
        assert!((eval_expr(&expr, 4.99) - 10.0).abs() < 1e-10);
    }

    #[test]
    fn test_after_last_keyframe_returns_last_value() {
        let a = auto(0.0, vec![kf(0.0, 0.0, "Linear"), kf(1.0, 5.0, "Linear")]);
        let expr = compile_automation_impl(&a).unwrap();
        assert!((eval_expr(&expr, 2.0) - 5.0).abs() < 1e-10);
        assert!((eval_expr(&expr, 100.0) - 5.0).abs() < 1e-10);
    }

    // --- Proptest suite ---

    fn arb_curve_kind() -> impl Strategy<Value = String> {
        prop_oneof![
            Just("Hold".to_string()),
            Just("Linear".to_string()),
            Just("Exponential".to_string()),
            Just("EaseInOut".to_string()),
        ]
    }

    /// Generates monotonically increasing keyframes using integer times (avoids float precision issues).
    fn arb_monotonic_keyframes() -> BoxedStrategy<Vec<Keyframe>> {
        proptest::collection::vec((0i32..=1000, -100.0f64..100.0), 0..=100)
            .prop_map(|mut pairs| {
                pairs.sort_by_key(|&(t, _)| t);
                pairs.dedup_by_key(|p| p.0);
                pairs
                    .into_iter()
                    .map(|(t, v)| Keyframe {
                        t: t as f64,
                        value: v,
                        curve: "Linear".to_string(),
                    })
                    .collect::<Vec<_>>()
            })
            .boxed()
    }

    /// Generates monotonically increasing keyframes with random curve kinds.
    fn arb_monotonic_keyframes_all_curves() -> BoxedStrategy<Vec<Keyframe>> {
        proptest::collection::vec((0i32..=1000, -100.0f64..100.0, arb_curve_kind()), 0..=100)
            .prop_map(|mut triples| {
                triples.sort_by_key(|&(t, _, _)| t);
                triples.dedup_by_key(|p| p.0);
                triples
                    .into_iter()
                    .map(|(t, v, c)| Keyframe {
                        t: t as f64,
                        value: v,
                        curve: c,
                    })
                    .collect::<Vec<_>>()
            })
            .boxed()
    }

    proptest! {
        /// compile_automation never panics on any valid (monotonic) Automation input.
        #[test]
        fn prop_never_panics(kfs in arb_monotonic_keyframes_all_curves()) {
            let a = Automation { default: 0.0, keyframes: kfs };
            let result = py_compile_automation(&a);
            prop_assert!(result.is_ok(), "returned Err on valid input");
        }

        /// Non-monotonic sequences (t2 <= t1) return Err, not panic.
        #[test]
        fn prop_non_monotonic_returns_err(
            t1 in 0i32..1000,
            t2 in 0i32..1000,
            v1 in -10.0f64..10.0,
            v2 in -10.0f64..10.0,
        ) {
            prop_assume!(t2 <= t1); // non-monotonic: second not strictly greater
            let a = Automation {
                default: 0.0,
                keyframes: vec![
                    Keyframe { t: t1 as f64, value: v1, curve: "Linear".to_string() },
                    Keyframe { t: t2 as f64, value: v2, curve: "Linear".to_string() },
                ],
            };
            prop_assert!(py_compile_automation(&a).is_err());
        }

        /// Endpoint invariant: for Linear curves, expression evaluates to keyframe value at each keyframe time.
        #[test]
        fn prop_endpoint_invariant(kfs in arb_monotonic_keyframes()) {
            prop_assume!(!kfs.is_empty());
            let a = Automation { default: 0.0, keyframes: kfs.clone() };
            let expr = compile_automation_impl(&a).unwrap();
            for keyframe in &kfs {
                let result = eval_expr(&expr, keyframe.t);
                prop_assert!(
                    (result - keyframe.value).abs() < 1e-6,
                    "endpoint: t={}, expected={}, got={result}",
                    keyframe.t,
                    keyframe.value
                );
            }
        }

        /// Output expression is non-empty for any input.
        #[test]
        fn prop_output_non_empty(kfs in arb_monotonic_keyframes_all_curves()) {
            let a = Automation { default: 0.0, keyframes: kfs };
            if let Ok(s) = py_compile_automation(&a) {
                prop_assert!(!s.is_empty());
                prop_assert!(!s.contains("NaN"));
                prop_assert!(!s.contains("inf"));
            }
        }
    }
}
