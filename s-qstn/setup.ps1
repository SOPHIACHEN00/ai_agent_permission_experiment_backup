param([switch]$Offline)
$ErrorActionPreference = 'Stop'
Push-Location -LiteralPath $PSScriptRoot
try {
    $sqstnPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    $sqstnCache = Join-Path $PSScriptRoot '.cache\uv'
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        if (-not (Test-Path -LiteralPath $sqstnPython)) {
            uv --cache-dir $sqstnCache venv --no-project --python 3.12 --no-python-downloads .venv
            if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python environment.' }
        }
        if ($Offline) {
            uv --cache-dir $sqstnCache pip sync --offline --python $sqstnPython requirements.lock
        } else {
            uv --cache-dir $sqstnCache pip sync --python $sqstnPython requirements.lock
        }
        if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    } else {
        if (-not (Test-Path -LiteralPath $sqstnPython)) {
            python -m venv .venv
            if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python environment.' }
        }
        if ($Offline) {
            & $sqstnPython -m pip install --no-index -r requirements.lock
        } else {
            & $sqstnPython -m pip install -r requirements.lock
        }
        if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    }
    Write-Output 'S-QSTN is ready. Run: .\.venv\Scripts\python.exe -B run.py'
} finally {
    Pop-Location
}
