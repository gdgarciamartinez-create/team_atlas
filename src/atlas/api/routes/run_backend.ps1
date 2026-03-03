# run_backend.ps1
$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repo

Write-Host "== TEAM_ATLAS backend ==" -ForegroundColor Cyan
Write-Host "Repo: $repo"
Write-Host "Cd -> src"

Set-Location (Join-Path $repo "src")

# Import test (quirúrgico)
python -c "import atlas.api.main as m; print('OK import atlas.api.main')"

# Run server
python -m uvicorn atlas.api.main:app --reload --host 127.0.0.1 --port 8001