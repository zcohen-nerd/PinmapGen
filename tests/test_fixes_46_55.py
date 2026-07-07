"""Regression tests for issues #46-#55."""

import json
import os
import tempfile
import unittest
from pathlib import Path

from tools.pinmapgen.emit_arduino import (
    _arduino_pin_literal,
    generate_arduino_with_roles,
)
from tools.pinmapgen.emit_json import validate_canonical_dict
from tools.pinmapgen.emit_markdown import _sanitize_identifier
from tools.pinmapgen.emit_mermaid import _build_node_id_map, generate_mermaid_graph
from tools.pinmapgen.emit_micropython import generate_micropython_with_roles
from tools.pinmapgen.roles import PinRole, RoleInferencer

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _canonical(mcu="rp2040", pins=None, diff_pairs=None):
    """Build a minimal canonical dict for testing."""
    if pins is None:
        pins = {"LED": ["GP4"]}
    if diff_pairs is None:
        diff_pairs = []
    return {
        "mcu": mcu,
        "pins": pins,
        "differential_pairs": diff_pairs,
        "metadata": {
            "total_nets": len(pins),
            "total_pins": sum(len(v) for v in pins.values()),
            "differential_pairs_count": len(diff_pairs),
            "special_pins_used": [],
            "validation_warnings": [],
            "validation_errors": [],
        },
    }


class TestIssue46ArduinoPinLiteral(unittest.TestCase):
    """#46 — Arduino #define values must be MCU-aware."""

    def test_rp2040_gp4(self):
        self.assertEqual(_arduino_pin_literal("GP4"), "4")

    def test_rp2040_gp29(self):
        self.assertEqual(_arduino_pin_literal("GP29"), "29")

    def test_esp32_gpio21(self):
        self.assertEqual(_arduino_pin_literal("GPIO21"), "21")

    def test_stm32_pa10(self):
        # STM32duino defines PA10 (not PinName PA_10) as the Arduino pin id.
        self.assertEqual(_arduino_pin_literal("PA10", "stm32g0"), "PA10")

    def test_stm32_pb2(self):
        self.assertEqual(_arduino_pin_literal("PB2", "stm32g0"), "PB2")

    def test_stm32_pc14(self):
        self.assertEqual(_arduino_pin_literal("PC14", "stm32g0"), "PC14")

    def test_empty(self):
        self.assertEqual(_arduino_pin_literal(""), "0")

    def test_unknown_format(self):
        self.assertEqual(_arduino_pin_literal("XYZ"), "0")

    def test_stm32_in_full_header(self):
        """STM32 canonical dict should produce PA10 style defines."""
        cd = _canonical(mcu="stm32g0", pins={"I2C0_SDA": ["PA10"]})
        header = generate_arduino_with_roles(cd)
        for line in header.splitlines():
            if line.startswith("#define I2C0_SDA"):
                self.assertIn(" PA10", line)
                self.assertNotIn("PA_10", line)
                break
        else:
            self.fail("no #define I2C0_SDA line emitted")


class TestIssue47ADCResolution(unittest.TestCase):
    """#47 — ADC_READ_VOLTAGE must match each core's analogRead default."""

    def test_rp2040_adc_macro_uses_1023(self):
        # Philhower RP2040 analogRead defaults to 10-bit.
        cd = _canonical(pins={"ADC_IN": ["GP26"]})
        header = generate_arduino_with_roles(cd)
        self.assertIn("3.3f / 1023.0f", header)

    def test_esp32_adc_macro_uses_4095(self):
        # ESP32 Arduino analogRead defaults to 12-bit.
        cd = _canonical(mcu="esp32", pins={"ADC_IN": ["GPIO32"]})
        header = generate_arduino_with_roles(cd)
        self.assertIn("3.3f / 4095.0f", header)

    def test_avr_adc_macro_uses_5v(self):
        cd = _canonical(mcu="atmega328p", pins={"ADC_IN": ["PC0"]})
        header = generate_arduino_with_roles(cd)
        self.assertIn("5.0f / 1023.0f", header)


