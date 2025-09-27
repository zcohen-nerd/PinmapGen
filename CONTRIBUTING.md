# Contributing to PinmapGen

Thank you for your interest in contributing to PinmapGen! This document provides guidelines for contributors to help maintain code quality and project consistency.

## 🚀 Quick Start

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/your-username/PinmapGen.git
   cd PinmapGen
   ```

2. **Set up the development environment:**
   ```bash
   # Create virtual environment (optional but recommended)
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   # .venv\Scripts\activate     # Windows
   
   # Install in development mode
   pip install -e .
   
   # Install git hooks
   bash .githooks/install-hooks.sh  # Linux/macOS
   pwsh -File .githooks/install-hooks.ps1  # Windows
   ```

3. **Test your setup:**
   ```bash
   python -m tools.pinmapgen.cli --help
   python -m tools.pinmapgen.cli --csv hardware/exports/sample_netlist.csv --mcu rp2040 --mcu-ref U1 --out-root . --mermaid
   ```

## 🎯 Development Workflow

### Creating a Feature or Fix

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/issue-description
   ```

2. **Make your changes** following the coding standards below

3. **Test your changes:**
   ```bash
   # Test basic functionality
   python -m tools.pinmapgen.cli --csv hardware/exports/sample_netlist.csv --mcu rp2040 --mcu-ref U1 --out-root . --mermaid
   
   # Test all modules import correctly
   python -c "import tools.pinmapgen.cli; print('CLI OK')"
   python -c "import tools.pinmapgen.bom_csv; print('CSV parser OK')"
   # ... test other modules
   ```

4. **Commit your changes:**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```
   
   The pre-commit hook will automatically regenerate pinmaps if needed.

5. **Push and create a Pull Request:**
   ```bash
   git push origin feature/your-feature-name
   ```

### Commit Message Format

Use conventional commits for clear history:

- `feat:` - New features
- `fix:` - Bug fixes  
- `docs:` - Documentation changes
- `style:` - Code formatting (no functional changes)
- `refactor:` - Code restructuring (no functional changes)
- `test:` - Adding or updating tests
- `chore:` - Build/tooling changes

Examples:
```
feat: add ESP32 MCU support
fix: handle empty CSV files gracefully  
docs: update installation instructions
refactor: extract common pin validation logic
```

## 📋 Coding Standards

### Python Code Style

PinmapGen follows these coding standards:

**Import Organization:**
```python
# Standard library imports first
import re
import json
from pathlib import Path
from typing import Dict, List, Any, Union

# Local imports last
from .normalize import normalize_pin_name
from .roles import infer_pin_role
```

**Function Documentation:**
```python
def emit_arduino_header(canonical_dict: Dict[str, Any], output_path: Union[Path, str]) -> None:
    """
    Generate Arduino C++ header file from canonical dictionary.
    
    Args:
        canonical_dict: Canonical pinmap dictionary with pins and metadata
        output_path: Path to output .h file
        
    Returns:
        None
        
    Raises:
        FileNotFoundError: If output directory cannot be created
    """
```

**Code Organization:**
- Keep functions focused and under 50 lines when possible
- Use descriptive variable names: `pin_assignments` not `pa`
- Prefer explicit over implicit: `is_differential_pair` not `is_diff`
- Use type hints for all function parameters and return values

**Error Handling:**
```python
# Good: Specific error handling
try:
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        # ... process
except FileNotFoundError:
    print(f"Error: CSV file not found: {csv_file}")
    return None
except UnicodeDecodeError:
    print(f"Error: Invalid encoding in CSV file: {csv_file}")
    return None

# Avoid: Catching all exceptions
try:
    # ... code
except Exception as e:
    print(f"Something went wrong: {e}")  # Too generic
