# Lessons (curated)
<!-- verified-against: ADR-043 -->

Short, append-only. Agents read this first together with `STATUS.md` — it exists so we do not re-read everything. Route through `internal-docs/INDEX.md` first; this file is the hot slice, not the archive.

**IDs.** `L-nn`, permanent, assigned in order, never renumbered or reused. Cite a lesson as `L-nn`, never by ordinal. ADR-030 §Consequences cites "lesson 13" by ordinal; that entry is `L-13`, order unchanged.

**Compaction.** When this file exceeds ~5,000 chars, roll the oldest entries into `internal-docs/lessons/YYYY-MM.md` and keep the recent hot set here. The first compaction moved L-01 through L-19 to the September archive on 2026-09-28; L-20 and L-21 followed on 2026-09-30 to keep room for L-28.

Archived L-01 through L-21: [September archive](lessons/2026-09.md). IDs remain permanent.

L-22. Blog diagrams must follow "Architectural Blueprint on Warm Paper" (2026-09-29). Avoid dark terminal/SaaS whiteboard boxes (`#111110`) on blog essays. Use warm paper grounds (`var(--bg-surface)` / `#ece8dd`), subtle hairline borders, muted analog washes (terracotta, slate, sage), and strictly lowercase SVG labels per `STYLE_BIBLE.md`. Involve `naquuuu-curator` for aesthetic vetting on blog visual artifacts.

L-23. Bump the asset version on every css/js edit (2026-09-30). After `blog/assets/js/main.js` was fixed, the browser kept running the cached old file because the `?v=` asset version was not bumped, so a fixed autoplay bug looked unfixed during testing. Bump the version in every reference (and the gate constant, `STYLE_BIBLE.md` 5.3) in the same change, before testing.

L-24. Gate every audio auto-resume path on an explicit user click (2026-09-30). Handlers for `visibilitychange`, pause recovery and spotify resume must check a flag set only by the visitor clicking the sound pill; the hero song is off by default (ADR-038). An ungated resume handler is autoplay by another name.

L-25. The ctrl+k palette must switch lens before scrolling (2026-09-30). In-page anchors can live inside a hidden lens panel, so scrolling to them without first activating that lens lands on nothing. Any new jump target added to `blog/assets/js/palette.js` needs its owning lens resolved first.

L-26. Blank screenshots of scrolled regions in the browser pane are a tooling artifact, not a page bug (2026-09-30). Measure layout with javascript, or set a tall viewport (for example 390x2600) and screenshot at scroll 0.

L-27. Blog visual work runs curator-in-the-loop with strict roles (2026-09-30). Owner rule: every part involves `naquuuu-curator`, and each subagent stays in its role: curator reviews taste, builder edits, skeptic challenges, verifier gates, scribe documents. Owner taste rejections from this pass ("too gimmicky" proof strip, "too ai" glowing toggle, frosted pills) are canon in `STYLE_BIBLE.md` 2.9; flowchart shape and legend rules are in 2.8.

L-28. Every dedicated blog detail page carries a red ai note (2026-09-30). Owner rule: pages written by ai must say so where visitors notice it at once, so the `.ai-note` aside is crimson on purpose, overriding the earlier muted grey spec. Any new dedicated page (essay, note, experience or competition page) adds the aside as the last child of its header, keeps it red, and uses the wording "post" on essays and notes, "page" on experience and competition pages; copy in `STYLE_BIBLE.md` 4.7.

L-29. ADR-041 (2026-09-30): route routine implementation/checks to configured lower-cost specialists; keep architecture, privacy/security, review, and integration with the orchestrator, escalating for risk or uncertainty. Cost never relaxes the Tier 1/Hermes-state boundary; configuration is not latency evidence.

L-30. ADR-043 (proposed 2026-10-02) removes laptop relay/standby duties. `mipad-linux` becomes standby only after disabled-Hermes setup, verified session transfer, phone-to-VPS kill-switch checks, Linux readiness, and a two-way drill; this is not yet implemented.

L-31. The 2026-10-05 guard supports ordinary bounded requested text art and filters unaddressed group-idle events; `NO_REPLY` is for group idle/acks, never direct substantive questions. Tests and canaries passed; no real phone/group turn was verified (`2026-10-05-TEXT_ART_LOOP_FIX.md`).

## Open questions

1. Compaction completed 2026-09-28 under ASTRA_ONESHOT authorization; L-01 through L-19 moved with stable IDs and L-13 remains resolvable in the archive.
2. Resolved 2026-09-28: the recovery order in `L-17` now lives in `internal-docs/relay/VPS_RELAY_RUNBOOK.md`, section "Relay recovery (2026-09-28 outage)", together with a symptom-to-cause table. It remains derived from one observed incident, not a rehearsed procedure - treat it as the documented intent and re-verify after the next real recovery.