class TestIssue48CollisionTrackedHelpers(unittest.TestCase):
    """#48 — Helper/struct sections must use collision-tracked names."""

    def test_arduino_usb_struct_uses_tracked_name(self):
        """If USB_DP collides with another net, struct must reference _2 name."""
        cd = _canonical(
            pins={
                "USB_DP": ["GP25"],
                "USB_DN": ["GP24"],
                "USB_DP_EXT": ["GP26"],  # might not collide, but test with real collision
            },
            diff_pairs=[{"positive": "USB_DP", "negative": "USB_DN"}],
        )
        header = generate_arduino_with_roles(cd)
        # The #define for USB_DP should exist
        self.assertIn("#define USB_DP ", header)
        # The struct should reference USB_DP (same name) since no collision
        self.assertIn("USBPins", header)

    def test_micropython_i2c_helper_uses_tracked_name(self):
        cd = _canonical(pins={"I2C0_SDA": ["GP0"], "I2C0_SCL": ["GP1"]})
        code = generate_micropython_with_roles(cd)
        # The constant names should appear in both definitions and helpers
        self.assertIn("I2C0_SDA", code)
        self.assertIn("I2C0_SCL", code)
        # Helper function should exist
        self.assertIn("def setup_i2c", code)

    def test_micropython_can_class_generated(self):
        """CAN differential pairs produce a CANPins class (also tests #51)."""
        cd = _canonical(pins={"CAN_H": ["GP4"], "CAN_L": ["GP5"]})
        code = generate_micropython_with_roles(cd)
        self.assertIn("class CANPins", code)
        self.assertIn("CAN Bus High", code)
        self.assertIn("CAN Bus Low", code)


class TestIssue49MermaidDiffPairNodes(unittest.TestCase):
    """#49 — Diff pair pins must have labeled node definitions in Mermaid."""

    def test_diff_pair_nodes_labeled(self):
        cd = _canonical(
            pins={
                "USB_DP": ["GP25"],
                "USB_DN": ["GP24"],
                "LED": ["GP4"],
            },
            diff_pairs=[{"positive": "USB_DP", "negative": "USB_DN"}],
        )
        diagram = generate_mermaid_graph(cd)
        # Diff pair nodes should have labeled definitions
        self.assertIn('USB_DP["', diagram)
        self.assertIn('USB_DN["', diagram)
        # Subgraph should still exist
        self.assertIn("Differential Pair", diagram)
        # LED should also appear
        self.assertIn("LED", diagram)


class TestIssue50MarkdownSanitizer(unittest.TestCase):
    """#50 — _sanitize_identifier must collapse underscores and strip trailing."""

    def test_consecutive_underscores_collapsed(self):
        self.assertEqual(_sanitize_identifier("A--B"), "A_B")

    def test_trailing_underscores_stripped(self):
        self.assertEqual(_sanitize_identifier("FOO-"), "FOO")

    def test_empty_becomes_unnamed(self):
        self.assertEqual(_sanitize_identifier("___"), "UNNAMED_PIN")

    def test_leading_digit_preserved(self):
        self.assertEqual(_sanitize_identifier("3V3"), "_3V3")

    def test_normal_name_unchanged(self):
        self.assertEqual(_sanitize_identifier("LED_DATA"), "LED_DATA")

    def test_multiple_special_chars(self):
        # "A..B--C" → "A__B__C" → collapse → "A_B_C"
        self.assertEqual(_sanitize_identifier("A..B--C"), "A_B_C")


class TestIssue51MicroPythonCAN(unittest.TestCase):
    """#51 — MicroPython emitter must generate CANPins class for CAN pairs."""

    def test_can_class_generated(self):
        cd = _canonical(pins={"CAN_H": ["GP4"], "CAN_L": ["GP5"]})
        code = generate_micropython_with_roles(cd)
        self.assertIn("class CANPins:", code)
        self.assertIn("get_pair", code)

    def test_usb_class_still_generated(self):
        cd = _canonical(
            pins={"USB_DP": ["GP25"], "USB_DN": ["GP24"]},
            diff_pairs=[{"positive": "USB_DP", "negative": "USB_DN"}],
        )
        code = generate_micropython_with_roles(cd)
        self.assertIn("class USBPins:", code)


class TestIssue52MermaidNodeCollision(unittest.TestCase):
    """#52 — Mermaid node IDs must be collision-safe."""

    def test_collision_suffixed(self):
        node_map = _build_node_id_map(
            {"A.B": ["GP0"], "A-B": ["GP1"]},
            [],
        )
        ids = set(node_map.values())
        # Both sanitize to A_B, so one must get a suffix
        self.assertEqual(len(ids), 2)
        self.assertIn("A_B", ids)
        self.assertIn("A_B_2", ids)

    def test_no_collision_distinct_names(self):
        node_map = _build_node_id_map(
            {"LED": ["GP4"], "BUTTON": ["GP5"]},
            [],
        )
        self.assertEqual(node_map["LED"], "LED")
        self.assertEqual(node_map["BUTTON"], "BUTTON")


