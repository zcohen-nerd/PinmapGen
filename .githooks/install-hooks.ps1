# Setup Git Hooks for PinmapGen (PowerShell Version)
#
# This script installs the pre-commit hook to automatically regenerate
# pinmap files when hardware exports change.

Write-Host "🔧 Setting up PinmapGen git hooks..." -ForegroundColor Cyan

# Check if we're in a git repository
try {
    $gitDir = git rev-parse --git-dir 2>$null
    if (-not $gitDir) {
        throw "Not in git repo"
    }
} catch {
    Write-Error "❌ Not in a git repository!"
    exit 1
}

# Get the git hooks directory
$hooksDir = "$gitDir\hooks"

# Create hooks directory if it doesn't exist
if (-not (Test-Path $hooksDir)) {
    New-Item -ItemType Directory -Path $hooksDir -Force | Out-Null
}

# Copy the appropriate pre-commit hook for the platform
Write-Host "📋 Installing pre-commit hook..." -ForegroundColor Yellow

# On Windows, we prefer the PowerShell version but also install bash version for WSL/Git Bash users
$bashHook = Join-Path $hooksDir "pre-commit"
$psHook = Join-Path $hooksDir "pre-commit.ps1"

Copy-Item ".githooks\pre-commit" $bashHook -Force
Copy-Item ".githooks\pre-commit.ps1" $psHook -Force

# Create a wrapper script that detects the environment
$wrapperScript = @"
#!/bin/bash
# PinmapGen pre-commit hook wrapper
# Detects environment and runs appropriate hook

if command -v pwsh >/dev/null 2>&1; then
    # PowerShell Core available
    pwsh -File `$(dirname `$0)/pre-commit.ps1
elif command -v powershell >/dev/null 2>&1; then
    # Windows PowerShell available
    powershell -File `$(dirname `$0)/pre-commit.ps1
else
    # Fall back to bash version
    `$(dirname `$0)/pre-commit
fi
"@

Set-Content -Path $bashHook -Value $wrapperScript -Encoding UTF8

try {
    # Set executable permission (works in Git Bash/WSL)
    git update-index --chmod=+x $bashHook 2>$null
} catch {
    # Silently ignore permission errors on Windows
}

Write-Host "✅ Pre-commit hook installed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "The hook will now automatically regenerate pinmap files when you commit" -ForegroundColor Gray
Write-Host "changes to files in the hardware/exports/ directory." -ForegroundColor Gray
Write-Host ""
Write-Host "To test the hook, try:" -ForegroundColor Yellow
Write-Host "  1. Make a change to hardware/exports/sample_netlist.csv"
Write-Host "  2. git add hardware/exports/sample_netlist.csv"
Write-Host "  3. git commit -m 'test hook'"
Write-Host ""
Write-Host "You should see the hook regenerate and stage the pinmap files automatically." -ForegroundColor Green