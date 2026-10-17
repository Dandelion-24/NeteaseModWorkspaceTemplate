param([string]$Python = 'python', [switch]$ResourcesOnly)
$ErrorActionPreference = 'Stop'
$prepare = Join-Path $PSScriptRoot 'prepare_workspace.py'
$verify = Join-Path $PSScriptRoot 'verify_local_environment.py'
$stateDirectory = Join-Path $PSScriptRoot 'local_state'
if (Test-Path -LiteralPath $stateDirectory) {
    if (((Get-Item -LiteralPath $stateDirectory -Force).Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw 'The local report directory cannot be a redirect.'
    }
}
New-Item -ItemType Directory -Path $stateDirectory -Force | Out-Null
$report = [ordered]@{
    attempt_id = [guid]::NewGuid().ToString()
    checked_at_utc = [DateTime]::UtcNow.ToString('o')
    result = 'RUNNING'
    failed_stage = $null
    source = 'NOT_CHECKED'
    source_scope = 'workspace'
    workspace_edits = @()
    resources = 'NOT_CHECKED'
    documents = $null
    tools = $null
    problems = @()
    official_updates = $null
    dependencies = 'NOT_REQUESTED'
    mcp_server_check = 'NOT_REQUESTED'
    mcp_client_configured = $false
    blockbench_plugins_loaded = $false
    modpc_game_runtime_checked = $false
    game_tested = $false
    official_setup = 'dev_tools/OFFICIAL_SETUP.md'
}
$reportPath = Join-Path $stateDirectory 'FIRST_USE_REPORT.json'
function Save-FirstUseReport {
    $reportJson = $report | ConvertTo-Json -Depth 12
    $temporaryReport = $reportPath + '.' + $report.attempt_id + '.tmp'
    try {
        [System.IO.File]::WriteAllText($temporaryReport, $reportJson + "`n", [System.Text.UTF8Encoding]::new($false))
        Move-Item -LiteralPath $temporaryReport -Destination $reportPath -Force
    } finally {
        if (Test-Path -LiteralPath $temporaryReport) { Remove-Item -LiteralPath $temporaryReport -Force }
    }
}
Save-FirstUseReport
$stage = 'core'
$exitCode = 1
try {
    $coreOutput = & $Python -B $verify --profile workspace
    if ($LASTEXITCODE -ne 0) { throw ('Workspace core validation failed: ' + ($coreOutput -join "`n")) }
    $core = ($coreOutput -join "`n") | ConvertFrom-Json
    $report.source = 'PASS'
    $report.workspace_edits = @($core.workspace_edits)

    $stage = 'official_updates'
    $updateOutput = & $Python -B (Join-Path $PSScriptRoot 'sync_netease_docs_from_web.py') --check-updates
    if ($LASTEXITCODE -notin @(0, 2)) { throw ($updateOutput -join "`n") }
    $report.official_updates = ($updateOutput -join "`n") | ConvertFrom-Json

    $stage = 'resources'
    $prepareOutput = & $Python -B $prepare --task all --fetch --fetch-docs
    $resourceExit = $LASTEXITCODE
    if ($resourceExit -notin @(0, 2)) { throw ($prepareOutput -join "`n") }
    $prepared = ($prepareOutput -join "`n") | ConvertFrom-Json
    $report.resources = $prepared.task_status
    $report.documents = $prepared.documents
    $report.tools = $prepared.resources
    $report.problems = @($prepared.problems)
    if (-not $ResourcesOnly) {
        $stage = 'dependencies'
        $report.dependencies = 'RUNNING'
        $setupArgs = @{Python = $Python}
        if ($prepared.resources.tracy.status -eq 'READY') { $setupArgs.WithTracy = $true }
        if ($prepared.resources.pixel.status -eq 'READY') { $setupArgs.WithPixelTools = $true }
        & (Join-Path $PSScriptRoot 'setup_python.ps1') @setupArgs
        $report.dependencies = 'PASS'
        $toolPython = Join-Path $PSScriptRoot 'python_env/Scripts/python.exe'
        $readyMcp = @(@('modpc', 'tracy') | Where-Object { $prepared.resources.$_.status -eq 'READY' })
        if ($readyMcp.Count -gt 0) {
            $stage = 'mcp'
            $report.mcp_server_check = 'RUNNING'
            $mcpOutput = & $toolPython -B (Join-Path $PSScriptRoot 'check_local_tools.py') --tools @readyMcp
            if ($LASTEXITCODE -ne 0) { throw ($mcpOutput -join "`n") }
            $report.mcp_server_check = 'PASS_ENUMERATION_ONLY'
        }
    }
    $needsVersionReview = $report.official_updates.template_update_status -in @('UNKNOWN', 'NEW_FORMAL_VERSION_REQUIRES_SYNC')
    $unknownUpdates = $report.official_updates.status -eq 'UNKNOWN' -or $report.official_updates.official_offline_file.status -eq 'UNKNOWN'
    $exitCode = if ($resourceExit -ne 0 -or $needsVersionReview -or $unknownUpdates) { 2 } else { 0 }
    $report.result = if ($exitCode -eq 0) { 'READY_RESOURCES' } else { 'ATTENTION_REQUIRED' }
} catch {
    $report.result = 'FAIL'
    $report.failed_stage = $stage
    $report.problems += @{ id = $stage; reason = $_.Exception.Message }
    if ($stage -eq 'core') { $report.source = 'FAIL' }
    if ($stage -eq 'dependencies') { $report.dependencies = 'FAIL' }
    if ($stage -eq 'mcp') { $report.mcp_server_check = 'FAIL' }
    $exitCode = 1
} finally {
    Save-FirstUseReport
}
Write-Output ($report | ConvertTo-Json -Depth 12)
exit $exitCode
