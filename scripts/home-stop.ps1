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
    $funnelStatus = (& $TailscalePath funnel status --json 2>$null) -join ''
    if ($LASTEXITCODE -eq 0 -and $funnelStatus.Trim() -ne '{}') {
        & $TailscalePath funnel reset
        if ($LASTEXITCODE -ne 0) { throw 'Tailscale Funnel shutdown failed.' }
    }
}
& $DockerPath compose -f $compose down
if ($LASTEXITCODE -ne 0) { throw 'Docker Compose shutdown failed.' }
Write-Host 'BookPath containers stopped. Persistent volumes were preserved.'
