#!/bin/bash
#
# Setup Git Hooks for PinmapGen
#
# This script installs the pre-commit hook to automatically regenerate
# pinmap files when hardware exports change.

echo "🔧 Setting up PinmapGen git hooks..."

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ Not in a git repository!"
    exit 1
fi

# Get the git hooks directory
HOOKS_DIR=$(git rev-parse --git-dir)/hooks

# Copy the pre-commit hook
echo "📋 Installing pre-commit hook..."
cp .githooks/pre-commit "$HOOKS_DIR/pre-commit"

# Make it executable
chmod +x "$HOOKS_DIR/pre-commit"

# Set the hooks directory (in case it's not the default)
git config core.hooksPath "$HOOKS_DIR"

echo "✅ Pre-commit hook installed successfully!"
echo ""
echo "The hook will now automatically regenerate pinmap files when you commit"
echo "changes to files in the hardware/exports/ directory."
echo ""
echo "To test the hook, try:"
echo "  1. Make a change to hardware/exports/sample_netlist.csv"
echo "  2. git add hardware/exports/sample_netlist.csv" 
echo "  3. git commit -m 'test hook'"
echo ""
echo "You should see the hook regenerate and stage the pinmap files automatically."