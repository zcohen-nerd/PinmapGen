# ULP Automation — Technical Notes

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
          PR.pin.contacts(C) { pinNum = C.name; }
        }
      }
    }
  }
}
```

The generated CSV uses the standard `RefDes,Pin,Component,Net` headers
expected by `bom_csv.parse_csv()`.

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

| MCU | Pin naming | Notable validation |
|-----|------------|--------------------|
| RP2040 | `GPxx` | USB diff pair detection, ADC range |
| STM32G0 | `PAxn` | Alternate-function mux, boot/SWD pins |
| ESP32 | `GPIOxx` | Strapping pins, ADC2+WiFi conflict, input-only pins |

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
