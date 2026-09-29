# Lessons (curated)
<!-- verified-against: ADR-040 -->

Short, append-only. Agents read this first together with `STATUS.md` — it exists so we do not re-read everything. Route through `internal-docs/INDEX.md` first; this file is the hot slice, not the archive.

**IDs.** `L-nn`, permanent, assigned in order, never renumbered or reused. Cite a lesson as `L-nn`, never by ordinal. ADR-030 §Consequences cites "lesson 13" by ordinal; that entry is `L-13`, order unchanged.

**Compaction.** When this file exceeds ~5,000 chars, roll the oldest entries into `internal-docs/lessons/YYYY-MM.md` and keep the recent hot set here. The first compaction moved L-01 through L-19 to the September archive on 2026-09-28.

Archived L-01 through L-19: [September archive](lessons/2026-09.md). IDs remain permanent.

L-20. Verify adapter dependencies before extending timeouts (Astra recovery, 2026-09-28). The live gateway already had `HERMES_GATEWAY_PLATFORM_CONNECT_TIMEOUT=180` in both its process environment and persistent drop-in. Its venv lacked `aiohttp`; `_poll_bridge_health` swallowed the import error and reported an HTTP startup timeout while the Node bridge connected successfully. Installed the checkout-pinned `aiohttp==3.14.3` into the existing venv and restarted the service. At 19:32:48 WIB the gateway logged `whatsapp connected`, followed by `Gateway running with 1 platform(s)` at 19:32:49. This corrects L-19's unproven hardware-only diagnosis and completes L-18's dependency recovery for bridge health polling. No code update or re-pair was needed. Phone message round-trip remains pending owner verification.

L-21. Relay verified end to end (2026-09-28, evening). Owner message round-trip confirmed: the bot replied and executed, closing L-20's open item. Full stack proven in one shot - session, bridge, gateway, owner gate, `opencode run`. The day's complete chain: (1) two hosts on one session plus `Restart=always` caused the outage (L-17); (2) an interrupted `hermes update` broke the environment (L-18); (3) a missing `aiohttp` masqueraded as timeouts (L-20, correcting L-19). Rule: when a health check reports a timeout, first prove the check itself can run - a swallowed import error and a slow host produce identical log lines. Do not run `hermes update` on the relay host.

L-22. Blog diagrams must follow "Architectural Blueprint on Warm Paper" (2026-09-29). Avoid dark terminal/SaaS whiteboard boxes (`#111110`) on blog essays. Use warm paper grounds (`var(--bg-surface)` / `#ece8dd`), subtle hairline borders, muted analog washes (terracotta, slate, sage), and strictly lowercase SVG labels per `STYLE_BIBLE.md`. Involve `naquuuu-curator` for aesthetic vetting on blog visual artifacts.

L-23. Bump the asset version on every css/js edit (2026-09-30). After `blog/assets/js/main.js` was fixed, the browser kept running the cached old file because the `?v=` asset version was not bumped, so a fixed autoplay bug looked unfixed during testing. Bump the version in every reference (and the gate constant, `STYLE_BIBLE.md` 5.3) in the same change, before testing.

L-24. Gate every audio auto-resume path on an explicit user click (2026-09-30). Handlers for `visibilitychange`, pause recovery and spotify resume must check a flag set only by the visitor clicking the sound pill; the hero song is off by default (ADR-038). An ungated resume handler is autoplay by another name.

L-25. The ctrl+k palette must switch lens before scrolling (2026-09-30). In-page anchors can live inside a hidden lens panel, so scrolling to them without first activating that lens lands on nothing. Any new jump target added to `blog/assets/js/palette.js` needs its owning lens resolved first.

L-26. Blank screenshots of scrolled regions in the browser pane are a tooling artifact, not a page bug (2026-09-30). Measure layout with javascript, or set a tall viewport (for example 390x2600) and screenshot at scroll 0.

L-27. Blog visual work runs curator-in-the-loop with strict roles (2026-09-30). Owner rule: every part involves `naquuuu-curator`, and each subagent stays in its role: curator reviews taste, builder edits, skeptic challenges, verifier gates, scribe documents. Owner taste rejections from this pass ("too gimmicky" proof strip, "too ai" glowing toggle, frosted pills) are canon in `STYLE_BIBLE.md` 2.9; flowchart shape and legend rules are in 2.8.

## Open questions

1. Compaction completed 2026-09-28 under ASTRA_ONESHOT authorization; L-01 through L-19 moved with stable IDs and L-13 remains resolvable in the archive.
2. Resolved 2026-09-28: the recovery order in `L-17` now lives in `internal-docs/relay/VPS_RELAY_RUNBOOK.md`, section "Relay recovery (2026-09-28 outage)", together with a symptom-to-cause table. It remains derived from one observed incident, not a rehearsed procedure - treat it as the documented intent and re-verify after the next real recovery.
