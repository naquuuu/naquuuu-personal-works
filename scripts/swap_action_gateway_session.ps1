# NAQUUUU: swap the Action Gateway MCP session endpoint in the global opencode config.
# Prompts for the new URL so it never appears in chat or docs. Backs up the config first.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\swap_action_gateway_session.ps1
$cfg = Join-Path $env:USERPROFILE ".config\opencode\opencode.jsonc"
if (-not (Test-Path $cfg)) { Write-Error "config not found: $cfg"; exit 1 }

$new = Read-Host "Paste the new Action Gateway MCP endpoint URL"
if ($new -notmatch '^https://actions\.do-ai\.run/mcp/session/') {
    Write-Error "That does not look like an Action Gateway session URL."
    exit 1
}

$text = Get-Content -Raw $cfg
$rx = [regex]'https://actions\.do-ai\.run/mcp/session/[^"]+'
$count = $rx.Matches($text).Count
if ($count -eq 0) {
    Write-Error "No existing action-gateway session URL found in the config."
    exit 1
}

Copy-Item $cfg "$cfg.bak" -Force
[IO.File]::WriteAllText($cfg, $rx.Replace($text, $new, 1))
"Replaced the action-gateway session URL ($count occurrence(s) found)."
"Backup: $cfg.bak"
"The URL was not printed anywhere."
