# Architecture Decision Log (ADR)

This log records major technical and structural decisions made across personal projects in the `naquuuu` hub.

---

## ADR-001: Multi-Repo Hub Architecture with Single GCP Routing
- **Date**: 2026-09-15
- **Status**: Accepted
- **Context**: Need a personal engineering home for multiple independent GitHub repositories while sharing a single personal Google Cloud Project for Gemini AI assistance, OpenCode, and local tooling.
- **Decision**:
  - Establish `C:\personal\naquuuu` as an umbrella workspace.
  - Sub-projects live in `projects/<repo-name>` as standalone git repositories with independent remotes.
  - Hub root `.gitignore` ignores `projects/` to prevent nested git submodules.
  - Shared `.env` and `.vscode/settings.json` define the single personal GCP project and Gemini API key across all projects.
- **Consequences**:
  - Clean separation between corporate (MAPCLUB) and personal IP.
  - Child repositories push directly to GitHub without any hub coupling.
  - Centralized scripts (`sync_all_repos.py`, `verify_sanitization.py`) provide multi-repo visibility.

---

## ADR-002: Relocation of naquuuu.github.io & Cross-Workspace Junction
- **Date**: 2026-09-15
- **Status**: Accepted
- **Context**: The personal blog (`naquuuu.github.io`) was originally located inside `c:\work\mapclub-po-workspace\blog`.
- **Decision**:
  - Relocated repository to `C:\personal\naquuuu\blog` directly as a child repository of `naquuuu`.
  - Created an NTFS directory junction at `c:\work\mapclub-po-workspace\blog` pointing to `C:\personal\naquuuu\blog`.
- **Consequences**:
  - Blog repository is physically housed directly inside `naquuuu/blog/` with its own git origin (`naquuuu.github.io`).
  - MAPCLUB workspace can still source, draft, and run blog QA gates without breaking paths or relative imports.

---

## ADR-003: Hub Remote Establishment & Personal Non-Employed Declaration
- **Date**: 2026-09-16
- **Status**: Accepted
- **Context**: Need a remote home for the personal meta-hub while explicitly distinguishing personal work from corporate employment.
- **Decision**:
  - Created and linked remote `https://github.com/naquuuu/naquuuu-personal-works.git`.
  - Updated root README.md and AGENTS.md with explicit mission statement: personal, non-employed engineering workspace, research, and portfolio.
- **Consequences**:
  - Hub repo is public/tracked on GitHub as `naquuuu-personal-works`.
  - Strict corporate data isolation enforced via pre-commit gate `python scripts/verify_sanitization.py`.

---

## ADR-004: Repository Taxonomy, Sandbox vs Dedicated Projects, and AI Prompt Tags
- **Date**: 2026-09-16
- **Status**: Accepted
- **Context**: Need a clear criteria to distinguish fast prototypes from serious, long-term tools, and enable AI models to recognize intent deterministically.
- **Decision**:
  - Cloned `https://github.com/naquuuu/random-stuff` into `projects/random-stuff/` as a disposable playground.
  - Dedicated projects live in `projects/<slug>/` with full Definition of Done (own .venv, tests, modular code).
  - Adopted standard prompt prefixes: `[PROJECT: <slug>]`, `[SANDBOX]` / `[SPIKE]`, `[BLOG]`, `[HUB]`.
- **Consequences**:
  - AI agents immediately route tasks and enforce appropriate rigor without repetitive prompting.
  - Multi-repo auditor (`scripts/sync_all_repos.py`) automatically tracks all child repositories.

---

## ADR-005: Self-Reinforcing Memory & Preference Persistence Protocol
- **Date**: 2026-09-16
- **Status**: Accepted
- **Context**: Need a mechanism to ensure all major decisions and user preferences persist across sessions so AI pair-programmers learn continuously.
- **Decision**:
  - Decisions are systematically logged in `internal-docs/DECISION_LOG.md`.
  - User preference invariants are registered in `AGENTS.md` Section 6 (which is automatically injected into agent context at every session start).
  - Diagrams must default to Mermaid flowcharts instead of brittle ASCII art to avoid wrapping bugs.
- **Consequences**:
  - Zero context loss across AI conversation boundaries.
  - Consistent coding and architectural patterns enforced automatically.
