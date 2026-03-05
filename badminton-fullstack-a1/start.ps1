$ErrorActionPreference = "Stop"

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
$PARENT = Split-Path -Parent $ROOT

$FULLSTACK_ROOT = $ROOT
$BACKEND = Join-Path $FULLSTACK_ROOT "backend"
$FRONTEND = Join-Path $FULLSTACK_ROOT "frontend"

$TRACKNET_ROOT = Join-Path $PARENT "TrackNetV3"
$ANALYZER_ROOT = Join-Path $PARENT "badminton-performance-analyzer"
$RUNS_ROOT = Join-Path $ANALYZER_ROOT "outputs"

$BACKEND_ACT = Join-Path $BACKEND ".venv\Scripts\Activate.ps1"
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
Require-Path $RUNS_ROOT "badminton-performance-analyzer\outputs"
Require-Path $BACKEND_ACT "backend venv activate"
Require-Path $BACKEND_PY "backend python"
Require-Path $TRACKNET_PY "tracknet python"
Require-Path $ANALYZER_PY "analyzer python"

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

Write-Host "[1/3] Backend http://127.0.0.1:8000"
Start-Process -WindowStyle Normal powershell -ArgumentList @(
  "-NoExit",
  "-Command",
  "cd '$BACKEND'; if (Test-Path '.\.venv\Scripts\Activate.ps1') { .\.venv\Scripts\Activate.ps1 }; `$env:RUNS_ROOT='$RUNS_ROOT'; `$env:TRACKNET_ROOT='$TRACKNET_ROOT'; `$env:ANALYZER_ROOT='$ANALYZER_ROOT'; `$env:TRACKNET_PY='$TRACKNET_PY'; `$env:ANALYZER_PY='$ANALYZER_PY'; `$env:RQ_SYNC='1'; python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
)

Write-Host "[2/3] Frontend http://127.0.0.1:4200"
Start-Process -WindowStyle Normal powershell -ArgumentList @(
  "-NoExit",
  "-Command",
  "cd '$FRONTEND'; npm start"
)

Write-Host "[3/3] Streamlit http://127.0.0.1:8501 (headless, no auto-open)"
Start-Process -WindowStyle Normal powershell -ArgumentList @(
  "-NoExit",
  "-Command",
  "cd '$ANALYZER_ROOT'; if (Test-Path '.\.venv\Scripts\Activate.ps1') { .\.venv\Scripts\Activate.ps1 }; `$env:PYTHONPATH='$ANALYZER_ROOT\src'; `$env:STREAMLIT_SERVER_HEADLESS='true'; if (Test-Path '$APP_MULTI') { python -m streamlit run dashboard\app_multi.py --server.address 127.0.0.1 --server.port 8501 --server.headless true -- --runs_root '$RUNS_ROOT' } else { python -m streamlit run dashboard\app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true -- --run_dir '$RUNS_ROOT\run_xxx' }"
)

Start-Sleep -Seconds 3
cmd /c start "" "http://localhost:4200/upload"