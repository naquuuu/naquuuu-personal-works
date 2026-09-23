# NAQUUUU Personal Engineering Workspace — Operating Guide & Definition of Done

This workspace is the central engineering operating hub for personal projects, creative explorations, portfolio applications, and the personal blog (`naquuuu.github.io`). It is designed around a **Single GCP Project, Multi-Repo Architecture**.

---

## CRITICAL RULES (Always Active)

1. **Clean git before starting**: Each child repo in `projects/` and the root hub must maintain clean working trees (`git status` clean).
2. **Strict Corporate Isolation**: Zero MAPCLUB or corporate data, stakeholder names, or credentials allowed in this workspace. All personal code must remain strictly separated.
3. **Single GCP Project Economy (amended by ADR-019)**: Personal model access and Tier 1 credentials route through the single personal Google Cloud Project (`.env` / `.vscode/settings.json`). DigitalOcean Managed Agents is an approved compute/execution host and MCP tool layer for Tier 2/3 work; its API token is Tier 1 and lives only in the hub `.env`. Tier 1 material never runs on DO sessions.
4. **Pre-Commit Sanitization**: Run `python scripts/verify_sanitization.py` before committing or pushing to any public GitHub repository.
5. **Independent Sub-Repos**: Subprojects live in `projects/<repo-slug>`. Never commit child git repositories into the root hub.

---

## 1. Pre-Commit Gates

Before committing in any project, run the relevant gate from the hub root:

| Gate | Command | When |
| :--- | :--- | :--- |
| **Sanitization & Leak Prevention** | `python scripts/verify_sanitization.py` | Before committing to any public repository |
| **Multi-Repo Audit** | `python scripts/sync_all_repos.py --strict` | Before ending a work session or pushing |
| **Blog Reliability QA** | `python scripts/verify_blog_qa.py` (inside blog repo) | Any blog or portfolio HTML/CSS/JS edits |
| **Host Readiness** | `python scripts/host_check.py` | Before starting dev on a standby host (Phase 4) |
| **New Project Scaffolding** | `python scripts/scaffold_personal_project.py --name <slug>` | Starting a new repository |

Git hooks (`.githooks/pre-commit`, `.githooks/pre-push`) enforce sanitization and block force-push automatically when `core.hooksPath` is set (Phase 4).

---

## 2. Multi-Repo Architecture Protocol

### Directory Structure
```
C:\personal\naquuuu\
├── .env                              # Global personal GCP / Gemini credentials (git-ignored)
├── .vscode/settings.json             # Antigravity IDE personal GCP project context
├── AGENTS.md                         # This operating manual
├── README.md                         # Hub directory & active project index
├── blog/                             # Personal blog & portfolio (git-ignored by hub, remote: naquuuu.github.io)
├── internal-docs/                    # Private ADRs, roadmap, notes (git-tracked in hub)
├── projects/                         # Additional independent repos live here (git-ignored by hub)
└── scripts/                          # Workspace automation & QA gates
```

### Protocol Rules
- **Adding a Project**: Clone or scaffold into `projects/<repo-name>` or directly at root for major repositories (like `blog/`).
- **Git Independence**: Run `git` commands inside each child repository (`blog/` or `projects/<name>`). The hub `.gitignore` explicitly ignores child repositories to prevent submodule entanglement.
- **Environment Inheritance**: Child projects read credentials from the hub's root `.env` or global user environment variables (`GEMINI_API_KEY`, `GOOGLE_CLOUD_PROJECT`).

### Project Routing Taxonomy & Prompt Prefixes
To ensure all AI agents route tasks to the correct repository and enforce appropriate rigor, use these prompt prefixes:

| Prompt Tag | Target Directory | Git Remote | Rigor & Definition of Done |
| :--- | :--- | :--- | :--- |
| **`[PROJECT: <slug>]`** | `projects/<slug>/` | Standalone GitHub repo | **Dedicated Project**: Scaffold via `python scripts/scaffold_personal_project.py --name <slug>`. Dedicated `.venv`, independent `.git`, modular architecture, tests, and documentation. Never place inside `random-stuff/`. |
| **`[SANDBOX]`** or **`[SPIKE]`** | `projects/random-stuff/<topic>/` | `naquuuu/random-stuff` | **Playground**: Fast prototyping, exploratory spikes, disposable scripts. Low ceremony, rapid iteration. |
| **`[BLOG]`** | `blog/` | `naquuuu/naquuuu.github.io` | **Publication**: Articles, interactive portfolio showcase. Strict blog QA, no inline widths, responsive column. |
| **`[HUB]`** | `.` | `naquuuu/naquuuu-personal-works` | **Meta-Hub**: Automation scripts, sanitization gates, ADRs, global personal environment setup. |

---

## 3. Model Routing & Data Classification

