# defekte Datei entfernen (falls vorhanden)
Remove-Item .\remove_edge_block.ps1 -Force -ErrorAction SilentlyContinue

# neue, saubere Version anlegen (kopiere die ganze Zeile und Enter)
'@ 
<#
remove_edge_block.ps1
Sucht nach "edge_all_open_tabs" in Dateien, zeigt Fundstellen (DryRun) und entfernt optional den Block.
Usage:
  .\remove_edge_block.ps1          # Dry run
  .\remove_edge_block.ps1 -Execute # Änderungen durchführen
#>

param([switch]$Execute)

$projectRoot = Get-Location
$pattern = "edge_all_open_tabs"
$backupRoot = Join-Path $projectRoot "tmp_backup_$(Get-Date -Format ''yyyyMMdd_HHmmss'')"

Write-Host "Projektverzeichnis:" $projectRoot
Write-Host "Suchmuster:" $pattern
Write-Host "DryRun (nur anzeigen) = " (-not $Execute)
if ($Execute) { Write-Host "=== AUSFÜHRUNGSMODUS: Änderungen werden durchgeführt ===" -ForegroundColor Yellow }

$matches = Get-ChildItem -Recurse -File -ErrorAction SilentlyContinue |
  Select-String -Pattern $pattern -SimpleMatch -List |
  Select-Object -ExpandProperty Path -Unique

if (-not $matches) {
  Write-Host "Keine Dateien mit ''$pattern'' gefunden." -ForegroundColor Green
  exit 0
}

Write-Host "`nGefundene Dateien:" -ForegroundColor Cyan
$matches | ForEach-Object { Write-Host " - $_" }

Write-Host "`n--- Fundstellen (Kontext) ---`n" -ForegroundColor Cyan
foreach ($f in $matches) {
  Write-Host "`nDatei: $f" -ForegroundColor Magenta
  Select-String -Path $f -Pattern $pattern -SimpleMatch | ForEach-Object {
    $ln = $_.LineNumber
    $start = [Math]::Max(1, $ln - 3)
    $end = $ln + 3
    Get-Content -Path $f | Select-Object -Index ($start-1..($end-1)) -ErrorAction SilentlyContinue |
      ForEach-Object -Begin { $i = $start } -Process {
        $prefix = if ($i -eq $ln) { ">>" } else { "  " }
        Write-Host ("{0,4}: {1} {2}" -f $i, $prefix, $_)
        $i++
      }
  }
}

if (-not $Execute) {
  Write-Host "`nDry run beendet. Um die Blöcke zu entfernen, führe das Skript mit -Execute aus." -ForegroundColor Yellow
  exit 0
}

New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
Write-Host "`nBackup-Ordner:" $backupRoot

$removedFiles = @()
foreach ($f in $matches) {
  try {
    $text = Get-Content -Path $f -Raw -ErrorAction Stop
    $patternRegex = '(?is)(#\s*User''s\s*Edge.*?edge_all_open_tabs\s*=\s*

\[.*?\]

.*?(\r?\n)?)'
    $new = [regex]::Replace($text, $patternRegex, '')
    if ($new -eq $text) {
      $patternRegex2 = '(?is)(edge_all_open_tabs\s*=\s*

\[.*?\]

.*?(\r?\n)?)'
      $new = [regex]::Replace($text, $patternRegex2, '')
    }
    if ($new -ne $text) {
      $dest = Join-Path $backupRoot (Split-Path $f -Leaf)
      Copy-Item -Path $f -Destination $dest -Force
      Set-Content -Path $f -Value $new -Encoding UTF8
      Write-Host "Bereinigt und gesichert:" $f -ForegroundColor Green
      $removedFiles += $f
    } else {
      Write-Host "Kein entfernbarer Block in:" $f -ForegroundColor DarkYellow
    }
  } catch {
    Write-Host "FEHLER beim Verarbeiten von $f :" $_.Exception.Message -ForegroundColor Red
  }
}

Write-Host "`nFertig. Dateien bereinigt:" -ForegroundColor Cyan
$removedFiles | ForEach-Object { Write-Host " - $_" }
Write-Host "`nBackups liegen in:" $backupRoot -ForegroundColor Cyan
'@ | Out-File -FilePath .\remove_edge_block.ps1 -Encoding utf8

