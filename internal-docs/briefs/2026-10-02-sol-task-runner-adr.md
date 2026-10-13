# Brief — Revise the Multi-CLI Task Runner Plan into Proposed ADR-044

**Goal**: Turn Sol's multi-CLI task runner proposal (Hermes gateway + `naquuuubot` orchestrator + shared runner over Codex, Claude Code, OpenCode, and human-operated AGY) into a Proposed ADR-044 that builds on existing decisions instead of duplicating them.

**Context** (paths only, no pastes):
- Your original proposal: the five-stage plan you produced in the previous session (launcher/profiles, portable task records, controlled execution, Hermes connection, dashboard). Restate it from memory; it is not stored in the repo.
- Operating rules: `AGENTS.md` (Sections 3, 4, 5, 7)
- Decisions to build on (read before writing): `internal-docs/DECISION_LOG.md` — ADR-012 (AGY human-operated, brief-and-notify, no agent invokes `agy`), ADR-016 (autonomous posture; Tier 1 rules are policy, not mechanism), ADR-029 (M2 dispatch + durable queue), ADR-040 (tailnet-only Hermes dashboard), ADR-041 (cost-aware model routing), ADR-043 (laptop enters employer device management 2026-10-08; open question on where the hub lives)
- Existing job system: `internal-docs/relay/M2_DISPATCH_RUNBOOK.md`, `scripts/dispatch_job.sh`, `scripts/drain_queue.sh`, `scripts/job_status.sh`, `scripts/worker_exec.sh`
- Existing handoff format: `internal-docs/briefs/README.md` and this folder's briefs
- Current blockers: `internal-docs/STATUS.md` (M2 worker SSH trust), `internal-docs/relay/BOT_IMPROVEMENT_BACKLOG.md` (row on uncertain-start duplicate execution)

**Review findings to resolve** (each must be addressed in the ADR):
1. **No parallel job system.** ADR-029 already has a durable `pending/done/failed` queue, timeouts, retry caps, archive, and status. Either extend the ADR-029 job format (task ID, goal, repo, allowed files, success criteria, four-block result) plus `internal-docs/briefs/`, or explicitly supersede ADR-029 with a migration path. Do not introduce a second state store silently. State which option and why.
2. **Stage 0: host placement.** Decide (or present as an owner decision with a recommendation) where the runner and CLI account profiles live, given ADR-043. Personal CLI credentials on the employer-managed laptop conflict with Strict Corporate Isolation and Tier 1 handling. `mipad-linux` is the likely candidate; check `internal-docs/HOSTS.md`.
3. **Stage 4 prerequisites.** Remote execution depends on M2 activation. List worker SSH trust and the relay-skill switch as blocking prerequisites, not new work.
4. **Enforcement realism.** The runner cannot claim to enforce the Model-Input Boundary under ADR-016. Add a sanitization scan on task-record writes (reuse `scripts/verify_sanitization.py` logic where possible), and a synthetic-secret canary run against the record store itself. Treat attachments as a leak vector.
5. **AGY boundary.** The runner may only write a brief for the owner to paste; AGY results return via the owner's commit. Keep ADR-012's negative test (no process invokes or proxies `agy`) in the definition of done.
6. **Smaller items:**
   - Stage 1 inventory includes a terms-of-service check for each CLI's programmatic interface and for profile switching. Tool switching on limits is fine; rotating multiple accounts of one provider to evade limits is out.
   - Stage 5 extends the ADR-040 dashboard rather than building a new one.
   - State where the runner code lives: a dedicated `projects/<slug>` (own `.venv`, tests) vs `scripts/`. Recommend one.
   - Verify every external doc link you cite (Codex app-server, Claude headless, OpenCode server, Hermes docs). Drop or mark any link you cannot confirm.
   - No invented metrics (AGENTS.md Section 5, Zero Synthetic Claims).

**Steps**:
1. Read the Context files above. Do not read the hub `.env` or any Hermes state (`%LOCALAPPDATA%\hermes`, `~/.hermes`).
2. Draft ADR-044 in the existing DECISION_LOG format (Date, Status: Proposed, Context, Decision, Consequences, Open). Include one compact Mermaid flowchart (no ASCII art) showing the revised architecture with the ADR-029 queue as the job store.
3. Restructure the stages as: Stage 0 (host) → 1 (launcher/profiles + ToS inventory) → 2 (extend ADR-029 job record + brief handoff) → 3 (controlled execution, worktrees, no duplicate execution after uncertain start) → 4 (Hermes, gated on M2) → 5 (ADR-040 dashboard + measured routing). Each stage gets a "Done when" line.
4. Define the first milestone: on the chosen host, one ADR-029 job record authored by Codex is picked up and completed by Claude Code or OpenCode, with a four-block result archived.

**Done when**:
1. The ADR text exists at `internal-docs/briefs/2026-10-02-sol-task-runner-adr.OUTPUT.md` and addresses all six findings above by number.
2. No file other than that output file is created or modified (`git status` shows only it as new).
3. The report lists every external link with a verified/unverified mark.

**Constraints**:
- In scope: writing the one output file.
- Out of scope: editing `internal-docs/DECISION_LOG.md`, `AGENTS.md`, `STATUS.md`, scripts, configs, or any child repo. `naquuuubot` owns DECISION_LOG and will merge the ADR after owner review.
- Tier 2 content only. No credentials, phone numbers, IDs, hostnames beyond those already in `HOSTS.md`.
- If you cannot write files, return the full ADR text in chat.

**Return** (four-block handoff):
```
### Result
### Files Changed
### Evidence
### Blockers
```
Include in Evidence: the finding-number → ADR-section mapping and the link verification list. Include in Blockers: any owner decisions required (host placement, hub location).
