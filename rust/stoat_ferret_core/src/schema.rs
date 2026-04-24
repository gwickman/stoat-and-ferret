//! Parameter schema translator for AI-facing effect discovery.
//!
//! Decomposes JSON Schema-style parameter descriptors (as emitted by the
//! Python `stoat_ferret.effects.definitions` module) into structured
//! [`ParameterSchema`] records. AI agents consuming `/api/v1/effects` use
//! the resulting list to discover valid parameter types, bounds, enum
//! domains, and natural-language hints without reasoning about raw JSON
//! Schema.
//!
//! The entry point is [`py_parameter_schemas_from_dict`], exposed to Python
//! as `parameter_schemas_from_dict` (via `#[pyo3(name = "...")]`).
//!
//! # Shape
//!
//! ```text
//! input schema   = {"type": "object", "properties": {"fontsize": {...}}}
//! input ai_hints = {"fontsize": "Font size in pixels"}
//! output         = [ParameterSchema { name: "fontsize", param_type: "int", ... }]
//! ```

use pyo3::prelude::*;
use pyo3::types::PyDict;
use pyo3_stub_gen::derive::{gen_stub_pyclass, gen_stub_pyfunction};

/// Structured parameter metadata for a single effect parameter.
///
/// Each field maps one JSON-Schema concept (type, default, bounds, enum,
/// description) onto a concrete Python-visible field. The `ai_hint` field
/// is populated from a separate Python dict keyed by parameter name.
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug)]
pub struct ParameterSchema {
    /// Parameter name (matches the key in the JSON Schema `properties` dict).
    #[pyo3(get)]
    pub name: String,
    /// Normalised parameter type: one of `int`, `float`, `string`, `bool`,
    /// `enum`, or `array`.
    #[pyo3(get)]
    pub param_type: String,
    /// Default value as a Python object, or `None` when the schema omits one.
    #[pyo3(get)]
    pub default_value: Option<Py<PyAny>>,
    /// Lower numeric bound (from JSON Schema `minimum`), when present.
    #[pyo3(get)]
    pub min_value: Option<f64>,
    /// Upper numeric bound (from JSON Schema `maximum`), when present.
    #[pyo3(get)]
    pub max_value: Option<f64>,
    /// Allowed string values when the schema declares an `enum`.
    #[pyo3(get)]
    pub enum_values: Option<Vec<String>>,
    /// Human-readable description from the JSON Schema `description` field.
    #[pyo3(get)]
    pub description: String,
    /// AI-oriented hint sourced from the per-effect `ai_hints` mapping.
    #[pyo3(get)]
    pub ai_hint: String,
}

impl Clone for ParameterSchema {
    fn clone(&self) -> Self {
        // Access the GIL to safely clone the `Py<PyAny>` default value.
        Python::attach(|py| Self {
            name: self.name.clone(),
            param_type: self.param_type.clone(),
            default_value: self.default_value.as_ref().map(|obj| obj.clone_ref(py)),
            min_value: self.min_value,
            max_value: self.max_value,
            enum_values: self.enum_values.clone(),
            description: self.description.clone(),
            ai_hint: self.ai_hint.clone(),
        })
    }
}

#[pymethods]
impl ParameterSchema {
    fn __repr__(&self) -> String {
        format!(
            "ParameterSchema(name='{}', param_type='{}')",
            self.name, self.param_type
        )
    }
}

/// Allowed set of normalised `param_type` values emitted by the translator.
const VALID_PARAM_TYPES: &[&str] = &["int", "float", "string", "bool", "enum", "array"];

/// Returns `true` when `value` is one of the normalised parameter-type strings
/// emitted by the translator.
///
/// The allowed set is `"int"`, `"float"`, `"string"`, `"bool"`, `"enum"`, and
/// `"array"`. Any value outside this set returns `false`.
pub fn is_valid_param_type(value: &str) -> bool {
    VALID_PARAM_TYPES.contains(&value)
}

