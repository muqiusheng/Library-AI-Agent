[CmdletBinding()]
param(
    [string]$StudentNo = 'admin',
    [string]$DisplayName = 'BookPath Administrator',
    [string]$DockerPath = 'C:\Users\lenovo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$composePath = Join-Path $root 'docker-compose.home.yml'

if (-not (Test-Path -LiteralPath $DockerPath)) {
    throw "Docker CLI not found: $DockerPath"
}

function ConvertFrom-SecureValue([Security.SecureString]$Value) {
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Value)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    }
}

$first = Read-Host 'Enter the super-admin password (8-16 characters)' -AsSecureString
$second = Read-Host 'Enter the password again' -AsSecureString
$password = ConvertFrom-SecureValue $first
$confirmation = ConvertFrom-SecureValue $second

try {
    if ($password.Length -lt 8 -or $password.Length -gt 16) {
        throw 'The password must contain 8-16 characters.'
    }
    if ($password -cne $confirmation) {
        throw 'The two passwords do not match.'
    }
    $env:BOOKPATH_ADMIN_PASSWORD = $password
    & $DockerPath compose -f $composePath exec -T `
        -e BOOKPATH_ADMIN_PASSWORD backend `
        .venv/bin/python -m app.cli seed-admin `
        --student-no $StudentNo --display-name $DisplayName
    if ($LASTEXITCODE -ne 0) {
        throw "Admin initialization failed. Docker exit code: $LASTEXITCODE"
    }
}
finally {
    Remove-Item Env:BOOKPATH_ADMIN_PASSWORD -ErrorAction SilentlyContinue
    $password = $null
    $confirmation = $null
}
