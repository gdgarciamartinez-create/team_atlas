# TEAM ATLAS - Run All (Backend + Frontend)
# Uso:  .\run_all.ps1

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path $repoRoot).Path

Write-Host "Repo root: $repoRoot"

# ---- Backend ----
$backendCmd = @"
cd "$repoRoot"
if (Test-Path ".\.venv\Scripts\Activate.ps1") { . ".\.venv\Scripts\Activate.ps1" }
python -m uvicorn atlas.api.main:app --reload --host 127.0.0.1 --port 8001 --app-dir src
"@

$backendArgs = '-NoExit -ExecutionPolicy Bypass -Command "' + ($backendCmd -replace '"','\"') + '"'
Start-Process -FilePath "powershell.exe" -ArgumentList $backendArgs -WorkingDirectory $repoRoot | Out-Null
Write-Host "Backend launched on 8001"

Start-Sleep -Milliseconds 800

# ---- Frontend ----
$frontDir = Join-Path $repoRoot "src\atlas\frontend"
if (-not (Test-Path $frontDir)) {
    Write-Host "ERROR: Frontend folder not found: $frontDir"
    exit 1
}

$frontendCmd = @"
cd "$frontDir"
if (-not (Test-Path ".\node_modules")) { npm install }
npm run dev -- --host 127.0.0.1 --port 3000
"@

$frontendArgs = '-NoExit -ExecutionPolicy Bypass -Command "' + ($frontendCmd -replace '"','\"') + '"'
Start-Process -FilePath "powershell.exe" -ArgumentList $frontendArgs -WorkingDirectory $frontDir | Out-Null
Write-Host "Frontend launched on 3000"

# ---- Healthcheck ----
Write-Host "Waiting for backend..."
for ($i=1; $i -le 40; $i++) {
    try {
        $r = Invoke-WebRequest "http://127.0.0.1:8001/api/status" -UseBasicParsing -TimeoutSec 2
        if ($r.StatusCode -eq 200) {
            Write-Host "Backend OK"
            break
        }
    } catch {
        Start-Sleep -Milliseconds 500
    }
}

Write-Host ""
Write-Host "DONE:"
Write-Host "Backend:  http://127.0.0.1:8001/api/status"
Write-Host "Frontend: http://127.0.0.1:3000"