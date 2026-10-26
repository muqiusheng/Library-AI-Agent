[CmdletBinding()]
param(
    [ValidateSet('Auto', 'Local', 'Home')]
    [string]$Mode = 'Auto',
    [string]$StudentNo = 'admin',
    [string]$DockerPath = ''
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

try {
    $StudentNo = $StudentNo.Trim()
    if (-not $StudentNo -or $StudentNo.Length -gt 64) {
        throw 'Specify an existing super-admin username with -StudentNo (1-64 characters).'
    }
    if ($Mode -eq 'Auto') {
        $Mode = if (Test-Path -LiteralPath (Join-Path $root '.env.home')) { 'Home' } else { 'Local' }
    }
    $isHome = $Mode -eq 'Home'
    $composeFile = if ($isHome) { 'docker-compose.home.yml' } else { 'docker-compose.yml' }
    $envFile = if ($isHome) { '.env.home' } else { '.env' }
    $envPath = Join-Path $root $envFile
    if (-not (Test-Path -LiteralPath $envPath)) {
        throw "$envFile is missing. Start the intended deployment with start.cmd first."
    }
    if (-not $DockerPath) {
        $command = Get-Command docker -CommandType Application -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($command) { $DockerPath = $command.Source }
        else {
            $DockerPath = @(
                "$env:ProgramFiles\Docker\Docker\resources\bin\docker.exe",
                "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin\docker.exe",
                "$env:LOCALAPPDATA\Docker\resources\bin\docker.exe"
            ) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
        }
    }
    if (-not $DockerPath -or -not (Test-Path -LiteralPath $DockerPath)) {
        throw 'Docker was not found. Install and start Docker Desktop first.'
    }

    Write-Host "Password recovery ($Mode), super-admin: $StudentNo"
    Write-Host 'Only the selected account password will change. Enter your new password twice below.'
    # Send code, not secrets. Base64 avoids Windows PowerShell native-argument quoting issues.
    # Existing backend images already contain the required app modules; no rebuild is needed.
    $source = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'reset_admin_password.py') -Raw -Encoding utf8
    $payload = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($source))
    $runner = "import base64; exec(base64.b64decode('$payload'))"
    $composeOptions = @('compose', '--project-directory', $root, '--env-file', $envPath,
        '-f', (Join-Path $root $composeFile))
    # Keep Compose's interactive TTY so getpass never needs a visible-input fallback.
    & $DockerPath @composeOptions exec backend .venv/bin/python -c $runner -- $StudentNo
    if ($LASTEXITCODE -ne 0) {
        throw 'Password reset failed or was cancelled. Check the message above; ensure the backend is running.'
    }
}
catch {
    Write-Host "BookPath: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
