param([string]$RuntimeRoot = $PSScriptRoot)
$ErrorActionPreference = 'Stop'
$client = Join-Path (Split-Path $RuntimeRoot -Parent) 'tunnel-client\tunnel-client.exe'
$status = & $client runtimes status pro-a-local --json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Managed runtime status failed.' }
$health = $null
$healthError = $null
if ($status.process_running -and $status.health_details_url) {
    try {
        $health = Invoke-RestMethod -Uri $status.health_details_url -TimeoutSec 10
    } catch {
        $healthError = 'Detailed local health unavailable; polling is not verified.'
    }
}
[pscustomobject]@{
    checked_at_utc = [DateTime]::UtcNow.ToString('o')
    alias = $status.alias
    process_running = $status.process_running
    healthy = $status.healthy
    ready = $status.ready
    control_plane_poll_health = $status.control_plane_poll_health
    control_plane_details = $health.components.'control-plane'
    proxy_details = $health.components.proxy
    mcp_details = $health.components.mcp
    health_error = $healthError
} | ConvertTo-Json -Depth 12
