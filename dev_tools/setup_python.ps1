param([string]$Python = 'python', [switch]$WithPixelTools, [switch]$WithTracy)
$ErrorActionPreference = 'Stop'
$toolEnv = Join-Path $PSScriptRoot 'python_env'
$toolPython = Join-Path $toolEnv 'Scripts/python.exe'
& $Python -c 'import sys; assert sys.version_info >= (3, 10), "Python 3.10+ required"'
if ($LASTEXITCODE -ne 0) { throw 'A working Python 3.10+ is required.' }
if (-not (Test-Path -LiteralPath $toolPython)) {
    & $Python -m venv $toolEnv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the tool environment.' }
}
& $toolPython -c 'import sys; assert sys.version_info >= (3, 10), "Existing tool environment requires Python 3.10+"'
if ($LASTEXITCODE -ne 0) { throw 'The existing tool environment needs rebuilding with Python 3.10+.' }
& $toolPython -m pip install --disable-pip-version-check --no-cache-dir -r (Join-Path $PSScriptRoot 'requirements-tools.txt')
if ($LASTEXITCODE -ne 0) { throw 'Tool dependency installation failed.' }
if ($WithTracy) {
    & $toolPython -B (Join-Path $PSScriptRoot 'prepare_workspace.py') --status --tools tracy | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Prepare Tracy first: python dev_tools/prepare_workspace.py --tools tracy --fetch' }
    & $toolPython -m pip install --disable-pip-version-check --no-cache-dir -e (Join-Path $PSScriptRoot 'external/mcdk-mcp-tracy')
    if ($LASTEXITCODE -ne 0) { throw 'Tracy package installation failed.' }
}
if ($WithPixelTools) {
    & $toolPython -B (Join-Path $PSScriptRoot 'prepare_workspace.py') --status --tools pixel | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Prepare the pixel tool first: python dev_tools/prepare_workspace.py --tools pixel --fetch' }
    & $toolPython -m pip install --no-cache-dir -r (Join-Path $PSScriptRoot 'pixel_art_converter/requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Pixel tool dependency installation failed.' }
}
& $toolPython -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependency consistency check failed.' }
