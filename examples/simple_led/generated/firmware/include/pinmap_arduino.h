#ifndef PINMAP_ARDUINO_H
#define PINMAP_ARDUINO_H

/*
 * Auto-generated Arduino pinmap for RP2040
 * Generated: 1970-01-01 00:00:00
 * Generator: PinmapGen
 *
 * This file contains pin definitions, helper structures, and macros
 * for easy hardware access in Arduino/PlatformIO projects.
 */

#include <Arduino.h>

// ========================================
// Pin Definitions
// ========================================

// Inputs Pins
#define BUTTON_1 5  // Push Button Input
#define BUTTON_2 6  // Push Button Input

// Indicators Pins
#define LED_BLUE 4  // Light Emitting Diode
#define LED_GREEN 3  // Light Emitting Diode
#define LED_RED 2  // Light Emitting Diode

// ========================================
// Helper Macros
// ========================================

// Digital I/O helpers
#define PIN_INPUT(pin)          pinMode(pin, INPUT)
#define PIN_INPUT_PULLUP(pin)   pinMode(pin, INPUT_PULLUP)
#define PIN_OUTPUT(pin)         pinMode(pin, OUTPUT)
#define READ_PIN(pin)           digitalRead(pin)
#define WRITE_PIN(pin, val)     digitalWrite(pin, val)

#endif // PINMAP_ARDUINO_H
