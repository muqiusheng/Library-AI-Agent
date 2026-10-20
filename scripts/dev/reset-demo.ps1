$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $Root
& .\.venv\Scripts\python.exe -m app.cli reset-demo
Write-Host "Demo activity reset. Library data, indexes and accounts were preserved."
