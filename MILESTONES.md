# 🚀 PinmapGen Milestones & Roadmap

This document tracks the staged development of **PinmapGen**, from a simple CLI to a polished Fusion add-in with rich validation, docs, and community workflows. Each milestone can be broken down into GitHub issues or Copilot tasks.

---

## 📍 Milestone 1: Core CLI MVP ✅ **COMPLETE**
**Goal:** Standalone Python script that converts Fusion/EAGLE exports into pinmap artifacts.

**Status:** Complete. The CLI path from CAD exports to firmware artifacts is stable and covered by unit tests.

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
- [x] Markdown: split tables into Single-ended vs Differential pairs
- [x] Mermaid: visualize diff pairs distinctly
- [x] Deterministic ordering + "Auto-generated" headers in all files

**Status:** Complete. Markdown and Mermaid outputs now surface differential information clearly and include metadata for downstream tooling.

---

## 📍 Milestone 3: Developer Experience ✅ **COMPLETE**
**Goal:** Smooth workflow in VS Code and GitHub.

- [x] VS Code snippets (I2C, UART, PWM, USB setup examples)
- [x] Add `.vscode/extensions.json` recommendations
- [x] Add `.vscode/pinmap.code-snippets` for MicroPython & Arduino
- [x] Add pre-commit hook: regen pinmaps before commit
- [x] GitHub Actions workflow:
  - [x] Run generator on sample netlist
  - [x] Fail build if outputs not up to date
- [x] Add CONTRIBUTING.md with coding style, adding MCU profiles, etc.
- [x] Add basic unit tests for parsers + emitters

**Status:** Complete. Hooks, CI, tasks, and tests keep generated artifacts synchronized across contributors.

---

## 📍 Milestone 4: Fusion Add-in Prototype ✅ **COMPLETE**
**Goal:** One-click pinmap generation inside Fusion.

- [x] Scaffold Fusion add-in in Python
- [x] Create palette with:
  - [x] MCU dropdown (RP2040, STM32G0, ESP32)
  - [x] Language checkboxes (MicroPython, Arduino, Docs, Mermaid)
  - [x] Smart defaults and user-friendly interface
- [x] Implement direct Fusion Electronics data extraction (no manual exports)
- [x] Call PinmapGen toolchain automatically with seamless integration
- [x] Show validation results with plain-English error messages
- [x] Add comprehensive error handling and recovery options
- [x] Create installation system and user documentation

**Status:** Complete. The add-in mirrors CLI outputs, installs via helper scripts, and surfaces validation guidance in Fusion.

---

## 📍 Milestone 5: Multi-MCU Support ✅ **COMPLETE**
**Goal:** Extend beyond RP2040 to STM32/ESP32.

- [x] Create MCU profile registry
- [x] Add STM32G0 profile with AF mux validation
- [x] Add ESP32 profile with IO matrix validation
- [x] Per-MCU emitter tweaks (e.g., Arduino cores differ)
- [x] Role-aware warnings: "UART2_TX not valid on this pin"

**Status:** Complete. Profiles now emit targeted warnings for strapping pins, USB lanes, ADC exclusivity, and more.

---

## 📍 Milestone 6: Classroom / Team Readiness ✅ **COMPLETE**
**Goal:** Scale for labs, teams, and education.

**Status:** Complete. Comprehensive documentation suite created covering all classroom and team needs.

- [x] Add template schematic with MCU symbol pre-named pins (`docs/templates/`)
- [x] Add `--fail-on-warn` flag for stricter classroom use  
- [x] Improve error messaging for students (plain-language CLI and add-in guidance)
- [x] Publish "quick-start" VS Code workspace template for labs
- [x] Document instructor & TA workflow (`docs/workflows.md`)
- [x] Provide printable lab handout summarizing RP2040 wiring checks

**Delivered:** Complete documentation ecosystem including troubleshooting guides, FAQ, workflow documentation, and comprehensive USER_GUIDE.md with education-focused content.

---

## 📍 Milestone 7: Docs & Community ✅ **COMPLETE** 
**Goal:** Make the project easy to adopt and contribute to.

**Status:** Complete. Full documentation ecosystem established with comprehensive guides and community resources.

- [x] Publish top-level `USER_GUIDE.md`
- [x] Seed `docs/` with:
  - [x] `docs/troubleshooting.md`
  - [x] `docs/faq.md`
  - [x] `docs/output-formats.md`
  - [x] `docs/workflows.md`
  - [x] `docs/extending.md`
  - [x] `docs/api-reference.md`
  - [x] `docs/CONTRIBUTING.md`
- [x] Example repo structure with `examples/README.md`
- [x] Add LICENSE (MIT) and badges
- [x] Contributing examples with Copilot prompts
- [x] Community documentation framework

**Delivered:** Comprehensive 13-section USER_GUIDE.md, complete docs/ directory structure, API reference, contributing guidelines, and community-ready documentation framework.

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

**Completed Milestones:** 7/8 (87.5%)

**Key Achievements:**
- ✅ CLI + Fusion add-in parity producing JSON, MicroPython, Arduino, Markdown, and Mermaid outputs
- ✅ Multi-MCU profiles (RP2040, STM32G0, ESP32) with role-aware validation warnings and pin metadata
- ✅ Automation guardrails: file watcher, VS Code tasks, pre-commit hook, and GitHub Actions regeneration checks
- ✅ Refreshed README plus CONTRIBUTING guide, unit tests, and sample data for rapid onboarding
- ✅ Fusion 360 add-in with installer scripts, smart defaults, and plain-language validation surfaced in-app
- ✅ **Complete documentation ecosystem:** 13-section USER_GUIDE.md, docs/ directory with 7 guides, API reference, troubleshooting, and community resources
- ✅ **Classroom-ready package:** Education workflows, template structures, examples framework, and instructor documentation
- ✅ **Test suite stability:** All 30 tests passing, lint issues reduced from 3000+ to 626, API consistency validated

**Next Priority:** Milestone 8 (Advanced Validation & Polish) — complete final robustness features and prepare for broad community adoption.

**Development Notes:**
- Project built with Python 3.11, stdlib-only (no external dependencies)
- All core parsing, normalization, and emission logic implemented
- VS Code workspace fully configured with tasks, snippets, and extensions
- Ready for production use in current form; documentation polish in progress