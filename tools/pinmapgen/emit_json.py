"""
JSON Emitter for PinmapGen.

Generates canonical pinmap.json files with role metadata.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Union

from .roles import analyze_roles


def emit_json(canonical_dict: Dict[str, Any], output_path: Union[Path, str]) -> None:
    """
    Generate canonical pinmap.json file from canonical dictionary with role metadata.
    
    Args:
        canonical_dict: Canonical pinmap dictionary with pins and differential pairs
        output_path: Path to output JSON file
    """
    # Ensure we have a Path object
    if isinstance(output_path, str):
        output_path = Path(output_path)
    
    # Create output directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Start with canonical dictionary
    output_data = canonical_dict.copy()
    
    # Analyze roles for enhanced metadata
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
        
        # Enhance pin data with role information
        enhanced_pins = {}
        for pin_info in pin_infos:
            enhanced_pins[pin_info.net_name] = {
                'pins': canonical_dict['pins'][pin_info.net_name],
                'role': pin_info.role.value,
                'bus_group': pin_info.bus_group,
                'description': pin_info.description
            }
        
        output_data['pins'] = enhanced_pins
        
        # Add bus groupings
        output_data['bus_groups'] = {}
        for group_name, pins in bus_groups.items():
            output_data['bus_groups'][group_name] = [pin.net_name for pin in pins]
        
        # Add differential pair metadata
        if diff_pairs:
            output_data['differential_pairs'] = []
            for pair in diff_pairs:
                output_data['differential_pairs'].append({
                    'positive': pair[0].net_name,
                    'negative': pair[1].net_name,
                    'type': pair[0].role.value.split('.')[0]  # e.g., 'usb' from 'usb.dp'
                })
    
    # Add generation metadata
    output_data['generated'] = {
        'timestamp': datetime.now().isoformat(),
        'generator': 'PinmapGen',
        'version': '0.1.0',
        'features': ['role_inference', 'bus_groups', 'differential_pairs']
    }
    
    # Write JSON file with pretty formatting
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
        f.write('\n')  # Add trailing newline


def create_pinmap_structure(nets: Dict[str, List[str]], mcu_name: str) -> Dict[str, Any]:
    """
    Create standardized pinmap data structure (legacy function).
    
    This function is deprecated - use normalize.normalize_pinmap() instead.
    
    Args:
        nets: Net to pin mappings  
        mcu_name: MCU name for profile selection
        
    Returns:
        Pinmap data structure
    """
    from . import normalize
    return normalize.normalize_pinmap(nets, mcu_name)


def validate_canonical_dict(canonical_dict: Dict[str, Any]) -> List[str]:
    """
    Validate canonical dictionary structure.
    
    Args:
        canonical_dict: Canonical pinmap dictionary
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    # Check required top-level keys
    required_keys = {'mcu', 'pins', 'differential_pairs', 'metadata'}
    missing_keys = required_keys - set(canonical_dict.keys())
    if missing_keys:
        errors.append(f"Missing required keys: {missing_keys}")
    
    # Validate pins structure
    if 'pins' in canonical_dict:
        pins = canonical_dict['pins']
        if not isinstance(pins, dict):
            errors.append("'pins' must be a dictionary")
        else:
            for net_name, pin_list in pins.items():
                if not isinstance(pin_list, list):
                    errors.append(f"Pin list for net '{net_name}' must be a list")
                elif not pin_list:
                    errors.append(f"Pin list for net '{net_name}' is empty")
    
    # Validate differential pairs structure
    if 'differential_pairs' in canonical_dict:
        diff_pairs = canonical_dict['differential_pairs']
        if not isinstance(diff_pairs, list):
            errors.append("'differential_pairs' must be a list")
        else:
            for i, pair in enumerate(diff_pairs):
                if not isinstance(pair, dict):
                    errors.append(f"Differential pair {i} must be a dictionary")
                elif not all(key in pair for key in ['positive', 'negative']):
                    errors.append(f"Differential pair {i} missing 'positive' or 'negative' key")
    
    return errors