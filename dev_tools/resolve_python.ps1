function Get-NeteaseToolsPython {
    $candidates = @($env:NETEASE_TOOLS_PYTHON, (Join-Path $PSScriptRoot 'python_env/Scripts/python.exe'))
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) { return $candidate }
    }
    throw 'Tool Python not found. Run dev_tools/setup_python.ps1 or set NETEASE_TOOLS_PYTHON.'
}

function Assert-NeteaseResource([string]$Resource, [string]$Python = 'python') {
    & $Python -B (Join-Path $PSScriptRoot 'prepare_workspace.py') --status --tools $Resource | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Resource $Resource is not ready. See dev_tools/README.md." }
}
