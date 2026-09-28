# NAQUUUU hub auto-sync (Windows laptop).
# Drives: stage -> sanitization gate (--staged) -> commit -> pull --rebase -> push.
# Intended to run from Windows Task Scheduler every ~10 minutes.
# No secrets in this file.
#
# The gate FAILS CLOSED: a missing gate script or a missing Python 3 means
# nothing is committed (LESSONS.md item 4 - auto-sync once published an
# invalid model pin because a gate silently did not run). The one deliberate
# escape hatch is $env:NAQUUUU_ALLOW_UNGATED_SYNC = "1", which warns on use.
#
# Order matters: 'git add -A' runs BEFORE the gate, and the gate runs with
# --staged so it audits the INDEX. A file an agent just created is untracked, so
# a tracked-files gate would skip it and the following commit would publish it
# unaudited. Consequence, on purpose: a gate failure leaves the offending files
# STAGED, not unstaged, and the message says how to unstage. Nothing is
# auto-unstaged - the staged index is the evidence of what was about to go out.

$ErrorActionPreference = "Continue"

# Workspace root: the env var wins (AGENTS.md Section 7 item 7); the old
# hardcoded path is only a fallback and is reported as such.
if ($env:NAQUUUU_WORKSPACE) {
    $hub = $env:NAQUUUU_WORKSPACE
    $hubSource = "NAQUUUU_WORKSPACE"
} else {
    $hub = "C:\personal\naquuuu"
    $hubSource = "hardcoded fallback (NAQUUUU_WORKSPACE is not set)"
}
Write-Output "auto-sync: hub root = $hub (source: $hubSource)"

if (-not (Test-Path (Join-Path $hub ".git"))) {
    Write-Output "auto-sync: WARNING - no git repository at '$hub' (source: $hubSource); nothing was synced"
    Write-Output "auto-sync: set NAQUUUU_WORKSPACE to the hub root and re-run - this is a broken path, not a healthy sync"
    exit 1
}
Set-Location $hub

git fetch --quiet origin main

if (git status --porcelain) {
    # Stage BEFORE the gate so the audit covers new, previously untracked files.
    git add -A
    if ($env:NAQUUUU_ALLOW_UNGATED_SYNC -eq "1") {
        Write-Output "auto-sync: WARNING - NAQUUUU_ALLOW_UNGATED_SYNC=1 is set; committing WITHOUT the sanitization gate"
    } else {
        $gateScript = "scripts\verify_sanitization.py"
        if (-not (Test-Path $gateScript)) {
            Write-Output "auto-sync: BLOCKED (gate script missing) - $gateScript is not in $hub; refusing to commit ungated"
            Write-Output "auto-sync: fix with 'git checkout -- $gateScript', or set NAQUUUU_ALLOW_UNGATED_SYNC=1 to override deliberately"
            Write-Output "auto-sync: changes are STAGED (staging happens before the gate); inspect with 'git diff --cached', unstage with 'git restore --staged .' (or 'git reset')"
            exit 1
        }
        $py = $null
        foreach ($candidate in @("python", "python3", "py")) {
            if (-not (Get-Command $candidate -ErrorAction SilentlyContinue)) { continue }
            & $candidate -c "import sys; sys.exit(0 if sys.version_info[0] >= 3 else 1)" 2>$null | Out-Null
            if ($LASTEXITCODE -eq 0) { $py = $candidate; break }
        }
        if (-not $py) {
            Write-Output "auto-sync: BLOCKED (no interpreter) - no working Python 3 found, so the sanitization gate cannot run; refusing to commit ungated"
            Write-Output "auto-sync: install Python 3 (and put it on PATH), or set NAQUUUU_ALLOW_UNGATED_SYNC=1 to override deliberately"
            Write-Output "auto-sync: changes are STAGED (staging happens before the gate); inspect with 'git diff --cached', unstage with 'git restore --staged .' (or 'git reset')"
            exit 1
        }
        & $py scripts/verify_sanitization.py --staged
        if ($LASTEXITCODE -ne 0) {
            Write-Output "auto-sync: sanitization gate FAILED (exit $LASTEXITCODE) - not committing"
            Write-Output "auto-sync: re-run '$py scripts/verify_sanitization.py --staged' for the full report on the same snapshot"
            Write-Output "auto-sync: the staged files are still STAGED (evidence of what was about to be published):"
            Write-Output "auto-sync:   inspect with 'git diff --cached'"
            Write-Output "auto-sync:   unstage with 'git restore --staged .' (or 'git reset' on older git)"
            exit 1
        }
    }
    git commit --quiet -m "chore(sync): hub $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
}

git rebase --autostash --quiet origin/main
if ($LASTEXITCODE -ne 0) {
    git rebase --abort
    Write-Output "auto-sync: rebase conflict - tree left for manual review"
    exit 1
}

# Push outcome is reported, never discarded. A read-only node failing to push
# stays non-fatal (ADR-025); anything else is logged with git's own stderr.
$pushOutput = git push --quiet origin main 2>&1
$pushCode = $LASTEXITCODE
if ($pushCode -eq 0) {
    Write-Output "auto-sync: push OK (origin/main)"
} else {
    $pushText = ($pushOutput | Out-String)
    if ($pushText -match "Permission denied|could not read Username|Authentication failed|403 Forbidden|write access| denied to ") {
        Write-Output "auto-sync: push failed: not a writer (expected on a read-only node), exit $pushCode"
    } else {
        Write-Output "auto-sync: push failed: real error, exit $pushCode"
    }
    foreach ($line in @($pushOutput)) {
        $text = "$line".Trim()
        # PS 5.1 wraps native stderr chunks; skip the type-name noise, keep the text.
        if ($text -and $text -notmatch "^System\.Management\.Automation\.") { Write-Output "auto-sync:   $text" }
    }
}
exit 0
