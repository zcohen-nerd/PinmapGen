# PinmapGen Milestones & Roadmap

Staged development history. Milestones 1–10 are complete; stretch goals are
listed at the end.

---

## Milestone 1: Core CLI MVP — Complete

Standalone Python script that converts Fusion/EAGLE exports into pinmap
artifacts.

- CSV parser (`bom_csv.py`)
- EAGLE `.sch` XML parser (`eagle_sch.py`)
- RP2040 pin normalization (`normalize.py`)
- Differential pair detection (DP/DM, `_P`/`_N`, CANH/CANL)
- Conflict validation (duplicate pin use, lonely diff pairs)
- Emitters: `pinmap.json`, `pinmap_micropython.py`, `pinmap_arduino.h`,
  `PINOUT.md`, `pinout.mmd`
- Sample netlist CSV for smoke testing
- VS Code tasks for generate and watch

---

## Milestone 2: Better Outputs — Complete

Role-aware generated code and documentation.

- `roles.py` for role inference (I2C SDA, UART TX, PWM, etc.)
- Role metadata in JSON and Markdown
- MicroPython helpers (`adc()`, `pin_in()`, `pin_out()`)
- Arduino `DiffPair` struct for USB/CAN
- Markdown: separate tables for single-ended vs differential pairs
- Mermaid: differential pairs rendered distinctly
- Deterministic ordering and auto-generated headers in all files

---

## Milestone 3: Developer Experience — Complete

Smooth workflow in VS Code and GitHub.

- VS Code snippets (I2C, UART, PWM, USB setup examples)
- `.vscode/extensions.json` recommendations
- `.vscode/pinmap.code-snippets` for MicroPython & Arduino
- Pre-commit hook to regenerate pinmaps before commit
- GitHub Actions workflow: run generator on sample netlist, fail if outputs
  drift
- `CONTRIBUTING.md` with coding style and MCU profile guide
- Unit tests for parsers and emitters

---

## Milestone 4: Fusion ULP Prototype — Complete

One-click pinmap generation inside Fusion.

- ULP scaffold with palette UI
- MCU dropdown, language checkboxes, smart defaults
- Direct schematic data extraction via ULP object model (no manual export)
- CLI invocation from within the ULP
- Validation results with plain-English error messages
- Installation helper and user documentation

---

## Milestone 5: Multi-MCU Support — Complete

Extend beyond RP2040 to STM32 and ESP32.

- MCU profile registry
- STM32G0 profile with alternate-function mux validation
- ESP32 profile with IO matrix and strapping pin validation
- Per-MCU emitter tweaks
- Role-aware warnings (e.g., "UART2_TX not valid on this pin")

---

## Milestone 6: Classroom / Team Readiness — Complete

Scale for labs, teams, and education.

- Template schematic with pre-named MCU pins
- `--fail-on-warn` flag for stricter classroom use
- Plain-language error messaging for students
- VS Code workspace template for labs
- Instructor/TA workflow docs (`docs/workflows.md`)
- Printable RP2040 wiring-check handout

---

## Milestone 7: Docs & Community — Complete

Make the project easy to adopt and contribute to.

- `USER_GUIDE.md` (13 sections)
- `docs/`: troubleshooting, FAQ, output-formats, workflows, extending
- `examples/README.md` and three worked examples
- License, badges, contributing guide
- Community documentation framework

---

## Milestone 8: ULP Enhancement & Real Integration — Complete

Production ULP with advanced UI and validation.

**Phase 1 — Core:** Working ULP, clean dialog, netlist export from live
schematic, error handling, input validation.

**Phase 2 — UI:** MCU profile buttons, output format checkboxes, quick-path
buttons, project name with auto-timestamp, settings persistence, preview mode.

**Phase 3 — Quality:** Pin conflict detection in the dialog, schematic analysis
with component/net validation, MCU reference validation, project-organized
output, real-time validation before generation.

**Phase 4 — Future (not started):** VS Code integration, notification system,
doc-site auto-generation, GitHub Actions trigger, diff view, undo/rollback.

---

## Milestone 9: Full Automation (ULP Breakthrough) — Complete

Eliminated the manual netlist export step.

**Problem:** ULP could not invoke `EXPORT NETLIST` programmatically.

**Solution:** The ULP traverses the schematic object model directly
(`schematic → sheets → nets → segments → pinrefs → pin → contacts`),
generates a CSV internally, and feeds it to the CLI.

Result: schematic-to-firmware-files in one click, tested with real schematics
(17 nets, multiple MCUs, power rails).

---

## Milestone 10: UI Polish & Messaging — Complete

Calmed down ULP messaging, confirmed production readiness, resolved remaining
ULP syntax issues.

---

## Current status

All 10 milestones complete. 30 tests passing. Python 3.11+, stdlib-only.

---

## Stretch goals (not started)

- Generate VS Code boilerplate projects (Arduino/PlatformIO, MicroPython)
- Generate test firmware that blinks each pin
- Export graphical pinout diagram (SVG/PNG) from schematic
- Web UI for browsing pinmaps (read-only)
- Mobile app for quick pinout reference
- AI-powered pin assignment suggestions
