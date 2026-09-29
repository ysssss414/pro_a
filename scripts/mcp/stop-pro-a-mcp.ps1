param([string]$RuntimeRoot = $PSScriptRoot)
$ErrorActionPreference = 'Stop'
$client = Join-Path (Split-Path $RuntimeRoot -Parent) 'tunnel-client\tunnel-client.exe'
$null = & $client runtimes stop pro-a-local --json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Managed runtime stop failed.' }
& (Join-Path $PSScriptRoot 'status-pro-a-mcp.ps1') -RuntimeRoot $RuntimeRoot
