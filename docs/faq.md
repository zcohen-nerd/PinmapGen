# FAQ

Frequently asked questions about PinmapGen.

---

## General

### What does PinmapGen do?

It reads netlist data exported from Fusion 360 Electronics (or EAGLE) and
generates firmware-ready pin definitions for MicroPython, Arduino, JSON,
Markdown, and Mermaid. MCU profiles normalize pin names and flag common design
issues.

### Which MCUs are supported?

RP2040, STM32G0 (STM32G071), and ESP32 (ESP32-WROOM-32). Adding a new MCU
means subclassing `MCUProfile` and registering it in the CLI. See
[extending.md](extending.md).

### Does it need internet access?

No. PinmapGen is stdlib-only and runs entirely offline.

### Can I use it commercially?

Non-commercial use is free. Commercial use requires a license. See the
[LICENSE](../LICENSE) file.

---

## Workflow

### ULP or CLI — which should I use?

- **ULP**: Best for designers who work inside Fusion and want one-click
  generation without touching the command line.
- **CLI**: Best for firmware engineers, CI pipelines, and anyone who already
  has a terminal-based workflow.

Both produce the same output.

### How do I update pin assignments after a schematic change?

Re-export the CSV (or rerun the ULP) and regenerate. The output files are
overwritten in place — there's no merge step. If you use the file watcher
(`tools.pinmapgen.watch`), regeneration happens automatically when the CSV
changes.

### Can I generate for more than one MCU from the same schematic?

Yes. Run the CLI once per MCU reference designator:

```bash
python -m tools.pinmapgen.cli --csv netlist.csv --mcu rp2040 --mcu-ref U1 --out-root out/rp2040
python -m tools.pinmapgen.cli --csv netlist.csv --mcu esp32  --mcu-ref U2 --out-root out/esp32
```

### What CSV columns does the parser expect?

`Net`, `Pin`, `Component`, `RefDes`. Column order doesn't matter (parsed with
`csv.DictReader`). Extra columns are ignored.

### Can I use KiCad / Altium / other CAD tool exports?

Not directly. If you can produce a CSV with the four required columns, the CLI
will accept it. Native KiCad `.net` or Altium NetList support would require a
new parser module.

---

## Technical details

### What is the "canonical dict"?

The single data structure that all emitters consume. It looks like:

```python
{
    "mcu": "rp2040",
    "pins": { "I2C0_SDA": ["GP0"], ... },
    "differential_pairs": [ {"positive": "USB_DP", "negative": "USB_DM"} ],
    "metadata": { "total_nets": 12, "total_pins": 18, ... }
}
```

Parsers produce raw net data; `MCUProfile.create_canonical_pinmap()` normalizes
it into this shape; emitters read from it.

### How does role inference work?

`roles.py` matches net names against regex patterns. For example, a net named
`I2C0_SDA` is assigned the `I2C_SDA` role, which affects how it appears in
documentation and whether the emitter generates helper code.

### Are the outputs deterministic?

Mostly. Pin ordering and content are deterministic for a given input. However,
timestamps in file headers change on each run, so byte-for-byte reproducibility
requires stripping or fixing the timestamp.

### How does validation work?

Each MCU profile defines pin capabilities (GPIO, ADC, PWM, etc.) and
constraints (input-only, strapping, boot). During `create_canonical_pinmap()`,
the profile checks every net assignment against these rules and emits warnings.
Warnings appear in CLI output and in the `metadata.validation_warnings` field
of `pinmap.json`.

### Why are there two RP2040 profiles?

`normalize.py` contains a legacy `RP2040Profile` from before the `MCUProfile`
ABC was introduced. The CLI uses the profile from `rp2040_profile.py`. The
legacy copy is kept for backward compatibility but should not be used for new
work.

---

## Classroom and education

### How can I use PinmapGen in a lab setting?

1. Prepare template CSVs for each lab exercise.
2. Students modify pin assignments and run the CLI (or ULP).
3. Validation warnings give immediate feedback on design issues.
4. Generated `PINOUT.md` serves as a starting point for lab reports.

### What can I assess with PinmapGen outputs?

- Semantic net naming (descriptive names vs generic `GP0`, `NET1`)
- Appropriate pin selection (ADC-capable pins for analog, PWM for LEDs)
- Differential pair handling
- Documentation completeness

---

## Integration and automation

### How do I integrate with CI/CD?

Example GitHub Actions snippet:

```yaml
- name: Regenerate pinmaps
  run: python -m tools.pinmapgen.cli --csv hardware/exports/sample_netlist.csv --mcu rp2040 --mcu-ref U1 --out-root .
- name: Fail if outputs drifted
  run: git diff --exit-code pinmaps/ firmware/
```

### Can I customize the output formats?

Modify the emitter modules in `tools/pinmapgen/emit_*.py`. Each emitter is a
standalone function that accepts the canonical dict and an output path. You can
also create new emitters following the same pattern. See [extending.md](extending.md).

### How do I add support for a custom MCU?

1. Subclass `MCUProfile` in a new `tools/pinmapgen/<mcu>_profile.py`.
2. Implement pin definitions, normalization, and peripheral metadata.
3. Register in `cli.py` → `MCU_PROFILES`.
4. Add tests and a sample netlist.

Detailed walkthrough: [extending.md](extending.md).

---

## Troubleshooting

### Where can I get help?

- [Troubleshooting guide](troubleshooting.md)
- [GitHub Issues](https://github.com/zcohen-nerd/PinmapGen/issues)
- Sample projects in `examples/` for reference

### What should I include in a bug report?

1. Full CLI command
2. Complete traceback
3. Minimal CSV that reproduces the problem
4. OS and Python version
5. Expected vs actual behavior
