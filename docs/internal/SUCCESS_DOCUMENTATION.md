# ULP Automation — Technical Notes

> **Internal development document.** Kept for project history; counts,
> tier lists, and feature claims reflect the moment they were written
> and are not maintained. Current user documentation lives in
> [README.md](../../README.md), [USER_GUIDE.md](../../USER_GUIDE.md),
> and [docs/](../).

This document records the key technical decisions and discoveries made while
building the Fusion 360 ULP integration.

## The problem

Fusion 360's ULP environment cannot invoke the `EXPORT NETLIST` command
programmatically. Early prototypes required users to manually export a CSV
before running the CLI.

## The solution

The ULP traverses the schematic object model directly:

```
schematic → sheets → nets → segments → pinrefs → pin → contacts
```

This yields the same net-to-pin data that a CSV export would contain, so the
ULP writes a temporary CSV and feeds it to the CLI. No manual export step is
needed.

### Key ULP syntax

```c
// Iterate nets and extract pin references
schematic(SCH) {
  SCH.sheets(SH) {
    SH.nets(N) {
      N.segments(SEG) {
        SEG.pinrefs(PR) {
          pinNum = PR.pin.name;                  // SYMBOL pin name (GP4, PA0)
          PR.pin.contacts(C) { padNum = C.name; } // physical pad, extra column
        }
      }
    }
  }
}
```

The Pin column carries the **symbol pin name**, never the package pad
number: pad 2 of an RP2040 is GPIO0, and the CLI would read a bare "2" as
GP2 — a plausible but wrong pinmap. The physical pad goes into an extra
`Pad` column for debugging.

The generated CSV uses the standard `RefDes,Pin,Component,Net,Pad` headers;
`bom_csv.parse_csv()` requires the first four and ignores the rest.

## Architecture

```
Fusion 360 Electronics schematic
       ↓  (ULP reads object model)
  Temporary CSV in output directory
       ↓  (ULP shells out to Python)
  PinmapGen CLI  →  all output formats
       ↓
  File Explorer opens output folder
```

## Supported MCU profiles

| MCU | Pin naming | Notable warnings |
|-----|------------|------------------|
| RP2040 | `GPxx` | USB diff pair detection, ADC channel labels |
| STM32G0 | `PAxn` | SWD debug pins, BOOT1 strap, oscillator/reset pins |
| ESP32 | `GPIOxx` | Strapping pins, ADC2+WiFi notes, input-only pins |

## Generated output

```
<project>/
├── pinmaps/pinmap.json
├── firmware/
│   ├── micropython/pinmap_micropython.py
│   ├── include/pinmap_arduino.h
│   └── docs/
│       ├── PINOUT.md
│       └── pinout.mmd
└── auto_netlist.csv  (temporary, can be deleted)
```

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Files appear on wrong Desktop | OneDrive Desktop redirection | Check actual `C:\Users\<you>\Desktop` |
| Python not found | PATH issue | Install Python 3.11+ and add to PATH |
| Empty output | MCU ref doesn't match schematic | Verify `U1` (or whatever ref) exists |
| Permission denied | Fusion or OS locking folder | Close Fusion, choose a different output dir |

## References

- [ULP_GUIDE.md](fusion_addin/ULP_GUIDE.md) — End-user installation and usage
- [FUSION_TEST_GUIDE.md](FUSION_TEST_GUIDE.md) — Test plan for the ULP
- [docs/extending.md](docs/extending.md) — Adding new MCU profiles
