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
  - User preference invariants are registered in `AGENTS.md` Section 7 (which is automatically injected into agent context at every session start).
  - Diagrams must default to Mermaid flowcharts instead of brittle ASCII art to avoid wrapping bugs.
- **Consequences**:
  - Zero context loss across AI conversation boundaries.
  - Consistent coding and architectural patterns enforced automatically.

---

## ADR-006: bi-scraper Dedicated Project with Public-Source-Only Policy
- **Date**: 2026-09-17
- **Status**: Accepted
- **Context**: Need a reproducible personal study corpus builder for the eight PCPM/TPD chapters without touching corporate workspaces or gated course platforms.
- **Decision**:
  - Scaffolded `projects/bi-scraper/` as an independent repo (own `.venv`, tests, remote `naquuuu/bi-scraper`).
  - Public `bi.go.id` sources only (host allowlist at the HTTP layer); `pejuang.berkarirbi.id` and BIReady Masternotes remain read-in-browser only and are never fetched, and no login/paywall/DRM/PDF-secure protection is ever bypassed.
  - Binding freshness rule: incremental fetch by default (end date = today), 60-day coverage FAIL except report-only chapter 7, `[NEWER-THAN-SYLLABUS]` flags against pinned syllabus versions.
  - Config by reference only: `os.getenv` plus optional hub `.env` load; secret values are never copied into child repos.
  - Exports: NotebookLM study packs (metadata + dated links + my notes) and portfolio packs (public-data-only charts + my analysis; zero course-verbatim, zero third-party PDFs).
  - pytest suite runs fully mocked via `httpx.MockTransport` (zero live network hits).
- **Consequences**:
  - Honest corpus coverage reporting (chapter 7 is explicitly thin) instead of padded/invented content.
  - Polite scraping policy (2s + jitter, UA rotation, 3s timeout, 2 retries, robots.txt respected) keeps usage within public-source ToS.

---

## ADR-007: Obys-Style Editorial Redesign of the Blog (Dual-Mode Preserved)
- **Date**: 2026-09-17
- **Status**: Accepted
- **Context**: User wants naquuuu.github.io to feel design-driven like obys.agency while keeping the soul that beat the discontinued _revamp attempt (production won on soul; subtract-only process killed that revamp).
- **Decision**:
  - Public brand is 'naquuuu.build' (stage name spanning professional + creative contexts); real name 'krishna, alias naquuuu' demoted to the hero kicker. Footer wordmark = naquuuu.
  - Copy canon: Murphy's Law is the intro spine; thesis 'systems that anticipate failure. taste that anticipates feeling.' + sub-thesis 'mapping every possibility, from code to culture.'; two-lens framing justifies the dual-mode theme switcher.
  - No em-dashes, ever, in any user-facing copy; enforced by grep gate going forward.
  - Design tokens (additive only): Space Grotesk display + JetBrains Mono labels/code on Open Sans body; culture-mode --text-muted: #B58287 (measured 5.0:1 to 6.1:1); --ease-editorial, reveal, marquee, media-hover tokens.
  - Layout language: ghost-numeral editorial rows (dossiers, loop hairline grid), pure-CSS marquee strips (aria-hidden), scroll-reveal via IntersectionObserver with .js no-JS guard, dual-panel-safe, prefers-reduced-motion off-switch; footer ghost wordmark.
  - Audio: legacy once-gesture autoplay trigger deleted; playback strictly button-driven (ended-loop + metadata preload kept).
  - Perf: krishna-artwork served as 720px WebP (102 KB) + JPEG fallback (121 KB) via picture element (was 303 KB 1280px JPEG, 3x oversized for its column). Heavy gallery JPEGs turned out to be ~3.3 MB of UNREFERENCED repo ballast (the lessons-learned 8 MB page payload figure was stale); deletion/move deferred to user decision.
- **Consequences**:
  - Home page identity shifts to brand-first (naquuuu.build) while keeping professional anchor (kicker), all warmth (twin, kafin lyric, stories) intact.
  - verify_blog_qa.py referenced by AGENTS.md and CI does not exist on disk; manual gate equivalents ran (inline-width grep 0, anchor audit, sanitization PASS, node syntax check). Building the missing gate script is a flagged follow-up.
  - WP5 (subpage port) pending; live site not pushed until user approves.

---

## ADR-008: Copy Canon, Model Routing, and Mobile Control Contract for the Blog
- **Date**: 2026-09-17
- **Status**: Accepted
- **Context**: Following ADR-007, the owner wanted deeper copy transformation and per-breakpoint switcher coverage; Gemini 3.1 Pro served as read-only QA auditor and returned FINAL GO.
- **Decision**:
  - Copy canon (Muse Spark 1.3 Contributor drafted, owner-curated): kickers 'shipped systems', 'culture as fuel', 'hands, ears, closet', 'notes: software and systems', 'notes: music, clothes'; loop cards 'plan for bad days' / 'map the edge cases early' / 'keep a little slack' / 'help people recover fast' (systems) and 'paint without undo' / 'cut cloth like a plan' / 'music that steadies me' / 'taste keeps work fresh' (culture); CTA prose ends 'my inbox is open.'; headline 'let's build something thoughtful together.' is LOCKED.
  - Owner-approved exception: leaner specifics in the buffers card and doc 03 built line (no parametric/equipment-lead-times/flight-API-thermal-storage restoration);  and all other locked facts remain mandatory.
  - Titles are LOCKED: all 5 dossier titles and all essay card titles (they anchor case-study pages and recruiter scanning).
  - Per-breakpoint control contract: desktop (>=769px) uses the header lens switcher pill; mobile (<=768px) uses the first-screen hero switcher plus a scroll-driven floating switcher (visible at scrollY > 180). One control per breakpoint; the floating switcher CSS is scoped entirely inside the <=768px media block.
  - Spotify carousel contract: mobile wraps tabs into a 2x2 chip grid with a separate index/arrow row (no horizontal scroll possible); desktop keeps the single-row strip with a JS-toggled .is-scrollable edge fade; indicator dots are real buttons with >=44px hit areas; HTML first-paint defaults must mirror the SPOTIFY_PLAYLISTS data contract exactly (Gemini NO-GO catch, since fixed).
  - scripts/verify_blog_qa.py (in the blog repo) implements the 5 reliability gates; it now exists on disk and the CI workflow reference resolves.
  - Model routing per WP: GLM 5.3 Flash primary editor, Muse Spark 1.3 Contributor for bulk port + copy drafting (training tier accepted by owner), Gemini 3.1 Pro read-only auditor in Antigravity, Gemini 3.8 Flash spot-checks.
- **Consequences**:
  - Blog redesign pushed to production in 4 per-WP commits (chore/perf/feat(home)/feat(qa)).
  - The copy-refresh pipeline (draft brief in git-ignored drafts/, owner curates A/B, gates re-run) is the repeatable pattern for future copy work.

---

