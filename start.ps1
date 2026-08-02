$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"
$BackendProcess = $null
$FrontendProcess = $null

function Resolve-RequiredCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Name,
        [Parameter(Mandatory = $true)]
        [string] $InstallHint,
        [string[]] $FallbackPaths = @()
    )

    $Command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($Command) {
        return $Command.Source
    }

    foreach ($Path in $FallbackPaths) {
        if (Test-Path -LiteralPath $Path -PathType Leaf) {
            return $Path
        }
    }

    Write-Error "Missing command: $Name`n$InstallHint"
}

function Stop-ChildProcess {
    param(
        [System.Diagnostics.Process] $Process
    )

    if ($null -ne $Process -and -not $Process.HasExited) {
        Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
        $Process.WaitForExit()
    }
}

$UvCommand = Resolve-RequiredCommand `
    -Name "uv" `
    -InstallHint "Install uv, then run 'uv sync --all-groups' in the backend directory." `
    -FallbackPaths @((Join-Path $env:USERPROFILE ".local\bin\uv.exe"))

$NpmCommand = Resolve-RequiredCommand `
    -Name "npm" `
    -InstallHint "Install Node.js and npm, then run 'npm ci' in the frontend directory."

if (-not (Test-Path -LiteralPath (Join-Path $FrontendDir "node_modules") -PathType Container)) {
    Write-Error "Frontend dependencies are not installed. Run: cd `"$FrontendDir`"; npm ci"
}

if (-not $env:CHAN_QUANT_DATA_SOURCE) {
    $env:CHAN_QUANT_DATA_SOURCE = "sina"
}

if (-not $env:CHAN_QUANT_SINA_DATALEN) {
    $env:CHAN_QUANT_SINA_DATALEN = "2000"
}

Write-Host "Starting Chan Quant..."
Write-Host "Data source: $env:CHAN_QUANT_DATA_SOURCE"
if ($env:CHAN_QUANT_MARKET_BREADTH_PACKAGE_PATH) {
    Write-Host "Market breadth package: $env:CHAN_QUANT_MARKET_BREADTH_PACKAGE_PATH"
}
else {
    Write-Host "Market breadth package: not configured (the panel will fail closed)"
}
Write-Host "Page: http://127.0.0.1:5173/"
Write-Host "Press Ctrl+C to stop both backend and frontend."

try {
    $BackendProcess = Start-Process `
        -FilePath $UvCommand `
        -ArgumentList @("run", "uvicorn", "chan_quant.api.app:app", "--host", "127.0.0.1", "--port", "8000") `
        -WorkingDirectory $BackendDir `
        -NoNewWindow `
        -PassThru

    $FrontendProcess = Start-Process `
        -FilePath $NpmCommand `
        -ArgumentList @("run", "dev", "--", "--host", "127.0.0.1", "--port", "5173") `
        -WorkingDirectory $FrontendDir `
        -NoNewWindow `
        -PassThru

    while ($true) {
        Start-Sleep -Seconds 1
        $BackendProcess.Refresh()
        $FrontendProcess.Refresh()

        if ($BackendProcess.HasExited) {
            Write-Error "Backend process exited with code $($BackendProcess.ExitCode); stopping frontend."
        }

        if ($FrontendProcess.HasExited) {
            Write-Error "Frontend process exited with code $($FrontendProcess.ExitCode); stopping backend."
        }
    }
}
finally {
    Stop-ChildProcess $BackendProcess
    Stop-ChildProcess $FrontendProcess
}
