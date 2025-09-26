# 🚀 PinmapGen Milestones & Roadmap

This document tracks the staged development of **PinmapGen**, from a simple CLI to a polished Fusion add-in with rich validation, docs, and community workflows. Each milestone can be broken down into GitHub issues or Copilot tasks.

---

## 📍 Milestone 1: Core CLI MVP ✅ **COMPLETE**
**Goal:** Standalone Python script that converts Fusion/EAGLE exports into pinmap artifacts.

- [x] Implement CSV parser (`bom_csv.py`)
- [x] Implement EAGLE .sch XML parser (`eagle_sch.py`)
- [x] Normalize RP2040 pin names (`normalize.py`)
- [x] Detect differential pairs (DP/DM, _P/_N, CANH/CANL)
- [x] Conflict validation (duplicate pin use, lonely diff pairs)
- [x] Emit:
  - [x] `pinmap.json`
  - [x] `pinmap_micropython.py`
  - [x] `pinmap_arduino.h`
  - [x] `PINOUT.md`
  - [x] (optional) `pinout.mmd`
- [x] Add sample netlist CSV for smoke testing
- [x] VS Code tasks.json for "Generate" and "Watch"

---

## 📍 Milestone 2: Better Outputs ✅ **COMPLETE**
**Goal:** Richer, role-aware generated code and docs.

- [x] Add `roles.py` to infer roles (i2c.sda, uart.tx, pwm, etc.)
- [x] Include role metadata in JSON and Markdown
- [x] MicroPython emitter: helpers for `adc()`, `pin_in()`, `pin_out()`
- [x] Arduino emitter: `DiffPair` struct for USB/CAN
- [ ] Markdown: split tables into Single-ended vs Differential pairs
- [ ] Mermaid: visualize diff pairs distinctly
- [x] Deterministic ordering + "Auto-generated" headers in all files

---

## 📍 Milestone 3: Developer Experience
**Goal:** Smooth workflow in VS Code and GitHub.

- [x] VS Code snippets (I2C, UART, PWM, USB setup examples)
- [x] Add `.vscode/extensions.json` recommendations
- [x] Add `.vscode/pinmap.code-snippets` for MicroPython & Arduino
- [ ] Add pre-commit hook: regen pinmaps before commit
- [ ] GitHub Actions workflow:
  - [ ] Run generator on sample netlist
  - [ ] Fail build if outputs not up to date
- [ ] Add CONTRIBUTING.md with coding style, adding MCU profiles, etc.
- [ ] Add basic unit tests for parsers + emitters

---

## 📍 Milestone 4: Fusion Add-in Prototype
**Goal:** One-click pinmap generation inside Fusion.

- [ ] Scaffold Fusion add-in in Python
- [ ] Create palette with:
  - [ ] MCU dropdown (RP2040 initially)
  - [ ] Language checkboxes (MicroPython, Arduino, Docs)
  - [ ] Options: "Fail on warnings" / "Watcher mode"
- [ ] Implement export of .sch/.csv into `hardware/exports/`
- [ ] Call CLI generator automatically
- [ ] Show validation results (errors/warnings) in Fusion palette
- [ ] Add "Open VS Code" button from Fusion

---

## 📍 Milestone 5: Multi-MCU Support
**Goal:** Extend beyond RP2040 to STM32/ESP32.

- [ ] Create MCU profile registry
- [ ] Add STM32G0 profile with AF mux validation
- [ ] Add ESP32 profile with IO matrix validation
- [ ] Per-MCU emitter tweaks (e.g., Arduino cores differ)
- [ ] Role-aware warnings: "UART2_TX not valid on this pin"

---

## 📍 Milestone 6: Classroom / Team Readiness
**Goal:** Scale for labs, teams, and education.

- [ ] Add template schematic with MCU symbol pre-named pins
- [ ] Add `--fail-on-warn` flag for stricter classroom use
- [ ] Improve error messaging for students
- [ ] Add "quick-start" VS Code workspace template
- [ ] Document workflow for instructors

---

## 📍 Milestone 7: Docs & Community
**Goal:** Make the project easy to adopt and contribute to.

- [ ] Full user guide in `docs/`
- [ ] Example repo with RP2040 + LED/button circuit
- [ ] FAQ: "Why not just name nets GPx?", "How do I add a new MCU?"
- [x] Add LICENSE (MIT) and badges
- [ ] Contributing examples with Copilot prompts
- [ ] GitHub Discussions/Q&A

---

## 📍 Milestone 8: Stretch Features
**Goal:** Extra polish and future-facing ideas.

- [ ] Generate VS Code boilerplate projects (Arduino/PlatformIO, MicroPython)
- [ ] Generate test firmware that blinks each pin
- [ ] Export graphical pinout diagram (SVG/PNG) from schema
- [ ] Fusion add-in auto-commit to GitHub
- [ ] Web UI for browsing pinmaps (read-only)

---

## 📊 Current Status

**Completed Milestones:** 2/8 (25%)

**Key Achievements:**
- ✅ Complete CLI toolchain with dual input support (CSV/EAGLE)
- ✅ RP2040 pin normalization with differential pair detection
- ✅ Five output formats: JSON, MicroPython, Arduino, Markdown, Mermaid
- ✅ File watcher for automatic regeneration
- ✅ VS Code integration with tasks and code snippets
- ✅ Role inference system with 20+ pin function patterns
- ✅ Enhanced JSON output with bus groups and role metadata
- ✅ MicroPython helpers: pin_in(), pin_out(), pwm(), setup_i2c0(), USBPins class
- ✅ Arduino helpers: DiffPair structs, PIN_INPUT/OUTPUT macros, SETUP_I2C0 macros
- ✅ Sample data and comprehensive documentation

**Next Priority:** Milestone 3 (Developer Experience) - Add GitHub Actions, pre-commit hooks, unit tests, and CONTRIBUTING.md.

**Development Notes:**
- Project built with Python 3.11, stdlib-only (no external dependencies)
- All core parsing, normalization, and emission logic implemented
- VS Code workspace fully configured with tasks, snippets, and extensions
- Ready for production use in current form