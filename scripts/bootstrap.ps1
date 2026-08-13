$ErrorActionPreference = "Stop"
if (-not (Test-Path ".venv")) {
  py -m venv .venv
}
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
if (-not (Test-Path "config.toml")) {
  Copy-Item "config.example.toml" "config.toml"
}
Write-Host "pro_a v0.1 bootstrap complete. Next: .\.venv\Scripts\Activate.ps1 ; pro-a init"
