# PinmapGen — from Fusion 360 schematic to working code

[![License: Custom](https://img.shields.io/badge/License-PinmapGen%20Community-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://python.org)
[![CI/CD](https://img.shields.io/github/actions/workflow/status/zcohen-nerd/PinmapGen/build-test.yml?branch=main&label=CI%2FCD)](https://github.com/zcohen-nerd/PinmapGen/actions)
[![Issues](https://img.shields.io/github/issues/zcohen-nerd/PinmapGen)](https://github.com/zcohen-nerd/PinmapGen/issues)

You've drawn your circuit in Fusion 360 Electronics. Now someone has to look
at the schematic and carefully type out which pin the LED is on, which pins
the sensor uses, and so on — and re-do it every time the design changes. One
typo and the firmware talks to the wrong pin.

**PinmapGen does that step for you.** It reads your schematic and writes the
pin definitions automatically:

```
Your schematic says:          PinmapGen writes for you:
─────────────────────         ─────────────────────────────
LED_STATUS  → pin GP15   →    LED_STATUS = 15        (MicroPython)
BUTTON_1    → pin GP5    →    #define BUTTON_1 5     (Arduino)
                              ...plus a readable pinout document
```

It also **checks your design** while it works — it warns you if two signals
share a pin, if you used a special pin (like a boot or debug pin) by
accident, or if a USB data pair is missing its partner.

---

## What you get

Every time you run PinmapGen, it creates a folder containing:

| File | What it's for |
|------|---------------|
| `pinmap_micropython.py` | Drop onto your board — pin names ready to use in MicroPython |
| `pinmap_arduino.h` | Include in your Arduino / PlatformIO project |
| `PINOUT.md` | A human-readable table of every pin — great for sharing with your team |
| `pinout.mmd` | A wiring diagram you can view with any Mermaid viewer |
| `pinmap.json` | Machine-readable data, for scripts and automation |

---

## What you'll need

1. **Windows PC** with **Fusion 360** (the Electronics workspace).
   *On Mac or Linux? The [command line](#using-the-command-line) works there too.*
2. **Python 3.11 or newer** — a free download, installed once (steps below).
3. **This project's files** — also a one-time download.

No programming experience needed for the Fusion workflow.

---

## One-time setup (about 10 minutes)

### Step 1 — Install Python

1. Go to [python.org/downloads](https://www.python.org/downloads/) and click
   the big **Download Python** button.
2. Run the installer. **Important:** on the first screen, tick the box that
   says **"Add python.exe to PATH"** before clicking Install. (If you miss
   it, just run the installer again — it's the checkbox at the bottom.)
3. That's it. You never have to touch Python directly — Fusion will use it
   behind the scenes.

### Step 2 — Download PinmapGen

1. On this page, click the green **`<> Code`** button (top right), then
   **Download ZIP**.
2. Right-click the downloaded ZIP → **Extract All**.
3. Put the extracted `PinmapGen` folder somewhere easy to find and permanent,
   for example `Documents\PinmapGen`. **Remember this location** — you'll
   point Fusion at it in Step 4.

*(If you're comfortable with git: `git clone https://github.com/zcohen-nerd/PinmapGen.git` does the same thing.)*

### Step 3 — Install the ULP into Fusion

A ULP is a small script that runs inside Fusion's Electronics workspace.

1. Open File Explorer, click in the address bar, paste this, and press Enter:
   ```
   %APPDATA%\Autodesk\Autodesk Fusion 360\API\ULPs
   ```
2. Copy `PinmapGen.ulp` from the `fusion_addin` folder of your PinmapGen
   download into that window.
3. Restart Fusion 360.

### Step 4 — First run

1. Open your design in the **Electronics** workspace (schematic view).
2. Go to **Automation → Run ULP** and pick **PinmapGen**.
3. In the dialog:
   - **PinmapGen repository** — enter the folder from Step 2, e.g.
     `C:\Users\YourName\Documents\PinmapGen`. You only do this once; it's
     remembered for next time.
   - **MCU Type** — click the button for your chip (RP2040 for a Pico,
     ATmega328P for an Uno, and so on — see the [chip list](#supported-chips)).
   - **MCU Reference** — the name of your microcontroller in the schematic,
     usually `U1`. Not sure? Click your MCU in the schematic and check its
     name, or use the **Analyze** button in the dialog.
   - **Output directory** — where the generated files should go (a sensible
     default is filled in).
4. Click **Generate Pinmap**. When it finishes, the output folder opens in
   File Explorer with your files ready to use.

From now on, whenever the schematic changes, just run the ULP again —
everything is remembered, so it's two clicks.

---

## Using the generated files

**MicroPython** (Raspberry Pi Pico and similar): copy
`pinmap_micropython.py` onto your board alongside your code, then:

```python
from pinmap_micropython import *
from machine import Pin

led = Pin(LED_STATUS, Pin.OUT)   # no pin numbers to look up — just names
led.on()
```

**Arduino / PlatformIO**: copy `pinmap_arduino.h` into your sketch or
project's include folder, then:

```cpp
#include "pinmap_arduino.h"

void setup() {
  pinMode(LED_STATUS, OUTPUT);
  digitalWrite(LED_STATUS, HIGH);
}
```

**For your team**: `PINOUT.md` is a plain document listing every net, its
pin, and any warnings — perfect to attach to a design review.

Read about every output in [docs/output-formats.md](docs/output-formats.md).

---

## Supported chips

PinmapGen knows the pin rules for 13 microcontrollers out of the box:

| If your board is a… | Choose this MCU type |
|---------------------|----------------------|
| Raspberry Pi Pico / Pico W | `rp2040` |
| Raspberry Pi Pico 2 | `rp2350` |
| ESP32 dev board (WROOM) | `esp32` |
| ESP32-S3 board | `esp32s3` |
| ESP32-C3 board | `esp32c3` |
| STM32 Nucleo / custom STM32G0 | `stm32g0` |
| "BlackPill" (STM32F411) | `stm32f411` |
| STM32H743 board | `stm32h743` |
| nRF52840 (Feather nRF52840, DK) | `nrf52840` |
| Arduino Uno / Nano | `atmega328p` |
| Arduino Mega 2560 | `atmega2560` |
| Arduino Zero / Adafruit M0 | `atsamd21` |
| Adafruit M4 boards | `atsamd51` |

Using a chip that isn't listed? You can add one by writing a small text file —
no programming required. See [docs/extending.md](docs/extending.md).

---

## When something goes wrong

**"MCU 'U1' not found"** — the reference name doesn't match your schematic.
Click your microcontroller in Fusion and check its name (it might be `IC1`
or `U2`), then enter that instead.

**"Python not found"** — Python isn't installed, or the "Add to PATH" box
wasn't ticked. Re-run the Python installer from Step 1 and tick the box.

**The ULP doesn't appear in Fusion** — make sure `PinmapGen.ulp` is in the
ULPs folder from Step 3, then restart Fusion completely.

**"does not look like the PinmapGen repository"** — the repository path in
the dialog should point at the folder that contains `tools` and `README.md`
(if you extracted a ZIP, watch out for a doubled folder like
`PinmapGen-main\PinmapGen-main`).

**Warnings about strapping / boot / debug pins** — not errors! PinmapGen is
telling you a pin has a special job on your chip. Double-check those pins
are safe to use for your signal, or move the signal to another pin.

More answers: [docs/troubleshooting.md](docs/troubleshooting.md) and
[docs/faq.md](docs/faq.md).

---

## Using the command line

If you're comfortable in a terminal (or you're on Mac/Linux), you can skip
the ULP entirely. Export a netlist CSV from your CAD tool with the columns
`Net, Pin, Component, RefDes`, then from the PinmapGen folder:

```bash
python -m tools.pinmapgen.cli --csv my_netlist.csv --mcu rp2040 --mcu-ref U1 --out-root output --mermaid
```

Handy extras:

```bash
python -m tools.pinmapgen.cli --list-mcus     # see every supported chip
python -m tools.pinmapgen.cli ... --strict    # fail (exit code 2) on any pin conflict — great for CI
python -m tools.pinmapgen.watch hardware/exports/   # auto-regenerate whenever a CSV changes
```

Tip for Windows: open the PinmapGen folder in File Explorer, click the
address bar, type `cmd`, and press Enter — that opens a terminal already in
the right place.

Full reference: [docs/usage.md](docs/usage.md). Team workflows and CI
recipes: [docs/workflows.md](docs/workflows.md).

---

## Examples

Three complete worked examples live in [`examples/`](examples/) — each has
the input netlist and every generated file, so you can see exactly what you'll
get before installing anything:

- [`simple_led`](examples/simple_led/) — LEDs and buttons (beginner)
- [`sensor_hub`](examples/sensor_hub/) — I²C/SPI sensors (intermediate)
- [`communication_module`](examples/communication_module/) — UART/CAN/USB (advanced)

---

## Contributing

Bug reports and pull requests are welcome — start with
[CONTRIBUTING.md](CONTRIBUTING.md). Run the test suite with `python -m pytest`
before submitting.

---

## License

PinmapGen is released under the **PinmapGen Community License**:

- **Free** for personal projects, education, and open source
- **Commercial license required** for business use, client work, and
  commercial products

See [LICENSE](LICENSE) for the complete terms.
