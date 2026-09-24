param(
    [switch]$Restart
)

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

if ($Restart) {
    & (Join-Path $PSScriptRoot 'stop.ps1')
    Start-Sleep -Milliseconds 500
}

$agentPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $agentPython)) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.11 or newer is required.' }
    $agentRequirements = if (Test-Path -LiteralPath 'requirements.lock.txt') { 'requirements.lock.txt' } else { 'requirements.txt' }
    & $agentPython -m pip install -r $agentRequirements
    if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
    & $agentPython -m playwright install chromium
    if ($LASTEXITCODE -ne 0) { throw 'Browser installation failed.' }
}
if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'frontend\dist\index.html'))) {
    Push-Location -LiteralPath (Join-Path $PSScriptRoot 'frontend')
    try {
        npm.cmd ci
        if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
        npm.cmd run build
        if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
    } finally { Pop-Location }
}
New-Item -ItemType Directory -Force -Path (Join-Path $PSScriptRoot 'data') | Out-Null
$agentUrl = 'http://127.0.0.1:8765'
if (-not $Restart) {
    try {
        $agentExisting = Invoke-RestMethod -Uri "$agentUrl/api/health" -TimeoutSec 2
        if ($agentExisting.app -eq 'jobfolio') {
            Write-Host "Jobfolio is already running at $agentUrl"
            exit 0
        }
    } catch {}
}
$agentArgs = @('-m','uvicorn','backend.app:app','--host','127.0.0.1','--port','8765','--no-access-log')
$agentProcess = Start-Process -FilePath $agentPython -ArgumentList $agentArgs -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $PSScriptRoot 'data\server.log') -RedirectStandardError (Join-Path $PSScriptRoot 'data\server-error.log')
$agentProcess.Id | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'data\server.pid')
for ($agentAttempt = 0; $agentAttempt -lt 30; $agentAttempt++) {
    Start-Sleep -Milliseconds 500
    try {
        $agentHealth = Invoke-RestMethod -Uri "$agentUrl/api/health" -TimeoutSec 1
        if ($agentHealth.app -eq 'jobfolio') {
            Write-Host "Jobfolio is ready at $agentUrl"
            exit 0
        }
    } catch {}
    if ($agentProcess.HasExited) { throw 'Server stopped. See data\server-error.log.' }
}
throw 'Server startup timed out. See data\server-error.log.'
