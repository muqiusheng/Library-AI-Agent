[CmdletBinding()]
param(
    [int]$Port = 8180,
    [string]$DockerPath = 'C:\Users\lenovo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe',
    [string]$TailscalePath = 'C:\Program Files\Tailscale\tailscale.exe'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$compose = Join-Path $root 'docker-compose.home.yml'
$logRoot = Join-Path $root 'data\home-ops'
$statePath = Join-Path $logRoot 'health-state.json'
$logPath = Join-Path $logRoot 'health.log'
New-Item -ItemType Directory -Force -Path $logRoot | Out-Null

function Write-HealthLog([string]$Level, [string]$Text) {
    Add-Content -LiteralPath $logPath -Value "$(Get-Date -Format o) [$Level] $Text" -Encoding utf8
}

$state = @{ consecutive_failures = 0 }
if (Test-Path -LiteralPath $statePath) {
    try { $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json }
    catch { Write-HealthLog 'WARN' 'Unable to parse previous health state.' }
}

$driveName = [IO.Path]::GetPathRoot($root).Substring(0, 1)
$drive = Get-PSDrive -Name $driveName
$freePercent = [math]::Round(($drive.Free / ($drive.Used + $drive.Free)) * 100, 1)
if ($freePercent -lt 30) { Write-HealthLog 'ALERT' "Disk free space is $freePercent percent." }

$latestBackup = Get-ChildItem -LiteralPath (Join-Path $root 'data\backups\daily') -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending | Select-Object -First 1
if (-not $latestBackup -or $latestBackup.LastWriteTime -lt (Get-Date).AddHours(-36)) {
    Write-HealthLog 'ALERT' 'No successful daily backup within 36 hours.'
}

$healthy = $false
try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 10
    $healthy = $health.data.status -eq 'ok'
}
catch { $healthy = $false }

if ($healthy) {
    $state.consecutive_failures = 0
    Write-HealthLog 'OK' 'Local health check passed.'
}
else {
    $state.consecutive_failures = [int]$state.consecutive_failures + 1
    Write-HealthLog 'ERROR' "Local health check failed ($($state.consecutive_failures)/3)."
    if ($state.consecutive_failures -lt 3) {
        & $DockerPath compose -f $compose up -d
        Write-HealthLog 'WARN' 'Requested Compose recovery.'
    }
    else {
        Write-HealthLog 'ALERT' 'Three consecutive failures; automatic restarts stopped.'
    }
}

if (Test-Path -LiteralPath $TailscalePath) {
    $funnel = (& $TailscalePath funnel status --json 2>$null) -join "`n"
    if ($funnel -and $funnel -notmatch '8180') {
        Write-HealthLog 'WARN' 'Funnel target is missing or unexpected.'
    }
}

$state | ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding utf8
if (-not $healthy) { exit 1 }
