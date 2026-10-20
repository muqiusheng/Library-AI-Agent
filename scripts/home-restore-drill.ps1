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
$postgresId = (& $DockerPath compose -f $compose ps -q postgres).Trim()
if (-not $postgresId) { throw 'PostgreSQL container is not running.' }

$testDatabase = 'bookpath_restore_test'
& $DockerPath cp $dump "${postgresId}:/tmp/bookpath-restore.dump"
try {
    & $DockerPath compose -f $compose exec -T postgres dropdb --if-exists --username=bookpath bookpath_restore_test
    & $DockerPath compose -f $compose exec -T postgres createdb --username=bookpath bookpath_restore_test
    if ($LASTEXITCODE -ne 0) { throw 'Unable to create restore test database.' }
    & $DockerPath compose -f $compose exec -T postgres pg_restore --exit-on-error --no-owner --no-privileges --username=bookpath --dbname=bookpath_restore_test /tmp/bookpath-restore.dump
    if ($LASTEXITCODE -ne 0) { throw 'Restore drill failed.' }
    $booksOutput = & $DockerPath compose -f $compose exec -T postgres psql --tuples-only --no-align --username=bookpath --dbname=bookpath_restore_test --command='SELECT count(*) FROM books;'
    $holdingsOutput = & $DockerPath compose -f $compose exec -T postgres psql --tuples-only --no-align --username=bookpath --dbname=bookpath_restore_test --command='SELECT count(*) FROM holdings;'
    $books = [int](($booksOutput -join '').Trim())
    $holdings = [int](($holdingsOutput -join '').Trim())
    if ($books -le 0 -or $holdings -le 0) {
        throw "Restore count validation failed: books=$books, holdings=$holdings"
    }
    Write-Host "Restore drill passed: books=$books, holdings=$holdings"
}
finally {
    & $DockerPath compose -f $compose exec -T postgres dropdb --if-exists --force --username=bookpath bookpath_restore_test
    & $DockerPath compose -f $compose exec -T postgres rm -f /tmp/bookpath-restore.dump
}
