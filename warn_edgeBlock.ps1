function Warn-EdgeBlock {
  [CmdletBinding()]
  param(
    [string]$Path = ".",
    [switch]$GitDiff
  )

  $pattern = "edge_all_open_tabs|User's Edge browser tabs metadata"
  $targets = @()

  if ($GitDiff) {
    if (-not (Test-Path .git)) {
      Write-Error "Kein Git-Repository gefunden. Entferne -GitDiff oder führe im Repo aus."
      return 2
    }
    # sichere Abfrage der gestageten Dateien, null-terminiert, dann filtern
    $raw = git diff --cached --name-only --diff-filter=ACM -z 2>$null
    if (-not $raw) { Write-Host "Keine gestageten Änderungen gefunden." -ForegroundColor Yellow; return 0 }
    $files = $raw -split "`0" | Where-Object { $_ -and (Test-Path $_) }
    $targets = $files
  } else {
    $targets = Get-ChildItem -Path $Path -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName }
  }

  $found = $false
  foreach ($f in $targets) {
    try {
      $matches = Select-String -Path $f -Pattern $pattern -SimpleMatch -ErrorAction SilentlyContinue
      if ($matches) {
        $found = $true
        Write-Host "`n=== Fund in: $f ===" -ForegroundColor Red
        foreach ($m in $matches) {
          $ln = $m.LineNumber
          $contextStart = [Math]::Max(1, $ln - 2)
          $contextEnd = [Math]::Min((Get-Content $f).Count, $ln + 2)
          $lines = Get-Content -Path $f -ErrorAction SilentlyContinue
          for ($i = $contextStart; $i -le $contextEnd; $i++) {
            $prefix = if ($i -eq $ln) { ">>" } else { "  " }
            Write-Host ("{0,4}: {1} {2}" -f $i, $prefix, $lines[$i-1])
          }
        }
      }
    } catch {
      Write-Host "Fehler beim Lesen von $f : $_" -ForegroundColor Yellow
    }
  }

  if ($found) {
    Write-Host "`nWarnung: Mindestens eine Datei enthält den Edge‑Block. Entferne ihn vor Commit/Deployment." -ForegroundColor Red
    return 1
  } else {
    Write-Host "Keine Edge‑Blöcke gefunden." -ForegroundColor Green
    return 0
  }
}
