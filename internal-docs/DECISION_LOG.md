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
