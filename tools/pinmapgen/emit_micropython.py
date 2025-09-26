"""
MicroPython Emitter for PinmapGen.

Generates pinmap_micropython.py files for MicroPython projects with helper functions.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Union

from .roles import analyze_roles, PinRole


def emit_micropython(canonical_dict: Dict[str, Any], output_path: Union[Path, str]) -> None:
    """
    Generate MicroPython pinmap file from canonical dictionary with helper functions.
    
    Args:
        canonical_dict: Canonical pinmap dictionary with pins and differential pairs
        output_path: Path to output Python file
    """
    # Ensure we have a Path object
    if isinstance(output_path, str):
        output_path = Path(output_path)
    
    # Create output directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Generate MicroPython code with role analysis
    code = generate_micropython_with_roles(canonical_dict)
    
    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(code)


def generate_micropython_constants(canonical_dict: Dict[str, Any]) -> str:
    """
    Generate MicroPython pin constant definitions from canonical dictionary.
    
    Args:
        canonical_dict: Canonical pinmap dictionary
        
    Returns:
        MicroPython code string
    """
    lines = []
    
    # File header
    mcu = canonical_dict.get('mcu', 'unknown').upper()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    lines.extend([
        '"""',
        f'Auto-generated MicroPython pinmap for {mcu}.',
        f'Generated: {timestamp}',
        'Generator: PinmapGen',
        '',
        'Pin constants for easy hardware access.',
        '"""',
        '',
    ])
    
    # Generate pin constants
    if 'pins' in canonical_dict:
        lines.append('# Pin Constants')
        
        # Sort pins by net name for consistent output
        sorted_pins = sorted(canonical_dict['pins'].items())
        
        for net_name, pin_data in sorted_pins:
            pin_name = pin_data.get('pin', 'UNKNOWN')
            
            # Extract numeric part of pin (e.g., 'GP24' -> '24')
            pin_num = re.search(r'\d+', pin_name)
            if pin_num:
                pin_num = pin_num.group()
                const_name = _sanitize_net_name(net_name)
                comment = _get_pin_comment(pin_name, canonical_dict)
                lines.append(f'{const_name} = {pin_num}  # {comment}')
        
        lines.append('')
    
    # Generate differential pairs if present
    if 'differential_pairs' in canonical_dict and canonical_dict['differential_pairs']:
        lines.append('# Differential Pairs')
        
        for pair in canonical_dict['differential_pairs']:
            pair_name = pair['name']
            pos_pin = pair['positive']['pin']
            neg_pin = pair['negative']['pin']
            
            # Extract numeric parts
            pos_num = re.search(r'\d+', pos_pin)
            neg_num = re.search(r'\d+', neg_pin)
            
            if pos_num and neg_num:
                pos_num = pos_num.group()
                neg_num = neg_num.group()
                
                pair_const = _sanitize_net_name(pair_name)
                lines.append(f'{pair_const}_POS = {pos_num}  # {pos_pin}')
                lines.append(f'{pair_const}_NEG = {neg_num}  # {neg_pin}')
        
        lines.append('')
    
    return '\n'.join(lines)


