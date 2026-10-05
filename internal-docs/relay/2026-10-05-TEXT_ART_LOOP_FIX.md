# Text art and quiet group behavior deployment receipt

**Date:** 2026-10-05

## Scope and behavior

WhatsApp supports user-requested bounded text art and phrase repetition up to 3,600 characters and 100 repeats, with the exact inbound ID carried into the outbound `replyTo`. At most 128 request grants are retained, each expiring after 10 minutes. Runtime filters unaddressed idle group statuses and keeps `NO_REPLY` only for WhatsApp groups. Direct messages and other platforms retain their prior behavior. Casual WhatsApp text art is handled directly; the locally changed `scripts/relay_run.py` was not deployed, and the canonical runtime wrapper was not changed.

## Deployment

The helper overlay was deployed under `$HOME/.local/share/naquuuu/relay-guards/`: `relay_outbound.py`, `wa_chat_policy.py`, `wa_group_guard.py`, `install_wa_group_guard.py`, and `verify_wa_group_guard_source.py`.

Patched Hermes source files: `gateway/run_turn.py`, `gateway/run_startup.py`, and `plugins/platforms/whatsapp/adapter.py`. The fenced persona content from `internal-docs/relay/WHATSAPP_SOUL.md` was mirrored.

Regression verification passed: 49 targeted tests; sanitization passed, scanning 11 changed or new Python files with zero findings. Patched source stubs passed for normal, queued, and crash group silence and send/poll behavior. Synthetic leak and identity canaries passed.

The workspace strict multi-repo audit failed because the preserved hub is dirty/diverged, an existing child repo is dirty, and the `STATUS.md` and `LESSONS.md` digests are stale. These audit findings are separate from the passing targeted tests and sanitization scan.

The gateway was restarted once and is active with `NRestarts=0`; bridge health reported `connected=true`, with no startup import errors. No real test messages were sent, so phone conversation end-to-end behavior is unverified.

## Rollback

Backup manifest: `$HOME/.local/share/naquuuu/relay-guard-backups/20261005-082347-469119/manifest.json`. It contains file paths and source backups only, with no raw identifiers, keys, or messages.

To roll back, use a short Python script to read that manifest, validate each listed destination against the deployed files in this receipt, and restore each corresponding backup with `shutil.copy2`. Refuse any destination outside that explicit allowlist, stop if a listed backup is missing, and do not delete files. Then restart the gateway using the established relay runbook and confirm active status, connected bridge health, and no startup import errors. Leave the local-only `scripts/relay_run.py` change untouched.

No public commit or push was made.