fn map_json_type(json_type: Option<&str>) -> String {
    match json_type {
        Some("integer") => "int".to_string(),
        Some("number") => "float".to_string(),
        Some("string") => "string".to_string(),
        Some("boolean") => "bool".to_string(),
        Some("array") => "array".to_string(),
        // Fall back to string for unknown or absent types so downstream
        // consumers always see a member of VALID_PARAM_TYPES.
        _ => "string".to_string(),
    }
}

/// Translate a JSON Schema parameter dict into a list of [`ParameterSchema`].
///
/// Iterates `schema["properties"]` and extracts a structured record for each
/// property. Returns an empty list when `schema` has no `properties` key
/// (including the empty-dict case).
///
/// Exposed to Python as `parameter_schemas_from_dict` (via `#[pyo3(name =
/// "...")]`).
///
/// # Args
///
/// - `schema`: JSON Schema-style dict (e.g. `{"properties": {"x": {...}}}`).
/// - `ai_hints`: Map of parameter name -> AI hint string.
///
/// # Returns
///
/// List of `ParameterSchema` objects, one per property, in iteration order.
///
/// # Errors
///
/// Returns a Python `TypeError` / `ValueError` if a property entry is not a
/// dict, or if a field cannot be coerced to its expected type.
///
/// # Example (Python)
///
/// ```python
/// from stoat_ferret_core import parameter_schemas_from_dict
///
/// schema = {
///     "properties": {
///         "fontsize": {"type": "integer", "default": 48, "minimum": 8, "maximum": 256},
///     },
/// }
/// ai_hints = {"fontsize": "Font size in pixels"}
///
/// params = parameter_schemas_from_dict(schema, ai_hints)
/// assert params[0].name == "fontsize"
/// assert params[0].param_type == "int"
/// assert params[0].ai_hint == "Font size in pixels"
/// ```
#[gen_stub_pyfunction]
#[pyfunction]
#[pyo3(name = "parameter_schemas_from_dict")]
pub fn py_parameter_schemas_from_dict(
    schema: &Bound<'_, PyDict>,
    ai_hints: &Bound<'_, PyDict>,
) -> PyResult<Vec<ParameterSchema>> {
    let Some(props_any) = schema.get_item("properties")? else {
        return Ok(Vec::new());
    };
    let properties = props_any.downcast_into::<PyDict>()?;

    let mut result = Vec::with_capacity(properties.len());
    for (key, value) in properties.iter() {
        let name: String = key.extract()?;
        let prop = value.downcast_into::<PyDict>()?;

        let json_type: Option<String> = match prop.get_item("type")? {
            Some(v) => Some(v.extract()?),
            None => None,
        };

        let enum_values: Option<Vec<String>> = match prop.get_item("enum")? {
            Some(v) => Some(v.extract()?),
            None => None,
        };

        let param_type = if enum_values.is_some() {
            "enum".to_string()
        } else {
            map_json_type(json_type.as_deref())
        };

        let default_value: Option<Py<PyAny>> = prop.get_item("default")?.map(|v| v.unbind());

        let min_value: Option<f64> = match prop.get_item("minimum")? {
            Some(v) => Some(v.extract()?),
            None => None,
        };

        let max_value: Option<f64> = match prop.get_item("maximum")? {
            Some(v) => Some(v.extract()?),
            None => None,
        };

        let description: String = match prop.get_item("description")? {
            Some(v) => v.extract()?,
            None => String::new(),
        };

        let ai_hint: String = match ai_hints.get_item(&name)? {
            Some(v) => v.extract()?,
            None => String::new(),
        };

        result.push(ParameterSchema {
            name,
            param_type,
            default_value,
            min_value,
            max_value,
            enum_values,
            description,
            ai_hint,
        });
    }

    Ok(result)
}

