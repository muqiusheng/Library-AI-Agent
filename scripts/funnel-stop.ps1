[CmdletBinding()]
param([string]$TailscalePath = 'C:\Program Files\Tailscale\tailscale.exe')

$ErrorActionPreference = 'Stop'
& $TailscalePath funnel --https=443 off
if ($LASTEXITCODE -ne 0) { throw 'Funnel shutdown failed.' }
& $TailscalePath funnel status
