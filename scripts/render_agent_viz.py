#!/usr/bin/env python3
"""Agent and subagent session visualizer for the personal engineering hub.

Reads the append-only telemetry written by the opencode plugin at
.opencode/plugin/session-viz.js and renders one self-contained html page
showing the 7-agent roster at work for a single session: who is active,
what the task board holds, and how work was handed off.

Two layers redact credentials. The plugin scrubs them at capture time, but
.session-viz/ is gitignored while internal-docs/agent-viz/ is not, so this
renderer scrubs again on the way out. Every string that reaches the page or
the api payload goes through clean(), which is the single chokepoint for both
the dash rules and the credential rules.

Stdlib only. Python 3.10+. Cross platform. No network calls except the
optional /api/session poll that only runs when --serve is used.

Usage:
  python scripts/render_agent_viz.py [--session <id>] [--out <path.html>]
                                     [--serve] [--port 8765] [--open]

--serve without --out is a viewing action, not a write: the page is held in
memory and nothing is written into the repository. --serve with an explicit
--out writes that file and then serves its directory.
"""

from __future__ import annotations

import argparse
import html as html_lib
import json
import os
import re
import sys
import webbrowser
from dataclasses import asdict, dataclass, field
from datetime import datetime
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import quote, urlparse

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover - only on exotic stdout replacements
    pass

# --------------------------------------------------------------------------
# constants
# --------------------------------------------------------------------------

FALLBACK_ROOT = "C:/personal/naquuuu"
DATA_DIRNAME = ".session-viz"
AGENT_DIRNAME = "agent"
DEFAULT_OUT = "internal-docs/agent-viz/session-map.html"
DEFAULT_PORT = 8765

BULLET = "\u2022"
LABEL_MAX = 34
PERSONA_MAX = 96
SNIPPET_MAX = 58
TIMELINE_CAP = 80

# lane order is the pipeline: orchestrator, creative, build, review, verify.
LANES = ("orchestrator", "creative", "build", "review", "verify")

# used only when the persona files cannot be parsed. the page says so.
FALLBACK_ROSTER = (
    ("naquuuubot", "chief of staff and engineering orchestrator. sole entry point for engineering tasks.", "primary"),
    ("naquuuu-curator", "aesthetic, taste and persona muse. bilingual creative director.", "all"),
    ("naquuuu-builder", "software and prototype builder. implements code, then runs the gates.", "subagent"),
    ("naquuuu-scribe", "content and documentation scribe. drafts articles and notes.", "subagent"),
    ("naquuuu-librarian", "knowledge librarian. read-only retrieval with citations.", "subagent"),
    ("naquuuu-skeptic", "adversarial reviewer. challenges claims and scope.", "subagent"),
    ("naquuuu-verifier", "quality gatekeeper. runs the gate scripts and reports.", "subagent"),
)

# shapes that must never reach the rendered page, from telemetry or from a
# persona file. replaced, never typed. the dash family is banned outright by
# style bible 4.2, and u+2026 is not on the allowed punctuation list in 1.9.
SCRUB_CHARS = {
    "\u2014": ".",
    "\u2013": ",",
    "\u2012": ",",
    "\u2015": ",",
    "\u2212": ",",
    "\u2500": "-",
    "\u00ad": "",
    "\u2026": "...",
}

# --------------------------------------------------------------------------
# credential scrubbing, the second redaction layer
# --------------------------------------------------------------------------
#
# the plugin at .opencode/plugin/session-viz.js is the first layer. this is the
# one that matters, because .session-viz/ is gitignored and the rendered page
# lands in internal-docs/agent-viz/, which is a tracked path. a single layer
# is a single point of failure, so the shapes are matched again here.
#
# the first block is copied rule for rule from the plugin, same order, so the
# two layers cannot drift apart on the shapes they both know about. the second
# block holds the shapes the renderer needs and the plugin does not have.
#
# every pattern is written as fragments or as a class, never as a literal
# specimen, because the hub sanitization linter greps this file for specimens
# including inside comments. keep it that way.
#
# the keep_label flag marks the key/value rule. that one keeps its label so a
# scrubbed string still reads as "token=[redacted]" and the reader keeps the
# context of what was removed.
REDACTED = "[redacted]"

SECRET_PATTERNS: tuple[tuple[re.Pattern[str], bool], ...] = (
    # ---- identical to .opencode/plugin/session-viz.js ----
    (re.compile("AI" + "zaSy[A-Za-z0-9_-]{25,}"), False),
    (re.compile("dop" + "_v1_[A-Za-z0-9_-]{12,}"), False),
    (re.compile(r"bearer\s+[A-Za-z0-9._~+/=-]{12,}", re.IGNORECASE), False),
    (re.compile(r"((?:api[_-]?key|token|secret|password|passwd)\s*[:=]\s*\"?)([A-Za-z0-9._~+/=-]{12,})", re.IGNORECASE), True),
    (re.compile(r"[A-Za-z0-9+/]{40,}={0,2}"), False),
    # ---- renderer only: header values, key material, long opaque runs ----
    (re.compile(r"(authorization\s*[:=]\s*)(?:\"[^\"\n]*\"|'[^'\n]*'|[A-Za-z0-9._~+/=-]{8,})", re.IGNORECASE), True),
    (re.compile("-----BEGIN" + r" [A-Z ]{0,24}PRIVATE KEY-----"), False),
    (re.compile(r"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}(?![A-Za-z0-9_-])"), False),
    # 40 is the plugin threshold and it is deliberate. a session id is 36
    # characters, so the page title survives, while a 40 character unlabelled
    # run in the base64url alphabet is treated as key material.
    (re.compile(r"(?<![A-Za-z0-9+/=_-])[A-Za-z0-9_-]{40,}(?![A-Za-z0-9+/=_-])"), False),
)

# hits are counted so the page can report what its own scrubber removed. the
# count is a diagnostic, not a gate: redaction happens whether or not anyone
# is looking at the number.
REDACTION_HITS = 0
COUNT_REDACTIONS = True


def redact(text: str) -> str:
    """Replace every credential shaped span with the redaction marker."""
    global REDACTION_HITS
    for pattern, keep_label in SECRET_PATTERNS:
        if keep_label:
            text, hits = pattern.subn(lambda match: match.group(1) + REDACTED, text)
        else:
            text, hits = pattern.subn(REDACTED, text)
        if hits and COUNT_REDACTIONS:
            REDACTION_HITS += hits
    return text


def redaction_count() -> int:
    return REDACTION_HITS


def reset_redactions() -> None:
    global REDACTION_HITS, COUNT_REDACTIONS
    REDACTION_HITS = 0
    COUNT_REDACTIONS = True


WRITE_TOOLS = ("edit", "write", "patch", "multiedit", "notebookedit")


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------


