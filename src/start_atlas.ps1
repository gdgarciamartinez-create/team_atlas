# start_atlas.ps1  (poner en la raiz del repo TEAM_ATLAS)

$ErrorActionPreference = "Stop"

# 1) Ir a la carpeta del repo (la del script)
Set-Location -Path $PSScriptRoot

# 2) Crear venv si no existe
if (!(Test-Path ".\venv")) {
  Write-Host ">> Creando venv..." -ForegroundColor Cyan
  python -m venv venv
}

# 3) Activar venv
Write-Host ">> Activando venv..." -ForegroundColor Cyan
. .\venv\Scripts\Activate.ps1

# 4) Instalar dependencias MINIMAS (porque no hay requirements.txt)
#    (esto evita el loop infinito de errores por modulos faltantes)
Write-Host ">> Instalando deps base (fastapi/uvicorn/openpyxl)..." -ForegroundColor Cyan
python -m pip install --upgrade pip
python -m pip install fastapi "uvicorn[standard]" openpyxl

# 5) Abrir BACKEND en una ventana nueva (usa tu script si existe, sino uvicorn directo)
if (Test-Path ".\run_backend.ps1") {
  Start-Process powershell -ArgumentList "-NoExit","-ExecutionPolicy Bypass","-File `"$PSScriptRoot\run_backend.ps1`""
} else {
  Start-Process powershell -ArgumentList "-NoExit","-Command","cd `"$PSScriptRoot`"; .\venv\Scripts\Activate.ps1; uvicorn src.atlas.api.main:app --reload --port 8001"
}

# 6) Abrir FRONTEND en otra ventana nueva (usa tu script si existe, sino npm directo)
if (Test-Path ".\run_frontend.ps1") {
  Start-Process powershell -ArgumentList "-NoExit","-ExecutionPolicy Bypass","-File `"$PSScriptRoot\run_frontend.ps1`""
} else {
  Start-Process powershell -ArgumentList "-NoExit","-Command","cd `"$PSScriptRoot\src\atlas\frontend`"; npm install; npm run dev"
}

Write-Host ">> LISTO: Backend + Frontend lanzados en 2 ventanas." -ForegroundColor Green
Write-Host ">> Backend: http://127.0.0.1:8001/api/status"
Write-Host ">> Frontend: http://127.0.0.1:3000/"
