$ErrorActionPreference = 'SilentlyContinue'
$agentPidFile = Join-Path $PSScriptRoot 'data\server.pid'
if (Test-Path -LiteralPath $agentPidFile) {
    $agentProcessId = [int](Get-Content -LiteralPath $agentPidFile)
    Stop-Process -Id $agentProcessId -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $agentPidFile -Force -ErrorAction SilentlyContinue
}

$conn = Get-NetTCPConnection -LocalPort 8765 -ErrorAction SilentlyContinue | Where-Object { $_.OwningProcess -gt 0 }
if ($conn) {
    foreach ($procId in ($conn.OwningProcess | Select-Object -Unique)) {
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }
}
Write-Host 'Jobfolio stopped.'
