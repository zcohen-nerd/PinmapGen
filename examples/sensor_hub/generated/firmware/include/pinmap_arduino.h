#ifndef PINMAP_ARDUINO_H
#define PINMAP_ARDUINO_H

/*
 * Auto-generated Arduino pinmap for RP2040
 * Generated: 2025-09-28 05:43:28
 * Generator: PinmapGen
 *
 * This file contains pin definitions, helper structures, and macros
 * for easy hardware access in Arduino/PlatformIO projects.
 */

#include <Arduino.h>

// ========================================
// Pin Definitions
// ========================================

// Other Pins
#define SENSOR_DATA 2  // General Purpose I/O

// I2C Pins
#define I2C_SDA 4  // I2C Serial Data (I2C)
#define I2C_SCL 5  // I2C Serial Clock (I2C)

// Indicators Pins
#define LIGHT_ANALOG 26  // Light Emitting Diode
#define STATUS_LED 15  // Light Emitting Diode

// Inputs Pins
#define BUTTON_IN 14  // Push Button Input

// ========================================
// Helper Macros
// ========================================

// Digital I/O helpers
#define PIN_INPUT(pin)          pinMode(pin, INPUT)
#define PIN_INPUT_PULLUP(pin)   pinMode(pin, INPUT_PULLUP)
#define PIN_OUTPUT(pin)         pinMode(pin, OUTPUT)
#define READ_PIN(pin)           digitalRead(pin)
#define WRITE_PIN(pin, val)     digitalWrite(pin, val)

// I2C setup helpers
#include <Wire.h>
#define SETUP_I2C(freq) \
    Wire.setSDA(I2C_SDA); \
    Wire.setSCL(I2C_SCL); \
    Wire.setClock(freq); \
    Wire.begin()

#endif // PINMAP_ARDUINO_H
