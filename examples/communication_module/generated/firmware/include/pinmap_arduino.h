#ifndef PINMAP_ARDUINO_H
#define PINMAP_ARDUINO_H

/*
 * Auto-generated Arduino pinmap for RP2040
 * Generated: 2025-09-28 05:43:31
 * Generator: PinmapGen
 *
 * This file contains pin definitions, helper structures, and macros
 * for easy hardware access in Arduino/PlatformIO projects.
 */

#include <Arduino.h>

// ========================================
// Pin Definitions
// ========================================

// UART Pins
#define DEBUG_TX 0  // UART Transmit
#define DEBUG_RX 1  // UART Receive
#define WIFI_TX 8  // UART Transmit
#define WIFI_RX 9  // UART Receive

// SPI Pins
#define SPI_SCK 16  // SPI Serial Clock (SPI)
#define SPI_MISO 18  // SPI Master In Slave Out (SPI)
#define SPI_MOSI 19  // SPI Master Out Slave In (SPI)
#define LORA_CS 17  // SPI Chip Select
#define SD_CS 20  // SPI Chip Select

// Other Pins
#define LORA_RST 21  // Reset Signal
#define LORA_DIO0 22  // General Purpose I/O

// Indicators Pins
#define WIFI_LED 10  // Light Emitting Diode
#define LORA_LED 11  // Light Emitting Diode
#define SD_LED 12  // Light Emitting Diode

// ========================================
// Helper Macros
// ========================================

// Digital I/O helpers
#define PIN_INPUT(pin)          pinMode(pin, INPUT)
#define PIN_INPUT_PULLUP(pin)   pinMode(pin, INPUT_PULLUP)
#define PIN_OUTPUT(pin)         pinMode(pin, OUTPUT)
#define READ_PIN(pin)           digitalRead(pin)
#define WRITE_PIN(pin, val)     digitalWrite(pin, val)

// SPI setup helpers
#include <SPI.h>
#define SETUP_SPI(freq) \
    SPI.setMOSI(SPI_MOSI); \
    SPI.setMISO(SPI_MISO); \
    SPI.setSCK(SPI_SCK); \
    SPI.begin(); \
    SPI.setClockDivider(SPI_CLOCK_DIV2)

#endif // PINMAP_ARDUINO_H
