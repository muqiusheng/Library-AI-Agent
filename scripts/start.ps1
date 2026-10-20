$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

docker compose up -d postgres
& .\.venv\Scripts\python.exe -m alembic upgrade head

$backend = Start-Process -FilePath ".\.venv\Scripts\python.exe" `
  -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" `
  -WorkingDirectory $Root -WindowStyle Hidden -PassThru
$frontend = Start-Process -FilePath "npm.cmd" `
  -ArgumentList "run", "dev", "--", "--host", "127.0.0.1", "--port", "4173", "--strictPort" `
  -WorkingDirectory (Join-Path $Root "frontend") -WindowStyle Hidden -PassThru

@($backend.Id, $frontend.Id) | Set-Content (Join-Path $Root ".bookpath-pids")
Write-Host "BookPath started: http://localhost:4173 (API http://localhost:8000)"
