param([string]$Python = 'python', [Parameter(ValueFromRemainingArguments=$true)][string[]]$AppArgs)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'resolve_python.ps1')
Assert-NeteaseResource -Resource 'blockbench' -Python $Python
$app = Join-Path $PSScriptRoot 'external/Blockbench/Blockbench_5.2.1_portable.exe'
$profile = Join-Path $PSScriptRoot 'local_state/blockbench'
if (-not (Test-Path -LiteralPath $app -PathType Leaf)) { throw 'The pinned Blockbench executable is missing; see dev_tools/README.md.' }
& $app "--user-data-dir=$profile" @AppArgs
