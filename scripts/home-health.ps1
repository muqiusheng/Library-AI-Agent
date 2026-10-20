[CmdletBinding()]
param(
    [int]$Port = 8180,
    [string]$DockerPath = 'C:\Users\lenovo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe',
    [string]$TailscalePath = 'C:\Program Files\Tailscale\tailscale.exe'
)

# Compatibility entry point for existing Windows scheduled tasks.
$ErrorActionPreference = 'Stop'
$global:LASTEXITCODE = 0
& (Join-Path $PSScriptRoot 'home/home-health.ps1') @PSBoundParameters
exit $LASTEXITCODE
