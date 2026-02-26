"""Tests for profile schema validation, collision detection, and CLI profiles.

Covers:
  - Valid TOML loads without errors
  - Missing schema_version fails with clear error
  - capabilities as single string fails
  - Alias target missing fails
  - Unknown keys rejected
  - Duplicate profile.name within a directory raises ProfileCollisionError
  - Python class overrides TOML (registry priority)
  - Deterministic ordering (sorted output)
  - CLI ``profiles list`` and ``profiles check`` subcommands
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import ClassVar

from tools.pinmapgen.mcu_profiles import MCUProfile, PinCapability, PinInfo
from tools.pinmapgen.profile_loader import TOMLProfile
from tools.pinmapgen.profile_registry import ProfileCollisionError, ProfileRegistry
from tools.pinmapgen.profile_schema import (
    CURRENT_SCHEMA_VERSION,
    ProfileValidationError,
    validate_profile_toml,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PROFILES_DIR = Path(__file__).resolve().parent.parent / "tools" / "pinmapgen" / "profiles"

_VALID_TOML = b"""\
[profile]
schema_version = 1
name = "testmcu"
display_name = "Test MCU"
description = "A unit-test MCU"
family = "test"

[normalization]
canonical_prefix = "P"
allow_numeric = true

[[normalization.patterns]]
regex = '(?i)GPIO(\\d+)'
output = "P{0}"

[normalization.aliases]
VCC = "P0"

[[pins.groups]]
range = { prefix = "P", start = 0, end = 7 }
capabilities = ["gpio", "pwm"]

[[pins.individual]]
name = "P0"
add_capabilities = ["adc"]
special_function = "Power supply"
special_function_short = "VCC"

