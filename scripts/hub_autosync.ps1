# NAQUUUU hub auto-sync (Windows laptop).
# Drives: sanitization gate -> commit -> pull --rebase -> push.
# Intended to run from Windows Task Scheduler every ~10 minutes.
# No secrets in this file.

$ErrorActionPreference = "Continue"
$hub = "C:\personal\naquuuu"

if (-not (Test-Path "$hub\.git")) { exit 0 }
Set-Location $hub
if (-not (git status --porcelain)) { exit 0 }

python scripts/verify_sanitization.py
if ($LASTEXITCODE -ne 0) {
    Write-Output "auto-sync: sanitization gate FAILED - not committing"
    exit 1
}

git add -A
git commit --quiet -m "chore(sync): $env:COMPUTERNAME $(Get-Date -Format 'yyyy-MM-dd HH:mm')"

git pull --rebase --autostash --quiet
if ($LASTEXITCODE -ne 0) {
    git rebase --abort
    Write-Output "auto-sync: pull/rebase conflict - tree left for manual review"
    exit 1
}

git push --quiet
