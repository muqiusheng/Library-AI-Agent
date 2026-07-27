[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$BackupDirectory,
    [string]$DockerPath = 'C:\Users\lenovo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$compose = Join-Path $root 'docker-compose.home.yml'
$dump = Join-Path $BackupDirectory 'postgres.dump'
if (-not (Test-Path -LiteralPath $dump)) { throw "Backup dump not found: $dump" }

Write-Warning 'This operation replaces data in the production database.'
$confirmation = Read-Host 'Type RESTORE-PRODUCTION to continue'
if ($confirmation -cne 'RESTORE-PRODUCTION') { throw 'Restore cancelled.' }

$postgresId = (& $DockerPath compose -f $compose ps -q postgres).Trim()
& $DockerPath cp $dump "${postgresId}:/tmp/bookpath-restore.dump"
try {
    & $DockerPath compose -f $compose stop gateway backend
    & $DockerPath compose -f $compose exec -T postgres pg_restore --clean --if-exists --exit-on-error --no-owner --no-privileges --username=bookpath --dbname=bookpath /tmp/bookpath-restore.dump
    if ($LASTEXITCODE -ne 0) { throw 'Production restore failed.' }
}
finally {
    & $DockerPath compose -f $compose exec -T postgres rm -f /tmp/bookpath-restore.dump 2>$null
    & $DockerPath compose -f $compose up -d backend gateway
}
Write-Host 'Production database restore completed.'
