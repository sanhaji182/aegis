# aegis.ps1 — Windows PowerShell launcher.
#
# Usage:
#   .\aegis.ps1                      (reads ~/.aegis/prompt.txt)
#   .\aegis.ps1 -Args "your prompt"  (inline payload)
#
# For full argument pass-through, the .cmd file is more reliable. This
# script exists because some Windows users prefer ps1 over bat.

param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = (Resolve-Path "$ScriptDir\..\..").Path

$aegis = Get-Command aegis -ErrorAction SilentlyContinue
if ($aegis) {
    & aegis @Args
    exit $LASTEXITCODE
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "[!] python not on PATH. Install Python 3.10+." -ForegroundColor Red
    exit 2
}

$PyScript = Join-Path $Root "aegis.py"
if (-not (Test-Path $PyScript)) {
    Write-Host "[!] aegis.py not found at $PyScript" -ForegroundColor Red
    exit 2
}

Push-Location $Root
try {
    & python $PyScript @Args
} finally {
    Pop-Location
}
exit $LASTEXITCODE
