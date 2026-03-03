param(
  [int]$Port = 8001
)

$ErrorActionPreference = "Stop"

Write-Host "== TEAM ATLAS :: Backend ==" -ForegroundColor Cyan

# Ir a la carpeta del repo (donde está este script)
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

# Activar venv si existe
if (Test-Path ".\.venv\Scripts\Activate.ps1") {
  . .\.venv\Scripts\Activate.ps1
  Write-Host "Venv activado: .venv" -ForegroundColor Green
} else {
  Write-Host "WARN: No se encontró .venv, usando Python global" -ForegroundColor Yellow
}

# Forzar que 'src' sea el root de imports (CLAVE)
$env:PYTHONPATH = (Join-Path $RepoRoot "src")

# Ejecutar API
python -m uvicorn atlas.api.main:app --host 127.0.0.1 --port $Port --reload