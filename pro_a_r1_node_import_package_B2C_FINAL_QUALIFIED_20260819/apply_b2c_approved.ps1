[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$DatabasePath,

    [Parameter(Mandatory = $true)]
    [ValidateSet("Isolated", "Production")]
    [string]$TargetIdentity,

    [Parameter(Mandatory = $true)]
    [string]$AuthorizationToken,

    [Parameter(Mandatory = $true)]
    [string]$ReportPath,

    [Parameter(Mandatory = $true)]
    [string]$PythonPath
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$packageRoot = [System.IO.Path]::GetFullPath($PSScriptRoot)
$manifestPath = Join-Path $packageRoot "manifest.json"
$pythonApplyPath = Join-Path $packageRoot "apply_b2c_approved.py"

if (-not (Test-Path -LiteralPath $DatabasePath -PathType Leaf)) {
    throw "DatabasePath does not exist or is not a file: $DatabasePath"
}
if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
    throw "PythonPath does not exist or is not a file: $PythonPath"
}
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
    throw "manifest.json is missing"
}

$resolvedDatabasePath = (Resolve-Path -LiteralPath $DatabasePath).ProviderPath
$resolvedPythonPath = (Resolve-Path -LiteralPath $PythonPath).ProviderPath
$resolvedReportPath = [System.IO.Path]::GetFullPath($ReportPath)

$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($manifest.package_id -ne (Split-Path -Leaf $packageRoot)) {
    throw "Manifest package_id does not match package directory"
}

foreach ($property in $manifest.semantic_inputs.PSObject.Properties) {
    $relativePath = $property.Name
    $entry = $property.Value
    $inputPath = Join-Path $packageRoot ($relativePath -replace '/', [System.IO.Path]::DirectorySeparatorChar)
    if (-not (Test-Path -LiteralPath $inputPath -PathType Leaf)) {
        throw "Manifest input is missing: $relativePath"
    }
    $actualHash = (Get-FileHash -LiteralPath $inputPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $actualBytes = (Get-Item -LiteralPath $inputPath).Length
    if ($actualHash -ne $entry.sha256 -or $actualBytes -ne $entry.bytes) {
        throw "Manifest hash/size mismatch: $relativePath"
    }
}

$manifestSha = (Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash.ToLowerInvariant()
$databaseSha = (Get-FileHash -LiteralPath $resolvedDatabasePath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($TargetIdentity -eq "Isolated") {
    $expectedToken = "AUTHORIZE_ISOLATED_DRY_RUN:$manifestSha`:$databaseSha"
}
else {
    $expectedToken = "AUTHORIZE_PRODUCTION_IMPORT:$manifestSha`:$databaseSha"
}
if ($AuthorizationToken -cne $expectedToken) {
    throw "AuthorizationToken does not bind this target identity, manifest SHA and DB SHA"
}

& $resolvedPythonPath -B $pythonApplyPath `
    --database-path $resolvedDatabasePath `
    --target-identity $TargetIdentity `
    --authorization-token $AuthorizationToken `
    --report-path $resolvedReportPath

if ($LASTEXITCODE -ne 0) {
    throw "B.2C apply failed closed with exit code $LASTEXITCODE"
}
