[CmdletBinding()]
param(
    [switch]$SkipFunnel,
    [int]$Port = 8180,
    [string]$DockerPath = 'C:\Users\lenovo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe',
    [string]$DockerDesktopPath = 'C:\Users\lenovo\AppData\Local\Programs\DockerDesktop\Docker Desktop.exe',
    [string]$TailscalePath = 'C:\Program Files\Tailscale\tailscale.exe'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$compose = Join-Path $root 'docker-compose.home.yml'

if (-not (Test-Path -LiteralPath $DockerPath)) { throw "Docker CLI not found: $DockerPath" }

function Test-DockerEngine {
    # `docker info` writes a connection error to stderr while Docker Desktop is
    # still starting. With ErrorActionPreference=Stop, PowerShell otherwise
    # turns that expected native stderr output into a terminating error before
    # this script gets a chance to launch Docker Desktop and retry.
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'SilentlyContinue'
        & $DockerPath info *> $null
        return $LASTEXITCODE -eq 0
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }
}

$dockerReady = Test-DockerEngine
if (-not $dockerReady -and (Test-Path -LiteralPath $DockerDesktopPath)) {
    Start-Process -FilePath $DockerDesktopPath -WindowStyle Hidden
    for ($attempt = 1; $attempt -le 60; $attempt++) {
        Start-Sleep -Seconds 3
        if (Test-DockerEngine) {
            $dockerReady = $true
            break
        }
    }
}
if (-not $dockerReady) { throw 'Docker Desktop engine is not ready.' }

& $DockerPath compose -f $compose up -d
if ($LASTEXITCODE -ne 0) { throw 'Docker Compose startup failed.' }

$healthUrl = "http://127.0.0.1:$Port/health"
$healthy = $false
for ($attempt = 1; $attempt -le 30; $attempt++) {
    try {
        $health = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 5
        if ($health.data.status -eq 'ok') { $healthy = $true; break }
    }
    catch { Start-Sleep -Seconds 2 }
}
if (-not $healthy) { throw "Health check failed: $healthUrl" }

if (-not $SkipFunnel) {
    if (-not (Test-Path -LiteralPath $TailscalePath)) { throw "Tailscale CLI not found: $TailscalePath" }
    & $TailscalePath funnel --bg $healthUrl.Replace('/health', '')
    if ($LASTEXITCODE -ne 0) { throw 'Tailscale Funnel startup failed.' }
}

Write-Host "BookPath is healthy at http://127.0.0.1:$Port"
