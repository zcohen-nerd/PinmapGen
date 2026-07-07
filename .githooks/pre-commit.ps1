# PinmapGen Pre-commit Hook (PowerShell Version)
#
# Validates staged netlist exports by running the generator against them in
# a temporary directory. The commit is blocked if generation fails, so broken
# netlists never land. Nothing is staged automatically - the root-level
# pinmaps/ and firmware/ outputs are gitignored scratch artifacts.

Write-Host "PinmapGen pre-commit hook running..." -ForegroundColor Cyan

# Collect staged CSV netlists under hardware/exports/
$changedCsvs = git diff --cached --name-only --diff-filter=ACM |
    Where-Object { $_ -match '^hardware/exports/.*\.csv$' }

if (-not $changedCsvs) {
    Write-Host "No netlist changes detected, skipping validation." -ForegroundColor Gray
    exit 0
}

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Error "Python not found - cannot validate netlists. Install Python or commit with --no-verify to skip."
    exit 1
}

$tmpOut = Join-Path ([System.IO.Path]::GetTempPath()) ("pinmapgen_hook_" + [System.Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tmpOut | Out-Null

$failed = $false
try {
    foreach ($csvFile in $changedCsvs) {
        Write-Host "Validating $csvFile..." -ForegroundColor Yellow

        # Detect MCU type from filename or default to rp2040
        $mcuType = "rp2040"
        if ($csvFile -match "stm32") { $mcuType = "stm32g0" }
        elseif ($csvFile -match "esp32s3") { $mcuType = "esp32s3" }
        elseif ($csvFile -match "esp32c3") { $mcuType = "esp32c3" }
        elseif ($csvFile -match "esp32") { $mcuType = "esp32" }
        elseif ($csvFile -match "nrf52") { $mcuType = "nrf52840" }

        $outDir = Join-Path $tmpOut ([System.IO.Path]::GetFileNameWithoutExtension($csvFile))
        python -m tools.pinmapgen.cli `
            --csv $csvFile `
            --mcu $mcuType `
            --mcu-ref U1 `
            --out-root $outDir `
            --mermaid

        if ($LASTEXITCODE -eq 0) {
            Write-Host "  OK ($mcuType)" -ForegroundColor Green
        } else {
            Write-Host "  FAILED ($mcuType) - fix the netlist or run the CLI manually to debug" -ForegroundColor Red
            $failed = $true
        }
    }
} finally {
    Remove-Item -Recurse -Force $tmpOut -ErrorAction SilentlyContinue
}

if ($failed) {
    Write-Host "Pre-commit validation failed. Commit aborted." -ForegroundColor Red
    exit 1
}

Write-Host "All changed netlists generate cleanly." -ForegroundColor Green
