# Relay trust pass deployment receipt

**Date:** 2026-10-13
**Related:** ADR-047, `L-33`, `L-34`, `BOT_IMPROVEMENT_BACKLOG.md`

## Scope and behavior

One inbound message yields at most one final user-visible reply. The adapter `send()` path claims a turn keyed by (chat, inbound message id) before posting; duplicate attempts (retry events, double fallback paths) become a success no-op, and a definite unconfirmed send releases the claim so exactly one plain failure line can still go out. An identical fallback line (`Jawaban belum bisa ditampilkan...`) is delivered at most once per turn inside a 120-second window. Routine model, provider, failover, health, and gateway notices are blocked across send, edit, and proactive paths unless the service is genuinely down or the current message explicitly asks for status (grant bound to that message, 10 minutes, max 128). Ordinary replies carry a ~20 sentence ceiling with fenced blocks exempt; requested text art and repeat counts keep their existing 3,600-character / 100-repeat bounds; consecutive token floods (6+ repeats) are rejected. The persona carries the tone-control, joining, one-reply, notice, and statelessness rules after a curator taste pass. `relay/CONTEXT_LIMITS.md` documents capability, memory requirements, and the bounded option.

## Repository changes (hub, uncommitted)

- `scripts/relay_outbound.py` (work hash `4ce050eb4e4525ae`): notice class, status-ask grammar, sentence ceiling, token-flood rule.
- `scripts/wa_chat_policy.py` (`799b5b23ac7d7167`): final-reply claim/release, failure-line dedupe, status-request grants, notice allowance plumbing.
- `scripts/install_wa_final_reply.py` (new): anchored send-path patch, idempotent, AST-validated.
- `scripts/verify_wa_group_guard_source.py`: send stubs now prove duplicate suppression and single-failure behavior.
- `scripts/wa_eval.py` + `scripts/test_wa_eval.py` (new): ten anonymized ID/EN cases; recorded failures stay caught.
- `scripts/verify_soul_mirror.py` (new): hash-only persona mirror check and apply with host backup.
- `scripts/test_install_wa_final_reply.py`, `test_relay_outbound.py`, `test_wa_chat_policy.py`: new regressions.
- `scripts/sync_all_repos.py`: `wa_eval.py` now runs inside `--strict`.
- `internal-docs/relay/WHATSAPP_SOUL.md`, `internal-docs/relay/README.md`, `internal-docs/relay/CONTEXT_LIMITS.md`.

## Deployment (relay host, overlay-only)

The clone was not written to: the `naquuuu-autosync.timer` was verified active and must never publish unreviewed code.

1. Preflight confirmed the overlay copies matched repo HEAD exactly (`relay_outbound.py` `456e9d8aeda1579d`, `wa_chat_policy.py` `0c24dd383b71f8fb`), so the delta was clean.
2. Backup: `~/.local/share/naquuuu/relay-guard-backups/20261013-160411-%f/overlay/` holds the pre-change `relay_outbound.py`, `wa_chat_policy.py`, and `verify_wa_group_guard_source.py`.
3. Overlay updated at `~/.local/share/naquuuu/relay-guards/`; verification staging at `~/.local/share/naquuuu/relay-verify/` (15 files).
4. Host unit tests: 55 tests OK; eval set on host: `eval_cases=10 caught=10 clean=10`, `relay_eval=pass`.
5. Adapter patch: `final_reply_source_contract=pass`, applied (1 file changed, timestamped `.bak` beside it), `adapter.py` compiles, marker count 1.
6. Source stubs against the patched checkout: `actual_source_send_poll_stubs=pass; normal_queued_crash_silence=pass; synthetic_canary=pass; final_reply_single_turn=pass`.
7. Persona mirror: applied with host backup, final hash matches on both sides (`soul_repo_sha256=6e53ed1ec679a222`, `soul_host_sha256=6e53ed1ec679a222`, `soul_mirror=match`).
8. One gateway restart: `active`, `gateway_restarts=0`, `bridge_port=up`, `bridge_health_connected=true`, `startup_errors=0`.

## Live canary (owner-verified)

Owner sent one DM greeting and one @mention in the designated test group. Result as observed by the owner: exactly one reply to each, typing indicator cleared. Post-canary host counters: gateway active, restarts 0, provider 503/429/timeout counts 0, leak blocks 0, bridge up. The dual-provider failure arm cannot be forced safely on a live host; it is proven by the send-path stubs only and is documented as such.

## Incident during rollout

The first `verify_soul_mirror.py --apply` used a double-`repr` template and wrote an escaped one-line SOUL.md for about ninety seconds. The next hash check showed drift; the pre-change host backup (`SOUL.md.bak-20261013-160452`) held the exact previous persona, the script was fixed, and the re-apply matched. Recorded as `L-34`. No message is known to have been produced from the corrupt window; the gateway restart happened after the fix.

## Rollback

1. Restore overlay files from `~/.local/share/naquuuu/relay-guard-backups/20261013-160411-%f/overlay/` into `~/.local/share/naquuuu/relay-guards/`.
2. Restore the adapter from its timestamped `adapter.py.bak-*` created by `install_wa_final_reply.py`.
3. Restore the persona from the newest known-good `~/.hermes/SOUL.md.bak-20261013-160452`, or re-apply the repo block with the fixed script.
4. `systemctl --user restart hermes-gateway.service` once, then confirm active status, bridge health, and zero startup errors.
5. Do not delete any backup. Re-run `python scripts/verify_soul_mirror.py` and `python3 verify_wa_group_guard_source.py --hermes-repo ~/.hermes/hermes-agent` to confirm state.