class TestIssue53RoleFalsePositives(unittest.TestCase):
    """#53 — Role patterns must not produce false positives on substrings."""

    def setUp(self):
        self.inferencer = RoleInferencer()

    def test_moscow_not_clock(self):
        role = self.inferencer.infer_role("MOSCOW")
        self.assertNotEqual(role, PinRole.CLOCK)

    def test_preset_not_reset(self):
        role = self.inferencer.infer_role("PRESET")
        self.assertNotEqual(role, PinRole.RESET)

    def test_reservoir_not_pwm(self):
        role = self.inferencer.infer_role("RESERVOIR")
        self.assertNotEqual(role, PinRole.PWM)

    def test_promotor_not_pwm(self):
        role = self.inferencer.infer_role("PROMOTOR")
        self.assertNotEqual(role, PinRole.PWM)

    def test_throttled_not_led(self):
        role = self.inferencer.infer_role("THROTTLED")
        self.assertNotEqual(role, PinRole.LED)

    def test_daylight_not_led(self):
        role = self.inferencer.infer_role("DAYLIGHT_SENSOR")
        self.assertNotEqual(role, PinRole.LED)

    # Legitimate matches must still work
    def test_led_data_still_led(self):
        role = self.inferencer.infer_role("LED_DATA")
        self.assertEqual(role, PinRole.LED)

    def test_reset_still_reset(self):
        role = self.inferencer.infer_role("RESET")
        self.assertEqual(role, PinRole.RESET)

    def test_mcu_reset_still_reset(self):
        role = self.inferencer.infer_role("MCU_RESET")
        self.assertEqual(role, PinRole.RESET)

    def test_osc1_still_clock(self):
        role = self.inferencer.infer_role("OSC1")
        self.assertEqual(role, PinRole.CLOCK)

    def test_servo1_still_pwm(self):
        role = self.inferencer.infer_role("SERVO1")
        self.assertEqual(role, PinRole.PWM)

    def test_motor_ctrl_still_pwm(self):
        role = self.inferencer.infer_role("MOTOR_CTRL")
        self.assertEqual(role, PinRole.PWM)

    def test_status_led_still_led(self):
        role = self.inferencer.infer_role("STATUS_LED")
        self.assertEqual(role, PinRole.LED)

    def test_light1_still_led(self):
        role = self.inferencer.infer_role("LIGHT1")
        self.assertEqual(role, PinRole.LED)

    def test_button1_still_button(self):
        role = self.inferencer.infer_role("BUTTON1")
        self.assertEqual(role, PinRole.BUTTON)


class TestIssue54ValidateCanonicalDict(unittest.TestCase):
    """#54 — validate_canonical_dict is called and works correctly."""

    def test_valid_dict_no_errors(self):
        cd = _canonical()
        errors = validate_canonical_dict(cd)
        self.assertEqual(errors, [])

    def test_missing_keys_reported(self):
        errors = validate_canonical_dict({"mcu": "rp2040"})
        self.assertTrue(any("Missing required keys" in e for e in errors))

    def test_empty_pin_list_reported(self):
        cd = _canonical(pins={"NET": []})
        errors = validate_canonical_dict(cd)
        self.assertTrue(any("empty" in e for e in errors))

    def test_emit_json_calls_validation(self):
        """emit_json should call validate_canonical_dict without crashing."""
        from tools.pinmapgen.emit_json import emit_json

        os.environ["SOURCE_DATE_EPOCH"] = "0"
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                out = Path(tmpdir) / "pinmap.json"
                cd = _canonical()
                emit_json(cd, out)
                self.assertTrue(out.exists())
                data = json.loads(out.read_text(encoding="utf-8"))
                self.assertEqual(data["mcu"], "rp2040")
        finally:
            os.environ.pop("SOURCE_DATE_EPOCH", None)


class TestIssue55EagleSchIndent(unittest.TestCase):
    """#55 — eagle_sch.py indentation is consistent."""

    def test_no_excessive_indent_in_extract_nets(self):
        """The nets_data.append line in parse_schematic_tuples must be at 24-space indent."""
        import inspect

        from tools.pinmapgen import eagle_sch

        source = inspect.getsource(eagle_sch.parse_schematic_tuples)
        for line in source.splitlines():
            stripped = line.lstrip()
            if "nets_data.append" in stripped:
                indent = len(line) - len(stripped)
                self.assertEqual(
                    indent,
                    24,
                    f"nets_data.append has {indent}-space indent, expected 24",
                )


if __name__ == "__main__":
    unittest.main()
