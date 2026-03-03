$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

if (Test-Path ".\.venv\Scripts\Activate.ps1") {
  . ".\.venv\Scripts\Activate.ps1"
}

$env:PYTHONPATH="src"
python -m uvicorn atlas.main:app --host 127.0.0.1 --port 8001 --reload