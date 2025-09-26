"""
Arduino C++ Header Emitter for PinmapGen.

Generates pinmap_arduino.h files for Arduino/PlatformIO projects with role-aware helpers.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Union

from .roles import analyze_roles, PinRole


def emit_arduino_header(canonical_dict: Dict[str, Any], output_path: Union[Path, str]) -> None:
    """
    Generate Arduino C++ header file from canonical dictionary with role-aware helpers.
    
    Args:
        canonical_dict: Canonical pinmap dictionary with pins and differential pairs
        output_path: Path to output header file
    """
    # Ensure we have a Path object
    if isinstance(output_path, str):
        output_path = Path(output_path)
    
    # Create output directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Generate header code with role analysis
    code = generate_arduino_with_roles(canonical_dict)
    
    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(code)


def generate_arduino_defines(canonical_dict: Dict[str, Any]) -> str:
    """
    Generate Arduino #define statements from canonical dictionary.
    
    Args:
        canonical_dict: Canonical pinmap dictionary
        
    Returns:
        C++ header code string
    """
    lines = []
    
    # Header guard name based on filename
    guard_name = "PINMAP_ARDUINO_H"
    mcu = canonical_dict.get('mcu', 'unknown').upper()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    lines.extend([
        f'#ifndef {guard_name}',
        f'#define {guard_name}',
        '',
        '/*',
        f' * Auto-generated Arduino pinmap for {mcu}',
        f' * Generated: {timestamp}',
        ' * Generator: PinmapGen',
        ' */',
        '',
    ])
    
    # Generate pin definitions
    if 'pins' in canonical_dict:
        lines.append('// Pin Definitions')
        
        # Sort pins by net name for consistent output
        sorted_pins = sorted(canonical_dict['pins'].items())
        
        for net_name, pin_list in sorted_pins:
            if pin_list:  # Check if pin list is not empty
                pin_name = pin_list[0]  # Take first pin from list
                
                # Extract numeric part of pin (e.g., 'GP24' -> '24')
                pin_num = re.search(r'\d+', pin_name)
                if pin_num:
                    pin_num = pin_num.group()
                    const_name = _sanitize_net_name(net_name)
                    comment = _get_pin_comment(pin_name, canonical_dict)
                    lines.append(f'#define {const_name} {pin_num}  // {comment}')
        
        lines.append('')
    
    # Generate differential pairs if present
    if 'differential_pairs' in canonical_dict and canonical_dict['differential_pairs']:
        lines.append('// Differential Pairs')
        
        for pair in canonical_dict['differential_pairs']:
            pos_net = pair['positive']
            neg_net = pair['negative']
            
            # Get pin numbers
            pos_pins = canonical_dict['pins'].get(pos_net, [])
            neg_pins = canonical_dict['pins'].get(neg_net, [])
            
            if pos_pins and neg_pins:
                pos_pin = pos_pins[0]
                neg_pin = neg_pins[0]
                
                # Extract numeric parts
                pos_num = re.search(r'\d+', pos_pin)
                neg_num = re.search(r'\d+', neg_pin)
                
                if pos_num and neg_num:
                    pos_num = pos_num.group()
                    neg_num = neg_num.group()
                    
                    pair_const = _sanitize_net_name(f"{pos_net}_{neg_net}")
                    lines.append(f'#define {pair_const}_POS {pos_num}  // {pos_pin}')
                    lines.append(f'#define {pair_const}_NEG {neg_num}  // {neg_pin}')
        
        lines.append('')
    
    # Close header guard
    lines.extend([
        f'#endif // {guard_name}',
        ''
    ])
    
    return '\n'.join(lines)


def _sanitize_net_name(net_name: str) -> str:
    """
    Sanitize net name for use as C++ macro.
    
    Args:
        net_name: Raw net name from netlist
        
    Returns:
        Sanitized macro name
    """
    # Remove invalid characters and replace with underscores
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', net_name)
    
    # Remove leading digits
    sanitized = re.sub(r'^[0-9]+', '', sanitized)
    
    # Remove consecutive underscores
    sanitized = re.sub(r'_{2,}', '_', sanitized)
    
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    
    # Handle empty or invalid names
    if not sanitized or sanitized == '_':
        sanitized = 'UNNAMED_PIN'
    
    return sanitized.upper()


def _get_pin_comment(pin: str, canonical_dict: Dict[str, Any]) -> str:
    """
    Get descriptive comment for a pin.
    
    Args:
        pin: Pin name (e.g., 'GP24')
        canonical_dict: Canonical pinmap dictionary
        
    Returns:
        Comment string
    """
    comments = [pin]  # Always include the pin name
    
    # Add special function information
    special_functions = {
        'GP24': 'USB D-',
        'GP25': 'USB D+', 
        'GP26': 'ADC0',
        'GP27': 'ADC1',
        'GP28': 'ADC2', 
        'GP29': 'ADC3',
        'GP23': 'SMPS_MODE'
    }
    
    if pin in special_functions:
        comments.append(special_functions[pin])
    
    return ' - '.join(comments)


def generate_arduino_with_roles(canonical_dict: Dict[str, Any]) -> str:
    """
    Generate enhanced Arduino header with role-aware structures and helpers.
    
    Args:
        canonical_dict: Canonical pinmap dictionary
        
    Returns:
        Enhanced C++ header code string
    """
    lines = []
    
    # Header guard and includes
    guard_name = "PINMAP_ARDUINO_H"
    mcu = canonical_dict.get('mcu', 'unknown').upper()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    lines.extend([
        f'#ifndef {guard_name}',
        f'#define {guard_name}',
        '',
        '/*',
        f' * Auto-generated Arduino pinmap for {mcu}',
        f' * Generated: {timestamp}',
        ' * Generator: PinmapGen',
        ' *',
        ' * This file contains pin definitions, helper structures, and macros',
        ' * for easy hardware access in Arduino/PlatformIO projects.',
        ' */',
        '',
        '#include <Arduino.h>',
        '',
    ])
    
    # Analyze roles if pins are available
    if 'pins' in canonical_dict:
        # Convert canonical pins format to role analyzer format
        pins_for_analysis = {}
        for net_name, pin_list in canonical_dict['pins'].items():
            pins_for_analysis[net_name] = {
                'pin': pin_list[0] if pin_list else 'UNKNOWN',
                'component': canonical_dict.get('mcu', 'UNKNOWN'),
                'ref_des': canonical_dict.get('mcu_ref', 'UNKNOWN')
            }
        
        pin_infos, bus_groups, diff_pairs = analyze_roles(pins_for_analysis)
        
        # Generate pin constants grouped by role
        lines.extend([
            '// ========================================',
            '// Pin Definitions',
            '// ========================================',
            '',
        ])
        
        # Group constants by bus/function
        for group_name, pins in bus_groups.items():
            if pins:
                lines.append(f'// {group_name} Pins')
                for pin_info in pins:
                    pin_num = pin_info.pin_name.replace('GP', '')
                    const_name = _sanitize_net_name(pin_info.net_name)
                    comment = f'  // {pin_info.description}'
                    lines.append(f'#define {const_name} {pin_num}{comment}')
                lines.append('')
        
        # Generate differential pair structures
        if diff_pairs:
            lines.extend([
                '// ========================================',
                '// Differential Pair Structures',
                '// ========================================',
                '',
            ])
            
            for pair in diff_pairs:
                if pair[0].role == PinRole.USB_DP:
                    pos_const = _sanitize_net_name(pair[0].net_name)
                    neg_const = _sanitize_net_name(pair[1].net_name)
                    
                    lines.extend([
                        'struct USBPins {',
                        f'    static constexpr uint8_t DP = {pos_const};  // {pair[0].description}',
                        f'    static constexpr uint8_t DN = {neg_const};  // {pair[1].description}',
                        '};',
                        '',
                    ])
                
                elif pair[0].role == PinRole.CAN_H:
                    pos_const = _sanitize_net_name(pair[0].net_name)
                    neg_const = _sanitize_net_name(pair[1].net_name)
                    
                    lines.extend([
                        'struct CANPins {',
                        f'    static constexpr uint8_t H = {pos_const};  // {pair[0].description}',
                        f'    static constexpr uint8_t L = {neg_const};  // {pair[1].description}',
                        '};',
                        '',
                    ])
        
        # Generate helper macros
        lines.extend([
            '// ========================================', 
            '// Helper Macros',
            '// ========================================',
            '',
        ])
        
        # Digital I/O macros
        lines.extend([
            '// Digital I/O helpers',
            '#define PIN_INPUT(pin)          pinMode(pin, INPUT)',
            '#define PIN_INPUT_PULLUP(pin)   pinMode(pin, INPUT_PULLUP)',
            '#define PIN_OUTPUT(pin)         pinMode(pin, OUTPUT)',
            '#define READ_PIN(pin)           digitalRead(pin)',
            '#define WRITE_PIN(pin, val)     digitalWrite(pin, val)',
            '',
        ])
        
        # PWM helper
        pwm_pins = [p for p in pin_infos if p.role == PinRole.PWM]
        if pwm_pins:
            lines.extend([
                '// PWM helpers',
                '#define PWM_WRITE(pin, val)     analogWrite(pin, val)',
                '#define PWM_FREQ(pin, freq)     analogWriteFreq(freq)  // ESP32/RP2040',
                '',
            ])
        
        # ADC helper
        adc_pins = [p for p in pin_infos if p.role == PinRole.ADC]
        if adc_pins:
            lines.extend([
                '// ADC helpers',
                '#define ADC_READ(pin)           analogRead(pin)',
                '#define ADC_READ_VOLTAGE(pin)   (analogRead(pin) * 3.3f / 1023.0f)',
                '',
            ])
        
        # Bus setup helpers
        i2c_groups = {k: v for k, v in bus_groups.items() if k.startswith('I2C')}
        if i2c_groups:
            lines.extend([
                '// I2C setup helpers',
                '#include <Wire.h>',
            ])
            
            for i2c_name, pins in i2c_groups.items():
                sda_pin = next((p for p in pins if p.role == PinRole.I2C_SDA), None)
                scl_pin = next((p for p in pins if p.role == PinRole.I2C_SCL), None)
                
                if sda_pin and scl_pin:
                    func_name = f'SETUP_{i2c_name}'
                    sda_const = _sanitize_net_name(sda_pin.net_name)
                    scl_const = _sanitize_net_name(scl_pin.net_name)
                    
                    lines.extend([
                        f'#define {func_name}(freq) \\',
                        f'    Wire.setSDA({sda_const}); \\',
                        f'    Wire.setSCL({scl_const}); \\',
                        f'    Wire.setClock(freq); \\',
                        f'    Wire.begin()',
                        '',
                    ])
        
        # SPI setup helpers  
        spi_groups = {k: v for k, v in bus_groups.items() if k.startswith('SPI')}
        if spi_groups:
            lines.extend([
                '// SPI setup helpers',
                '#include <SPI.h>',
            ])
            
            for spi_name, pins in spi_groups.items():
                mosi_pin = next((p for p in pins if p.role == PinRole.SPI_MOSI), None)
                miso_pin = next((p for p in pins if p.role == PinRole.SPI_MISO), None)
                sck_pin = next((p for p in pins if p.role == PinRole.SPI_SCK), None)
                
                if mosi_pin and miso_pin and sck_pin:
                    func_name = f'SETUP_{spi_name}'
                    mosi_const = _sanitize_net_name(mosi_pin.net_name)
                    miso_const = _sanitize_net_name(miso_pin.net_name)
                    sck_const = _sanitize_net_name(sck_pin.net_name)
                    
                    lines.extend([
                        f'#define {func_name}(freq) \\',
                        f'    SPI.setMOSI({mosi_const}); \\',
                        f'    SPI.setMISO({miso_const}); \\',
                        f'    SPI.setSCK({sck_const}); \\',
                        f'    SPI.begin(); \\',
                        f'    SPI.setClockDivider(SPI_CLOCK_DIV2)',
                        '',
                    ])
    
    else:
        # Fallback if no pin data
        lines.extend([
            '// No pin data available',
            '// Please check your netlist input',
            '',
        ])
    
    # Close header guard
    lines.extend([
        f'#endif // {guard_name}',
        '',
    ])
    
    return '\n'.join(lines)