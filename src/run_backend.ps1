# run_backend.ps1 (QUIRÚRGICO)
$ErrorActionPreference = "Stop"

Write-Host "== TEAM_ATLAS backend ==" -ForegroundColor Cyan

# 1) Pararse EXACTO en la carpeta donde está este .ps1 (o sea /src)
$HERE = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $HERE
Write-Host "PWD: $HERE" -ForegroundColor Yellow

# 2) Import test (para saber que el entrypoint existe)
python -c "import atlas.api.main as m; print('OK import atlas.api.main')"

# 3) Run server
python -m uvicorn atlas.api.main:app --reload --host 127.0.0.1 --port 8001