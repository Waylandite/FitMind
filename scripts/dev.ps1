param(
    [ValidateSet('check', 'web', 'agent')]
    [string]$Task = 'check'
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$bundledNode = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
$nodePath = if (Test-Path $bundledNode) { $bundledNode } else { (Get-Command node -ErrorAction Stop).Source }
$pythonPath = Join-Path $projectRoot 'agent/.venv/Scripts/python.exe'

function Invoke-Checked($Executable, $Arguments) {
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Command failed with exit code $LASTEXITCODE" }
}

Push-Location $projectRoot
try {
    switch ($Task) {
        'web' {
            Set-Location (Join-Path $projectRoot 'web')
            Invoke-Checked $nodePath @('node_modules/vite/bin/vite.js', '--host', '127.0.0.1')
        }
        'agent' {
            Set-Location (Join-Path $projectRoot 'agent')
            Invoke-Checked $pythonPath @('-m', 'uvicorn', 'fitmind_agent.main:app', '--reload', '--host', '127.0.0.1', '--port', '8000')
        }
        'check' {
            Set-Location (Join-Path $projectRoot 'agent')
            Invoke-Checked $pythonPath @('-m', 'pytest', '-q')
            Invoke-Checked $pythonPath @('-m', 'ruff', 'check', '.')
            Set-Location (Join-Path $projectRoot 'web')
            Invoke-Checked $nodePath @('node_modules/vitest/vitest.mjs', 'run')
            Invoke-Checked $nodePath @('node_modules/eslint/bin/eslint.js', '.')
            Invoke-Checked $nodePath @('node_modules/vite/bin/vite.js', 'build')
        }
    }
} finally {
    Pop-Location
}
