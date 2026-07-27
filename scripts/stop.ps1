$Root = Split-Path -Parent $PSScriptRoot
$PidFile = Join-Path $Root ".bookpath-pids"
if (Test-Path $PidFile) {
  Get-Content $PidFile | ForEach-Object { Stop-Process -Id ([int]$_) -Force -ErrorAction SilentlyContinue }
  Remove-Item $PidFile -Force
}
Write-Host "BookPath application processes stopped. PostgreSQL remains running."
