[CmdletBinding()]
param([string]$OffsitePath = '')

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$powershell = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$user = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 2 -RestartInterval (New-TimeSpan -Minutes 2) -ExecutionTimeLimit (New-TimeSpan -Hours 2)

function Install-BookPathTask([string]$Name, $Trigger, [string]$Script, [string]$ExtraArguments = '') {
    $scriptPath = Join-Path $PSScriptRoot $Script
    # Scheduled tasks use an interactive logon so they can access the user's
    # Docker Desktop session. Hide the console window to avoid a PowerShell
    # window flashing every time a recurring task runs.
    $arguments = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$scriptPath`" $ExtraArguments".Trim()
    $action = New-ScheduledTaskAction -Execute $powershell -Argument $arguments -WorkingDirectory $root
    Register-ScheduledTask -TaskName $Name -Action $action -Trigger $Trigger -Principal $principal -Settings $settings -Force | Out-Null
}

$startupTrigger = New-ScheduledTaskTrigger -AtLogOn -User $user
$healthTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) -RepetitionInterval (New-TimeSpan -Minutes 5)
$backupTrigger = New-ScheduledTaskTrigger -Daily -At '03:00'

Install-BookPathTask 'BookPath-Home-Start' $startupTrigger 'home-start.ps1'
Install-BookPathTask 'BookPath-Home-Health' $healthTrigger 'home-health.ps1'
$backupArguments = if ($OffsitePath) { "-OffsitePath `"$OffsitePath`"" } else { '' }
Install-BookPathTask 'BookPath-Home-Backup' $backupTrigger 'home-backup.ps1' $backupArguments

Get-ScheduledTask -TaskName 'BookPath-Home-*' | Select-Object TaskName,State
