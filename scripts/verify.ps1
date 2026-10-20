$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
& .\.venv\Scripts\python.exe -m pytest app\tests -q
& .\.venv\Scripts\ruff.exe check app
Push-Location frontend
npm.cmd run test
npm.cmd run build
Pop-Location
Write-Host "BookPath verification passed."
