param([ValidateRange(1,65535)][int]$GamePort=14520, [ValidateRange(1,65535)][int]$HttpPort=3002)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'resolve_python.ps1')
$toolPython = Get-NeteaseToolsPython
Assert-NeteaseResource -Resource 'modpc' -Python $toolPython
$env:PYTHONDONTWRITEBYTECODE = '1'
& $toolPython -B (Join-Path $PSScriptRoot 'external/ModPC-MCP-Tool/server.py') --game-host 127.0.0.1 --game-port $GamePort --http-host 127.0.0.1 --http-port $HttpPort
exit $LASTEXITCODE
