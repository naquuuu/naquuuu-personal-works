# Lessons (curated)
<!-- verified-against: ADR-034 -->

Short, append-only. Agents read this first together with `STATUS.md` — it exists so we do not re-read everything. Route through `internal-docs/INDEX.md` first; this file is the hot slice, not the archive.

**IDs.** `L-nn`, permanent, assigned in order, never renumbered or reused. Cite a lesson as `L-nn`, never by ordinal. ADR-030 §Consequences cites "lesson 13" by ordinal; that entry is `L-13`, order unchanged.

**Compaction.** When this file exceeds ~5,000 chars, roll the oldest entries into `internal-docs/lessons/YYYY-MM.md` and keep the recent hot set here. The first compaction moved L-01 through L-19 to the September archive on 2026-09-28.

Archived L-01 through L-19: [September archive](lessons/2026-09.md). IDs remain permanent.

L-20. Verify adapter dependencies before extending timeouts (Astra recovery, 2026-09-28). The live gateway already had `HERMES_GATEWAY_PLATFORM_CONNECT_TIMEOUT=180` in both its process environment and persistent drop-in. Its venv lacked `aiohttp`; `_poll_bridge_health` swallowed the import error and reported an HTTP startup timeout while the Node bridge connected successfully. Installed the checkout-pinned `aiohttp==3.14.3` into the existing venv and restarted the service. At 19:32:48 WIB the gateway logged `whatsapp connected`, followed by `Gateway running with 1 platform(s)` at 19:32:49. This corrects L-19's unproven hardware-only diagnosis and completes L-18's dependency recovery for bridge health polling. No code update or re-pair was needed. Phone message round-trip remains pending owner verification.

L-21. Relay verified end to end (2026-09-28, evening). Owner message round-trip confirmed: the bot replied and executed, closing L-20's open item. Full stack proven in one shot - session, bridge, gateway, owner gate, `opencode run`. The day's complete chain: (1) two hosts on one session plus `Restart=always` caused the outage (L-17); (2) an interrupted `hermes update` broke the environment (L-18); (3) a missing `aiohttp` masqueraded as timeouts (L-20, correcting L-19). Rule: when a health check reports a timeout, first prove the check itself can run - a swallowed import error and a slow host produce identical log lines. Do not run `hermes update` on the relay host.

L-22. Blog diagrams must follow "Architectural Blueprint on Warm Paper" (2026-09-29). Avoid dark terminal/SaaS whiteboard boxes (`#111110`) on blog essays. Use warm paper grounds (`var(--bg-surface)` / `#ece8dd`), subtle hairline borders, muted analog washes (terracotta, slate, sage), and strictly lowercase SVG labels per `STYLE_BIBLE.md`. Involve `naquuuu-curator` for aesthetic vetting on blog visual artifacts.

## Open questions

1. Compaction completed 2026-09-28 under ASTRA_ONESHOT authorization; L-01 through L-19 moved with stable IDs and L-13 remains resolvable in the archive.
2. Resolved 2026-09-28: the recovery order in `L-17` now lives in `internal-docs/relay/VPS_RELAY_RUNBOOK.md`, section "Relay recovery (2026-09-28 outage)", together with a symptom-to-cause table. It remains derived from one observed incident, not a rehearsed procedure - treat it as the documented intent and re-verify after the next real recovery.
