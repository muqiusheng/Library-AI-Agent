[CmdletBinding()]
param(
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$templatePath = Join-Path $root '.env.home.example'
$targetPath = Join-Path $root '.env.home'

if ((Test-Path -LiteralPath $targetPath) -and -not $Force) {
    throw '.env.home already exists. Use -Force only when you intend to rotate all generated secrets.'
}

function New-Base64UrlSecret([int]$ByteCount) {
    $bytes = New-Object byte[] $ByteCount
    $random = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $random.GetBytes($bytes)
    }
    finally {
        $random.Dispose()
    }
    return [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
}

$postgresPassword = New-Base64UrlSecret 32
$jwtSecret = New-Base64UrlSecret 48
$content = Get-Content -LiteralPath $templatePath -Encoding utf8 -Raw
$content = $content.Replace('__POSTGRES_PASSWORD__', $postgresPassword)
$content = $content.Replace('__JWT_SECRET__', $jwtSecret)
[System.IO.File]::WriteAllText($targetPath, $content, (New-Object System.Text.UTF8Encoding($false)))

Write-Host 'Created .env.home with generated PostgreSQL and JWT secrets.'
Write-Host 'Registration is closed by default. Do not commit or share this file.'
