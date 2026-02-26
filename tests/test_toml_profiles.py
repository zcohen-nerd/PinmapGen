"""
Test cases for TOML-based MCU profile loading, registry auto-discovery,
normalization, and canonical pinmap generation.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.pinmapgen.mcu_profiles import PinCapability, PinInfo
from tools.pinmapgen.profile_loader import TOMLProfile, _parse_capabilities
from tools.pinmapgen.profile_registry import ProfileRegistry, registry


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_PROFILES_DIR = Path(__file__).resolve().parent.parent / "tools" / "pinmapgen" / "profiles"
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ============================================================================
# Registry tests
# ============================================================================


class TestProfileRegistry(unittest.TestCase):
    """Test the ProfileRegistry auto-discovery and API."""

    def test_builtin_profiles_discovered(self):
        """All 13 built-in TOML profiles should be discovered."""
        profiles = registry.list_profiles()
        expected = {
            "rp2040", "rp2350",
            "esp32", "esp32s3", "esp32c3",
            "stm32g0", "stm32f411", "stm32h743",
            "nrf52840",
            "atmega328p", "atmega2560",
            "atsamd21", "atsamd51",
        }
        self.assertTrue(expected.issubset(set(profiles)), f"Missing: {expected - set(profiles)}")

    def test_contains(self):
        """The ``in`` operator should work case-insensitively."""
        self.assertIn("rp2040", registry)
        self.assertIn("RP2040", registry)
        self.assertIn("Rp2040", registry)
        self.assertNotIn("nonexistent_mcu", registry)

    def test_get_profile_returns_toml_profile(self):
        profile = registry.get_profile("rp2040")
        self.assertIsInstance(profile, TOMLProfile)

    def test_get_profile_unknown_raises(self):
        with self.assertRaises(KeyError):
            registry.get_profile("nonexistent_mcu_xyz")

    def test_get_profile_info(self):
        info = registry.get_profile_info("rp2040")
        self.assertEqual(info["name"], "rp2040")
        self.assertEqual(info["source"], "toml")
        self.assertEqual(info["family"], "rp2")
        self.assertIn("RP2040", info["display_name"])

    def test_list_profiles_sorted(self):
        profiles = registry.list_profiles()
        self.assertEqual(profiles, sorted(profiles))

    def test_add_profile_dir(self):
        """Adding a user directory discovers TOML files in it."""
        tmpdir = tempfile.mkdtemp()
        try:
            toml_content = b"""
[profile]
schema_version = 1
name = "test_custom_mcu"

[normalization]
canonical_prefix = "X"
allow_numeric = true

