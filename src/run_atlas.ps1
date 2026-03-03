$repo = "C:\Users\gdgar\MisProyectosVSCode\TEAM_ATLAS"

Write-Host "🔪 Cerrando procesos 8001 y 3000 si existen..."

$ports = 8001,3000
foreach ($p in $ports) {
  $conn = Get-NetTCPConnection -LocalPort $p -ErrorAction SilentlyContinue
  if ($conn) {
    Stop-Process -Id $conn.OwningProcess -Force
    Write-Host "Puerto $p liberado."
  }
}

Start-Sleep -Seconds 1

Write-Host "🚀 Levantando BACKEND..."

Start-Process powershell -ArgumentList @(
  "-NoExit",
  "-Command",
  "cd `"$repo`"; .\venv\Scripts\Activate.ps1; python -m uvicorn atlas.api.main:app --reload --host 127.0.0.1 --port 8001 --app-dir src"
)

Start-Sleep -Seconds 2

Write-Host "🎨 Levantando FRONTEND..."

Start-Process powershell -ArgumentList @(
  "-NoExit",
  "-Command",
  "cd `"$repo\src\atlas\frontend`"; npm run dev -- --host 127.0.0.1 --port 3000"
)

Write-Host ""
Write-Host "🧠 TEAM ATLAS DESPIERTO"
Write-Host "Backend:  http://127.0.0.1:8001/docs"
Write-Host "Frontend: http://127.0.0.1:3000"
