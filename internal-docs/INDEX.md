# Internal Docs Index — Read Contract

Route every question to exactly one file through this index; do not wander the corpus.
Read in this order: **Tier 0** this index (always, cheap) → **Tier 1** the two bounded digests (current state, standing lessons) → **Tier 2** the single on-demand source Tier 1 points you to.

## Tier 0 — router
`internal-docs/INDEX.md`. Under 45 lines by contract; if it grows, the routing table is wrong, not the cap.

## Tier 1 — bounded digests
Read the hot slice only; never past it.
- `internal-docs/STATUS.md` — current workspace state, phase table, pending items, next steps.
- `internal-docs/LESSONS.md` — standing lessons keyed `L-nn`; append-only, compacted on a size threshold.

## Tier 2 — on demand, reached BY PATH from here
`DECISION_LOG.md` (grep `ADR-nnn`, never whole) · `HOSTS.md` · `relay/*.md` runbooks · `specs/` · `research/` · `briefs/` · `TASTE_PROFILE.md` · `TAILSCALE_ACL.md` · `AGENT_PLAYBOOK.md` · `ROADMAP.md` · `TECH_STACK.md` · `STYLE_BIBLE.md` · `PROJECT_PROMPT_GUIDE.md`

## Question class → file to open
| Question class | Open this |
| :--- | :--- |
| Current workspace state | `internal-docs/STATUS.md` |
| Why was something decided | `internal-docs/DECISION_LOG.md` (grep `ADR-nnn`) |
| Host topology, bootstrap, switch, failover | `internal-docs/HOSTS.md` |
| Relay / WhatsApp operations | `internal-docs/relay/VPS_RELAY_RUNBOOK.md` |
| Phone-side shell on the relay VPS (`naquuuu-term`) | `internal-docs/NQ_TERM_RUNBOOK.md` |
| Worker dispatch and durable queue | `internal-docs/relay/M2_DISPATCH_RUNBOOK.md` |
| Tailscale / network / remote access | `internal-docs/TAILSCALE_ACL.md` |
| Group policy — who may speak, who may act | `internal-docs/relay/README.md` |
| Aesthetic, persona, taste | `internal-docs/TASTE_PROFILE.md` |
| Agent roster, prompt formula, handoff contract | `internal-docs/AGENT_PLAYBOOK.md` |
| Research notes (DO Managed Agents, Phase 4) | `internal-docs/research/` |
| A decision not yet made | `internal-docs/ROADMAP.md` |

## Rules
- Grep `DECISION_LOG.md` by `ADR-nnn`; never read it whole (~64 KB, growing ~2.6 ADRs/day).
- Cite standing lessons as `L-nn`, never by ordinal.
- `research/` and `specs/` are read only when this index says they are relevant.
- Do not introduce a vector database or embedding index. Rationale (owner, 2026-09-28): ripgrep over this corpus is sub-millisecond; a retrieval service would add latency and a staleness surface.

## Freshness
- Each digest (`STATUS.md`, `LESSONS.md`) carries one HTML comment line immediately under its H1: `<!-- verified-against: ADR-nnn -->`.
- The checker in `scripts/sync_all_repos.py` reads the max `ADR-nnn` present in `DECISION_LOG.md` and compares. A digest stamped behind the log is STALE: non-strict mode warns, `--strict` fails.
- Bump the stamp in the same commit that adds the ADR it reflects. A stale digest is a defect, not a warning to ignore.
- This file carries no stamp and is excluded from the check; it is a router, not a digest.
