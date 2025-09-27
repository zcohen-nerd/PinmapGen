# Git Hooks for PinmapGen

This directory contains git hooks that help maintain the PinmapGen project by automatically regenerating pinmap files when source files change.

## Available Hooks

### Pre-commit Hook

The pre-commit hook automatically regenerates pinmap files when changes are detected in the `hardware/exports/` directory. This ensures that generated outputs always stay in sync with input files.

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

When you commit changes that include files in `hardware/exports/`:

1. The hook detects the changed files
2. Runs the PinmapGen CLI on any CSV files found
3. Regenerates all pinmap output files
4. Automatically stages the regenerated files to be included in the commit

This ensures that:
- Generated files are never out of sync with source data
- Code reviews include both source and generated changes
- Team members always have up-to-date pinmaps

## Testing the Hook

To test that the hook is working:

1. Make a small change to `hardware/exports/sample_netlist.csv`
2. Stage the change: `git add hardware/exports/sample_netlist.csv`
3. Try to commit: `git commit -m "test hook"`
4. You should see the hook run and regenerate the pinmap files automatically

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