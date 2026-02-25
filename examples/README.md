# PinmapGen Examples

Three worked examples at increasing complexity. Each includes a netlist CSV
and pre-generated output files.

---

## 1. Simple LED (`simple_led/`)

**Complexity:** Beginner
**Focus:** Basic GPIO — LEDs and buttons on RP2040.

```bash
python -m tools.pinmapgen.cli --csv examples/simple_led/netlist.csv --mcu rp2040 --mcu-ref U1 --out-root examples/simple_led/generated --mermaid
```

## 2. Sensor Hub (`sensor_hub/`)

**Complexity:** Intermediate
**Focus:** Mixed I/O — DHT22 (digital), MPU6050 (I2C), LDR (analog), LED,
button.

```bash
python -m tools.pinmapgen.cli --csv examples/sensor_hub/netlist.csv --mcu rp2040 --mcu-ref U1 --out-root examples/sensor_hub/generated --mermaid
```

## 3. Communication Module (`communication_module/`)

**Complexity:** Advanced
**Focus:** Multiple protocols — dual UART, shared SPI bus with chip selects
(LoRa + SD card), status LEDs.

```bash
python -m tools.pinmapgen.cli --csv examples/communication_module/netlist.csv --mcu rp2040 --mcu-ref U1 --out-root examples/communication_module/generated --mermaid
```

---

## What each example contains

```
<example>/
├── netlist.csv          # Input netlist
├── README.md            # Description and pin assignments
└── generated/
    ├── pinmaps/pinmap.json
    └── firmware/
        ├── micropython/pinmap_micropython.py
        ├── include/pinmap_arduino.h
        └── docs/
            ├── PINOUT.md
            └── pinout.mmd
```

## Running all examples

```bash
for dir in simple_led sensor_hub communication_module; do
  python -m tools.pinmapgen.cli \
    --csv examples/$dir/netlist.csv \
    --mcu rp2040 --mcu-ref U1 \
    --out-root examples/$dir/generated \
    --mermaid
done
```
