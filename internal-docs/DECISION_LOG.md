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
