[CmdletBinding()]
param([string]$TailscalePath = 'C:\Program Files\Tailscale\tailscale.exe')

$ErrorActionPreference = 'Stop'
$json = & $TailscalePath funnel status --json
if ($LASTEXITCODE -ne 0) { throw 'Unable to read Funnel status.' }
$status = $json | ConvertFrom-Json
$text = $json | Out-String
$match = [regex]::Match($text, 'https://[^"\\\s]+\.ts\.net')
if (-not $match.Success) { throw 'No public Funnel HTTPS URL is configured.' }
Write-Output $match.Value
