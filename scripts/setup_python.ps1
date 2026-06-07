$ErrorActionPreference = "Stop"

$python312 = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
if (-not (Test-Path -LiteralPath $python312)) {
  throw "Python 3.12 was not found at $python312. Install Python.Python.3.12."
}

& $python312 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
& .\.venv\Scripts\python.exe -m pip install -e . --no-deps
& .\.venv\Scripts\python.exe -m pytest -p no:cacheprovider
