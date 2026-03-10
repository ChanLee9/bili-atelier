[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

function Assert-Command {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [string]$InstallHint
    )

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Missing required command '$Name'. $InstallHint"
    }
}

function Get-FileTextOrEmpty {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (Test-Path $Path) {
        return (Get-Content $Path -Raw).Trim()
    }

    return ""
}

Assert-Command -Name "python" -InstallHint "Please install Python 3 and make sure it is available in PATH."
Assert-Command -Name "pnpm" -InstallHint "Please install pnpm and make sure it is available in PATH."

$venvPath = Join-Path $projectRoot ".venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"
$requirementsPath = Join-Path $projectRoot "api\requirements.txt"
$requirementsHashPath = Join-Path $venvPath ".requirements.hash"
$frontendModulesPath = Join-Path $projectRoot "node_modules"

if (-not (Test-Path $venvPython)) {
    Write-Host "Creating Python virtual environment..."
    python -m venv $venvPath
}

if (-not (Test-Path $frontendModulesPath)) {
    Write-Host "Installing frontend dependencies..."
    pnpm install
}

$currentRequirementsHash = (Get-FileHash $requirementsPath -Algorithm SHA256).Hash
$savedRequirementsHash = Get-FileTextOrEmpty -Path $requirementsHashPath

if ($savedRequirementsHash -ne $currentRequirementsHash) {
    Write-Host "Syncing backend dependencies..."
    & $venvPython -m pip install -r $requirementsPath
    Set-Content -Path $requirementsHashPath -Value $currentRequirementsHash
}

$escapedProjectRoot = $projectRoot.Replace("'", "''")
$backendCommand = "Set-Location '$escapedProjectRoot'; & '$venvPython' -m uvicorn api.app.main:app --reload --host 127.0.0.1 --port 8000"
$frontendCommand = "Set-Location '$escapedProjectRoot'; pnpm dev:web"

Write-Host "Starting backend at http://127.0.0.1:8000 ..."
Start-Process -FilePath "powershell.exe" -ArgumentList @(
    "-NoExit",
    "-Command",
    $backendCommand
)

Write-Host "Starting frontend..."
Start-Process -FilePath "powershell.exe" -ArgumentList @(
    "-NoExit",
    "-Command",
    $frontendCommand
)

Write-Host ""
Write-Host "Frontend should be available at http://127.0.0.1:5173"
Write-Host "Backend should be available at http://127.0.0.1:8000"
