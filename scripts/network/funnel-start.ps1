[CmdletBinding()]
param(
    [int]$Port = 8180,
    [string]$TailscalePath = 'C:\Program Files\Tailscale\tailscale.exe'
)

$ErrorActionPreference = 'Stop'
$target = "http://127.0.0.1:$Port"
$health = Invoke-RestMethod -Uri "$target/health" -TimeoutSec 10
if ($health.data.status -ne 'ok') { throw 'Local service is not healthy.' }
& $TailscalePath funnel --bg $target
if ($LASTEXITCODE -ne 0) { throw 'Funnel startup failed.' }
& $TailscalePath funnel status
