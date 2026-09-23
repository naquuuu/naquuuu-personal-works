#Requires -RunAsAdministrator
# NAQUUUU remote access setup (Phase 3D)
# Installs OpenSSH Server + enables RDP, both reachable ONLY over the Tailscale
# interface. Run in an elevated PowerShell after `tailscale up` has signed in.
# All output is logged to %TEMP%\naquuuu-remote-setup.log.
$ErrorActionPreference = "Stop"
$log = "$env:TEMP\naquuuu-remote-setup.log"
Start-Transcript -Path $log -Force | Out-Null

try {
    Write-Host "== NAQUUUU remote access setup ==" -ForegroundColor Cyan

    # 0. Tailscale must be logged in and have an IPv4 address.
    $tsExe = "$env:ProgramFiles\Tailscale\tailscale.exe"
    if (-not (Test-Path $tsExe)) { throw "Tailscale not found at $tsExe" }
    $ts = & $tsExe ip -4 2>$null | Select-Object -First 1
    if (-not $ts) { throw "Tailscale has no IPv4 address yet. Run 'tailscale up' first, then re-run this script." }
    Write-Host "Tailscale IP: $ts"

    # 1. OpenSSH Server
    $cap = Get-WindowsCapability -Online -Name "OpenSSH.Server*"
    if ($cap.State -ne "Installed") {
        Write-Host "Installing OpenSSH Server..."
        Add-WindowsCapability -Online -Name $cap.Name | Out-Null
    }
    Set-Service sshd -StartupType Automatic
    Start-Service sshd
    Write-Host "OpenSSH Server running."

    # 2. Bind sshd to the Tailscale IP only (idempotent)
    $cfg = "$env:ProgramData\ssh\sshd_config"
    $marker = "# NAQUUUU: tailnet-only binding"
    $existing = Get-Content -Path $cfg -ErrorAction SilentlyContinue
    if ($existing -notmatch [regex]::Escape($marker)) {
        Add-Content -Path $cfg -Value "`r`n$marker`r`nListenAddress $ts"
    }
    Restart-Service sshd
    Write-Host "sshd bound to $ts."

    # 3. Firewall: Tailscale-interface-only rules; built-in wide rules disabled.
    Disable-NetFirewallRule -DisplayGroup "OpenSSH Server" -ErrorAction SilentlyContinue
    Remove-NetFirewallRule -DisplayName "NAQUUUU SSH (Tailscale)" -ErrorAction SilentlyContinue
    New-NetFirewallRule -DisplayName "NAQUUUU SSH (Tailscale)" -Direction Inbound -Action Allow `
        -Protocol TCP -LocalPort 22 -InterfaceAlias "Tailscale" | Out-Null

    # 4. RDP enable + Tailscale-scoped rule.
    Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server" -Name fDenyTSConnections -Value 0
    Disable-NetFirewallRule -DisplayGroup "Remote Desktop" -ErrorAction SilentlyContinue
    Remove-NetFirewallRule -DisplayName "NAQUUUU RDP (Tailscale)" -ErrorAction SilentlyContinue
    New-NetFirewallRule -DisplayName "NAQUUUU RDP (Tailscale)" -Direction Inbound -Action Allow `
        -Protocol TCP -LocalPort 3389 -InterfaceAlias "Tailscale" | Out-Null

    # 5. NLA off on RDP-Tcp (required for Azure AD account sign-in over RDP).
    Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp" -Name UserAuthentication -Value 0
    Restart-Service TermService -Force
    Start-Sleep -Seconds 3

    Write-Host ""
    Write-Host "Done. SSH (port 22) and RDP (port 3389) are reachable only over Tailscale ($ts)." -ForegroundColor Green
    Write-Host "Next: connect from the phone (SSH/RDP) to $ts."
} catch {
    Write-Host ""
    Write-Host "FAILED: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Full log: $log"
} finally {
    Stop-Transcript | Out-Null
}
