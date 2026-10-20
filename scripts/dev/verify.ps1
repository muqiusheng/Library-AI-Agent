$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $Root
& .\.venv\Scripts\python.exe -m pytest tests -q
& .\.venv\Scripts\ruff.exe check app tests
Push-Location frontend
npm.cmd run test
npm.cmd run build
Pop-Location
Write-Host "BookPath verification passed."
