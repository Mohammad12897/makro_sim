#!/usr/bin/env pwsh
$pattern = "edge_all_open_tabs|User's Edge browser tabs metadata"
$files = git diff --cached --name-only --diff-filter=ACM
if (-not $files) { exit 0 }

$bad = $false
foreach ($f in $files) {
  if (Test-Path $f) {
    $m = Select-String -Path $f -Pattern $pattern -SimpleMatch -ErrorAction SilentlyContinue
    if ($m) {
      Write-Host "ERROR: Commit enthält Edge browser metadata in $f" -ForegroundColor Red
      $m | ForEach-Object { Write-Host "  $($_.LineNumber): $($_.Line.Trim())" }
      $bad = $true
    }
  }
}

if ($bad) {
  Write-Host "Commit abgebrochen. Entferne die Metadaten und versuche erneut." -ForegroundColor Red
  exit 1
}
exit 0
