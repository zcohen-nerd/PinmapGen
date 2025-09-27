# PinmapGen Pre-commit Hook (PowerShell Version)
#
# This hook automatically regenerates pinmap files when source files change.
# It ensures that generated outputs stay in sync with input files.

Write-Host "🔧 PinmapGen pre-commit hook running..." -ForegroundColor Cyan

# Check if we have any changes in hardware/exports/
$hardwareChanged = git diff --cached --name-only | Where-Object { $_ -match '^hardware/exports/' }

if ($hardwareChanged) {
    Write-Host "📁 Hardware export files changed:" -ForegroundColor Yellow
    $hardwareChanged | ForEach-Object { Write-Host "   $_" }
    
    # Check if we have Python available
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        Write-Host "🔄 Regenerating pinmaps..." -ForegroundColor Green
        
        # Find CSV files in hardware/exports/
        $csvFiles = Get-ChildItem -Path "hardware/exports/" -Filter "*.csv" -Recurse -ErrorAction SilentlyContinue
        
        if ($csvFiles) {
            foreach ($csvFile in $csvFiles) {
                Write-Host "📋 Processing $($csvFile.FullName)..." -ForegroundColor Yellow
                
                # Detect MCU type from filename or default to rp2040
                $mcuType = "rp2040"
                if ($csvFile.Name -match "stm32") {
                    $mcuType = "stm32g0"
                } elseif ($csvFile.Name -match "esp32") {
                    $mcuType = "esp32"
                }
                
                Write-Host "🔍 Detected MCU type: $mcuType" -ForegroundColor Cyan
                
                try {
                    # Run the generator
                    $result = python -m tools.pinmapgen.cli `
                        --csv $csvFile.FullName `
                        --mcu $mcuType `
                        --mcu-ref U1 `
                        --out-root . `
                        --mermaid
                    
                    if ($LASTEXITCODE -eq 0) {
                        Write-Host "✅ Generated pinmaps for $($csvFile.Name)" -ForegroundColor Green
                    } else {
                        Write-Error "❌ Failed to generate pinmaps for $($csvFile.Name)"
                        exit 1
                    }
                } catch {
                    Write-Error "❌ Error processing $($csvFile.Name): $_"
                    exit 1
                }
            }
            
            # Stage the regenerated files
            Write-Host "📤 Staging regenerated pinmap files..." -ForegroundColor Cyan
            git add pinmaps/
            git add firmware/micropython/
            git add firmware/include/
            git add firmware/docs/
            
            Write-Host "✅ Pinmaps regenerated and staged successfully!" -ForegroundColor Green
        } else {
            Write-Warning "⚠️  No CSV files found in hardware/exports/"
        }
    } else {
        Write-Error "❌ Python not found! Please install Python to use auto-regeneration."
        Write-Host "   You can manually regenerate with:" -ForegroundColor Yellow
        Write-Host "   python -m tools.pinmapgen.cli --csv hardware/exports/sample_netlist.csv --mcu rp2040 --mcu-ref U1 --out-root . --mermaid" -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "📋 No hardware export changes detected, skipping regeneration." -ForegroundColor Gray
}

Write-Host "🎉 Pre-commit hook completed successfully!" -ForegroundColor Green