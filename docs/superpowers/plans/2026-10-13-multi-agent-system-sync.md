# Multi-Agent Cross-Surface Parity & Verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish cross-surface parity for the 7-agent architecture across Antigravity (AGY), Claude Code, Codex, and the VPS Relay, enforced by automated synchronization and contract validation gates.

**Architecture:** 
- Maintain `.opencode/agent/*.md` as the canonical source of truth for agent personas.
- Mirror all subagents to `.agents/agents/*.md` for AGY.
- Create a dedicated `CLAUDE.md` root router for Claude Code pointing directly to `AGENTS.md`.
- Implement automated verification gates in Python (`scripts/verify_agent_sync.py` and `scripts/verify_handoff.py`) tested via pytest.
- Wire `verify_agent_sync.py` into `scripts/sync_all_repos.py --strict` so audits fail if surfaces drift.

**Tech Stack:** Python 3.10+, pytest, Markdown, JSONC.

**Spec:** [internal-docs/specs/2026-09-22-agent-subagent-architecture.md](file:///C:/personal/naquuuu/internal-docs/specs/2026-09-22-agent-subagent-architecture.md) & [ADR-011](file:///C:/personal/naquuuu/internal-docs/DECISION_LOG.md#L160) / [ADR-014](file:///C:/personal/naquuuu/internal-docs/DECISION_LOG.md#L220).

## Global Constraints
- **Strict Corporate Isolation**: Zero MAPCLUB or corporate data, credentials, or stakeholder names.
- **Cross-Platform**: UTF-8 clean, path-agnostic (`pathlib.Path`), compatible with Windows and Linux (VPS).
- **No Unsolicited Commits**: Run gates and verify, but leave commit/push to explicit user approval.
- **Diagram Width**: All Mermaid diagrams must be vertical and constrained to `< 80` columns.

---

### Task 1: Create `CLAUDE.md` Root Router for Claude Code

**Files:**
- Create: `CLAUDE.md`

**Interfaces:**
- Consumes: `AGENTS.md`, `internal-docs/AGENT_PLAYBOOK.md`
- Produces: `CLAUDE.md` router read by Claude Code CLI on startup.

- [ ] **Step 1: Write `CLAUDE.md`**
Define workspace role, routing to `AGENTS.md`, 7-agent roster, four-block handoff requirement, and pre-commit gates.

- [ ] **Step 2: Verify file existence and syntax**
Run: `python -c "import pathlib; assert pathlib.Path('CLAUDE.md').exists()"`

---

### Task 2: Mirror Hidden Subagents into Antigravity (`.agents/agents/`)

**Files:**
- Create: `.agents/agents/naquuuu-builder.md`
- Create: `.agents/agents/naquuuu-scribe.md`
- Create: `.agents/agents/naquuuu-librarian.md`
- Create: `.agents/agents/naquuuu-skeptic.md`
- Create: `.agents/agents/naquuuu-verifier.md`

**Interfaces:**
- Consumes: `.opencode/agent/*.md`
- Produces: Mirror agent personas for Antigravity with appropriate YAML frontmatter (`mode: subagent`).

- [ ] **Step 1: Write mirrored persona markdown files in `.agents/agents/`**
- [ ] **Step 2: Verify all 7 agents exist in `.agents/agents/`**
Run: `python -c "import pathlib; agents = [p.stem for p in pathlib.Path('.agents/agents').glob('*.md')]; assert len(agents) == 7, agents"`

---

### Task 3: Build Surface Parity Verification Gate (`scripts/verify_agent_sync.py`)

**Files:**
- Create: `tests/test_verify_agent_sync.py`
- Create: `scripts/verify_agent_sync.py`

**Interfaces:**
- Consumes: `.opencode/agent/*.md`, `.agents/agents/*.md`, `CLAUDE.md`, `opencode.jsonc`
- Produces: CLI script `scripts/verify_agent_sync.py` returning exit code 0 if all surfaces match, 1 on drift.

- [ ] **Step 1: Write failing test in `tests/test_verify_agent_sync.py`**
- [ ] **Step 2: Run pytest to verify it fails**
Run: `pytest tests/test_verify_agent_sync.py -v`
- [ ] **Step 3: Implement `scripts/verify_agent_sync.py`**
- [ ] **Step 4: Run pytest to verify it passes**
Run: `pytest tests/test_verify_agent_sync.py -v`

---

### Task 4: Build Four-Block Handoff Contract Linter (`scripts/verify_handoff.py`)

**Files:**
- Create: `tests/test_verify_handoff.py`
- Create: `scripts/verify_handoff.py`

**Interfaces:**
- Consumes: Text input (stdin, file, or string)
- Produces: CLI script `scripts/verify_handoff.py` validating `### Result`, `### Files Changed`, `### Evidence`, `### Blockers`.

- [ ] **Step 1: Write failing test in `tests/test_verify_handoff.py`**
- [ ] **Step 2: Run pytest to verify it fails**
Run: `pytest tests/test_verify_handoff.py -v`
- [ ] **Step 3: Implement `scripts/verify_handoff.py`**
- [ ] **Step 4: Run pytest to verify it passes**
Run: `pytest tests/test_verify_handoff.py -v`

---

### Task 5: Integrate `verify_agent_sync.py` into Strict Audit Gate

**Files:**
- Modify: `scripts/sync_all_repos.py:260-267`

**Interfaces:**
- Consumes: `scripts/verify_agent_sync.py`
- Produces: Updated `sync_all_repos.py` running surface parity check under `--strict`.

- [ ] **Step 1: Update `scripts/sync_all_repos.py` to invoke `verify_agent_sync.py`**
- [ ] **Step 2: Test `scripts/sync_all_repos.py --strict` invocation**

---

### Task 6: Final Verification & Gate Execution

- [ ] **Step 1: Run full pytest suite**
Run: `pytest tests/ -v`
- [ ] **Step 2: Run sanitization gate**
Run: `python scripts/verify_sanitization.py`
- [ ] **Step 3: Run model routing gate**
Run: `python scripts/verify_model_routing.py`
- [ ] **Step 4: Report Four-Block Handoff and prompt for OpenCode QA or commit review**
