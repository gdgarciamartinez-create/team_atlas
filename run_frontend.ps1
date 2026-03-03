# TEAM ATLAS - Frontend runner (PowerShell)
$ErrorActionPreference = "Stop"

Set-Location -Path $PSScriptRoot

$frontendPath = "src\atlas\frontend"
if (-not (Test-Path $frontendPath)) {
  throw "No encuentro frontend en: $frontendPath"
}

Set-Location -Path $frontendPath

Write-Host "== TEAM ATLAS FRONTEND =="
Write-Host "PWD: $(Get-Location)"
Write-Host "Running npm dev on http://localhost:3000 ..."

if (-not (Test-Path "node_modules")) {
  npm install
}

npm run dev -- --port 3000
