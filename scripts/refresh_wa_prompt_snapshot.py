#!/usr/bin/env python3
"""Invalidate only the contradictory prompt snapshot for the 2026-10-01 WhatsApp pwd turn.

The transcript and pinned tools are never modified. Default mode is read-only; use
--apply only after review. Output contains counters/booleans only, never row IDs or text.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
import sqlite3
import sys

INCIDENT_UTC = datetime(2026, 9, 30, 20, 35, tzinfo=timezone.utc).timestamp()
WINDOW_SECONDS = 90
CURRENT_HOST_AUTH_MARKER = "may add a system-only verdict for the active turn"
CURRENT_AUTH_VALUES = ("authorized", "not_authorized")
CONTRADICTORY_PROMPT_MARKER = "decision is not visible to you"
CONTRADICTORY_HISTORY_MARKER = "decision is not visible to you"
TARGET_USER_MARKERS = ("jalankan pwd saja", "jangan ubah apa pun")
PWD_RE = re.compile(r"\bpwd\b", re.IGNORECASE)


def current_prompt_contract(text: str) -> bool:
    normalized = text.lower()
    return (CURRENT_HOST_AUTH_MARKER in normalized
            and all(value in normalized for value in CURRENT_AUTH_VALUES)
            and CONTRADICTORY_PROMPT_MARKER not in normalized)


def _whatsapp(row: sqlite3.Row) -> bool:
    return "whatsapp" in str(row["source"] or "").lower() or "whatsapp" in str(row["session_key"] or "").lower()


def _snapshot(row: sqlite3.Row) -> str:
    return str(row["system_prompt"] or row["stored_prompt"] or "")


def select_incident_session(conn: sqlite3.Connection) -> tuple[str, str] | None:
    """Return the internal session key and stale prompt only for a unique exact incident row."""
    rows = conn.execute(
        """SELECT m.session_id,m.content,m.api_content,m.timestamp,
                  s.source,s.session_key,s.system_prompt,s.system_prompt_hash,sp.prompt AS stored_prompt
           FROM messages m JOIN sessions s ON s.id=m.session_id
           LEFT JOIN system_prompts sp ON sp.hash=s.system_prompt_hash
           WHERE m.role='user' AND m.timestamp BETWEEN ? AND ?""",
        (INCIDENT_UTC - WINDOW_SECONDS, INCIDENT_UTC + WINDOW_SECONDS),
    ).fetchall()
    matching: dict[str, str] = {}
    for row in rows:
        if not _whatsapp(row):
            continue
        user_text = f"{row['content'] or ''} {row['api_content'] or ''}"
        if not PWD_RE.search(user_text):
            continue
        prompt = _snapshot(row).lower()
        if (all(marker in user_text.lower() for marker in TARGET_USER_MARKERS)
                and CONTRADICTORY_PROMPT_MARKER in prompt
                and CURRENT_HOST_AUTH_MARKER not in prompt):
            matching[str(row["session_id"])] = _snapshot(row)
    if len(matching) != 1:
        return None
    session_id, prompt = next(iter(matching.items()))
    return session_id, prompt


def _snapshot_state(conn: sqlite3.Connection, session_id: str) -> tuple[int, int, str | None, str | None, str | None]:
    session = conn.execute(
        "SELECT system_prompt,system_prompt_hash,tool_names FROM sessions WHERE id=?", (session_id,)
    ).fetchone()
    if session is None:
        raise RuntimeError("target session disappeared")
    counts = conn.execute(
        "SELECT COUNT(*),COALESCE(SUM(id),0) FROM messages WHERE session_id=?", (session_id,)
    ).fetchone()
    return int(counts[0]), int(counts[1]), session[0], session[1], session[2]


def _transcript_fingerprint(conn: sqlite3.Connection, session_id: str) -> tuple[int, str, bool]:
    digest = hashlib.sha256()
    rows = conn.execute(
        "SELECT id,role,content,api_content,tool_call_id,tool_calls,tool_name,timestamp,active,compacted "
        "FROM messages WHERE session_id=? ORDER BY id", (session_id,)
    )
    count = 0
    stale_directive = False
    for row in rows:
        count += 1
        encoded = "\x1f".join("" if value is None else str(value) for value in row).encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
        text = " ".join(str(value or "") for value in row[2:6]).lower()
        if CONTRADICTORY_HISTORY_MARKER in text:
            stale_directive = True
    return count, digest.hexdigest(), stale_directive


def run(db_path: Path, hermes_home: Path, hermes_repo: Path, apply: bool, session_db_cls=None) -> int:
    soul_path = hermes_home / "SOUL.md"
    try:
        soul = soul_path.read_text(encoding="utf-8").lower()
    except (OSError, UnicodeError):
        print("active_prompt_contract=false")
        print("incident_match_count=0")
        return 2
    prompt_current = current_prompt_contract(soul)
    print(f"active_prompt_contract={str(prompt_current).lower()}")
    if not prompt_current:
        print("incident_match_count=0")
        return 2

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        candidate = select_incident_session(conn)
        if candidate is None:
            print("incident_match_count=0_or_ambiguous")
            return 2
        session_id, old_prompt = candidate
        before = _snapshot_state(conn, session_id)
        transcript_before = _transcript_fingerprint(conn, session_id)
        print("incident_match_count=1")
        print("stored_prompt_stale=true")
        print("contradictory_history_present=" + str(transcript_before[2]).lower())
        print("apply_requested=" + str(apply).lower())
    finally:
        conn.close()

    if not apply:
        return 0

    sys.path.insert(0, str(hermes_repo))
    if session_db_cls is None:
        from hermes_state import SessionDB as session_db_cls

    backup_dir = hermes_home / "backups" / "wa-owner-auth-prompt-refresh"
    if not backup_dir.exists():
        backup_dir.mkdir(mode=0o700, parents=True)
    elif backup_dir.stat().st_mode & 0o077:
        print("private_backup_dir=false")
        return 2
    backup_path = backup_dir / "wa-prompt-snapshot-20261001T033500WIB.txt"
    fd = os.open(backup_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(old_prompt.encode("utf-8"))

    # Re-read the exact target immediately before mutation. If another process has
    # advanced the route, changed its prompt, or appended transcript rows, fail closed.
    preflight = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    preflight.row_factory = sqlite3.Row
    try:
        current_candidate = select_incident_session(preflight)
        current_state = _snapshot_state(preflight, session_id)
        current_transcript = _transcript_fingerprint(preflight, session_id)
    finally:
        preflight.close()
    if (current_candidate is None or current_candidate[0] != session_id
            or current_candidate[1] != old_prompt or current_state != before
            or current_transcript[:2] != transcript_before[:2]):
        print("pre_mutation_precondition=false")
        return 4
    print("pre_mutation_precondition=true")

    db = session_db_cls(db_path)
    update_ok = True
    try:
        try:
            db.update_system_prompt(session_id, None)
        except Exception:
            update_ok = False
            try:
                db.update_system_prompt(session_id, old_prompt)
            except Exception:
                pass
    finally:
        db.close()

    verify = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        after = _snapshot_state(verify, session_id)
        transcript_after = _transcript_fingerprint(verify, session_id)
    finally:
        verify.close()
    unchanged_history = transcript_before[:2] == transcript_after[:2]
    unchanged_tool_pin = before[4] == after[4]
    invalidated = after[2] is None and after[3] is None
    if not (update_ok and unchanged_history and unchanged_tool_pin and invalidated):
        rollback_db = session_db_cls(db_path)
        try:
            rollback_db.update_system_prompt(session_id, old_prompt)
        finally:
            rollback_db.close()
        print("invalidation_verified=false")
        print("rollback_attempted=true")
        return 3
    print("invalidation_verified=true")
    print("transcript_unchanged=true")
    print("tool_pin_unchanged=true")
    print("session_and_history_preserved=true")
    print("prompt_snapshot_backup=" + str(backup_path))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path.home() / ".hermes" / "state.db")
    parser.add_argument("--hermes-home", type=Path, default=Path.home() / ".hermes")
    parser.add_argument("--hermes-repo", type=Path, default=Path.home() / ".hermes" / "hermes-agent")
    parser.add_argument("--apply", action="store_true", help="invalidate the unique matching session prompt snapshot")
    args = parser.parse_args()
    return run(args.db, args.hermes_home, args.hermes_repo, args.apply)


if __name__ == "__main__":
    raise SystemExit(main())
