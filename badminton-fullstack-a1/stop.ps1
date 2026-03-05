$ErrorActionPreference = "SilentlyContinue"

function Kill-Port($port) {
  $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
  if (-not $conns) {
    Write-Host "Port $port not listening"
    return
  }
  $pids = $conns | Select-Object -ExpandProperty OwningProcess -Unique
  foreach ($pid in $pids) {
    if ($pid) {
      Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
      Write-Host "Killed PID $pid on port $port"
    }
  }
}

Kill-Port 8000
Kill-Port 4200
Kill-Port 8501