## ADR-009: Desktop Floating Switcher Restored Alongside Header Pill
- **Date**: 2026-09-17
- **Status**: Accepted
- **Context**: After live use, the owner explicitly wants the floating sticky switcher kept on desktop too (it was removed in favor of the header pill in ADR-008's control contract).
- **Decision**:
  - Desktop (>=769px) now has BOTH: the header lens pill (always visible in nav) and the floating switcher, which appears via IntersectionObserver once the hero switcher strip scrolls above the viewport.
  - Mobile (<=768px) keeps its scroll-driven floating switcher (scrollY > 180); the desktop observer exits early at innerWidth <= 768 so the two mechanisms never fight.
  - CSS restructured: base carries shared fixed positioning + .visible state for all viewports; the <=768px block only overrides top/width. All three button groups (hero strip, header pill, floating switcher) sync via [data-mode-tab].
- **Consequences**:
  - Redundancy on desktop after scroll is intentional (owner preference, not drift); if the pill ever feels duplicative, it can be dropped without touching the floating switcher.
  - Committed and pushed to production: 61b77f3..4883dd5 (blog repo).

---

## ADR-010: Header Lens Pill Removed; Unified Floating Switcher Trigger
- **Date**: 2026-09-17
- **Status**: Accepted
- **Context**: After live use with both desktop controls, the owner judged the header lens pill redundant with the floating switcher and asked to remove it.
- **Decision**:
  - The floating switcher is the single post-load lens control on every viewport.
  - Its trigger is unified and scroll-driven (scrollY > 180, hidden at top) on all breakpoints; the desktop-only IntersectionObserver and its hero-strip observation were deleted along with heroModeBar.
  - Remaining button groups: hero strip (in-flow) + floating switcher, both synced via [data-mode-tab].
  - Cache params bumped to 20260917c per the post-deploy CSS/JS change rule.
- **Consequences**:
  - At load (scrollY = 0) no lens switcher is visible; it appears after minimal scroll. The in-flow hero switcher remains reachable at the hero.
  - One mechanism, no breakpoint guards; future switcher work touches a single code path.

---

## ADR-011: Agent-Subagent Architecture & Two-IDE Workflow
- **Date**: 2026-09-22
- **Status**: Accepted
- **Context**: Personal workspace lacked structured agent orchestration. The MAPCLUB PO Workspace proved that a 7-agent roster with strict role separation, four-block handoffs, and deterministic gates dramatically improves quality and traceability. The owner uses two IDEs (Antigravity + OpenCode) and needs a disciplined handoff protocol between them.
- **Decision**:
  - **7-agent roster** with two user-facing entry points (`naquuubot` as Chief of Staff, `naquuu-curator` as Aesthetic Muse) and five hidden subagents (`naquuu-builder`, `naquuu-scribe`, `naquuu-librarian`, `naquuu-skeptic`, `naquuu-verifier`). Roster capped at 7 (beyond ~7, description-based routing reliability degrades).
  - **Persona files** live in `.opencode/agent/*.md`; permissions and registry in `opencode.jsonc`. No model fields in either — agents inherit the session model.
  - **Four-block handoff** (Result, Files Changed, Evidence, Blockers) is the universal subagent return contract.
  - **Author + Reviewer Pairing**: builder/scribe author, skeptic/verifier review. Max 2 review cycles before human escalation.
  - **Two-IDE workflow**: Antigravity (AGY) authors text artifacts and audits read-only; OpenCode (deepseek) handles terminal execution and runtime verification. One writer per tree, commit at every IDE handoff.
  - **`NAQUUUU_WORKSPACE` env var** replaces all hardcoded workspace paths. Scripts, agents, and relay skills resolve root from this variable.
  - **`TASTE_PROFILE.md`** is the live-editable ground truth for aesthetic preferences, read by agents at task time.
  - **Forward-compat**: `.githooks/pre-commit` and `.githooks/pre-push` (Phase 4), `host_check.py` (Phase 4), and `HOSTS.md` (Phase 4) are referenced in AGENTS.md now but implemented later.
  - **Corporate isolation**: the architectural *pattern* is adopted from MAPCLUB; zero domain content, credentials, or stakeholder names cross over (ADR-003).
- **Consequences**:
  - Structured delegation replaces ad-hoc single-agent prompting.
  - Every subagent report carries raw evidence and file citations, enabling audit.
  - Persona changes are a single-file edit (`.opencode/agent/<name>.md` or `TASTE_PROFILE.md`) — no JSON or code changes needed.
  - Model pinning and `verify_agent_config.py` are deliberately deferred to a future ADR once the varied provider mix is settled.
  - Stage 1 verification fixes (2026-09-22): sanitizer gate now scans git-tracked files by default with an `--all` escape hatch (untracked scraped dumps caused false positives); the owner's intentionally published inquiry number is allowlisted; the email rule quantifier is bounded to avoid quadratic backtracking on scraped HTML; AGENTS.md sections renumbered so Agent Orchestration is Section 4.

---

## ADR-012: Thin Relay Scope: Human-Operated AGY and Remote Handoff (Phase 3)
- **Date**: 2026-09-23
- **Status**: Accepted
- **Context**: The owner wants heavy authoring work to consume Antigravity (AGY) subscription quota instead of Google Cloud (GCP) credits, and wants to trigger and supervise that work remotely from a phone. An earlier design considered opencode/Hermes invoking the official `agy` headless CLI (`agy -p --output-format json`) as a delegation backend.
- **Decision**:
  - Programmatic AGY delegation is rejected: Antigravity ToS Section 6 prohibits "using the Service in connection with products not provided by us", and the Antigravity FAQ explicitly names third-party agents (including OpenCode) as a violation, recommending Vertex/AI Studio keys for programmatic Gemini. "Human-like" UI automation was rejected as evasion.
  - AGY stays human-operated: the owner pastes task briefs into the AGY IDE or the interactive `agy` TUI; the work consumes AGY quota directly.
  - Brief-and-notify handoff: opencode writes briefs to `internal-docs/briefs/`; Hermes sends WhatsApp notifications and result pings only. No agent invokes AGY.
  - Remote access: Tailscale mesh (laptop + phone, private). GUI path = RDP over Tailscale to the AGY IDE; phone-preferred path = OpenSSH Server + `agy` interactive TUI over Tailscale. No public exposure; AGY credentials and session never leave the laptop.
  - Model roles: opencode orchestrator and all subagents inherit the session model (deepseek-v4.1-flash); Hermes uses its configured provider (Nous Portal free, interim); AGY uses the owner-selected Gemini model under the Antigravity subscription.
  - Phase 3 tests must include negative tests proving no agent process invokes `agy` or proxies AGY.
- **Consequences**:
  - Heavy authoring burns AGY quota with zero terms risk; cost is one manual paste plus commit per AGY task.
  - Tailscale is pulled forward into Phase 3 and reused by the Phase 4 host topology.
  - If fully automated AGY usage is ever required, the sanctioned path is a Vertex/AI Studio API key (GCP billing) or a non-Google provider.

---

## ADR-013: Phase 3 v2 Scope (Review-Driven): Notification-First Relay, Privacy Stance, SSH+RDP
- **Date**: 2026-09-23
- **Status**: Accepted
- **Context**: Two independent adversarial reviews (an external 3.1 Pro review and a low-reasoning Astral review) challenged the Phase 3 plan. Verification against the machine and vendor terms confirmed: Nous Portal's default terms grant training and third-party data rights (Privacy Mode is an opt-out); the Hermes gateway's own shell/code execution is approval-gated with a fail-closed assessor (tirith) but the gateway does not enforce the CLI's training-tier guard; git hooks were absent; Windows 10 Pro supports RDP (currently disabled); OpenSSH is not installed; agents and the owner share one Windows account, so "no AGY automation" is policy, not yet a mechanical boundary.
- **Decision**:
  - Adopt Phase 3 v2 in tiers: 3A safety basics before any relay (git hooks pulled forward from Phase 4, Model-Input Boundary policy, minimal `scripts/host_check.py`, brief lock convention), 3B notification/read-only relay (status and brief creation only), 3C gated writes (per-job branch, path allowlist, approval via an independent channel, protected gates), 3D human-run remote AGY (Tailscale; SSH primary, RDP optional), 3E bounded negative tests.
  - Privacy: the owner explicitly declines Privacy Mode and accepts free-tier training for Hermes-routed chat content ("contributing to the open society"). The hard rule is unchanged: keys, credentials, phone numbers, and session tokens never enter any model context. This acceptance applies to chat content only and is a recorded exception to the Tier 1 paid-no-train preference.
  - Remote access: both paths over Tailscale-only. Install OpenSSH Server restricted to Tailscale; enable RDP with firewall scoped to Tailscale, acknowledging it locks the local screen while connected.
  - Isolation (separate Windows identity or VM for agents): deferred to the Phase 4 panel review; residual risk recorded here in the interim.
  - Negative tests are bounded claims: specified agents/identities lack specified capabilities under a documented threat model, with indirect-attempt tests. No claim of absolute prevention.
  - Supervision uses native tooling (`hermes gateway install`) plus the minimal host check; PM2/NSSM are not adopted.
  - Two-surface persona mirroring (OpenCode + AGY) is recorded separately in ADR-014.
- **Consequences**:
  - Remote chat can request work but cannot execute writes until 3C guardrails exist; heavy authoring stays human-run in AGY (ADR-012).
  - The sanitizer remains a git gate, not a model-input firewall; the Model-Input Boundary policy governs what enters model context.
  - Separate-identity isolation remains an open Phase 4 input, with residual risk accepted in the interim.

---

## ADR-014: Two-Surface Persona Mirroring (OpenCode + AGY)
- **Date**: 2026-09-23
- **Status**: Accepted
- **Context**: The two entry-point personas (`naquuubot`, `naquuu-curator`) existed only as OpenCode agents, so they never appeared in Antigravity 2.0's agent picker. AGY discovers custom agents exclusively from `.agents/agents/<name>.md` (workspace), `~/.gemini/config/agents/` (global), or plugin bundles — it does not read `opencode.jsonc` or `.opencode/agent/*.md`. The owner wants both surfaces to contribute to the workspace under the same orchestration discipline.
- **Decision**:
  - Mirror the two entry-point personas as AGY custom agents in `.agents/agents/naquuubot.md` and `.agents/agents/naquuu-curator.md`, selectable from the AGY message-box picker and `/agents` panel (`mainAgent: true`; picker support requires a build with custom agents, 2.15+).
  - Surface-specific frontmatter: AGY `naquuubot` is `subagent: false` (orchestrator is primary-only, mirroring OpenCode `mode: primary`) and runs `commandExecutionPolicy: sandbox`; AGY `naquuu-curator` is `mainAgent: true` + `subagent: true` (mirroring OpenCode `mode: all`) with an explicit tool list of `view_file` + `grep_search`.
  - **Open question — AGY tool semantics**: the docs table documents `tools` default as `[]` while the 2.15 changelog implies custom agents keep a default toolset unless switched off. `naquuubot` omits `tools`, betting on inherited defaults; whether curator's explicit list restricts or extends its toolset is unverified. A human picker smoke test (naquuubot can read/search/run; curator cannot edit or execute) must pass before the mirror is trusted; fallback is an explicit documented tool list on both agents.
    - **Resolved (2026-09-23, smoke test)**: omitting `tools` does not bind `run_command` — the AGY naquuubot reported it unavailable, so `commandExecutionPolicy: auto` alone cannot execute commands. An explicit `tools` list including `run_command` is required. Per-surface registries differ: the Antigravity 2.0 app registry rejected `code_search` ("unknown component: tool not found") and flags `multi_replace_file_content` as deprecated (both crash executor construction), while the IDE surface accepted the longer list. Final list in `.agents/agents/naquuubot.md`: view_file, grep_search, run_command, write_to_file, replace_file_content. Verified executing on the IDE surface; re-test the 2.0 app after reload.
  - `.opencode/agent/<name>.md` stays the single source of truth; persona edits land in both surfaces in the same change.
  - Hidden subagent roster (`builder`, `scribe`, `librarian`, `skeptic`, `verifier`) remains OpenCode-only for now; AGY-side delegation is limited to built-in subagents plus `naquuu-curator`.
  - Human-operated AGY (ADR-012) is unchanged: no agent invokes the `agy` CLI or proxies AGY; the mirror makes the personas available inside a human-run AGY session.
  - AGY tool lists use only documented tool names (`view_file`, `grep_search`, `run_command`, `replace_file_content`) — the docs' tool-validation known issue is why AGY tool lists stay minimal.
  - **Open question — Standing Rule 3**: the AGY `naquuubot` runs `commandExecutionPolicy: sandbox`, which overlaps with Standing Rule 3 ("Antigravity audits text only; only OpenCode verifies runtime"); reconcile before Phase 4.
- **Consequences**:
  - Both IDEs can run the same entry-point personas; AGY-side work consumes AGY quota under the owner-selected Gemini model.
  - Persona changes become two-file edits across surfaces, enforced by manual review until a future `verify_agent_config.py` sync check exists.
  - The human smoke test also confirms the installed AGY build lists both agents and resolves the tool-semantics open question as expected.
  - Platform gaps are explicit: AGY has no four-block enforcement, no `task` allowlists, and no model pinning (models inherit the owner-selected AGY model).

---

## ADR-015: Entry-Point Latency Budget (Model Pinning + Task Triage)
- **Date**: 2026-09-23
- **Status**: Accepted
- **Context**: Neither entry-point agent pinned a model, so fresh sessions defaulted to the free-tier `big-pickle` model with variable queue latency (observed via `opencode run`: `naquuu-curator · big-pickle`). The `naquuubot` persona also mandated the full gate → classify → plan → delegate → verify ceremony for every engineering prompt, paying multi-round-trip cost on trivial/read-only asks. Measured local costs are negligible (sanitization gate 0.30 s, `git status` 0.15 s): the latency lives in model selection and round-trip count, not workspace scripts.
- **Decision**:
  - Pin workspace default and small model to the paid flash tier in `opencode.jsonc` (`opencode-go/deepseek-v4.1-flash` / `opencode-go/deepseek-v4-flash`) so entry points and subagents skip the free-tier queue.
  - Add triage to the `naquuubot` persona: trivial/read-only asks act directly; full ceremony is reserved for standard/multi-step work. The sanitization gate is a pre-commit gate (AGENTS.md Section 1), not a pre-prompt tax.
  - Bash auto-approval with commit/push ask and destructive deny (`opencode.jsonc`), removing human-in-the-loop latency for shell commands.
- **Consequences**:
  - Prompt→result on this host is deterministic; hosts without `opencode-go` auth must override `model` in their global config (Phase 4 multi-host note).
  - Free-tier fallback is no longer the default; an unavailable paid model fails closed until the user switches model in the TUI.
  - Delegation is reserved for work that benefits from role separation, not single-step tasks.

---

## ADR-016: Autonomous Execution Posture (Owner Override of Review Gating)
- **Date**: 2026-09-23
- **Status**: Accepted
- **Context**: The review-driven plan (ADR-013) gated dangerous execution behind approvals (Hermes `approvals.mode=smart` with fail-closed unattended modes; Phase 3 3C writes requiring approval via an independent channel). The owner's usage is WhatsApp-driven work away from the laptop, where per-command approvals are impractical; on 2026-09-23 the owner directed full execution autonomy.
- **Decision**:
  - Hermes approvals: `mode=off`; `cron_mode`, `single_query_mode`, and `unattended_mode` set to `approve`; a destructive deny-list blocks even under autonomy: `rm -r*`, `git reset --hard*`, `git push --force*`, `git push -f*`, `git clean -*`, `git checkout -- .*`, `Remove-Item -Recurse*`, `rd /s*`, `format *`, `diskpart*`, `shutdown*`, `bcdedit*`, `reg delete*`, `*-EncodedCommand*`, `certutil -urlcache*`, `wmic*delete*`, `sc delete*`.
  - opencode `naquuubot` and `naquuu-builder`: `external_directory` allowed for files outside the worktree, with Hermes state (`~/AppData/Local/hermes/**`) denied per the Model-Input Boundary. Bash stays auto-approved (ADR-015) with `git commit`/`git push` as `ask` and destructive denies.
  - The independent-approval design in Phase 3 3C is superseded; relay work runs autonomously.
  - `git commit`/`git push` remain the publication gate; force-push stays blocked by the Hermes deny-list.
  - The Model-Input Boundary and Tier 1 secret rules remain policy-level and are not mechanically enforced once bash is auto-approved.
- **Consequences**:
  - WhatsApp-driven execution no longer stalls on approvals.
  - Accepted residual risk: prompt injection or a compromised allowlisted WhatsApp account can execute arbitrary non-denied commands with the owner's rights. The deny-list and the commit/push ask are the remaining mechanical guards; the 3.1 Pro / Astra gating recommendations are knowingly overridden.
  - The Hermes gateway must be restarted to load the approvals changes.

---

## ADR-017: Permission Surface Roll-Up (Zero Non-Key Prompts)
- **Date**: 2026-09-23
- **Status**: Accepted
- **Context**: Owner directed that shell-adjacent work (ssh, env vars), tooling installs (plugins, MCP servers, skills), and external-path access should never prompt; only commit/push stay reviewable. External-directory allow existed only on `naquuubot` and `naquuu-builder` (ADR-016), so the five specialist subagents still asked on out-of-worktree paths.
- **Decision**:
  - Hoist `external_directory` to top-level `permission` (`"*": "allow"`, `~/AppData/Local/hermes/**` denied); removed the two agent-level duplicates. All seven agents inherit it; agent-level blocks still take precedence elsewhere.
  - Set `skill: "allow"` explicitly at top level (already the default, now documented).
  - No other prompt sources exist: ssh/scp and env vars are ordinary bash (auto-approved); plugin/MCP/skill installs run through bash + edit (both auto-approved). `git commit`/`git push` stay `ask`; `doom_loop` stays the default `ask`.
  - Per ADR-016 line on policy-level boundaries, no mechanical `.env` guard is added to bash, and the opencode destructive deny-list is not expanded to the Hermes ADR-016 list (left for owner review).
- **Consequences**:
  - Remaining prompts: commit/push (key decision) and doom-loop repeats (rare).
  - All agents may read arbitrary external paths except Hermes state; accepted under ADR-016's autonomy posture.
  - Outcome (2026-09-23): the AGY parity brief (`internal-docs/briefs/2026-09-23-agy-permission-parity.md`) closed — `.agents/agents/naquuubot.md` now runs `commandExecutionPolicy: auto` with the triage and delegation-economy wording mirrored; `eager` has no published definition in the Antigravity docs checked and was not adopted.

---

## ADR-018: Thin Relay v1 Implemented (WhatsApp to opencode)
- **Date**: 2026-09-23
- **Status**: Accepted
- **Context**: Phase 3B needed WhatsApp tasks to reach the full opencode orchestration instead of Hermes executing workspace work with its own tools. Constraints: no AGY automation (ADR-012), autonomous execution (ADR-016), commit/push stay gated (ADR-015).
- **Decision**:
  - Implement the relay as a Hermes local skill (`opencode-relay`, installed at `%LOCALAPPDATA%\hermes\skills\relay\opencode-relay\SKILL.md`) that runs `opencode run "<task>"` from the hub and returns trimmed output.
  - The canonical copy and rules live in the hub at `internal-docs/relay/README.md`; re-copy after edits.
  - Relay prompts carry no secrets; commits and pushes stay `ask`; AGY work goes through human briefs.
- **Consequences**:
  - Phone requests now execute with the 7-agent roster, gates, and pinned models; evidence captured for the CLI path and the WhatsApp round-trip.
  - Job IDs remain informal; a durable queue or approval channel was superseded by the autonomy posture and can be revisited if needed.
  - The relay depends on Hermes skills discovery at session start; new skills may need a gateway restart.

---

## ADR-019: DigitalOcean Managed Agents as Phase 4 Remote Execution Host and MCP Layer
- **Date**: 2026-09-23
- **Status**: Accepted
- **Context**: The Phase 3 relay depends on the laptop being awake (ADR-018), and Phase 4 needs a remote execution host. DigitalOcean Managed Agents entered public preview on 2026-09-21: Harness Runtime runs coding agents (OpenCode is a first-class adapter) in microVMs with pause/resume/fork and per-second billing; Action Gateway is a managed MCP endpoint (16,000+ tools; credentials brokered outside the sandbox). The staged plan and risk register live in `internal-docs/research/2026-09-23-do-managed-agents-phase4.md` (skeptic-reviewed). Stage B executed 2026-09-23: OpenCode connected to Action Gateway via OAuth, a `droplet:read` provider connection was authorized, and a read-only call returned real data at $0.00 against a $5 signup credit (`doctl harness-runtime balance`: Status OK).
- **Decision**:
  1. Adopt the staged integration: B (Action Gateway MCP into local opencode, done) then A (relay-dispatched DO OpenCode sessions) then C (unattended cron/webhook triggers); defer D (cloud Hermes gateway) to a separate risk review.
  2. Scope Critical Rule 3: GCP remains the credential and model home for Tier 1; DO is an approved compute/execution host and MCP tool layer for Tier 2/3 content. Tier 1 material never runs on DO sessions. The DO API token is Tier 1 and lives only in hub `.env`.
  3. Model inference for DO sessions is DO Inference (`HARNESS_INFERENCE_*`) or a BYO provider key; the opencode-go auth is expected not to transfer (ADR-015 multi-host note) and is verified in Stage A.
  4. Budget: the $5 signup credit with auto top-off off; the prepaid balance is the hard stop (preview terms Section 5.14). No per-session spend limits exist.
  5. All gates, sanitization, and commit/push stay local and are never re-hosted; no writes to the hub or child repos from Stage A or B until a commit/push policy exists for DO hosts.
  6. Stage C triggers only with deny-by-default specs (no ask rules), no GitHub credential, bash-matcher deny rules for git push/commit/reset/clean and rm -rf, and the T1 no-push negative test passing.
  7. Phase 3/4 alignment: the Phase 4 host topology gains a managed host class (spec Section 10); `HOSTS.md` must include it; `host_check.py` gains DO readiness checks in Phase 4; the VPS plan remains the fallback/standby path.
  8. Sanitizer coverage: `scripts/verify_sanitization.py` now detects `dop_v1_` tokens and live Action Gateway session URLs.
- **Consequences**:
  - Preview risk is contained to disposable workloads; no SLA, no durability guarantees, termination at will.
  - A second cloud credential enters the workspace (Tier 1, hub `.env` only); rotation and monitoring become workspace duties.
  - Model routing diverges between local hosts (opencode-go pin) and DO hosts (DO Inference or BYO provider).
  - Per-invocation Action Gateway costs add a billing dimension; the wallet is the hard stop.
  - The Stage B gateway session runs Default Action Allow; a tighter session (read-only allow, writes ask) is required before Stage C.
  - AGENTS.md Critical Rule 3 amended in the same change.
  - Cloud Hermes (Stage D) remains out of scope until a separate risk review.
  - **Amendment (2026-09-23, five-review panel + owner decision)**: five independent adversarial reviews (Opus 4.6, 3.8 Flash High, 3.1 Pro High, Muse Spark 1.3, Big Pickle) reviewed the Stage B evidence and the staged plan. Consensus: STOP before Stage A — Stage B proved connectivity, not controls. Accepted blockers: (1) teardown the Allow-default agent and recreate with `default_action: deny`, proving a forbidden call is rejected platform-side; (2) confirm the enforcement locus (platform-enforced vs advisory); (3) guardrails restated as egress allowlist + bash denied for read-only jobs + server-side branch protection as the no-push backstop + IAM minimality, with client-side deny rules as defense-in-depth only; (4) token scope inventory + revocation drill + storage without env-var/argv exposure + separate admin/agent identity; (5) model-backend verification gate (which model sessions call; whether the key is pinnable) before any Stage A; (6) spend controls: autorecharge OFF (already recorded), card cap, threshold alerts, billing-lag re-measure, relay turn/time budgets, kill switch reachable without the laptop; (7) Insights opt-out verified before any data transits; (8) ingestion gate: DO artifacts are untrusted patches requiring manual review + sanitization before the laptop tree; (9) egress split-brain: add secret/egress scanning on WhatsApp outbound and fetch tools; (10) induced-push rule: DO output must never ask the human to run commit/push; (11) governance: incident runbook, DO account 2FA, transcript retention, preview exit/export plan.
  - **Owner decision (2026-09-23): decoupled topology (option a)** — the relay moves to a plain droplet/VPS (Tailscale + systemd, flat cost) for availability; DO Managed Agents is used only as a sandboxed worker after the gates pass. Stage 0 (zero-cost guardrail probes) approved; Stage A stays blocked until the gates pass; Stage D remains deferred.
  - **Stage 0 result (2026-09-23, no-token probes)**: deny-default is documented as supported ("Deny: Block calls unless a more-specific rule permits them"; "Selected tools" restricts the catalog and an allow rule cannot widen it); session configuration is fixed at creation and replacing a session does NOT revoke provider connections (connections are managed separately); doctl 1.171.0 present via winget (PATH stale in some shells). Remaining probes are owner/token actions: console deny-default session + rejected-call proof, revocation drill, Insights opt-out, alerts/card cap, 2FA, phone-only kill drill.
  - **Stage 0 Gate 1 PASSED (2026-09-23, live probe)**: a deny-default Action Gateway session (`naquuuu-deny-probe`; Default Action Deny; Selected tools: List Droplets = allow) was probed directly over the MCP endpoint via a script that never printed the OAuth token. Evidence: allowed call `digitalocean_droplet-list` executed (`{"text":"[]"}`); forbidden read `digitalocean_droplet-get` denied platform-side (`Tool "digitalocean_droplet-get" is denied by the session policy.`); forbidden write `digitalocean_droplet-delete` denied identically; `action_invoke` is itself denied by policy (restricted sessions expose only `action_search`, while direct tool calls are policy-evaluated); discovery searches for create/delete/resize return only the allowed tool. Conclusion: deny-by-default is platform-enforced, not advisory. Finding for future sessions: for an agent (opencode) to invoke tools in a restricted session, either preload the allowed tools or explicitly allow `action_invoke`; also delete the superseded Allow session (teardown).

---

## ADR-020: Remote Access Live (Tailscale + RDP; SSH Deferred)
- **Date**: 2026-09-23
- **Status**: Accepted
- **Context**: Phase 3D needed phone access to operate AGY (human-run per ADR-012) and the workspace. Tailscale was installed but its daemon wedged at `NoState` through logins, a state reset, and service restarts; a clean reinstall plus post-login warm-up fixed it. The OpenSSH Server install hung on Windows Update (likely a corporate WSUS source), so the SSH path was blocked.
- **Decision**:
  - Remote access = Tailscale mesh + RDP, reachable only on the Tailscale interface (built-in wide firewall rules disabled) with Network Level Authentication disabled because the account is Azure AD (`UserAuthentication=0`).
  - SSH deferred; the two fallbacks are the Win32-OpenSSH release (no Windows Update dependency) or Tailscale's built-in SSH (`tailscale set --ssh` plus a tailnet ACL rule).
  - `scripts/setup_remote_access.ps1` captures the full setup (OpenSSH attempt, tailnet-only firewall scoping, RDP + NLA) with transcript logging; verified live from the iPhone.
- **Consequences**:
  - The phone drives the full desktop, so AGY authoring is possible remotely with the owner as the operator.
  - The laptop's local screen locks during RDP sessions (normal Windows client behavior).
  - NLA is off, so RDP security relies on Tailscale scoping plus the account password; keep the tailnet ACLs tight.
  - If the laptop's network blocks Tailscale (some corporate networks), remote access stops until it reconnects.

---

## ADR-021: Spotify Taste Snapshot for Curator Ground Truth
- **Date**: 2026-09-23
- **Status**: Accepted (implementation verified; live auth/fetch pending owner one-time Spotify app setup)
- **Context**: `internal-docs/TASTE_PROFILE.md` v1 (compiled from naquuuu.github.io) inferred music taste from the public site. The owner asked for real listening data via the Spotify Web API. `naquuu-curator` is read-only by design (no bash, no tools), so it cannot call an API at task time; and Spotify's February 2026 Dev Mode changes (owner Premium required, batch endpoints removed, playlist `tracks` to `items` rename) constrain any integration.
- **Decision**:
  1. Local-only Authorization Code + PKCE flow via `scripts/spotify_taste.py` (stdlib-only; no client secret, no hosted callback). Subcommands: `auth` (one-time browser consent on loopback `http://127.0.0.1:8080/callback`), `fetch` (top artists/tracks over 3 time ranges, playlists, recently played), `status` (masked auth report).
  2. Tier 1 handling: `SPOTIFY_CLIENT_ID` lives in hub `.env`; the refresh token lives in `.secrets/spotify_token.json` (git-ignored). Neither is ever read by agents, printed to stdout, or written into the snapshot.
  3. The curator consumes a sanitized generated snapshot at `internal-docs/SPOTIFY_SNAPSHOT.md`; `TASTE_PROFILE.md` section 2 carries the pointer. Refresh is owner-run (`fetch`), not scheduled.
  4. Runbook: `internal-docs/SPOTIFY_INTEGRATION.md` (setup, refresh, troubleshooting, security rules).
- **Consequences**:
  - Curator music context becomes real data, refreshed on demand; the snapshot is stale until `fetch` is re-run.
  - The app owner must keep active Spotify Premium (Feb 2026 Dev Mode rule) or the app stops working until resubscribed.
  - New ignored path `.secrets/` and new env var in `.env.example`; sanitization gate remains mandatory pre-commit.
  - Live `auth`/`fetch` paths are owner-run and remain unexercised until setup completes.

---

## ADR-022: Agent ID Standardization to naquuuu (4u)
- **Date**: 2026-09-24
- **Status**: Accepted
- **Context**: The workspace brand and all repositories use the "naquuuu" (4u) spelling, but the seven agent IDs carried the 3u spelling ("naquuu-*") across both persona surfaces, config, and living docs. Owner directive (2026-09-24): the agent IDs should be naquuuu (4 u, not 3u) and the workspace updated accordingly.
- **Decision**:
  - Standardize all agent IDs and references to the 4u spelling: `naquuuubot`, `naquuuu-curator`, `naquuuu-builder`, `naquuuu-scribe`, `naquuuu-librarian`, `naquuuu-skeptic`, `naquuuu-verifier`; the delegation allowlist pattern becomes `naquuuu-*`.
  - Renamed in the same change: `.opencode/agent/` (7 personas), `.agents/agents/` (2 AGY mirrors), `opencode.jsonc` (agent keys, `default_agent`, task allowlist), `AGENTS.md`, and the living internal-docs (`AGENT_PLAYBOOK.md`, the architecture spec, relay README, `SPOTIFY_INTEGRATION.md`, `TASTE_PROFILE.md`).
  - Historical records (prior ADRs, dated briefs, research) keep their original text; this ADR is the rename note.
- **Consequences**:
  - Invocations use the new names from the next session (`opencode run --agent naquuuubot`; AGY agent picker); the WhatsApp relay picks up `default_agent` automatically on its next run.
  - The Hermes-installed relay skill copy still shows the old example and needs a manual re-copy (the Hermes path is agent-denied); the canonical copy is updated at `internal-docs/relay/README.md`.
  - External notes or pinned invocations using the 3u names must switch to 4u.

---

## ADR-023: naquuuu-curator Context Update (Listener First; Na/Gua Register Routing)
- **Date**: 2026-09-24
- **Status**: Accepted
- **Context**: The owner supplied the curator's updated context: Listener First, Fixer Second ("solving isn't the same as loving"); dual-register voice routing — the warm "Na" voice for creative, emotional, or hybrid tasks and the blunt "Gua" voice for logical or operational tasks, with hybrids defaulting to Na; bilingual (ID/EN) South Jakarta fusion with domain vocabulary; clean orthography; cohesive rhythm, no rapid-fire micro-bursts.
- **Decision**:
  - Both persona surfaces (`.opencode/agent/naquuuu-curator.md`, `.agents/agents/naquuuu-curator.md`) adopt this context; the previous fragmented rapid-fire voice spec is superseded, including the same-day staged edit.
  - Workspace mechanics are unchanged: `TASTE_PROFILE.md` ground truth, four-block handoff, read-only AGY surface, no delegation.
  - The `AGENT_PLAYBOOK.md` character sheet and the `opencode.jsonc` agent description are updated in the same change.
- **Consequences**:
  - The curator's register now routes by task type; hybrid tasks default to the warm register.
  - Two-surface mirror sync (ADR-014) is maintained in the same change.

---

## ADR-024: WhatsApp Group Intake via Per-Group Allowlist (Relay)
- **Date**: 2026-09-24
- **Status**: Accepted (group replies verified live; host_check READY)
- **Context**: The owner wanted the WhatsApp relay usable in a group chat, not just DMs. Hermes defaults to `WHATSAPP_GROUP_POLICY=pairing`, which forwards nothing from groups, so group messages never reached the agent. A first attempt with `group_policy=open` was rejected by the installed Hermes v0.21.4: it refuses to start with `open` unless `WHATSAPP_ALLOW_ALL_USERS` is enabled (safe-mode rail, confirmed via foreground run: "Refusing to start … Gateway exiting cleanly"), and the refusal surfaced as an unexplained gateway outage (spawns exited cleanly; Windows logged no crash).
- **Decision**:
  1. Group intake = per-group allowlist: `WHATSAPP_GROUP_POLICY=allowlist` + `WHATSAPP_GROUP_ALLOWED_USERS=<group JID>@g.us` for the private test group; `WHATSAPP_REQUIRE_MENTION=true` (reply only to @mentions, replies to the bot, or /commands). `open` is not used; `WHATSAPP_ALLOW_ALL_USERS` is rejected as unsafe (any sender could trigger the relay).
  2. Sender gating stays layered on top: `WHATSAPP_ALLOWED_USERS` carries the owner plus one guest number (owner-side config; numbers never enter the repo or model context).
  3. Tooling: `scripts/whatsapp_group_fix.py` applies the policy idempotently (timestamped `.env` backup; number/JID values passed on the command line only, never echoed). On this VBS-only Windows install the script falls back to `hermes gateway start` when `gateway restart` reports a service-manager failure.
  4. Operational notes: a stale bridge process from a previous run can hold port 3000 and must be cleared before restart; the gateway's Windows auto-start is a Startup-folder VBS (no scheduled task).
- **Consequences**:
  - The relay is reachable in the allowlisted group only, mention-gated; all other groups stay silent; DM behavior is unchanged.
  - The group JID is a private identifier (owner-side); docs and the repo keep only the setup pattern.
  - Residual risk unchanged and restated: any allowlisted account can trigger `opencode run` with full autonomy; keep the allowlist tight.
  - `hermes update --backup` (install is 1021 commits behind) remains the recommended maintenance to normalize the Windows service/restart path.

---

## ADR-025: Automatic Workspace Sync (Gate-Protected Auto-Commit + Node Auto-Pull)
- **Date**: 2026-09-25
- **Status**: Accepted (live on the laptop and the VPS; home server pending its tailnet join)
- **Context**: The owner works across several machines (the laptop, the always-on VPS, a second laptop, and a planned home-server laptop) and does not want manual `git push`/`pull` steps. The previous posture (ADR-015/016) kept commit and push as the human gate. Multi-writer reality now needs a deterministic convergence mechanism that still protects the public repo.
- **Decision**:
  1. Every node runs a sync timer: Windows laptop — a Scheduled Task (`Naquuuu Hub Auto-Sync`) every 10 minutes; Linux nodes (VPS, home server) — a systemd user timer every 5 minutes.
  2. The sync routine is uniform: `git fetch` → if the tree is dirty, run `scripts/verify_sanitization.py` (abort on failure) → `git add -A` + `git commit` → `git rebase --autostash origin/main` → `git push origin main`.
  3. GitHub remains the canonical hub. Standing Rule 1 (one writer per tree) is amended for this personal workspace: any node may write, but nodes stay converged through auto-sync, and work stays on one thread at a time to avoid same-file conflicts.
  4. Artifacts: `scripts/hub_autosync.ps1` (Windows), `scripts/node_autosync.sh` (Linux), `scripts/provision_home_server.sh` (home-server onboarding: base packages, Tailscale, always-on, clone, opencode, sync timer).
  5. The VPS stays push-disabled until a repo-scoped deploy key is provisioned (owner-approved; pending). Failed pushes from read-only nodes are non-fatal by design.
- **Consequences**:
  - Commit history gains `chore(sync): <host> <timestamp>` entries; the public repo mirrors the workspace within ~10 minutes.
  - A failed sanitization gate blocks the commit/push (by design); a rebase conflict stops the sync and leaves the tree for manual review.
  - The laptop is no longer the sole writer; the VPS can push once the deploy key lands, and the home server joins as a replica/worker node.

---

## ADR-026: M1 Complete — Relay Hosted on the VPS (Scoped Writer)
- **Date**: 2026-09-25
- **Status**: Accepted (verified live from WhatsApp)
- **Context**: The decoupled topology (ADR-019 amendment) planned the relay on a plain VPS, with the laptop remaining the hub. M1 required the WhatsApp front door to survive the laptop being off. The VPS (Tencent Cloud Lighthouse, 2 vCPU / 2 GB / 40 GB, Singapore, Ubuntu 24.04) now runs Hermes, the WhatsApp bridge, opencode, and a workspace clone.
- **Decision**:
  1. The VPS is the **live relay host**: the WhatsApp session was copied from the laptop (laptop copy retained as rollback); the gateway runs as a systemd user service with lingering enabled.
  2. The VPS is a **scoped writer**: a repo-scoped ed25519 deploy key (write enabled) is registered on GitHub and installed on the VPS; the clone's remote is SSH. Scope is that one repository; revocable from the repo's Deploy keys page.
  3. All host trees converge through the ADR-025 auto-sync (laptop Scheduled Task; VPS and home-server systemd user timers).
  4. The **laptop** remains a workstation/co-writer; its Hermes gateway is stopped and its session copy is the rollback path.
  5. Two independent model layers: the Hermes assistant runs on Nous Portal; the opencode worker runs on `opencode-go` (pinned in `opencode.jsonc`).
- **Consequences**:
  - The relay survives the laptop being off; WhatsApp tasks run against the VPS clone and the VPS can commit/push them (gate-protected).
  - The home server is onboarded as a synced replica and M2 worker candidate; dispatch + queue remain M2 work.
  - Operational notes: only one WhatsApp bridge may run at a time — after `hermes gateway stop` an orphaned `bridge.js` can survive and must be cleared (verify port 3000) before starting another host; the WhatsApp env transfer must include `WHATSAPP_ENABLED` (a filtered copy can miss it) and the VPS bridge needs `npm install` once before its first start.

---

## ADR-027: WhatsApp Relay UX Standard (Human Tone, No Meta, Curator Route)
- **Date**: 2026-09-25
- **Status**: Accepted (applied on the relay host; tone upgrade pending a stronger assistant model)
- **Context**: After M1, the owner reported the WhatsApp replies still felt robotic: bullets and menus in place of conversation, capability monologues, process narration, and one reply that printed a raw recipient identifier. The owner also wants to reach `naquuuu-curator` from WhatsApp instead of only inside the IDE.
- **Decision**:
  1. **Display**: on the relay host the WhatsApp platform runs with `tool_progress: off`, `show_reasoning: false`, `interim_assistant_messages: false`, and `streaming: false` (`display.platforms.whatsapp`).
  2. **Persona** (`~/.hermes/SOUL.md` on the relay host): human, 1-3 sentences by default, no bullet lists or choice menus unless asked, no process narration (skills/tools/reasoning), failures in one plain sentence, and **never print phone numbers, IDs, or JIDs** — people are named, not numbered.
  3. **Routing**: workspace/agent/project/state questions run `opencode run --agent naquuuubot` and are answered from the result, never from Hermes memory or other skills. Curator-directed messages (`@curator`, "ask the curator", "curator:") run `opencode run --agent naquuuu-curator` and relay the curator reply, trimmed.
  4. **Model**: the assistant model must be capable; the free-tier default produced verbose, manual-like output. The owner selects via `/model <name> --global`.
  5. **Canonical persona**: the SOUL text is versioned in the repo (`internal-docs/relay/WHATSAPP_SOUL.md`) and copied to the relay host.
- **Consequences**:
  - Replies read like a colleague; workspace answers stay grounded in the repository through opencode.
  - The curator is reachable from WhatsApp without a second number; a dedicated second-number curator bot remains an option if the owner wants separate creative threads.
   - Any future persona or display change lands in both the repo copy and the relay host (mirror rule, same as ADR-014).

---

## ADR-028: Relay Policy Bundle — Assistant Provider, Image Generation, Group Intake, Anti-Leak
- **Date**: 2026-09-25
- **Status**: Accepted (owner-set; policy record)
- **Context**: After M1 (relay on the VPS, ADR-026) and the UX standard (ADR-027), several day-of decisions had no single record: which assistant provider the relay prefers, how images are generated, how group access is granted, and how identifiers may be handled. They are bundled here so agents stop re-deriving them.
- **Decision**:
  1. **Assistant provider**: Nous Portal is primary for the Hermes relay assistant; **Gemini is the configured fallback** so a primary outage does not silence the relay. Model choice stays owner-side (`/model <name> --global`); the ADR-027 "must be capable" bar applies to both.
  2. **Image generation has no viable free tier**: the keyless free generator was dropped the same day it shipped; generation runs through the Gemini API in `scripts/gen_image.py` with a configurable model and a fallback chain (`gemini-3.1-flash-image` → `gemini-2.5-flash-image` → `gemini-3-pro-image`), keyed by `GEMINI_IMAGE_KEY` (fallback `GOOGLE_API_KEY`). Vision (reading images) stays on `auxiliary.vision`.
  3. **Pinned model IDs retire without notice**: external-model callers keep a configurable model plus a fallback chain rather than a single hardcoded ID (grounded in the `gen_image.py` chain).
  4. **Group intake is an explicit allowlist, not a config edit**: `WHATSAPP_GROUP_POLICY=allowlist` + `WHATSAPP_GROUP_ALLOWED_USERS`, managed by the owner-driven command in `scripts/wa_group_allow.py`, with the mention gate on; `open`/allow-all is refused and not used; sender gating stays on `WHATSAPP_ALLOWED_USERS` (ADR-024).
  5. **Anti-leak**: the relay never prints phone numbers, IDs, or JIDs — people are named (ADR-027). The rule covers tool output and error text, not only persona prose.
- **Consequences**:
  - A primary-provider outage fails over instead of going dark; the fallback must be validated when changed.
  - Image generation is paid and key-gated; a missing or billing-disabled key is a one-line failure, never a stack trace.
  - Adding a group is a command; removing one is the same command inverted.
  - Any relay surface that can print an identifier is a leak surface; reviewers check tool output, not just the persona.

---

## ADR-029: M2 — Worker Dispatch and Durable Queue (VPS → Home Server)
- **Date**: 2026-09-25
- **Status**: Approved 2026-09-28 by owner; activating (worker SSH trust + relay-skill wiring in progress; was Proposed with scripts authored)
- **Context**: The VPS relay (2 vCPU / 2 GB) is the always-on WhatsApp front door but is too small for heavy dev jobs. The home server (`mipad-linux`, i5-8250U / 8 GB) is an onboarded synced replica and the M2 worker candidate (ADR-026). Heavy jobs should run on the worker over Tailscale and must survive the worker being offline.
- **Decision (proposed)**:
  1. **Dispatch**: `scripts/dispatch_job.sh` runs on the relay host; heavy engineering tasks go to the worker over SSH when reachable, and are enqueued durably when not. `--local` keeps light work on the relay host (RELAY_PLAN §1).
  2. **Durable queue**: `~/.naquuuu/queue/{pending,done,failed}/` with header-prefixed job files (no `jq` dependency); `scripts/drain_queue.sh` drains at most one job per tick under a `flock` (with a `mkdir`-lock fallback that fails closed), enqueues atomically (tmp + `mv`), and validates job ids before using them in paths.
  3. **Timer**: `scripts/install_dispatch_drain.sh` installs the drain + `job_status.sh` helpers and a systemd user service + timer on the relay host, with unit timeouts and an `EnvironmentFile` (`~/.config/naquuuu/dispatch.env`) so tunables reach the timer (mirrors the ADR-025 pattern).
  4. **Worker execution**: `scripts/worker_exec.sh` runs on the worker (best-effort pull, then opencode). Commit/push are not expected and not credentialed on the replica — that is policy, not a mechanism.
  5. **Trust**: a **dedicated** relay→worker ed25519 key (`NAQUUUU_WORKER_KEY`, default `~/.ssh/id_ed25519_worker`) is pinned with `-i` + `IdentitiesOnly=yes`; the GitHub deploy key is never used for worker SSH, and a missing key means the worker is not ready (the job queues). The owner authorizes it with `scripts/authorize_worker.sh`.
  6. **Resilience**: remote runs are wrapped in `timeout` (`NAQUUUU_JOB_TIMEOUT`, default 1800 s) with `ServerAliveInterval`; a reachable-but-failing dispatch is enqueued rather than dropped.
  7. **Results and retention**: completions append to `$NAQUUUU_QUEUE_DIR/completed.log` and are summarized by `scripts/job_status.sh`; `--prune` with `NAQUUUU_QUEUE_KEEP` (default 50) bounds `done/` and `failed/`. Job bodies are stored verbatim and must be Tier 2 only (owner responsibility).
  8. **Configuration** is by env only: `NAQUUUU_WORKER_HOST`, `NAQUUUU_WORKER_USER`, `NAQUUUU_WORKER_REPO`, `NAQUUUU_REPO`, `NAQUUUU_WORKER_KEY`, `NAQUUUU_QUEUE_DIR`, `NAQUUUU_WORKER_REACH_TIMEOUT`, `NAQUUUU_JOB_TIMEOUT`, `NAQUUUU_MAX_ATTEMPTS`, `NAQUUUU_DRAIN_BATCH`, `NAQUUUU_QUEUE_KEEP`, `OPENCODE_ATTACH`, `NAQUUUU_OPENCODE`.
- **Consequences**:
  - Heavy jobs are bounded by the worker's RAM, not the relay's; the optional 4 GB VPS upgrade is avoided.
  - Queued jobs wait for the worker instead of failing; the owner sees a `queued` reply, and results are archived and queryable via `scripts/job_status.sh` (the relay skill is not yet wired to poll them — pending approval).
  - Adds one network hop to heavy jobs; light work stays local on the relay host.
  - **Open**: worker key authorization and owner approval before the relay skill is switched to dispatch.

---

## ADR-030: WhatsApp Sender Allowlist Is Owner-Side (No Chat Command)
- **Date**: 2026-09-25
- **Status**: Accepted (policy record)
- **Context**: In a shared group the group allowlist was granted, yet members other than the owner/guest stayed silent. The owner asked the bot in chat to "whitelist <number>"; the relay refused because `scripts/wa_group_allow.py` manages group JIDs only, while person admission lives in `WHATSAPP_ALLOWED_USERS`. A chat command that takes typed numbers would push Tier 1 identifiers through the model (AGENTS.md Model-Input Boundary), and a log-derived "latest sender" variant would usually capture the owner's own command.
- **Decision**:
  1. Group admission (`WHATSAPP_GROUP_ALLOWED_USERS`, via `scripts/wa_group_allow.py`) and person admission (`WHATSAPP_ALLOWED_USERS`) stay separate gates. Granting a group does not admit its members.
  2. Person admission is owner-side only: `scripts/whatsapp_group_fix.py --allow-user <digits>` on the relay host, or edit `WHATSAPP_ALLOWED_USERS` and restart. No WhatsApp chat command exists and none is planned while phone numbers remain Tier 1.
  3. `WHATSAPP_ALLOW_ALL_USERS` / `WHATSAPP_ALLOWED_USERS=*` stay rejected (ADR-024). Add named people, never the whole room.
  4. Deferred: a name-resolution tool (owner types a display name; a script resolves it against the bridge log and appends the JID without printing it) is gated on verifying the bridge log exposes display names plus sender JIDs.
- **Consequences**:
  - "Allowlist this person" in chat gets a one-line owner-side instruction instead of a dead end; the relay never handles numbers.
  - Every added person can trigger `opencode run` with full autonomy (ADR-016 residual risk); keep the list tight.
  - The two-gate model is documented in `internal-docs/relay/README.md` and `internal-docs/LESSONS.md` #13; the relay skill copies carry the owner-side redirect rule.

---

## ADR-032: Phone-Driven VPS Access via a Thin Web Terminal (naquuuu-term)
- **Date**: 2026-09-28
- **Status**: Accepted (authored and committed; deployment pending owner action)
- **Context**: The owner asked for control of the relay VPS from the phone, outside WhatsApp, because the relay bot was down. Two facts made this urgent rather than cosmetic: (1) the WhatsApp front door was unavailable, and (2) `internal-docs/relay/VPS_RELAY_RUNBOOK.md` documents a "kill switch from the phone: tailnet SSH" while `internal-docs/HOSTS.md` Section 7 has phone SSH deferred (ADR-020), so the documented recovery path was not actually reachable from a phone. A second, separate gap: the owner wanted to see the workspace layout, `PATH`, and host state from the phone, which no existing surface provided. Options weighed: `opencode web` (official but unverified at phone width), third-party mobile clients (OpenClient for iOS, OpenCode Mobile for Android - both exist and speak the same HTTP+SSE API, but they place third-party code in front of a surface that can execute shell), and a custom thin client. The owner chose the custom client.
- **Decision**:
  1. **PTY over WebSocket, not the opencode HTTP API, for the terminal.** One mechanism spawns a real login shell in the clone, so `opencode`, Antigravity CLI (`agy`), `git`, `systemctl`, and `python` all work unchanged. An API client would only ever speak opencode. The HTTP API is still used, but read-only, by the visualiser.
  2. **A shared headless `opencode serve` is a hard prerequisite for the visualiser.** A TUI running inside a PTY owns a server on a random port, so nothing outside that process can observe its session tree. The deployment is therefore `opencode serve --hostname 127.0.0.1 --port 4096` plus `opencode attach http://127.0.0.1:4096` in the terminal. This also removes opencode cold start from relay turns (RELAY_PLAN Section 1).
  3. **The server brokers the opencode credential.** The browser never holds `OPENCODE_SERVER_PASSWORD`; it receives a curated snapshot over a separate read-only `/ws/viz` channel that cannot spawn a shell or drive the agent.
  4. **Auth is a Tailscale whois tag check requiring `tag:phone`, resolved from the caller's tailnet address.** Three traps had to be avoided together, and the first draft of this ADR got one of them wrong:
     - Tailscale Serve identity headers are **not populated for tagged devices**, and the phone carries `tag:personal,tag:phone` (TAILSCALE_ACL.md), so `Tailscale-User-Login` is empty and the documented passwordless path does not apply.
     - **`req.socket.remoteAddress` is `127.0.0.1` behind Serve**, because the proxy connects from loopback. A whois on the socket address therefore identifies nobody and denies every legitimate request. The caller address must come from `X-Forwarded-For` when the peer is loopback.
     - **Proxy headers must not be trusted on their own.** Any local process can set `X-Forwarded-For` itself; the openclaw advisory (issue #13153) is exactly this class of bug. The header is acceptable only because Serve SETS rather than appends it and the app binds loopback, and it is then independently verified.
     The settled sequence: take the socket address on a direct tailnet connection, else the first `X-Forwarded-For` entry; **reject anything outside `100.64.0.0/10` and `fd7a:115c:a1e0::/48`** (which eliminates forged loopback and LAN values before tailscaled is consulted, and rejects malformed input rather than normalising it); whois that address; require `tag:phone`. Consequence: no password, key, or stored secret on the phone, and untagged work machines denied by default. Tailscale app capabilities (`grants[].app` with `serve --accept-app-caps=`) are a documented alternative that also covers tagged devices; not required, because it needs more policy machinery.
  5. **Fail closed.** An unreachable LocalAPI, an absent address, a non-tailnet address, or a node without the required tag are all DENY, never an allow. The app binds `127.0.0.1` only, which is what makes the `X-Forwarded-For` path safe: only the local proxy can set that header. A bearer token exists solely for loopback development and is not set by default. The unit tests cover forged loopback and LAN header values specifically.
  6. **Tailnet only; never Funnel.** Exposure is `tailscale serve --bg`, giving a real `*.ts.net` certificate with no public port. Funnel is explicitly rejected: it would publish a shell-capable host that holds relay authority and a repo-scoped deploy key.
  7. **No synthetic telemetry.** Sprite state, walk speed, sparks, and the cat's "nyaa~" derive from real opencode status transitions; a still server renders a still world. `cost`, `tokens`, `messages`, and `tools` are reported by opencode. **Context occupancy is v2-only and prints `n/a` on opencode 1.x** rather than an estimate; the app probes for the endpoint at startup and labels every metric with its source.
  8. **Secret exclusion happens during traversal, not after filtering**, so no future caller can widen it. Covers `.env*`, `*.pem`, `*.key`, `id_rsa*`, `id_ed25519*`, `*session*`, `.hermes`, `credentials`, `secrets`, per AGENTS.md Model-Input Boundary. Locked by `test/auth.test.js`.
  9. **Free and self-contained.** MIT/Apache only, xterm vendored locally with no runtime CDN calls, 24 files, ~406 KB committed. The only marginal cost is model tokens, already decided in ADR-015 and ADR-028.
  10. **Aesthetic**: palette ported from the blog `data-mode="culture"` tokens (espresso-maroon, terracotta crimson), with the blog's three-colour typographic cap honoured so state is encoded by weight, opacity, and motion rather than new hues. The cast is warm shibuya-kei rather than neon, consistent with the owner's documented 1970s-inflected tailoring and city-pop rotation.
- **Consequences**:
  - The owner regains out-of-band control of the relay host, which closes the ADR-020 gap where the documented phone kill switch was unreachable.
  - The visualiser reflects real orchestration because opencode models subagents as child sessions (`sessions.create({ parentID, subagent: true })`) and `task_id` values are session IDs. The hierarchy, per-agent capabilities, todos, and diffs are server state, not inference.
  - The relay host gains two long-running user services (`naquuuu-term.service`, `opencode-serve.service`) on a 2 GB box. Session count is capped (`NQ_MAX_SESSIONS`, default 4) and idle PTYs are reaped.
  - **Open**: deployment is owner-run. The tailnet ACL needs one new grant, `tag:phone` to `tag:personal:443`, or the phone is denied. `internal-docs/TAILSCALE_ACL.md` must be updated in the same change.
  - **Open**: the relay host already keeps a warm opencode server on 4096 for the WhatsApp relay. Two units cannot own one port, so the installer probes `/global/health` and reuses the existing server rather than creating a second unit. If that existing server runs behind `OPENCODE_SERVER_PASSWORD`, the same value must be set for `naquuuu-term` or the agents tab stays offline.
  - **Open**: a 2 GB RAM host is the M1 minimum. The relay now runs Hermes, a warm opencode server, and this app. If they contend, the 4 GB upgrade deferred in the VPS runbook becomes the fix.
  - **Open**: `scripts/host_check.py` has no `naquuuu-term` or port 7777 check, so a dead terminal service would not surface in readiness.
  - Not pushed to any remote yet; the repository is local-only pending the owner's remote decision.

---

## ADR-031: WhatsApp Group Presence (Per-Group Free-Response, Owner-Only Execution)
- **Date**: 2026-09-27
- **Status**: Accepted (authored; owner rollout pending on the relay host). Supersedes the earlier "observe + wake word" draft of this ADR, which was built on an unverified feature (see Context).
- **Context**: The owner asked the WhatsApp bot to participate in the group chat, showing initiative and talking smart, with two explicit requirements: other people must be able to chat with the bot, but **only the owner's chat may provoke tool execution or skill installation**, and the owner must later be able to whitelist additional groups from WhatsApp. The first draft of this ADR assumed an "observe + backfill" awareness feature; a live probe of the relay host proved that feature is **Telegram-only on the installed Hermes v0.21.4** and that free-response is the only workable proactivity lever for WhatsApp. A speaker therefore reaches the agent but is not an operator, and the person allowlist is a speaking filter, not an execution gate.
- **Decision**:
  0. **Supersession**: this ADR narrows two earlier consequences that are now too broad — ADR-024 §Consequences ("any allowlisted account can trigger `opencode run` with full autonomy") and ADR-030 §Consequences ("Every added person can trigger `opencode run` with full autonomy"). Under this ADR a listed person may **speak** but not **act**; execution is owner-only via `wa_owner_gate.py`. The earlier statements remain the historical record for the pre-free-response posture.
  1. **Speaking — per-group free-response**: `WHATSAPP_FREE_RESPONSE_CHATS` lists chats whose members reach the agent with no @mention (the group path bypasses the per-sender allowlist for those chats). It is applied per already-allowlisted group via `scripts/wa_free_response.py` (idempotent, timestamped backup, counts only, never prints a chat id). A newly added group is **mention-only** until the owner promotes it — admission (`scripts/wa_group_allow.py`) and promotion (`scripts/wa_free_response.py`) are separate owner-run commands. `WHATSAPP_ALLOW_ALL_USERS` / `open` stay refused (ADR-024).
  2. **Acting — owner-only, enforced by a hard gate**: `scripts/wa_owner_gate.py` is the sole execution gate. It ALLOWs only a sender in `NAQUUUU_WA_OWNER_IDS` (host env, digits only, never in the repo) and DENYs otherwise, failing closed (unset/unreadable/wildcard owner list denies). The relay skill runs it before `opencode run`, before any tool, and before any skill install or change; on DENY the assistant replies conversationally and executes nothing. Guests can always chat; only the owner can provoke tool execution. This is what closes the ADR-016 residual risk that free-response would otherwise reopen.
  3. **Owner-only chat command — group admission**: the single chat command is "add this group" (owner-only, refused for anyone else via the same owner gate), running `scripts/wa_group_allow.py --add-latest`, which takes the JID from the gateway log so an id is never typed, printed, or passed through chat. There is no chat command to install a tool, edit config, or admit a person (ADR-030).
  4. **Silence**: when nothing is worth saying, the assistant emits `NO_REPLY` (supported by the gateway) instead of a message; replies stay 1-3 sentences in the owner's language/register and never print numbers, ids, or JIDs (ADR-027 / ADR-028).
  5. **No thread awareness**: the relay is **stateless per turn** on v0.21.4 — each turn sees only the triggering message. No observation/`observe_*`/`history_backfill` keys are written (they do not exist for WhatsApp on this version). The dead `wa_group_proactive.py` helper that applied them is removed.
  6. **Persona**: `internal-docs/relay/WHATSAPP_SOUL.md` encodes the above (free-response vs mention-only addressing, owner-gate-before-execute, `NO_REPLY` default, group-add command), mirrored to `~/.hermes/SOUL.md` (ADR-027 mirror rule). Model stays the `opencode.jsonc` default `opencode-go/deepseek-v4.1-flash` (`small_model` `opencode-go/deepseek-v4-flash`).
- **Consequences**:
  - The owner's two requirements are met: anyone in a promoted group can chat; only the owner can execute. The execution boundary is one fail-closed script, not prose alone.
  - Proactivity is per group and deliberate; adding groups does not widen execution, and promotion is never automatic.
  - The relay is stateless per turn: it cannot reference earlier unmentioned chatter, and no turn may imply it read the room. This is a real limit of the current Hermes version, not a design choice.
  - Rollout is owner-run on the relay host: promote groups, set `NAQUUUU_WA_OWNER_IDS` (host-side), mirror the SOUL, restart; steps and verification in `internal-docs/relay/VPS_RELAY_RUNBOOK.md`.

---

## ADR-033: Knowledge Read Contract (Stable IDs, Tiered Index, Freshness Gate)
- **Date**: 2026-09-28
- **Status**: Accepted. The compaction pass named in item 4 is deferred; the AGENTS.md Section 7 dedup named in the Consequences is deferred.
- **Numbering note**: authored as ADR-032 and renumbered to ADR-033 on 2026-09-28 after a collision - a concurrent session committed its own ADR-032 ("Phone-Driven VPS Access via a Thin Web Terminal") in the same working tree. The earlier-numbered, earlier-positioned entry keeps 032; this one moves. The digest stamps in `STATUS.md` and `LESSONS.md` were bumped to match. Cause: two writers on `DECISION_LOG.md` with no reservation mechanism for ADR numbers. Until a reservation mechanism exists, take the next free number by reading the file immediately before appending, not from memory.
- **Context**: The knowledge layer was not failing on volume, it was failing on wiring. Measured 2026-09-28: `DECISION_LOG.md` held 31 ADRs in 63,887 chars, growing at roughly 2.6 ADRs/day since ADR-001 on 2026-09-15, which extrapolates past 500K chars in 90 days. But grep over that corpus was always sub-millisecond, so retrieval speed was never the defect. The real defects were behavioural. First, `LESSONS.md` was referenced by nothing: a grep for `LESSONS` across `AGENTS.md`, `opencode.jsonc`, all seven `.opencode/agent/*.md`, and both `.agents/agents/*.md` mirrors returned zero hits, so the "Self-Reinforcing Memory" section had a dead file and lessons reached no model on any path except one relay skill. Second, lessons were a bare numbered list, so a lesson could not be found by reference. Third, `STATUS.md` self-declared `Updated: 2026-09-25` while its own mtime was 2026-09-27: the declared date was already wrong and nothing detected it. At 10x corpus size the failure mode is a silent wrong answer from a stale digest, not a slow one.
- **Decision**:
  1. **Stable IDs.** Lessons take `L-nn`, permanent, assigned in order, never renumbered or reused, cited by ID and never by ordinal. `ADR-nnn` continues unchanged. Every cross-reference is by ID, so `rg 'L-14'` finds every mention of that lesson anywhere in the workspace. The one known ordinal citation (ADR-030 naming "lesson 13") resolves to `L-13` because order was preserved.
  2. **Tiered read contract** in `internal-docs/INDEX.md`, hard cap 45 lines, self-describing that if it grows the routing table is wrong rather than the cap. Tier 0 is the router. Tier 1 is the two bounded digests, `STATUS.md` and the hot `LESSONS.md` slice, read only to the hot slice. Tier 2 is the single on-demand source that Tier 1 points to, reached by path and never enumerated. A question-class to file routing table covers state, rationale, hosts, relay operations, dispatch, network, group policy, taste, research, and undecided questions.
  3. **Freshness stamp.** Each digest carries one HTML comment line immediately under its H1: `<!-- verified-against: ADR-nnn -->`, bumped in the same commit that adds the ADR it reflects. `scripts/sync_all_repos.py` gains `--check-freshness`, implied by `--strict`: it reads the max `## ADR-nnn:` heading in `DECISION_LOG.md` and compares numerically, never lexically, so ADR-099 correctly reports stale against ADR-100. STALE, MISSING stamp, missing file, misplaced stamp, and unreadable log are distinct named conditions; the checker never crashes and never passes silently. Non-strict warns and exits 0; `--strict` exits 1. `INDEX.md` carries no stamp and is excluded, being a router rather than a digest.
  4. **Bounded hot slice.** Compaction triggers at roughly 5,000 chars, rolling the oldest entries into `internal-docs/lessons/YYYY-MM.md`. The first pass is NOT performed and is explicitly out of scope here: the file was already past the threshold at authoring, and moving entries would change which `L-nn` resolves in the hot slice, colliding with the never-renumber rule and with ADR-030's ordinal citation. Tracked as an open question in `LESSONS.md`; `internal-docs/lessons/` does not exist yet.
  5. **Enforcement over convention.** The read contract is wired into all seven `.opencode/agent/*.md` personas and both `.agents/agents/*.md` mirrors as an additive "Before you act" block. This is the actual fix for the dead-file finding: previously nothing instructed any agent to read `LESSONS.md`, so the process had no enforcement point and could not survive a change of agent, host, or model. The skeptic persona additionally must challenge any claim lacking a file path and line number. Frontmatter, permissions, voice, and autonomy statements were left byte-identical.
  6. **No retrieval service.** No vector database, embedding index, or RAG. Rationale, owner-confirmed 2026-09-28: ripgrep over this corpus is sub-millisecond, and a retrieval service would add latency, a dependency, and a third staleness surface to solve a problem that does not exist. This decision is written to survive corpus growth, not just today's size.
  7. **The auditor audits the hub.** `sync_all_repos.py` now includes the workspace root itself, labelled `naquuuu (hub)`. It previously enumerated only direct children plus `projects/*`, so the hub repo was never reported and a real unpushed commit was invisible to the gate that exists to catch exactly that.
- **Consequences**:
  - Read cost is bounded by the caps, not by corpus size. The 10x failure mode is now a named, visible STALE condition rather than a confidently wrong answer.
  - `AGENTS.md` Section 7 restated several lessons that also lived in `LESSONS.md`, which is two write sites for one fact and guarantees drift; item 9 is now cited by `L-ID`. The rest of the Section 7 dedup is DEFERRED and is not claimed as a win: measurement showed most of Section 7 is unique invariant text rather than duplicated lessons, so the available prefill reduction is small next to the risk of dropping an invariant out of always-injected context. Recorded as an open question.
  - The 2026-09-28 relay outage (`L-17`) is deliberately not an ADR. It is an operational incident with a recovery procedure, not an architecture decision, and forcing it into the log would misrepresent its status. Its recovery procedure is not yet written into a runbook; that gap is tracked as `L-17` open question 2.
  - Compaction is owed before the next ten lessons land, and the archive directory must be created first.

## ADR-034: Authenticated Chat Access Commands and Bounded Relay Turns
- **Date**: 2026-09-28
- **Status**: Accepted by the owner's ASTRA_ONESHOT authorization. Command implementation is subject to host integration and live matrix verification; acceptance is not evidence of rollout completion.
- **Decision**: Supersede ADR-030's blanket ban on chat admission commands with exactly `/allow-group`, `/allow-person`, `/list`, and `/remove`. Authenticate the bridge-sourced sender before parsing. Person admission uses authenticated reply context, never digits typed into chat. Keep timestamped env backups, owner access protection, counts-only listing, and fail-closed guest behavior. Pre-send text must resolve identifiers to locally cached display names or refuse delivery. Proactive delivery is restricted to explicitly promoted and admitted groups; no test target was supplied in the brief.
- **Reliability**: A generic status is permitted after sixty seconds despite ADR-027's normal quiet display. Cap transient primary retries at two with exponential backoff and bound the complete vision stage to forty-five seconds; retain the existing provider fallback ladder and model pins. The authenticated local opencode wrapper may reuse only trusted host context, never a global last session.
- **Evidence boundary**: Synthetic command tests, retry tests and live service settings do not prove phone delivery, accurate photo interpretation, proactive mentions, or worker activation. These remain separate checks in `ASTRA_EXECUTION_REPORT.md`.
- **Knowledge maintenance**: The owner authorized the first compaction: L-01 through L-19 moved to `lessons/2026-09.md`, preserving IDs and the historical L-13 reference. Add `/agent-viz` to session-end checks, using `--serve` without `--out` for private viewing and publishing only sanitized explicit exports.

## ADR-035: Per-Turn Ephemeral Owner Verdict (V2) and Host-Only Admin Actions
- **Date**: 2026-10-01
- **Status**: Accepted. Verdict V2 is deployed on the relay host and was verified live on 2026-10-01. The host-only guard (item 4) is authored and unit-tested on branch `claude/hermes-whatsapp-owner-auth-modywq`; its host rollout (`git pull`, installer re-run and `--check`, SOUL mirror, restart only with `session_turn_leases` = 0; runbook Step 6.5) is owner-run and still pending. Live-test results below are owner-session evidence from the relay host on 2026-10-01; no artifact for them is stored in this repo.
- **Context**: After the bridge-side owner check landed (ADR-031, ADR-034), the owner's own WhatsApp requests were still refused with "cannot verify owner authorization". A one-shot temporary boolean probe, since removed, showed that the strict bridge flag reached `TurnRunner` as `True` end to end. The model (`gpt-6-luna`) was ignoring it: the V1 verdict note was weakly worded, and the chat history was full of earlier refusals that the model copied. Separately, on 2026-10-01 the bot ran an `.env`-editing, gateway-restarting admission script from chat for the verified owner, contrary to the SOUL rule that group admission is host-only. At 05:02 the same day `approvals.destructive_slash_confirm` was set to `false` from chat, with no backup.
- **Decision**:
  1. **Per-turn ephemeral owner verdict.** The bridge computes a strict owner boolean. The adapter sets `source._naquuuu_owner_authorized`. `TurnRunner._combined_ephemeral_prompt()` appends an API-only note, "Trusted host verdict for this WhatsApp turn: AUTHORIZED / NOT_AUTHORIZED". The note is never persisted to session prompt or history and never logged. The executor gate (`wa_turn_auth.must_deny_tool`) stays authoritative; the note only stops a correct owner request being refused.
  2. **V2 wording** (marker `NAQUUUU_WA_OWNER_VERDICT_EPHEMERAL_V2`, `scripts/install_wa_owner_auth.py`, with an in-place V1 to V2 upgrade). It states that verification is complete and is not the model's job, that earlier refusals are obsolete, and that a requested action means calling the relevant tool now. Verified live on `gpt-6.1-sol`, `opencode-go/deepseek-v4.1-flash` and `gpt-6-luna`, including luna in a fresh `/new` session: a tool call ran, there were 0 gate denials, and the verdict was persisted nowhere.
  3. **Model choice is per chat** via `/model`. Owner authorization does not depend on the model; the host gate enforces the same boundary under every model.
  4. **Host-only admin actions are never run from WhatsApp, owner included.** `wa_turn_auth.must_deny_host_only()` runs in the executor patch (marker `NAQUUUU_WA_HOST_ONLY_GUARD_V1`) after the owner check and before relay hooks, middleware and dispatch. On any bound WhatsApp turn it blocks a tool call whose arguments reference any of the following:
     - the admission and policy scripts: `whatsapp_group_fix.py`, `wa_free_response.py`, `wa_group_allow.py`, `wa_owner_gate.py`, `install_wa_owner_auth.py`, `install_wa_chat_policy.py`;
     - any `.env` file (not `.env.example`/`.sample`/`.template`, not JS `process.env`);
     - Hermes home paths written as `.hermes/`, `$HERMES_HOME` or `%LOCALAPPDATA%\hermes`, except the media caches directly under it (`image_cache`, `audio_cache`, `document_cache`, `video_cache`, `cache`) so owner photo turns keep working;
     - the other host-admin scripts (`wa_chat_policy.py`, `install_relay_guards.py`, `sync_wa_owner_auth_prompt.py`, `refresh_wa_prompt_snapshot.py`, `enable_gates.sh`, `swap_action_gateway_session.ps1`) and environment dumps (`printenv`, `/proc/*/environ`);
     - Hermes service or config control: `hermes [flags] gateway start|stop|restart|...|--replace` (including `hermes_cli` module forms), `hermes config set|edit`, `systemctl`/`service ... hermes`, `pkill`/`killall`/`pgrep ... hermes`.
     A missing guard function fails closed: it blocks the tool rather than skipping the gate. The SOUL, the relay skill and the runbook state the same rule. Chat-side group admission remains the host chat policy (`/allow-group`, ADR-034), which runs before the model sees the message.
  5. **New groups are admitted by JID from the host shell only** (`scripts/whatsapp_group_fix.py --group <jid>`), with `WHATSAPP_GROUP_POLICY=allowlist` and `REQUIRE_MENTION=true`. Admitting "any group" would require allow-all users and stays refused (ADR-024).
- **Consequences**:
  - **Lesson L-22**: before blaming the model for ignoring a host signal, prove the signal arrives with a temporary one-shot boolean probe, then remove the probe. The probe here moved the fix from plumbing to prompt wording in one step.
  - The host-only guard is a tripwire, not a sandbox. It matches the text of Hermes tool arguments only: an obfuscated command can evade it, and it cannot see what a child `opencode run` does once started, so the SOUL and relay-skill rule still binds the agent. It also blocks innocent prompts that mention a listed name (for example an `opencode run` prompt that says ".env"). The owner's host shell remains the only admin path, so a false block costs one host command.
  - Accepted gaps of the same class: a relative path after `cd` into an exempt cache (`cd ~/.hermes/cache; cat ../config.yaml`) and URL-encoded traversal (`%2e%2e`) are not matched. Every gap in the pattern is length-bounded so a large argument cannot stall the executor (a 200 KB regression test enforces this).
  - The media-cache exemption assumes Hermes stores inbound attachments under those directory names. That assumption is unverified in this repo: the first owner photo turn after rollout is the check, and a block there means adjusting the exemption.
  - Adding the guard changes the installed executor patch, so `install_wa_owner_auth.py --check` fails on the relay host until the installer is re-run after `git pull`. The installer migrates the V2 executor block in place.
  - Hermes slash commands such as `/config` do not pass through the tool executor, so the guard cannot prevent a repeat of the `destructive_slash_confirm` change. The owner chose to restore it to `true` (host step). Until it is restored, destructive slash commands run without confirmation.
  - Open on the host: re-point or repair the broken PATH `hermes` launcher, which lacks `dotenv`, so scripts prefer `~/.hermes/hermes-agent/venv/bin/hermes`; and resolve the VPS-side drift of `scripts/wa_chat_policy.py`, since the local copy matches origin.
