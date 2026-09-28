# ASTRA ONE-SHOT — entire workspace, engineering + creative, end to end

Owner-prepared 2026-09-28. Astra: read this whole file, fill nothing in (Tier 1 was
filled before handoff), then execute workstreams in order. Commit and push as you go —
do not stop for approval. Your only stop condition is a safety-rail violation, in
which case you take the reversible path and record the rest as a blocker.

## Autonomy grant (explicit, from the owner)

You may, without asking: read/write anything in the workspace repos; run any host
command (systemctl, hermes via full venv path, git, npm, python, uv); commit AND push
to the hub and child repos; modify ~/.hermes/.env, systemd units, Hermes config;
install packages (apt/pip/npm); restart services; manage the WhatsApp session (restart
bridge freely; re-pair ONLY if you prove the session dead, since that spends a rate
window); run scripts/authorize_worker.sh on the worker (M2 trust APPROVED 2026-09-28).
Commit messages follow repo style: `type(scope): subject`.

## Safety rails (the only things that override autonomy)

1. Never delete backup files: .env.bak-*, pre-update-*.zip, *.bak, adapter.py.bak.
2. Snapshot before destructive ops: timestamped backup first (existing helper pattern).
3. Never `hermes update`, `hermes gateway install`, or bare `hermes` on the relay host.
   Full path `~/.hermes/hermes-agent/venv/bin/hermes` always. Code stays at ecacf3d0c9.
4. One gateway per host. Before starting: `ss -tln | grep 3000`, `pgrep -af bridge`,
   `systemctl --user is-active`. Kill strays first.
5. Tier 1 values below live in host env/files ONLY. Never in commit messages, docs,
   handoffs, or chat. Grep counts, redact before reading.
6. If an op is truly irreversible (drop a database, delete a repo), do everything
   reversible around it, then record it as a blocker with the exact command ready.
   That is the ONLY case you stop short.

## TIER 1 — filled by owner (Astra: use these, never print them)

```
OWNER_DIGITS=
GUEST_DIGITS=
BOT_DIGITS=
WHATSAPP_GROUP_IDS=
VPS_ACCESS=
HOMESERVER_ACCESS=
NOUS_PORTAL_KEY_REF=
GEMINI_KEYS_REF=
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
DO_API_TOKEN=
GITHUB_PUSH_AUTH=
```

Blank DO_API_TOKEN = skip all DO work this run, no questions asked. Blank GITHUB_PUSH_AUTH
= use whatever the host already has. Digits are international format, no `+`, no spaces.

## Environment map (verified 2026-09-28)

- Laptop (Windows): C:\personal\naquuuu — hub repo naquuuu/naquuuu-personal-works.
  Hermes autostart DISARMED, no bridge, port 3000 free. opencode 1.18.32.
- VPS VM-0-8-ubuntu (Ubuntu 24.04, 2 vCPU/2 GB): ~/naquuuu — LIVE relay host.
  Hermes v0.21.4 at ecacf3d0c9 (detached HEAD). venv rebuilt (yaml OK, aiohttp 3.14.3).
  Service hermes-gateway.service + drop-ins: restart.conf (on-failure/30s/5-in-5min)
  and override.conf (ExecStart=venv python ONLY — no PATH line, Node is inherited).
  Bridge :3000, session paired at ~/.hermes/whatsapp/session/.
  Hotfixes that die on update: adapter.py range(90) + HERMES_GATEWAY_PLATFORM_CONNECT_TIMEOUT.
- Home server mipad-linux: M2 worker candidate. Needs `opencode auth login` + reboot —
  do it over HOMESERVER_ACCESS if reachable, else record the exact command.