[[peripherals]]
name = "SPI"
instance = 0
pins = { mosi = "P3", miso = "P4", sck = "P5" }
"""


def _make_toml_dir(*files: tuple[str, bytes]) -> str:
    """Create a temp dir with the given (filename, content) pairs."""
    tmpdir = tempfile.mkdtemp()
    for name, content in files:
        Path(tmpdir, name).write_bytes(content)
    return tmpdir


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


class TestSchemaValidation(unittest.TestCase):
    """Tests for ``validate_profile_toml()``."""

    def test_valid_toml_no_errors(self):
        """A well-formed TOML produces no errors and returns warnings."""
        import tomllib

        data = tomllib.loads(_VALID_TOML.decode())
        warnings = validate_profile_toml(data, Path("testmcu.toml"))
        self.assertIsInstance(warnings, list)

    def test_missing_schema_version_errors(self):
        """Missing profile.schema_version raises with a clear message."""
        data = {
            "profile": {"name": "bad"},
            "pins": {
                "groups": [
                    {"range": {"prefix": "P", "start": 0, "end": 1},
                     "capabilities": ["gpio"]},
                ],
            },
        }
        with self.assertRaises(ProfileValidationError) as ctx:
            validate_profile_toml(data, Path("bad.toml"))
        self.assertTrue(
            any("schema_version" in e for e in ctx.exception.errors),
            f"Expected schema_version error, got: {ctx.exception.errors}",
        )

    def test_wrong_schema_version_errors(self):
        """Unsupported schema_version raises."""
        data = {
            "profile": {"name": "future", "schema_version": 999},
            "pins": {"groups": []},
        }
        with self.assertRaises(ProfileValidationError) as ctx:
            validate_profile_toml(data, Path("future.toml"))
        self.assertTrue(
            any("999" in e for e in ctx.exception.errors),
        )

    def test_capabilities_as_single_string_errors(self):
        """capabilities given as a bare string instead of list[str] fails."""
        data = {
            "profile": {"name": "caps", "schema_version": 1},
            "pins": {
                "groups": [
                    {"range": {"prefix": "P", "start": 0, "end": 1},
                     "capabilities": "gpio"},
                ],
            },
        }
        with self.assertRaises(ProfileValidationError) as ctx:
            validate_profile_toml(data, Path("caps.toml"))
        self.assertTrue(
            any("single string" in e for e in ctx.exception.errors),
            f"Expected 'single string' error, got: {ctx.exception.errors}",
        )

    def test_alias_target_missing_errors(self):
        """Alias whose target is not a canonical pin errors."""
        data = {
            "profile": {"name": "alias", "schema_version": 1},
            "normalization": {
                "aliases": {"VBUS": "NONEXISTENT_PIN"},
            },
            "pins": {
                "groups": [
                    {"range": {"prefix": "P", "start": 0, "end": 1},
                     "capabilities": ["gpio"]},
                ],
            },
        }
        with self.assertRaises(ProfileValidationError) as ctx:
            validate_profile_toml(data, Path("alias.toml"))
        self.assertTrue(
            any("NONEXISTENT_PIN" in e for e in ctx.exception.errors),
        )

    def test_unknown_top_level_key_errors(self):
        """Unknown top-level keys are rejected."""
        data = {
            "profile": {"name": "unk", "schema_version": 1},
            "pins": {"groups": []},
            "bogus_section": {},
        }
        with self.assertRaises(ProfileValidationError) as ctx:
            validate_profile_toml(data, Path("unk.toml"))
        self.assertTrue(
            any("bogus_section" in e for e in ctx.exception.errors),
        )

    def test_unknown_profile_key_errors(self):
        """Unknown keys inside [profile] are rejected."""
        data = {
            "profile": {"name": "unk2", "schema_version": 1, "colour": "red"},
            "pins": {"groups": []},
        }
        with self.assertRaises(ProfileValidationError) as ctx:
            validate_profile_toml(data, Path("unk2.toml"))
        self.assertTrue(
            any("colour" in e for e in ctx.exception.errors),
        )

    def test_unsafe_profile_name_errors(self):
        """Profile name starting with digit or containing uppercase fails."""
        data = {
            "profile": {"name": "3bad", "schema_version": 1},
            "pins": {"groups": []},
        }
        with self.assertRaises(ProfileValidationError) as ctx:
            validate_profile_toml(data, Path("3bad.toml"))
        self.assertTrue(
            any("safe identifier" in e for e in ctx.exception.errors),
        )

    def test_name_mismatch_warns(self):
        """profile.name not matching filename stem produces a warning."""
        data = {
            "profile": {"name": "alpha", "schema_version": 1},
            "pins": {"groups": []},
        }
        warnings = validate_profile_toml(data, Path("beta.toml"))
        self.assertTrue(
            any("does not match" in w for w in warnings),
            f"Expected name-mismatch warning, got: {warnings}",
        )

    def test_current_schema_version_constant(self):
        """CURRENT_SCHEMA_VERSION should be 1."""
        self.assertEqual(CURRENT_SCHEMA_VERSION, 1)

    def test_group_missing_range_and_names_errors(self):
        """A pin group without 'range' or 'names' errors."""
        data = {
            "profile": {"name": "grp", "schema_version": 1},
            "pins": {
                "groups": [{"capabilities": ["gpio"]}],
            },
        }
        with self.assertRaises(ProfileValidationError) as ctx:
            validate_profile_toml(data, Path("grp.toml"))
        self.assertTrue(
            any("'range' or 'names'" in e for e in ctx.exception.errors),
        )

    def test_individual_pin_missing_name_errors(self):
        """An individual pin without 'name' errors."""
        data = {
            "profile": {"name": "ind", "schema_version": 1},
            "pins": {
                "individual": [{"capabilities": ["gpio"]}],
            },
        }
        with self.assertRaises(ProfileValidationError) as ctx:
            validate_profile_toml(data, Path("ind.toml"))
        self.assertTrue(
            any("'name'" in e for e in ctx.exception.errors),
        )

    def test_peripheral_missing_name_errors(self):
        """A peripheral without 'name' errors."""
        data = {
            "profile": {"name": "peri", "schema_version": 1},
            "peripherals": [{"instance": 0}],
        }
        with self.assertRaises(ProfileValidationError) as ctx:
            validate_profile_toml(data, Path("peri.toml"))
        self.assertTrue(
            any("'name'" in e for e in ctx.exception.errors),
        )

    def test_all_builtin_profiles_validate(self):
        """Every built-in TOML profile passes schema validation."""
        import tomllib

        for toml_file in sorted(_PROFILES_DIR.glob("*.toml")):
            with toml_file.open("rb") as fh:
                data = tomllib.load(fh)
            warnings = validate_profile_toml(data, toml_file)
            # Warnings are OK, errors would raise.
            self.assertIsInstance(warnings, list, toml_file.name)


# ---------------------------------------------------------------------------
# Collision detection (registry)
# ---------------------------------------------------------------------------


class TestCollisionDetection(unittest.TestCase):
    """Tests for ProfileRegistry collision/priority rules."""

    def test_same_dir_duplicate_name_errors(self):
        """Two TOMLs in the same directory with the same profile.name error."""
        toml_a = b"""\
[profile]
schema_version = 1
name = "dupe"

[[pins.groups]]
range = { prefix = "P", start = 0, end = 1 }
capabilities = ["gpio"]
"""
        toml_b = b"""\
[profile]
schema_version = 1
name = "dupe"

[[pins.groups]]
range = { prefix = "Q", start = 0, end = 1 }
capabilities = ["gpio"]
"""
        tmpdir = _make_toml_dir(("a.toml", toml_a), ("b.toml", toml_b))
        try:
            reg = ProfileRegistry(discover_builtins=False)
            with self.assertRaises(ProfileCollisionError) as ctx:
                reg.add_profile_dir(tmpdir)
            self.assertIn("dupe", str(ctx.exception))
        finally:
            shutil.rmtree(tmpdir)

    def test_python_overrides_toml(self):
        """register() with a Python class overrides TOML of the same name."""

        class _FakeProfile(MCUProfile):
            def __init__(self):
                super().__init__("rp2040")

            def _initialize_pin_definitions(self):
                self.pins["GP0"] = PinInfo(name="GP0", capabilities={PinCapability.GPIO})

            def _initialize_peripherals(self):
                pass

            def normalize_pin_name(self, pin_name: str) -> str:
                return pin_name.upper()

        reg = ProfileRegistry(discover_builtins=True)
        self.assertIn("rp2040", reg)  # TOML-based

        reg.register("rp2040", _FakeProfile)
        profile = reg.get_profile("rp2040")
        # Should be the Python class, not the TOML profile.
        self.assertIsInstance(profile, _FakeProfile)

    def test_cross_dir_override_allowed(self):
        """A user directory can override a built-in profile (no error)."""
        toml = b"""\
