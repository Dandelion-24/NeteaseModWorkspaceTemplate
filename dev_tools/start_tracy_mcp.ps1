$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'resolve_python.ps1')
$toolPython = Get-NeteaseToolsPython
Assert-NeteaseResource -Resource 'tracy' -Python $toolPython
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:TRACY_BIN_DIR = Join-Path $PSScriptRoot 'external/mcdk-mcp-tracy/bin'
$tracySource = Join-Path $PSScriptRoot 'external/mcdk-mcp-tracy/src'
$env:PYTHONPATH = $tracySource + [System.IO.Path]::PathSeparator + $env:PYTHONPATH
& $toolPython -B -m mcdk_mcp_tracy --stdio @args
exit $LASTEXITCODE
