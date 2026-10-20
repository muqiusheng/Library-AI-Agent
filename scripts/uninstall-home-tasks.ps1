[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Get-ScheduledTask -TaskName 'BookPath-Home-*' -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false
Write-Host 'BookPath scheduled tasks removed.'
