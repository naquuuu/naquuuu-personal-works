"""Verify OpenCode model routing matches ADR-044 and corporate skills stay denied.

Usage:
  python scripts/verify_model_routing.py

Exit 0 when every pinned model matches EXPECTED and `mapclub-*` skills are denied;
exit 1 otherwise. Reads only opencode.jsonc (no secrets). Idempotent.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

# Single source of truth for ADR-044. Change only together with a new ADR.
EXPECTED: dict[str, str] = {
    "model": "opencode-go/deepseek-v4.1-flash",
    "small_model": "opencode-go/deepseek-v4.1-flash",
    "naquuuubot": "opencode-go/deepseek-v4.1-flash",
    "naquuuu-builder": "opencode-go/deepseek-v4.1-flash",
    "naquuuu-skeptic": "opencode-go/glm-5.3-flash",
    "naquuuu-verifier": "opencode-go/deepseek-v4-flash",
    "naquuuu-librarian": "opencode-go/muse-spark-1.3-contributor",
    "naquuuu-curator": "opencode-go/qwen3.8-flash",
    "naquuuu-scribe": "opencode-go/qwen3.8-flash",
}


def strip_jsonc(text: str) -> str:
    """Drop // line comments outside strings and trailing commas."""
    out, in_str, esc, i = [], False, False, 0
    while i < len(text):
        ch = text[i]
        if in_str:
            out.append(ch)
            esc = (ch == "\\") and not esc
            if ch == '"' and not esc:
                in_str = False
        elif ch == '"':
            in_str = True
            out.append(ch)
        elif text.startswith("//", i):
            while i < len(text) and text[i] != "\n":
                i += 1
            continue
        else:
            out.append(ch)
        i += 1
    return re.sub(r",(\s*[}\]])", r"\1", "".join(out))


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    root = Path(os.environ.get("NAQUUUU_WORKSPACE") or Path(__file__).resolve().parent.parent)
    config = json.loads(strip_jsonc((root / "opencode.jsonc").read_text(encoding="utf-8")))
    agents = config.get("agent", {})
    failures: list[str] = []

    for key, want in EXPECTED.items():
        got = config.get(key) if key in ("model", "small_model") else agents.get(key, {}).get("model")
        status = "ok" if got == want else "MISMATCH"
        if got != want:
            failures.append(key)
        print(f"  {status:8} {key:18} {got}")

    skill = config.get("permission", {}).get("skill")
    denied = isinstance(skill, dict) and skill.get("mapclub-*") == "deny"
    print(f"  {'ok' if denied else 'MISSING':8} {'skill mapclub-*':18} {'deny' if denied else skill}")
    if not denied:
        failures.append("skill mapclub-*")

    if failures:
        print(f"MODEL ROUTING: FAIL ({', '.join(failures)}). See ADR-044.")
        return 1
    print("MODEL ROUTING: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