[[pins.groups]]
range = { prefix = "X", start = 0, end = 3 }
capabilities = ["gpio"]
"""
            Path(tmpdir, "test_custom_mcu.toml").write_bytes(toml_content)

            reg = ProfileRegistry(discover_builtins=False)
            self.assertEqual(len(reg), 0)

            reg.add_profile_dir(tmpdir)
            self.assertIn("test_custom_mcu", reg)
            profile = reg.get_profile("test_custom_mcu")
            self.assertEqual(profile.normalize_pin_name("X2"), "X2")
        finally:
            shutil.rmtree(tmpdir)

    def test_add_profile_dir_missing_raises(self):
        reg = ProfileRegistry(discover_builtins=False)
        with self.assertRaises(FileNotFoundError):
            reg.add_profile_dir("/nonexistent/path/xyz")

    def test_register_python_class_overrides_toml(self):
        """A Python class registered under the same name takes priority."""
        from tools.pinmapgen.mcu_profiles import MCUProfile

        class DummyProfile(MCUProfile):
            def __init__(self):
                super().__init__("dummy")

            def _initialize_pin_definitions(self):
                self.pins["DUMMY0"] = PinInfo("DUMMY0", {PinCapability.GPIO})

            def _initialize_peripherals(self):
                pass

            def normalize_pin_name(self, pin_name):
                return "DUMMY0"

        reg = ProfileRegistry(discover_builtins=True)
        reg.register("rp2040", DummyProfile)
        profile = reg.get_profile("rp2040")
        self.assertIsInstance(profile, DummyProfile)
        self.assertNotIsInstance(profile, TOMLProfile)


# ============================================================================
# TOML loader tests
# ============================================================================


class TestTOMLLoader(unittest.TestCase):
    """Test TOMLProfile loading mechanics."""

    def test_load_rp2040_profile(self):
        """RP2040 TOML profile loads with correct pin count."""
        profile = TOMLProfile(_PROFILES_DIR / "rp2040.toml")
        self.assertEqual(profile.mcu_name, "RP2040")
        # GP0-GP29 = 30 pins
        self.assertEqual(len(profile.pins), 30)
        self.assertIn("GP0", profile.pins)
        self.assertIn("GP29", profile.pins)

    def test_load_esp32_profile(self):
        """ESP32 TOML profile loads with correct pin count."""
        profile = TOMLProfile(_PROFILES_DIR / "esp32.toml")
        self.assertEqual(profile.mcu_name, "ESP32")
        self.assertIn("GPIO0", profile.pins)
        self.assertIn("GPIO39", profile.pins)
        self.assertTrue(len(profile.pins) > 20)

    def test_load_stm32g0_profile(self):
        """STM32G0 TOML profile loads with ports A-F."""
        profile = TOMLProfile(_PROFILES_DIR / "stm32g0.toml")
        self.assertIn("PA0", profile.pins)
        self.assertIn("PB0", profile.pins)
        self.assertIn("PF0", profile.pins)

    def test_load_nrf52840_profile(self):
        """nRF52840 TOML profile loads with P0 and P1 ports."""
        profile = TOMLProfile(_PROFILES_DIR / "nrf52840.toml")
        # 32 (P0) + 16 (P1) = 48 pins
        self.assertEqual(len(profile.pins), 48)
        self.assertIn("P0_00", profile.pins)
        self.assertIn("P0_31", profile.pins)
        self.assertIn("P1_00", profile.pins)
        self.assertIn("P1_15", profile.pins)

    def test_load_atmega328p_profile(self):
        """ATmega328P TOML profile loads with ports B, C, D."""
        profile = TOMLProfile(_PROFILES_DIR / "atmega328p.toml")
        self.assertIn("PB0", profile.pins)
        self.assertIn("PC0", profile.pins)
        self.assertIn("PD0", profile.pins)
        # PB0-PB7(8) + PC0-PC6(7) + PD0-PD7(8) = 23
        self.assertEqual(len(profile.pins), 23)


class TestAllProfilesLoad(unittest.TestCase):
    """Verify every built-in TOML profile loads without errors."""

    def test_all_profiles_instantiate(self):
        """Every .toml in profiles/ must load successfully."""
        for toml_file in sorted(_PROFILES_DIR.glob("*.toml")):
            with self.subTest(profile=toml_file.stem):
                profile = TOMLProfile(toml_file)
                self.assertGreater(len(profile.pins), 0, f"{toml_file.stem} has no pins")
                self.assertTrue(profile.mcu_name, f"{toml_file.stem} has no mcu_name")

    def test_all_profiles_have_peripherals(self):
        """Every profile should declare at least one peripheral."""
        for toml_file in sorted(_PROFILES_DIR.glob("*.toml")):
            with self.subTest(profile=toml_file.stem):
                profile = TOMLProfile(toml_file)
                self.assertGreater(
                    len(profile.peripherals), 0,
                    f"{toml_file.stem} has no peripherals",
                )


# ============================================================================
# Normalization tests — RP2040
# ============================================================================


class TestRP2040TOMLNormalization(unittest.TestCase):
    """Test RP2040 TOML profile normalizes identically to the Python profile."""

    def setUp(self):
        self.profile = TOMLProfile(_PROFILES_DIR / "rp2040.toml")

    def test_gpio_format(self):
        self.assertEqual(self.profile.normalize_pin_name("GPIO0"), "GP0")
        self.assertEqual(self.profile.normalize_pin_name("GPIO15"), "GP15")
        self.assertEqual(self.profile.normalize_pin_name("GPIO29"), "GP29")

    def test_already_canonical(self):
        self.assertEqual(self.profile.normalize_pin_name("GP0"), "GP0")
        self.assertEqual(self.profile.normalize_pin_name("GP28"), "GP28")

    def test_bare_number(self):
        self.assertEqual(self.profile.normalize_pin_name("0"), "GP0")
        self.assertEqual(self.profile.normalize_pin_name("29"), "GP29")

    def test_io_format(self):
        self.assertEqual(self.profile.normalize_pin_name("IO5"), "GP5")

    def test_usb_aliases(self):
        self.assertEqual(self.profile.normalize_pin_name("USB_DP"), "GP25")
        self.assertEqual(self.profile.normalize_pin_name("USB_DM"), "GP24")
        self.assertEqual(self.profile.normalize_pin_name("USB_DN"), "GP24")
        self.assertEqual(self.profile.normalize_pin_name("USBDP"), "GP25")
        self.assertEqual(self.profile.normalize_pin_name("USBDM"), "GP24")

    def test_adc_aliases(self):
        self.assertEqual(self.profile.normalize_pin_name("ADC0"), "GP26")
        self.assertEqual(self.profile.normalize_pin_name("ADC1"), "GP27")
        self.assertEqual(self.profile.normalize_pin_name("ADC2"), "GP28")
        self.assertEqual(self.profile.normalize_pin_name("ADC3"), "GP29")

    def test_case_insensitive(self):
        self.assertEqual(self.profile.normalize_pin_name("gpio0"), "GP0")
        self.assertEqual(self.profile.normalize_pin_name("Gpio15"), "GP15")
        self.assertEqual(self.profile.normalize_pin_name("usb_dp"), "GP25")
        self.assertEqual(self.profile.normalize_pin_name("adc0"), "GP26")

    def test_invalid_pin_raises(self):
        with self.assertRaises(ValueError):
            self.profile.normalize_pin_name("GP30")
        with self.assertRaises(ValueError):
            self.profile.normalize_pin_name("XYZ")
        with self.assertRaises(ValueError):
            self.profile.normalize_pin_name("")

    def test_whitespace_stripped(self):
        self.assertEqual(self.profile.normalize_pin_name("  GP5  "), "GP5")


# ============================================================================
# Normalization tests — STM32G0
# ============================================================================


class TestSTM32G0TOMLNormalization(unittest.TestCase):
    """Test STM32G0 TOML profile normalization."""

    def setUp(self):
        self.profile = TOMLProfile(_PROFILES_DIR / "stm32g0.toml")

    def test_already_canonical(self):
        self.assertEqual(self.profile.normalize_pin_name("PA0"), "PA0")
        self.assertEqual(self.profile.normalize_pin_name("PB15"), "PB15")

    def test_gpio_prefix(self):
        self.assertEqual(self.profile.normalize_pin_name("GPIOA0"), "PA0")
        self.assertEqual(self.profile.normalize_pin_name("GPIOB5"), "PB5")

    def test_bare_port_pin(self):
        """A0 → PA0 via the ([A-Z])(\\d+) pattern."""
        self.assertEqual(self.profile.normalize_pin_name("A0"), "PA0")
        self.assertEqual(self.profile.normalize_pin_name("B2"), "PB2")

    def test_aliases(self):
        self.assertEqual(self.profile.normalize_pin_name("SWDIO"), "PA13")
        self.assertEqual(self.profile.normalize_pin_name("SWCLK"), "PA14")
        self.assertEqual(self.profile.normalize_pin_name("NRST"), "PF2")

    def test_case_insensitive(self):
        self.assertEqual(self.profile.normalize_pin_name("pa0"), "PA0")
        self.assertEqual(self.profile.normalize_pin_name("gpiob5"), "PB5")

    def test_invalid_pin_raises(self):
        with self.assertRaises(ValueError):
            self.profile.normalize_pin_name("PG0")  # No port G on this chip
        with self.assertRaises(ValueError):
            self.profile.normalize_pin_name("123")


# ============================================================================
# Normalization tests — ESP32
# ============================================================================


class TestESP32TOMLNormalization(unittest.TestCase):
    """Test ESP32 TOML profile normalization."""

    def setUp(self):
        self.profile = TOMLProfile(_PROFILES_DIR / "esp32.toml")

    def test_already_canonical(self):
        self.assertEqual(self.profile.normalize_pin_name("GPIO0"), "GPIO0")
        self.assertEqual(self.profile.normalize_pin_name("GPIO21"), "GPIO21")

    def test_io_shorthand(self):
        self.assertEqual(self.profile.normalize_pin_name("IO2"), "GPIO2")

    def test_bare_number(self):
        self.assertEqual(self.profile.normalize_pin_name("0"), "GPIO0")
        self.assertEqual(self.profile.normalize_pin_name("36"), "GPIO36")

    def test_aliases(self):
        self.assertEqual(self.profile.normalize_pin_name("VP"), "GPIO36")
        self.assertEqual(self.profile.normalize_pin_name("VN"), "GPIO39")
        self.assertEqual(self.profile.normalize_pin_name("DAC1"), "GPIO25")
        self.assertEqual(self.profile.normalize_pin_name("DAC2"), "GPIO26")

    def test_case_insensitive(self):
        self.assertEqual(self.profile.normalize_pin_name("gpio2"), "GPIO2")
        self.assertEqual(self.profile.normalize_pin_name("io5"), "GPIO5")

    def test_invalid_pin_raises(self):
        with self.assertRaises(ValueError):
            self.profile.normalize_pin_name("GPIO40")
        with self.assertRaises(ValueError):
            self.profile.normalize_pin_name("")


# ============================================================================
# Normalization tests — nRF52840
# ============================================================================


class TestNRF52840TOMLNormalization(unittest.TestCase):
    """Test nRF52840 TOML profile normalization with P<port>_<pin> format."""

    def setUp(self):
        self.profile = TOMLProfile(_PROFILES_DIR / "nrf52840.toml")

    def test_canonical_format(self):
        self.assertEqual(self.profile.normalize_pin_name("P0_00"), "P0_00")
        self.assertEqual(self.profile.normalize_pin_name("P0_13"), "P0_13")
        self.assertEqual(self.profile.normalize_pin_name("P1_08"), "P1_08")

    def test_dot_to_underscore(self):
        """P0.13 → P0_13 via regex pattern."""
        self.assertEqual(self.profile.normalize_pin_name("P0.13"), "P0_13")
        self.assertEqual(self.profile.normalize_pin_name("P1.08"), "P1_08")

    def test_aliases(self):
        self.assertEqual(self.profile.normalize_pin_name("LED1"), "P0_13")
        self.assertEqual(self.profile.normalize_pin_name("LED2"), "P0_14")
        self.assertEqual(self.profile.normalize_pin_name("NRST"), "P0_18")

    def test_case_insensitive(self):
        self.assertEqual(self.profile.normalize_pin_name("p0_13"), "P0_13")
        self.assertEqual(self.profile.normalize_pin_name("led1"), "P0_13")

    def test_invalid_raises(self):
        with self.assertRaises(ValueError):
            self.profile.normalize_pin_name("P2_00")  # No port 2
        with self.assertRaises(ValueError):
            self.profile.normalize_pin_name("P0_32")  # Port 0 only has 0-31


# ============================================================================
# Normalization tests — ATmega328P
# ============================================================================


class TestATmega328PNormalization(unittest.TestCase):
    """Test ATmega328P TOML profile with Arduino aliases."""

    def setUp(self):
        self.profile = TOMLProfile(_PROFILES_DIR / "atmega328p.toml")

    def test_canonical_format(self):
        self.assertEqual(self.profile.normalize_pin_name("PB0"), "PB0")
        self.assertEqual(self.profile.normalize_pin_name("PD7"), "PD7")

    def test_arduino_digital_aliases(self):
        self.assertEqual(self.profile.normalize_pin_name("D0"), "PD0")
        self.assertEqual(self.profile.normalize_pin_name("D13"), "PB5")
        self.assertEqual(self.profile.normalize_pin_name("D8"), "PB0")

    def test_arduino_analog_aliases(self):
        self.assertEqual(self.profile.normalize_pin_name("A0"), "PC0")
        self.assertEqual(self.profile.normalize_pin_name("A5"), "PC5")

    def test_spi_aliases(self):
        self.assertEqual(self.profile.normalize_pin_name("SCK"), "PB5")
        self.assertEqual(self.profile.normalize_pin_name("MOSI"), "PB3")
        self.assertEqual(self.profile.normalize_pin_name("MISO"), "PB4")

    def test_i2c_aliases(self):
        self.assertEqual(self.profile.normalize_pin_name("SDA"), "PC4")
        self.assertEqual(self.profile.normalize_pin_name("SCL"), "PC5")

    def test_case_insensitive(self):
        self.assertEqual(self.profile.normalize_pin_name("d0"), "PD0")
        self.assertEqual(self.profile.normalize_pin_name("a0"), "PC0")
        self.assertEqual(self.profile.normalize_pin_name("sck"), "PB5")


# ============================================================================
# Capability and special function tests
# ============================================================================


class TestCapabilities(unittest.TestCase):
    """Test capability parsing and per-pin overrides."""

    def test_rp2040_group_capabilities(self):
        """GP0-GP22 should have full peripheral capabilities."""
        profile = TOMLProfile(_PROFILES_DIR / "rp2040.toml")
        gp0 = profile.pins["GP0"]
        self.assertIn(PinCapability.GPIO, gp0.capabilities)
        self.assertIn(PinCapability.PWM, gp0.capabilities)
        self.assertIn(PinCapability.I2C_SDA, gp0.capabilities)
        self.assertIn(PinCapability.UART_TX, gp0.capabilities)

    def test_rp2040_limited_pin(self):
        """GP23 (SMPS) should only have GPIO capability."""
        profile = TOMLProfile(_PROFILES_DIR / "rp2040.toml")
        gp23 = profile.pins["GP23"]
        self.assertEqual(gp23.capabilities, {PinCapability.GPIO})
        self.assertIsNotNone(gp23.special_function)
        self.assertIn("SMPS", gp23.special_function)

    def test_rp2040_adc_additive(self):
        """GP26-GP29 should inherit group caps PLUS adc."""
        profile = TOMLProfile(_PROFILES_DIR / "rp2040.toml")
        gp26 = profile.pins["GP26"]
        self.assertIn(PinCapability.ADC, gp26.capabilities)
        # Should also keep group caps
        self.assertIn(PinCapability.GPIO, gp26.capabilities)
        self.assertIn(PinCapability.PWM, gp26.capabilities)

    def test_nrf52840_adc_additive(self):
        """nRF52840 AIN pins should have ADC added to base caps."""
        profile = TOMLProfile(_PROFILES_DIR / "nrf52840.toml")
        p0_02 = profile.pins["P0_02"]
        self.assertIn(PinCapability.ADC, p0_02.capabilities)
        self.assertIn(PinCapability.GPIO, p0_02.capabilities)

    def test_esp32_strapping_warnings(self):
        """ESP32 strapping pins should have warnings."""
        profile = TOMLProfile(_PROFILES_DIR / "esp32.toml")
        gpio0 = profile.pins["GPIO0"]
        self.assertIsNotNone(gpio0.warnings)
        self.assertTrue(len(gpio0.warnings) > 0)

    def test_parse_capabilities_invalid(self):
        """Unknown capability string should raise ValueError."""
        with self.assertRaises(ValueError):
            _parse_capabilities(["gpio", "invalid_capability_xyz"])


class TestSpecialFunctions(unittest.TestCase):
    """Test special_function and special_function_short fields."""

    def test_rp2040_usb_special_functions(self):
        profile = TOMLProfile(_PROFILES_DIR / "rp2040.toml")
        gp25 = profile.pins["GP25"]
        self.assertIn("USB", gp25.special_function)
        self.assertEqual(gp25.special_function_short, "USB D+")

    def test_nrf52840_nfc_special_functions(self):
        profile = TOMLProfile(_PROFILES_DIR / "nrf52840.toml")
        p0_09 = profile.pins["P0_09"]
        self.assertIn("NFC", p0_09.special_function)
        self.assertEqual(p0_09.special_function_short, "NFC1")

    def test_special_functions_in_canonical_dict(self):
        """Canonical dict metadata should contain special_functions dicts."""
        profile = TOMLProfile(_PROFILES_DIR / "rp2040.toml")
        nets = {"LED": ["GP0"], "USB_DP": ["GP25"]}
        canonical = profile.create_canonical_pinmap(nets)

        metadata = canonical["metadata"]
        self.assertIn("special_functions_short", metadata)
        self.assertIn("special_functions_long", metadata)

        short = metadata["special_functions_short"]
        self.assertIn("GP25", short)
        self.assertEqual(short["GP25"], "USB D+")


# ============================================================================
# Peripherals
# ============================================================================


class TestPeripherals(unittest.TestCase):
    """Test peripheral loading from TOML profiles."""

    def test_rp2040_peripherals(self):
        profile = TOMLProfile(_PROFILES_DIR / "rp2040.toml")
        names = [p.name for p in profile.peripherals]
        self.assertIn("I2C", names)
        self.assertIn("SPI", names)
        self.assertIn("UART", names)
        self.assertIn("USB", names)
        self.assertIn("ADC", names)

    def test_peripheral_pin_mapping(self):
        profile = TOMLProfile(_PROFILES_DIR / "rp2040.toml")
        usb = [p for p in profile.peripherals if p.name == "USB"][0]
        self.assertEqual(usb.pins["dp"], "GP25")
        self.assertEqual(usb.pins["dm"], "GP24")


# ============================================================================
# Canonical pinmap generation
# ============================================================================


class TestCanonicalPinmap(unittest.TestCase):
    """Test canonical pinmap generation through TOML profiles."""

    def test_rp2040_canonical_pinmap(self):
        """RP2040 TOML profile should produce a valid canonical dict."""
        profile = TOMLProfile(_PROFILES_DIR / "rp2040.toml")
        nets = {
            "I2C0_SDA": ["GP0"],
            "I2C0_SCL": ["GP1"],
            "LED_DATA": ["GPIO4"],  # should normalize to GP4
        }
        canonical = profile.create_canonical_pinmap(nets)

        self.assertEqual(canonical["mcu"], "rp2040")
        self.assertIn("I2C0_SDA", canonical["pins"])
        self.assertIn("LED_DATA", canonical["pins"])
        # GPIO4 should have been normalized to GP4
        self.assertEqual(canonical["pins"]["LED_DATA"], ["GP4"])

    def test_stm32g0_canonical_pinmap(self):
        profile = TOMLProfile(_PROFILES_DIR / "stm32g0.toml")
        nets = {"UART_TX": ["PA9"], "UART_RX": ["PA10"]}
        canonical = profile.create_canonical_pinmap(nets)
        self.assertEqual(canonical["mcu"], "stm32g0")
        self.assertEqual(canonical["pins"]["UART_TX"], ["PA9"])

    def test_esp32_canonical_pinmap(self):
        profile = TOMLProfile(_PROFILES_DIR / "esp32.toml")
        nets = {"SENSOR": ["IO21"]}  # IO21 → GPIO21
        canonical = profile.create_canonical_pinmap(nets)
        self.assertEqual(canonical["pins"]["SENSOR"], ["GPIO21"])

    def test_nrf52840_canonical_pinmap(self):
        profile = TOMLProfile(_PROFILES_DIR / "nrf52840.toml")
        nets = {"LED": ["P0.13"]}  # dot format → underscore
        canonical = profile.create_canonical_pinmap(nets)
        self.assertEqual(canonical["pins"]["LED"], ["P0_13"])

    def test_atmega328p_canonical_pinmap(self):
        profile = TOMLProfile(_PROFILES_DIR / "atmega328p.toml")
        nets = {"LED": ["D13"]}  # Arduino alias → PB5
        canonical = profile.create_canonical_pinmap(nets)
        self.assertEqual(canonical["pins"]["LED"], ["PB5"])


# ============================================================================
# New MCU profiles — basic validation
# ============================================================================


class TestNewProfiles(unittest.TestCase):
    """Validate that each new MCU profile has sensible data."""

    def _load(self, name):
        return TOMLProfile(_PROFILES_DIR / f"{name}.toml")

    def test_rp2350_has_more_pins_than_rp2040(self):
        rp2040 = self._load("rp2040")
        rp2350 = self._load("rp2350")
        self.assertGreater(len(rp2350.pins), len(rp2040.pins))

    def test_esp32s3_normalization(self):
        profile = self._load("esp32s3")
        self.assertEqual(profile.normalize_pin_name("IO21"), "GPIO21")
        self.assertEqual(profile.normalize_pin_name("1"), "GPIO1")

    def test_esp32c3_pin_count(self):
        profile = self._load("esp32c3")
        # ESP32-C3 module exposes 15 GPIOs (GPIO11-17 used by flash)
        self.assertGreaterEqual(len(profile.pins), 15)

    def test_stm32f411_has_ports(self):
        profile = self._load("stm32f411")
        self.assertIn("PA0", profile.pins)
        self.assertIn("PB0", profile.pins)

    def test_stm32h743_has_ports(self):
        profile = self._load("stm32h743")
        self.assertIn("PA0", profile.pins)

    def test_atmega2560_has_many_pins(self):
        profile = self._load("atmega2560")
        # ATmega2560 has 86 I/O pins
        self.assertGreater(len(profile.pins), 50)

    def test_atsamd21_normalization(self):
        profile = self._load("atsamd21")
        self.assertIn("PA00", profile.pins)

    def test_atsamd51_normalization(self):
        profile = self._load("atsamd51")
        self.assertIn("PA00", profile.pins)

    def test_all_new_profiles_can_generate_canonical(self):
        """Every profile should be able to create a canonical pinmap."""
        for name in registry.list_profiles():
            with self.subTest(profile=name):
                profile = registry.get_profile(name)
                # Use first pin from the profile as a simple net
                first_pin = next(iter(profile.pins))
                nets = {"TEST_NET": [first_pin]}
                canonical = profile.create_canonical_pinmap(nets)
                self.assertEqual(canonical["mcu"], name.lower())
                self.assertIn("TEST_NET", canonical["pins"])


# ============================================================================
# CLI integration
# ============================================================================


class TestCLIListMCUs(unittest.TestCase):
    """Test --list-mcus CLI flag."""

    def test_list_mcus_output(self):
        result = subprocess.run(
            [
                sys.executable, "-m", "tools.pinmapgen.cli",
                "--list-mcus",
            ],
            capture_output=True,
            text=True,
            cwd=str(_PROJECT_ROOT),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout
        # Should list all built-in profiles
        self.assertIn("rp2040", output)
        self.assertIn("esp32", output)
        self.assertIn("nrf52840", output)
        self.assertIn("atmega328p", output)

    def test_cli_generates_with_toml_profile(self):
        """The CLI should work end-to-end using a TOML-loaded profile."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [
                    sys.executable, "-m", "tools.pinmapgen.cli",
                    "--csv", "hardware/exports/sample_netlist.csv",
                    "--mcu", "rp2040",
                    "--mcu-ref", "U1",
                    "--out-root", tmpdir,
                    "--mermaid",
                ],
                capture_output=True,
                text=True,
                cwd=str(_PROJECT_ROOT),
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            # Verify outputs were generated
            self.assertTrue(
                Path(tmpdir, "pinmaps", "pinmap.json").exists(),
                "pinmap.json not generated",
            )
            self.assertTrue(
                Path(tmpdir, "firmware", "micropython", "pinmap_micropython.py").exists(),
                "MicroPython file not generated",
            )
            self.assertTrue(
                Path(tmpdir, "firmware", "include", "pinmap_arduino.h").exists(),
                "Arduino header not generated",
            )
            self.assertTrue(
                Path(tmpdir, "firmware", "docs", "PINOUT.md").exists(),
                "Markdown docs not generated",
            )
            self.assertTrue(
                Path(tmpdir, "firmware", "docs", "pinout.mmd").exists(),
                "Mermaid diagram not generated",
            )


