# NAQUUUU Workspace — Claude Code Operating Guide

This workspace is the central engineering operating hub for personal projects, creative explorations, and portfolio applications. It operates under a **Single GCP Project, Multi-Repo Architecture**.

Authoritative master instructions: `AGENTS.md`.

---

## Critical Invariants (Always Active)

1. **Strict Corporate Isolation**: Zero MAPCLUB or corporate data, credentials, stakeholder names, or architectures allowed in this workspace. All personal code must remain strictly separated.
2. **Pre-Commit Sanitization**: Run `python scripts/verify_sanitization.py` before committing or pushing to any public repository.
3. **Never Commit Without Approval**: Never run `git commit` or `git push` without explicit confirmation from the owner.
4. **Clean Git Working Trees**: Maintain clean working trees across hub and child repositories under `projects/`.

---

## 7-Agent Architecture & Handoff Contract

This workspace uses a 7-agent role separation pattern:
- **`naquuuubot`** (Entry Point): Chief of Staff & Engineering Orchestrator. Plans, delegates, serializes writes, verifies gates, and reports.
- **`naquuuu-curator`** (Entry Point): Aesthetic, Taste & Persona Muse (ID/EN). Reads `internal-docs/TASTE_PROFILE.md`.
- **`naquuuu-builder`** (Subagent): Software Builder for `projects/`, `blog/`, and scripts.
- **`naquuuu-scribe`** (Subagent): Documentation Scribe for `internal-docs/`, ADRs, and blog copy.
- **`naquuuu-librarian`** (Subagent): Knowledge Librarian. Read-only retrieval with `file:line` citations.
- **`naquuuu-skeptic`** (Subagent): Adversarial Reviewer. Hunts for hallucinations, scope creep, and ungrounded claims.
- **`naquuuu-verifier`** (Subagent): Quality Gatekeeper. Runs verification scripts and returns raw output.

### The Four-Block Handoff Contract
All delegated tasks must conclude with:
```markdown
### Result
### Files Changed
### Evidence
### Blockers
```

---

## Common Verification Gates

Always run gates from the workspace root (`%NAQUUUU_WORKSPACE%` or `$NAQUUUU_WORKSPACE`):

```bash
# 1. Sanitization & leak audit (mandatory before commit)
python scripts/verify_sanitization.py

# 2. Multi-repo status and freshness audit
python scripts/sync_all_repos.py --strict

# 3. Cross-surface agent parity check
python scripts/verify_agent_sync.py

# 4. Model routing check
python scripts/verify_model_routing.py
```
