"""
JSON Emitter for PinmapGen.

Generates canonical pinmap.json files.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Union


def emit_json(canonical_dict: Dict[str, Any], output_path: Union[Path, str]) -> None:
    """
    Generate canonical pinmap.json file from canonical dictionary.
    
    Args:
        canonical_dict: Canonical pinmap dictionary with pins and differential pairs
        output_path: Path to output JSON file
    """
    # Ensure we have a Path object
    if isinstance(output_path, str):
        output_path = Path(output_path)
    
    # Create output directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Add generation timestamp
    output_data = canonical_dict.copy()
    output_data['generated'] = {
        'timestamp': datetime.now().isoformat(),
        'generator': 'PinmapGen',
        'version': '0.1.0'
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