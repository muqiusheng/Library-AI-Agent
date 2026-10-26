[CmdletBinding()]
param(
    [ValidateSet('Start', 'Stop')]
    [string]$Action = 'Start',
    [ValidateSet('Auto', 'Local', 'Home')]
    [string]$Mode = 'Auto',
    [switch]$Rebuild,
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

function Find-Docker {
    $command = Get-Command docker -CommandType Application -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($command) { return $command.Source }
    foreach ($candidate in @(
        "$env:ProgramFiles\Docker\Docker\resources\bin\docker.exe",
        "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin\docker.exe",
        "$env:LOCALAPPDATA\Docker\resources\bin\docker.exe"
    )) {
        if (Test-Path -LiteralPath $candidate) { return $candidate }
    }
    throw 'Docker was not found. Install Docker Desktop, then double-click start.cmd again.'
}

function Test-DockerEngine {
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'SilentlyContinue'
        & $dockerPath info *> $null
        return $LASTEXITCODE -eq 0
    }
    finally { $ErrorActionPreference = $previousPreference }
}

function Invoke-Compose([string[]]$ComposeArguments) {
    & $dockerPath @composeOptions @ComposeArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose failed (exit $LASTEXITCODE). See the output above."
    }
}

try {
    if ($Mode -eq 'Auto') {
        $Mode = if (Test-Path -LiteralPath (Join-Path $root '.env.home')) { 'Home' } else { 'Local' }
    }
    $isHome = $Mode -eq 'Home'
    $composeFile = if ($isHome) { 'docker-compose.home.yml' } else { 'docker-compose.yml' }
    $envFile = if ($isHome) { '.env.home' } else { '.env' }
    $envPath = Join-Path $root $envFile
    $siteUrl = if ($isHome) { 'http://127.0.0.1:8180' } else { 'http://localhost:4173' }
    $healthUrl = if ($isHome) { "$siteUrl/health" } else { 'http://localhost:8000/health' }
    Write-Host "BookPath $Action ($Mode): $siteUrl"

    $dockerPath = Find-Docker
    & $dockerPath compose version
    if ($LASTEXITCODE -ne 0) { throw 'Docker Compose v2 is required. Update Docker Desktop.' }
    if (-not (Test-DockerEngine)) {
        if ($Action -eq 'Stop') { throw 'Docker is not running; services may already be stopped.' }
        $desktop = @(
            "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe",
            "$env:LOCALAPPDATA\Programs\DockerDesktop\Docker Desktop.exe",
            "$env:LOCALAPPDATA\Docker\Docker Desktop.exe"
        ) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
        if (-not $desktop) { throw 'Start Docker Desktop and retry.' }
        Start-Process -FilePath $desktop -WindowStyle Hidden
        Write-Host 'Waiting for Docker Desktop...'
        $deadline = (Get-Date).AddMinutes(3)
        while (-not (Test-DockerEngine)) {
            if ((Get-Date) -ge $deadline) { throw 'Docker did not become ready. Check Docker Desktop.' }
            Start-Sleep -Seconds 2
        }
    }

    if (-not (Test-Path -LiteralPath $envPath)) {
        if ($Action -eq 'Stop') { throw "$envFile is missing. Check -Mode Local or -Mode Home." }
        if ($isHome) {
            & (Join-Path $PSScriptRoot 'home\init-home-env.ps1')
        }
        else {
            Copy-Item -LiteralPath (Join-Path $root '.env.example') -Destination $envPath
        }
        Write-Host "Created $envFile. Existing configuration files are always preserved."
    }

    # Keep the original Compose project names and volumes, regardless of the working directory.
    $composeOptions = @('compose', '--project-directory', $root, '--env-file', $envPath,
        '-f', (Join-Path $root $composeFile))
    if ($Action -eq 'Stop') {
        Invoke-Compose -ComposeArguments @('stop')
        Write-Host 'Stopped. All accounts, library data and volumes were preserved.'
        exit 0
    }

    $upArguments = @('up', '-d')
    if ($Rebuild) { $upArguments += '--build' }
    Write-Host 'Starting services. The first run downloads and builds images; this may take several minutes.'
    Invoke-Compose -ComposeArguments $upArguments
    Write-Host 'Waiting for the API and web page...'
    $ready = $false
    $deadline = (Get-Date).AddMinutes(3)
    while ((Get-Date) -lt $deadline) {
        try {
            $health = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 5
            $page = Invoke-WebRequest -Uri $siteUrl -UseBasicParsing -TimeoutSec 5
            if ($health.data.status -eq 'ok' -and $page.StatusCode -eq 200) {
                $ready = $true
                break
            }
        }
        catch { }
        Start-Sleep -Seconds 2
    }
    if (-not $ready) {
        Invoke-Compose -ComposeArguments @('logs', '--tail', '60')
        throw 'Services did not become ready. Check the logs above, then run start.cmd again.'
    }
    Write-Host "Ready: $siteUrl"
    Write-Host "For a NEW empty database, initial credentials are in $envFile (BOOTSTRAP_ADMIN_*)."
    Write-Host 'Existing accounts keep their current passwords. See docs/deployment/QUICK_START.md.'
    if (-not $NoBrowser) { Start-Process $siteUrl }
}
catch {
    Write-Host "BookPath: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