# ============================================================================
# Edge cases
# ============================================================================


class TestEdgeCases(unittest.TestCase):
    """Test edge cases in TOML profile handling."""

    def test_minimal_toml_profile(self):
        """A minimal profile with just a group should work."""
        tmpdir = tempfile.mkdtemp()
        try:
            content = b"""
[profile]
schema_version = 1
name = "minimal"

[normalization]
canonical_prefix = "P"
allow_numeric = true

[[pins.groups]]
range = { prefix = "P", start = 0, end = 3 }
capabilities = ["gpio"]

[[peripherals]]
name = "GPIO"
instance = 0
pins = {}
"""
            toml_path = Path(tmpdir, "minimal.toml")
            toml_path.write_bytes(content)
            profile = TOMLProfile(toml_path)
            self.assertEqual(len(profile.pins), 4)
            self.assertEqual(profile.normalize_pin_name("0"), "P0")
            self.assertEqual(profile.normalize_pin_name("P3"), "P3")
        finally:
            shutil.rmtree(tmpdir)

    def test_profile_repr(self):
        profile = TOMLProfile(_PROFILES_DIR / "rp2040.toml")
        r = repr(profile)
        self.assertIn("rp2040.toml", r)
        self.assertIn("pins=30", r)

    def test_duplicate_pin_in_group_and_individual(self):
        """Individual pin entry replaces group capabilities when using 'capabilities'."""
        tmpdir = tempfile.mkdtemp()
        try:
            content = b"""
[profile]
schema_version = 1
name = "test_override"

[normalization]
canonical_prefix = "X"

[[pins.groups]]
range = { prefix = "X", start = 0, end = 3 }
capabilities = ["gpio", "pwm", "adc"]

[[pins.individual]]
name = "X0"
capabilities = ["gpio"]

[[peripherals]]
name = "GPIO"
instance = 0
pins = {}
"""
            toml_path = Path(tmpdir, "test_override.toml")
            toml_path.write_bytes(content)
            profile = TOMLProfile(toml_path)
            # X0 should have ONLY gpio (replaced, not additive)
            self.assertEqual(profile.pins["X0"].capabilities, {PinCapability.GPIO})
            # X1 should still have all group caps
            self.assertIn(PinCapability.PWM, profile.pins["X1"].capabilities)
            self.assertIn(PinCapability.ADC, profile.pins["X1"].capabilities)
        finally:
            shutil.rmtree(tmpdir)


if __name__ == "__main__":
    unittest.main()
