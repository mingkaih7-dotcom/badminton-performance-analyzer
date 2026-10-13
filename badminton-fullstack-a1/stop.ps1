$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$processFile = Join-Path $projectRoot "logs\processes.json"
if (-not (Test-Path $processFile)) {
  Write-Host "No recorded launcher processes."
  exit 0
}

$records = @(Get-Content -Raw -LiteralPath $processFile | ConvertFrom-Json)
foreach ($record in $records) {
  $serviceProcess = Get-Process -Id $record.ProcessId -ErrorAction SilentlyContinue
  if (-not $serviceProcess) { continue }
  $started = $serviceProcess.StartTime.ToUniversalTime().ToString("o")
  if ($started -ne $record.Started -or $serviceProcess.ProcessName -ne "powershell") {
    Write-Host "Skipping $($record.Name): process identity changed."
    continue
  }
  & taskkill.exe /PID $record.ProcessId /T /F | Out-Null
  Write-Host "Stopped launcher process tree: $($record.Name)"
}