- Blog: blog/ → naquuuu/naquuuu.github.io. STYLE_BIBLE.md governs voice.
- Remotes: GitHub naquuuu/*. Hub canonical. No force-push (pre-push hook refuses it).

## Current verified state (do not re-derive)

Relay LIVE end to end 2026-09-28 evening (L-21): session, bridge, gateway, owner gate,
opencode run — all proven by an owner message round-trip. Chain behind it: L-17 outage
(two hosts + Restart=always), L-18 (interrupted update broke the env), L-20 (missing
aiohttp posing as timeouts, correcting L-19). Baselines: cold opencode run 15,177 ms,
CLI startup 2,097 ms (L-09). Max IDs: ADR-033, L-21 — check before numbering anything.
M2 (ADR-029): APPROVED 2026-09-28, activating — this brief includes the full sequence.

## Live incident (2026-09-28, 21:16 WIB) — 5-minute typing hang, diagnosed

- Symptom: an owner message held the typing indicator 5+ minutes with no reply.
- VPS state at the time: `opencode serve` running (PID 327235, 127.0.0.1:4096, verified
  in the same check); gateway `active`; journal shows `vision_analyze` failing with
  `Gemini HTTP 503 (UNAVAILABLE): high demand` after 5.28s, then a self-improvement
  review 26s later.
- Reading: the turn involved an image (or a vision call); the provider 503'd; the agent
  either retried without backoff or stalled with the turn open. A single provider 503
  must never hold a turn open — cap retries, back off, fall back, and send the 60s
  interim status per Workstream 0.
- Fix first if you find it: a retry loop with no backoff on 503/429. Max 2 retries,
  exponential backoff, then the fallback chain (L-10/L-11), then a one-line status to
  chat. The 503 itself is transient provider demand; the hang is the missing guard.

## Hard rules (workspace law)

- Cite lessons L-nn, decisions ADR-nnn. INDEX.md first; grep DECISION_LOG by ADR-nnn,
  never read it whole.
- Routing: [BLOG]=blog/, [PROJECT]=projects/<slug>/, [HUB]=repo root. Never mix them.
- Four-block handoff per workstream (Result / Files Changed / Evidence / Blockers).
  Real command output only. No invented numbers — the workspace forbids synthetic
  claims, and a full-day outage proved why: when a health check reports a timeout,
  first prove the check itself can run.

## 0 — Personality: human, curator-led, fast

Voice contracts are law: TASTE_PROFILE.md, STYLE_BIBLE.md, WHATSAPP_SOUL.md. Curator
owns taste; execution stays inside it. WhatsApp: 1-3 sentences, owner register, ID/EN
as curator directs, NO_REPLY when silence is right, never robotic, never slow.
naquuuubot: decisive chief of staff, numbered steps, max five per list. Blind-test five
replies against STYLE_BIBLE — all pass, with no slower model and no extra agent turn.
Interim-reply rule (mandatory, not advisory): any turn crossing 60s sends a one-line
status instead of holding typing — a 5-minute silent typing indicator is a defect.

## 1 — Reply speed (headline metric)

Current setup only: no model change, no paid service. Adopt the existing
`opencode serve` on the relay host as a systemd user unit + `opencode run --attach`;
it is already running at 127.0.0.1:4096 (PID 327235, verified 21:16 WIB) — attach the
relay skill to it, do NOT start a second one;
session reuse for follow-ups; verify the STATUS.md fast path short-circuits; trim the
relay prompt. Measure before/after on a one-word task, record in L-09 with date and
command, commit.

## 2 — Full latency audit (BE/system, free only)

Gates, autosync cadence, repo I/O, script startup, doc-read costs. Touch nothing paid,
no model pins, leave .opencode/node_modules+plugin/ alone (live). No vector DB, no
embeddings, no RAG — ripgrep is sub-millisecond. Every finding: measured-ms
before/after, or "measured, not worth it" with the number.

## 3 — Proactive mentions, names never IDs (two live bugs)

Bug 1: the bot claimed it cannot mention or greet unprompted. Bug 2: it printed a raw
numeric @ID instead of a name (L-02/L-14 violated in a live reply). ADR-031 permits
speaking in free-response groups: extend to INITIATING (@mention by name, greet first)
in promoted groups; mention gate stays ON elsewhere. Build a JID→display-name resolver
(bridge logs / gateway state, cached locally) plus a pre-send scrubber: any raw ID
about to go out becomes the resolved name, or the send is refused. Done-when:
unprompted correct @mention in a test group; zero raw IDs across the full
owner/guest/mention-only matrix.

## 4 — WA-commandable whitelists, owner-only (deliberate ADR-030 reversal)

People by NAME or REPLY-CONTEXT only — never typed digits, so Tier 1 stays out of chat.
Gate everything through wa_owner_gate.py BEFORE parsing; guests refused with no state
change and no leak. Four commands only: `/allow-group` (current group), `/allow-person`
(replied-to sender), `/list` (counts only), `/remove` (current group or replied-to
sender). Timestamped .env backup per mutation (existing pattern). Seed the current
owner+guests from TIER 1 above, then prove a full chat-only add/remove cycle on a test
entry. Record the new ADR (check the next free number — this file has collided before).
Done-when: add/remove works entirely from chat; guest attempts change nothing; zero
digits in any chat at any point.

## 5 — Visualizer live on the blog

Render the recovery session via /agent-viz; confirm zero credential patterns and zero
gate violations. Ship as a performance page on naquuuu.github.io (session maps +
Workstream-1 numbers + gate status) passing full blog QA: fluid to 320px, zero inline
widths, anchors resolve, 72ch column, semantic HTML, meta, alt text. Keep
`--serve`-without-`--out` for clean viewing. Add /agent-viz to the session-end
checklist. Done-when: page live, real session rendered, QA green.

## 6 — Blog revamp, full

Performance, structure, responsive, accessible, SEO. Same QA bar as Workstream 5 plus
render-blocking and responsive-image basics. STYLE_BIBLE.md governs voice — restructure
and accelerate, never rewrite prose. Run verify_blog_qa.py + sanitization before
staging. Done-when: QA green, mobile-width clean, every existing page resolves.

## 7 — M2 activation (APPROVED — execute, don't ask)

ADR-029 is Approved; activating. In order, relay host then worker, both via Tier 1 access:
1. Relay: generate the dedicated key if absent —
   `ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_worker -N ""`
2. Read the public half: `cat ~/.ssh/id_ed25519_worker.pub` (public key only)
3. Worker: `bash ~/naquuuu/scripts/authorize_worker.sh "<pubkey>"` — AUTHORIZED
4. Verify: `tailscale ping mipad-linux`, then
   `ssh -i ~/.ssh/id_ed25519_worker -o IdentitiesOnly=yes ubuntu@mipad-linux true`
5. Relay: `bash scripts/install_dispatch_drain.sh`; confirm the drain timer is live
6. Switch the relay skill to dispatch per M2_DISPATCH_RUNBOOK.md; verify with a light
   job then a heavy one; confirm output under done/ and job_status.sh summarizes
7. Home-server login + reboot via HOMESERVER_ACCESS if reachable, else exact commands
Rules: dedicated key only, never a reused deploy key. Drain timer BEFORE the skill
switch — otherwise offline jobs queue forever. Light work stays local. Done-when:
a heavy test job runs on the worker, archives under done/, and the queue is proven
durable with the worker offline at least once.

## 8 — Hygiene + Spotify (last)

LESSONS compaction (past threshold; roll oldest to internal-docs/lessons/YYYY-MM.md,
never renumber — ADR-030 cites L-13); protect the adapter.py range(90) patch (document
the re-apply or push upstream — no update to do it); random-stuff's 1 unpushed commit
(inspect, push or drop); naquuuu-term remote steps prepared, nothing created;
deliberate-update plan as a document only. Spotify: complete scripts/spotify_taste.py
using SPOTIFY_CLIENT_ID/SECRET above (perform the one-time app setup yourself), cache
the snapshot, split fetch/status so status costs zero network. Document the owner
setup steps in one place. Done-when: fetch→status clean on cache, zero redundant calls.

## 9 — Image: free read + generate (experimental)

Read: WhatsApp images already reach the bridge per RELAY_PLAN. Enable
`auxiliary.vision` with a free multimodal model; confirm the skill forwards image
attachments into `opencode run` turns. Done-when: a photo with both text and an object
is described correctly on both. Known failure (21:16 WIB): `vision_analyze` returned
Gemini HTTP 503 after 5.28s and the turn hung — so the vision path MUST ship with a
retry cap (max 2, exponential backoff) and the L-10/L-11 fallback chain, or provider
demand spikes will hang turns exactly like the live incident above. If no free vision
model on the current plan can do it, name the ones tested and stop — do not upgrade
anything.
Generate: L-12/ADR-028 record "no viable free tier" — test whether that's still true,
with the paid Gemini chain in scripts/gen_image.py as AUTOMATIC fallback. Start from
RELAY_PLAN's unadopted Pollinations option; one alternative if it fails. No key, no
cost. Log which path served every generation. Deliver via MEDIA: as a native WhatsApp
image; natural trigger in ID and EN. Done-when: 5 consecutive generations return real
images with zero fallback and zero failure. Anything less: keep the fallback, record
the honest hit rate, do NOT claim a free tier exists. Adopted → new ADR or ADR-028
amendment (check numbers). Failed → one-line failure record, paid chain stays.

## Out of scope entirely

Phone rotation. Tailscale ACL apply. DO console actions (blank DO_API_TOKEN = skip,
no questions). Anything irreversible without a backup (rail 6).

## Freshness

Prepared 2026-09-28 against ADR-033 / L-21. If either has moved when you read this,
re-verify the max IDs before numbering anything new.
