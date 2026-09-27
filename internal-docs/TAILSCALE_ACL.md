# Tailnet ACL Hardening (tag:personal + default-deny)

- Purpose: stop work machines on the tailnet from reaching the personal relay host and worker.
- Status: **drafted, NOT applied**. The current tailnet policy lets nodes reach each other by default.
- Related: `internal-docs/HOSTS.md` Sections 2, 3, 7; `internal-docs/relay/M2_DISPATCH_RUNBOOK.md`; `internal-docs/relay/VPS_RELAY_RUNBOOK.md`; `internal-docs/DECISION_LOG.md` ADR-020, ADR-026, ADR-029.
- Scope: tailnet access control only. It does not replace host firewalls (UFW on the VPS), SSH key policy, or the Tier 1 boundary.

## 1. Problem

The tailnet mixes the owner's work machines with personal devices. Personal devices are the laptop, the phone, the VPS relay, and the home server (`mipad-linux`). With no ACL restrictions, every node on the tailnet can reach every other node, including the SSH and RDP surfaces on the personal hosts. Work machines (described generically here; no corporate identifiers enter this repo, per AGENTS.md Critical Rule 2) share the same tailnet.

## 2. Goal

Only personal devices reach the personal hosts:

- Work machines get no access to the VPS relay, the home server, or any personal device.
- Personal devices reach personal hosts over SSH, including the M2 relay-to-worker hop.
- The phone reaches the laptop over RDP, scoped to the Tailscale interface (ADR-020). The RDP grant is scoped to the phone and laptop tags, not to every personal device.
- Everything else is denied by default.

Approach: tag every personal device `tag:personal` for the SSH grant, add `tag:phone` to the phone and `tag:laptop` to the laptop for the RDP grant, and define only the explicit grants below. An untagged node (every work machine) matches no rule, so default-deny applies to it. A node may carry more than one tag, and a selector matches if any advertised tag matches. Naming the RDP endpoints keeps the grant equal to the stated goal (phone -> laptop); if a broader personal-to-personal RDP grant is ever intended, that must be stated explicitly.

## 3. Policy (HuJSON)

Paste the block below into the Tailscale admin console access controls. Comments use HuJSON `//`.

```jsonc
{
  // Only tailnet admins may assign these tags.
  "tagOwners": {
    "tag:personal": ["autogroup:admin"],
    "tag:phone": ["autogroup:admin"],
    "tag:laptop": ["autogroup:admin"]
  },

  // Default-deny: once any ACL file exists, traffic that matches no rule is
  // denied. Work machines stay untagged, so they match nothing below.
  "acls": [
    // Personal devices may reach personal devices over SSH. This covers the
    // M2 relay -> worker hop and owner SSH from the phone.
    {
      "action": "accept",
      "src": ["tag:personal"],
      "dst": ["tag:personal:22"]
    },
    // Phone -> laptop RDP only, scoped to the Tailscale interface (ADR-020).
    // The phone carries tag:phone; the laptop carries tag:laptop. This grant
    // does not open RDP between arbitrary personal devices.
    {
      "action": "accept",
      "src": ["tag:phone"],
      "dst": ["tag:laptop:3389"]
    }
  ],

  // Tailscale SSH grants; only active if `tailscale set --ssh` is enabled on
  // the target. Plain OpenSSH (the M2 path) is governed by the "acls" rule above.
  "ssh": [
    {
      "action": "accept",
      "src": ["tag:personal"],
      "dst": ["tag:personal"],
      "users": ["autogroup:nonroot", "root"]
    }
  ]
}
```

There is no catch-all `accept` and no explicit deny entry; unmatched traffic is denied by default. Tailnet ACLs govern tailnet traffic only, not a node's own outbound internet path (the relay's WhatsApp connection is unaffected unless an exit node is introduced).

## 4. Apply (owner console steps)

1. Sign in to the Tailscale admin console and open Access controls.
2. Tag the devices. A node may carry more than one tag.
   - Laptop: `sudo tailscale up --advertise-tags=tag:personal,tag:laptop` and complete the re-auth prompt.
   - Phone: add `tag:personal` and `tag:phone` during the portal re-auth flow or in the app's device settings (the app may not accept `--advertise-tags`).
   - VPS relay: `sudo tailscale up --advertise-tags=tag:personal` and complete the re-auth prompt.
   - Home server (`mipad-linux`): `sudo tailscale up --advertise-tags=tag:personal` and complete the re-auth prompt.
   Tag reassignment changes node identity (Section 6).
3. Paste the policy from Section 3 into Access controls and save it. Work machines stay untagged, so they match no rule and are denied by default.
4. Validate in the console ACL tester before trusting the policy: work machine -> VPS:22 (expect deny); personal device -> VPS:22 (expect accept); phone -> laptop:3389 (expect accept); a non-phone personal device -> laptop:3389 (expect deny). The console reports HuJSON parse errors inline.
5. ACL changes take effect within seconds.
6. If Tailscale SSH (not plain OpenSSH) is wanted on a target, run `sudo tailscale set --ssh` there; otherwise only the `acls` rule applies.
7. Verify from both sides (Section 5).

## 5. Verification

- On a personal device: `tailscale debug prefs` shows the local preferences and the advertised tag; confirm `tag:personal` is present.
- On a personal device: `tailscale status` lists the expected nodes.
- Accept check: from a personal device, `tailscale ping mipad-linux` and a key-only SSH login succeed.
- Deny check: from a work machine, a tailnet SSH/RDP attempt to the VPS or home server is refused. A connection refusal is enough; do not run destructive tests.
- Authoritative check: the admin console ACL tester, used before trusting the policy.

## 6. Caveats

- Tag reassignment drops node identity: a tagged node uses a tagged node key and a new ACL identity, existing sessions may drop, and the node may need re-authentication. Apply when a brief reconnect is acceptable.
- Default-deny is a property of the whole ACL file, not of one rule; review the full policy, and remember that legacy or leftover broad rules can still allow access.
- ACLs do not replace host firewalls, OS SSH configuration, or key policy; keep UFW and key-only SSH in place (`VPS_RELAY_RUNBOOK.md` Security notes).
- `tag:personal` must be assigned at authentication time; the `tagOwners` entry lets admins do it. Keep personal identifiers (login emails) out of this repo.
- The M2 relay-to-worker hop is personal-to-personal and is covered by the port-22 grant; if the worker is ever placed behind a different tag, this policy must be updated in the same change.
- The RDP grant is phone -> laptop only (`tag:phone` -> `tag:laptop:3389`); it does not make RDP reachable to every personal device.
- Untagged nodes (every work machine) match no rule, so default-deny applies to them; keep work machines untagged and remember that a broad legacy rule can still allow access.
- Test with `tailscale debug prefs` (local tag/prefs) and the admin-console ACL tester; a successful SSH to a personal host is not proof that work machines are denied.

## 7. Open questions

1. Is the intended boundary both-directions deny (this draft), or should personal devices also reach work machines for any reason?
2. Are any personal services other than SSH (22) and RDP (3389) exposed over the tailnet that need an explicit grant?
3. Should Tailscale SSH (`tailscale set --ssh`) be used, or only the OS sshd governed by the `acls` rule?
4. Does the current phone app expose an `--advertise-tags` equivalent, or is the portal re-auth flow required in every case?
