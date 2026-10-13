$ErrorActionPreference = "Stop"

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
$PARENT = Split-Path -Parent $ROOT

$FULLSTACK_ROOT = $ROOT
$BACKEND = Join-Path $FULLSTACK_ROOT "backend"
$FRONTEND = Join-Path $FULLSTACK_ROOT "frontend"

$TRACKNET_ROOT = Join-Path $PARENT "TrackNetV3"
$ANALYZER_ROOT = Join-Path $PARENT "badminton-performance-analyzer"
$RUNS_ROOT = Join-Path $ANALYZER_ROOT "outputs"

$BACKEND_PY = Join-Path $BACKEND ".venv\Scripts\python.exe"

$TRACKNET_PY = Join-Path $TRACKNET_ROOT ".venv\Scripts\python.exe"
$ANALYZER_PY = Join-Path $ANALYZER_ROOT ".venv\Scripts\python.exe"

function Require-Path($p, $name) {
  if (-not (Test-Path $p)) {
    Write-Host ""
    Write-Host "Missing: $name"
    Write-Host "Expected path: $p"
    Write-Host ""
    throw "Missing required path: $name"
  }
}

Require-Path $BACKEND "badminton-fullstack-a1\backend"
Require-Path $FRONTEND "badminton-fullstack-a1\frontend"
Require-Path $TRACKNET_ROOT "TrackNetV3"
Require-Path $ANALYZER_ROOT "badminton-performance-analyzer"
Require-Path $BACKEND_PY "backend python"
Require-Path $TRACKNET_PY "tracknet python"
Require-Path $ANALYZER_PY "analyzer python"

$tracknetCheckpoint = if ($env:TRACKNET_CKPT) { $env:TRACKNET_CKPT } else { "ckpts\TrackNet_best.pt" }
$inpaintCheckpoint = if ($env:INPAINT_CKPT) { $env:INPAINT_CKPT } else { "ckpts\InpaintNet_best.pt" }
Require-Path (Join-Path $TRACKNET_ROOT $tracknetCheckpoint) "TrackNet checkpoint (see docs/SETUP.md)"
Require-Path (Join-Path $TRACKNET_ROOT $inpaintCheckpoint) "InpaintNet checkpoint (see docs/SETUP.md)"
$npmCommand = (Get-Command npm.cmd -ErrorAction Stop).Source

foreach ($servicePort in @(8000, 4200, 8501)) {
  if (Get-NetTCPConnection -LocalPort $servicePort -State Listen -ErrorAction SilentlyContinue) {
    throw "Port $servicePort is already in use. Stop the previous instance before launching."
  }
}

$LOGS_ROOT = Join-Path $ROOT "logs"
New-Item -ItemType Directory -Force -Path $RUNS_ROOT, $LOGS_ROOT | Out-Null

$APP_MULTI = Join-Path $ANALYZER_ROOT "dashboard\app_multi.py"
$APP_SINGLE = Join-Path $ANALYZER_ROOT "dashboard\app.py"

if (-not (Test-Path $APP_MULTI) -and -not (Test-Path $APP_SINGLE)) {
  throw "Missing Streamlit app: dashboard\app_multi.py or dashboard\app.py"
}

$env:RUNS_ROOT     = $RUNS_ROOT
$env:TRACKNET_ROOT = $TRACKNET_ROOT
$env:ANALYZER_ROOT = $ANALYZER_ROOT
$env:TRACKNET_PY   = $TRACKNET_PY
$env:ANALYZER_PY   = $ANALYZER_PY
$env:RQ_SYNC       = "1"

$env:PYTHONPATH = Join-Path $ANALYZER_ROOT "src"
$env:STREAMLIT_SERVER_HEADLESS = "true"

function Quote-PSLiteral([string]$value) {
  return "'" + $value.Replace("'", "''") + "'"
}

function Start-ServiceProcess($name, $directory, $command) {
  $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($command))
  $process = Start-Process -FilePath powershell.exe -WindowStyle Hidden -PassThru `
    -WorkingDirectory $directory -ArgumentList @("-NoProfile", "-EncodedCommand", $encoded) `
    -RedirectStandardOutput (Join-Path $LOGS_ROOT "$name.stdout.log") `
    -RedirectStandardError (Join-Path $LOGS_ROOT "$name.stderr.log")
  return [pscustomobject]@{ Name = $name; ProcessId = $process.Id; Started = $process.StartTime.ToUniversalTime().ToString("o") }
}

$processFile = Join-Path $LOGS_ROOT "processes.json"
$services = @()
try {
  Write-Host "[1/3] Backend http://127.0.0.1:8000"
  $services += Start-ServiceProcess "backend" $BACKEND ("& " + (Quote-PSLiteral $BACKEND_PY) + " -m uvicorn app.main:app --host 127.0.0.1 --port 8000")
  $services | ConvertTo-Json -Depth 3 | Set-Content -Encoding UTF8 -LiteralPath $processFile

  Write-Host "[2/3] Frontend http://127.0.0.1:4200"
  $services += Start-ServiceProcess "frontend" $FRONTEND ("& " + (Quote-PSLiteral $npmCommand) + " start")
  $services | ConvertTo-Json -Depth 3 | Set-Content -Encoding UTF8 -LiteralPath $processFile

  Write-Host "[3/3] Streamlit http://127.0.0.1:8501"
  if (-not (Test-Path $APP_MULTI)) { throw "Multi-run dashboard missing: $APP_MULTI" }
  $streamlitCommand = "& " + (Quote-PSLiteral $ANALYZER_PY) + " -m streamlit run " + (Quote-PSLiteral $APP_MULTI) + " --server.address 127.0.0.1 --server.port 8501 --server.headless true -- --runs_root " + (Quote-PSLiteral $RUNS_ROOT)
  $services += Start-ServiceProcess "streamlit" $ANALYZER_ROOT $streamlitCommand
  $services | ConvertTo-Json -Depth 3 | Set-Content -Encoding UTF8 -LiteralPath $processFile
} catch {
  Write-Host "Startup failed. Stop any recorded services with stop.bat; inspect $LOGS_ROOT."
  throw
}

for ($attempt = 0; $attempt -lt 30; $attempt++) {
  try {
    Invoke-WebRequest -Uri "http://127.0.0.1:4200/upload" -UseBasicParsing -TimeoutSec 2 | Out-Null
    Start-Process "http://127.0.0.1:4200/upload"
    Write-Host "Application opened. Logs: $LOGS_ROOT"
    exit 0
  } catch {
    Start-Sleep -Seconds 1
  }
}
Write-Host "Frontend is still starting or failed. Inspect logs in $LOGS_ROOT."
