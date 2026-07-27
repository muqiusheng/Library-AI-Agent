[CmdletBinding()]
param(
    [switch]$KeepFunnel,
    [string]$DockerPath = 'C:\Users\lenovo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe',
    [string]$TailscalePath = 'C:\Program Files\Tailscale\tailscale.exe'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$compose = Join-Path $root 'docker-compose.home.yml'

if (-not $KeepFunnel -and (Test-Path -LiteralPath $TailscalePath)) {
    & $TailscalePath funnel --https=443 off
}
& $DockerPath compose -f $compose down
if ($LASTEXITCODE -ne 0) { throw 'Docker Compose shutdown failed.' }
Write-Host 'BookPath containers stopped. Persistent volumes were preserved.'
