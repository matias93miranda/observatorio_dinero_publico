# Uso: .\scripts\run_windows.ps1 [setup|sync|test|serve]
param([string]$cmd = "serve")
$ErrorActionPreference = "Stop"
$Root = Resolve-Path "$PSScriptRoot\.."
$Py = "$Root\.venv\Scripts\python.exe"
switch ($cmd) {
  "setup" {
    py -3 -m venv "$Root\.venv"
    & $Py -m pip install -r "$Root\backend\requirements.txt"
    Push-Location "$Root\frontend"; npm ci; npm run build; Pop-Location
  }
  "sync"  { Push-Location "$Root\backend"; & $Py -m observatorio.cli sync; Pop-Location }
  "test"  { Push-Location "$Root\backend"; & $Py -m pytest -q; Pop-Location }
  "serve" { Push-Location "$Root\backend"; & $Py -m uvicorn observatorio.api:app --host 127.0.0.1 --port 8000; Pop-Location }
  default { Write-Error "comando desconocido: $cmd" }
}