def workspace_root() -> Path:
    """Resolve the hub root from the env var, then the documented fallback."""
    raw = os.environ.get("NAQUUUU_WORKSPACE", "").strip()
    return Path(raw) if raw else Path(FALLBACK_ROOT)


def clean(value: Any) -> str:
    """The single chokepoint. every string that leaves telemetry or a persona
    file for the page, the api payload or a cli line passes through here.

    order matters. redaction runs first so that dash replacement cannot split a
    credential into two harmless looking halves before the patterns see it.
    every html interpolation goes through esc(), which is clean() plus html
    escaping, so a field added to the page later cannot skip the scrubber
    without also skipping the escaper.
    """
    text = "" if value is None else str(value)
    text = redact(text)
    for bad, good in SCRUB_CHARS.items():
        text = text.replace(bad, good)
    text = text.replace("&mdash;", "-").replace("&ndash;", "-")
    text = text.replace("&amp;mdash;", "-").replace("&amp;ndash;", "-")
    return " ".join(text.split())


def esc(value: Any) -> str:
    """Escape and lowercase. the style bible is unconditional about case.

    this is the only way body text reaches the document. keep it that way.
    """
    return html_lib.escape(clean(value).lower(), quote=True)


def clip(value: str, limit: int) -> str:
    # three periods, not a horizontal ellipsis. the style bible 1.9 list of
    # allowed punctuation does not include u+2026, and the period is on it.
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 3)].rstrip() + "..."


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def short_time(raw: Any) -> tuple[str, str]:
    """Return (machine datetime, display clock). display carries no dashes."""
    text = clean(raw)
    try:
        stamp = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return ("", text[:8] if text else "--:--:--")
    return (stamp.isoformat(), stamp.strftime("%H:%M:%S"))


# --------------------------------------------------------------------------
# roster
# --------------------------------------------------------------------------


def parse_frontmatter(text: str) -> dict[str, Any]:
    """Minimal frontmatter reader: top level scalars plus indented blocks."""
    if not text.startswith("---"):
        return {}
    lines = text.splitlines()
    fields: dict[str, Any] = {}
    index = 1
    while index < len(lines) and lines[index].strip() != "---":
        line = lines[index]
        if not line.strip() or line.startswith("#"):
            index += 1
            continue
        if not line[:1].isspace() and ":" in line:
            key, _, value = line.partition(":")
            key = key.strip().lower()
            value = value.strip()
            if value:
                fields[key] = value
            else:
                block: list[str] = []
                cursor = index + 1
                while cursor < len(lines) and (not lines[cursor].strip() or lines[cursor][:1].isspace()):
                    if lines[cursor].strip():
                        block.append(lines[cursor].strip())
                    cursor += 1
                fields[key] = " ".join(block) if block else ""
                index = cursor
                continue
        index += 1
    return fields


def lane_for(name: str, description: str) -> str:
    """Assign a role lane so the map reads left to right as a pipeline."""
    who = name.lower()
    says = description.lower()
    if "orchestrat" in who or "orchestrat" in says or "chief of staff" in says:
        return "orchestrator"
    if "curator" in who or any(k in says for k in ("aesthetic", "taste", "creative", "muse")):
        return "creative"
    if "verifier" in who or "gatekeeper" in says or "gate script" in says:
        return "verify"
    if any(k in who for k in ("skeptic", "librarian")) or any(
        k in says for k in ("review", "adversarial", "challenge", "citation", "knowledge")
    ):
        return "review"
    return "build"


@dataclass
class Agent:
    name: str
    description: str
    mode: str
    permission: str
    lane: str
    tasks: int = 0
    tools: int = 0
    files: int = 0
    sent: int = 0
    received: int = 0
    errors: int = 0
    status: str = "idle"
    last_index: int = -1
    last_label: str = ""
    file_paths: list[str] = field(default_factory=list)
    synthetic: bool = False