// ---------------------------------------------------------------------------
// Unit tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use pyo3::types::PyList;

    fn run_translator<F>(build: F) -> Vec<ParameterSchema>
    where
        F: for<'py> FnOnce(Python<'py>) -> (Bound<'py, PyDict>, Bound<'py, PyDict>),
    {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            let (schema, hints) = build(py);
            py_parameter_schemas_from_dict(&schema, &hints).unwrap()
        })
    }

    #[test]
    fn test_empty_dict_returns_empty_vec() {
        let result = run_translator(|py| (PyDict::new(py), PyDict::new(py)));
        assert!(result.is_empty());
    }

    #[test]
    fn test_schema_without_properties_returns_empty_vec() {
        let result = run_translator(|py| {
            let schema = PyDict::new(py);
            schema.set_item("type", "object").unwrap();
            (schema, PyDict::new(py))
        });
        assert!(result.is_empty());
    }

    #[test]
    fn test_enum_override() {
        let result = run_translator(|py| {
            let schema = PyDict::new(py);
            let props = PyDict::new(py);
            let prop = PyDict::new(py);
            prop.set_item("type", "string").unwrap();
            let enum_list = PyList::new(py, ["a", "b", "c"]).unwrap();
            prop.set_item("enum", enum_list).unwrap();
            props.set_item("mode", prop).unwrap();
            schema.set_item("properties", props).unwrap();
            (schema, PyDict::new(py))
        });

        assert_eq!(result.len(), 1);
        assert_eq!(result[0].name, "mode");
        assert_eq!(result[0].param_type, "enum");
        assert_eq!(
            result[0].enum_values.as_ref().unwrap(),
            &vec!["a".to_string(), "b".to_string(), "c".to_string()]
        );
    }

    #[test]
    fn test_array_type_supported() {
        let result = run_translator(|py| {
            let schema = PyDict::new(py);
            let props = PyDict::new(py);
            let prop = PyDict::new(py);
            prop.set_item("type", "array").unwrap();
            props.set_item("weights", prop).unwrap();
            schema.set_item("properties", props).unwrap();
            (schema, PyDict::new(py))
        });

        assert_eq!(result.len(), 1);
        assert_eq!(result[0].param_type, "array");
    }

    #[test]
    fn test_bounds_ordering() {
        let result = run_translator(|py| {
            let schema = PyDict::new(py);
            let props = PyDict::new(py);
            let prop = PyDict::new(py);
            prop.set_item("type", "number").unwrap();
            prop.set_item("minimum", 0.25_f64).unwrap();
            prop.set_item("maximum", 4.0_f64).unwrap();
            props.set_item("factor", prop).unwrap();
            schema.set_item("properties", props).unwrap();
            (schema, PyDict::new(py))
        });

        assert_eq!(result.len(), 1);
        let p = &result[0];
        assert_eq!(p.param_type, "float");
        let (min, max) = (p.min_value.unwrap(), p.max_value.unwrap());
        assert!(min <= max, "min ({min}) must be <= max ({max})");
    }

    #[test]
    fn test_valid_param_types() {
        let result = run_translator(|py| {
            let schema = PyDict::new(py);
            let props = PyDict::new(py);
            for (name, json_type) in [
                ("n_int", "integer"),
                ("n_num", "number"),
                ("n_str", "string"),
                ("n_bool", "boolean"),
                ("n_arr", "array"),
            ] {
                let prop = PyDict::new(py);
                prop.set_item("type", json_type).unwrap();
                props.set_item(name, prop).unwrap();
            }
            schema.set_item("properties", props).unwrap();
            (schema, PyDict::new(py))
        });

        assert_eq!(result.len(), 5);
        for p in &result {
            assert!(
                is_valid_param_type(&p.param_type),
                "param_type {:?} not in VALID_PARAM_TYPES",
                p.param_type
            );
        }
    }

    #[test]
    fn test_ai_hint_lookup() {
        let result = run_translator(|py| {
            let schema = PyDict::new(py);
            let props = PyDict::new(py);
            let prop = PyDict::new(py);
            prop.set_item("type", "string").unwrap();
            prop.set_item("description", "the text").unwrap();
            props.set_item("text", prop).unwrap();
            schema.set_item("properties", props).unwrap();

            let hints = PyDict::new(py);
            hints.set_item("text", "Natural-language hint").unwrap();
            (schema, hints)
        });

        assert_eq!(result.len(), 1);
        let p = &result[0];
        assert_eq!(p.description, "the text");
        assert_eq!(p.ai_hint, "Natural-language hint");
    }

    #[test]
    fn test_default_value_preserved() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            let schema = PyDict::new(py);
            let props = PyDict::new(py);
            let prop = PyDict::new(py);
            prop.set_item("type", "integer").unwrap();
            prop.set_item("default", 48_i64).unwrap();
            props.set_item("fontsize", prop).unwrap();
            schema.set_item("properties", props).unwrap();
            let hints = PyDict::new(py);

            let result = py_parameter_schemas_from_dict(&schema, &hints).unwrap();
            assert_eq!(result.len(), 1);
            let default = result[0].default_value.as_ref().expect("default present");
            let as_int: i64 = default.extract(py).unwrap();
            assert_eq!(as_int, 48);
        });
    }

    #[test]
    fn test_missing_type_and_enum_defaults_to_string() {
        let result = run_translator(|py| {
            let schema = PyDict::new(py);
            let props = PyDict::new(py);
            let prop = PyDict::new(py);
            prop.set_item("description", "untyped").unwrap();
            props.set_item("x", prop).unwrap();
            schema.set_item("properties", props).unwrap();
            (schema, PyDict::new(py))
        });

        assert_eq!(result.len(), 1);
        assert_eq!(result[0].param_type, "string");
    }
}

