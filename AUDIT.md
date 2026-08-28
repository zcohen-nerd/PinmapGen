# PinmapGen usability audit

**Date:** 2026-08-28 · **Scope:** full repository (`main` @ c39bf23) · **Method:** hands-on CLI runs (happy paths, malformed inputs, packaging), line-level review of both ULPs against the EAGLE/Fusion ULP language reference, execution of the parser/emitter code paths, and cross-checking every user-facing document against the code. All findings below were verified against source or reproduced; file:line references included.

PinmapGen has three audiences: **Fusion 360 designers** (non-programmers using the ULP — the README's primary audience), **CLI users** (including the Mac/Linux users the README points at the terminal), and **contributors**. Ranking:

- **P0** — the core promise fails or lies: wrong/empty output presented as success, or a hard failure on a documented path.
- **P1** — a whole audience hits a broken promise; workarounds exist but trust is damaged.
- **P2** — real friction on common paths: unhelpful errors, silent surprises, docs contradicting code.
- **P3** — papercuts, polish, hygiene.

---

## P0 — Core promise broken

### P0.1 The Fusion ULP can generate confidently *wrong* pinmaps (physical pad numbers read as GPIO numbers)

> **Status: FIXED.** The ULP now exports the symbol pin name in the Pin column (the physical pad moves to an extra `Pad` column the parser ignores), and the CLI prints one summary warning whenever bare numbers are interpreted as GPIO numbers — counted in the status line and shown by the ULP's issues dialog. Example netlists were converted to explicit `GP*` names; docs state the Pin-column contract.

The ULP exports each pin as the **physical package pad name** whenever the part has a package: `fusion_addin/PinmapGen.ulp:258-264` sets `pinNum = PR.pin.name`, then overwrites it with `C.name` from `PR.pin.contacts(C)`. `SUCCESS_DOCUMENTATION.md:14-33` confirms this is the intended design ("pinrefs → pin → contacts").

On the Python side, `rp2040`, `rp2350`, `esp32`, `esp32s3`, `esp32c3` set `allow_numeric = true` (`profiles/rp2040.toml:15`), so a bare `"2"` silently becomes `GP2`/`GPIO2`. Physical pad 2 of an RP2040 QFN-56 is **GPIO0**, not GP2. For the flagship Fusion → Pico workflow, the generated header compiles, looks plausible, and drives the wrong pins — with zero warnings (reproduced: `Pin,2` → `LED_STATUS = 2  # (GP2)`, no diagnostic).

For the other eight profiles (`allow_numeric = false`), the same input makes every pin fail normalization: pins are dropped with stderr warnings the ULP user never sees, the CLI exits 0, and the ULP reports success (P0.2). Either way the user is told it worked.

**Fix:** prefer the symbol pin name in the ULP (or emit both columns); on the Python side print a prominent notice whenever `allow_numeric` interprets bare integers, and consider `--pin-namespace {gpio,pad}` with per-package pad→GPIO tables.

### P0.2 The advertised design checks are invisible — and failures say "Success"

> **Status: FIXED.** Warnings now print to stderr (deduplicated) and count into an honest final status line; a new `--log-file` option mirrors all console output for GUI front ends; both ULPs run with `-NoProfile`/`exit $LASTEXITCODE`, read the log back, and show a clean-success / generated-with-issues / failure-with-real-error / Python-never-started dialog accordingly.

`README.md:24-27` leads with "It also **checks your design** … warns you if two signals share a pin, if you used a special pin (like a boot or debug pin) by accident". Four stacked defects make this promise false in practice:

1. **Special-pin warnings are never printed at all.** `create_canonical_pinmap` collects per-pin profile warnings into `metadata.validation_warnings` (`mcu_profiles.py:326-331`) but only ever prints `validation_errors` (`:346-349`). Verified: nets on ESP32 GPIO0 (boot strap) or RP2040 GP24/25 produce **no console output whatsoever**, with or without `--verbose`, and `--strict` ignores them (`cli.py:426-427`). Every `warnings = [...]` array lovingly authored across the 13 TOML profiles is dead code at the console; the only trace is buried in `pinmap.json` metadata and a PINOUT.md section.
2. **Validation *errors* don't fail the run.** Two nets on one pin prints `Validation error: Pin GP5 used by multiple nets` to stderr, then `Pinmap files generated successfully`, exit 0 (reproduced). Only opt-in `--strict` changes this.
3. **The ULP never passes `--strict` and discards all CLI output.** `PinmapGen.ulp:409-418` runs PowerShell with no output capture and no log; the console flashes and closes; `--verbose` is appended to a stream nobody can see. On exit 0 the user gets "Pinmap Generation Complete!" (`:420-432`) — including for a run where *every* pin was dropped and `pinmap.json` contains zero pins (reproduced with wrong `--mcu`: empty outputs, success message). `powershell -Command` also doesn't reliably propagate exit codes without `; exit $LASTEXITCODE`, and there is no `-NoProfile`.
4. **On failure, the real error is never shown.** The ULP's error dialog (`:436-444`) is four static guesses; the actual Python message was never captured.

**Fix:** print `validation_warnings` to stderr; make the final status line honest ("generated with N errors, M warnings, K dropped pins"); in the ULP, redirect output to a log file in the output folder, append `; exit $LASTEXITCODE`, pass `--strict` or parse the log, and show it in a `dlgTextView`.

### P0.3 `pip install -e .` fails outright — and it's both the documented setup and the documented fix

Reproduced: `error: Multiple top-level packages discovered in a flat-layout: ['hardware', 'fusion_addin']`. Causes:

- `pyproject.toml` has no `[tool.setuptools]`/`packages` config, so setuptools auto-discovers — and its flat-layout finder **excludes a directory named `tools/`** while treating `hardware/` and `fusion_addin/` as namespace packages and refusing to build.
- Even if fixed, the `pinmapgen = "tools.pinmapgen.cli:main"` console script (`pyproject.toml:21-22`) points into a package auto-discovery would never include; no doc ever shows the `pinmapgen` command.
- No `package-data`/`MANIFEST.in`, so the 13 profile TOMLs (loaded from `Path(__file__).parent / "profiles"`, `profile_registry.py:63`) wouldn't ship in a wheel — an installed copy would say "No MCU profiles found."

Seven places instruct the broken command: `CONTRIBUTING.md:20` (contributor quick-start), `USER_GUIDE.md:81`, `docs/troubleshooting.md:25,36` — where it is offered as **the fix** for `No module named 'tools'`, the most common CLI mistake (running from any directory but the repo root; reproduced) — `docs/usage.md:201`, `docs/workflows.md:210` (copy-paste CI recipes), and `.github/workflows/release.yml:140` (the published release notes). The repo's own CI never runs it, which is why it went unnoticed.

**Fix (minimal):** `[tool.setuptools] packages = ["tools", "tools.pinmapgen"]` + `[tool.setuptools.package-data] "tools.pinmapgen" = ["profiles/*.toml"]`. **Fix (right):** rename the package to `pinmapgen/` so users aren't installing a global top-level package named `tools`, keep a shim, update docs — or delete `[project.scripts]` and every `pip install -e .` instruction and standardize on "run from the repo root".

---

## P1 — A whole audience hits a broken promise

### P1.1 The RP2040 profile's USB pin data is factually wrong (and other profile-data errors)

> **Status: FIXED.** rp2040.toml now matches rp2350's treatment: USB aliases, GP24/GP25 USB labels, and the USB peripheral are gone (USB names drop with a visible warning; GP23–25 are plain chip GPIOs with Pico-board notes in comments). stm32g0.toml loses its phantom CAN peripheral/capabilities and its description now names the LQFP-64 part its pin list describes. esp32.toml labels GPIO34/35 input-only and warns on GPIO37/38 (not bonded on WROOM-32). Sample netlist/schematic now demo an RS485 pair instead of USB-on-GPIO; tests updated to encode the corrected data.

`profiles/rp2040.toml:26-31` aliases `USB_DP → GP25`, `USB_DM → GP24`, and `:56-70` labels GP24/GP25 as "USB D-/D+". On the RP2040 die, USB D+/D− are **dedicated pins (QFN-56 pins 47/46), not GPIO-muxed**; on a Pico, **GP25 is the on-board LED and GP24 is VBUS sense**. Reproduced: a `USB_DP` net emits `USB_DP = 25` — firmware "driving USB" toggles the LED. The sibling `rp2350.toml:106-107` models this correctly ("dedicated, not GPIO-muxed … not in pin groups"), making the rp2040 entry a plain bug. Also in this class: `stm32g0.toml` declares a CAN peripheral (PB8/PB9) on an STM32G071, which **has no FDCAN**, and its pin list includes LQFP-64-only pins while the description says LQFP-48; `esp32.toml` declares GPIO37/38, which aren't bonded out on the WROOM-32 module it names. Wrong reference data is worse than no data — this tool's whole pitch is "no more pin-mapping mistakes."

### P1.2 CI never runs the test suite (307 tests behind a green badge)

Neither workflow contains any pytest/unittest step — `build-test.yml` does imports, `--help`, one generation, file-existence checks, and a watcher smoke test. Yet `README.md:5` shows a CI badge, `CONTRIBUTING.md:191` says CI ensures "tests pass", and `copilot-instructions.md:128` claims it. All 307 tests pass locally in ~2 s with zero dependencies (`python -m unittest discover -s tests`). **Fix:** one CI step.

### P1.3 Contributor setup instructions fail twice

`CONTRIBUTING.md` step 2 (`pip install -e .`) fails per P0.3; step 3 (`python -m pytest tests/ -v`) fails because pytest is never installed nor declared anywhere (no `[project.optional-dependencies]`, no requirements file; verified `No module named pytest`). The working command appears only in `tests/README.md:19`. Same broken pytest instruction in `README.md:238`.

### P1.4 CSV parsing is brittle and its errors don't help

The #1 first-run surface for CLI users, all reproduced:

- **Any ragged row** (trailing comma, unquoted `10k, 1%`) crashes with `Error: 'list' object has no attribute 'strip'` — `bom_csv.py:70` calls `.strip()` on the list `csv.DictReader` stores under the `None` key. No filename, no line number.
- **Headers are case- and whitespace-sensitive** with no delimiter sniffing: `net,pin,…`, `Net ; Pin ;…`, and semicolon-delimited (European Excel) all die with `CSV missing required columns: {'RefDes', 'Pin', 'Component', 'Net'}` — a Python set in random order that never shows what **was** found, even though `reader.fieldnames` is right there. No alias table (`Designator`→`RefDes`), though `docs/troubleshooting.md:62-63` admits Fusion uses different names.
- **The `Component` column is required but never used** (`bom_csv.py:51` vs `:161-175`) — rows with it empty are skipped (data loss with a warning), files without it are rejected.
- **Wrong `--mcu-ref`** yields `No entries found for MCU reference 'U9'` without listing the RefDes values that exist in the file — the one hint that would fix it.
- (Good news: Excel's UTF-8 BOM and CRLF are handled correctly.)

### P1.5 Generated code breaks on the most natural net names

- **Arduino:** nets named `MOSI`, `MISO`, `SCK`, `SDA`, `SCL`, `SS`, `A0`-`A7`, `LED_BUILTIN` become `#define MOSI 4` etc. — emitted **before** the header's own `#include <SPI.h>`/`<Wire.h>` (`emit_arduino.py:293`, `:411,467`), textually rewriting the core's `pins_arduino.h` declarations. Reproduced: `#define MOSI 4` … `#include <SPI.h>` in one header — this does not compile on standard cores, and these are *the* conventional SPI net names.
- **MicroPython:** nets named `SPI`, `PWM`, `I2C`, `ADC` rebind the classes imported at the top of the generated module (`emit_micropython.py:180`, `:273`), so the bundled helpers crash at call time (`TypeError: 'int' object is not callable`).
- `naming.py` has no reserved-identifier list; the fix is a small per-emitter blacklist with suffixing.

### P1.6 The ULP's quick-select buttons don't visibly work (missing `dlgRedisplay()`)

Every quick button mutates a variable bound to a text field — MCU type (`PinmapGen.ulp:313-329`), project name (`:302-304`), output dir (`:348-350`) — but the file contains zero `dlgRedisplay()` calls, which EAGLE dialogs require to refresh widgets after programmatic changes. The user clicks **ESP32**, the field still shows `rp2040`; they either conclude the tool is broken or can't tell which value will be used. This is the README's step 3: "click the button for your chip" (`README.md:98`). One line per handler fixes it.

### P1.7 The ULP is Windows-only in ways the docs half-deny, with fragile shell plumbing

`powershell -Command`, `mkdir … 2>nul`, `del … 2>nul`, `explorer` (`PinmapGen.ulp:401,409,430,433`) are Windows/cmd constructs, yet `FUSION_TEST_GUIDE.md:20-22` documents a macOS install path (Fusion/Mac runs ULPs; this one just dies unexplained at generation). `mkdir`/`del` are **cmd.exe built-ins invoked without a shell** (EAGLE's `system()` needs `cmd.exe /c` for built-ins and `2>nul` redirection), with return values discarded — and if the mkdir fails, the ULP's `output()` netlist write dies with a raw EAGLE file error before any friendly handler runs. `explorer` gets forward-slash paths, which Explorer rejects (opens the wrong folder right after the success dialog names the right one). The ULP also hardcodes `python` (`:409`): on Windows the Microsoft-Store alias exists even with no Python installed, and the `py` launcher — present even when "Add to PATH" was left unticked, the exact failure `README.md:176` documents — is never tried; no version pre-flight (3.9 dies on `X | Y` syntax invisibly per P0.2).

### P1.8 There is no working path to the required CSV without the ULP

The CLI needs columns `Net,Pin,Component,RefDes`; no CAD tool exports that natively, and the docs' pointers are wrong or vague: `USER_GUIDE.md:187` cites a menu ("Design Workspace → Output → Netlist (CSV)") that doesn't produce this format, `docs/troubleshooting.md:63` hand-waves "adjust the export settings", and the manual ULP's fallback dialog (`PinmapGen_Manual.ulp:243-253`) never states the required columns. The README promises Mac/Linux users the CLI "works there too" (`README.md:47`) — but on those platforms there's no ULP and hence no documented way to obtain input. **Fix:** ship a tiny export-only ULP, document a real recipe, and/or accept native Fusion/KiCad netlist formats.

---

## P2 — Significant friction and contradictions

**P2.1 Contradictory status messaging and warning/error taxonomy.** `Validation error: …` followed by `Pinmap files generated successfully` (exit 0). Docs then disagree with the code about severity: `USER_GUIDE.md:344-346` calls multi-pin nets "fine for power rails" and duplicate pins "warnings", but both live in `validation_errors` and fail `--strict` (`mcu_profiles.py:215-273`); `README.md:210` says `--strict` fails on "any pin conflict" when it also fails on any dropped pin.

**P2.2 `--strict` is unusable on realistic boards.** The lonely-differential-pair heuristic (`mcu_profiles.py:254-273`) flags every active-low net — `RESET_N`, `CS_N`, `INT_N`, `WP_N` all produce validation *errors* (verified), so a normal board fails `--strict` CI out of the box. The multi-pin whitelist (`:277-299`) allows `VCC`/`GND`/`3V3` but rejects `VIN`, `VBAT`, `VSYS` as "routing error". The README recommends `--strict` for CI; following that advice on a real design fails immediately for false-positive reasons.

**P2.3 Identifier sanitization can silently assign the wrong constant.** `naming.py:58-64` registers only pre-suffix names, so `LED-1` (sanitized first) **steals** `LED_1`, and the net literally named `LED_1` becomes `LED_1_2`; a third net can then collide into a duplicate `LED_1_2` (verified) — in MicroPython the later assignment silently wins. No rename is ever reported. PINOUT.md's examples use a collision-free sanitizer (`emit_markdown.py:331-340` admits it), so the doc can reference constants that don't exist in the code files.

**P2.4 Two differential-pair detectors disagree — five outputs, two answers.** `mcu_profiles.py:179-186` (feeds Markdown/Mermaid) misses `USB_D+`/`USB_D-` (the docstring's own example), bare `CANH`/`CANL`, and `CAN_H`/`CAN_L`; `roles.py:328-352` (feeds MicroPython/Arduino/JSON) catches them. Verified end-to-end: with `USB_D+`/`USB_D-`, the .py/.h/JSON show the pair while PINOUT.md says "Differential pairs: 0". The role-based one also pairs by list position (`zip(dp_pins, dn_pins)`), which can cross-pair two USB ports.

**P2.5 PINOUT.md's usage examples are dangerous or wrong.** `emit_markdown.py:129-146` takes the first three single-pin nets with no role filtering, generating `_3v3 = Pin(_3V3, Pin.OUT)` and `pinMode(_3V3, OUTPUT)` — copy-pasteable instructions to drive a power rail push-pull (verified). Power/ground nets are emitted as ordinary constants everywhere (`GND = 7  # General Purpose I/O`) because `PinRole.POWER/GROUND` exist but have no patterns (`roles.py:46-47` vs `:72-175`).

**P2.6 Role inference is confidently wrong in visible places.** Any net containing "light" is an LED (`roles.py:155-158`): the shipped `sensor_hub` example labels the light *sensor* `LIGHT_ANALOG = 26  # Light Emitting Diode`. UART patterns outrank LED, so `TX_LED` → "UART Transmit". And PINOUT.md's Function column comes from separate ad-hoc keyword code (`emit_markdown.py:355-373`), so the same net gets different descriptions in PINOUT.md vs the code files (committed examples show `LED_RED` as "General Purpose I/O" in one and "Light Emitting Diode" in the other).

**P2.7 Overpromised validation.** `USER_GUIDE.md:112-118` claims checks for input-only pads wired as outputs and ADC-role mismatches; `docs/troubleshooting.md:141-153` documents four warning messages; `SUCCESS_DOCUMENTATION.md:58-62` claims alternate-function and ADC2+WiFi checks. None exist: there is no direction model at all (`gpio.in`/`gpio.out` have no capability mapping, `mcu_profiles.py:141-160`; ESP32 GPIO34-39 driven as outputs produce zero warnings — verified), and rp2040 grants every pin every capability (`rp2040.toml:39-46`), so no role/pin mismatch can ever fire for the most-used profile.

**P2.8 The ULP's output-format checkboxes are decorative.** Only Mermaid maps to a flag; the MicroPython/Arduino/Documentation boxes change nothing but the preview and the success text (`PinmapGen.ulp:356-375, 422-426` vs `cli.py:262-283`, which always writes all four) — the success dialog then misreports what was written. No CLI flags exist to select outputs or flatten the fixed `pinmaps/` + `firmware/{...}` tree either.

**P2.9 The documented CI drift-check can never fail.** `docs/usage.md:203`, `docs/workflows.md:215`, `docs/faq.md:147-148` recommend `git diff --exit-code pinmaps/ firmware/` — paths that are **gitignored** (`.gitignore:27-31`), so the gate always passes. The repo's own workflow knows this and diffs `examples/` instead (`validate-pinmaps.yml:39-41`).

**P2.10 Troubleshooting doc states wrong facts.** `--no-mermaid` doesn't exist (`docs/troubleshooting.md:172`); "Case matters: `U1` ≠ `u1`" (`:55`) is false (matching is case-insensitive, `bom_csv.py:17-19` — CI even tests `u1`); the quoted warning strings (`:143-164`) match no actual program output, so searching the page for the message you saw finds nothing; `README.md:171`'s quoted error ("MCU 'U1' not found") likewise doesn't match the real message.

**P2.11 ULP settings and path handling have sharp edges.** No `dlgDirectory()`/file pickers — paths are typed into plain text fields; Explorer's "Copy as path" (quoted) fails validation; trailing spaces survive; mixed separators unhandled (`PinmapGen.ulp:205-207`). Settings save *before* validation (`:392` vs `:398`) and live in the AppData ULPs folder that `FUSION_TEST_GUIDE.md:236-241` itself warns is often unwritable — where a failed `output()` is a raw fatal error. The default output dir is that same hidden folder (`:12`); README calls it "a sensible default" (`README.md:104`). "Add Timestamp" appends repeatedly and persists the compounded name (`:302-304`,`:107`). The empty-output-dir check is dead code (`:192-194` tests a string that can no longer be empty after `:395`). Project names are never validated for `\/:*?"<>|`. The ULP's MCU check is case-sensitive though the CLI isn't, and its hardcoded 13-name list means custom `--profile-dir` TOMLs can't be used from Fusion at all.

**P2.12 Manual ULP is worse where it matters and undocumented.** `PinmapGen_Manual.ulp` deletes the user's hand-exported `live_netlist.csv` on success (`:234`) — the file they were just told to create — forcing a re-export every run, unwarned. It drops Analyze/Preview, doesn't persist checkbox settings (`:86-94` saves only 4 keys), uses a separate settings file (repo path must be re-entered), and `exit(1)`s on validation errors instead of returning to the dialog. `ULP_GUIDE.md` never mentions it.

**P2.13 ULP netlist CSV content bugs.** The `Component` column is filled with the RefDes (`PR.part.name` passed twice, `PinmapGen.ulp:266-270`) instead of a device name; embedded `"` in net names is never escaped (silent row corruption in Python's csv reader); and there's no pre-flight check that the entered MCU ref exists in the schematic — the Analyze code (`:169-173`) already knows how — so `U99` yields "Generation Complete!" with an empty pinmap.

---

## P3 — Papercuts and hygiene

- **P3.1 Dialog buttons carry titles as labels.** All ten `dlgMessageBox(msg, "Some Title")` calls make the single *button* read "CLI Error"/"Input Validation Failed" — the second argument is a button list in EAGLE ULP, not a window title (`PinmapGen.ulp:338,381,432,444,466,469`; `_Manual:197,236,239,243`).
- **P3.2 Root-directory clutter with stale internal docs.** `MILESTONES.md`, `PROJECT_COMPLETION.md`, `SUCCESS_DOCUMENTATION.md`, `FUSION_TEST_GUIDE.md` sit beside the README claiming 3 MCUs (there are 13), "30 tests" (there are 307), and phantom deliverables (`--fail-on-warn`, a VS Code workspace template, a printable handout). The issue template `documentation.md` offers `SUCCESS_DOCUMENTATION.md` as user docs while omitting the four real guides. Move to `docs/internal/` or delete.
- **P3.3 FAQ contradicts itself.** `docs/faq.md:16-21` says 3 MCUs and "subclass MCUProfile" while `:157-167` in the same file gives the correct TOML instructions; `:98-101` forgets `--reproducible` exists.
- **P3.4 Docs sprawl.** CLI usage, ULP install, classroom workflows, CI recipes, and naming advice each live in 3–5 places with drift between copies; `docs/` has no index. Merge `usage.md`+`workflows.md`; slim `USER_GUIDE.md` to pointers.
- **P3.5 Undiscoverable CLI surface.** `profiles list|check` is dispatched before argparse (`cli.py:392-394`) so `--help` never mentions it; `docs/usage.md:22-37`'s "Full option reference" omits `--list-mcus` and `--version`. The `--version` string is hardcoded in `cli.py:107` separately from `pyproject.toml`.
- **P3.6 Phantom content in ULP docs.** `ULP_GUIDE.md:117-124` documents two research ULPs that don't exist; `:73-84` a `temp/` directory nothing creates; `:52-53` claims blank project names auto-timestamp (they don't); `:155` says to check "verbose output in the ULP dialog" (no such thing). `FUSION_TEST_GUIDE.md` tests a dropdown and a directory selector that don't exist — the plan can't be executed as written.
- **P3.7 Example nits.** `examples/sensor_hub/README.md:35` and `communication_module/README.md:43` give commands that fail from the example's own directory (`No module named 'tools'`); `simple_led/README.md:106` suggests regenerating with `--mcu stm32g0`, which drops every pin of that netlist; path conventions differ between `examples/README.md` and per-example READMEs.
- **P3.8 Small doc/code lies.** `docs/output-formats.md:76-78` says ESP32 MicroPython pins are quoted strings (they're bare ints — the code is right); `:190` claims GitHub renders `.mmd` inline (it doesn't — only ```mermaid fences); `tests/README.md` lists 4 of 17 test files and its example imports a function that doesn't exist; `CONTRIBUTING.md:132` documents a `*_profile.py` convention no file follows; `CONTRIBUTING.md:57,190` + `docs/usage.md:213` + `docs/workflows.md:220` say the pre-commit hook regenerates/stages outputs (it only validates in a temp dir, `.githooks/pre-commit:5-8`); `copilot-instructions.md:157` describes a normalize.py inconsistency that was already fixed; `.vscode/extensions.json` recommends flake8 for a Ruff-only project; `pyproject.toml` classifiers stop at 3.11 while CI tests 3.11–3.14.
- **P3.9 Output determinism holes.** `special_pins_used` is computed pre-sort (`mcu_profiles.py:355-360`) — reordering CSV rows reorders PINOUT.md and pinmap.json (verified); emitters open files without `newline="\n"`, so Windows runs produce CRLF artifacts (no `.gitattributes`), defeating `--reproducible` cross-platform; timestamp formats differ per emitter (UTC-suffixed, naked, ISO); Mermaid node-ID suffixes depend on sort order.
- **P3.10 Mermaid emitter robustness.** Net names are interpolated into labels unescaped — a quote in a net name breaks the whole diagram's parse (`emit_mermaid.py:137,168,210`); every multi-pin net is styled with `class … power` (a 2-pin sensor bus renders as a yellow power rail, `:212`); it uses a third, different sanitizer that ignores the `+`/`-` polarity scheme.
- **P3.11 Arduino header details.** Fixed include guard `PINMAP_ARDUINO_H` (`emit_arduino.py:196`) — two pinmaps in one project silently no-op the second; differential-pair constants use `static constexpr uint8_t` initialized with tokens like `PA10` on STM32 (hard error on some cores).
- **P3.12 watch.py papercuts.** `--interval 0` (or negative) busy-loops at 100% CPU (no validation, `watch.py:274-282`); no write debounce (regenerates on half-written Excel saves); watching a directory with several netlists silently overwrites one output set last-write-wins (documented in usage.md but not warned at runtime); the subprocess requires the CWD to make `tools` importable, so `cd hardware/exports && watch .` fails on every trigger; defaults `--mcu rp2040 --mcu-ref U1` silently generate wrong-profile output for anyone watching non-RP2040 files without flags.
- **P3.13 Profile-registry edges.** One malformed TOML in `--profile-dir` makes `--list-mcus` die with a raw `TOMLDecodeError` and no filename (`profile_registry.py:190-193` vs `:135-136`); every `get_profile()` re-parses and re-validates the TOML (no caching); STM32G0 peripheral instances are numbered from 0 while ST names them from 1 (generated `SPI(0, …)` comments mislead).
- **P3.14 Misc runtime.** A pre-existing empty/garbage `SOURCE_DATE_EPOCH` env var crashes every run (`__init__.py:14-17` unguarded `int()`; `cli.py:409` `setdefault` won't repair it); `emit_json.py:31-39` reports problems via `warnings.warn` (deduplicated, easy to miss) while everything else uses stderr.
- **P3.15 License friction.** The custom non-OSI license is a legitimate choice, but: GitHub can't auto-detect it (no license badge/filtering), setuptools warns about the deprecated classifier on every build, "open source projects where no money is made" is ambiguous, and the commercial contact is a bare GitHub profile URL. An SPDX `LicenseRef` expression, a contact email, and one FAQ paragraph on what counts as commercial would help adopters' legal reviews.
- **P3.16 Zero releases.** `release.yml` is polished but has never run (no tags). Cutting `v0.1.0` would also flush out the broken install text in its notes (P0.3) before anyone follows it.

---

## Suggested order of attack

1. **Make results honest** (P0.2): print `validation_warnings`, honest final status line, ULP log capture + `--strict` + `exit $LASTEXITCODE` + show the log. One change converts silent wrong output into visible errors and makes every other ULP bug diagnosable.
2. **Fix the pin-namespace trap** (P0.1) and the **rp2040 USB pin data** (P1.1) — these are the two ways the tool can hand a beginner a wrong-but-plausible pinmap.
3. **Fix packaging or drop the promise** (P0.3): one `pyproject.toml` block, then sweep the 7 doc sites; add the CI test step (P1.2) and fix CONTRIBUTING (P1.3) in the same PR.
4. **ULP quick wins**: `dlgRedisplay()` (P1.6), `cmd.exe /c` + backslashed `explorer` paths (P1.7), `py -3` fallback + version probe, real button labels (P3.1).
5. **CSV ergonomics** (P1.4): fix the ragged-row crash, case-insensitive headers + sniffing + alias table, "found columns …" errors, list available RefDes values, stop requiring `Component`.
6. **Emitter safety** (P1.5, P2.5): reserved-name blacklist, role-aware usage examples, power/ground handling.
7. **One mechanical doc-sweep PR** for P2.9–P2.10 and the P3 doc items.