def load_roster(root: Path) -> tuple[list[Agent], str]:
    """Parse .opencode/agent/*.md so persona edits show up without a code change."""
    agent_dir = root / ".opencode" / AGENT_DIRNAME
    roster: list[Agent] = []
    if agent_dir.is_dir():
        for path in sorted(agent_dir.glob("*.md")):
            try:
                fields = parse_frontmatter(path.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                continue
            name = str(fields.get("name", "")).strip() or path.stem
            description = str(fields.get("description", "")).strip()
            if not description:
                continue
            roster.append(
                Agent(
                    name=name.lower(),
                    description=description,
                    mode=str(fields.get("mode", "")).strip() or "unknown",
                    permission=str(fields.get("permission", "")).strip(),
                    lane=lane_for(name, description),
                )
            )
    if not roster:
        return (
            [
                Agent(name=name, description=description, mode=mode, permission="", lane=lane_for(name, description))
                for name, description, mode in FALLBACK_ROSTER
            ],
            "built-in fallback roster, persona files were not parsed",
        )
    return roster, f"parsed from .opencode/{AGENT_DIRNAME}/*.md"


def agent_index(roster: list[Agent]) -> dict[str, Agent]:
    return {agent.name: agent for agent in roster}


# --------------------------------------------------------------------------
# telemetry
# --------------------------------------------------------------------------


def resolve_session_file(root: Path, session: str | None) -> Path:
    """Pick the named session file, or the most recently modified one."""
    data_dir = root / DATA_DIRNAME
    if not data_dir.is_dir():
        raise FileNotFoundError(f"no telemetry directory at {data_dir}. run an opencode session first.")
    if session:
        candidate = data_dir / f"{session}.jsonl"
        if not candidate.is_file():
            raise FileNotFoundError(f"no telemetry file at {candidate}")
        return candidate
    files = sorted(data_dir.glob("*.jsonl"), key=lambda item: item.stat().st_mtime)
    if not files:
        raise FileNotFoundError(f"no telemetry files in {data_dir}")
    return files[-1]


def load_records(path: Path) -> list[dict[str, Any]]:
    """Read the jsonl stream, skipping any line that is not a json object."""
    records: list[dict[str, Any]] = []
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return records
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            records.append(item)
    return records


def handoff_target(record: dict[str, Any]) -> str:
    """A handoff edge needs a destination. the after half of a task tool call
    has none, so it stays a plain tool event instead of inventing a bot."""
    handoff = record.get("handoff")
    if isinstance(handoff, dict):
        found = clean(handoff.get("to") or handoff.get("subagent_type")).lower()
        if found:
            return found
    if str(record.get("tool", "")).lower() == "task" or str(record.get("type", "")).lower() == "task":
        return clean(record.get("subagent_type") or record.get("to")).lower()
    return ""


def is_handoff(record: dict[str, Any]) -> bool:
    return handoff_target(record) != ""


def tool_label(record: dict[str, Any]) -> str:
    tool = str(record.get("tool", record.get("type", "event"))).lower()
    if record.get("command"):
        return f"{tool}: {clip(clean(record['command']), SNIPPET_MAX)}"
    if record.get("path"):
        return f"{tool}: {clean(record['path']).rsplit('/', 1)[-1].rsplit(chr(92), 1)[-1]}"
    todos = record.get("todos")
    if isinstance(todos, list) and todos:
        return f"{tool}: {len(todos)} items"
    if record.get("text"):
        return f"{tool}: {clip(clean(record['text']), SNIPPET_MAX)}"
    return tool


@dataclass
class State:
    session: str
    source: str
    generated: str
    roster_note: str
    agents: list[Agent]
    edges: list[dict[str, Any]]
    tasks: list[dict[str, Any]]
    timeline: list[dict[str, Any]]
    records: int
    synthetic_agents: int
    current_task: str

    def payload(self) -> dict[str, Any]:
        return {
            "session": self.session,
            "source": self.source,
            "generated": self.generated,
            "roster_note": self.roster_note,
            "roster": [
                {"name": a.name, "description": a.description, "mode": a.mode, "lane": a.lane}
                for a in self.agents
            ],
            "agents": [asdict(a) for a in self.agents],
            "edges": self.edges,
            "tasks": self.tasks,
            "timeline": self.timeline,
            "records": self.records,
            "synthetic_agents": self.synthetic_agents,
            "current_task": self.current_task,
        }


def build_state(root: Path, source: Path) -> State:
    roster, note = load_roster(root)
    index = agent_index(roster)
    records = load_records(source)
    # the before half of a call carries the shape, the after half carries the
    # outcome. pair them by call id so the timeline shows one row per call.
    after_by_call: dict[str, dict[str, Any]] = {}
    before_calls: set[str] = set()
    for record in records:
        call = str(record.get("callID", "")).strip()
        phase = str(record.get("phase", ""))
        if not call:
            continue
        if phase == "after":
            after_by_call[call] = record
        elif phase == "before":
            before_calls.add(call)
    edges: list[dict[str, Any]] = []
    seen_edges: set[tuple[str, str, str]] = set()
    tasks: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    timeline: list[dict[str, Any]] = []
    synthetic = [0]

    def resolve(name: Any) -> Agent | None:
        """Look an agent up by name. an empty name means nobody owns the record."""
        key = clean(name).lower()
        if key == "":
            return None
        agent = index.get(key)
        if agent is None:
            agent = Agent(
                name=key,
                description="agent seen in telemetry but absent from the persona directory.",
                mode="unknown",
                permission="",
                lane=lane_for(key, ""),
                synthetic=True,
            )
            index[key] = agent
            roster.append(agent)
            synthetic[0] += 1
        return agent

    for position, record in enumerate(records):
        owner = resolve(record.get("agent"))
        owner_name = owner.name if owner is not None else "unattributed"
        kind = "event"
        label = clean(record.get("event", "")) or clean(record.get("type", "event"))
        ok = record.get("ok")
        rtype = str(record.get("type", "")).lower()
        tool = str(record.get("tool", "")).lower()
        phase = str(record.get("phase", ""))
        call = str(record.get("callID", "")).strip()
        paired = after_by_call.get(call) if call else None
        if phase == "after" and call in before_calls:
            # the before half already produced this row, with the same label
            continue
        if phase == "before" and paired is not None:
            ok = paired.get("ok")

        if isinstance(record.get("todos"), list):
            # the task board is a board in its own right, so it is collected
            # even when the record carries no agent.
            for todo in record["todos"]:
                if not isinstance(todo, dict):
                    continue
                content = clip(clean(todo.get("content", "")), 90)
                if not content:
                    continue
                if content not in tasks:
                    order.append(content)
                tasks[content] = {
                    "content": content,
                    "status": clean(todo.get("status", "unknown")).lower() or "unknown",
                    "priority": clean(todo.get("priority", "unknown")).lower() or "unknown",
                    "agent": owner_name,
                    "index": position,
                }

        if is_handoff(record):
            handoff = record.get("handoff") if isinstance(record.get("handoff"), dict) else {}
            sender = resolve(handoff.get("from") or record.get("agent")) or owner
            if sender is None:
                sender = resolve("unattributed")
            target = resolve(handoff_target(record)) or resolve("unassigned")
            owner_name = sender.name
            edge_label = clip(clean(handoff.get("description") or record.get("description") or "delegate"), LABEL_MAX)
            key = (sender.name, target.name, edge_label)
            if key not in seen_edges:
                seen_edges.add(key)
                edges.append(
                    {
                        "from": sender.name,
                        "to": target.name,
                        "label": edge_label,
                        "index": position,
                        "ts": clean(record.get("ts", "")),
                    }
                )
            sender.sent += 1
            target.received += 1
            target.tasks += 1
            sender.last_index = max(sender.last_index, position)
            target.last_index = max(target.last_index, position)
            sender.last_label = f"handoff to {target.name}"
            kind = "handoff"
            label = f"to {target.name}: {edge_label}"
        elif owner is not None:
            if rtype == "tool":
                kind = "tool"
                if tool in WRITE_TOOLS and record.get("path"):
                    owner.files += 1
                    path_text = clean(record["path"])
                    if path_text not in owner.file_paths:
                        owner.file_paths.append(path_text)
                if record.get("phase") != "before":
                    owner.tools += 1
                if ok is False:
                    owner.errors += 1
                owner.last_index = max(owner.last_index, position)
                owner.last_label = tool_label(record)
            elif rtype == "chat.message":
                kind = "chat"
                owner.last_index = max(owner.last_index, position)
                owner.last_label = tool_label(record)
            elif rtype == "event":
                if ok is False:
                    owner.errors += 1
                owner.last_index = max(owner.last_index, position)
                owner.last_label = label
            label = tool_label(record) if kind in ("tool", "chat") else label

        timeline.append(
            {
                "index": position,
                "ts": clean(record.get("ts", "")),
                "kind": kind,
                "agent": owner_name,
                "label": label,
                "ok": ok,
            }
        )

    active_cut = max((agent.last_index for agent in roster), default=-1)
    for agent in roster:
        if agent.errors > 0:
            agent.status = "blocked"
        elif agent.last_index < 0:
            agent.status = "idle"
        elif agent.last_index == active_cut:
            agent.status = "active"
        else:
            agent.status = "done"

    board = [tasks[key] for key in order]
    current = next((item for item in board if item["status"] == "in_progress"), None)
    if current is None:
        current = next((item for item in board if item["status"] == "pending"), None)
    current_task = current["content"] if current else "none recorded"

    return State(
        session=clean(source.stem),
        source=clean(source),
        generated=now_iso(),
        roster_note=note,
        agents=sorted(roster, key=lambda a: (LANES.index(a.lane), a.name)),
        edges=edges,
        tasks=board,
        timeline=timeline,
        records=len(records),
        synthetic_agents=synthetic[0],
        current_task=current_task,
    )


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------


def avatar_svg(seed: str) -> str:
    """A bot head drawn in css terms. variant comes from the agent name."""
    variant = sum(ord(char) * (position + 3) for position, char in enumerate(seed)) % 4
    parts = [
        '<path d="M24 14 L24 7" />',
        '<circle class="avatar-dot" cx="24" cy="4.5" r="2.4" />',
        '<rect class="avatar-head" x="7" y="14" width="34" height="25" rx="7" />',
    ]
    if variant == 0:
        parts.append('<circle class="avatar-eye" cx="18" cy="25" r="2.6" />')
        parts.append('<circle class="avatar-eye" cx="30" cy="25" r="2.6" />')
        parts.append('<path d="M19 33 L29 33" />')
    elif variant == 1:
        parts.append('<path class="avatar-eye" d="M14 25 L22 25" />')
        parts.append('<path class="avatar-eye" d="M26 25 L34 25" />')
        parts.append('<path d="M19 33 Q24 36 29 33" />')
    elif variant == 2:
        parts.append('<path class="avatar-eye" d="M13 24 L35 24 L35 27 L13 27 Z" />')
        parts.append('<path d="M20 33 L28 33" />')
    else:
        parts.append('<path class="avatar-eye" d="M18 21 L22 27 L14 27 Z" />')
        parts.append('<path class="avatar-eye" d="M30 21 L34 27 L26 27 Z" />')
        parts.append('<circle class="avatar-dot" cx="21" cy="33" r="1.3" />')
        parts.append('<circle class="avatar-dot" cx="27" cy="33" r="1.3" />')
    return (
        '<svg class="avatar-svg" viewBox="0 0 48 48" aria-hidden="true" focusable="false">'
        + "".join(parts)
        + "</svg>"
    )


def agent_card(agent: Agent) -> str:
    persona = clip(clean(agent.description), PERSONA_MAX)
    mode = clean(agent.mode) or "unknown"
    permission = clean(agent.permission)
    meta = mode if not permission else f"{mode} / {clip(permission, 48)}"
    stats = (
        ("tasks", agent.tasks),
        ("tools", agent.tools),
        ("files", agent.files),
        ("out", agent.sent),
        ("in", agent.received),
        ("err", agent.errors),
    )
    stat_html = "".join(
        f'<div class="stat"><dt>{esc(label)}</dt><dd data-value="{value}">{value}</dd></div>' for label, value in stats
    )
    touched = ""
    if agent.file_paths:
        listed = " ".join(BULLET.join(esc(path) for path in agent.file_paths[:3]))
        touched = f'<p class="bot-files"><span class="k">files</span> {listed}</p>'
    last = ""
    if agent.last_label:
        last = f'<p class="bot-last"><span class="k">last</span> {esc(agent.last_label)}</p>'
    synthetic = ' <span class="tag">roster gap</span>' if agent.synthetic else ""
    return (
        f'<article class="bot" id="agent-{esc(agent.name)}" data-agent="{esc(agent.name)}" '
        f'data-lane="{esc(agent.lane)}" data-status="{esc(agent.status)}">'
        f'<div class="bot-top"><span class="avatar" aria-hidden="true">{avatar_svg(agent.name)}</span>'
        f'<div class="bot-id"><h3 class="bot-name">{esc(agent.name)}{synthetic}</h3>'
        f'<p class="bot-mode">{esc(meta)}</p></div>'
        f'<span class="led" data-status="{esc(agent.status)}" title="{esc(agent.status)}">'
        f'<span class="sr-only">{esc(agent.status)}</span></span></div>'
        f'<p class="bot-persona">{esc(persona)}</p>'
        f'<dl class="bot-stats">{stat_html}</dl>'
        f"{touched}{last}"
        f"</article>"
    )


def lane_block(lane: str, agents: Iterable[Agent]) -> str:
    cards = "".join(agent_card(agent) for agent in agents)
    return f'<div class="lane" data-lane="{esc(lane)}"><p class="lane-label">{esc(lane)}</p>{cards}</div>'


def task_card(task: dict[str, Any]) -> str:
    return (
        f'<li class="task" data-status="{esc(task["status"])}" data-priority="{esc(task["priority"])}">'
        f'<p class="task-content">{esc(task["content"])}</p>'
        f'<p class="task-meta"><span class="pill">{esc(task["status"].replace("_", " "))}</span>'
        f'<span class="pill pill-quiet">{esc(task["priority"])}</span>'
        f'<span class="task-owner">{esc(task["agent"])}</span></p></li>'
    )


def timeline_row(entry: dict[str, Any]) -> str:
    machine, clock = short_time(entry["ts"])
    stamp = f'<time datetime="{html_lib.escape(machine, quote=True)}">{esc(clock)}</time>' if machine else f"<span>{esc(clock)}</span>"
    state = "ok" if entry.get("ok") is not False else "bad"
    return (
        f'<li class="tl" data-kind="{esc(entry["kind"])}" data-state="{state}">{stamp}'
        f'<span class="tl-agent">{esc(entry["agent"])}</span>'
        f'<span class="tl-label">{esc(entry["label"])}</span></li>'
    )


def self_check(document: str) -> dict[str, int]:
    return {
        "dashes": document.count("\u2014") + document.count("\u2013"),
        "inline_width": len(re.findall(r'style="[^"]*width', document)),
    }


CSS = """
*, *::before, *::after { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
html[data-lens="culture"] {
  --bg-primary: #120305;
  --bg-surface: #1B1214;
  --bg-elevated: #241A1C;
  --bg-input: #2C2023;
  --border-subtle: #362529;
  --border-active: #4F353B;
  --text-primary: #F5ECE8;
  --text-muted: #B5A5A0;
  --text-soft: #B58287;
  --accent-crimson: #C85250;
  --accent-wine: #9A3836;
  --accent-dim: rgba(200, 82, 80, 0.14);
  --led-active: #C85250;
  --led-idle: #6A5459;
  --led-done: #8AA47C;
  --led-blocked: #D98A3A;
  --task-open: #B5A5A0;
  --task-active: #C85250;
  --task-closed: #8AA47C;
  --task-queued: #6A5459;
  --shadow: rgba(0, 0, 0, 0.55);
}
html[data-lens="systems"] {
  --bg-primary: #FBFBFA;
  --bg-surface: #F2F2ED;
  --bg-elevated: #ECECE6;
  --bg-input: #FFFFFF;
  --border-subtle: #E5E5DF;
  --border-active: #D4D4CE;
  --text-primary: #111110;
  --text-muted: #555550;
  --text-soft: #6B6B66;
  --accent-crimson: #DC2626;
  --accent-wine: #991B1B;
  --accent-dim: rgba(220, 38, 38, 0.08);
  --led-active: #DC2626;
  --led-idle: #C4C4BE;
  --led-done: #4F7A46;
  --led-blocked: #B45309;
  --task-open: #555550;
  --task-active: #DC2626;
  --task-closed: #4F7A46;
  --task-queued: #A8A8A2;
  --shadow: rgba(0, 0, 0, 0.12);
}
:root {
  --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  --font-mono: ui-monospace, "JetBrains Mono", "Cascadia Mono", Consolas, "Courier New", monospace;
  --radius-sm: 6px;
  --radius-md: 12px;
  --radius-full: 9999px;
  --measure: 74ch;
}
html, body { margin: 0; padding: 0; }
body {
  background: var(--bg-primary);
  color: var(--text-primary);
  font-family: var(--font-sans);
  font-size: 16px;
  line-height: 1.6;
  overflow-x: clip;
}
img, svg { max-width: 100%; }
a { color: var(--accent-crimson); }
.sr-only {
  position: absolute; margin: -1px; padding: 0; border: 0;
  clip: rect(0 0 0 0); clip-path: inset(50%); overflow: hidden; white-space: nowrap;
}
.wrap {
  max-width: 1180px;
  margin: 0 auto;
  padding: 0 1.1rem;
  min-width: 0;
}
.skip {
  position: absolute; left: -9999px; top: 0; background: var(--bg-elevated);
  color: var(--text-primary); padding: 0.6rem 0.9rem; z-index: 10;
}
.skip:focus { left: 0.5rem; top: 0.5rem; }
.site-header {
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg-surface);
  position: sticky; top: 0; z-index: 5;
}
.head {
  display: flex; flex-wrap: wrap; align-items: center; gap: 0.7rem 1.1rem;
  padding-top: 0.7rem; padding-bottom: 0.7rem;
}
.brand {
  font-family: var(--font-mono); font-size: 0.95rem; font-weight: 700;
  text-decoration: none; color: var(--text-primary); display: inline-flex; align-items: center; gap: 0.45rem;
}
.dot {
  inline-size: 9px; block-size: 9px; border-radius: var(--radius-full);
  background: var(--accent-crimson); box-shadow: 0 0 0 3px var(--accent-dim);
}
.head-meta { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-inline-start: auto; min-width: 0; }
.head-actions { display: flex; flex-wrap: wrap; gap: 0.4rem; }
button {
  min-height: 44px; min-width: 44px; padding: 0.4rem 0.85rem;
  font-family: var(--font-mono); font-size: 0.76rem; letter-spacing: 0.04em;
  color: var(--text-primary); background: var(--bg-elevated);
  border: 1px solid var(--border-active); border-radius: var(--radius-sm); cursor: pointer;
}
button:hover { border-color: var(--accent-crimson); color: var(--accent-crimson); }
button:focus-visible { outline: 2px solid var(--accent-crimson); outline-offset: 2px; }
.pill {
  display: inline-block; padding: 0.15rem 0.55rem; border-radius: var(--radius-full);
  font-family: var(--font-mono); font-size: 0.7rem; letter-spacing: 0.05em;
  border: 1px solid var(--border-active); color: var(--text-muted); min-width: 0;
}
.pill-quiet { border-color: var(--border-subtle); color: var(--text-soft); }
.badge { border-color: var(--accent-crimson); color: var(--accent-crimson); }
.badge[data-live="live"] { background: var(--accent-dim); }
.badge[data-live="stale"] { color: var(--led-blocked); border-color: var(--led-blocked); }
h1 {
  font-size: 1.5rem; line-height: 1.25; margin: 1.4rem 0 0.4rem; letter-spacing: -0.01em;
  overflow-wrap: anywhere;
}
h2 {
  font-size: 1.05rem; margin: 0 0 0.7rem; letter-spacing: 0.02em;
  text-transform: lowercase; font-family: var(--font-mono); color: var(--accent-crimson);
}
.kicker { color: var(--text-muted); margin: 0 0 1.1rem; max-width: var(--measure); font-size: 0.92rem; }
.meta-row {
  display: flex; flex-wrap: wrap; gap: 0.45rem; align-items: center;
  font-family: var(--font-mono); font-size: 0.72rem; color: var(--text-soft); margin: 0 0 1.2rem;
}
section { margin: 0 0 1.8rem; }
.legend { display: flex; flex-wrap: wrap; gap: 0.4rem 0.9rem; margin: 0 0 0.8rem; }
.legend span { display: inline-flex; align-items: center; gap: 0.35rem; font-family: var(--font-mono); font-size: 0.7rem; color: var(--text-muted); }
.map { position: relative; }
.lanes { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 0.7rem; align-items: start; }
.lane { min-width: 0; border-left: 1px dashed var(--border-subtle); padding-inline-start: 0.7rem; }
.lane-label {
  font-family: var(--font-mono); font-size: 0.68rem; letter-spacing: 0.14em;
  text-transform: uppercase; color: var(--text-soft); margin: 0 0 0.5rem;
}
.bot {
  background: var(--bg-surface); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md); padding: 0.75rem; margin: 0 0 0.7rem;
  min-width: 0; overflow-wrap: anywhere; box-shadow: 0 4px 18px var(--shadow);
}
.bot[data-status="active"] { border-color: var(--accent-crimson); }
.bot[data-status="blocked"] { border-color: var(--led-blocked); }
.bot-top { display: flex; align-items: flex-start; gap: 0.55rem; min-width: 0; }
.avatar { flex: 0 0 auto; color: var(--text-muted); }
.bot[data-status="active"] .avatar { color: var(--accent-crimson); }
.bot[data-status="blocked"] .avatar { color: var(--led-blocked); }
.bot[data-status="done"] .avatar { color: var(--led-done); }
.avatar-svg { display: block; inline-size: 34px; block-size: 34px; fill: none; stroke: currentColor; stroke-width: 1.6; }
.avatar-dot { fill: currentColor; stroke: none; }
.avatar-head, .avatar-eye { fill: none; }
.bot-id { min-width: 0; }
.bot-name { font-size: 0.9rem; margin: 0; font-family: var(--font-mono); letter-spacing: 0.01em; }
.bot-mode { font-size: 0.66rem; margin: 0.1rem 0 0; color: var(--text-soft); font-family: var(--font-mono); }
.led {
  display: inline-block; margin-inline-start: auto; flex: 0 0 auto;
  inline-size: 10px; block-size: 10px;
  border-radius: var(--radius-full); background: var(--led-idle);
  box-shadow: 0 0 0 3px var(--bg-primary);
}
.led[data-status="active"] { background: var(--led-active); animation: pulse 1.8s ease-in-out infinite; }
.led[data-status="done"] { background: var(--led-done); }
.led[data-status="blocked"] { background: var(--led-blocked); }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.35; } }
@media (prefers-reduced-motion: reduce) { .led { animation: none; } }
.bot-persona { font-size: 0.78rem; color: var(--text-muted); margin: 0.5rem 0 0; }
.bot-stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 0.3rem; margin: 0.6rem 0 0; }
.stat { min-width: 0; }
.stat dt { font-family: var(--font-mono); font-size: 0.6rem; color: var(--text-soft); text-transform: uppercase; letter-spacing: 0.08em; }
.stat dd { margin: 0; font-family: var(--font-mono); font-size: 0.95rem; color: var(--text-primary); }
.bot-files, .bot-last { font-size: 0.68rem; color: var(--text-soft); margin: 0.45rem 0 0; font-family: var(--font-mono); }
.k { color: var(--accent-crimson); }
.tag { font-size: 0.6rem; color: var(--led-blocked); font-family: var(--font-mono); }
.edges { position: absolute; inset: 0; pointer-events: none; overflow: visible; }
.edge-path { fill: none; stroke: var(--accent-crimson); stroke-width: 1.4; opacity: 0.75; }
.edge-path[data-state="bad"] { stroke: var(--led-blocked); stroke-dasharray: 4 3; }
.edge-label {
  position: absolute; transform: translate(-50%, -50%);
  background: var(--bg-elevated); border: 1px solid var(--border-active);
  border-radius: var(--radius-full); padding: 0.1rem 0.5rem;
  font-family: var(--font-mono); font-size: 0.64rem; color: var(--text-muted);
  max-width: 12rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.board { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.55rem; grid-template-columns: repeat(auto-fill, minmax(min(100%, 17rem), 1fr)); }
.task {
  background: var(--bg-surface); border: 1px solid var(--border-subtle);
  border-inline-start: 4px solid var(--task-open);
  border-radius: var(--radius-sm); padding: 0.6rem 0.7rem; min-width: 0; overflow-wrap: anywhere;
}
.task[data-status="in_progress"] { border-inline-start-color: var(--task-active); }
.task[data-status="completed"] { border-inline-start-color: var(--task-closed); }
.task[data-status="pending"] { border-inline-start-color: var(--task-queued); }
.task-content { margin: 0 0 0.4rem; font-size: 0.85rem; }
.task-meta { display: flex; flex-wrap: wrap; gap: 0.35rem; align-items: center; margin: 0; }
.task-owner { font-family: var(--font-mono); font-size: 0.66rem; color: var(--text-soft); }
.timeline { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.2rem; }
.tl {
  display: grid; grid-template-columns: 5.2rem 8.5rem minmax(0, 1fr); gap: 0.5rem;
  align-items: baseline; padding: 0.3rem 0.45rem; border-radius: var(--radius-sm);
  font-family: var(--font-mono); font-size: 0.72rem; border-inline-start: 3px solid var(--border-subtle);
  min-width: 0;
}
.tl time, .tl > span:first-child { color: var(--text-soft); }
.tl-agent { color: var(--accent-crimson); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tl-label { color: var(--text-muted); overflow-wrap: anywhere; }
.tl[data-kind="handoff"] { border-inline-start-color: var(--accent-crimson); }
.tl[data-kind="chat"] { border-inline-start-color: var(--led-done); }
.tl[data-state="bad"] .tl-label { color: var(--led-blocked); }
.site-footer { border-top: 1px solid var(--border-subtle); margin: 2rem 0 0; padding: 1.2rem 0 2.4rem; }
.foot-wordmark { font-size: 2.6rem; font-weight: 700; color: var(--border-active); margin: 0 0 0.5rem; letter-spacing: -0.02em; }
.checks { display: flex; flex-wrap: wrap; gap: 0.4rem 0.5rem; }
.check {
  font-family: var(--font-mono); font-size: 0.68rem; color: var(--text-soft);
  border: 1px solid var(--border-subtle); border-radius: var(--radius-full); padding: 0.1rem 0.55rem;
}
.check-pass { color: var(--led-done); border-color: var(--led-done); }
.check-fail { color: var(--led-blocked); border-color: var(--led-blocked); }
.note { font-size: 0.78rem; color: var(--text-muted); max-width: var(--measure); }
@media (max-width: 1080px) { .lanes { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
@media (max-width: 760px) { .lanes { grid-template-columns: repeat(2, minmax(0, 1fr)); } .head-meta { margin-inline-start: 0; } }
@media (max-width: 520px) {
  .lanes { grid-template-columns: minmax(0, 1fr); }
  .tl { grid-template-columns: minmax(0, 1fr); }
  h1 { font-size: 1.25rem; }
}
"""

SCRIPT = """
(function () {
  var root = document.documentElement;
  var map = document.getElementById("map");
  var svg = document.getElementById("edges");
  var layer = document.getElementById("edge-layer");
  var badge = document.getElementById("live-badge");
  var stamp = document.getElementById("live-stamp");
  var lensBtn = document.getElementById("lens-btn");
  var reloadBtn = document.getElementById("reload-btn");
  var themeMeta = document.querySelector('meta[name="theme-color"]');
  var labels = [].slice.call(document.querySelectorAll(".edge-label"));

  function token(name) {
    return getComputedStyle(root).getPropertyValue(name).trim();
  }

  function marker(color) {
    var found = document.getElementById("viz-arrow");
    if (!found) {
      found = document.createElementNS("http://www.w3.org/2000/svg", "marker");
      found.setAttribute("id", "viz-arrow");
      found.setAttribute("viewBox", "0 0 8 8");
      found.setAttribute("refX", "7");
      found.setAttribute("refY", "4");
      found.setAttribute("markerWidth", "5");
      found.setAttribute("markerHeight", "5");
      found.setAttribute("orient", "auto-start-reverse");
      var head = document.createElementNS("http://www.w3.org/2000/svg", "path");
      head.setAttribute("d", "M0 0 L8 4 L0 8 Z");
      found.appendChild(head);
      document.getElementById("edge-defs").appendChild(found);
    }
    found.firstChild.setAttribute("fill", color);
    return found;
  }

  function draw() {
    if (!map || !svg || !layer) return;
    var box = map.getBoundingClientRect();
    var accent = token("--accent-crimson") || "currentColor";
    marker(accent);
    svg.setAttribute("viewBox", "0 0 " + Math.max(box.width, 1) + " " + Math.max(box.height, 1));
    while (layer.firstChild) layer.removeChild(layer.firstChild);
    labels.forEach(function (label) { label.style.visibility = "hidden"; });
    labels.forEach(function (label) {
      var from = document.querySelector('.bot[data-agent="' + label.getAttribute("data-from") + '"]');
      var to = document.querySelector('.bot[data-agent="' + label.getAttribute("data-to") + '"]');
      if (!from || !to) return;
      var a = from.getBoundingClientRect();
      var b = to.getBoundingClientRect();
      var ax = a.left - box.left + a.width / 2;
      var ay = a.top - box.top + a.height / 2;
      var bx = b.left - box.left + b.width / 2;
      var by = b.top - box.top + b.height / 2;
      var rightward = bx >= ax;
      var x1 = rightward ? ax + a.width / 2 : ax - a.width / 2;
      var x2 = rightward ? bx - b.width / 2 : bx + b.width / 2;
      var bow = Math.max(Math.abs(x2 - x1) * 0.45, 14) * (rightward ? 1 : -1);
      var path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("class", "edge-path");
      path.setAttribute("d", "M" + x1 + " " + ay + " C" + (x1 + bow) + " " + ay +
        ", " + (x2 - bow) + " " + by + ", " + x2 + " " + by);
      path.setAttribute("marker-end", "url(#viz-arrow)");
      if (from.getAttribute("data-status") === "blocked") {
        path.setAttribute("data-state", "bad");
        path.setAttribute("marker-end", "");
        marker(token("--led-blocked") || accent);
      }
      layer.appendChild(path);
      label.style.left = (x1 + x2) / 2 + "px";
      label.style.top = (ay + by) / 2 + "px";
      label.style.visibility = "visible";
    });
  }

  function badgeSet(state, text) {
    if (!badge) return;
    badge.setAttribute("data-live", state);
    badge.textContent = text;
  }

  function poll() {
    if (location.protocol !== "http:" && location.protocol !== "https:") {
      badgeSet("static", "static");
      return;
    }
    fetch("api/session", { cache: "no-store" }).then(function (response) {
      if (!response.ok) throw new Error("bad status");
      return response.json();
    }).then(function (data) {
      badgeSet("live", "live");
      if (stamp && data && data.generated) stamp.textContent = "served " + String(data.generated);
    }).catch(function () {
      badgeSet("stale", "stale");
    });
  }

  if (lensBtn) {
    lensBtn.addEventListener("click", function () {
      var next = root.getAttribute("data-lens") === "systems" ? "culture" : "systems";
      root.setAttribute("data-lens", next);
      lensBtn.textContent = "lens: " + next;
      if (themeMeta) themeMeta.setAttribute("content", token("--bg-surface"));
      draw();
    });
  }
  if (reloadBtn) reloadBtn.addEventListener("click", function () { location.reload(); });
  window.addEventListener("resize", draw);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(draw);
  draw();
  poll();
  window.setInterval(poll, 2000);
})();
"""


def render_html(state: State, dashes: int, inline_width: int, redactions: int) -> str:
    """Assemble the whole page. no external asset, no font, no network."""
    by_lane: dict[str, list[Agent]] = {lane: [] for lane in LANES}
    for agent in state.agents:
        by_lane.setdefault(agent.lane, []).append(agent)
    lanes = "".join(lane_block(lane, by_lane.get(lane, [])) for lane in LANES)

    edge_labels = "".join(
        f'<span class="edge-label" data-from="{esc(edge["from"])}" data-to="{esc(edge["to"])}">{esc(edge["label"])}</span>'
        for edge in state.edges
    )
    if not edge_labels:
        edge_labels = '<p class="note">no handoff edges in this session.</p>'

    board = "".join(task_card(task) for task in state.tasks)
    if not board:
        board = '<li class="task" data-status="pending" data-priority="unknown"><p class="task-content">no todowrite records in this session</p></li>'

    shown = state.timeline[-TIMELINE_CAP:]
    rows = "".join(timeline_row(entry) for entry in shown)
    truncated = len(state.timeline) - len(shown)

    active = [agent for agent in state.agents if agent.status == "active"]
    active_names = ", ".join(agent.name for agent in active) if active else "none"
    blocked = [agent for agent in state.agents if agent.status == "blocked"]
    blocked_names = ", ".join(agent.name for agent in blocked) if blocked else "none"

    dash_state = "pass" if dashes == 0 else "fail"
    width_state = "pass" if inline_width == 0 else "fail"
    machine, clock = short_time(state.generated)

    checks = [
        f'<span class="check check-{dash_state}">dashes: {dashes}</span>',
        f'<span class="check check-{width_state}">inline width styles: {inline_width}</span>',
        f'<span class="check">credential patterns scrubbed: {redactions}</span>',
        f'<span class="check">records: {state.records}</span>',
        f'<span class="check">agents: {len(state.agents)}</span>',
        f'<span class="check">handoff edges: {len(state.edges)}</span>',
        f'<span class="check">tasks: {len(state.tasks)}</span>',
        f'<span class="check">roster: {esc(state.roster_note)}</span>',
    ]
    if truncated > 0:
        checks.append(f'<span class="check">timeline shows the last {len(shown)} of {len(state.timeline)}</span>')

    legend = "".join(
        f'<span><i class="led" data-status="{status}"></i>{status}</span>'
        for status in ("active", "idle", "done", "blocked")
    )

    return f"""<!DOCTYPE html>
<html lang="en" data-lens="culture">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="dark light">
<meta name="theme-color" content="#1B1214">
<title>session map: {esc(state.session)} | naquuuu agent viz</title>
<meta name="description" content="lowercase game bot map of the seven agent roster, its task board, and its handoffs for one opencode session.">
<style>{CSS}</style>
</head>
<body>
<a class="skip" href="#map">skip to the map</a>
<header class="site-header">
  <div class="wrap head">
    <a class="brand" href="#top"><span class="dot" aria-hidden="true"></span>naquuuu</a>
    <div class="head-meta">
      <span class="pill badge" id="live-badge" data-live="static" aria-live="polite">static</span>
      <span class="pill">session {esc(state.session)}</span>
      <span class="pill" id="live-stamp">written {esc(clock)}</span>
    </div>
    <div class="head-actions">
      <button type="button" id="lens-btn">lens: culture</button>
      <button type="button" id="reload-btn">reload</button>
    </div>
  </div>
</header>
<main class="wrap" id="top">
  <h1>session map: {esc(state.session)}</h1>
  <p class="kicker">game bot view of the roster at work. lanes read left to right as the pipeline. a card lights up when that agent was the last one to move. a dashed card means its last tool call failed.</p>
  <p class="meta-row">
    <span>active: {esc(active_names)}</span><span>{BULLET}</span>
    <span>blocked: {esc(blocked_names)}</span><span>{BULLET}</span>
    <span>current task: {esc(state.current_task)}</span><span>{BULLET}</span>
    <span>generated <time datetime="{html_lib.escape(machine, quote=True)}">{esc(clock)}</time></span>
  </p>

  <section aria-labelledby="map-title">
    <h2 id="map-title">the roster</h2>
    <div class="legend" aria-hidden="true">{legend}</div>
    <div class="map" id="map">
      <svg class="edges" id="edges" aria-hidden="true" focusable="false"><defs id="edge-defs"></defs><g id="edge-layer"></g></svg>
      <div class="lanes">{lanes}</div>
      {edge_labels}
    </div>
  </section>

  <section aria-labelledby="board-title">
    <h2 id="board-title">task board</h2>
    <ul class="board">{board}</ul>
  </section>

  <section aria-labelledby="timeline-title">
    <h2 id="timeline-title">timeline</h2>
    <ol class="timeline">{rows}</ol>
  </section>
</main>
<footer class="wrap site-footer">
  <p class="foot-wordmark" aria-hidden="true">naquuuu</p>
  <div class="checks">{''.join(checks)}</div>
  <p class="note">telemetry lives in {esc(DATA_DIRNAME)} and holds paths, commands, and task text only. file contents are never recorded. credential shaped strings are replaced with {esc(REDACTED)} twice, once when the record is written and again when this page is built, so a key in a record cannot reach a file git would accept. this page holds itself to the same dash and inline width rules as the blog.</p>
</footer>
<script>{SCRIPT}</script>
</body>
</html>
"""


def build_document(state: State) -> tuple[str, dict[str, int]]:
    """Two pass so the footer can report its own mechanical checks.

    the first pass is a dry run and does not count redactions. without that, a
    value scrubbed while building state would be counted once and a value
    scrubbed only at render time would be counted twice, because the second
    pass renders the same fields again. the number the page prints is the
    number of spans the scrubber actually removed on the way to this file.
    """
    global COUNT_REDACTIONS
    COUNT_REDACTIONS = False
    try:
        first = render_html(state, 0, 0, 0)
    finally:
        COUNT_REDACTIONS = True
    measured = self_check(first)
    document = render_html(state, measured["dashes"], measured["inline_width"], redaction_count())
    checks = self_check(document)
    checks["redactions"] = redaction_count()
    return document, checks


# --------------------------------------------------------------------------
# serve
# --------------------------------------------------------------------------


def make_handler(
    root: Path,
    session_file: Path,
    *,
    out_dir: Path | None = None,
    page_name: str = "",
    document: str = "",
) -> type[SimpleHTTPRequestHandler]:
    """Build the request handler for either serve mode.

    memory mode, document non empty: the rendered page is answered straight
    from the string. nothing is read from and nothing is written to the
    working tree, which is the whole point of dropping the default out path
    when --serve is used on its own.

    disk mode, out_dir given: the legacy static serve runs and "/" redirects
    to the written file.
    """
    memory = bool(document)

    class Handler(SimpleHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - stdlib naming
            path = urlparse(self.path).path
            if path == "/api/session":
                self.serve_api(root, session_file)
                return
            if memory:
                if path in ("/", "/index.html"):
                    self.send_page(document)
                    return
                self.send_error(404, "not found. memory mode serves only the session map.")
                return
            if path == "/":
                self.send_response(302)
                self.send_header("location", "/" + quote(page_name))
                self.end_headers()
                return
            super().do_GET()

        def send_page(self, body: str) -> None:
            raw = body.encode("utf-8")
            self.send_response(200)
            self.send_header("content-type", "text/html; charset=utf-8")
            self.send_header("cache-control", "no-store")
            self.send_header("content-length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def serve_api(self, root_dir: Path, source: Path) -> None:
            try:
                state = build_state(root_dir, source)
                raw = json.dumps(state.payload(), ensure_ascii=False).encode("utf-8")
                code = 200
            except Exception as exc:  # pragma: no cover - defensive
                raw = json.dumps({"error": str(exc)}).encode("utf-8")
                code = 500
            self.send_response(code)
            self.send_header("content-type", "application/json; charset=utf-8")
            self.send_header("cache-control", "no-store")
            self.send_header("content-length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, fmt: str, *args: Any) -> None:
            sys.stdout.write("  [serve] " + (fmt % args) + "\n")

    return Handler


def serve(handler: Callable[[], SimpleHTTPRequestHandler], port: int, label: str, open_browser: bool) -> int:
    try:
        httpd = ThreadingHTTPServer(("127.0.0.1", port), handler)
    except OSError as exc:
        print(f"  cannot bind 127.0.0.1:{port}. {exc}")
        return 2
    url = f"http://127.0.0.1:{port}/"
    print(f"  serving {label}")
    print(f"  page: {url}")
    print(f"  api:  {url}api/session")
    print("  ctrl-c to stop.")
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        httpd.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        print("\n  server stopped.")
    finally:
        httpd.server_close()
    return 0


def open_path(path: Path) -> None:
    try:
        webbrowser.open(path.resolve().as_uri())
        print(f"  opened {path}")
    except Exception:
        print(f"  could not open a browser for {path}. open it by hand.")


# --------------------------------------------------------------------------
# cli
# --------------------------------------------------------------------------


def report(state: State, written: str, checks: dict[str, int]) -> None:
    active = [agent for agent in state.agents if agent.status in ("active", "blocked")]
    print(f"  session:   {state.session}")
    print(f"  source:    {state.source}")
    print(f"  written:   {written or 'nothing. held in memory for --serve.'}")
    print(f"  roster:    {len(state.agents)} agents, {state.roster_note}")
    if state.synthetic_agents:
        print(f"  note:      {state.synthetic_agents} agent(s) in telemetry are absent from the persona directory")
    print(f"  active:    {', '.join(agent.name for agent in active) or 'none'}")
    print(f"  handoffs:  {len(state.edges)} edges")
    print(f"  current:   {state.current_task}")
    print(
        f"  checks:    dashes {checks['dashes']}, inline width styles {checks['inline_width']}, "
        f"credential patterns scrubbed {checks.get('redactions', 0)}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="render the agent session map for the workspace hub")
    parser.add_argument("--session", help="session id, defaults to the most recently modified jsonl file")
    parser.add_argument(
        "--out",
        help="output html path, defaults to " + DEFAULT_OUT + ". ignored by --serve, which serves from memory",
    )
    parser.add_argument("--serve", action="store_true", help="serve the page with a live api")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="port for --serve")
    parser.add_argument("--open", action="store_true", help="open the result in the default browser")
    args = parser.parse_args(argv)

    root = workspace_root()
    try:
        source = resolve_session_file(root, args.session)
    except FileNotFoundError as exc:
        print(f"  {exc}")
        return 2

    # the counter starts before the state is built, so the page reports every
    # span the scrubber removed, not only the ones removed at render time.
    reset_redactions()
    state = build_state(root, source)
    document, checks = build_document(state)

    # --serve on its own is a viewing action. internal-docs/ is tracked, so
    # falling back to DEFAULT_OUT here would dirty the working tree every time
    # the owner watched a live session. nothing goes to disk in this branch.
    if args.serve and not args.out:
        report(state, "", checks)
        handler = partial(make_handler(root, source, document=document))
        return serve(handler, args.port, "from memory. nothing written to the repository.", args.open)

    raw_out = Path(args.out) if args.out else Path(DEFAULT_OUT)
    out_path = raw_out if raw_out.is_absolute() else root / raw_out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(document, encoding="utf-8")
    relative = str(out_path.relative_to(root)) if str(out_path).startswith(str(root)) else str(out_path)
    report(state, relative, checks)

    if args.serve:
        handler = partial(
            make_handler(root, source, out_dir=out_path.parent, page_name=out_path.name),
            directory=str(out_path.parent),
        )
        return serve(handler, args.port, str(out_path.parent), args.open)
    if args.open:
        open_path(out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