// ---------------------------------------------------------------------------
// Property tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod proptests {
    use super::*;
    use proptest::prelude::*;
    use pyo3::types::PyList;

    fn build_synthetic_schema<'py>(
        py: Python<'py>,
        entries: &[(
            String,
            &'static str,
            Option<(f64, f64)>,
            Option<Vec<String>>,
        )],
    ) -> Bound<'py, PyDict> {
        let schema = PyDict::new(py);
        let props = PyDict::new(py);
        for (name, json_type, bounds, enum_values) in entries {
            let prop = PyDict::new(py);
            prop.set_item("type", *json_type).unwrap();
            if let Some((lo, hi)) = bounds {
                prop.set_item("minimum", *lo).unwrap();
                prop.set_item("maximum", *hi).unwrap();
            }
            if let Some(values) = enum_values {
                let list = PyList::new(py, values).unwrap();
                prop.set_item("enum", list).unwrap();
            }
            props.set_item(name.as_str(), prop).unwrap();
        }
        schema.set_item("properties", props).unwrap();
        schema
    }

    proptest! {
        #[test]
        fn param_type_always_in_valid_set(
            json_type in prop::sample::select(vec![
                "integer", "number", "string", "boolean", "array",
            ]),
            has_enum in any::<bool>(),
        ) {
            pyo3::prepare_freethreaded_python();
            Python::with_gil(|py| {
                let entries = vec![(
                    "x".to_string(),
                    json_type,
                    None,
                    if has_enum {
                        Some(vec!["a".into(), "b".into()])
                    } else {
                        None
                    },
                )];
                let schema = build_synthetic_schema(py, &entries);
                let result = py_parameter_schemas_from_dict(&schema, &PyDict::new(py))
                    .unwrap();
                prop_assert_eq!(result.len(), 1);
                prop_assert!(
                    is_valid_param_type(&result[0].param_type),
                    "param_type {:?} not in VALID_PARAM_TYPES",
                    result[0].param_type,
                );
                Ok(())
            }).unwrap();
        }

        #[test]
        fn bounds_preserve_ordering(
            lo in -1000.0f64..1000.0f64,
            delta in 0.0f64..1000.0f64,
        ) {
            pyo3::prepare_freethreaded_python();
            Python::with_gil(|py| {
                let hi = lo + delta;
                let entries = vec![(
                    "x".to_string(),
                    "number",
                    Some((lo, hi)),
                    None,
                )];
                let schema = build_synthetic_schema(py, &entries);
                let result = py_parameter_schemas_from_dict(&schema, &PyDict::new(py))
                    .unwrap();
                prop_assert_eq!(result.len(), 1);
                let p = &result[0];
                prop_assert!(p.min_value.unwrap() <= p.max_value.unwrap());
                Ok(())
            }).unwrap();
        }
    }
}
