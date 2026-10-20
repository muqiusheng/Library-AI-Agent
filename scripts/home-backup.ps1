[CmdletBinding()]
param(
    [string]$OffsitePath = '',
    [string]$DockerPath = 'C:\Users\lenovo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe'
)

# Compatibility entry point for existing Windows scheduled tasks.
$ErrorActionPreference = 'Stop'
$global:LASTEXITCODE = 0
& (Join-Path $PSScriptRoot 'home/home-backup.ps1') @PSBoundParameters
exit $LASTEXITCODE