| Tier | Data | Allowed Models |
| :--- | :--- | :--- |
| **TIER 1 Private Personal** | Personal API keys, private passwords, unreleased private source code | Gemini (paid no-train) / Vertex AI |
| **TIER 2 Internal Workspace** | Workspace scripts, notes, roadmaps, technical ADRs | Any model (free-tier OK) |
| **TIER 3 Public Open-Source** | Published blog posts, public portfolio UI, open-source repositories | Any model |

**Forbidden**: Storing corporate business data, enterprise credentials, or internal company architectures in this workspace.

### Model-Input Boundary
The sanitization gate audits git-tracked content; it is **not** a model-input firewall. Rules for what may enter any agent or model context:
1. Tier 1 material (keys, passwords, session tokens, phone numbers, credential files) never enters model context — not via files, terminal output, tool errors, attachments, or chat.
2. Hub `.env` and Hermes state (`%LOCALAPPDATA%\hermes`, `~/.hermes`) are out of bounds for agent reads.
3. Briefs and relay payloads carry Tier 2 content only; strip sender identifiers and metadata where possible.
4. Changes to relay or model-input paths require a synthetic-secret canary check before rollout.

---

## 4. Agent Orchestration (Root First)

This workspace uses a 7-agent architecture with strict role separation, structured handoffs, and deterministic gates. Agent personas live in `.opencode/agent/*.md`; permissions and registry in `opencode.jsonc`. The two entry-point personas are also mirrored as Antigravity custom agents in `.agents/agents/*.md` (ADR-014).

### Entry Points
The user speaks only to **two** agents directly:
- **`naquuubot`** — Chief of Staff / Engineering Orchestrator. Sole entry point for engineering tasks.
- **`naquuu-curator`** — Aesthetic, Taste & Persona Muse. Direct access for creative, style, and taste conversations.

All other agents are hidden subagents that never communicate with the user.

### Subagent Roster

| Agent | Role | Writes | Permissions |
| :--- | :--- | :--- | :--- |
| `naquuubot` | Orchestrator (primary) | AGENTS.md, internal-docs/DECISION_LOG.md | edit, bash (auto-approve; commit/push ask; destructive deny), delegate naquuu-* |
| `naquuu-curator` | Aesthetic Muse (primary) | — | read-only, no bash, no delegation |
| `naquuu-builder` | Software Builder (subagent) | projects/, scripts/, blog/ | edit, bash |
| `naquuu-scribe` | Documentation Scribe (subagent) | internal-docs/, blog/ | edit only |
| `naquuu-librarian` | Knowledge Librarian (subagent) | — | read-only |
| `naquuu-skeptic` | Adversarial Reviewer (subagent) | — | read-only |
| `naquuu-verifier` | Quality Gatekeeper (subagent) | — | bash only (runs gate scripts) |

### Shared Contracts

**Four-Block Handoff**: Every subagent returns exactly:
```
### Result
### Files Changed
### Evidence
### Blockers
```

**Universal Prompt Formula**: Root delegates using:
```
Goal:        <one sentence outcome>
Context:     <file paths or line ranges, no pastes>
Done when:   <2-3 verifiable criteria>
Constraints: <In-scope / out-of-scope>
Evidence:    Four-block handoff
```

**Persona Precedence**: Each agent's `.opencode/agent/<name>.md` is the single source of truth for voice, emoji usage, and communication style; its AGY mirror in `.agents/agents/<name>.md` must match it (ADR-014; manual review until a sync check lands). `internal-docs/TASTE_PROFILE.md` is the ground truth for aesthetic preferences.

### Orchestration Rules
- **Subagent depth**: 1. Subagents never delegate further.
- **Concurrency**: Read-only subagents may parallelize; writers serialize per file path.
- **Memory authority**: Only `naquuubot` edits `AGENTS.md`, `internal-docs/DECISION_LOG.md`, and core workspace docs.
- **Workflow diagrams**: When a task runs through subagents, root presents a compact Mermaid diagram first (never ASCII box art — Section 7.4).
- **Author + Reviewer Pairing**: `naquuu-builder` and `naquuu-scribe` author; `naquuu-skeptic` challenges qualitatively and `naquuu-verifier` runs deterministic gates; root synthesizes and reports. Max 2 review cycles before human escalation.

---

## 5. Behavioral Guidelines

### Think Before Coding
State assumptions. If uncertain, verify. Keep designs straightforward.

### Simplicity First
Minimum code that solves the problem. No unnecessary dependencies or premature abstraction. If 200 lines could be 50, rewrite.

### Surgical Changes
Touch only what is requested. Don't add unsolicited refactors to adjacent code. Match existing repository conventions.

### Goal-Driven Execution
Every task gets clear success criteria: `1. [Step] → verify: [check]`. Loop until verified with working code.

### Concise Output
Lead with action. Number steps. Cap lists at 5 items. No unnecessary conversational filler.

