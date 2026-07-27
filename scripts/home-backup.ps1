[CmdletBinding()]
param(
    [string]$OffsitePath = '',
    [string]$DockerPath = 'C:\Users\lenovo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$compose = Join-Path $root 'docker-compose.home.yml'
$operationLogRoot = Join-Path $root 'data\home-ops'
New-Item -ItemType Directory -Force -Path $operationLogRoot | Out-Null
$operationLog = Join-Path $operationLogRoot 'backup.log'
trap {
    Add-Content -LiteralPath $operationLog -Value "$(Get-Date -Format o) [ERROR] $($_.Exception.Message)" -Encoding utf8
    exit 1
}
Add-Content -LiteralPath $operationLog -Value "$(Get-Date -Format o) [START] Backup started." -Encoding utf8
$backupRoot = Join-Path $root 'data\backups'
$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$dailyRoot = Join-Path $backupRoot 'daily'
$weeklyRoot = Join-Path $backupRoot 'weekly'
$destination = Join-Path $dailyRoot $timestamp

New-Item -ItemType Directory -Force -Path $destination | Out-Null
New-Item -ItemType Directory -Force -Path $weeklyRoot | Out-Null

$postgresId = (& $DockerPath compose -f $compose ps -q postgres).Trim()
$backendId = (& $DockerPath compose -f $compose ps -q backend).Trim()
if (-not $postgresId -or -not $backendId) { throw 'Production containers are not running.' }

try {
    & $DockerPath compose -f $compose exec -T postgres sh -lc 'pg_dump --format=custom --compress=9 --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --file=/tmp/bookpath.dump'
    if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL dump failed.' }
    & $DockerPath cp "${postgresId}:/tmp/bookpath.dump" (Join-Path $destination 'postgres.dump')
    if ($LASTEXITCODE -ne 0) { throw 'Unable to copy PostgreSQL dump.' }

    & $DockerPath compose -f $compose exec -T backend sh -lc 'tar -czf /tmp/uploads.tar.gz -C /app/data uploads'
    if ($LASTEXITCODE -ne 0) { throw 'Uploads archive failed.' }
    & $DockerPath cp "${backendId}:/tmp/uploads.tar.gz" (Join-Path $destination 'uploads.tar.gz')
    if ($LASTEXITCODE -ne 0) { throw 'Unable to copy uploads archive.' }

    $alembic = (& $DockerPath compose -f $compose exec -T backend .venv/bin/alembic current) -join "`n"
    $metadata = [ordered]@{
        created_at = (Get-Date).ToString('o')
        git_commit = (& git -C $root rev-parse HEAD).Trim()
        alembic = $alembic.Trim()
        compose_file = 'docker-compose.home.yml'
        includes_secrets = $false
    }
    $metadata | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $destination 'metadata.json') -Encoding utf8
}
finally {
    & $DockerPath compose -f $compose exec -T postgres rm -f /tmp/bookpath.dump 2>$null
    & $DockerPath compose -f $compose exec -T backend rm -f /tmp/uploads.tar.gz 2>$null
}

function Remove-OldBackups([string]$Path, [int]$Keep) {
    $resolvedRoot = [IO.Path]::GetFullPath($Path).TrimEnd('\')
    $old = Get-ChildItem -LiteralPath $resolvedRoot -Directory | Sort-Object Name -Descending | Select-Object -Skip $Keep
    foreach ($item in $old) {
        $resolvedItem = [IO.Path]::GetFullPath($item.FullName)
        if (-not $resolvedItem.StartsWith($resolvedRoot + '\', [StringComparison]::OrdinalIgnoreCase)) {
            throw "Unsafe backup retention target: $resolvedItem"
        }
        Remove-Item -LiteralPath $resolvedItem -Recurse -Force
    }
}

function Copy-BackupFiles([string]$Source, [string]$Target) {
    New-Item -ItemType Directory -Force -Path $Target | Out-Null
    Start-Sleep -Seconds 2
    Get-ChildItem -LiteralPath $Source -File | ForEach-Object {
        $targetFile = Join-Path $Target $_.Name
        $copied = $false
        for ($attempt = 1; $attempt -le 5; $attempt++) {
            try {
                Copy-Item -LiteralPath $_.FullName -Destination $targetFile -Force
                $copied = $true
                break
            }
            catch {
                if ($attempt -eq 5) { throw }
                Start-Sleep -Seconds 2
            }
        }
        if (-not $copied) { throw "Unable to copy backup file: $($_.Name)" }
    }
}

Remove-OldBackups $dailyRoot 3
$weeklyNeeded = (Get-Date).DayOfWeek -eq 'Sunday' -or -not (Get-ChildItem -LiteralPath $weeklyRoot -Directory)
if ($weeklyNeeded) {
    Copy-BackupFiles $destination (Join-Path $weeklyRoot $timestamp)
}
Remove-OldBackups $weeklyRoot 2

if ($OffsitePath) {
    if (-not (Test-Path -LiteralPath $OffsitePath)) {
        throw "Offsite backup directory is unavailable: $OffsitePath"
    }
    function Copy-OffsiteSet([string]$Prefix) {
        foreach ($name in @('postgres.dump', 'uploads.tar.gz', 'metadata.json')) {
            $sourceFile = Join-Path $destination $name
            $targetFile = Join-Path $OffsitePath "$Prefix-$name"
            $copied = $false
            for ($attempt = 1; $attempt -le 5; $attempt++) {
                try {
                    Copy-Item -LiteralPath $sourceFile -Destination $targetFile -Force
                    $copied = $true
                    break
                }
                catch {
                    if ($attempt -eq 5) { throw }
                    Start-Sleep -Seconds 2
                }
            }
            if (-not $copied) { throw "Unable to copy offsite file: $name" }
        }
    }
    function Remove-OldOffsiteSets([string]$Kind, [int]$Keep) {
        $metadataFiles = Get-ChildItem -LiteralPath $OffsitePath -File -Filter "$Kind-*-metadata.json" | Sort-Object Name -Descending | Select-Object -Skip $Keep
        foreach ($metadataFile in $metadataFiles) {
            $setPrefix = $metadataFile.Name.Substring(0, $metadataFile.Name.Length - '-metadata.json'.Length)
            Get-ChildItem -LiteralPath $OffsitePath -File -Filter "$setPrefix-*" | Remove-Item -Force
        }
    }
    Copy-OffsiteSet "daily-$timestamp"
    if ($weeklyNeeded) { Copy-OffsiteSet "weekly-$timestamp" }
    Remove-OldOffsiteSets 'daily' 3
    Remove-OldOffsiteSets 'weekly' 2
}

Write-Host "Backup completed: $destination"
Add-Content -LiteralPath $operationLog -Value "$(Get-Date -Format o) [OK] Backup completed: $destination" -Encoding utf8
