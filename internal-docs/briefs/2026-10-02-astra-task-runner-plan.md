# Brief — Astra (Codex): Execution Plan for ADR-044 M0/M1, Review-Only

**Goal**: Produce one final feedback-and-plan document that Opus 5.5 or Fable reviews before anything is executed. You challenge the Opus review, then turn the agreed parts into an exact, executable plan for M0 (ADR-029 repair) and M1 (multi-CLI handoff pilot).

## Mode: PLAN ONLY — read this first

- **The `internal-docs/ASTRA_ONESHOT.md` autonomy grant does NOT apply to this brief.** Ignore its commit, push, install, service-restart and host-command permissions.
- No code edits, script runs against hosts, SSH, service changes, installs, commits, or pushes.
- No `dispatch_job.sh`, `drain_queue.sh`, `worker_exec.sh`, `authorize_worker.sh`, or `node_autosync.sh` execution, including `--dry-run` against a real host.
- Allowed: reading repository files, `git log`/`git diff`/`git status`, and reading official docs online.
- Do not read the hub `.env`, Hermes state (`%LOCALAPPDATA%\hermes`, `~/.hermes`), CLI auth files, or `~/.ssh`.
- The one file you may create: `internal-docs/briefs/2026-10-02-astra-task-runner-plan.OUTPUT.md`.

## Context (paths only)

Read in this order:
1. `internal-docs/briefs/2026-10-02-sol-task-runner-adr.OUTPUT.md` — Sol's proposed ADR-044
2. `internal-docs/briefs/2026-10-02-opus-task-runner-review.OUTPUT.md` — Opus review (failure modes F1–F5, M0/M1 sequence, state diagram, bundle return)
3. Code: `scripts/dispatch_job.sh`, `scripts/drain_queue.sh`, `scripts/worker_exec.sh`, `scripts/job_status.sh`, `scripts/node_autosync.sh`, `scripts/test_dispatch_queue.sh`, `scripts/verify_sanitization.py`
4. Decisions: `internal-docs/DECISION_LOG.md` ADR-012, 016, 025, 029, 041, 043; `internal-docs/STATUS.md`; `internal-docs/relay/M2_DISPATCH_RUNBOOK.md`; `internal-docs/briefs/README.md`
5. Rules: `AGENTS.md` Sections 3, 5, 6C

## Steps

1. **Challenge the Opus review.** For each of F1–F5 and verdicts 1–9, say confirm or dispute, with file:line evidence. Specifically test:
   - the 8-run worst case;
   - whether the remote `opencode` really survives a relay-side `timeout`;
   - whether worktrees outside the synced checkout fully remove the auto-sync collision;
   - whether `.task` records are truly invisible to the current drain, prune and `job_status.sh` paths.
2. **M0 plan (ADR-029 repair).** For each change, give:
   - file and function;
   - before/after behaviour;
   - the exact new receipt and directory layout (`claimed/`, `uncertain/`, receipts);
   - exit-code handling (0, 124, 255, other);
   - the worker-side timeout value relative to the relay's;
   - the attach-server health probe;
   - per-attempt output retention.
   Keep it bash, matching the existing style. No new dependencies.
3. **M0 tests.** Write fixture test cases to extend `scripts/test_dispatch_queue.sh`, with no live SSH (stub `ssh`/`opencode` on `PATH`). At minimum, cover:
   - rc 255 before acceptance → requeued once;
   - rc 255 after acceptance → `uncertain/`, zero further runs;
   - rc 124 → `uncertain/`;
   - legacy `*.job` still drains;
   - `*.task` is ignored by the old code;
   - the synced checkout stays clean during a job.
   List each case as name → setup → expected state.
4. **M1 plan.** Cover:
   - the v2 `.task` field list;
   - a thin adapter interface (`--backend codex|claude|opencode`), with the exact headless invocation for each CLI, quoted from its official docs with the link;
   - the bundle/manifest/result package layout;
   - the sanitization scan point;
   - the brief-lock admission check;
   - an assertion that no adapter invokes or proxies `agy` (ADR-012).
   Mark every CLI flag as verified (link) or unverified.
5. **Migration and rollback runbook.** Write it as numbered owner-run steps for the relay host, including how to stop the timer, back up, deploy, verify and roll back. Commands are written, not run.
6. **Execution split.** Assign each step to a role: `naquuuu-builder` authors, `naquuuu-verifier` runs gates, the owner runs host steps. Use the cost routing in ADR-041. Mark what can run in parallel (no overlapping files).

## Done when

1. `internal-docs/briefs/2026-10-02-astra-task-runner-plan.OUTPUT.md` exists, and `git status` shows no other new or modified file caused by this run.
2. Every F1–F5 finding and verdict 1–9 has a confirm or dispute line with file:line evidence.
3. The document ends with a **"Decisions for the final reviewer"** section: at most 5 numbered yes/no or A/B questions for Opus 5.5 or Fable. Answering them must be enough to green-light execution.

## Constraints

- In scope: one output document.
- Out of scope: any edit to scripts, `DECISION_LOG.md`, `STATUS.md`, `AGENTS.md`, configs, child repos, or hosts. ADR-044 stays unaccepted.
- Include the four owner blockers from the Opus review (host, pilot timing, terms, scope cuts) unchanged, unless you have evidence that changes them.
- No invented metrics. Any count must be derived from code paths and say so.
- Tier 2 content only. No credentials, phone numbers, IDs, or hostnames beyond those already in `HOSTS.md`.
- If you cannot write files, return the full document in chat.

## Return (four-block handoff)

```
### Result
### Files Changed
### Evidence
### Blockers
```

Evidence must include the F1–F5 / verdict confirm-dispute table and the CLI-flag verification list.
