# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Effect registry for discovering available effects."""

from __future__ import annotations

import re
from typing import Any

import jsonschema
import structlog
from pydantic import ValidationError

from stoat_ferret.api.schemas.effect import AutomationEnvelope
from stoat_ferret.effects.definitions import EffectDefinition
from stoat_ferret_core import Automation, Keyframe, compile_automation

logger = structlog.get_logger(__name__)

# Maps API curve names (lowercase) to Rust Keyframe curve strings (TitleCase).
_CURVE_NAME_MAP: dict[str, str] = {
    "hold": "Hold",
    "linear": "Linear",
    "exponential": "Exponential",
    "ease_in_out": "EaseInOut",
}


class EffectValidationError:
    """Structured validation error from JSON schema validation.

    Attributes:
        path: JSON path to the invalid field (e.g. "fontsize").
        message: Human-readable error description.
    """

    def __init__(self, path: str, message: str) -> None:
        self.path = path
        self.message = message

    def __repr__(self) -> str:
        return f"EffectValidationError(path={self.path!r}, message={self.message!r})"


def _validate_scalar_parameters(
    definition: EffectDefinition, scalar_parameters: dict[str, Any]
) -> list[EffectValidationError]:
    """Validate non-automation scalar parameters against the effect's JSON schema."""
    schema = definition.parameter_schema
    validator = jsonschema.Draft7Validator(schema)
    errors: list[EffectValidationError] = []
    for error in validator.iter_errors(scalar_parameters):
        path = ".".join(str(p) for p in error.absolute_path) if error.absolute_path else ""
        errors.append(EffectValidationError(path=path, message=error.message))
    return errors


def _build_rust_keyframes(envelope: AutomationEnvelope) -> str:
    """Compile an automation envelope to a Rust expression string.

    Args:
        envelope: Validated automation envelope.

    Returns:
        The compiled FFmpeg expression string.

    Raises:
        ValueError: If the Rust compiler rejects the envelope.
    """
    rust_keyframes = [
        Keyframe(t=kf.t, value=kf.value, curve=_CURVE_NAME_MAP[kf.curve])
        for kf in envelope.keyframes
    ]
    automation = Automation(default=envelope.default, keyframes=rust_keyframes)
    return compile_automation(automation)


def _process_automation_parameter(
    definition: EffectDefinition,
    name: str,
    value: dict[str, Any],
) -> tuple[list[EffectValidationError], str | None, Any]:
    """Process one automation envelope parameter.

    Args:
        definition: The effect definition.
        name: The parameter name.
        value: The automation envelope dict (must contain a ``"keyframes"`` key).

    Returns:
        A 3-tuple ``(errors, compiled_expression, scalar_default)``.
        On any error ``compiled_expression`` and ``scalar_default`` are ``None``.
        On success ``compiled_expression`` is the Rust-compiled string and
        ``scalar_default`` is the envelope's default for JSON schema injection.
    """
    errors: list[EffectValidationError] = []

    try:
        envelope = AutomationEnvelope.model_validate(value)
    except ValidationError as exc:
        for error in exc.errors():
            loc = ".".join(str(p) for p in error["loc"]) if error["loc"] else ""
            errors.append(EffectValidationError(path=loc, message=error["msg"]))
        return errors, None, None

    if name not in definition.automatable:
        errors.append(
            EffectValidationError(
                path=name,
                message=f"Parameter '{name}' is not automatable",
            )
        )
        return errors, None, None

    try:
        compiled_expression = _build_rust_keyframes(envelope)
    except ValueError as exc:
        errors.append(EffectValidationError(path=name, message=str(exc)))
        return errors, None, None

    return errors, compiled_expression, envelope.default


