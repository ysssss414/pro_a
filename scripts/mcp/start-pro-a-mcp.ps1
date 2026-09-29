param([string]$RuntimeRoot = $PSScriptRoot)
$ErrorActionPreference = 'Stop'
$python = Join-Path $RuntimeRoot '.venv\Scripts\python.exe'
$secret = Join-Path $RuntimeRoot 'secrets\runtime-api-key.txt'
$client = Join-Path (Split-Path $RuntimeRoot -Parent) 'tunnel-client\tunnel-client.exe'
foreach ($path in @($python, $secret, $client)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw 'Stable runtime setup is incomplete. Check Python, tunnel-client and the private key file.'
    }
}
$settings = Get-Content -LiteralPath (Join-Path $RuntimeRoot 'runtime-settings.json') -Raw | ConvertFrom-Json
if (-not (Test-Path -LiteralPath $settings.workbench_config -PathType Leaf)) {
    throw 'The saved private Workbench configuration is unavailable.'
}
if ($settings.tunnel_id -notmatch '^tunnel_[a-zA-Z0-9]+$') {
    throw 'The saved Tunnel ID is invalid.'
}
$proxy = [uri]$settings.control_plane_http_proxy
if ($proxy.Scheme -notin @('http', 'https') -or -not $proxy.Host -or $proxy.UserInfo -or $proxy.Query -or $proxy.Fragment) {
    throw 'The control-plane proxy must be a credential-free HTTP(S) URL.'
}
$previousProxy = $env:CONTROL_PLANE_HTTP_PROXY
Push-Location -LiteralPath $RuntimeRoot
try {
    $env:CONTROL_PLANE_HTTP_PROXY = $proxy.AbsoluteUri
    $command = '"{0}" -B -m pro_a.mcp.server --config "{1}" --transport stdio' -f $python.Replace('\', '/'), $settings.workbench_config.Replace('\', '/')
    # Windows PowerShell's native argument marshalling consumes unescaped quotes.
    if ($PSVersionTable.PSVersion.Major -lt 7) { $command = $command.Replace('"', '\"') }
    $connectArgs = @('runtimes', 'connect', '--alias', 'pro-a-local',
        '--tunnel-id', $settings.tunnel_id, '--profile', 'pro-a-stable',
        '--profile-dir', (Join-Path $RuntimeRoot 'profiles'),
        '--runtime-api-key', ('file:' + $secret.Replace('\', '/')),
        '--mcp-command', $command, '--json')
    $connection = & $client @connectArgs | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw 'Managed runtime start failed; inspect native runtime status.' }
    if (-not $connection.process_running) { throw 'Managed runtime process is not running.' }
} finally {
    $env:CONTROL_PLANE_HTTP_PROXY = $previousProxy
    Pop-Location
}
& (Join-Path $PSScriptRoot 'status-pro-a-mcp.ps1') -RuntimeRoot $RuntimeRoot