```

### File Structure

When adding new functionality, follow these patterns:

**Parser modules** (`bom_csv.py`, `eagle_sch.py`):
- Return standardized `RawPinmap` data structure
- Handle file encoding and format variations
- Provide clear error messages for invalid input

**Emitter modules** (`emit_*.py`):
- Accept canonical dictionary format
- Create output directories as needed
- Generate deterministic output (same input → same output)
- Include auto-generated headers with timestamps

**Utility modules** (`normalize.py`, `roles.py`):
- Focus on single responsibilities
- Provide pure functions when possible
- Include comprehensive test cases

## 🔧 Adding New Features

### Adding a New MCU Profile

To add support for a new microcontroller:

1. **Update normalize.py:**
   ```python
   def normalize_pin_name(pin_name: str, mcu: str) -> str:
       """Normalize pin names for the target MCU."""
       if mcu.lower() == 'rp2040':
           # Existing RP2040 logic...
       elif mcu.lower() == 'stm32g0':  # New MCU
           # Add STM32G0 pin normalization
           return normalize_stm32g0_pin(pin_name)
   ```

2. **Add MCU-specific validation in roles.py:**
   ```python
   def validate_pin_assignment(pin: str, role: str, mcu: str) -> List[str]:
       """Validate that a pin can fulfill the assigned role."""
       warnings = []
       
       if mcu.lower() == 'stm32g0':
           # Add STM32G0-specific pin capability checks
           if role == 'adc' and not pin.startswith('PA'):
               warnings.append(f"Pin {pin} may not support ADC")
               
       return warnings
   ```

3. **Update emitters for MCU-specific code generation**

4. **Add test data and documentation**

### Adding a New Input Format

To support a new input format (e.g., KiCad netlists):

1. **Create parser module:**
   ```python
   # tools/pinmapgen/kicad_net.py
   def parse_kicad_netlist(file_path: str, mcu_ref: str) -> Optional[RawPinmap]:
       """Parse KiCad netlist file."""
   ```

2. **Update CLI to support new format:**
   ```python
   # In cli.py
   parser.add_argument('--kicad', help='KiCad netlist file')
   ```

3. **Add detection logic and tests**

### Adding a New Output Format

To add a new output format (e.g., Rust constants):

1. **Create emitter module:**
   ```python
   # tools/pinmapgen/emit_rust.py
   def emit_rust_constants(canonical_dict: Dict[str, Any], output_path: Union[Path, str]) -> None:
       """Generate Rust constants file."""
   ```

2. **Update CLI and main generator logic**

3. **Add format to documentation and examples**

## 🧪 Testing

### Manual Testing

Always test your changes with:

```bash
# Basic functionality
python -m tools.pinmapgen.cli --csv hardware/exports/sample_netlist.csv --mcu rp2040 --mcu-ref U1 --out-root test_output --mermaid

# Different MCU references
python -m tools.pinmapgen.cli --csv hardware/exports/sample_netlist.csv --mcu rp2040 --mcu-ref IC1 --out-root test_output

# File watcher
python -m tools.pinmapgen.watch hardware/exports/ --out-root test_output --interval 1.0
```

### Adding Unit Tests

When adding unit tests (see [Milestone 3](MILESTONES.md)):

```python
# tests/test_normalize.py
import unittest
from tools.pinmapgen.normalize import normalize_pin_name

class TestNormalize(unittest.TestCase):
    def test_rp2040_pin_normalization(self):
        """Test RP2040 pin name normalization."""
        self.assertEqual(normalize_pin_name("GPIO0", "rp2040"), "GP0")
        self.assertEqual(normalize_pin_name("GP1", "rp2040"), "GP1")
```

## 📚 Documentation

### Code Documentation

- Document all public functions with docstrings
- Include examples in docstrings for complex functions
- Update README.md when adding major features
- Add comments for complex logic or workarounds

### User Documentation  

- Update README.md for new CLI options
- Add examples to relevant sections
- Update VS Code snippets for new output formats
- Consider adding tutorial documentation

## 🐛 Bug Reports and Issues

### Reporting Bugs

When reporting bugs, include:

1. **Environment information:**
   - Operating system (Windows/macOS/Linux)  
   - Python version (`python --version`)
   - Git commit or version being used

2. **Reproduction steps:**
   - Exact command that triggered the issue
   - Input files (or minimal examples)
   - Expected vs. actual behavior

3. **Error output:**
   - Full error messages and stack traces
   - Generated files if relevant

### Feature Requests

For feature requests:

1. **Describe the use case:** What problem does this solve?
2. **Proposed solution:** How should it work?
3. **Alternatives considered:** What other approaches were considered?
4. **Implementation notes:** Any technical constraints or suggestions?

## 🔄 Development Tools

### VS Code Configuration

The project includes VS Code configuration:
- `.vscode/tasks.json` - Build and watch tasks
- `.vscode/extensions.json` - Recommended extensions
- `.vscode/pinmap.code-snippets` - Code snippets

### Git Hooks

Pre-commit hooks automatically:
- Regenerate pinmaps when hardware files change
- Ensure outputs stay in sync with inputs

To bypass hooks (not recommended):
```bash
git commit --no-verify -m "message"
```

### GitHub Actions

The CI pipeline:
- Tests on multiple Python versions and platforms
- Validates generated outputs are up to date  
- Performs integration testing
- Runs performance tests

## ❓ Getting Help

- **GitHub Issues:** For bug reports and feature requests
- **GitHub Discussions:** For questions and general discussion  
- **Code Review:** All contributions go through pull request review
- **Documentation:** Check README.md and code comments first

## 🎉 Recognition

Contributors are recognized through:
- Git commit history
- GitHub contributor statistics  
- Mentions in release notes for significant contributions

Thank you for contributing to PinmapGen! Your efforts help make electronics development more productive and enjoyable.