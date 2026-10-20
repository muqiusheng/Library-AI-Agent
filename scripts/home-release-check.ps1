[CmdletBinding()]
param(
    [string]$BaseUrl = 'http://127.0.0.1:8180',
    [string]$DockerPath = 'C:\Users\lenovo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$compose = Join-Path $root 'docker-compose.home.yml'
$python = Join-Path $root '.venv\Scripts\python.exe'

& $python -m ruff check app
if ($LASTEXITCODE -ne 0) { throw 'Ruff check failed.' }
& $python -m pytest
if ($LASTEXITCODE -ne 0) { throw 'Backend tests failed.' }
Push-Location (Join-Path $root 'frontend')
try {
    & npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
}
finally { Pop-Location }

& $DockerPath compose -f $compose config -q
if ($LASTEXITCODE -ne 0) { throw 'Compose validation failed.' }
$health = Invoke-RestMethod -Uri "$($BaseUrl.TrimEnd('/'))/health" -TimeoutSec 15
if ($health.data.status -ne 'ok') { throw 'Production health check failed.' }

$countsOutput = & $DockerPath compose -f $compose exec -T backend .venv/bin/python -c "from sqlalchemy import func,select; from app.db.models import Book,Holding,User,UserRole; from app.db.session import SessionLocal; s=SessionLocal(); print(str(s.scalar(select(func.count()).select_from(Book)) or 0)+','+str(s.scalar(select(func.count()).select_from(Holding)) or 0)+','+str(s.scalar(select(func.count()).select_from(User).where(User.role==UserRole.SUPER_ADMIN)) or 0)); s.close()"
$counts = (($countsOutput -join '').Trim() -split ',')
if ($counts.Count -ne 3 -or [int]$counts[0] -ne 41774 -or [int]$counts[1] -ne 113204 -or [int]$counts[2] -lt 1) {
    throw "Production count gate failed: $countsOutput"
}

$runtimeFiles = Get-ChildItem (Join-Path $root 'frontend\dist') -Recurse -File
$forbidden = $runtimeFiles | Select-String -SimpleMatch 'localhost:8000'
if ($forbidden) { throw "Forbidden production string found: $($forbidden[0].Path)" }
& git -C $root check-ignore -q .env.home
if ($LASTEXITCODE -ne 0) { throw '.env.home is not excluded from Git.' }

$releaseRoot = Join-Path $root 'data\releases'
New-Item -ItemType Directory -Force -Path $releaseRoot | Out-Null
$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$alembic = (& $DockerPath compose -f $compose exec -T backend .venv/bin/alembic current) -join "`n"
$record = [ordered]@{
    checked_at = (Get-Date).ToString('o')
    version = 'v1-home'
    git_commit = (& git -C $root rev-parse HEAD).Trim()
    alembic = $alembic.Trim()
    base_url = $BaseUrl
    books = [int]$counts[0]
    holdings = [int]$counts[1]
    super_admins = [int]$counts[2]
    result = 'passed'
}
$record | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $releaseRoot "release-$timestamp.json") -Encoding utf8
Write-Host 'Home production release check passed.'
