"""
TOML profile schema validation for PinmapGen.

Design decision
---------------
We use **stdlib-only validation** (manual type checks + dataclass-like
constants) instead of pydantic or jsonschema.  The project has a hard
``stdlib-only`` constraint — ``pyproject.toml`` declares **zero** runtime
dependencies — and adding a validation library would break that rule for
every user.  The checks below provide equivalent coverage with actionable
error messages that include the profile file path, failing field, and
expected type/value.

Schema version: 1 (required in ``profile.schema_version``).
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from .mcu_profiles import PinCapability

_logger = logging.getLogger(__name__)

CURRENT_SCHEMA_VERSION = 1

# Valid capability strings (derived from PinCapability enum).
_VALID_CAPABILITIES: frozenset[str] = frozenset(c.value for c in PinCapability)

# ── Known keys per section (unknown keys are rejected to prevent typos) ───

_TOP_LEVEL_KEYS = frozenset({"profile", "normalization", "pins", "peripherals"})

_PROFILE_KEYS = frozenset({
    "name", "schema_version",
    "display_name", "description", "family",
})

_NORMALIZATION_KEYS = frozenset({
    "canonical_prefix", "allow_numeric", "patterns", "aliases",
})

_NORM_PATTERN_KEYS = frozenset({"regex", "output"})

_PIN_GROUP_KEYS = frozenset({"range", "names", "capabilities"})

_PIN_RANGE_KEYS = frozenset({"prefix", "start", "end"})

_PIN_INDIVIDUAL_KEYS = frozenset({
    "name", "capabilities", "add_capabilities",
    "special_function", "special_function_short",
    "warnings", "alternate_names",
})

_PERIPHERAL_KEYS = frozenset({"name", "instance", "pins"})

# Safe identifier: lowercase letter followed by lowercase letters/digits/-/_
_SAFE_ID_RE = re.compile(r"[a-z][a-z0-9_-]*$")


# ── Public API ────────────────────────────────────────────────────────────


class ProfileValidationError(Exception):
    """Raised when a TOML profile fails schema validation.

    Attributes:
        errors: List of individual error descriptions.
        profile_path: Path to the failing TOML file.
    """

    def __init__(self, errors: list[str], path: Path | str) -> None:
        self.errors = errors
        self.profile_path = str(path)
        detail = "\n  ".join(errors)
        super().__init__(f"Invalid profile '{path}':\n  {detail}")


def validate_profile_toml(
    data: dict[str, Any],
    file_path: Path | str,
) -> list[str]:
    """Validate a parsed TOML profile dict against the v1 schema.

    Args:
        data: The raw dict produced by ``tomllib.load()``.
        file_path: Path to the TOML file (used in error messages).

    Returns:
        List of non-fatal warning strings.

    Raises:
        ProfileValidationError: If one or more validation errors are found.
            The exception ``errors`` attribute lists every problem.
    """
    file_path = Path(file_path)
    errors: list[str] = []
    warnings: list[str] = []

    # ── Top-level unknown keys ────────────────────────────────────────────
    _check_unknown_keys(data, _TOP_LEVEL_KEYS, "", errors)

    # ── [profile] section ─────────────────────────────────────────────────
    profile_cfg = data.get("profile")
    if profile_cfg is None:
        errors.append("Missing required section: [profile]")
    elif not isinstance(profile_cfg, dict):
        errors.append(
            f"[profile] must be a table, got {type(profile_cfg).__name__}"
        )
    else:
        _check_unknown_keys(profile_cfg, _PROFILE_KEYS, "profile", errors)
        _validate_profile_section(profile_cfg, file_path, errors, warnings)

    # ── [normalization] section ───────────────────────────────────────────
    norm_cfg = data.get("normalization")
    if norm_cfg is not None:
        if not isinstance(norm_cfg, dict):
            errors.append(
                f"[normalization] must be a table, "
                f"got {type(norm_cfg).__name__}"
            )
        else:
            # ``patterns`` and ``aliases`` are sub-tables, not top-level
            # normalization keys for the unknown-key check.
            _check_unknown_keys(
                norm_cfg, _NORMALIZATION_KEYS, "normalization", errors,
            )
            _validate_normalization_section(norm_cfg, errors)

    # ── [pins] section ────────────────────────────────────────────────────
    pins_cfg = data.get("pins")
    all_canonical_pins: set[str] = set()
    if pins_cfg is not None:
        if not isinstance(pins_cfg, dict):
            errors.append(
                f"[pins] must be a table, got {type(pins_cfg).__name__}"
            )
        else:
            _check_unknown_keys(
                pins_cfg, frozenset({"groups", "individual"}), "pins", errors,
            )
            all_canonical_pins = _validate_pins_section(pins_cfg, errors)

    # ── [[peripherals]] section ───────────────────────────────────────────
    peris = data.get("peripherals")
    if peris is not None:
        if not isinstance(peris, list):
            errors.append(
                f"[[peripherals]] must be an array of tables, "
                f"got {type(peris).__name__}"
            )
        else:
            _validate_peripherals(peris, errors)

    # ── Cross-reference: alias targets must resolve to canonical pins ─────
    if norm_cfg and isinstance(norm_cfg, dict) and all_canonical_pins:
        aliases = norm_cfg.get("aliases")
        if isinstance(aliases, dict):
            _validate_alias_targets(aliases, all_canonical_pins, errors)

    if errors:
        raise ProfileValidationError(errors, file_path)

    return warnings


# ── Section validators ────────────────────────────────────────────────────


def _validate_profile_section(
    cfg: dict[str, Any],
    file_path: Path,
    errors: list[str],
    warnings: list[str],
) -> None:
    # schema_version — required int
    sv = cfg.get("schema_version")
    if sv is None:
        errors.append(
            "Missing required field: profile.schema_version (int). "
            "Add 'schema_version = 1' to the [profile] section."
        )
    elif not isinstance(sv, int):
        errors.append(
            f"profile.schema_version must be int, "
            f"got {type(sv).__name__}"
        )
    elif sv != CURRENT_SCHEMA_VERSION:
        errors.append(
            f"Unsupported profile.schema_version={sv}. "
            f"Expected {CURRENT_SCHEMA_VERSION}."
        )

    # name — required, safe identifier
    name = cfg.get("name")
    if name is None:
        errors.append("Missing required field: profile.name")
    elif not isinstance(name, str):
        errors.append(
            f"profile.name must be str, got {type(name).__name__}"
        )
    else:
        if not _SAFE_ID_RE.match(name):
            errors.append(
                f"profile.name '{name}' is not a safe identifier. "
                f"Use only lowercase letters, digits, hyphens, or "
                f"underscores, starting with a letter."
            )
        # Warn if name doesn't match filename stem
        if name != file_path.stem:
            warnings.append(
                f"profile.name '{name}' does not match filename stem "
                f"'{file_path.stem}'. Consider renaming to match."
            )

    # Optional typed fields
    for field, expected_type in [
        ("display_name", str),
        ("description", str),
        ("family", str),
    ]:
        val = cfg.get(field)
        if val is not None and not isinstance(val, expected_type):
            errors.append(
                f"profile.{field} must be {expected_type.__name__}, "
                f"got {type(val).__name__}"
            )


def _validate_normalization_section(
    cfg: dict[str, Any],
    errors: list[str],
) -> None:
    cp = cfg.get("canonical_prefix")
    if cp is not None and not isinstance(cp, str):
        errors.append(
            f"normalization.canonical_prefix must be str, "
            f"got {type(cp).__name__}"
        )

    an = cfg.get("allow_numeric")
    if an is not None and not isinstance(an, bool):
        errors.append(
            f"normalization.allow_numeric must be bool, "
            f"got {type(an).__name__}"
        )

    # patterns
    patterns = cfg.get("patterns")
    if patterns is not None:
        if not isinstance(patterns, list):
            errors.append(
                f"normalization.patterns must be an array, "
                f"got {type(patterns).__name__}"
            )
        else:
            for i, pat in enumerate(patterns):
                ctx = f"normalization.patterns[{i}]"
                if not isinstance(pat, dict):
                    errors.append(f"{ctx} must be a table")
                    continue
                _check_unknown_keys(pat, _NORM_PATTERN_KEYS, ctx, errors)
                if "regex" not in pat:
                    errors.append(f"{ctx}: missing required key 'regex'")
                elif not isinstance(pat["regex"], str):
                    errors.append(f"{ctx}.regex must be str")
                if "output" not in pat:
                    errors.append(f"{ctx}: missing required key 'output'")
                elif not isinstance(pat["output"], str):
                    errors.append(f"{ctx}.output must be str")

    # aliases
    aliases = cfg.get("aliases")
    if aliases is not None:
        if not isinstance(aliases, dict):
            errors.append(
                f"normalization.aliases must be a table, "
                f"got {type(aliases).__name__}"
            )
        else:
            for key, val in aliases.items():
                if not isinstance(val, str):
                    errors.append(
                        f"normalization.aliases.{key} must be str, "
                        f"got {type(val).__name__}"
                    )


def _validate_pins_section(
    cfg: dict[str, Any],
    errors: list[str],
) -> set[str]:
    """Validate pins section and return set of all canonical pin names."""
    canonical_pins: set[str] = set()

    # groups
    groups = cfg.get("groups")
    if groups is not None:
        if not isinstance(groups, list):
            errors.append(
                f"pins.groups must be an array, "
                f"got {type(groups).__name__}"
            )
        else:
            for i, grp in enumerate(groups):
                ctx = f"pins.groups[{i}]"
                if not isinstance(grp, dict):
                    errors.append(f"{ctx} must be a table")
                    continue
                _check_unknown_keys(grp, _PIN_GROUP_KEYS, ctx, errors)

                # capabilities must be list[str]
                caps = grp.get("capabilities")
                if caps is not None:
                    _validate_capabilities_field(caps, f"{ctx}.capabilities", errors)

                # Must have range OR names (not both)
                has_range = "range" in grp
                has_names = "names" in grp
                if not has_range and not has_names:
                    errors.append(f"{ctx}: must have 'range' or 'names'")
                elif has_range and has_names:
                    errors.append(
                        f"{ctx}: cannot have both 'range' and 'names'"
                    )

                if has_range:
                    rng = grp["range"]
                    if not isinstance(rng, dict):
                        errors.append(f"{ctx}.range must be a table")
                    else:
                        _check_unknown_keys(
                            rng, _PIN_RANGE_KEYS, f"{ctx}.range", errors,
                        )
                        for rk in ("prefix", "start", "end"):
                            if rk not in rng:
                                errors.append(  # noqa: PERF401
                                    f"{ctx}.range: missing required "
                                    f"key '{rk}'"
                                )
                        if all(k in rng for k in ("prefix", "start", "end")):
                            try:
                                prefix = rng["prefix"]
                                start = int(rng["start"])
                                end = int(rng["end"])
                                for n in range(start, end + 1):
                                    canonical_pins.add(f"{prefix}{n}")
                            except (TypeError, ValueError):
                                errors.append(
                                    f"{ctx}.range: start/end must be integers"
                                )

                if has_names:
                    names = grp["names"]
                    if not isinstance(names, list):
                        errors.append(f"{ctx}.names must be an array")
                    else:
                        for n in names:
                            if not isinstance(n, str):
                                errors.append(
                                    f"{ctx}.names: all entries must "
                                    f"be strings"
                                )
                                break
                            canonical_pins.add(n)

    # individual
    indiv = cfg.get("individual")
    if indiv is not None:
        if not isinstance(indiv, list):
            errors.append(
                f"pins.individual must be an array, "
                f"got {type(indiv).__name__}"
            )
        else:
            for i, pin in enumerate(indiv):
                ctx = f"pins.individual[{i}]"
                if not isinstance(pin, dict):
                    errors.append(f"{ctx} must be a table")
                    continue
                _check_unknown_keys(
                    pin, _PIN_INDIVIDUAL_KEYS, ctx, errors,
                )

                pname = pin.get("name")
                if pname is None:
                    errors.append(f"{ctx}: missing required key 'name'")
                elif not isinstance(pname, str):
                    errors.append(f"{ctx}.name must be str")
                else:
                    canonical_pins.add(pname)

                # capabilities and add_capabilities must be list[str]
                for field in ("capabilities", "add_capabilities"):
                    val = pin.get(field)
                    if val is not None:
                        _validate_capabilities_field(
                            val, f"{ctx}.{field}", errors,
                        )

                # warnings and alternate_names must be list[str]
                for field in ("warnings", "alternate_names"):
                    val = pin.get(field)
                    if val is not None:
                        if not isinstance(val, list):
                            errors.append(
                                f"{ctx}.{field} must be a list, "
                                f"got {type(val).__name__}"
                            )
                        elif not all(isinstance(v, str) for v in val):
                            errors.append(
                                f"{ctx}.{field}: all entries must be strings"
                            )

                # special_function / special_function_short — str
                for field in (
                    "special_function",
                    "special_function_short",
                ):
                    val = pin.get(field)
                    if val is not None and not isinstance(val, str):
                        errors.append(
                            f"{ctx}.{field} must be str, "
                            f"got {type(val).__name__}"
                        )

    return canonical_pins


def _validate_peripherals(
    peris: list[Any],
    errors: list[str],
) -> None:
    for i, peri in enumerate(peris):
        ctx = f"peripherals[{i}]"
        if not isinstance(peri, dict):
            errors.append(f"{ctx} must be a table")
            continue
        _check_unknown_keys(peri, _PERIPHERAL_KEYS, ctx, errors)

        if "name" not in peri:
            errors.append(f"{ctx}: missing required key 'name'")
        elif not isinstance(peri["name"], str):
            errors.append(f"{ctx}.name must be str")

        inst = peri.get("instance")
        if inst is not None and not isinstance(inst, int):
            errors.append(
                f"{ctx}.instance must be int, got {type(inst).__name__}"
            )

        pins = peri.get("pins")
        if pins is not None and not isinstance(pins, dict):
            errors.append(
                f"{ctx}.pins must be a table, got {type(pins).__name__}"
            )


def _validate_alias_targets(
    aliases: dict[str, Any],
    canonical_pins: set[str],
    errors: list[str],
) -> None:
    """Check that every alias target resolves to a known canonical pin."""
    for alias, target in aliases.items():
        if not isinstance(target, str):
            continue  # Type error already reported above
        if target not in canonical_pins:
            errors.append(
                f"normalization.aliases.{alias}: target '{target}' "
                f"does not match any canonical pin defined in [pins]"
            )


def _validate_capabilities_field(
    value: Any,
    context: str,
    errors: list[str],
) -> None:
    """Validate that a capabilities field is ``list[str]`` with known values."""
    if isinstance(value, str):
        errors.append(
            f"{context} must be a list of strings, not a single string. "
            f'Use [{context} = ["{value}"]] instead.'
        )
        return
    if not isinstance(value, list):
        errors.append(f"{context} must be a list, got {type(value).__name__}")
        return
    for item in value:
        if not isinstance(item, str):
            errors.append(
                f"{context}: all entries must be strings, "
                f"got {type(item).__name__}"
            )
            return
        if item not in _VALID_CAPABILITIES:
            errors.append(
                f"{context}: unknown capability '{item}'. "
                f"Valid: {', '.join(sorted(_VALID_CAPABILITIES))}"
            )


# ── Helpers ───────────────────────────────────────────────────────────────


def _check_unknown_keys(
    data: dict[str, Any],
    known: frozenset[str],
    context: str,
    errors: list[str],
) -> None:
    """Append an error for every key in *data* not in *known*."""
    unknown = set(data) - known
    if unknown:
        prefix = f"[{context}]" if context else "top-level"
        errors.append(
            f"Unknown key(s) in {prefix}: {', '.join(sorted(unknown))}. "
            f"Allowed: {', '.join(sorted(known))}"
        )
