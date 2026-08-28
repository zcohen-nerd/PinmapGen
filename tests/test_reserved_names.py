"""
Tests for the P1.5 audit fix (reserved identifiers in generated code)
and the P2.3 collision-handling fixes in naming.build_name_map.

A net named MOSI must not #define over the Arduino core's MOSI inside
<SPI.h>; a net named SPI must not rebind the MicroPython class the
generated module imports. Collisions resolve fairly (the net that IS the
identifier keeps it), never produce duplicates, and are always announced.
"""

import unittest

import tempfile
from pathlib import Path

from tools.pinmapgen.emit_arduino import generate_arduino_with_roles
from tools.pinmapgen.emit_markdown import emit_markdown_docs
from tools.pinmapgen.emit_micropython import generate_micropython_with_roles
from tools.pinmapgen.naming import RESERVED_IDENTIFIERS, build_name_map


def _render_markdown(cd) -> str:
    """emit_markdown_docs writes a file; render to a temp file and read."""
    with tempfile.TemporaryDirectory() as temp_dir:
        out = Path(temp_dir) / "PINOUT.md"
        emit_markdown_docs(cd, out)
        return out.read_text(encoding="utf-8")


def _canonical(pins):
    return {
        "mcu": "rp2040",
        "pins": pins,
        "differential_pairs": [],
        "metadata": {
            "total_nets": len(pins),
            "total_pins": sum(len(v) for v in pins.values()),
            "differential_pairs_count": 0,
            "special_pins_used": [],
            "validation_warnings": [],
            "validation_errors": [],
        },
    }


class TestBuildNameMap(unittest.TestCase):
    """The shared name map is fair, duplicate-free, and announced."""

    def test_reserved_names_get_pin_suffix(self):
        mapping, notes = build_name_map(["MOSI", "SPI", "A0", "LED"])
        self.assertEqual(mapping["MOSI"], "MOSI_PIN")
        self.assertEqual(mapping["SPI"], "SPI_PIN")
        self.assertEqual(mapping["A0"], "A0_PIN")
        self.assertEqual(mapping["LED"], "LED")
        self.assertEqual(len([n for n in notes if "reserved" in n]), 3)

    def test_exact_identifier_keeps_clean_name(self):
        """LED_1 keeps LED_1 even though LED-1 sanitizes to it too."""
        mapping, notes = build_name_map(["LED-1", "LED_1"])
        self.assertEqual(mapping["LED_1"], "LED_1")
        self.assertEqual(mapping["LED-1"], "LED_1_2")
        self.assertTrue(any("LED-1" in n for n in notes))

    def test_suffixes_never_collide_with_real_nets(self):
        """A generated _2 suffix can't shadow a net literally named that."""
        mapping, _ = build_name_map(["LED-1", "LED_1", "LED_1_2"])
        values = list(mapping.values())
        self.assertEqual(len(values), len(set(values)), values)
        self.assertEqual(mapping["LED_1"], "LED_1")
        self.assertEqual(mapping["LED_1_2"], "LED_1_2")

    def test_clean_names_produce_no_notes(self):
        mapping, notes = build_name_map(["LED_STATUS", "I2C0_SDA"])
        self.assertEqual(notes, [])
        self.assertEqual(mapping["LED_STATUS"], "LED_STATUS")

    def test_reserved_set_covers_the_dangerous_names(self):
        for name in ("MOSI", "MISO", "SCK", "SS", "SDA", "SCL",
                     "SPI", "I2C", "PWM", "ADC", "LED_BUILTIN",
                     "HIGH", "LOW", "INPUT", "OUTPUT", "A0", "A15"):
            self.assertIn(name, RESERVED_IDENTIFIERS, name)


class TestEmittersUseReservedSafeNames(unittest.TestCase):
    """Generated code never shadows core/language symbols."""

    def setUp(self):
        self.cd = _canonical({
            "MOSI": ["GP4"], "MISO": ["GP3"], "SCK": ["GP2"],
            "SPI": ["GP5"], "LED": ["GP6"],
        })

    def test_arduino_header_does_not_clobber_core_symbols(self):
        header = generate_arduino_with_roles(self.cd)
        self.assertIn("#define MOSI_PIN 4", header)
        self.assertIn("#define SPI_PIN 5", header)
        self.assertNotIn("#define MOSI 4", header)
        self.assertNotIn("#define SPI 5", header)

    def test_micropython_does_not_shadow_machine_classes(self):
        code = generate_micropython_with_roles(self.cd)
        self.assertIn("MOSI_PIN = 4", code)
        self.assertIn("SPI_PIN = 5", code)
        self.assertNotIn("\nSPI = ", code)
        self.assertNotIn("\nMOSI = ", code)

    def test_markdown_examples_reference_the_same_constants(self):
        """PINOUT.md examples use the exact emitted identifiers."""
        docs = _render_markdown(self.cd)
        self.assertNotIn("Pin(MOSI,", docs)
        self.assertNotIn("pinMode(MOSI,", docs)


class TestMarkdownExampleSafety(unittest.TestCase):
    """Usage examples never drive rails or unknown nets as outputs."""

    def test_power_nets_are_never_example_material(self):
        cd = _canonical({
            "GND": ["GP7"], "3V3": ["GP8"], "VBUS": ["GP9"],
            "LED_STATUS": ["GP5"], "SENSE": ["GP6"],
        })
        docs = _render_markdown(cd)
        self.assertNotIn("Pin(GND", docs)
        self.assertNotIn("Pin(_3V3", docs)
        self.assertNotIn("pinMode(VBUS", docs)
        # LED example drives out; unknown nets default to input.
        self.assertIn("Pin(LED_STATUS, Pin.OUT)", docs)
        self.assertIn("Pin(SENSE, Pin.IN)", docs)
        self.assertIn("pinMode(SENSE, INPUT);", docs)


if __name__ == "__main__":
    unittest.main()