### Reality Grounding & Anti-Slop Standards
- **Zero Synthetic Claims**: Never invent metrics or unverifiable performance statements (e.g. avoid claims like "60fps", "sub-millisecond latency", or "zero memory leaks" without empirical instrumentation).
- **Accessible & Responsive Baseline**: Every web UI must enforce responsive layouts, mobile viewport tags, descriptive `alt` text on images, and zero inline width hacks.

---

## 6. Subsystem Definitions of Done

### A. Web Apps & Portfolios
1. **Responsive First**: Fluid layout down to 320px viewport without horizontal overflow (`overflow-x: clip`).
2. **Modern CSS & Tokens**: Vanilla CSS or curated design system using CSS variables, modern semantic typography, and accessible contrast ratios.
3. **SEO & Accessibility**: Semantic HTML5, unique element IDs for testability, and standard meta tags.

### B. Personal Blog (`naquuuu.github.io`)
1. **Zero Inline Width Attributes**: No inline `style=".*width"` elements.
2. **Subpage Anchor Integrity**: All in-page anchors must resolve to valid DOM IDs.
3. **Audio / Media Resilience**: Any audio features must use valid user gestures (`click`, `pointerdown`) and deterministic loop handling.
4. **Reading Column**: Constrained to `max-width: 72ch; margin: 0 auto; min-width: 0;`.

### C. CLI & Tooling Scripts
1. **Cross-Platform**: Compatible with Windows PowerShell and Unix bash environments.
2. **UTF-8 Safe**: Windows console stdout safely handles UTF-8 characters without encoding crashes.
3. **Idempotent**: Scripts can be run repeatedly without duplicating state or corrupting data.

---

## 7. Self-Reinforcing Memory & Invariant Preferences

To ensure continuous learning across prompts and sessions, all AI agents must observe these established user preferences:

1. **Continuous ADR Logging**: Whenever a major technical decision, workflow change, or architectural pattern is agreed upon, log it immediately in `internal-docs/DECISION_LOG.md`.
2. **Active Multi-Repo Registry**:
   - `.` → `naquuuu-personal-works` (Meta-hub, orchestration, pre-commit QA gates, `.env`)
   - `projects/random-stuff/` → `naquuuu/random-stuff` (Playground, rapid spikes, disposable scripts)
   - `projects/<slug>/` → Independent GitHub repo (Dedicated production-ready apps & tools, own `.venv`, own tests)
   - `blog/` → `naquuuu/naquuuu.github.io` (Public blog, portfolio, published findings)
3. **Deterministic Prompt Routing**:
   - `[PROJECT: <slug>]`: Enforce dedicated project scaffolding via `python scripts/scaffold_personal_project.py --name <slug>`.
   - `[SANDBOX]` or `[SPIKE]`: Direct to `projects/random-stuff/<folder>`.
   - `[BLOG]`: Direct to `blog/`.
   - `[HUB]`: Direct to root hub.
4. **Diagram Standard**: Always use standard Mermaid flowcharts (` ```mermaid `) instead of fragile ASCII box art to avoid line-wrapping breakage on different viewport sizes.
5. **Data & Scraper Guidelines**:
   - Python 3.10+ with type hints.
   - Polite crawling: randomized User-Agents, exponential backoff, rate limiting.
   - Tabular data exported to Parquet and/or SQLite.
   - Mocked test fixtures (`pytest`) to avoid hitting live servers during testing.
6. **Dual-Format Deliverables (Lesson Learned, 2026-09-17)**: Every study-pack export is written as BOTH `.md` and `.txt` in the same run (`exports/notebook/` for `.md`, `exports/notebook_txt/` for `.txt` upload copies) — never update one without the other. Tooling defaults must produce both (e.g. `bi-scraper export-notebook`; `--no-txt` is the explicit opt-out). A format pair with mismatched timestamps or content is treated as stale and re-exported.
7. **Workspace Root Env Var**: All scripts, agent personas, and relay skills resolve workspace root from `$NAQUUUU_WORKSPACE` (Linux) or `%NAQUUUU_WORKSPACE%` (Windows) instead of hardcoding `C:\personal\naquuuu`. Set in `.env` and host bootstrap.
8. **Agent Architecture (ADR-011, 2026-09-22)**: 7-agent roster with two entry points (`naquuubot`, `naquuu-curator`), hidden subagents (`builder`, `scribe`, `librarian`, `skeptic`, `verifier`), four-block handoff contract, author+reviewer pairing. Personas in `.opencode/agent/*.md` (source of truth) with AGY mirrors in `.agents/agents/*.md` (ADR-014), registry in `opencode.jsonc`. See `internal-docs/AGENT_PLAYBOOK.md` for character sheets and `internal-docs/HOSTS.md` for multi-host topology (Phase 4).

