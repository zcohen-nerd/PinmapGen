# Git Hooks for PinmapGen

This directory contains git hooks that validate netlist exports before they are committed.

## Available Hooks

### Pre-commit Hook

When a commit stages CSV files under `hardware/exports/`, the hook runs the PinmapGen CLI against each changed netlist in a temporary directory. If generation fails (unparseable CSV, unknown pins, missing MCU reference), the commit is blocked so broken netlists never land.

The hook does **not** stage or commit generated output — the root-level `pinmaps/` and `firmware/` directories are gitignored scratch artifacts produced by the quick-start commands.

**Files:**
- `pre-commit` - Bash version for Linux/macOS/Git Bash
- `pre-commit.ps1` - PowerShell version for Windows

## Installation

### Automatic Installation

Run the installation script for your platform:

**Linux/macOS/Git Bash:**
```bash
bash .githooks/install-hooks.sh
```

**Windows PowerShell:**
```powershell
pwsh -File .githooks/install-hooks.ps1
```

### Manual Installation

If the automatic installation doesn't work:

1. Copy the appropriate hook file:
   ```bash
   # For bash environments
   cp .githooks/pre-commit .git/hooks/pre-commit
   chmod +x .git/hooks/pre-commit
   
   # For PowerShell environments  
   cp .githooks/pre-commit.ps1 .git/hooks/pre-commit.ps1
   ```

2. Make the hook executable (Linux/macOS):
   ```bash
   chmod +x .git/hooks/pre-commit
   ```

## How It Works

When you commit changes that include CSV files in `hardware/exports/`:

1. The hook lists the staged `.csv` files
2. Picks an MCU profile from each filename (`stm32*` → stm32g0, `esp32*` → esp32, `nrf52*` → nrf52840, otherwise rp2040)
3. Runs the PinmapGen CLI on each file, writing to a temporary directory
4. Blocks the commit if any generation run fails

This ensures broken or malformed netlists are caught before they reach the repository.

## Testing the Hook

To test that the hook is working:

1. Make a small change to `hardware/exports/sample_netlist.csv`
2. Stage the change: `git add hardware/exports/sample_netlist.csv`
3. Try to commit: `git commit -m "test hook"`
4. You should see the hook validate the netlist (and block the commit if you made it invalid)

## Bypassing the Hook

If you need to commit without running the hook (not recommended):

```bash
git commit --no-verify -m "commit message"
```

## Troubleshooting

**Hook not running:**
- Verify the hook file exists in `.git/hooks/`
- Ensure it's executable: `chmod +x .git/hooks/pre-commit`
- Check that Python is available in your PATH

**Permission errors on Windows:**
- Try running your shell as administrator
- Use the PowerShell version instead of bash version

**Python not found:**
- Ensure Python is installed and available in PATH
- The hook requires the PinmapGen modules to be available