[profile]
schema_version = 1
name = "rp2040"

[normalization]
canonical_prefix = "GP"
allow_numeric = true

[[pins.groups]]
range = { prefix = "GP", start = 0, end = 3 }
capabilities = ["gpio"]
"""
        tmpdir = _make_toml_dir(("rp2040.toml", toml))
        try:
            reg = ProfileRegistry(discover_builtins=True)
            # Should NOT raise — user override is intentional.
            reg.add_profile_dir(tmpdir)
            # The user's version has only 4 pins.
            profile = reg.get_profile("rp2040")
            self.assertEqual(len(profile.pins), 4)
        finally:
            shutil.rmtree(tmpdir)


# ---------------------------------------------------------------------------
# Deterministic ordering
# ---------------------------------------------------------------------------


class TestDeterministicOrder(unittest.TestCase):
    """Registry and emitter output must be sorted/deterministic."""

    def test_list_profiles_sorted(self):
        """list_profiles() returns names in sorted order."""
        reg = ProfileRegistry(discover_builtins=True)
        names = reg.list_profiles()
        self.assertEqual(names, sorted(names))

    def test_canonical_pinmap_pins_sorted(self):
        """Canonical dict pins are sorted by net name."""
        profile = TOMLProfile(_PROFILES_DIR / "rp2040.toml")
        nets = {
            "SPI0_MOSI": ["GP3"],
            "I2C0_SDA": ["GP0"],
            "LED": ["GP25"],
            "ADC0": ["GP26"],
        }
        canonical = profile.create_canonical_pinmap(nets)
        pin_keys = list(canonical["pins"].keys())
        self.assertEqual(pin_keys, sorted(pin_keys))


# ---------------------------------------------------------------------------
# CLI ``profiles`` subcommand
# ---------------------------------------------------------------------------


class TestCLIProfiles(unittest.TestCase):
    """Integration tests for the CLI ``profiles`` sub-commands."""

    _CMD_BASE: ClassVar[list[str]] = [sys.executable, "-m", "tools.pinmapgen.cli", "profiles"]

    def test_profiles_list(self):
        """``profiles list`` exits 0 and includes known profile names."""
        result = subprocess.run(
            [*self._CMD_BASE, "list"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("rp2040", result.stdout)
        self.assertIn("esp32", result.stdout)
        self.assertIn("Name", result.stdout)  # header

    def test_profiles_check_valid(self):
        """``profiles check rp2040`` exits 0 with summary info."""
        result = subprocess.run(
            [*self._CMD_BASE, "check", "rp2040"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Pin count:", result.stdout)
        self.assertIn("Validation OK", result.stdout)

    def test_profiles_check_unknown(self):
        """``profiles check nonexistent`` exits non-zero."""
        result = subprocess.run(
            [*self._CMD_BASE, "check", "nonexistent"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unknown profile", result.stderr)

    def test_profiles_list_with_profile_dir(self):
        """``profiles list --profile-dir`` discovers user profiles."""
        toml = b"""\
[profile]
schema_version = 1
name = "mymcu"

[[pins.groups]]
range = { prefix = "X", start = 0, end = 1 }
capabilities = ["gpio"]
"""
        tmpdir = _make_toml_dir(("mymcu.toml", toml))
        try:
            result = subprocess.run(
                [*self._CMD_BASE, "--profile-dir", tmpdir, "list"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("mymcu", result.stdout)
        finally:
            shutil.rmtree(tmpdir)


# ---------------------------------------------------------------------------
# Full load validation integration
# ---------------------------------------------------------------------------


class TestFullLoadValidation(unittest.TestCase):
    """Ensure TOMLProfile.__init__ enforces schema validation."""

    def test_missing_schema_version_rejects_load(self):
        """Loading a TOML without schema_version raises."""
        toml = b"""\
[profile]
name = "noversion"

[[pins.groups]]
range = { prefix = "P", start = 0, end = 1 }
capabilities = ["gpio"]
"""
        tmpdir = _make_toml_dir(("noversion.toml", toml))
        try:
            with self.assertRaises(ProfileValidationError):
                TOMLProfile(Path(tmpdir, "noversion.toml"))
        finally:
            shutil.rmtree(tmpdir)


if __name__ == "__main__":
    unittest.main()