class EffectRegistry:
    """Registry of available effects with parameter schemas and AI hints.

    Follows the register_handler() pattern from the job queue (LRN-009).
    Effects are registered by type string and can be listed or retrieved.
    """

    def __init__(self) -> None:
        self._effects: dict[str, EffectDefinition] = {}

    def register(self, effect_type: str, definition: EffectDefinition) -> None:
        """Register an effect definition.

        Args:
            effect_type: Unique identifier for the effect (e.g., "text_overlay").
            definition: The effect definition with schema, hints, and preview.
        """
        self._effects[effect_type] = definition
        logger.info("effect_registered", effect_type=effect_type)

    def get(self, effect_type: str) -> EffectDefinition | None:
        """Get an effect definition by type.

        Args:
            effect_type: The effect type identifier.

        Returns:
            The effect definition, or None if not found.
        """
        return self._effects.get(effect_type)

    def list_all(self) -> list[tuple[str, EffectDefinition]]:
        """List all registered effects.

        Returns:
            List of (effect_type, definition) tuples.
        """
        return list(self._effects.items())

    def validate(self, effect_type: str, parameters: dict[str, Any]) -> list[EffectValidationError]:
        """Validate parameters against the effect's JSON schema.

        This method validates scalar parameters only. For automation envelope
        support, use :meth:`validate_with_automation`.

        Args:
            effect_type: The effect type identifier.
            parameters: The parameters to validate.

        Returns:
            List of validation errors. Empty if valid.

        Raises:
            KeyError: If the effect type is not registered.
        """
        definition = self._effects.get(effect_type)
        if definition is None:
            msg = f"Unknown effect type: {effect_type}"
            raise KeyError(msg)

        return _validate_scalar_parameters(definition, parameters)

    def validate_with_automation(
        self, effect_type: str, parameters: dict[str, Any]
    ) -> tuple[list[EffectValidationError], str | None]:
        """Validate parameters with automation envelope support.

        Automation envelope parameters (dicts with a ``"keyframes"`` key) are
        parsed via :class:`AutomationEnvelope`, routed through
        ``compile_automation()``, and excluded from JSON schema validation.
        Scalar parameters continue through JSON schema validation unchanged.

        Args:
            effect_type: The effect type identifier.
            parameters: The parameters to validate. Values may be scalars or
                dicts representing automation envelopes.

        Returns:
            A 2-tuple of (validation_errors, compiled_expression). The second
            element is the Rust-compiled FFmpeg expression string when an
            automation envelope was processed, or ``None`` for scalar-only
            requests.

        Raises:
            KeyError: If the effect type is not registered.
        """
        definition = self._effects.get(effect_type)
        if definition is None:
            msg = f"Unknown effect type: {effect_type}"
            raise KeyError(msg)

        errors: list[EffectValidationError] = []
        compiled_expression: str | None = None
        scalar_parameters: dict[str, Any] = {}

        for name, value in parameters.items():
            if isinstance(value, dict) and "keyframes" in value:
                param_errors, param_compiled, param_default = _process_automation_parameter(
                    definition, name, value
                )
                errors.extend(param_errors)
                if param_compiled is not None:
                    compiled_expression = param_compiled
                    # Inject the default scalar so JSON schema's "required" check passes.
                    # The schema is designed for scalar validation; the envelope bypasses
                    # range checks (the Rust compiler owns range correctness).
                    scalar_parameters[name] = param_default
            else:
                scalar_parameters[name] = value

        # Run JSON schema validation on scalar parameters only.
        if not errors:
            errors.extend(_validate_scalar_parameters(definition, scalar_parameters))

        return errors, compiled_expression

    def build_automation_filter_string(self, effect_type: str, compiled_expression: str) -> str:
        """Build a filter string for a time-varying expression.

        Includes :eval=frame so FFmpeg evaluates the expression per frame
        instead of once at stream start (the default eval=once mode).

        Args:
            effect_type: The effect type identifier (e.g., "volume").
            compiled_expression: The Rust-compiled FFmpeg expression string.

        Returns:
            The full FFmpeg filter string with :eval=frame appended.

        Raises:
            ValueError: If the effect type does not support automation filter strings.
        """
        effect_def = self._effects.get(effect_type)
        if effect_def is None or effect_def.automation_filter_template is None:
            raise ValueError(f"No automation filter string for effect_type: {effect_type}")
        template = effect_def.automation_filter_template
        escaped = compiled_expression.replace(",", r"\,")
        if "{expr_T}" in template:
            expr_uppercase_t = re.sub(r"\bt\b", "T", escaped)
            return template.replace("{expr_T}", expr_uppercase_t)
        return template.replace("{expr}", escaped)
