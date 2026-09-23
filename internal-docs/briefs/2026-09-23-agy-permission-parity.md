# Brief — AGY Permission Parity + Persona Mirror Sync

**Goal**: Bring the AGY surface to parity with the OpenCode posture — standard commands auto-run, commits and risky operations stay gated — and mirror the ADR-015 triage wording into `.agents/agents/naquuubot.md`.

**Context** (paths only, no pastes):
- Target: `.agents/agents/naquuubot.md`
- Review only: `.agents/agents/naquuu-curator.md`
- Source of truth for persona wording: `.opencode/agent/naquuubot.md`
- Reference, do not edit: `opencode.jsonc`, `internal-docs/DECISION_LOG.md` (ADR-014 mirroring, ADR-015 triage, ADR-016 autonomy posture, ADR-017 prompt-free surface)
- External docs: Antigravity "Custom Subagents" page (`commandExecutionPolicy` values) and "Permissions" page (presets, allow/deny/ask rules)

**Steps** (agent-executable):
1. Frontmatter: set `commandExecutionPolicy: auto` in `.agents/agents/naquuubot.md`. Leave every other frontmatter key unchanged.
2. Body: mirror the triage sentence and the delegation-economy sentence from `.opencode/agent/naquuubot.md`, adapting surface references only.
3. Two-IDE paragraph: replace the read-only execution restriction with — "On this surface, inspection and standard build/test/install commands run autonomously (`commandExecutionPolicy: auto`); risky operations, commits, and the full gate matrix stay with OpenCode (briefs in internal-docs/briefs/)." Keep the rest verbatim (one writer per tree, commit at every handoff, never invoke the `agy` CLI).
4. Query the Antigravity docs for the exact meaning of `commandExecutionPolicy: eager` and quote the definition in the report. Do not adopt it.
5. Review `.agents/agents/naquuu-curator.md` against `.opencode/agent/naquuu-curator.md`; edit only if persona drift exists beyond surface wording.

**Done when**:
1. `.agents/agents/naquuubot.md` frontmatter reads `commandExecutionPolicy: auto` and its body contains the triage line.
2. `git diff --stat` shows only `.agents/agents/*.md` paths touched.
3. The report quotes the docs definition of `eager` and names the Settings → Projects path for full autonomy as a human-only option.

**Constraints**:
- In scope: the two `.agents/agents/*.md` files.
- Out of scope: `opencode.jsonc`, `.opencode/**`, `AGENTS.md`, `internal-docs/DECISION_LOG.md` (OpenCode root logs the outcome after this brief closes), global `~/.gemini/**` settings, work-scoped MCP configs.
- Human-only steps (do not attempt): full no-prompt = Settings → Projects → this project → Terminal Command Auto Execution → Always Proceed. Do not change the global General preset — it is shared with work-scoped contexts.
- Windows caveat: sandbox modes are documented for macOS/Linux; verify before recommending any sandbox-based mode.
- If this surface cannot write files, return exact final file contents for the owner to apply.

**Return**: changed paths, one-line diff summary, the `eager` definition quote, curator drift verdict, blockers.

---

## Done
- 2026-09-23 — Executed by OpenCode (naquuubot).
  - `.agents/agents/naquuubot.md`: `commandExecutionPolicy: sandbox` -> `auto`; triage sentence mirrored; two-IDE execution paragraph replaced per step 3; delegation-economy sentence appended.
  - `eager`: no published definition found in the docs checked (Custom Subagents, Execution Modes, Permissions, CLI fine-grained permissions, SDK Subagents, SDK Policies); the enum is documented without per-value semantics. Not adopted.
  - Curator drift: none beyond surface wording (identical body; AGY adds `tools` list + `mainAgent`/`subagent` flags + mirror note).
  - Lock released on completion.
