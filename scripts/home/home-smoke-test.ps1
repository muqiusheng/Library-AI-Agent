[CmdletBinding()]
param([string]$BaseUrl = 'http://127.0.0.1:8180')

$ErrorActionPreference = 'Stop'
$base = $BaseUrl.TrimEnd('/')
if ($base.StartsWith('https://')) {
    $pageContent = & curl.exe --connect-timeout 20 --max-time 40 -fsS "$base/"
    $pageText = $pageContent -join "`n"
    if ($LASTEXITCODE -ne 0 -or $pageText -notmatch 'id="app"') {
        throw 'Frontend smoke test failed.'
    }
    $healthContent = & curl.exe --connect-timeout 20 --max-time 40 -fsS "$base/health"
    if ($LASTEXITCODE -ne 0 -or ($healthContent | ConvertFrom-Json).data.status -ne 'ok') {
        throw 'Health smoke test failed.'
    }
    $authStatus = & curl.exe --connect-timeout 20 --max-time 40 -sS -o NUL -w '%{http_code}' "$base/api/v1/auth/me"
    if ($LASTEXITCODE -ne 0 -or $authStatus -ne '401') {
        throw 'Anonymous auth endpoint did not return 401.'
    }
}
else {
    $page = Invoke-WebRequest -UseBasicParsing -Uri "$base/" -TimeoutSec 20
    if ($page.StatusCode -ne 200 -or $page.Content -notmatch 'id="app"') {
        throw 'Frontend smoke test failed.'
    }
    $health = Invoke-RestMethod -Uri "$base/health" -TimeoutSec 20
    if ($health.data.status -ne 'ok') { throw 'Health smoke test failed.' }
    try {
        Invoke-RestMethod -Uri "$base/api/v1/auth/me" -TimeoutSec 20 | Out-Null
        throw 'Anonymous auth endpoint unexpectedly succeeded.'
    }
    catch {
        if ($_.Exception.Response.StatusCode.value__ -ne 401) { throw }
    }
}
Write-Host "Smoke test passed: $base"
