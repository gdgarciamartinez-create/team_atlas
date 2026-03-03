# self_check.ps1
$ErrorActionPreference = "Stop"

Write-Host "== TEAM_ATLAS self check ==" -ForegroundColor Cyan

try {
  $status = Invoke-RestMethod -Uri "http://127.0.0.1:8001/api/status" -Method Get -TimeoutSec 3
  Write-Host "STATUS OK:" -ForegroundColor Green
  $status | ConvertTo-Json -Depth 5
} catch {
  Write-Host "STATUS FAIL (server no arriba o puerto 8001 bloqueado)" -ForegroundColor Red
  throw
}

try {
  $snap = Invoke-RestMethod -Uri "http://127.0.0.1:8001/api/snapshot?symbol=XAUUSD&tf=M1&count=120&strategy=GENERAL" -Method Get -TimeoutSec 6
  Write-Host "SNAPSHOT OK:" -ForegroundColor Green
  Write-Host ("mode=" + $snap.mode + " world=" + $snap.world + " candles=" + ($snap.candles.Count))
  Write-Host ("doctrine_ok=" + $snap.doctrine_ok + " last_error=" + $snap.last_error)
} catch {
  Write-Host "SNAPSHOT FAIL" -ForegroundColor Red
  throw
}