def _sanitize_net_name(net_name: str) -> str:
    """
    Sanitize net name for use as Python constant.
    
    Args:
        net_name: Raw net name from netlist
        
    Returns:
        Sanitized constant name
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


def generate_micropython_with_roles(canonical_dict: Dict[str, Any]) -> str:
    """
    Generate enhanced MicroPython pinmap with role-aware helper functions.
    
    Args:
        canonical_dict: Canonical pinmap dictionary
        
    Returns:
        Enhanced MicroPython code string
    """
    lines = []
    
    # File header
    mcu = canonical_dict.get('mcu', 'unknown').upper()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    lines.extend([
        '"""',
        f'Auto-generated MicroPython pinmap for {mcu}.',
        f'Generated: {timestamp}',
        'Generator: PinmapGen',
        '',
        'This file contains pin constants and helper functions for easy hardware access.',
        '"""',
        '',
        'from machine import Pin, I2C, SPI, PWM, ADC',
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
        lines.append('# ========================================')
        lines.append('# Pin Constants')
        lines.append('# ========================================')
        lines.append('')
        
        # Group constants by bus/function
        for group_name, pins in bus_groups.items():
            if pins:
                lines.append(f'# {group_name} Pins')
                for pin_info in pins:
                    pin_num = pin_info.pin_name.replace('GP', '')
                    const_name = _sanitize_net_name(pin_info.net_name)
                    comment = f'  # {pin_info.description}'
                    lines.append(f'{const_name} = {pin_num}{comment}')
                lines.append('')
        
        # Generate helper functions
        lines.extend([
            '# ========================================',
            '# Helper Functions',
            '# ========================================',
            '',
        ])
        
        # Digital I/O helpers
        lines.extend([
            'def pin_in(pin_num, pull=None):',
            '    """Create a digital input pin with optional pull resistor."""',
            '    return Pin(pin_num, Pin.IN, pull)',
            '',
            'def pin_out(pin_num, value=0):',
            '    """Create a digital output pin with initial value."""',
            '    return Pin(pin_num, Pin.OUT, value=value)',
            '',
        ])
        
        # ADC helper
        adc_pins = [p for p in pin_infos if p.role == PinRole.ADC]
        if adc_pins:
            lines.extend([
                'def adc(pin_num):',
                '    """Create an ADC object for analog reading."""',
                '    return ADC(Pin(pin_num))',
                '',
            ])
        
        # PWM helper
        pwm_pins = [p for p in pin_infos if p.role == PinRole.PWM]
        if pwm_pins:
            lines.extend([
                'def pwm(pin_num, freq=1000):',
                '    """Create a PWM object with specified frequency."""',
                '    return PWM(Pin(pin_num), freq=freq)',
                '',
            ])
        
        # I2C setup helpers
        i2c_groups = {k: v for k, v in bus_groups.items() if k.startswith('I2C')}
        for i2c_name, pins in i2c_groups.items():
            sda_pin = next((p for p in pins if p.role == PinRole.I2C_SDA), None)
            scl_pin = next((p for p in pins if p.role == PinRole.I2C_SCL), None)
            
            if sda_pin and scl_pin:
                i2c_num = i2c_name.replace('I2C', '').lower() or '0'
                func_name = f'setup_{i2c_name.lower()}'
                sda_const = _sanitize_net_name(sda_pin.net_name)
                scl_const = _sanitize_net_name(scl_pin.net_name)
                
                lines.extend([
                    f'def {func_name}(freq=400000):',
                    f'    """Setup {i2c_name} with SDA={sda_pin.pin_name}, SCL={scl_pin.pin_name}."""',
                    f'    return I2C({i2c_num}, sda=Pin({sda_const}), scl=Pin({scl_const}), freq=freq)',
                    '',
                ])
        
        # SPI setup helpers
        spi_groups = {k: v for k, v in bus_groups.items() if k.startswith('SPI')}
        for spi_name, pins in spi_groups.items():
            mosi_pin = next((p for p in pins if p.role == PinRole.SPI_MOSI), None)
            miso_pin = next((p for p in pins if p.role == PinRole.SPI_MISO), None)
            sck_pin = next((p for p in pins if p.role == PinRole.SPI_SCK), None)
            
            if mosi_pin and miso_pin and sck_pin:
                spi_num = spi_name.replace('SPI', '').lower() or '0'
                func_name = f'setup_{spi_name.lower()}'
                mosi_const = _sanitize_net_name(mosi_pin.net_name)
                miso_const = _sanitize_net_name(miso_pin.net_name)
                sck_const = _sanitize_net_name(sck_pin.net_name)
                
                lines.extend([
                    f'def {func_name}(baudrate=1000000):',
                    f'    """Setup {spi_name} with MOSI={mosi_pin.pin_name}, MISO={miso_pin.pin_name}, SCK={sck_pin.pin_name}."""',
                    f'    return SPI({spi_num}, mosi=Pin({mosi_const}), miso=Pin({miso_const}), sck=Pin({sck_const}), baudrate=baudrate)',
                    '',
                ])
        
        # Differential pair helpers
        if diff_pairs:
            lines.extend([
                '# ========================================',
                '# Differential Pair Classes',
                '# ========================================',
                '',
            ])
            
            for pair in diff_pairs:
                if pair[0].role == PinRole.USB_DP:
                    pos_const = _sanitize_net_name(pair[0].net_name)
                    neg_const = _sanitize_net_name(pair[1].net_name)
                    
                    lines.extend([
                        'class USBPins:',
                        '    """USB differential pair pin definitions."""',
                        f'    DP = {pos_const}  # {pair[0].description}',
                        f'    DN = {neg_const}  # {pair[1].description}',
                        '',
                        '    @classmethod',
                        '    def get_pair(cls):',
                        '        """Get USB D+/D- pin tuple."""',
                        '        return (cls.DP, cls.DN)',
                        '',
                    ])
    
    else:
        # Fallback to basic constants if no pin data
        lines.extend([
            '# No pin data available',
            '# Please check your netlist input',
            '',
        ])
    
    return '\n'.join(lines)