$ErrorActionPreference = "Stop"
Write-Host "== TEAM ATLAS :: RUN ==" -ForegroundColor Cyan

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

# Backend en una ventana separada
Start-Process powershell -ArgumentList "-NoExit", "-Command", ".\run_backend.ps1 -Port 8001"

# Frontend
Set-Location (Join-Path $RepoRoot "src\atlas\frontend")
if (Test-Path ".\node_modules") {
  Write-Host "node_modules OK" -ForegroundColor Green
} else {
  Write-Host "Instalando deps..." -ForegroundColor Yellow
  npm install
}
npm run dev -- --host 127.0.0.1 --port 3000