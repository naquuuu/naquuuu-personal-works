# Hermes activity integration — 2026-10-05

## Shipped

Native Hermes dashboard Agents tab at `/agents`; the existing dashboard authentication and plugin navigation remain authoritative. Short role names and one-line descriptions, aggregate task/tool/file/error counts, responsive cards, explicit empty/stale/connection states, and ten-second refresh. No session IDs, paths, task text, commands, or conversation content leave the new API. Telemetry freshness is a five-minute file-age heuristic, not proof a task is currently running; this view is OpenCode-only.

Two user themes (`naquuuu-light`, `naquuuu-dark`) match the blog's current warm paper / espresso-maroon colors, crimson accents, hairlines, and font stacks. Dark is selected initially; use the existing Hermes theme picker to switch. The blog itself was not edited. Font names use local fallbacks; no new remote font dependency is introduced.

The local session visualizer has shorter copy, persisted light/dark mode, hidden crossing arrows on smaller screens, compact session metadata, and corrected filename joining (the old renderer joined individual characters).

## Verification

- 55 targeted relay/activity unit tests passed; synthetic aggregate canary fields are excluded.
- Native component fixture: eight light/dark viewport checks at 320, 390, 768, and 1440px, seven cards, no horizontal overflow. Mobile dark and desktop light screenshots visually reviewed. This is a synthetic component fixture, not authenticated live browser acceptance.
- Dashboard plugin discovered, both themes discovered, static bundle returned 200, unauthenticated activity API returned 401. Dashboard-only restart kept the gateway active.
- Backup: `/home/ubuntu/.local/share/naquuuu/dashboard-backups/20261005-111046/`; private config backup remains host-only. Versioned source: `dashboard-plugin/`, `dashboard-themes/`, and `scripts/hermes_agent_activity.py`.

## Relay and audit follow-through

A single-invocation wrapper, final assistant-event selection, image-cache containment/signature validation, uncertain-delivery replay stop, explicit paused typing, and a 15-second presence safety lease were deployed. Preflight compared public source hashes, parsed Python, checked Node syntax, and backed up files before writes. Backup manifest: `/home/ubuntu/.local/share/naquuuu/relay-guard-backups/20261005-112115/manifest.json`. Actual adapter first/later failed-chunk stubs, bridge paused/lease route stubs, and installed group send/poll/silence canaries passed. Gateway active, restart counter zero, bridge health status connected. No real message was sent.

Multi-repo audit now fails when a repository is behind or Git status/fetch/count probes fail, rather than claiming clean. Six mocked audit cases passed. STATUS and LESSONS were semantically reconciled through ADR-043. Six unapproved contact occurrences in the archived portfolio HTML were redacted with zero remaining text findings; published portfolio source was not changed.

## Remaining acceptance and Git work

Authenticated owner-device navigation, off-tailnet access rejection, a designated real WhatsApp test for exactly one reply and cleared typing, worker trust/dispatch/artifact return, standby migration, and authorized model comparisons remain unverified or blocked by their documented prerequisites. No new worker was activated and no paid benchmark was started.

Strict audit still fails for the dirty/diverged hub and dirty independent portfolio. Main is six local commits ahead / four remote behind; the committed histories merge cleanly, but four dirty paths overlap remote changes. Preserve those edits and reconcile before publishing. The blog is clean and its existing QA passed. `naquuuu-term` has no remote/upstream; do not invent one. No commits or pushes were made: the orchestrator persona explicitly requires user commit approval.
